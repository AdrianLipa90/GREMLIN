from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Sequence

import numpy as np

SCHEMA = "GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_1"
VERSION = "0.1.0"


def _sha_array(x: np.ndarray) -> str:
    a = np.ascontiguousarray(np.asarray(x, dtype=np.float64))
    h = hashlib.sha256()
    h.update(str(a.shape).encode())
    h.update(a.tobytes())
    return h.hexdigest()


def _safe_corr(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if a.shape != b.shape:
        raise ValueError("correlation inputs must have equal shape")
    aa = a - a.mean()
    bb = b - b.mean()
    den = float(np.linalg.norm(aa) * np.linalg.norm(bb))
    return 0.0 if den == 0.0 else float(np.dot(aa, bb) / den)


def _linear_drift_r2(x: np.ndarray) -> tuple[float, float]:
    x = np.asarray(x, float)
    t = np.arange(x.size, dtype=float)
    tc = t - t.mean()
    xc = x - x.mean()
    den = float(np.dot(tc, tc))
    slope = 0.0 if den == 0.0 else float(np.dot(tc, xc) / den)
    pred = slope * tc
    ss = float(np.dot(xc, xc))
    r2 = 0.0 if ss == 0.0 else max(0.0, min(1.0, float(np.dot(pred, pred) / ss)))
    scale = float(np.std(x))
    norm_slope = 0.0 if scale == 0.0 else slope * x.size / scale
    return norm_slope, r2


def _block_mean_scaling(x: np.ndarray) -> float:
    x = np.asarray(x, float)
    n = x.size
    ms: list[float] = []
    ys: list[float] = []
    m = 1
    while m <= n // 16:
        k = n // m
        if k < 8:
            break
        blocks = x[: k * m].reshape(k, m).mean(axis=1)
        s = float(np.std(blocks, ddof=1)) if k > 1 else 0.0
        if s > 0.0:
            ms.append(math.log(m))
            ys.append(math.log(s))
        m *= 2
    if len(ms) < 2:
        return float("nan")
    return float(np.polyfit(ms, ys, 1)[0])


def _run_features(x: np.ndarray) -> dict[str, Any]:
    x = np.asarray(x, float)
    if x.ndim != 1 or x.size < 64 or not np.all(np.isfinite(x)):
        raise ValueError("each residual run must be finite 1D with >=64 samples")
    xc = x - x.mean()
    lag1 = _safe_corr(xc[:-1], xc[1:])
    norm_slope, r2 = _linear_drift_r2(x)

    # Analysis copies may be detrended; source residual is never mutated.
    t = np.arange(x.size, dtype=float)
    coef = np.polyfit(t, x, 1)
    detr = x - np.polyval(coef, t)
    detr -= detr.mean()
    fft = np.fft.rfft(detr)
    power = np.abs(fft) ** 2
    if power.size > 1:
        power[0] = 0.0
    total = float(power.sum())
    peak_bin = int(np.argmax(power)) if total > 0.0 else 0
    peak_fraction = 0.0 if total == 0.0 else float(power[peak_bin] / total)
    phase = 0.0 if peak_bin == 0 else float(np.angle(fft[peak_bin]))
    return {
        "mean": float(x.mean()),
        "std": float(x.std(ddof=1)),
        "lag1": lag1,
        "drift_normalized_slope": norm_slope,
        "drift_r2": r2,
        "block_mean_log_slope": _block_mean_scaling(x),
        "peak_bin": peak_bin,
        "peak_fraction": peak_fraction,
        "peak_phase": phase,
        "fft": fft,
    }


def analyze_residual_stack(
    raw_runs: Sequence[Sequence[float]],
    model_runs: Sequence[Sequence[float]],
    *,
    nuisance_runs: Sequence[Sequence[float]] | None = None,
    known_template_runs: Sequence[Sequence[float]] | None = None,
    sample_spacing: float = 1.0,
) -> dict[str, Any]:
    raw = np.asarray(raw_runs, float)
    model = np.asarray(model_runs, float)
    if raw.shape != model.shape or raw.ndim != 2 or raw.shape[0] < 2 or raw.shape[1] < 64:
        raise ValueError("raw/model must be equal-shape 2D arrays with >=2 runs and >=64 samples")
    if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(model)):
        raise ValueError("raw/model must be finite")
    if not math.isfinite(sample_spacing) or sample_spacing <= 0.0:
        raise ValueError("sample_spacing must be positive finite")

    residual = raw - model
    feats = [_run_features(r) for r in residual]
    bins = np.array([f["peak_bin"] for f in feats], int)
    positive = bins[bins > 0]
    if positive.size:
        counts = np.bincount(positive)
        consensus = int(np.argmax(counts))
        persistence = float(np.mean(np.abs(bins - consensus) <= 1))
        phases = np.array([
            np.angle(f["fft"][consensus]) if consensus < len(f["fft"]) else 0.0
            for f in feats
        ])
        phase_coh = float(abs(np.mean(np.exp(1j * phases))))
        freq = consensus / (raw.shape[1] * sample_spacing)
    else:
        consensus = 0
        persistence = 0.0
        phase_coh = 0.0
        freq = 0.0

    peak_fraction = float(np.median([f["peak_fraction"] for f in feats]))
    lag1 = float(np.median([abs(f["lag1"]) for f in feats]))
    drift_r2 = float(np.median([f["drift_r2"] for f in feats]))
    drift_slope = float(np.median([abs(f["drift_normalized_slope"]) for f in feats]))
    scale_slopes = np.array([f["block_mean_log_slope"] for f in feats], float)
    finite_scale = scale_slopes[np.isfinite(scale_slopes)]
    scale_slope = float(np.median(finite_scale)) if finite_scale.size else None

    nuisance_corr = 0.0
    if nuisance_runs is not None:
        nuisance = np.asarray(nuisance_runs, float)
        if nuisance.shape != raw.shape:
            raise ValueError("nuisance_runs must match raw shape")
        nuisance_corr = float(np.median([
            abs(_safe_corr(residual[i], nuisance[i])) for i in range(raw.shape[0])
        ]))

    known_corr = 0.0
    if known_template_runs is not None:
        known = np.asarray(known_template_runs, float)
        if known.shape != raw.shape:
            raise ValueError("known_template_runs must match raw shape")
        known_corr = float(np.median([
            abs(_safe_corr(residual[i], known[i])) for i in range(raw.shape[0])
        ]))

    if known_corr >= 0.75:
        classification = "KNOWN_MODEL_STRUCTURE_CANDIDATE"
    elif nuisance_corr >= 0.70:
        classification = "SYSTEMATIC_OR_INSTRUMENTAL_CANDIDATE"
    elif drift_r2 >= 0.70 and drift_slope >= 1.0:
        classification = "SYSTEMATIC_DRIFT_CANDIDATE"
    elif persistence >= 0.75 and phase_coh >= 0.65 and peak_fraction >= 0.10:
        classification = "UNRESOLVED_STRUCTURED_CANDIDATE"
    elif lag1 <= 0.20 and peak_fraction <= 0.06 and persistence <= 0.50:
        classification = "STOCHASTIC_BACKGROUND_COMPATIBLE"
    else:
        classification = "UNRESOLVED_RESIDUAL"

    per_run = [{k: v for k, v in f.items() if k != "fft"} for f in feats]
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "classification": classification,
        "sample_spacing": float(sample_spacing),
        "shape": list(raw.shape),
        "commitments": {
            "raw_sha256": _sha_array(raw),
            "model_sha256": _sha_array(model),
            "residual_sha256": _sha_array(residual),
        },
        "metrics": {
            "consensus_peak_bin": consensus,
            "consensus_frequency": freq,
            "cross_run_peak_persistence": persistence,
            "cross_run_phase_coherence": phase_coh,
            "median_peak_power_fraction": peak_fraction,
            "median_abs_lag1": lag1,
            "median_drift_r2": drift_r2,
            "median_abs_normalized_drift_slope": drift_slope,
            "median_block_mean_log_slope": scale_slope,
            "median_abs_nuisance_correlation": nuisance_corr,
            "median_abs_known_template_correlation": known_corr,
        },
        "per_run": per_run,
        "policy": {
            "raw_preserved": True,
            "residual_preserved": True,
            "destructive_denoising": False,
            "interpretation_last": True,
            "new_physics_from_residual_only": False,
            "time_fluctuation_claim_allowed": False,
        },
        "promotion_gates": [
            "independent-run persistence",
            "cross-channel coherence where available",
            "instrument/environment/clock controls",
            "sampling/jitter/alias controls",
            "known-physics template controls",
            "independent replication before physical interpretation",
        ],
    }
    core["analysis_sha256"] = hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    return core


__all__ = ["SCHEMA", "VERSION", "analyze_residual_stack"]
