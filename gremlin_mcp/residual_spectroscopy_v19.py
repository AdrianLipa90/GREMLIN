from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v12 import (
    _iaaft_rows,
    _median_abs_lag1,
    _robust_nonstationarity_diagnostic,
    _sha_array,
)
from .residual_spectroscopy_v18 import analyze_residual_stack_v18

SCHEMA="GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_19"
VERSION="0.19.0"
_EULER_GAMMA=0.5772156649015328606


def _digamma_positive_integer_table(n:int)->np.ndarray:
    if n<1:
        raise ValueError("n must be positive")
    out=np.empty(n+1,float)
    out[0]=np.nan
    out[1]=-_EULER_GAMMA
    harmonic=0.0
    for j in range(2,n+1):
        harmonic += 1.0/(j-1)
        out[j]=harmonic-_EULER_GAMMA
    return out


def _ksg_mi_pair(x:np.ndarray,y:np.ndarray,k:int=3)->float:
    x=np.asarray(x,float).reshape(-1)
    y=np.asarray(y,float).reshape(-1)
    if x.shape!=y.shape or x.size<=k:
        raise ValueError("KSG inputs must have equal length > k")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("KSG inputs must be finite")

    dx=np.abs(x[:,None]-x[None,:])
    dy=np.abs(y[:,None]-y[None,:])
    joint=np.maximum(dx,dy)
    np.fill_diagonal(joint,np.inf)
    eps=np.partition(joint,k-1,axis=1)[:,k-1]
    if np.any(eps<=0.0):
        raise ValueError("exact ties make v0.19 KSG calibration unavailable")

    nx=np.sum(dx<eps[:,None],axis=1)-1
    ny=np.sum(dy<eps[:,None],axis=1)-1
    table=_digamma_positive_integer_table(x.size+1)
    return float(
        table[k]
        +table[x.size]
        -np.mean(table[nx+1]+table[ny+1])
    )


def _max_pair_ksg(runs:np.ndarray,k:int=3)->tuple[float,dict[str,int]]:
    x=np.asarray(runs,float)
    best=-np.inf
    witness={"run_i":-1,"run_j":-1,"k":int(k)}
    for i in range(x.shape[0]):
        for j in range(i+1,x.shape[0]):
            value=_ksg_mi_pair(x[i],x[j],k)
            if value>best:
                best=float(value)
                witness={"run_i":int(i),"run_j":int(j),"k":int(k)}
    return float(best),witness


def _exact_tie_fraction(row:np.ndarray)->float:
    x=np.asarray(row,float)
    return float(1.0-len(np.unique(x))/len(x))


def raw_run_dependence_ksg_audit_v19(
    residual_runs:Sequence[Sequence[float]],
    *,
    null_count:int=511,
    iaaft_iterations:int=20,
    alpha:float=0.005,
    k:int=3,
)->dict[str,Any]:
    residual=np.asarray(residual_runs,float)
    if residual.ndim!=2 or residual.shape[0]<8 or residual.shape[1]<64:
        raise ValueError("v0.19 RAW KSG audit requires [runs,samples] with >=8 runs and >=64 samples")
    if not np.all(np.isfinite(residual)):
        raise ValueError("residual must be finite")
    if not (0.0<alpha<1.0):
        raise ValueError("alpha must be in (0,1)")
    if k<1 or residual.shape[1]<=k:
        raise ValueError("invalid KSG neighbor count")
    if null_count<1 or 1.0/(null_count+1)>alpha:
        raise ValueError("null_count cannot resolve RAW KSG alpha")
    if iaaft_iterations<5:
        raise ValueError("iaaft_iterations must be >=5")

    tie_fractions=[_exact_tie_fraction(row) for row in residual]
    max_tie=float(max(tie_fractions))
    if max_tie>0.0:
        return {
            "status":"ABSTAIN_EXACT_TIES_PRESENT",
            "invalidates_crossfit":None,
            "max_exact_tie_fraction":max_tie,
            "claim_boundary":{
                "pass_proves_independence":False,
                "fail_identifies_cause":False,
            },
        }

    observed,witness=_max_pair_ksg(residual,k)
    seed=int(_sha_array(residual)[:16],16) ^ 0x19A19
    rng=np.random.default_rng(seed)
    null=[]
    quality=[]
    for _ in range(int(null_count)):
        surrogate,error=_iaaft_rows(residual,rng,int(iaaft_iterations))
        stat,_=_max_pair_ksg(surrogate,k)
        null.append(stat)
        quality.append(error)

    null=np.asarray(null,float)
    p=float((1+np.sum(null>=observed))/(len(null)+1))
    return {
        "status":"CALIBRATED_RAW_KSG_IAAFT_MAX_NULL",
        "observed_max_pair_ksg_mi":observed,
        "witness":witness,
        "family_scope":"MAX_OVER_ALL_RUN_PAIRS",
        "ksg_neighbors":int(k),
        "monte_carlo_p":p,
        "alpha":float(alpha),
        "invalidates_crossfit":bool(p<=alpha),
        "null_ensemble_size":int(len(null)),
        "null_kind":"RAW_INDEPENDENT_IAAFT_PER_RUN_THEN_MAX_PAIR_KSG",
        "seed_content_addressed":True,
        "median_surrogate_psd_relative_error":float(np.median(quality)),
        "q90_surrogate_psd_relative_error":float(np.quantile(quality,0.90)),
        "q95_null":float(np.quantile(null,0.95)),
        "q99_null":float(np.quantile(null,0.99)),
        "max_exact_tie_fraction":max_tie,
        "claim_boundary":{
            "pass_proves_independence":False,
            "fail_identifies_cause":False,
            "finite_sample_power_universal":False,
        },
    }


