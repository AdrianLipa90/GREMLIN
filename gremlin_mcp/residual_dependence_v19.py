from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v12 import _iaaft_rows, _notch, _sha_array

SCHEMA="GREMLIN_RESIDUAL_DUAL_SURFACE_FUNCTIONAL_DEPENDENCE_V0_19"
VERSION="0.19.0"


def _knn_predictive_r2(x:np.ndarray,y:np.ndarray,k:int=5)->float:
    x=np.asarray(x,float)
    y=np.asarray(y,float)
    if x.shape!=y.shape or x.ndim!=1:
        raise ValueError("x/y must be equal-shape 1D arrays")
    if not (1<=k<len(x)):
        raise ValueError("invalid k")
    d=np.abs(x[:,None]-x[None,:])
    np.fill_diagonal(d,np.inf)
    idx=np.argpartition(d,k-1,axis=1)[:,:k]
    pred=np.mean(y[idx],axis=1)
    sst=float(np.sum((y-y.mean())**2))
    return 0.0 if sst==0.0 else float(1.0-np.sum((y-pred)**2)/sst)


def _max_functional_predictability(runs:np.ndarray,k:int=5)->tuple[float,dict[str,Any]]:
    x=np.asarray(runs,float)
    best=-np.inf
    witness={"run_i":None,"run_j":None,"direction":None}
    for i in range(len(x)):
        for j in range(i+1,len(x)):
            ij=_knn_predictive_r2(x[i],x[j],k)
            ji=_knn_predictive_r2(x[j],x[i],k)
            if ij>=ji:
                value=ij
                direction="i_to_j"
            else:
                value=ji
                direction="j_to_i"
            if value>best:
                best=float(value)
                witness={
                    "run_i":int(i),
                    "run_j":int(j),
                    "direction":direction,
                }
    return float(best),witness


def functional_dependence_surface_audit_v19(
    residual_runs:Sequence[Sequence[float]],
    candidate_bin:int,
    *,
    surface:str,
    null_count:int=255,
    iaaft_iterations:int=10,
    alpha:float=0.005,
    knn_k:int=5,
)->dict[str,Any]:
    residual=np.asarray(residual_runs,float)
    if residual.ndim!=2 or residual.shape[0]<8 or residual.shape[1]<64:
        raise ValueError("v0.19 requires [runs,samples] with >=8 runs and >=64 samples")
    if not np.all(np.isfinite(residual)):
        raise ValueError("residual must be finite")
    if surface not in {"raw","post_candidate_removal"}:
        raise ValueError("surface must be raw or post_candidate_removal")
    if not (0.0<alpha<1.0):
        raise ValueError("alpha must be in (0,1)")
    if 1.0/(null_count+1)>alpha:
        raise ValueError("null_count cannot resolve alpha")
    if iaaft_iterations<5:
        raise ValueError("iaaft_iterations must be >=5")

    def process(rows:np.ndarray)->np.ndarray:
        if surface=="raw":
            return np.asarray(rows,float)
        return _notch(np.asarray(rows,float),int(candidate_bin))

    observed_processed=process(residual)
    observed,witness=_max_functional_predictability(observed_processed,knn_k)

    seed=(
        int(_sha_array(residual)[:16],16)
        ^ int(hashlib.sha256(surface.encode()).hexdigest()[:16],16)
        ^ 0x19D19
    )
    rng=np.random.default_rng(seed)
    null=[]
    quality=[]
    for _ in range(int(null_count)):
        surrogate_raw,error=_iaaft_rows(residual,rng,int(iaaft_iterations))
        stat,_=_max_functional_predictability(process(surrogate_raw),knn_k)
        null.append(stat)
        quality.append(error)

    null=np.asarray(null,float)
    p=float((1+np.sum(null>=observed))/(len(null)+1))
    return {
        "surface":surface,
        "observed_max_knn_predictive_r2":observed,
        "witness":witness,
        "knn_k":int(knn_k),
        "family_scope":"MAX_OVER_ALL_RUN_PAIRS_AND_BOTH_PREDICTION_DIRECTIONS",
        "monte_carlo_p":p,
        "alpha":float(alpha),
        "invalidates_independence":bool(p<=alpha),
        "null_ensemble_size":int(len(null)),
        "null_kind":"RAW_IAAFT_THEN_IDENTICAL_SURFACE_OPERATOR",
        "median_surrogate_psd_relative_error":float(np.median(quality)),
        "q95_null":float(np.quantile(null,0.95)),
        "q99_null":float(np.quantile(null,0.99)),
        "claim_boundary":{
            "guard_is_universal_independence_test":False,
            "pass_proves_independence":False,
            "fail_identifies_cause":False,
            "conditional_mean_blind_spot_open":True,
        },
    }


