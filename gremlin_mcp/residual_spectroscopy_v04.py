from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v02 import (
    analyze_residual_stack as analyze_residual_stack_v02,
)

SCHEMA="GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_4"
VERSION="0.4.0"


def _sha_array(x: np.ndarray)->str:
    a=np.ascontiguousarray(np.asarray(x,dtype=np.float64))
    h=hashlib.sha256(); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def _safe_corr(a: np.ndarray,b: np.ndarray)->float:
    aa=np.asarray(a,float); bb=np.asarray(b,float)
    aa=aa-aa.mean(); bb=bb-bb.mean()
    den=float(np.linalg.norm(aa)*np.linalg.norm(bb))
    return 0.0 if den==0.0 else float(np.dot(aa,bb)/den)


def _spectrum(x: np.ndarray)->np.ndarray:
    x=np.asarray(x,float)
    t=np.arange(x.size,dtype=float)
    coef=np.polyfit(t,x,1)
    y=x-np.polyval(coef,t)
    y-=y.mean()
    fft=np.fft.rfft(y)
    p=np.abs(fft)**2
    if p.size>1: p[0]=0.0
    total=float(p.sum())
    return np.zeros_like(p) if total==0.0 else p/total


def _stacked_psd(runs: np.ndarray)->np.ndarray:
    return np.median(np.stack([_spectrum(x) for x in runs]),axis=0)


def _band_indices(length:int,k:int,halfwidth:int=2)->tuple[list[int],list[int]]:
    lo=max(1,k-halfwidth)
    hi=min(length,k+halfwidth+1)
    band=list(range(lo,hi))
    local=[
        j for j in range(max(1,k-16),min(length,k+17))
        if j not in band and abs(j-k)>halfwidth
    ]
    if len(local)<8:
        local=[j for j in range(1,min(length,34)) if j not in band and abs(j-k)>halfwidth]
    return band,local


def _band_validation(runs: np.ndarray,k:int,*,support_threshold:float=2.5)->dict[str,float]:
    psd=np.stack([_spectrum(x) for x in runs])
    stacked=np.median(psd,axis=0)
    kk=min(max(1,int(k)),len(stacked)-1)
    band,local=_band_indices(len(stacked),kk)
    if not local:
        return {"prominence":0.0,"support_fraction":0.0}
    baseline=float(np.median(stacked[local]))
    width=max(1,len(band))
    prominence=0.0 if baseline<=0.0 else float(np.sum(stacked[band])/(baseline*width))
    supports=[]
    for row in psd:
        b=float(np.sum(row[band]))
        floor=float(np.median(row[local]))
        score=0.0 if floor<=0.0 else b/(floor*width)
        supports.append(score>=support_threshold)
    return {
        "prominence":prominence,
        "support_fraction":float(np.mean(supports)),
    }


