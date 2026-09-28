from __future__ import annotations
import hashlib, json
from collections.abc import Mapping, Sequence
from typing import Any
import numpy as np
from .residual_spectroscopy_v09 import analyze_residual_stack_v09

SCHEMA="GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_10"
VERSION="0.10.0"

def _detrend(x):
    x=np.asarray(x,float); t=np.arange(x.size,dtype=float)
    y=x-np.polyval(np.polyfit(t,x,1),t)
    return y-y.mean()

def _notch(runs,k,w=3):
    out=[]
    for row in runs:
        y=_detrend(row); f=np.fft.rfft(y)
        f[max(1,k-w):min(len(f),k+w+1)]=0.0
        out.append(np.fft.irfft(f,n=len(y)))
    return np.asarray(out)

def _corr(a,b):
    a=a-a.mean(); b=b-b.mean()
    d=float(np.linalg.norm(a)*np.linalg.norm(b))
    return 0.0 if d==0.0 else float(np.dot(a,b)/d)

def _max_circular_corr(a,b):
    a=a-a.mean(); b=b-b.mean()
    d=float(np.linalg.norm(a)*np.linalg.norm(b))
    if d==0.0: return 0.0
    c=np.fft.irfft(np.fft.rfft(a)*np.conj(np.fft.rfft(b)),n=len(a))
    return float(np.max(np.abs(c))/d)

def _background_dependence(residual,k):
    x=_notch(residual,k); zero=[]; circ=[]
    for i in range(len(x)):
        for j in range(i+1,len(x)):
            zero.append(abs(_corr(x[i],x[j])))
            circ.append(_max_circular_corr(x[i],x[j]))
    return {
        "median_abs_zero_lag_correlation":float(np.median(zero)),
        "q90_abs_zero_lag_correlation":float(np.quantile(zero,.9)),
        "median_max_circular_correlation":float(np.median(circ)),
        "q90_max_circular_correlation":float(np.quantile(circ,.9)),
    }

def analyze_residual_stack_v10(
    raw_runs:Sequence[Sequence[float]],
    model_runs:Sequence[Sequence[float]],
    *,
    nuisance_runs=None, known_template_runs=None, channel_runs=None,
    sample_spacing:float=1.0, ordered_runs:bool=False,
    trend_ambiguity_cycles:float=3.0, accumulation_alpha:float=0.01,
    path_alpha:float=0.01, path_slope_max:float=1.5, path_slope_step:float=0.25,
    transient_half_alpha:float=0.01,
    max_median_zero_lag_background_corr:float=0.10,
    max_median_circular_background_corr:float=0.35,
)->dict[str,Any]:
    raw=np.asarray(raw_runs,float); model=np.asarray(model_runs,float)
    base=analyze_residual_stack_v09(
        raw,model,nuisance_runs=nuisance_runs,
        known_template_runs=known_template_runs,channel_runs=channel_runs,
        sample_spacing=sample_spacing,ordered_runs=ordered_runs,
        trend_ambiguity_cycles=trend_ambiguity_cycles,
        accumulation_alpha=accumulation_alpha,path_alpha=path_alpha,
        path_slope_max=path_slope_max,path_slope_step=path_slope_step,
        transient_half_alpha=transient_half_alpha,
    )
    residual=raw-model
    gate=base["metrics"]["crossfit_narrowband_gate"]
    k=int(round(float(gate["median_discovery_bin"])))
    dep=_background_dependence(residual,k)
    invalid=(dep["median_abs_zero_lag_correlation"]>max_median_zero_lag_background_corr
             or dep["median_max_circular_correlation"]>max_median_circular_background_corr)

    out=dict(base)
    out["schema"]=SCHEMA; out["version"]=VERSION
    out["legacy_v09_classification"]=base["classification"]
    out["classification"]="RUN_DEPENDENCE_INVALIDATES_CROSSFIT" if invalid else base["classification"]
    out["metrics"]=dict(base["metrics"])
    out["metrics"]["background_run_dependence"]=dep
    out["metrics"]["background_dependence_candidate_bin_removed"]=k
    out["policy"]=dict(base["policy"])
    out["policy"].update({
        "run_independence_required_for_crossfit":True,
        "crossfit_valid_under_background_dependence_audit":not invalid,
        "candidate_band_removed_before_background_dependence_test":True,
        "max_median_zero_lag_background_corr":float(max_median_zero_lag_background_corr),
        "max_median_circular_background_corr":float(max_median_circular_background_corr),
        "shared_or_shifted_background_realization_is_not_independent_replication":True,
    })
    out["promotion_gates"]=[
        "background run-independence / shared-realization audit",
        *base["promotion_gates"],
    ]
    out.pop("analysis_sha256",None)
    out["analysis_sha256"]=hashlib.sha256(
        json.dumps(out,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()
    return out

__all__=["SCHEMA","VERSION","analyze_residual_stack_v10"]
