from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v06 import analyze_residual_stack_v06

SCHEMA="GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_7"
VERSION="0.7.0"


def _spectrum(x:np.ndarray)->np.ndarray:
    x=np.asarray(x,float)
    t=np.arange(x.size,dtype=float)
    coef=np.polyfit(t,x,1)
    y=x-np.polyval(coef,t)
    y-=y.mean()
    p=np.abs(np.fft.rfft(y))**2
    if p.size>1:
        p[0]=0.0
    total=float(p.sum())
    return np.zeros_like(p) if total==0.0 else p/total


def _trimmed_stack(runs:np.ndarray, trim_fraction:float=0.10)->np.ndarray:
    psd=np.stack([_spectrum(row) for row in runs])
    ordered=np.sort(psd,axis=0)
    cut=int(np.floor(trim_fraction*psd.shape[0]))
    if cut>0 and 2*cut<psd.shape[0]:
        ordered=ordered[cut:-cut]
    return np.mean(ordered,axis=0)


def _local_prominence_curve(
    stacked:np.ndarray,
    *,
    band_halfwidth:int=2,
    local_radius:int=16,
)->np.ndarray:
    s=np.asarray(stacked,float)
    out=np.full(s.shape,np.nan,dtype=float)
    for k in range(max(1,local_radius),len(s)-local_radius):
        band=list(range(k-band_halfwidth,k+band_halfwidth+1))
        local=[
            j for j in range(k-local_radius,k+local_radius+1)
            if j not in band
        ]
        baseline=float(np.median(s[local]))
        if baseline>0.0:
            out[k]=float(np.mean(s[band])/baseline)
    return out


def _rank_validate(runs:np.ndarray,k:int)->dict[str,float]:
    curve=_local_prominence_curve(_trimmed_stack(runs))
    kk=int(k)
    if kk<0 or kk>=len(curve) or not np.isfinite(curve[kk]):
        return {"p":1.0,"prominence":0.0,"valid_centers":0}
    finite=curve[np.isfinite(curve)]
    obs=float(curve[kk])
    p=float((1+np.sum(finite>=obs))/(1+len(finite)))
    return {"p":p,"prominence":obs,"valid_centers":int(len(finite))}


def _fold_pairs(n_runs:int)->list[tuple[np.ndarray,np.ndarray]]:
    ids=np.arange(n_runs)
    out=[]
    for mask in (ids%2==0,ids<n_runs//2):
        a=ids[mask]
        b=ids[~mask]
        if a.size>=4 and b.size>=4:
            out.extend([(a,b),(b,a)])
    return out


def _replicate_accumulation_gate(
    residual:np.ndarray,
    *,
    alpha:float,
    trend_ambiguity_cycles:float,
)->dict[str,Any]:
    directions=[]
    for train,holdout in _fold_pairs(residual.shape[0]):
        discover_curve=_local_prominence_curve(_trimmed_stack(residual[train]))
        valid=np.where(np.isfinite(discover_curve))[0]
        if valid.size==0:
            continue
        k=int(valid[np.argmax(discover_curve[valid])])

        raw_check=_rank_validate(residual[holdout],k)

        diff=np.diff(residual[holdout],axis=1)
        kd=int(round(k*(residual.shape[1]-1)/residual.shape[1]))
        diff_check=_rank_validate(diff,kd)

        passed=bool(
            k>=trend_ambiguity_cycles
            and raw_check["p"]<=alpha
            and diff_check["p"]<=alpha
        )
        directions.append({
            "discovery_peak_bin":k,
            "raw_validation":raw_check,
            "difference_validation":diff_check,
            "pass":passed,
        })

    bins=[d["discovery_peak_bin"] for d in directions]
    median_bin=float(np.median(bins)) if bins else 0.0
    agreement=float(np.mean([abs(k-median_bin)<=2 for k in bins])) if bins else 0.0
    pass_fraction=float(np.mean([d["pass"] for d in directions])) if directions else 0.0
    passed=bool(pass_fraction>=0.75 and agreement>=0.75)

    return {
        "alpha_per_direction":float(alpha),
        "directions":directions,
        "pass_fraction":pass_fraction,
        "bin_agreement_fraction":agreement,
        "median_discovery_bin":median_bin,
        "pass":passed,
        "stack":"10_PERCENT_TRIMMED_MEAN_PSD",
        "holdout_statistic":"LOCAL_PROMINENCE_FREQUENCY_RANK",
        "individual_run_effect_size_threshold_required":False,
    }


def analyze_residual_stack_v07(
    raw_runs:Sequence[Sequence[float]],
    model_runs:Sequence[Sequence[float]],
    *,
    nuisance_runs:Sequence[Sequence[float]]|None=None,
    known_template_runs:Sequence[Sequence[float]]|None=None,
    channel_runs:Mapping[str,Sequence[Sequence[float]]]|None=None,
    sample_spacing:float=1.0,
    ordered_runs:bool=False,
    trend_ambiguity_cycles:float=3.0,
    accumulation_alpha:float=0.01,
)->dict[str,Any]:
    if not (0.0<accumulation_alpha<1.0):
        raise ValueError("accumulation_alpha must be in (0,1)")

    raw=np.asarray(raw_runs,float)
    model=np.asarray(model_runs,float)
    base=analyze_residual_stack_v06(
        raw,
        model,
        nuisance_runs=nuisance_runs,
        known_template_runs=known_template_runs,
        channel_runs=channel_runs,
        sample_spacing=sample_spacing,
        ordered_runs=ordered_runs,
        trend_ambiguity_cycles=trend_ambiguity_cycles,
    )
    residual=raw-model

    accumulation=_replicate_accumulation_gate(
        residual,
        alpha=accumulation_alpha,
        trend_ambiguity_cycles=trend_ambiguity_cycles,
    )

    classification=base["classification"]
    eligible=classification in {
        "STOCHASTIC_WHITE_BACKGROUND_COMPATIBLE",
        "STOCHASTIC_COLORED_BACKGROUND_COMPATIBLE",
        "UNRESOLVED_RESIDUAL",
    }
    if eligible and accumulation["pass"]:
        classification="UNRESOLVED_WEAK_NARROWBAND_ACCUMULATION_CANDIDATE"

    out=dict(base)
    out["schema"]=SCHEMA
    out["version"]=VERSION
    out["classification"]=classification
    out["legacy_v06_classification"]=base["classification"]
    out["metrics"]=dict(base["metrics"])
    out["metrics"]["replicate_accumulation_gate"]=accumulation
    out["policy"]=dict(base["policy"])
    out["policy"].update({
        "weak_persistent_structure_may_accumulate_across_runs":True,
        "fixed_effect_size_floor_not_required_for_accumulation_class":True,
        "frequency_discovered_on_training_runs_validated_on_holdout_runs":True,
        "local_frequency_rank_is_diagnostic_not_fully_calibrated_p_value":True,
        "accumulation_candidate_is_not_physical_attribution":True,
    })
    out["promotion_gates"]=list(base["promotion_gates"])+[
        "replicate-accumulation rank gate requires external Monte Carlo calibration by background class",
        "weak accumulation candidate requires independent dataset replication before interpretation",
    ]
    out.pop("analysis_sha256",None)
    out["analysis_sha256"]=hashlib.sha256(
        json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return out


__all__=["SCHEMA","VERSION","analyze_residual_stack_v07"]