def analyze_residual_stack_v19(
    raw_runs:Sequence[Sequence[float]],
    model_runs:Sequence[Sequence[float]],
    *,
    run_dependence_alpha:float=0.01,
    run_dependence_null_count:int=511,
    iaaft_iterations:int=20,
    iaaft_null_applicable_declared:bool=False,
    max_median_surrogate_psd_relative_error:float=0.15,
    long_memory_lag1_abstain:float=0.97,
    ksg_neighbors:int=3,
    **kwargs:Any,
)->dict[str,Any]:
    raw=np.asarray(raw_runs,float)
    model=np.asarray(model_runs,float)
    if raw.shape!=model.shape or raw.ndim!=2:
        raise ValueError("raw/model must be equal-shape 2D arrays")
    residual=raw-model

    if not (0.0<run_dependence_alpha<1.0):
        raise ValueError("run_dependence_alpha must be in (0,1)")
    raw_alpha=run_dependence_alpha/2.0
    legacy_alpha=run_dependence_alpha/2.0

    nonstationary=_robust_nonstationarity_diagnostic(residual)
    lag1=_median_abs_lag1(np.asarray([
        row-np.mean(row) for row in residual
    ]))

    if not iaaft_null_applicable_declared:
        raw_audit={
            "status":"IAAFT_NULL_NOT_DECLARED",
            "invalidates_crossfit":None,
        }
        classification="RAW_RUN_DEPENDENCE_AUDIT_IAAFT_NULL_NOT_DECLARED"
        crossfit_valid=False
        base=None
    elif nonstationary["obvious_nonstationarity"]:
        raw_audit={
            "status":"NONSTATIONARY_HARD_ABSTENTION",
            "invalidates_crossfit":None,
        }
        classification="RAW_RUN_DEPENDENCE_AUDIT_NONSTATIONARY_UNCALIBRATED"
        crossfit_valid=False
        base=None
    elif lag1>=long_memory_lag1_abstain:
        raw_audit={
            "status":"LONG_MEMORY_HARD_ABSTENTION",
            "invalidates_crossfit":None,
        }
        classification="RAW_RUN_DEPENDENCE_AUDIT_LONG_MEMORY_UNCALIBRATED"
        crossfit_valid=False
        base=None
    else:
        raw_audit=raw_run_dependence_ksg_audit_v19(
            residual,
            null_count=run_dependence_null_count,
            iaaft_iterations=iaaft_iterations,
            alpha=raw_alpha,
            k=ksg_neighbors,
        )
        if raw_audit["status"]=="ABSTAIN_EXACT_TIES_PRESENT":
            classification="RAW_RUN_DEPENDENCE_KSG_TIES_UNCALIBRATED"
            crossfit_valid=False
            base=None
        elif raw_audit["median_surrogate_psd_relative_error"]>max_median_surrogate_psd_relative_error:
            classification="RAW_RUN_DEPENDENCE_SURROGATE_QUALITY_UNCALIBRATED"
            crossfit_valid=False
            base=None
        elif raw_audit["invalidates_crossfit"]:
            classification="RAW_RUN_DEPENDENCE_INVALIDATES_CROSSFIT"
            crossfit_valid=False
            base=None
        else:
            base=analyze_residual_stack_v18(
                raw,
                model,
                run_dependence_alpha=legacy_alpha,
                run_dependence_null_count=run_dependence_null_count,
                iaaft_iterations=iaaft_iterations,
                iaaft_null_applicable_declared=True,
                **kwargs,
            )
            classification=base["classification"]
            crossfit_valid=bool(
                base.get("policy",{}).get(
                    "crossfit_valid_under_run_dependence_audit",False
                )
            )

    out={} if base is None else dict(base)
    out["schema"]=SCHEMA
    out["version"]=VERSION
    out["classification"]=classification
    out["shape"]=list(raw.shape)
    out["commitments"]={
        "raw_sha256":_sha_array(raw),
        "model_sha256":_sha_array(model),
        "residual_sha256":_sha_array(residual),
    }
    out["metrics"]=dict(out.get("metrics",{}))
    out["metrics"]["raw_run_dependence_ksg_audit_v19"]=raw_audit
    out["metrics"]["raw_nonstationarity_diagnostic_v19"]=nonstationary
    out["metrics"]["raw_median_abs_lag1_v19"]=float(lag1)
    out["policy"]=dict(out.get("policy",{}))
    out["policy"].update({
        "run_dependence_total_alpha":float(run_dependence_alpha),
        "raw_ksg_family_alpha":float(raw_alpha),
        "legacy_postprocessing_dependence_alpha":float(legacy_alpha),
        "raw_dependence_audit_precedes_notch_and_detrend":True,
        "postprocessing_cannot_rehabilitate_raw_dependence_failure":True,
        "raw_ksg_max_pair_family_null":True,
        "exact_ties_cause_abstention":True,
        "passing_raw_ksg_audit_proves_independence":False,
        "failing_raw_ksg_audit_identifies_cause":False,
        "crossfit_valid_after_v19":bool(crossfit_valid),
        "new_physics_from_residual_only":False,
        "time_fluctuation_claim_allowed":False,
    })
    out["promotion_gates"]=[
        "RAW max-pair KSG joint-IAAFT dependence audit before preprocessing",
        "exact-tie abstention",
        "RAW nonstationarity/long-memory abstention",
        *out.get("promotion_gates",[]),
    ]

    out.pop("analysis_sha256",None)
    out["analysis_sha256"]=hashlib.sha256(
        json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return out


__all__=[
    "SCHEMA",
    "VERSION",
    "_ksg_mi_pair",
    "_max_pair_ksg",
    "raw_run_dependence_ksg_audit_v19",
    "analyze_residual_stack_v19",
]
