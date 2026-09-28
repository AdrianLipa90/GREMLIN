from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v09 import analyze_residual_stack_v09

SCHEMA="GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_10"
VERSION="0.10.2"


def _sha_array(x:np.ndarray)->str:
    a=np.ascontiguousarray(np.asarray(x,dtype=np.float64))
    h=hashlib.sha256(); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def _detrend(x:np.ndarray)->np.ndarray:
    x=np.asarray(x,float); t=np.arange(x.size,dtype=float)
    y=x-np.polyval(np.polyfit(t,x,1),t)
    return y-y.mean()


def _notch(runs:np.ndarray,k:int,w:int=3)->np.ndarray:
    out=[]
    for row in runs:
        y=_detrend(row); f=np.fft.rfft(y)
        f[max(1,k-w):min(len(f),k+w+1)]=0.0
        out.append(np.fft.irfft(f,n=len(y)))
    return np.asarray(out)


def _safe_corr(a:np.ndarray,b:np.ndarray)->float:
    aa=a-a.mean(); bb=b-b.mean()
    d=float(np.linalg.norm(aa)*np.linalg.norm(bb))
    return 0.0 if d==0.0 else float(np.dot(aa,bb)/d)


def _dependence_stat(runs:np.ndarray)->tuple[float,float]:
    x=np.asarray(runs,float)
    x=x-x.mean(axis=1,keepdims=True)
    norms=np.linalg.norm(x,axis=1)
    den=norms[:,None]*norms[None,:]
    corr=np.divide(x@x.T,den,out=np.zeros_like(den),where=den>0)
    iu=np.triu_indices(len(x),1)
    zero=float(np.median(np.abs(corr[iu])))

    F=np.fft.rfft(x,axis=1)
    cross=F[:,None,:]*np.conj(F[None,:,:])
    cc=np.fft.irfft(cross,n=x.shape[1],axis=-1)
    mx=np.max(np.abs(cc),axis=-1)
    mc=np.divide(mx,den,out=np.zeros_like(mx),where=den>0)
    circular=float(np.median(mc[iu]))
    return zero,circular


def _median_abs_lag1(runs:np.ndarray)->float:
    vals=[]
    for row in runs:
        y=np.asarray(row,float)
        vals.append(abs(_safe_corr(y[:-1],y[1:])))
    return float(np.median(vals))


def _iaaft_row(
    x:np.ndarray,
    rng:np.random.Generator,
    iterations:int,
)->tuple[np.ndarray,float]:
    x=np.asarray(x,float)
    sorted_x=np.sort(x)
    target_mag=np.abs(np.fft.rfft(x))
    y=rng.permutation(x)

    for _ in range(iterations):
        Y=np.fft.rfft(y)
        phase=np.exp(1j*np.angle(Y))
        z=np.fft.irfft(target_mag*phase,n=len(x))
        order=np.argsort(z)
        y_new=np.empty_like(y)
        y_new[order]=sorted_x
        if np.array_equal(y_new,y):
            y=y_new
            break
        y=y_new

    mag=np.abs(np.fft.rfft(y))
    den=max(float(np.linalg.norm(target_mag)),1e-15)
    rel=float(np.linalg.norm(mag-target_mag)/den)
    return y,rel


def _iaaft_rows(
    runs:np.ndarray,
    rng:np.random.Generator,
    iterations:int,
)->tuple[np.ndarray,float]:
    rows=[]; errors=[]
    for row in runs:
        y,e=_iaaft_row(row,rng,iterations)
        rows.append(y); errors.append(e)
    return np.asarray(rows),float(np.median(errors))


def _run_dependence_surrogate_audit(
    residual:np.ndarray,
    candidate_bin:int,
    *,
    null_count:int,
    iaaft_iterations:int,
)->dict[str,Any]:
    background=_notch(residual,candidate_bin)
    observed_zero,observed_circular=_dependence_stat(background)

    seed=int(_sha_array(background)[:16],16)
    rng=np.random.default_rng(seed)
    null=np.empty((null_count,2),dtype=float)
    quality=np.empty(null_count,dtype=float)

    for i in range(null_count):
        surrogate,quality[i]=_iaaft_rows(background,rng,iaaft_iterations)
        null[i]=_dependence_stat(surrogate)

    med_zero=float(np.median(null[:,0]))
    med_circular=float(np.median(null[:,1]))
    scale_zero=max(med_zero,1e-15)
    scale_circular=max(med_circular,1e-15)
    null_score=np.maximum(
        null[:,0]/scale_zero,
        null[:,1]/scale_circular,
    )
    observed_score=max(
        observed_zero/scale_zero,
        observed_circular/scale_circular,
    )
    p=float((1+np.sum(null_score>=observed_score))/(null_count+1))

    return {
        "candidate_bin_removed":int(candidate_bin),
        "observed_median_abs_zero_lag_correlation":observed_zero,
        "observed_median_max_circular_correlation":observed_circular,
        "null_median_zero_lag_correlation":med_zero,
        "null_median_max_circular_correlation":med_circular,
        "combined_relative_dependence_score":float(observed_score),
        "monte_carlo_p":p,
        "null_count":int(null_count),
        "iaaft_iterations":int(iaaft_iterations),
        "median_surrogate_psd_relative_error":float(np.median(quality)),
        "q90_surrogate_psd_relative_error":float(np.quantile(quality,.90)),
        "null_kind":"IAAFT_PRESERVING_EMPIRICAL_AMPLITUDE_DISTRIBUTION_AND_APPROX_POWER_SPECTRUM",
    }


