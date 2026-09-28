from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v09 import analyze_residual_stack_v09

SCHEMA = "GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_12"
VERSION = "0.12.0"


def _sha_array(x: np.ndarray) -> str:
    a = np.ascontiguousarray(np.asarray(x, dtype=np.float64))
    h = hashlib.sha256()
    h.update(str(a.shape).encode())
    h.update(a.tobytes())
    return h.hexdigest()


def _safe_corr(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, float) - float(np.mean(a))
    bb = np.asarray(b, float) - float(np.mean(b))
    den = float(np.linalg.norm(aa) * np.linalg.norm(bb))
    return 0.0 if den == 0.0 else float(np.dot(aa, bb) / den)


def _detrend(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, float)
    t = np.arange(x.size, dtype=float)
    y = x - np.polyval(np.polyfit(t, x, 1), t)
    return y - y.mean()


def _notch(runs: np.ndarray, k: int, width: int = 3) -> np.ndarray:
    out = []
    for row in np.asarray(runs, float):
        y = _detrend(row)
        f = np.fft.rfft(y)
        f[max(1, k - width):min(len(f), k + width + 1)] = 0.0
        out.append(np.fft.irfft(f, n=len(y)))
    return np.asarray(out)


def _pair_dependence_stats(x: np.ndarray) -> tuple[float, float]:
    x = np.asarray(x, float)
    x = x - x.mean(axis=1, keepdims=True)
    norms = np.linalg.norm(x, axis=1)
    safe = np.where(norms == 0.0, 1.0, norms)
    xn = x / safe[:, None]
    iu = np.triu_indices(len(x), 1)

    zero = np.abs((xn @ xn.T)[iu])
    median_zero = float(np.median(zero))

    f = np.fft.rfft(x, axis=1)
    cross = f[iu[0]] * np.conj(f[iu[1]])
    circ = np.fft.irfft(cross, n=x.shape[1], axis=1)
    den = (safe[iu[0]] * safe[iu[1]])[:, None]
    max_circ = np.max(np.abs(circ) / den, axis=1)
    median_circ = float(np.median(max_circ))
    return median_zero, median_circ


def _median_abs_lag1(runs: np.ndarray) -> float:
    vals = []
    for row in np.asarray(runs, float):
        vals.append(abs(_safe_corr(row[:-1], row[1:])))
    return float(np.median(vals))


def _iaaft_row(
    x: np.ndarray,
    rng: np.random.Generator,
    iterations: int,
) -> tuple[np.ndarray, float]:
    x = np.asarray(x, float)
    sorted_x = np.sort(x)
    target_mag = np.abs(np.fft.rfft(x))
    y = rng.permutation(x)

    for _ in range(iterations):
        Y = np.fft.rfft(y)
        phase = np.exp(1j * np.angle(Y))
        z = np.fft.irfft(target_mag * phase, n=len(x))
        order = np.argsort(z)
        y_new = np.empty_like(y)
        y_new[order] = sorted_x
        if np.array_equal(y_new, y):
            y = y_new
            break
        y = y_new

    mag = np.abs(np.fft.rfft(y))
    den = max(float(np.linalg.norm(target_mag)), 1e-15)
    rel = float(np.linalg.norm(mag - target_mag) / den)
    return y, rel


def _iaaft_rows(
    runs: np.ndarray,
    rng: np.random.Generator,
    iterations: int,
) -> tuple[np.ndarray, float]:
    rows = []
    errors = []
    for row in np.asarray(runs, float):
        y, e = _iaaft_row(row, rng, iterations)
        rows.append(y)
        errors.append(e)
    return np.asarray(rows), float(np.median(errors))


