from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v12 import (
    _iaaft_rows,
    _notch,
    _sha_array,
)
from .residual_spectroscopy_v18 import (
    _feature_bank,
    analyze_residual_stack_v18,
)

SCHEMA="GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_19"
VERSION="0.19.0"
_FEATURE_NAMES=("x","x2","x3","absx")


def _max_lagged_nonlinear_dependence_stat(
    runs:np.ndarray,
)->tuple[float,dict[str,Any]]:
    banks=[_feature_bank(row) for row in np.asarray(runs,float)]
    spectra=[np.fft.fft(bank,axis=1) for bank in banks]

    best=-1.0
    witness={
        "run_i":None,
        "run_j":None,
        "feature_i":None,
        "feature_j":None,
        "circular_lag":None,
    }

    for i in range(len(banks)):
        for j in range(i+1,len(banks)):
            for fi in range(len(_FEATURE_NAMES)):
                for fj in range(len(_FEATURE_NAMES)):
                    corr=np.fft.ifft(
                        spectra[i][fi]*np.conj(spectra[j][fj])
                    ).real
                    lag=int(np.argmax(np.abs(corr)))
                    value=float(abs(corr[lag]))
                    if value>best:
                        best=value
                        witness={
                            "run_i":int(i),
                            "run_j":int(j),
                            "feature_i":_FEATURE_NAMES[fi],
                            "feature_j":_FEATURE_NAMES[fj],
                            "circular_lag":lag,
                        }

    return max(best,0.0),witness


