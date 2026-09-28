from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v12 import (
    analyze_residual_stack_v12,
    _iaaft_rows,
    _notch,
    _sha_array,
)

SCHEMA="GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_18"
VERSION="0.18.0"
_FEATURE_NAMES=("x","x2","x3","absx")


def _feature_bank(row:np.ndarray)->np.ndarray:
    x=np.asarray(row,float)
    scale=max(float(np.max(np.abs(x))),1e-15)
    u=x/scale
    feats=np.vstack([u,u*u,u*u*u,np.abs(u)])
    out=[]
    for f in feats:
        f=f-f.mean()
        norm=float(np.linalg.norm(f))
        out.append(np.zeros_like(f) if norm==0.0 else f/norm)
    return np.asarray(out)


def _max_nonlinear_dependence_stat(runs:np.ndarray)->tuple[float,dict[str,Any]]:
    banks=[_feature_bank(row) for row in np.asarray(runs,float)]
    best=-1.0
    witness={"run_i":None,"run_j":None,"feature_i":None,"feature_j":None}
    for i in range(len(banks)):
        for j in range(i+1,len(banks)):
            corr=np.abs(banks[i]@banks[j].T)
            idx=np.unravel_index(int(np.argmax(corr)),corr.shape)
            value=float(corr[idx])
            if value>best:
                best=value
                witness={
                    "run_i":int(i),
                    "run_j":int(j),
                    "feature_i":_FEATURE_NAMES[int(idx[0])],
                    "feature_j":_FEATURE_NAMES[int(idx[1])],
                }
    return max(best,0.0),witness


def nonlinear_run_dependence_audit_v18(
    residual_runs:Sequence[Sequence[float]],
    candidate_bin:int,
    *,
    null_count:int=511,
    iaaft_iterations:int=20,
    alpha:float=0.005,
)->dict[str,Any]:
    residual=np.asarray(residual_runs,float)
    if residual.ndim!=2 or residual.shape[0]<8 or residual.shape[1]<64:
        raise ValueError("v0.18 nonlinear audit requires [runs,samples] with >=8 runs and >=64 samples")
    if not np.all(np.isfinite(residual)):
        raise ValueError("residual must be finite")
    if not (0.0<alpha<1.0):
        raise ValueError("alpha must be in (0,1)")
    if null_count<1:
        raise ValueError("null_count must be positive")
    if 1.0/(null_count+1)>alpha:
        raise ValueError("null_count cannot resolve nonlinear alpha")
    if iaaft_iterations<5:
        raise ValueError("iaaft_iterations must be >=5")

    observed_processed=_notch(residual,int(candidate_bin))
    observed,witness=_max_nonlinear_dependence_stat(observed_processed)

    seed=int(_sha_array(residual)[:16],16) ^ 0x18A18
    rng=np.random.default_rng(seed)
    null=[]
    quality=[]
    for _ in range(int(null_count)):
        surrogate_raw,error=_iaaft_rows(residual,rng,int(iaaft_iterations))
        surrogate_processed=_notch(surrogate_raw,int(candidate_bin))
        stat,_=_max_nonlinear_dependence_stat(surrogate_processed)
        null.append(stat)
        quality.append(error)

    null=np.asarray(null,float)
    p=float((1+np.sum(null>=observed))/(len(null)+1))
    return {
        "observed_max_feature_dependence":observed,
        "witness":witness,
        "feature_bank":list(_FEATURE_NAMES),
        "family_scope":"MAX_OVER_ALL_RUN_PAIRS_AND_FEATURE_PAIRS",
        "monte_carlo_p":p,
        "alpha":float(alpha),
        "invalidates_crossfit":bool(p<=alpha),
        "null_ensemble_size":int(len(null)),
        "null_kind":"RAW_IAAFT_THEN_IDENTICAL_DETREND_NOTCH_THEN_NONLINEAR_MAX",
        "median_surrogate_psd_relative_error":float(np.median(quality)),
        "q95_null":float(np.quantile(null,0.95)),
        "q99_null":float(np.quantile(null,0.99)),
        "claim_boundary":{
            "pass_proves_independence":False,
            "fail_identifies_cause":False,
        },
    }