def _fold_pairs(n_runs:int)->list[tuple[np.ndarray,np.ndarray]]:
    ids=np.arange(n_runs)
    out=[]
    for mask in (ids%2==0,ids<n_runs//2):
        a=ids[mask]; b=ids[~mask]
        if a.size>=2 and b.size>=2:
            out.extend([(a,b),(b,a)])
    return out


def _crossfit_narrowband_gate(residual:np.ndarray)->dict[str,Any]:
    directions=[]
    for train,holdout in _fold_pairs(residual.shape[0]):
        discover=_stacked_psd(residual[train])
        k=int(np.argmax(discover))

        raw_check=_band_validation(residual[holdout],k)

        diff=np.diff(residual[holdout],axis=1)
        kd=int(round(k*(residual.shape[1]-1)/residual.shape[1]))
        diff_check=_band_validation(diff,kd)

        passed=(
            raw_check["prominence"]>=2.5
            and raw_check["support_fraction"]>=0.50
            and diff_check["prominence"]>=2.5
            and diff_check["support_fraction"]>=0.50
        )
        directions.append({
            "discovery_peak_bin":k,
            "raw_validation":raw_check,
            "difference_validation":diff_check,
            "pass":bool(passed),
        })

    bins=[d["discovery_peak_bin"] for d in directions]
    if bins:
        median_bin=float(np.median(bins))
        bin_agreement=float(np.mean([abs(k-median_bin)<=2 for k in bins]))
    else:
        median_bin=0.0; bin_agreement=0.0

    pass_fraction=float(np.mean([d["pass"] for d in directions])) if directions else 0.0
    return {
        "directions":directions,
        "pass_fraction":pass_fraction,
        "bin_agreement_fraction":bin_agreement,
        "median_discovery_bin":median_bin,
        "pass":bool(pass_fraction>=0.75 and bin_agreement>=0.75),
    }


def analyze_residual_stack_v04(
    raw_runs:Sequence[Sequence[float]],
    model_runs:Sequence[Sequence[float]],
    *,
    nuisance_runs:Sequence[Sequence[float]]|None=None,
    known_template_runs:Sequence[Sequence[float]]|None=None,
    channel_runs:Mapping[str,Sequence[Sequence[float]]]|None=None,
    sample_spacing:float=1.0,
)->dict[str,Any]:
    raw=np.asarray(raw_runs,float); model=np.asarray(model_runs,float)
    if raw.shape!=model.shape or raw.ndim!=2 or raw.shape[0]<8 or raw.shape[1]<64:
        raise ValueError("v0.4 requires equal-shape [runs,samples] with >=8 runs and >=64 samples")
    if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(model)):
        raise ValueError("raw/model must be finite")
    if not math.isfinite(sample_spacing) or sample_spacing<=0:
        raise ValueError("sample_spacing must be positive finite")

    residual=raw-model
    legacy=analyze_residual_stack_v02(
        raw,model,
        nuisance_runs=nuisance_runs,
        known_template_runs=known_template_runs,
        channel_runs=channel_runs,
        sample_spacing=sample_spacing,
    )

    means=np.mean(residual,axis=1)
    std=np.std(residual,axis=1,ddof=1)
    signed_z=np.divide(
        means,
        std/np.sqrt(residual.shape[1]),
        out=np.zeros_like(means),
        where=std>0,
    )
    strong=np.abs(signed_z)>=5.0
    if np.any(strong):
        pos_fraction=float(np.mean(signed_z[strong]>0))
        neg_fraction=float(np.mean(signed_z[strong]<0))
    else:
        pos_fraction=neg_fraction=0.0
    signed_offset_consistency=max(pos_fraction,neg_fraction)

    lag1=float(np.median([
        abs(_safe_corr((r-r.mean())[:-1],(r-r.mean())[1:]))
        for r in residual
    ]))

    nuisance_corr=float(legacy["metrics"]["median_abs_nuisance_correlation"])
    known_corr=float(legacy["metrics"]["median_abs_known_template_correlation"])
    drift_r2=float(legacy["metrics"]["median_drift_r2"])
    drift_slope=float(legacy["metrics"]["median_abs_normalized_drift_slope"])
    median_abs_z=float(np.median(np.abs(signed_z)))

    gate=_crossfit_narrowband_gate(residual)

    if known_corr>=0.75:
        classification="KNOWN_MODEL_STRUCTURE_CANDIDATE"
    elif nuisance_corr>=0.70:
        classification="SYSTEMATIC_OR_INSTRUMENTAL_CANDIDATE"
    elif drift_r2>=0.70 and drift_slope>=1.0:
        classification="SYSTEMATIC_DRIFT_CANDIDATE"
    elif median_abs_z>=5.0 and signed_offset_consistency>=0.80:
        classification="PERSISTENT_SIGNED_OFFSET_CANDIDATE"
    elif median_abs_z>=5.0:
        classification="RUNWISE_OFFSET_VARIATION_CANDIDATE"
    elif gate["pass"]:
        classification="UNRESOLVED_NARROWBAND_STRUCTURE_CANDIDATE"
    elif lag1>=0.30:
        classification="STOCHASTIC_COLORED_BACKGROUND_COMPATIBLE"
    elif (
        lag1<=0.20
        and float(legacy["metrics"]["stacked_peak_to_median_ratio"])<=6.0
        and median_abs_z<4.0
        and drift_r2<0.5
    ):
        classification="STOCHASTIC_WHITE_BACKGROUND_COMPATIBLE"
    else:
        classification="UNRESOLVED_RESIDUAL"

    channel_coherence=dict(legacy["metrics"].get("cross_channel_coherence") or {})

    out={
        "schema":SCHEMA,
        "version":VERSION,
        "classification":classification,
        "legacy_v02_classification":legacy["classification"],
        "shape":list(raw.shape),
        "sample_spacing":float(sample_spacing),
        "commitments":{
            "raw_sha256":_sha_array(raw),
            "model_sha256":_sha_array(model),
            "residual_sha256":_sha_array(residual),
        },
        "metrics":{
            "median_abs_lag1":lag1,
            "median_abs_signed_mean_z":median_abs_z,
            "strong_offset_run_fraction":float(np.mean(strong)),
            "positive_strong_offset_fraction":pos_fraction,
            "negative_strong_offset_fraction":neg_fraction,
            "signed_offset_consistency":signed_offset_consistency,
            "median_abs_nuisance_correlation":nuisance_corr,
            "median_abs_known_template_correlation":known_corr,
            "median_drift_r2":drift_r2,
            "median_abs_normalized_drift_slope":drift_slope,
            "cross_channel_coherence":channel_coherence,
            "crossfit_narrowband_gate":gate,
            "legacy_stacked_peak_to_median_ratio":float(
                legacy["metrics"]["stacked_peak_to_median_ratio"]
            ),
        },
        "policy":{
            "raw_preserved":True,
            "residual_preserved":True,
            "analysis_copy_allowed":True,
            "destructive_denoising":False,
            "frequency_selected_and_validated_on_same_runs":False,
            "first_difference_is_analysis_copy_only":True,
            "broad_colored_noise_not_auto_promoted_to_narrowband_structure":True,
            "interpretation_last":True,
            "new_physics_from_residual_only":False,
            "time_fluctuation_claim_allowed":False,
        },
        "promotion_gates":[
            "cross-fit frequency discovery/validation",
            "raw and first-difference transform persistence",
            "instrument/environment/clock controls",
            "sampling/jitter/alias controls",
            "known-physics template controls",
            "independent replication before physical interpretation",
        ],
    }
    out["analysis_sha256"]=hashlib.sha256(
        json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return out


__all__=["SCHEMA","VERSION","analyze_residual_stack_v04"]