def analyze_residual_stack_v10(
    raw_runs:Sequence[Sequence[float]],
    model_runs:Sequence[Sequence[float]],
    *,
    nuisance_runs=None,
    known_template_runs=None,
    channel_runs=None,
    sample_spacing:float=1.0,
    ordered_runs:bool=False,
    trend_ambiguity_cycles:float=3.0,
    accumulation_alpha:float=0.01,
    path_alpha:float=0.01,
    path_slope_max:float=1.5,
    path_slope_step:float=0.25,
    transient_half_alpha:float=0.01,
    run_dependence_alpha:float=0.01,
    run_dependence_null_count:int=127,
    iaaft_iterations:int=20,
    max_median_surrogate_psd_relative_error:float=0.15,
    long_memory_lag1_abstain:float=0.97,
)->dict[str,Any]:
    if not (0.0<run_dependence_alpha<1.0):
        raise ValueError("run_dependence_alpha must be in (0,1)")
    if run_dependence_null_count<99:
        raise ValueError("run_dependence_null_count must be >=99")
    if iaaft_iterations<5:
        raise ValueError("iaaft_iterations must be >=5")
    if not (0.0<long_memory_lag1_abstain<1.0):
        raise ValueError("long_memory_lag1_abstain must be in (0,1)")
    if max_median_surrogate_psd_relative_error<=0.0:
        raise ValueError("surrogate PSD error threshold must be positive")

    raw=np.asarray(raw_runs,float); model=np.asarray(model_runs,float)
    base=analyze_residual_stack_v09(
        raw,model,
        nuisance_runs=nuisance_runs,
        known_template_runs=known_template_runs,
        channel_runs=channel_runs,
        sample_spacing=sample_spacing,
        ordered_runs=ordered_runs,
        trend_ambiguity_cycles=trend_ambiguity_cycles,
        accumulation_alpha=accumulation_alpha,
        path_alpha=path_alpha,
        path_slope_max=path_slope_max,
        path_slope_step=path_slope_step,
        transient_half_alpha=transient_half_alpha,
    )

    residual=raw-model
    k=int(round(float(base["metrics"]["crossfit_narrowband_gate"]["median_discovery_bin"])))
    background=_notch(residual,k)
    lag1=_median_abs_lag1(background)
    audit=_run_dependence_surrogate_audit(
        residual,
        k,
        null_count=run_dependence_null_count,
        iaaft_iterations=iaaft_iterations,
    )
    audit["median_abs_background_lag1"]=lag1
    audit["alpha"]=float(run_dependence_alpha)
    audit["long_memory_lag1_abstain"]=float(long_memory_lag1_abstain)
    audit["max_median_surrogate_psd_relative_error"]=float(
        max_median_surrogate_psd_relative_error
    )

    if lag1>=long_memory_lag1_abstain:
        cls="RUN_DEPENDENCE_AUDIT_LONG_MEMORY_UNCALIBRATED"
        crossfit_valid=False
    elif audit["median_surrogate_psd_relative_error"]>max_median_surrogate_psd_relative_error:
        cls="RUN_DEPENDENCE_SURROGATE_QUALITY_UNCALIBRATED"
        crossfit_valid=False
    elif audit["monte_carlo_p"]<=run_dependence_alpha:
        cls="RUN_DEPENDENCE_INVALIDATES_CROSSFIT"
        crossfit_valid=False
    else:
        cls=base["classification"]
        crossfit_valid=True

    out=dict(base)
    out["schema"]=SCHEMA; out["version"]=VERSION
    out["legacy_v09_classification"]=base["classification"]
    out["classification"]=cls
    out["metrics"]=dict(base["metrics"])
    out["metrics"]["background_run_dependence_surrogate_audit"]=audit
    out["policy"]=dict(base["policy"])
    out["policy"].update({
        "run_independence_required_for_crossfit":True,
        "crossfit_valid_under_run_dependence_audit":crossfit_valid,
        "shared_or_shifted_background_realization_is_not_independent_replication":True,
        "run_dependence_null_preserves_empirical_amplitude_distribution":True,
        "run_dependence_null_approximately_preserves_each_run_power_spectrum":True,
        "absolute_correlation_threshold_is_authoritative":False,
        "extreme_long_memory_causes_abstention":True,
        "poor_surrogate_spectral_fidelity_causes_abstention":True,
    })
    out["promotion_gates"]=[
        "IAAFT run-dependence surrogate audit",
        "surrogate spectral-fidelity gate",
        "long-memory abstention before cross-fit interpretation",
        *base["promotion_gates"],
    ]
    out.pop("analysis_sha256",None)
    out["analysis_sha256"]=hashlib.sha256(
        json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return out


__all__=["SCHEMA","VERSION","analyze_residual_stack_v10"]
