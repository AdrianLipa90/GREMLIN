from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v08 import analyze_residual_stack_v08
from .residual_spectroscopy_v07 import _local_prominence_curve, _spectrum

SCHEMA="GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_9"
VERSION="0.9.0"


def _rank_at(curve:np.ndarray,k:int)->float:
    if k<0 or k>=len(curve) or not np.isfinite(curve[k]):
        return 1.0
    finite=curve[np.isfinite(curve)]
    return float((1+np.sum(finite>=curve[k]))/(1+len(finite)))


def _crosshalf_run_audit(row:np.ndarray,alpha:float)->dict[str,Any]:
    n=len(row)
    h=n//2
    left=row[:h]
    right=row[-h:]
    c_left=_local_prominence_curve(_spectrum(left))
    c_right=_local_prominence_curve(_spectrum(right))
    valid=np.where(np.isfinite(c_left)&np.isfinite(c_right))[0]
    if valid.size==0:
        return {"reproducible":False,"k_left":0,"k_right":0,"p_left":1.0,"p_right":1.0}

    k_left=int(valid[np.argmax(c_left[valid])])
    k_right=int(valid[np.argmax(c_right[valid])])
    p_right=_rank_at(c_right,k_left)
    p_left=_rank_at(c_left,k_right)
    reproducible=bool(
        abs(k_left-k_right)<=2
        and p_left<=alpha
        and p_right<=alpha
    )
    return {
        "reproducible":reproducible,
        "k_left":k_left,
        "k_right":k_right,
        "p_left":p_left,
        "p_right":p_right,
        "full_run_bin_estimate":float(k_left+k_right),
    }


def _transient_cohort_gate(
    residual:np.ndarray,
    *,
    ordered_runs:bool,
    alpha_per_half:float,
    frequency_tolerance_halfbins:float=3.0,
)->dict[str,Any]:
    audits=[_crosshalf_run_audit(row,alpha_per_half) for row in residual]
    good=[i for i,a in enumerate(audits) if a["reproducible"]]

    clusters=[]
    if ordered_runs and good:
        current=[good[0]]
        for i in good[1:]:
            prev=current[-1]
            k_prev=0.5*(audits[prev]["k_left"]+audits[prev]["k_right"])
            k_now=0.5*(audits[i]["k_left"]+audits[i]["k_right"])
            if i==prev+1 and abs(k_now-k_prev)<=frequency_tolerance_halfbins:
                current.append(i)
            else:
                clusters.append(current)
                current=[i]
        clusters.append(current)

    largest=max(clusters,key=len) if clusters else []
    return {
        "ordered_runs":bool(ordered_runs),
        "alpha_per_half":float(alpha_per_half),
        "per_run":audits,
        "reproducible_run_indices":good,
        "clusters":clusters,
        "largest_cluster":largest,
        "largest_cluster_length":len(largest),
        "cohort_pass":bool(ordered_runs and len(largest)>=2),
        "single_run_anomalies_are_diagnostic_only":True,
        "frequency_rank_is_diagnostic_not_fully_calibrated_p_value":True,
    }


def analyze_residual_stack_v09(
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
    transient_half_alpha:float=0.01,
)->dict[str,Any]:
    if not (0.0<transient_half_alpha<1.0):
        raise ValueError("transient_half_alpha must be in (0,1)")

    raw=np.asarray(raw_runs,float)
    model=np.asarray(model_runs,float)
    base=analyze_residual_stack_v08(
        raw,
        model,
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
    )
    residual=raw-model
    transient=_transient_cohort_gate(
        residual,
        ordered_runs=ordered_runs,
        alpha_per_half=transient_half_alpha,
    )

    classification=base["classification"]
    eligible=classification in {
        "STOCHASTIC_WHITE_BACKGROUND_COMPATIBLE",
        "STOCHASTIC_COLORED_BACKGROUND_COMPATIBLE",
        "UNRESOLVED_RESIDUAL",
    }
    if eligible and transient["cohort_pass"]:
        classification="UNRESOLVED_TRANSIENT_COHORT_STRUCTURE_CANDIDATE"

    out=dict(base)
    out["schema"]=SCHEMA
    out["version"]=VERSION
    out["classification"]=classification
    out["legacy_v08_classification"]=base["classification"]
    out["metrics"]=dict(base["metrics"])
    out["metrics"]["transient_cohort_gate"]=transient
    out["policy"]=dict(base["policy"])
    out["policy"].update({
        "transient_structure_not_required_to_be_global_persistent":True,
        "single_run_anomaly_not_promoted_to_cohort":True,
        "ordered_run_provenance_required_for_cohort":True,
        "transient_cohort_candidate_is_not_physical_attribution":True,
    })
    out["promotion_gates"]=list(base["promotion_gates"])+[
        "transient cohort requires independent instrument/environment controls",
        "single-run spectral anomalies remain diagnostics until separately calibrated",
        "transient half-rank thresholds require background-class calibration",
    ]
    out.pop("analysis_sha256",None)
    out["analysis_sha256"]=hashlib.sha256(
        json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return out


__all__=["SCHEMA","VERSION","analyze_residual_stack_v09"]
