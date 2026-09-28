from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v07 import (
    analyze_residual_stack_v07,
    _local_prominence_curve,
    _spectrum,
)

SCHEMA="GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_8"
VERSION="0.8.0"


def _run_prominence(runs:np.ndarray)->np.ndarray:
    return np.stack([
        _local_prominence_curve(_spectrum(row))
        for row in runs
    ])


def _path_score_grid(
    prominence:np.ndarray,
    run_indices:np.ndarray,
    slopes:np.ndarray,
    mid_bins:np.ndarray,
)->np.ndarray:
    mid_run=(prominence.shape[0]-1)/2.0
    scores=np.full((len(slopes),len(mid_bins)),-np.inf,dtype=float)

    for si,slope in enumerate(slopes):
        rows=[]
        valid_all=np.ones(len(mid_bins),dtype=bool)
        for r in run_indices:
            idx=np.rint(mid_bins+slope*(float(r)-mid_run)).astype(int)
            valid=(idx>=0)&(idx<prominence.shape[1])
            vals=np.full(len(mid_bins),np.nan,dtype=float)
            vals[valid]=prominence[r,idx[valid]]
            valid_all &= valid & np.isfinite(vals) & (vals>0.0)
            rows.append(vals)

        arr=np.stack(rows)
        logp=np.where(arr>0.0,np.log(arr),np.nan)
        score=np.nanmedian(logp,axis=0)
        score[~valid_all]=-np.inf
        scores[si]=score

    return scores


