from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v02 import analyze_residual_stack

SCHEMA = "GREMLIN_RECURSIVE_RESIDUAL_DECOMPOSITION_V0_3"
VERSION = "0.3.0"

_ALLOWED_SOURCE_TYPES = {
    "instrument_channel",
    "environment_channel",
    "clock_channel",
    "preregistered_template",
    "known_systematic_template",
}


def _sha_array(x: np.ndarray) -> str:
    a = np.ascontiguousarray(np.asarray(x, dtype=np.float64))
    h = hashlib.sha256()
    h.update(str(a.shape).encode())
    h.update(a.tobytes())
    return h.hexdigest()


def _canonical_sha(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _fit(target: np.ndarray, components: Sequence[np.ndarray], runs: np.ndarray) -> np.ndarray:
    if not components:
        return np.zeros(0, dtype=float)
    y = target[runs].reshape(-1)
    X = np.stack([c[runs].reshape(-1) for c in components], axis=1)
    return np.linalg.lstsq(X, y, rcond=None)[0]


def _model(initial: np.ndarray, components: Sequence[np.ndarray], beta: np.ndarray) -> np.ndarray:
    out = np.array(initial, dtype=float, copy=True)
    for component, coefficient in zip(components, beta):
        out += float(coefficient) * component
    return out


def _fold_pairs(n_runs: int) -> list[tuple[np.ndarray, np.ndarray]]:
    ids = np.arange(n_runs)
    even = ids % 2 == 0
    first = ids < n_runs // 2
    pairs: list[tuple[np.ndarray, np.ndarray]] = []
    for mask in (even, first):
        a = ids[mask]
        b = ids[~mask]
        if a.size and b.size:
            pairs.append((a, b))
            pairs.append((b, a))
    return pairs


def _phase_scrambled_null(component: np.ndarray, name: str) -> np.ndarray:
    # Preserve each run's spectrum exactly under circular shift while destroying
    # the original time/phase alignment used for nuisance attribution.
    n_runs, n_samples = component.shape
    seed = int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)
    out = np.empty_like(component)
    for i in range(n_runs):
        shift = 1 + ((seed + 7919 * i) % (n_samples - 1))
        out[i] = np.roll(component[i], shift)
    return out


def _flat_corr(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, float).reshape(-1)
    bb = np.asarray(b, float).reshape(-1)
    aa = aa - aa.mean()
    bb = bb - bb.mean()
    den = float(np.linalg.norm(aa) * np.linalg.norm(bb))
    return 0.0 if den == 0.0 else float(np.dot(aa, bb) / den)


def _increment_score(
    raw: np.ndarray,
    initial: np.ndarray,
    accepted: Sequence[np.ndarray],
    candidate: np.ndarray,
    name: str,
) -> dict[str, Any]:
    target = raw - initial
    null = _phase_scrambled_null(candidate, name)
    gains: list[float] = []
    null_gains: list[float] = []
    coefficients: list[float] = []

    for train, holdout in _fold_pairs(raw.shape[0]):
        beta_base = _fit(target, accepted, train)
        model_base = _model(initial, accepted, beta_base)
        sse_base = float(np.sum((raw[holdout] - model_base[holdout]) ** 2))
        if sse_base <= 0.0:
            raise ValueError("degenerate zero holdout SSE")

        beta_aug = _fit(target, [*accepted, candidate], train)
        model_aug = _model(initial, [*accepted, candidate], beta_aug)
        sse_aug = float(np.sum((raw[holdout] - model_aug[holdout]) ** 2))
        gains.append(1.0 - sse_aug / sse_base)
        coefficients.append(float(beta_aug[-1]))

        beta_null = _fit(target, [*accepted, null], train)
        model_null = _model(initial, [*accepted, null], beta_null)
        sse_null = float(np.sum((raw[holdout] - model_null[holdout]) ** 2))
        null_gains.append(1.0 - sse_null / sse_base)

    nonzero_signs = [int(np.sign(x)) for x in coefficients if abs(x) > 1e-12]
    sign_consistent = bool(nonzero_signs) and all(x == nonzero_signs[0] for x in nonzero_signs)
    conservative_gain = float(min(gains))
    conservative_null_gain = float(max(null_gains))
    margin = conservative_gain - conservative_null_gain
    return {
        "holdout_gains": gains,
        "phase_scrambled_null_gains": null_gains,
        "crossfit_coefficients": coefficients,
        "coefficient_sign_consistent": sign_consistent,
        "conservative_holdout_gain": conservative_gain,
        "conservative_null_gain": conservative_null_gain,
        "gain_over_null_margin": margin,
    }


