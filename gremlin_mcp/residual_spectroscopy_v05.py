from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v04 import analyze_residual_stack_v04

SCHEMA = "GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_5"
VERSION = "0.5.0"


def _sha_array(x: np.ndarray) -> str:
    a = np.ascontiguousarray(np.asarray(x, dtype=np.float64))
    h = hashlib.sha256()
    h.update(str(a.shape).encode())
    h.update(a.tobytes())
    return h.hexdigest()


def _spectrum(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, float)
    t = np.arange(x.size, dtype=float)
    coef = np.polyfit(t, x, 1)
    y = x - np.polyval(coef, t)
    y -= y.mean()
    p = np.abs(np.fft.rfft(y)) ** 2
    if p.size > 1:
        p[0] = 0.0
    total = float(p.sum())
    return np.zeros_like(p) if total == 0.0 else p / total


def _stacked_psd(runs: np.ndarray) -> np.ndarray:
    return np.median(np.stack([_spectrum(x) for x in runs]), axis=0)


def _fold_pairs(n_runs: int) -> list[tuple[np.ndarray, np.ndarray]]:
    ids = np.arange(n_runs)
    out: list[tuple[np.ndarray, np.ndarray]] = []
    for mask in (ids % 2 == 0, ids < n_runs // 2):
        a = ids[mask]
        b = ids[~mask]
        if a.size >= 2 and b.size >= 2:
            out.extend([(a, b), (b, a)])
    return out


def _smooth_continuum_excess(
    runs: np.ndarray,
    k: int,
    *,
    fit_hi: int = 64,
    halfwidth: int = 1,
    support_threshold: float = 4.0,
) -> dict[str, float]:
    psd = np.stack([_spectrum(x) for x in runs])
    stacked = np.median(psd, axis=0)
    nfreq = stacked.size
    kk = min(max(1, int(k)), nfreq - 1)

    band = np.arange(max(1, kk - halfwidth), min(nfreq, kk + halfwidth + 1))
    excluded = set(int(x) for x in band)
    fit_idx = np.asarray([
        j for j in range(1, min(nfreq, fit_hi + 1))
        if j not in excluded
    ], dtype=int)
    if fit_idx.size < 8:
        return {"prominence": 0.0, "support_fraction": 0.0}

    design = np.c_[
        np.ones(fit_idx.size, dtype=float),
        np.log(fit_idx.astype(float)),
    ]

    y = np.log(np.maximum(stacked[fit_idx], 1e-300))
    coef = np.linalg.lstsq(design, y, rcond=None)[0]
    pred = np.exp(coef[0] + coef[1] * np.log(band.astype(float)))
    prominence = float(np.mean(stacked[band] / pred))

    supports = []
    for row in psd:
        y = np.log(np.maximum(row[fit_idx], 1e-300))
        coef = np.linalg.lstsq(design, y, rcond=None)[0]
        pred = np.exp(coef[0] + coef[1] * np.log(band.astype(float)))
        score = float(np.mean(row[band] / pred))
        supports.append(score >= support_threshold)

    return {
        "prominence": prominence,
        "support_fraction": float(np.mean(supports)),
    }


def _crossfit_low_frequency_gate(
    residual: np.ndarray,
    *,
    low_frequency_max_bin: int = 8,
    prominence_threshold: float = 4.0,
    support_threshold: float = 0.50,
) -> dict[str, Any]:
    directions = []
    for train, holdout in _fold_pairs(residual.shape[0]):
        discover = _stacked_psd(residual[train])
        k = int(np.argmax(discover[1:]) + 1)

        check = _smooth_continuum_excess(
            residual[holdout],
            k,
            fit_hi=max(64, low_frequency_max_bin * 8),
            halfwidth=1,
            support_threshold=prominence_threshold,
        )
        passed = (
            k <= low_frequency_max_bin
            and check["prominence"] >= prominence_threshold
            and check["support_fraction"] >= support_threshold
        )
        directions.append({
            "discovery_peak_bin": k,
            "smooth_continuum_validation": check,
            "pass": bool(passed),
        })

    bins = [d["discovery_peak_bin"] for d in directions]
    median_bin = float(np.median(bins)) if bins else 0.0
    agreement = (
        float(np.mean([abs(k - median_bin) <= 2 for k in bins]))
        if bins else 0.0
    )
    pass_fraction = (
        float(np.mean([d["pass"] for d in directions]))
        if directions else 0.0
    )
    return {
        "directions": directions,
        "pass_fraction": pass_fraction,
        "bin_agreement_fraction": agreement,
        "median_discovery_bin": median_bin,
        "low_frequency_max_bin": int(low_frequency_max_bin),
        "pass": bool(pass_fraction >= 0.75 and agreement >= 0.75),
    }


def analyze_residual_stack_v05(
    raw_runs: Sequence[Sequence[float]],
    model_runs: Sequence[Sequence[float]],
    *,
    nuisance_runs: Sequence[Sequence[float]] | None = None,
    known_template_runs: Sequence[Sequence[float]] | None = None,
    channel_runs: Mapping[str, Sequence[Sequence[float]]] | None = None,
    sample_spacing: float = 1.0,
    low_frequency_max_bin: int = 8,
) -> dict[str, Any]:
    raw = np.asarray(raw_runs, float)
    model = np.asarray(model_runs, float)
    if raw.shape != model.shape or raw.ndim != 2 or raw.shape[0] < 8 or raw.shape[1] < 64:
        raise ValueError("v0.5 requires equal-shape [runs,samples] with >=8 runs and >=64 samples")
    if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(model)):
        raise ValueError("raw/model must be finite")
    if not math.isfinite(sample_spacing) or sample_spacing <= 0.0:
        raise ValueError("sample_spacing must be positive finite")

    base = analyze_residual_stack_v04(
        raw,
        model,
        nuisance_runs=nuisance_runs,
        known_template_runs=known_template_runs,
        channel_runs=channel_runs,
        sample_spacing=sample_spacing,
    )
    residual = raw - model
    low_gate = _crossfit_low_frequency_gate(
        residual,
        low_frequency_max_bin=low_frequency_max_bin,
    )

    protected = {
        "KNOWN_MODEL_STRUCTURE_CANDIDATE",
        "SYSTEMATIC_OR_INSTRUMENTAL_CANDIDATE",
        "SYSTEMATIC_DRIFT_CANDIDATE",
        "PERSISTENT_SIGNED_OFFSET_CANDIDATE",
        "RUNWISE_OFFSET_VARIATION_CANDIDATE",
        "UNRESOLVED_NARROWBAND_STRUCTURE_CANDIDATE",
    }

    if base["classification"] in protected:
        classification = base["classification"]
    elif low_gate["pass"]:
        classification = "UNRESOLVED_LOW_FREQUENCY_SPECTRAL_FEATURE_CANDIDATE"
    else:
        classification = base["classification"]

    out = {
        "schema": SCHEMA,
        "version": VERSION,
        "classification": classification,
        "base_v04_classification": base["classification"],
        "shape": list(raw.shape),
        "sample_spacing": float(sample_spacing),
        "commitments": {
            "raw_sha256": _sha_array(raw),
            "model_sha256": _sha_array(model),
            "residual_sha256": _sha_array(residual),
        },
        "metrics": {
            **dict(base["metrics"]),
            "crossfit_low_frequency_feature_gate": low_gate,
        },
        "policy": {
            **dict(base["policy"]),
            "low_frequency_feature_not_forced_through_first_difference": True,
            "low_frequency_feature_is_not_automatically_a_line": True,
            "spectral_knee_or_bump_may_remain_structured_without_physical_assignment": True,
            "interpretation_last": True,
            "new_physics_from_residual_only": False,
            "time_fluctuation_claim_allowed": False,
        },
        "promotion_gates": list(base["promotion_gates"]) + [
            "low-frequency smooth-continuum excess cross-fit",
            "feature morphology before line/mechanism assignment",
        ],
    }
    out["analysis_sha256"] = hashlib.sha256(
        json.dumps(out, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    return out


__all__ = ["SCHEMA", "VERSION", "analyze_residual_stack_v05"]
