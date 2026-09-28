from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v12 import _iaaft_rows, _sha_array

SCHEMA="GREMLIN_PROVENANCE_BOUND_CONDITIONAL_RUN_DEPENDENCE_V0_19"
VERSION="0.19.0"
DEFAULT_SIGMAS=(0.02,0.03,0.05,0.08,0.10,0.20,0.40,0.80,1.60)


def _is_hex64(value: object)->bool:
    return (
        isinstance(value,str)
        and len(value)==64
        and all(ch in "0123456789abcdef" for ch in value.lower())
    )


def _validate_conditioner_provenance(meta: Mapping[str,Any])->None:
    if not isinstance(meta,Mapping):
        raise ValueError("conditioner provenance must be a mapping")
    required_true=(
        "frozen_before_target",
        "external_chronology_verified",
        "independent_of_target_fit",
    )
    for key in required_true:
        if meta.get(key) is not True:
            raise ValueError(f"conditioner provenance gate failed: {key}")
    if meta.get("derived_from_target") is not False:
        raise ValueError("target-derived conditioner is forbidden")
    if not isinstance(meta.get("source_id"),str) or not meta["source_id"]:
        raise ValueError("conditioner source_id missing")
    for key in (
        "operator_sha256",
        "covariate_commitment_sha256",
        "conditioned_runs_sha256",
    ):
        if not _is_hex64(meta.get(key)):
            raise ValueError(f"invalid conditioner commitment: {key}")


def _kernel_pack(
    runs: np.ndarray,
    sigmas: Sequence[float],
)->tuple[np.ndarray,np.ndarray,np.ndarray,list[tuple[int,float]]]:
    runs=np.asarray(runs,float)
    flats=[]
    row_sums=[]
    sums=[]
    meta=[]
    for i,row in enumerate(runs):
        sd=float(np.std(row))
        if sd<=0.0:
            z=row-float(np.mean(row))
        else:
            z=(row-float(np.mean(row)))/sd
        d2=(z[:,None]-z[None,:])**2
        for sigma in sigmas:
            sigma=float(sigma)
            if not np.isfinite(sigma) or sigma<=0.0:
                raise ValueError("all kernel sigmas must be finite and >0")
            K=np.exp(-0.5*d2/(sigma*sigma)).astype(np.float32)
            np.fill_diagonal(K,0.0)
            flats.append(K.reshape(-1))
            rs=K.sum(axis=1,dtype=np.float64)
            row_sums.append(rs.astype(np.float32))
            sums.append(float(rs.sum()))
            meta.append((int(i),sigma))
    return (
        np.stack(flats).astype(np.float32),
        np.stack(row_sums).astype(np.float32),
        np.asarray(sums,dtype=np.float64),
        meta,
    )


def _unbiased_hsic_matrix(
    runs: np.ndarray,
    sigmas: Sequence[float],
)->tuple[np.ndarray,list[tuple[int,float]]]:
    F,row_sums,sums,meta=_kernel_pack(runs,sigmas)
    n=int(runs.shape[1])
    term1=(F@F.T).astype(np.float64)
    term2=np.outer(sums,sums)/((n-1)*(n-2))
    term3=2.0*(row_sums@row_sums.T).astype(np.float64)/(n-2)
    H=(term1+term2-term3)/(n*(n-3))
    return H,meta


def _canonical_edges(n_runs:int,edges:Sequence[Sequence[int]]|None)->list[tuple[int,int]]:
    if edges is None:
        return [(i,j) for i in range(n_runs) for j in range(i+1,n_runs)]
    out=set()
    for edge in edges:
        if len(edge)!=2:
            raise ValueError("each edge must contain exactly two run indices")
        i,j=map(int,edge)
        if i==j or i<0 or j<0 or i>=n_runs or j>=n_runs:
            raise ValueError("invalid run-dependence edge")
        out.add(tuple(sorted((i,j))))
    if not out:
        raise ValueError("edge set must not be empty")
    return sorted(out)


def _max_family_hsic(
    runs: np.ndarray,
    edges: Sequence[tuple[int,int]],
    sigmas: Sequence[float],
)->tuple[float,dict[str,Any]]:
    H,meta=_unbiased_hsic_matrix(runs,sigmas)
    edge_set=set(edges)
    best=-np.inf
    witness=None
    for a,(i,sigma_i) in enumerate(meta):
        for b,(j,sigma_j) in enumerate(meta):
            if i>=j or (i,j) not in edge_set:
                continue
            value=float(H[a,b])
            if value>best:
                best=value
                witness={
                    "run_i":int(i),
                    "run_j":int(j),
                    "sigma_i":float(sigma_i),
                    "sigma_j":float(sigma_j),
                }
    if witness is None:
        raise RuntimeError("no admissible pair evaluated")
    return float(best),witness


