from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v05 import analyze_residual_stack_v05

SCHEMA="GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_6"
VERSION="0.6.0"


def _poly_r2(x: np.ndarray, degree: int=3) -> float:
    x=np.asarray(x,float)
    t=np.linspace(-1.0,1.0,x.size,dtype=float)
    coef=np.polyfit(t,x,degree)
    pred=np.polyval(coef,t)
    xc=x-x.mean()
    pc=pred-pred.mean()
    den=float(np.dot(xc,xc))
    return 0.0 if den==0.0 else float(max(0.0,min(1.0,np.dot(pc,pc)/den)))


def analyze_residual_stack_v06(
    raw_runs:Sequence[Sequence[float]],
    model_runs:Sequence[Sequence[float]],
    *,
    nuisance_runs:Sequence[Sequence[float]]|None=None,
    known_template_runs:Sequence[Sequence[float]]|None=None,
    channel_runs:Mapping[str,Sequence[Sequence[float]]]|None=None,
    sample_spacing:float=1.0,
    ordered_runs:bool=False,
    trend_ambiguity_cycles:float=3.0,
)->dict[str,Any]:
    if not np.isfinite(trend_ambiguity_cycles) or trend_ambiguity_cycles<=0.0:
        raise ValueError("trend_ambiguity_cycles must be positive finite")

    raw=np.asarray(raw_runs,float)
    model=np.asarray(model_runs,float)
    base=analyze_residual_stack_v05(
        raw,
        model,
        nuisance_runs=nuisance_runs,
        known_template_runs=known_template_runs,
        channel_runs=channel_runs,
        sample_spacing=sample_spacing,
        ordered_runs=ordered_runs,
    )
    residual=raw-model

    gate=base["metrics"]["crossfit_narrowband_gate"]
    median_bin=float(gate["median_discovery_bin"])
    poly_r2=np.asarray([_poly_r2(row,3) for row in residual],float)
    median_poly_r2=float(np.median(poly_r2))

    legacy=base["classification"]
    narrowband=legacy in {
        "UNRESOLVED_NARROWBAND_PHASE_ORDERED_CANDIDATE",
        "UNRESOLVED_NARROWBAND_PHASE_UNORDERED_CANDIDATE",
        "UNRESOLVED_NARROWBAND_PHASE_UNTYPED_CANDIDATE",
    }

    low_frequency_ambiguous=bool(
        narrowband and median_bin < float(trend_ambiguity_cycles)
    )

    if low_frequency_ambiguous:
        classification="LOW_FREQUENCY_TREND_OR_NARROWBAND_AMBIGUOUS_CANDIDATE"
    else:
        classification=legacy

    out=dict(base)
    out["schema"]=SCHEMA
    out["version"]=VERSION
    out["classification"]=classification
    out["legacy_v05_classification"]=legacy
    out["metrics"]=dict(base["metrics"])
    out["metrics"]["trend_ambiguity_audit"]={
        "median_discovery_bin":median_bin,
        "cycles_across_run_at_selected_bin":median_bin,
        "trend_ambiguity_cycles":float(trend_ambiguity_cycles),
        "low_frequency_ambiguous":low_frequency_ambiguous,
        "median_cubic_polynomial_r2":median_poly_r2,
        "per_run_cubic_polynomial_r2":[float(v) for v in poly_r2],
        "runs":int(raw.shape[0]),
        "samples_per_run":int(raw.shape[1]),
    }
    out["policy"]=dict(base["policy"])
    out["policy"].update({
        "low_frequency_trend_and_narrowband_not_forced_apart":True,
        "finite_window_subcycle_structure_preserved_as_ambiguous":True,
        "sensitivity_threshold_not_universal_across_sample_count_or_background":True,
        "ambiguity_is_not_noise":True,
    })
    out["promotion_gates"]=list(base["promotion_gates"])+[
        "low-frequency narrowband/trend ambiguity must be resolved by longer baseline or independent trend control",
        "detection-power calibration must be indexed by run count, samples per run, background class and frequency location",
    ]
    out.pop("analysis_sha256",None)
    out["analysis_sha256"]=hashlib.sha256(
        json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return out


__all__=["SCHEMA","VERSION","analyze_residual_stack_v06"]