def lagged_nonlinear_run_dependence_audit_v19(
    residual_runs:Sequence[Sequence[float]],
    candidate_bin:int,
    *,
    null_count:int=511,
    iaaft_iterations:int=20,
    alpha:float=0.0033333333333333335,
)->dict[str,Any]:
    residual=np.asarray(residual_runs,float)
    if residual.ndim!=2 or residual.shape[0]<8 or residual.shape[1]<64:
        raise ValueError(
            "v0.19 lagged nonlinear audit requires [runs,samples] "
            "with >=8 runs and >=64 samples"
        )
    if not np.all(np.isfinite(residual)):
        raise ValueError("residual must be finite")
    if not (0.0<alpha<1.0):
        raise ValueError("alpha must be in (0,1)")
    if null_count<1:
        raise ValueError("null_count must be positive")
    if 1.0/(null_count+1)>alpha:
        raise ValueError("null_count cannot resolve lagged nonlinear alpha")
    if iaaft_iterations<5:
        raise ValueError("iaaft_iterations must be >=5")

    observed_processed=_notch(residual,int(candidate_bin))
    observed,witness=_max_lagged_nonlinear_dependence_stat(
        observed_processed
    )

    seed=int(_sha_array(residual)[:16],16) ^ 0x19A19
    rng=np.random.default_rng(seed)
    null=[]
    quality=[]
    for _ in range(int(null_count)):
        surrogate_raw,error=_iaaft_rows(
            residual,rng,int(iaaft_iterations)
        )
        surrogate_processed=_notch(
            surrogate_raw,int(candidate_bin)
        )
        stat,_=_max_lagged_nonlinear_dependence_stat(
            surrogate_processed
        )
        null.append(stat)
        quality.append(error)

    null=np.asarray(null,float)
    p=float((1+np.sum(null>=observed))/(len(null)+1))
    return {
        "observed_max_lagged_feature_dependence":observed,
        "witness":witness,
        "feature_bank":list(_FEATURE_NAMES),
        "lag_family":"ALL_CIRCULAR_LAGS",
        "family_scope":"MAX_OVER_ALL_RUN_PAIRS_FEATURE_PAIRS_AND_CIRCULAR_LAGS",
        "monte_carlo_p":p,
        "alpha":float(alpha),
        "invalidates_crossfit":bool(p<=alpha),
        "null_ensemble_size":int(len(null)),
        "null_kind":"RAW_IAAFT_THEN_IDENTICAL_DETREND_NOTCH_THEN_LAGGED_NONLINEAR_MAX",
        "median_surrogate_psd_relative_error":float(np.median(quality)),
        "q95_null":float(np.quantile(null,0.95)),
        "q99_null":float(np.quantile(null,0.99)),
        "claim_boundary":{
            "pass_proves_independence":False,
            "fail_identifies_cause":False,
            "circular_lag_is_physical_delay":False,
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
    **kwargs:Any,
)->dict[str,Any]:
    if not (0.0<run_dependence_alpha<1.0):
        raise ValueError("run_dependence_alpha must be in (0,1)")

    component_alpha=run_dependence_alpha/3.0

    # Give v0.12 linear/circular family and v0.18 zero-lag nonlinear
    # family two thirds of the total budget. v0.18 splits that input in
    # half, so each receives one third. v0.19 receives the final third.
    base=analyze_residual_stack_v18(
        raw_runs,
        model_runs,
        run_dependence_alpha=2.0*run_dependence_alpha/3.0,
        run_dependence_null_count=run_dependence_null_count,
        iaaft_iterations=iaaft_iterations,
        iaaft_null_applicable_declared=iaaft_null_applicable_declared,
        **kwargs,
    )

    out=dict(base)
    out["schema"]=SCHEMA
    out["version"]=VERSION
    out["legacy_v18_classification"]=base["classification"]

    base_linear_valid=bool(
        base.get("policy",{}).get(
            "crossfit_valid_under_run_dependence_audit",False
        )
    )
    v18_audit=(
        base.get("metrics",{})
        .get("nonlinear_run_dependence_audit_v18",{})
    )
    v18_invalid=(
        v18_audit.get("invalidates_crossfit") is True
    )
    base_valid=base_linear_valid and not v18_invalid

    if not iaaft_null_applicable_declared:
        lagged={
            "status":"NOT_EVALUATED_IAAFT_NULL_NOT_DECLARED",
            "invalidates_crossfit":None,
        }
    elif not base_valid:
        lagged={
            "status":"NOT_EVALUATED_BASE_V18_INVALID_OR_ABSTAIN",
            "invalidates_crossfit":None,
        }
    else:
        residual=np.asarray(raw_runs,float)-np.asarray(model_runs,float)
        gate=base["metrics"]["crossfit_narrowband_gate"]
        k=int(round(float(gate["median_discovery_bin"])))
        lagged=lagged_nonlinear_run_dependence_audit_v19(
            residual,
            k,
            null_count=run_dependence_null_count,
            iaaft_iterations=iaaft_iterations,
            alpha=component_alpha,
        )
        lagged["status"]="CALIBRATED_LAGGED_NONLINEAR_IAAFT_MAX_NULL"
        if lagged["invalidates_crossfit"]:
            out["classification"]="LAGGED_NONLINEAR_RUN_DEPENDENCE_INVALIDATES_CROSSFIT"

    out["metrics"]=dict(base["metrics"])
    out["metrics"]["lagged_nonlinear_run_dependence_audit_v19"]=lagged

    out["policy"]=dict(base["policy"])
    out["policy"].update({
        "run_dependence_total_alpha":float(run_dependence_alpha),
        "linear_circular_family_alpha":float(component_alpha),
        "zero_lag_nonlinear_family_alpha":float(component_alpha),
        "lagged_nonlinear_family_alpha":float(component_alpha),
        "lagged_nonlinear_family_max_null":True,
        "lag_scan_is_circular_index_not_physical_delay":True,
        "lagged_nonlinear_pass_proves_independence":False,
        "lagged_nonlinear_fail_identifies_cause":False,
    })
    out["promotion_gates"]=[
        "lagged nonlinear run-dependence max-null audit",
        *base["promotion_gates"],
    ]

    out.pop("analysis_sha256",None)
    out["analysis_sha256"]=hashlib.sha256(
        json.dumps(
            out,
            sort_keys=True,
            separators=(",",":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()
    return out


__all__=[
    "SCHEMA",
    "VERSION",
    "_max_lagged_nonlinear_dependence_stat",
    "lagged_nonlinear_run_dependence_audit_v19",
    "analyze_residual_stack_v19",
]
