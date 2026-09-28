from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v09 import analyze_residual_stack_v09

SCHEMA = "GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_11"
VERSION = "0.11.0"


def _sha_array(x: np.ndarray) -> str:
    a = np.ascontiguousarray(np.asarray(x, dtype=np.float64))
    h = hashlib.sha256()
    h.update(str(a.shape).encode())
    h.update(a.tobytes())
    return h.hexdigest()


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


def _raw_phase_surrogate(raw: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    raw = np.asarray(raw, float)
    n = raw.shape[1]
    f = np.fft.rfft(raw, axis=1)
    amp = np.abs(f)
    phase = rng.uniform(0.0, 2.0 * np.pi, f.shape)

    # Preserve real-valued constraints at DC and Nyquist.
    phase[:, 0] = np.angle(f[:, 0])
    if n % 2 == 0:
        phase[:, -1] = np.angle(f[:, -1])

    return np.fft.irfft(amp * np.exp(1j * phase), n=n, axis=1)


def _run_dependence_surrogate_audit(
    residual: np.ndarray,
    candidate_bin: int,
    *,
    null_count: int,
    alpha: float,
) -> dict[str, Any]:
    if not (0.0 < alpha < 1.0):
        raise ValueError("run_dependence_alpha must be in (0,1)")
    if null_count < 1:
        raise ValueError("run_dependence_null_count must be positive")

    # Two dependence statistics are tested; Bonferroni split controls their union.
    per_metric_alpha = alpha / 2.0
    if 1.0 / (null_count + 1) > per_metric_alpha:
        raise ValueError(
            "run-dependence null_count cannot resolve alpha/2; increase null_count"
        )

    observed_processed = _notch(residual, candidate_bin)
    observed_zero, observed_circ = _pair_dependence_stats(observed_processed)

    seed = int(_sha_array(residual)[:16], 16)
    rng = np.random.default_rng(seed)
    null_zero: list[float] = []
    null_circ: list[float] = []

    # IMPORTANT ORDER:
    # surrogate RAW residual first, then apply the exact same detrend+notch.
    # Randomizing phase after preprocessing is invalid for strongly colored
    # processes because preprocessing can couple amplitudes and phases.
    for _ in range(null_count):
        surrogate_raw = _raw_phase_surrogate(residual, rng)
        surrogate_processed = _notch(surrogate_raw, candidate_bin)
        z, c = _pair_dependence_stats(surrogate_processed)
        null_zero.append(z)
        null_circ.append(c)

    nz = np.asarray(null_zero, float)
    nc = np.asarray(null_circ, float)
    p_zero = float((1 + np.sum(nz >= observed_zero)) / (len(nz) + 1))
    p_circ = float((1 + np.sum(nc >= observed_circ)) / (len(nc) + 1))

    invalid = bool(min(p_zero, p_circ) <= per_metric_alpha)
    return {
        "candidate_bin_removed": int(candidate_bin),
        "observed_median_abs_zero_lag_correlation": observed_zero,
        "observed_median_max_circular_correlation": observed_circ,
        "zero_lag_monte_carlo_p": p_zero,
        "circular_monte_carlo_p": p_circ,
        "zero_lag_null_q995": float(np.quantile(nz, 0.995)),
        "circular_null_q995": float(np.quantile(nc, 0.995)),
        "run_dependence_alpha": float(alpha),
        "per_metric_alpha": float(per_metric_alpha),
        "null_ensemble_size": int(len(nz)),
        "invalidates_crossfit": invalid,
        "surrogate_operator_order": "RAW_PHASE_SURROGATE_THEN_IDENTICAL_DETREND_AND_NOTCH",
        "surrogate_preserves_each_raw_run_amplitude_spectrum": True,
    }


def analyze_residual_stack_v11(
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
    run_dependence_stationarity_declared: bool = False,
    run_dependence_alpha: float = 0.01,
    run_dependence_null_count: int = 255,
) -> dict[str, Any]:
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

    if run_dependence_stationarity_declared:
        audit = _run_dependence_surrogate_audit(
            residual,
            k,
            null_count=run_dependence_null_count,
            alpha=run_dependence_alpha,
        )
        audit_status = "CALIBRATED_STATIONARY_SURROGATE"
    else:
        audit = {
            "candidate_bin_removed": k,
            "invalidates_crossfit": None,
            "run_dependence_alpha": float(run_dependence_alpha),
            "null_ensemble_size": 0,
            "surrogate_operator_order": None,
            "surrogate_preserves_each_raw_run_amplitude_spectrum": None,
        }
        audit_status = "UNCALIBRATED_STATIONARITY_NOT_DECLARED"

    out = dict(base)
    out["schema"] = SCHEMA
    out["version"] = VERSION
    out["legacy_v09_classification"] = base["classification"]

    if run_dependence_stationarity_declared and audit["invalidates_crossfit"] is True:
        out["classification"] = "RUN_DEPENDENCE_INVALIDATES_CROSSFIT"
    else:
        out["classification"] = base["classification"]

    out["metrics"] = dict(base["metrics"])
    out["metrics"]["run_dependence_surrogate_audit"] = audit
    out["metrics"]["run_dependence_audit_status"] = audit_status

    out["policy"] = dict(base["policy"])
    out["policy"].update({
        "run_independence_required_for_crossfit": True,
        "fixed_absolute_run_correlation_thresholds_forbidden": True,
        "run_dependence_surrogate_requires_stationarity_declaration": True,
        "raw_phase_surrogate_precedes_preprocessing": True,
        "post_preprocessing_phase_scramble_forbidden": True,
        "two_dependence_metrics_bonferroni_split": True,
        "run_dependence_audit_calibrated": bool(run_dependence_stationarity_declared),
        "shared_or_shifted_background_realization_is_not_independent_replication": True,
        "stationarity_declaration_is_not_physical_attribution": True,
    })
    out["promotion_gates"] = [
        "run-dependence surrogate audit with acquisition-valid null",
        *base["promotion_gates"],
    ]

    out.pop("analysis_sha256", None)
    out["analysis_sha256"] = hashlib.sha256(
        json.dumps(out, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    return out


__all__ = ["SCHEMA", "VERSION", "analyze_residual_stack_v11"]