def analyze_residual_stack_v18(
    raw_runs:Sequence[Sequence[float]],
    model_runs:Sequence[Sequence[float]],
    *,
    run_dependence_alpha:float=0.01,
    run_dependence_null_count:int=511,
    iaaft_iterations:int=20,
    iaaft_null_applicable_declared:bool=False,
    **kwargs:Any,
)->dict[str,Any]:
    if not (0.0<run_dependence_alpha<1.0):
        raise ValueError("run_dependence_alpha must be in (0,1)")

    # Split experimentwise dependence-audit alpha between the existing v0.12
    # linear/circular family and the new nonlinear feature family.
    linear_alpha=run_dependence_alpha/2.0
    nonlinear_alpha=run_dependence_alpha/2.0

    base=analyze_residual_stack_v12(
        raw_runs,
        model_runs,
        iaaft_null_applicable_declared=iaaft_null_applicable_declared,
        run_dependence_alpha=linear_alpha,
        run_dependence_null_count=run_dependence_null_count,
        iaaft_iterations=iaaft_iterations,
        **kwargs,
    )

    out=dict(base)
    out["schema"]=SCHEMA
    out["version"]=VERSION
    out["legacy_v12_classification"]=base["classification"]

    base_valid=bool(
        base.get("policy",{}).get("crossfit_valid_under_run_dependence_audit",False)
    )

    if not iaaft_null_applicable_declared:
        nonlinear={
            "status":"NOT_EVALUATED_IAAFT_NULL_NOT_DECLARED",
            "invalidates_crossfit":None,
        }
    elif not base_valid:
        nonlinear={
            "status":"NOT_EVALUATED_BASE_V12_INVALID_OR_ABSTAIN",
            "invalidates_crossfit":None,
        }
    else:
        residual=np.asarray(raw_runs,float)-np.asarray(model_runs,float)
        gate=base["metrics"]["crossfit_narrowband_gate"]
        k=int(round(float(gate["median_discovery_bin"])))
        nonlinear=nonlinear_run_dependence_audit_v18(
            residual,
            k,
            null_count=run_dependence_null_count,
            iaaft_iterations=iaaft_iterations,
            alpha=nonlinear_alpha,
        )
        nonlinear["status"]="CALIBRATED_NONLINEAR_IAAFT_MAX_NULL"
        if nonlinear["invalidates_crossfit"]:
            out["classification"]="NONLINEAR_RUN_DEPENDENCE_INVALIDATES_CROSSFIT"

    out["metrics"]=dict(base["metrics"])
    out["metrics"]["nonlinear_run_dependence_audit_v18"]=nonlinear

    out["policy"]=dict(base["policy"])
    out["policy"].update({
        "run_dependence_total_alpha":float(run_dependence_alpha),
        "linear_family_alpha":float(linear_alpha),
        "nonlinear_family_alpha":float(nonlinear_alpha),
        "nonlinear_feature_family_max_null":True,
        "sparse_pair_dependence_not_aggregated_by_median":True,
        "nonlinear_audit_pass_proves_independence":False,
        "nonlinear_audit_fail_identifies_cause":False,
    })
    out["promotion_gates"]=[
        "nonlinear sparse-pair run-dependence max-null audit",
        *base["promotion_gates"],
    ]

    out.pop("analysis_sha256",None)
    out["analysis_sha256"]=hashlib.sha256(
        json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return out


__all__=[
    "SCHEMA",
    "VERSION",
    "_max_nonlinear_dependence_stat",
    "nonlinear_run_dependence_audit_v18",
    "analyze_residual_stack_v18",
]
