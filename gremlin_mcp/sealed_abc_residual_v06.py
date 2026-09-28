from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from .recursive_residual_v04 import (
    _canonical_sha,
    _fit,
    _null_proxies,
    _validate_metadata,
    recursive_residual_decomposition_v04,
)
from .residual_spectroscopy_v05 import analyze_residual_stack_v05

SCHEMA="GREMLIN_SEALED_ABC_RESIDUAL_CONFIRMATION_V0_6"
VERSION="0.6.0"


def _as_index_array(values:Sequence[int],n_runs:int,name:str)->np.ndarray:
    idx=np.asarray(values,dtype=int)
    if idx.ndim!=1 or idx.size<8:
        raise ValueError(f"{name} must contain at least 8 run indices")
    if np.any(idx<0) or np.any(idx>=n_runs):
        raise ValueError(f"{name} contains out-of-range run index")
    if len(set(int(x) for x in idx))!=idx.size:
        raise ValueError(f"{name} contains duplicate run index")
    return idx


def _apply_model(
    initial:np.ndarray,
    components:Sequence[np.ndarray],
    beta:np.ndarray,
)->np.ndarray:
    out=np.array(initial,dtype=float,copy=True)
    for component,value in zip(components,beta):
        out+=float(value)*component
    return out


def _sealed_split_test(
    raw:np.ndarray,
    initial:np.ndarray,
    accepted_components:Sequence[np.ndarray],
    candidate:np.ndarray,
    beta_base:np.ndarray,
    beta_aug:np.ndarray,
    split:np.ndarray,
    *,
    null_policy:str,
    null_count:int,
    alpha:float,
    min_gain:float,
)->dict[str,Any]:
    base=_apply_model(
        initial[split],
        [c[split] for c in accepted_components],
        beta_base,
    )
    aug=_apply_model(
        initial[split],
        [c[split] for c in [*accepted_components,candidate]],
        beta_aug,
    )
    sse_base=float(np.sum((raw[split]-base)**2))
    if sse_base<=0.0:
        raise ValueError("degenerate sealed baseline SSE")
    gain=float(1.0-np.sum((raw[split]-aug)**2)/sse_base)

    null_gains=[]
    for null in _null_proxies(candidate[split],null_policy,null_count):
        null_aug=_apply_model(
            initial[split],
            [
                *[c[split] for c in accepted_components],
                null,
            ],
            beta_aug,
        )
        value=float(1.0-np.sum((raw[split]-null_aug)**2)/sse_base)
        null_gains.append(value)

    empirical_p=float(
        (1+np.sum(np.asarray(null_gains)>=gain))/(len(null_gains)+1)
    )
    return {
        "gain":gain,
        "empirical_p":empirical_p,
        "alpha":float(alpha),
        "null_worlds":len(null_gains),
        "min_gain":float(min_gain),
        "pass":bool(gain>min_gain and empirical_p<=alpha),
    }