def _family_hsic_iaaft_audit(
    runs: np.ndarray,
    *,
    edges: Sequence[tuple[int,int]],
    sigmas: Sequence[float],
    null_count:int,
    iaaft_iterations:int,
    alpha:float,
)->dict[str,Any]:
    if not (0.0<alpha<1.0):
        raise ValueError("alpha must be in (0,1)")
    if null_count<1:
        raise ValueError("null_count must be positive")
    if 1.0/(null_count+1)>alpha:
        raise ValueError("null_count cannot resolve declared alpha")
    if iaaft_iterations<5:
        raise ValueError("iaaft_iterations must be >=5")

    observed,witness=_max_family_hsic(runs,edges,sigmas)
    seed=int(_sha_array(runs)[:16],16) ^ 0x19C019
    rng=np.random.default_rng(seed)
    null=[]
    quality=[]
    for _ in range(int(null_count)):
        surrogate,error=_iaaft_rows(runs,rng,int(iaaft_iterations))
        stat,_=_max_family_hsic(surrogate,edges,sigmas)
        null.append(stat)
        quality.append(error)

    null=np.asarray(null,float)
    p=float((1+np.sum(null>=observed))/(len(null)+1))
    return {
        "observed_max_unbiased_hsic":observed,
        "witness":witness,
        "edge_count":int(len(edges)),
        "bandwidth_bank":[float(x) for x in sigmas],
        "family_scope":"MAX_OVER_PREDECLARED_RUN_EDGES_AND_KERNEL_BANDWIDTH_PAIRS",
        "monte_carlo_p":p,
        "alpha":float(alpha),
        "rejects_no_dependence_null":bool(p<=alpha),
        "null_ensemble_size":int(len(null)),
        "null_kind":"INDEPENDENT_RAW_IAAFT_PER_RUN_THEN_IDENTICAL_OMNIBUS_HSIC",
        "median_surrogate_psd_relative_error":float(np.median(quality)),
        "q95_null":float(np.quantile(null,0.95)),
        "q99_null":float(np.quantile(null,0.99)),
    }


def provenance_bound_conditional_run_dependence_audit_v19(
    raw_runs:Sequence[Sequence[float]],
    conditioned_runs:Sequence[Sequence[float]],
    conditioner_provenance:Mapping[str,Any],
    *,
    edges:Sequence[Sequence[int]]|None=None,
    kernel_sigmas:Sequence[float]=DEFAULT_SIGMAS,
    null_count:int=127,
    iaaft_iterations:int=10,
    alpha:float=0.01,
    iaaft_null_applicable_declared:bool=False,
)->dict[str,Any]:
    raw=np.asarray(raw_runs,float)
    conditioned=np.asarray(conditioned_runs,float)
    if raw.shape!=conditioned.shape or raw.ndim!=2 or raw.shape[0]<8 or raw.shape[1]<64:
        raise ValueError("v0.19 requires equal-shape [runs,samples] with >=8 runs and >=64 samples")
    if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(conditioned)):
        raise ValueError("raw/conditioned runs must be finite")

    _validate_conditioner_provenance(conditioner_provenance)
    actual_conditioned_sha=_sha_array(conditioned)
    if actual_conditioned_sha!=conditioner_provenance["conditioned_runs_sha256"].lower():
        raise ValueError("conditioned-run commitment mismatch")

    edge_list=_canonical_edges(raw.shape[0],edges)

    if not iaaft_null_applicable_declared:
        return {
            "schema":SCHEMA,
            "version":VERSION,
            "status":"ABSTAIN_IAAFT_NULL_NOT_DECLARED",
            "raw_sha256":_sha_array(raw),
            "conditioned_sha256":actual_conditioned_sha,
            "conditioner_provenance":dict(conditioner_provenance),
            "claims":{
                "independence_proven":False,
                "causal_independence_proven":False,
                "conditioner_truth_proven_by_code":False,
            },
        }

    raw_audit=_family_hsic_iaaft_audit(
        raw,
        edges=edge_list,
        sigmas=kernel_sigmas,
        null_count=null_count,
        iaaft_iterations=iaaft_iterations,
        alpha=alpha,
    )
    conditioned_audit=_family_hsic_iaaft_audit(
        conditioned,
        edges=edge_list,
        sigmas=kernel_sigmas,
        null_count=null_count,
        iaaft_iterations=iaaft_iterations,
        alpha=alpha,
    )

    raw_reject=bool(raw_audit["rejects_no_dependence_null"])
    conditioned_reject=bool(conditioned_audit["rejects_no_dependence_null"])

    if conditioned_reject:
        status="CONDITIONED_RUN_DEPENDENCE_DETECTED"
        crossfit_supported=False
    elif raw_reject:
        status="RAW_DEPENDENCE_EXPLAINED_BY_FROZEN_COVARIATE_CANDIDATE"
        crossfit_supported=True
    else:
        status="NO_DETECTED_DEPENDENCE_UNDER_FROZEN_CONDITIONING"
        crossfit_supported=True

    out={
        "schema":SCHEMA,
        "version":VERSION,
        "status":status,
        "raw_sha256":_sha_array(raw),
        "conditioned_sha256":actual_conditioned_sha,
        "conditioner_provenance":dict(conditioner_provenance),
        "edges":[list(edge) for edge in edge_list],
        "raw_audit":raw_audit,
        "conditioned_audit":conditioned_audit,
        "policy":{
            "conditioning_must_be_frozen_before_target":True,
            "target_derived_conditioning_forbidden":True,
            "external_chronology_required":True,
            "familywise_pair_and_bandwidth_max_statistic":True,
            "conditioned_pass_proves_independence":False,
            "crossfit_supported_under_this_audit":bool(crossfit_supported),
            "external_design_independence_still_required":True,
            "conditioner_truth_external_trust_root":True,
            "new_physics_from_dependence_audit":False,
            "time_fluctuation_claim_allowed":False,
        },
        "claims":{
            "independence_proven":False,
            "causal_independence_proven":False,
            "conditioner_truth_proven_by_code":False,
            "physical_mechanism_established":False,
            "new_physics_established":False,
            "time_fluctuation_established":False,
        },
    }
    out["analysis_sha256"]=hashlib.sha256(
        json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return out


__all__=[
    "SCHEMA",
    "VERSION",
    "DEFAULT_SIGMAS",
    "provenance_bound_conditional_run_dependence_audit_v19",
]