def _fold_pairs(n_runs:int)->list[tuple[np.ndarray,np.ndarray]]:
    ids=np.arange(n_runs)
    out=[]
    for mask in (ids%2==0,ids<n_runs//2):
        a=ids[mask]
        b=ids[~mask]
        if a.size>=4 and b.size>=4:
            out.extend([(a,b),(b,a)])
    return out


def _spectral_path_gate(
    residual:np.ndarray,
    *,
    alpha:float,
    slope_max:float,
    slope_step:float,
    trend_ambiguity_cycles:float,
)->dict[str,Any]:
    slopes=np.arange(-slope_max,slope_max+0.5*slope_step,slope_step,dtype=float)
    raw_prom=_run_prominence(residual)
    diff=np.diff(residual,axis=1)
    diff_prom=_run_prominence(diff)

    low_edge=20
    high_edge=raw_prom.shape[1]-20
    mid_bins=np.arange(low_edge,high_edge,dtype=int)

    directions=[]
    for train,holdout in _fold_pairs(residual.shape[0]):
        train_scores=_path_score_grid(raw_prom,train,slopes,mid_bins)
        flat=int(np.argmax(train_scores))
        si,mi=np.unravel_index(flat,train_scores.shape)
        slope=float(slopes[si])
        mid_bin=int(mid_bins[mi])

        hold_scores=_path_score_grid(raw_prom,holdout,slopes,mid_bins)
        observed=float(hold_scores[si,mi])
        finite=hold_scores[np.isfinite(hold_scores)]
        raw_p=float((1+np.sum(finite>=observed))/(1+len(finite)))

        diff_mid_bins=np.arange(20,diff_prom.shape[1]-20,dtype=int)
        diff_mid=int(round(mid_bin*(residual.shape[1]-1)/residual.shape[1]))
        mi_d=int(np.argmin(np.abs(diff_mid_bins-diff_mid)))
        diff_scores=_path_score_grid(diff_prom,holdout,slopes,diff_mid_bins)
        observed_diff=float(diff_scores[si,mi_d])
        finite_diff=diff_scores[np.isfinite(diff_scores)]
        diff_p=float((1+np.sum(finite_diff>=observed_diff))/(1+len(finite_diff)))

        passed=bool(
            mid_bin>=trend_ambiguity_cycles
            and raw_p<=alpha
            and diff_p<=alpha
        )
        directions.append({
            "mid_bin":mid_bin,
            "slope_bins_per_run":slope,
            "raw_rank_p":raw_p,
            "difference_rank_p":diff_p,
            "raw_log_prominence_score":None if not np.isfinite(observed) else observed,
            "difference_log_prominence_score":None if not np.isfinite(observed_diff) else observed_diff,
            "pass":passed,
        })

    mids=np.asarray([d["mid_bin"] for d in directions],float)
    slopes_found=np.asarray([d["slope_bins_per_run"] for d in directions],float)
    median_mid=float(np.median(mids)) if len(mids) else 0.0
    median_slope=float(np.median(slopes_found)) if len(slopes_found) else 0.0
    parameter_agreement=float(np.mean(
        (np.abs(mids-median_mid)<=2.0)
        & (np.abs(slopes_found-median_slope)<=slope_step+1e-12)
    )) if len(mids) else 0.0
    pass_fraction=float(np.mean([d["pass"] for d in directions])) if directions else 0.0

    passed=bool(
        pass_fraction>=0.75
        and parameter_agreement>=0.75
        and abs(median_slope)>=0.5*slope_step
    )
    return {
        "pass":passed,
        "pass_fraction":pass_fraction,
        "parameter_agreement_fraction":parameter_agreement,
        "median_mid_bin":median_mid,
        "median_slope_bins_per_run":median_slope,
        "directions":directions,
        "alpha_per_direction":float(alpha),
        "slope_search_max_abs_bins_per_run":float(slope_max),
        "slope_search_step_bins_per_run":float(slope_step),
        "path_family":"LINEAR_FREQUENCY_VS_RUN_INDEX",
        "frequency_rank_is_diagnostic_not_fully_calibrated_p_value":True,
    }


def analyze_residual_stack_v08(
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
    path_alpha:float=0.01,
    path_slope_max:float=1.5,
    path_slope_step:float=0.25,
)->dict[str,Any]:
    if not (0.0<path_alpha<1.0):
        raise ValueError("path_alpha must be in (0,1)")
    if not np.isfinite(path_slope_max) or path_slope_max<=0.0:
        raise ValueError("path_slope_max must be positive finite")
    if not np.isfinite(path_slope_step) or path_slope_step<=0.0:
        raise ValueError("path_slope_step must be positive finite")

    raw=np.asarray(raw_runs,float)
    model=np.asarray(model_runs,float)
    base=analyze_residual_stack_v07(
        raw,
        model,
        nuisance_runs=nuisance_runs,
        known_template_runs=known_template_runs,
        channel_runs=channel_runs,
        sample_spacing=sample_spacing,
        ordered_runs=ordered_runs,
        trend_ambiguity_cycles=trend_ambiguity_cycles,
        accumulation_alpha=accumulation_alpha,
    )
    residual=raw-model

    path=_spectral_path_gate(
        residual,
        alpha=path_alpha,
        slope_max=path_slope_max,
        slope_step=path_slope_step,
        trend_ambiguity_cycles=trend_ambiguity_cycles,
    )

    classification=base["classification"]
    eligible=classification in {
        "STOCHASTIC_WHITE_BACKGROUND_COMPATIBLE",
        "STOCHASTIC_COLORED_BACKGROUND_COMPATIBLE",
        "UNRESOLVED_RESIDUAL",
    }
    if eligible and path["pass"]:
        classification="UNRESOLVED_FREQUENCY_WANDERING_STRUCTURE_CANDIDATE"

    out=dict(base)
    out["schema"]=SCHEMA
    out["version"]=VERSION
    out["classification"]=classification
    out["legacy_v07_classification"]=base["classification"]
    out["metrics"]=dict(base["metrics"])
    out["metrics"]["spectral_path_gate"]=path
    out["policy"]=dict(base["policy"])
    out["policy"].update({
        "fixed_frequency_required_for_structure":False,
        "frequency_wandering_may_be_preserved_as_structure":True,
        "spectral_path_candidate_is_not_physical_attribution":True,
        "linear_path_family_is_not_universal":True,
    })
    out["promotion_gates"]=list(base["promotion_gates"])+[
        "spectral-path bank must be preregistered before target inspection",
        "path-rank calibration must be validated by background class and acquisition geometry",
        "frequency-wandering candidate requires instrument/clock/registration controls before interpretation",
    ]
    out.pop("analysis_sha256",None)
    out["analysis_sha256"]=hashlib.sha256(
        json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return out


__all__=["SCHEMA","VERSION","analyze_residual_stack_v08"]