def dual_surface_functional_dependence_audit_v19(
    residual_runs:Sequence[Sequence[float]],
    candidate_bin:int,
    *,
    total_alpha:float=0.01,
    null_count:int=255,
    iaaft_iterations:int=10,
    knn_k:int=5,
)->dict[str,Any]:
    if not (0.0<total_alpha<1.0):
        raise ValueError("total_alpha must be in (0,1)")
    surface_alpha=total_alpha/2.0
    if 1.0/(null_count+1)>surface_alpha:
        raise ValueError("null_count cannot resolve per-surface alpha")

    raw=functional_dependence_surface_audit_v19(
        residual_runs,
        candidate_bin,
        surface="raw",
        null_count=null_count,
        iaaft_iterations=iaaft_iterations,
        alpha=surface_alpha,
        knn_k=knn_k,
    )
    post=functional_dependence_surface_audit_v19(
        residual_runs,
        candidate_bin,
        surface="post_candidate_removal",
        null_count=null_count,
        iaaft_iterations=iaaft_iterations,
        alpha=surface_alpha,
        knn_k=knn_k,
    )

    raw_fail=bool(raw["invalidates_independence"])
    post_fail=bool(post["invalidates_independence"])

    if raw_fail and post_fail:
        status="RUN_DEPENDENCE_INVALIDATES_CROSSFIT"
        crossfit_valid=False
    elif raw_fail and not post_fail:
        status="OPERATOR_SENSITIVE_RUN_DEPENDENCE_AMBIGUOUS"
        crossfit_valid=False
    elif (not raw_fail) and post_fail:
        status="POST_OPERATOR_RUN_DEPENDENCE_INVALIDATES_CROSSFIT"
        crossfit_valid=False
    else:
        status="NO_REJECTION_UNDER_V19_FUNCTIONAL_GUARD"
        crossfit_valid=True

    out={
        "schema":SCHEMA,
        "version":VERSION,
        "status":status,
        "candidate_bin":int(candidate_bin),
        "total_alpha":float(total_alpha),
        "per_surface_alpha":float(surface_alpha),
        "raw_surface":raw,
        "post_candidate_removal_surface":post,
        "crossfit_valid_under_v19_functional_guard":bool(crossfit_valid),
        "policy":{
            "raw_surface_is_truly_unprocessed_residual":True,
            "post_surface_uses_existing_detrend_notch_operator":True,
            "operator_sensitive_disagreement_causes_abstention":True,
            "functional_guard_is_not_universal":True,
            "variance_only_dependence_can_escape":True,
            "pass_proves_independence":False,
            "fail_identifies_cause":False,
            "new_physics_from_guard":False,
            "time_fluctuation_claim_allowed":False,
        },
    }
    out["audit_sha256"]=hashlib.sha256(
        json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return out


__all__=[
    "SCHEMA",
    "VERSION",
    "_knn_predictive_r2",
    "_max_functional_predictability",
    "functional_dependence_surface_audit_v19",
    "dual_surface_functional_dependence_audit_v19",
]