def _robust_nonstationarity_diagnostic(residual: np.ndarray) -> dict[str, Any]:
    x = np.asarray(residual, float)
    h = x.shape[1] // 2
    scale_ratio = []
    scale_direction = []
    location_shift = []
    location_direction = []

    for row in x:
        left = row[:h]
        right = row[-h:]
        ml = float(np.median(left))
        mr = float(np.median(right))
        sl = max(1.4826 * float(np.median(np.abs(left - ml))), 1e-12)
        sr = max(1.4826 * float(np.median(np.abs(right - mr))), 1e-12)
        scale_ratio.append(max(sl / sr, sr / sl))
        scale_direction.append(float(np.sign(np.log(sr / sl))))
        pooled = max(0.5 * (sl + sr), 1e-12)
        location_shift.append(abs(mr - ml) / pooled)
        location_direction.append(float(np.sign(mr - ml)))

    scale_ratio = np.asarray(scale_ratio)
    location_shift = np.asarray(location_shift)
    scale_strong = scale_ratio >= 2.0
    location_strong = location_shift >= 1.0

    def _direction_consistency(values: list[float], mask: np.ndarray) -> float:
        v = np.asarray(values)[mask]
        if v.size == 0:
            return 0.0
        return float(max(np.mean(v > 0), np.mean(v < 0)))

    scale_consistency = _direction_consistency(scale_direction, scale_strong)
    location_consistency = _direction_consistency(location_direction, location_strong)

    obvious = bool(
        (float(np.mean(scale_strong)) >= 0.75 and scale_consistency >= 0.80)
        or
        (float(np.mean(location_strong)) >= 0.75 and location_consistency >= 0.80)
    )
    return {
        "heuristic_only": True,
        "median_half_scale_ratio": float(np.median(scale_ratio)),
        "strong_scale_shift_run_fraction": float(np.mean(scale_strong)),
        "strong_scale_shift_direction_consistency": scale_consistency,
        "median_standardized_half_location_shift": float(np.median(location_shift)),
        "strong_location_shift_run_fraction": float(np.mean(location_strong)),
        "strong_location_shift_direction_consistency": location_consistency,
        "obvious_nonstationarity": obvious,
    }


def _run_dependence_iaaft_audit(
    residual: np.ndarray,
    candidate_bin: int,
    *,
    null_count: int,
    iaaft_iterations: int,
    alpha: float,
) -> dict[str, Any]:
    observed_processed = _notch(residual, candidate_bin)
    observed_zero, observed_circ = _pair_dependence_stats(observed_processed)

    seed = int(_sha_array(residual)[:16], 16)
    rng = np.random.default_rng(seed)
    null_zero = []
    null_circ = []
    quality = []

    # Important: preserve RAW marginal+PSD first, then apply exactly the same
    # detrend/notch operator as for the observed residual.
    for _ in range(null_count):
        surrogate_raw, error = _iaaft_rows(residual, rng, iaaft_iterations)
        surrogate_processed = _notch(surrogate_raw, candidate_bin)
        z, c = _pair_dependence_stats(surrogate_processed)
        null_zero.append(z)
        null_circ.append(c)
        quality.append(error)

    nz = np.asarray(null_zero, float)
    nc = np.asarray(null_circ, float)
    p_zero = float((1 + np.sum(nz >= observed_zero)) / (len(nz) + 1))
    p_circ = float((1 + np.sum(nc >= observed_circ)) / (len(nc) + 1))
    per_metric_alpha = alpha / 2.0

    return {
        "candidate_bin_removed": int(candidate_bin),
        "observed_median_abs_zero_lag_correlation": observed_zero,
        "observed_median_max_circular_correlation": observed_circ,
        "zero_lag_monte_carlo_p": p_zero,
        "circular_monte_carlo_p": p_circ,
        "per_metric_alpha": float(per_metric_alpha),
        "invalidates_crossfit": bool(min(p_zero, p_circ) <= per_metric_alpha),
        "null_ensemble_size": int(null_count),
        "iaaft_iterations": int(iaaft_iterations),
        "median_surrogate_psd_relative_error": float(np.median(quality)),
        "q90_surrogate_psd_relative_error": float(np.quantile(quality, 0.90)),
        "null_kind": "RAW_IAAFT_THEN_IDENTICAL_DETREND_AND_NOTCH",
        "empirical_marginal_preserved_by_rank_remap": True,
        "surrogate_operator_order": "RAW_IAAFT_THEN_IDENTICAL_DETREND_AND_NOTCH",
    }