def _validate_metadata(metadata: Mapping[str, Mapping[str, Any]], names: Sequence[str]) -> None:
    for name in names:
        m = metadata.get(name)
        if not isinstance(m, Mapping):
            raise ValueError(f"missing nuisance metadata for {name}")
        if m.get("frozen_before_fit") is not True:
            raise ValueError(f"nuisance {name} was not frozen before target fit")
        if m.get("independent_of_target_fit") is not True:
            raise ValueError(f"nuisance {name} is target-derived")
        if m.get("source_type") not in _ALLOWED_SOURCE_TYPES:
            raise ValueError(f"unsupported nuisance source_type for {name}")
        if not isinstance(m.get("source_id"), str) or not m["source_id"]:
            raise ValueError(f"missing nuisance source_id for {name}")


def recursive_residual_decomposition(
    raw_runs: Sequence[Sequence[float]],
    initial_model_runs: Sequence[Sequence[float]],
    nuisance_components: Mapping[str, Sequence[Sequence[float]]],
    nuisance_metadata: Mapping[str, Mapping[str, Any]],
    *,
    sample_spacing: float = 1.0,
    min_holdout_gain: float = 0.01,
    min_gain_over_null: float = 0.005,
    alias_abs_correlation: float = 0.97,
    max_layers: int = 8,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    raw = np.asarray(raw_runs, float)
    initial = np.asarray(initial_model_runs, float)
    if raw.shape != initial.shape or raw.ndim != 2 or raw.shape[0] < 4 or raw.shape[1] < 64:
        raise ValueError("raw/initial must be equal-shape 2D arrays with >=4 runs and >=64 samples")
    if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(initial)):
        raise ValueError("raw/initial must be finite")
    if not nuisance_components:
        raise ValueError("at least one frozen nuisance component is required")
    if max_layers < 1:
        raise ValueError("max_layers must be positive")

    names = sorted(str(name) for name in nuisance_components)
    _validate_metadata(nuisance_metadata, names)
    components: dict[str, np.ndarray] = {}
    for name in names:
        c = np.asarray(nuisance_components[name], float)
        if c.shape != raw.shape or not np.all(np.isfinite(c)):
            raise ValueError(f"invalid nuisance component {name}")
        components[name] = c

    alias_pairs: list[dict[str, Any]] = []
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            corr = abs(_flat_corr(components[left], components[right]))
            if corr >= alias_abs_correlation:
                alias_pairs.append({"left": left, "right": right, "abs_correlation": corr})

    accepted: list[str] = []
    selection_rounds: list[dict[str, Any]] = []
    stages: list[dict[str, Any]] = []

    stage0_packet = analyze_residual_stack(raw, initial, sample_spacing=sample_spacing)
    stage0 = {
        "stage_index": 0,
        "accepted_component": None,
        "accepted_components": [],
        "joint_coefficients": {},
        "classification": stage0_packet["classification"],
        "analysis_sha256": stage0_packet["analysis_sha256"],
        "commitments": stage0_packet["commitments"],
        "previous_stage_sha256": None,
    }
    stage0["stage_sha256"] = _canonical_sha(stage0)
    stages.append(stage0)

    for round_index in range(max_layers):
        round_scores: dict[str, Any] = {}
        passing: list[tuple[float, float, str]] = []
        accepted_arrays = [components[name] for name in accepted]

        for name in names:
            if name in accepted:
                continue
            score = _increment_score(raw, initial, accepted_arrays, components[name], name)
            if score["conservative_holdout_gain"] < min_holdout_gain:
                reason = "NO_CONSERVATIVE_HOLDOUT_GAIN"
            elif score["gain_over_null_margin"] < min_gain_over_null:
                reason = "FAIL_PHASE_SCRAMBLED_NULL_MARGIN"
            elif score["coefficient_sign_consistent"] is not True:
                reason = "CROSSFIT_COEFFICIENT_SIGN_INSTABILITY"
            else:
                reason = "PASS"
                passing.append((
                    score["gain_over_null_margin"],
                    score["conservative_holdout_gain"],
                    name,
                ))
            round_scores[name] = {**score, "decision": reason}

        selection_rounds.append({
            "round_index": round_index + 1,
            "candidate_scores": round_scores,
        })
        if not passing:
            break

        # Candidate input order is ignored. Selection is score-first with lexical
        # tie break, making mapping insertion order non-authoritative.
        passing.sort(key=lambda item: (-item[0], -item[1], item[2]))
        chosen = passing[0][2]
        accepted.append(chosen)

        accepted_arrays = [components[name] for name in accepted]
        full_beta = _fit(raw - initial, accepted_arrays, np.arange(raw.shape[0]))
        current_model = _model(initial, accepted_arrays, full_beta)
        packet = analyze_residual_stack(raw, current_model, sample_spacing=sample_spacing)
        stage = {
            "stage_index": len(stages),
            "accepted_component": chosen,
            "accepted_components": list(accepted),
            "joint_coefficients": {
                name: float(beta) for name, beta in zip(accepted, full_beta)
            },
            "selection_score": round_scores[chosen],
            "classification": packet["classification"],
            "analysis_sha256": packet["analysis_sha256"],
            "commitments": packet["commitments"],
            "previous_stage_sha256": stages[-1]["stage_sha256"],
        }
        stage["stage_sha256"] = _canonical_sha(stage)
        stages.append(stage)

    accepted_arrays = [components[name] for name in accepted]
    final_beta = _fit(raw - initial, accepted_arrays, np.arange(raw.shape[0]))
    final_model = _model(initial, accepted_arrays, final_beta)
    final_residual = raw - final_model
    final_packet = analyze_residual_stack(raw, final_model, sample_spacing=sample_spacing)

    final_scores: dict[str, Any] = {}
    for round_info in reversed(selection_rounds):
        for name, score in round_info["candidate_scores"].items():
            if name not in accepted and name not in final_scores:
                final_scores[name] = score

    alias_with_accepted = [
        pair for pair in alias_pairs
        if pair["left"] in accepted or pair["right"] in accepted
    ]
    if not accepted:
        status = "NO_NUISANCE_LAYER_ACCEPTED"
    elif alias_with_accepted:
        status = "PASS_WITH_ATTRIBUTION_ALIAS_OPEN"
    else:
        status = "PASS"

    result: dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": status,
        "ordering_policy": "MAX_CONSERVATIVE_CROSSFIT_GAIN_OVER_PHASE_SCRAMBLED_NULL_THEN_LEXICAL_TIEBREAK",
        "input_mapping_order_authoritative": False,
        "raw_sha256": _sha_array(raw),
        "initial_model_sha256": _sha_array(initial),
        "accepted_layers": accepted,
        "final_joint_coefficients": {
            name: float(beta) for name, beta in zip(accepted, final_beta)
        },
        "selection_rounds": selection_rounds,
        "stages": stages,
        "rejected_candidates": final_scores,
        "alias_pairs": alias_pairs,
        "attribution_ambiguous": bool(alias_with_accepted),
        "final_packet": final_packet,
        "policy": {
            "raw_preserved_across_all_stages": True,
            "each_layer_requires_out_of_fold_gain": True,
            "phase_scrambled_null_required": True,
            "candidate_must_be_frozen_before_fit": True,
            "target_derived_nuisance_forbidden": True,
            "joint_refit_after_acceptance": True,
            "destructive_denoising": False,
            "interpretation_last": True,
            "physical_mechanism_from_decomposition_only": False,
            "time_fluctuation_claim_allowed": False,
        },
    }
    result["decomposition_sha256"] = _canonical_sha(result)
    return result, final_model, final_residual


__all__ = ["SCHEMA", "VERSION", "recursive_residual_decomposition"]