def sealed_abc_residual_confirmation_v06(
    raw_runs:Sequence[Sequence[float]],
    initial_model_runs:Sequence[Sequence[float]],
    nuisance_components:Mapping[str,Sequence[Sequence[float]]],
    nuisance_metadata:Mapping[str,Mapping[str,Any]],
    *,
    discovery_runs:Sequence[int],
    confirmation_runs:Sequence[int],
    replication_runs:Sequence[int],
    analysis_plan_sha256:str,
    analysis_plan_frozen_before_fit:bool,
    sample_spacing:float=1.0,
    discovery_familywise_alpha:float=0.01,
    discovery_null_count:int=255,
    confirmation_alpha:float=0.01,
    confirmation_null_count:int=255,
    min_confirmation_gain:float=0.0,
    max_candidates:int=64,
    max_layers:int=8,
)->tuple[dict[str,Any],np.ndarray,np.ndarray]:
    raw=np.asarray(raw_runs,float)
    initial=np.asarray(initial_model_runs,float)
    if raw.shape!=initial.shape or raw.ndim!=2 or raw.shape[1]<64:
        raise ValueError("raw/initial must be equal-shape [runs,samples] with >=64 samples")
    if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(initial)):
        raise ValueError("raw/initial must be finite")
    if analysis_plan_frozen_before_fit is not True:
        raise ValueError("analysis plan was not frozen before fit")
    if (
        not isinstance(analysis_plan_sha256,str)
        or len(analysis_plan_sha256)!=64
        or any(ch not in "0123456789abcdef" for ch in analysis_plan_sha256.lower())
    ):
        raise ValueError("analysis_plan_sha256 must be a 64-character hex digest")
    if not (0.0<confirmation_alpha<1.0):
        raise ValueError("confirmation_alpha must be in (0,1)")
    if 1.0/(confirmation_null_count+1.0)>confirmation_alpha:
        raise ValueError("confirmation null ensemble cannot resolve confirmation_alpha")
    if len(nuisance_components)>max_candidates:
        raise ValueError("candidate family too large for sealed v0.6")

    A=_as_index_array(discovery_runs,raw.shape[0],"discovery_runs")
    B=_as_index_array(confirmation_runs,raw.shape[0],"confirmation_runs")
    C=_as_index_array(replication_runs,raw.shape[0],"replication_runs")
    if set(A)&set(B) or set(A)&set(C) or set(B)&set(C):
        raise ValueError("A/B/C run splits must be disjoint")

    names=sorted(str(name) for name in nuisance_components)
    _validate_metadata(nuisance_metadata,names)
    components={}
    for name in names:
        value=np.asarray(nuisance_components[name],float)
        if value.shape!=raw.shape or not np.all(np.isfinite(value)):
            raise ValueError(f"invalid nuisance component {name}")
        components[name]=value

    sliced_components={name:value[A] for name,value in components.items()}
    discovery,_,_=recursive_residual_decomposition_v04(
        raw[A],
        initial[A],
        sliced_components,
        nuisance_metadata,
        sample_spacing=sample_spacing,
        familywise_alpha=discovery_familywise_alpha,
        null_count=discovery_null_count,
        max_candidates=max_candidates,
        max_layers=max_layers,
    )
    proposals=list(discovery["accepted_layers"])

    confirmed=[]
    confirmation_stages=[]
    target_A=raw[A]-initial[A]

    for proposal_index,name in enumerate(proposals):
        accepted_full=[components[x] for x in confirmed]
        candidate=components[name]
        accepted_A=[x[A] for x in accepted_full]
        candidate_A=candidate[A]

        beta_base=_fit(target_A,accepted_A,np.arange(len(A)))
        beta_aug=_fit(
            target_A,
            [*accepted_A,candidate_A],
            np.arange(len(A)),
        )

        policy=str(nuisance_metadata[name]["null_policy"])
        test_B=_sealed_split_test(
            raw,
            initial,
            accepted_full,
            candidate,
            beta_base,
            beta_aug,
            B,
            null_policy=policy,
            null_count=confirmation_null_count,
            alpha=confirmation_alpha,
            min_gain=min_confirmation_gain,
        )
        test_C=_sealed_split_test(
            raw,
            initial,
            accepted_full,
            candidate,
            beta_base,
            beta_aug,
            C,
            null_policy=policy,
            null_count=confirmation_null_count,
            alpha=confirmation_alpha,
            min_gain=min_confirmation_gain,
        )

        stage={
            "proposal_index":proposal_index,
            "candidate":name,
            "fit_source":"A_ONLY",
            "refit_on_B":False,
            "refit_on_C":False,
            "confirmation_B":test_B,
            "replication_C":test_C,
            "pass":bool(test_B["pass"] and test_C["pass"]),
        }
        stage["stage_sha256"]=_canonical_sha(stage)
        confirmation_stages.append(stage)

        if not stage["pass"]:
            break
        confirmed.append(name)

    confirmed_full=[components[x] for x in confirmed]
    beta_final=_fit(
        target_A,
        [x[A] for x in confirmed_full],
        np.arange(len(A)),
    )
    evidence_model=_apply_model(initial,confirmed_full,beta_final)
    final_residual=raw-evidence_model
    # Sealed B/C data are not returned to a discovery-capable analyzer.
    # Residual discovery after confirmation remains restricted to A.
    discovery_residual_packet=analyze_residual_stack_v05(
        raw[A],evidence_model[A],sample_spacing=sample_spacing
    )
    sealed_residual_diagnostics={
        "B":{
            "residual_sha256":hashlib.sha256(
                np.ascontiguousarray(final_residual[B],dtype=np.float64).tobytes()
            ).hexdigest(),
            "sse":float(np.sum(final_residual[B]**2)),
            "spectral_discovery_permitted":False,
        },
        "C":{
            "residual_sha256":hashlib.sha256(
                np.ascontiguousarray(final_residual[C],dtype=np.float64).tobytes()
            ).hexdigest(),
            "sse":float(np.sum(final_residual[C]**2)),
            "spectral_discovery_permitted":False,
        },
    }

    alias_pairs=list(discovery.get("alias_pairs") or [])
    alias_with_confirmed=[
        pair for pair in alias_pairs
        if pair["left"] in confirmed or pair["right"] in confirmed
    ]

    if not proposals:
        status="NO_DISCOVERY_PROPOSAL"
    elif not confirmed:
        status="DISCOVERY_PROPOSAL_REJECTED_BY_SEALED_BC"
    elif len(confirmed)<len(proposals):
        status="PARTIAL_SEALED_ABC_PASS_STOPPED_ON_FAILURE"
    elif alias_with_confirmed:
        status="SEALED_ABC_PASS_WITH_ATTRIBUTION_ALIAS_OPEN"
    else:
        status="SEALED_ABC_PASS"

    split_payload={
        "A":[int(x) for x in A],
        "B":[int(x) for x in B],
        "C":[int(x) for x in C],
    }
    split_sha256=hashlib.sha256(
        json.dumps(split_payload,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()

    result={
        "schema":SCHEMA,
        "version":VERSION,
        "status":status,
        "analysis_plan_sha256":analysis_plan_sha256.lower(),
        "split_sha256":split_sha256,
        "splits":split_payload,
        "discovery_proposals":proposals,
        "confirmed_layers":confirmed,
        "confirmation_stages":confirmation_stages,
        "evidence_model_coefficients":{
            name:float(value)
            for name,value in zip(confirmed,beta_final)
        },
        "discovery_residual_packet_A":discovery_residual_packet,
        "sealed_residual_diagnostics":sealed_residual_diagnostics,
        "discovery_result_sha256":discovery["decomposition_sha256"],
        "attribution_ambiguous":bool(alias_with_confirmed),
        "policy":{
            "A_role":"DISCOVERY_AND_FIT_ONLY",
            "B_role":"SEALED_CONFIRMATION_NO_REFIT",
            "C_role":"SEALED_REPLICATION_NO_REFIT",
            "stop_on_first_sealed_failure":True,
            "no_discovery_on_B_or_C":True,
            "post_confirmation_residual_discovery_requires_fresh_D_or_new_dataset":True,
            "analysis_plan_frozen_before_fit":True,
            "destructive_denoising":False,
            "interpretation_last":True,
            "formal_joint_error_proof":False,
            "split_independence_required_for_error_interpretation":True,
            "same_visit_temporal_dependence_must_be_audited":True,
            "physical_mechanism_from_sealed_pass_only":False,
            "time_fluctuation_claim_allowed":False,
        },
    }
    result["confirmation_sha256"]=_canonical_sha(result)
    return result,evidence_model,final_residual


__all__=["SCHEMA","VERSION","sealed_abc_residual_confirmation_v06"]