def analyze_residual_stack_v12(
    raw_runs: Sequence[Sequence[float]],
    model_runs: Sequence[Sequence[float]],
    *,
    nuisance_runs=None,
    known_template_runs=None,
    channel_runs=None,
    sample_spacing: float = 1.0,
    ordered_runs: bool = False,
    trend_ambiguity_cycles: float = 3.0,
    accumulation_alpha: float = 0.01,
    path_alpha: float = 0.01,
    path_slope_max: float = 1.5,
    path_slope_step: float = 0.25,
    transient_half_alpha: float = 0.01,
    iaaft_null_applicable_declared: bool = False,
    run_dependence_alpha: float = 0.01,
    run_dependence_null_count: int = 255,
    iaaft_iterations: int = 20,
    max_median_surrogate_psd_relative_error: float = 0.15,
    long_memory_lag1_abstain: float = 0.97,
) -> dict[str, Any]:
    if not (0.0 < run_dependence_alpha < 1.0):
        raise ValueError("run_dependence_alpha must be in (0,1)")
    if 1.0 / (run_dependence_null_count + 1) > run_dependence_alpha / 2.0:
        raise ValueError("run_dependence_null_count cannot resolve alpha/2")
    if iaaft_iterations < 5:
        raise ValueError("iaaft_iterations must be >=5")

    raw = np.asarray(raw_runs, float)
    model = np.asarray(model_runs, float)
    base = analyze_residual_stack_v09(
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
        transient_half_alpha=transient_half_alpha,
    )

    residual = raw - model
    gate = base["metrics"]["crossfit_narrowband_gate"]
    k = int(round(float(gate["median_discovery_bin"])))

    nonstationary = _robust_nonstationarity_diagnostic(residual)
    detrended = np.asarray([_detrend(row) for row in residual])
    background = _notch(residual, k)
    lag1 = max(_median_abs_lag1(detrended), _median_abs_lag1(background))

    audit: dict[str, Any]
    if not iaaft_null_applicable_declared:
        classification = "RUN_DEPENDENCE_AUDIT_IAAFT_NULL_NOT_DECLARED"
        crossfit_valid = False
        audit = {"status": "IAAFT_NULL_NOT_DECLARED", "invalidates_crossfit": None}
    elif nonstationary["obvious_nonstationarity"]:
        classification = "RUN_DEPENDENCE_AUDIT_NONSTATIONARY_UNCALIBRATED"
        crossfit_valid = False
        audit = {"status": "NONSTATIONARY_HARD_ABSTENTION", "invalidates_crossfit": None}
    elif lag1 >= long_memory_lag1_abstain:
        classification = "RUN_DEPENDENCE_AUDIT_LONG_MEMORY_UNCALIBRATED"
        crossfit_valid = False
        audit = {"status": "LONG_MEMORY_HARD_ABSTENTION", "invalidates_crossfit": None}
    else:
        audit = _run_dependence_iaaft_audit(
            residual,
            k,
            null_count=run_dependence_null_count,
            iaaft_iterations=iaaft_iterations,
            alpha=run_dependence_alpha,
        )
        if audit["median_surrogate_psd_relative_error"] > max_median_surrogate_psd_relative_error:
            classification = "RUN_DEPENDENCE_SURROGATE_QUALITY_UNCALIBRATED"
            crossfit_valid = False
        elif audit["invalidates_crossfit"]:
            classification = "RUN_DEPENDENCE_INVALIDATES_CROSSFIT"
            crossfit_valid = False
        else:
            classification = base["classification"]
            crossfit_valid = True

    audit["median_abs_lag1_for_abstention"] = float(lag1)
    audit["long_memory_lag1_abstain"] = float(long_memory_lag1_abstain)
    audit["max_median_surrogate_psd_relative_error"] = float(
        max_median_surrogate_psd_relative_error
    )

    out = dict(base)
    out["schema"] = SCHEMA
    out["version"] = VERSION
    out["legacy_v09_classification"] = base["classification"]
    out["classification"] = classification
    out["metrics"] = dict(base["metrics"])
    out["metrics"]["run_dependence_iaaft_audit"] = audit
    out["metrics"]["nonstationarity_hard_abstention_diagnostic"] = nonstationary
    out["policy"] = dict(base["policy"])
    out["policy"].update({
        "run_independence_required_for_crossfit": True,
        "iaaft_null_applicability_must_be_declared": True,
        "raw_marginal_preservation_required": True,
        "raw_power_spectrum_approximation_required": True,
        "raw_surrogate_precedes_preprocessing": True,
        "post_preprocessing_phase_scramble_forbidden": True,
        "fixed_absolute_run_correlation_thresholds_forbidden": True,
        "obvious_nonstationarity_causes_abstention": True,
        "extreme_long_memory_causes_abstention": True,
        "poor_surrogate_spectral_fidelity_causes_abstention": True,
        "crossfit_valid_under_run_dependence_audit": bool(crossfit_valid),
        "shared_or_shifted_background_realization_is_not_independent_replication": True,
        "passing_dependence_audit_proves_independence": False,
        "failing_dependence_audit_identifies_cause": False,
        "new_physics_from_residual_only": False,
        "time_fluctuation_claim_allowed": False,
    })
    out["promotion_gates"] = [
        "IAAFT run-dependence audit with raw marginal preservation",
        "nonstationarity and long-memory abstention",
        "surrogate spectral-fidelity gate",
        *base["promotion_gates"],
    ]

    out.pop("analysis_sha256", None)
    out["analysis_sha256"] = hashlib.sha256(
        json.dumps(out, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    return out


__all__ = [
    "SCHEMA",
    "VERSION",
    "_iaaft_row",
    "_robust_nonstationarity_diagnostic",
    "analyze_residual_stack_v12",
]
