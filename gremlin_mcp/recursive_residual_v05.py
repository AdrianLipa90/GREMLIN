from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v04 import analyze_residual_stack_v04

SCHEMA = "GREMLIN_RECURSIVE_RESIDUAL_DECOMPOSITION_V0_5"
VERSION = "0.5.0"

_ALLOWED_SOURCE_TYPES = {
    "instrument_channel",
    "environment_channel",
    "clock_channel",
    "preregistered_template",
    "known_systematic_template",
}
_ALLOWED_NULL_POLICIES = {"sample_circular_shift", "run_permutation"}


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
    out: list[tuple[np.ndarray, np.ndarray]] = []
    for mask in (ids % 2 == 0, ids < n_runs // 2):
        a = ids[mask]
        b = ids[~mask]
        out.extend([(a, b), (b, a)])
    return out


def _family_seed(
    components: Mapping[str, np.ndarray],
    metadata: Mapping[str, Mapping[str, Any]],
    remaining: Sequence[str],
) -> int:
    # Labels do not contribute: the null family is content/provenance addressed.
    tokens = sorted(
        f"{metadata[name]['null_policy']}:{_sha_array(components[name])}"
        for name in remaining
    )
    digest = hashlib.sha256("|".join(tokens).encode()).hexdigest()
    return int(digest[:16], 16)


def _shared_null_worlds(
    components: Mapping[str, np.ndarray],
    metadata: Mapping[str, Mapping[str, Any]],
    remaining: Sequence[str],
    *,
    count: int,
) -> list[dict[str, np.ndarray]]:
    first = components[remaining[0]]
    n_runs, n_samples = first.shape
    rng = np.random.default_rng(_family_seed(components, metadata, remaining))

    worlds: list[dict[str, np.ndarray]] = []
    seen_perm: set[tuple[int, ...]] = set()
    seen_shifts: set[tuple[int, ...]] = set()
    identity = tuple(range(n_runs))
    needs_perm = any(
        metadata[name]["null_policy"] == "run_permutation"
        for name in remaining
    )
    needs_shift = any(
        metadata[name]["null_policy"] == "sample_circular_shift"
        for name in remaining
    )
    if needs_perm and count > math.factorial(n_runs) - 1:
        raise ValueError(
            "requested null_count exceeds unique nonidentity run permutations"
        )

    for _ in range(count):
        perm: tuple[int, ...] | None = None
        if needs_perm:
            attempts = 0
            while perm is None:
                attempts += 1
                if attempts > 10000:
                    raise RuntimeError("could not construct shared run-permutation null world")
                candidate = tuple(int(x) for x in rng.permutation(n_runs))
                if candidate != identity and candidate not in seen_perm:
                    seen_perm.add(candidate)
                    perm = candidate

        shifts = None
        if needs_shift:
            attempts = 0
            while shifts is None:
                attempts += 1
                if attempts > 10000:
                    raise RuntimeError(
                        "could not construct unique shared circular-shift null world"
                    )
                candidate_shifts = tuple(
                    int(x)
                    for x in rng.integers(
                        1, n_samples, size=n_runs, endpoint=False
                    )
                )
                if candidate_shifts in seen_shifts:
                    continue
                seen_shifts.add(candidate_shifts)
                shifts = np.asarray(candidate_shifts, dtype=int)

        world: dict[str, np.ndarray] = {}
        for name in remaining:
            component = components[name]
            policy = str(metadata[name]["null_policy"])
            if policy == "run_permutation":
                assert perm is not None
                world[name] = component[np.asarray(perm, dtype=int)]
            elif policy == "sample_circular_shift":
                assert shifts is not None
                proxy = np.empty_like(component)
                for i, shift in enumerate(shifts):
                    proxy[i] = np.roll(component[i], int(shift))
                world[name] = proxy
            else:
                raise ValueError("unsupported nuisance null policy")
        worlds.append(world)
    return worlds


def _candidate_observed(
    raw: np.ndarray,
    initial: np.ndarray,
    accepted: Sequence[np.ndarray],
    candidate: np.ndarray,
) -> tuple[float, list[float], bool, list[float]]:
    target = raw - initial
    gains: list[float] = []
    coefficients: list[float] = []
    base_sse: list[float] = []
    pairs = _fold_pairs(raw.shape[0])

    for train, holdout in pairs:
        beta_base = _fit(target, accepted, train)
        base = _model(initial, accepted, beta_base)
        sse_base = float(np.sum((raw[holdout] - base[holdout]) ** 2))
        if sse_base <= 0.0:
            raise ValueError("degenerate zero holdout SSE")
        base_sse.append(sse_base)

        beta = _fit(target, [*accepted, candidate], train)
        pred = _model(initial, [*accepted, candidate], beta)
        sse = float(np.sum((raw[holdout] - pred[holdout]) ** 2))
        gains.append(1.0 - sse / sse_base)
        coefficients.append(float(beta[-1]))

    signs = [int(np.sign(x)) for x in coefficients if abs(x) > 1e-12]
    sign_consistent = bool(signs) and all(x == signs[0] for x in signs)
    return float(min(gains)), coefficients, sign_consistent, base_sse


def _null_gain(
    raw: np.ndarray,
    initial: np.ndarray,
    accepted: Sequence[np.ndarray],
    null: np.ndarray,
    base_sse: Sequence[float],
) -> float:
    target = raw - initial
    fold: list[float] = []
    for (train, holdout), sse_base in zip(_fold_pairs(raw.shape[0]), base_sse):
        beta = _fit(target, [*accepted, null], train)
        pred = _model(initial, [*accepted, null], beta)
        sse = float(np.sum((raw[holdout] - pred[holdout]) ** 2))
        fold.append(1.0 - sse / sse_base)
    return float(min(fold))


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
        if m.get("null_policy") not in _ALLOWED_NULL_POLICIES:
            raise ValueError(f"unsupported nuisance null_policy for {name}")
        if not isinstance(m.get("source_id"), str) or not m["source_id"]:
            raise ValueError(f"missing nuisance source_id for {name}")


def recursive_residual_decomposition_v05(
    raw_runs: Sequence[Sequence[float]],
    initial_model_runs: Sequence[Sequence[float]],
    nuisance_components: Mapping[str, Sequence[Sequence[float]]],
    nuisance_metadata: Mapping[str, Mapping[str, Any]],
    *,
    sample_spacing: float = 1.0,
    min_holdout_gain: float = 0.01,
    min_gain_over_individual_null: float = 0.005,
    global_familywise_alpha: float = 0.01,
    null_count: int = 1023,
    max_candidates: int = 64,
    alias_abs_correlation: float = 0.97,
    max_layers: int = 8,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    raw = np.asarray(raw_runs, float)
    initial = np.asarray(initial_model_runs, float)
    if raw.shape != initial.shape or raw.ndim != 2 or raw.shape[0] < 8 or raw.shape[1] < 64:
        raise ValueError("v0.5 requires equal-shape [runs,samples] with >=8 runs and >=64 samples")
    if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(initial)):
        raise ValueError("raw/initial must be finite")
    if not nuisance_components:
        raise ValueError("at least one frozen nuisance component is required")
    if not (0.0 < global_familywise_alpha < 1.0):
        raise ValueError("global_familywise_alpha must be in (0,1)")
    if max_layers < 1:
        raise ValueError("max_layers must be positive")
    if len(nuisance_components) > max_candidates:
        raise ValueError("candidate family too large for greedy v0.5")

    round_alpha = float(global_familywise_alpha) / float(max_layers)
    minimum_null_worlds = int(math.ceil(1.0 / round_alpha) - 1)
    if null_count < minimum_null_worlds:
        raise ValueError(
            f"null_count={null_count} cannot resolve round alpha={round_alpha}; "
            f"need at least {minimum_null_worlds}"
        )

    names = sorted(str(name) for name in nuisance_components)
    _validate_metadata(nuisance_metadata, names)
    components: dict[str, np.ndarray] = {}
    for name in names:
        c = np.asarray(nuisance_components[name], float)
        if c.shape != raw.shape or not np.all(np.isfinite(c)):
            raise ValueError(f"invalid nuisance component {name}")
        components[name] = c

    def flat_corr(a: np.ndarray, b: np.ndarray) -> float:
        aa = a.reshape(-1) - float(a.mean())
        bb = b.reshape(-1) - float(b.mean())
        den = float(np.linalg.norm(aa) * np.linalg.norm(bb))
        return 0.0 if den == 0.0 else float(np.dot(aa, bb) / den)

    alias_pairs = []
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            corr = abs(flat_corr(components[left], components[right]))
            if corr >= alias_abs_correlation:
                alias_pairs.append({"left": left, "right": right, "abs_correlation": corr})

    stage0_packet = analyze_residual_stack_v04(raw, initial, sample_spacing=sample_spacing)
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

    stages = [stage0]
    accepted: list[str] = []
    selection_rounds: list[dict[str, Any]] = []
    alpha_spent = 0.0

    for round_index in range(max_layers):
        remaining = [name for name in names if name not in accepted]
        if not remaining:
            break
        accepted_arrays = [components[name] for name in accepted]
        worlds = _shared_null_worlds(
            components, nuisance_metadata, remaining, count=null_count
        )

        observed: dict[str, Any] = {}
        for name in remaining:
            gain, coefficients, sign_consistent, base_sse = _candidate_observed(
                raw, initial, accepted_arrays, components[name]
            )
            null_gains = np.asarray([
                _null_gain(
                    raw, initial, accepted_arrays, world[name], base_sse
                )
                for world in worlds
            ], dtype=float)
            individual_q90 = float(np.quantile(null_gains, 0.90))
            observed[name] = {
                "conservative_holdout_gain": gain,
                "crossfit_coefficients": coefficients,
                "coefficient_sign_consistent": sign_consistent,
                "null_conservative_gains": null_gains,
                "individual_null_q90_gain": individual_q90,
                "gain_over_individual_null_q90": gain - individual_q90,
                "null_policy": str(nuisance_metadata[name]["null_policy"]),
            }

        family_max_null = np.asarray([
            max(observed[name]["null_conservative_gains"][b] for name in remaining)
            for b in range(null_count)
        ], dtype=float)

        passing = []
        scored: dict[str, Any] = {}
        for name in remaining:
            s = observed[name]
            adjusted_p = float(
                (1 + np.sum(family_max_null >= s["conservative_holdout_gain"]))
                / (null_count + 1)
            )
            if s["conservative_holdout_gain"] < min_holdout_gain:
                decision = "NO_CONSERVATIVE_HOLDOUT_GAIN"
            elif s["gain_over_individual_null_q90"] < min_gain_over_individual_null:
                decision = "FAIL_INDIVIDUAL_NULL_MARGIN"
            elif s["coefficient_sign_consistent"] is not True:
                decision = "CROSSFIT_COEFFICIENT_SIGN_INSTABILITY"
            elif adjusted_p > round_alpha:
                decision = "FAIL_GLOBAL_ALPHA_LEDGER_MAX_NULL"
            else:
                decision = "PASS"
                passing.append((
                    adjusted_p,
                    -s["conservative_holdout_gain"],
                    name,
                ))
            scored[name] = {
                **{k: v for k, v in s.items() if k != "null_conservative_gains"},
                "familywise_adjusted_p": adjusted_p,
                "round_alpha_budget": round_alpha,
                "family_size": len(remaining),
                "shared_null_worlds": null_count,
                "decision": decision,
            }

        alpha_spent += round_alpha
        selection_rounds.append({
            "round_index": round_index + 1,
            "round_alpha_budget": round_alpha,
            "cumulative_alpha_budget_spent": alpha_spent,
            "global_familywise_alpha": float(global_familywise_alpha),
            "shared_null_worlds": null_count,
            "candidate_scores": scored,
        })

        if not passing:
            break

        passing.sort(key=lambda item: (item[0], item[1], item[2]))
        chosen = passing[0][2]
        accepted.append(chosen)

        accepted_arrays = [components[name] for name in accepted]
        beta = _fit(raw - initial, accepted_arrays, np.arange(raw.shape[0]))
        current_model = _model(initial, accepted_arrays, beta)
        packet = analyze_residual_stack_v04(
            raw, current_model, sample_spacing=sample_spacing
        )
        stage = {
            "stage_index": len(stages),
            "accepted_component": chosen,
            "accepted_components": list(accepted),
            "joint_coefficients": {
                name: float(value) for name, value in zip(accepted, beta)
            },
            "selection_score": scored[chosen],
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
    final_packet = analyze_residual_stack_v04(
        raw, final_model, sample_spacing=sample_spacing
    )

    alias_with_accepted = [
        pair for pair in alias_pairs
        if pair["left"] in accepted or pair["right"] in accepted
    ]
    status = (
        "NO_NUISANCE_LAYER_ACCEPTED"
        if not accepted
        else "PASS_WITH_ATTRIBUTION_ALIAS_OPEN"
        if alias_with_accepted
        else "PASS"
    )

    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": status,
        "raw_sha256": _sha_array(raw),
        "initial_model_sha256": _sha_array(initial),
        "accepted_layers": accepted,
        "final_joint_coefficients": {
            name: float(value) for name, value in zip(accepted, final_beta)
        },
        "selection_rounds": selection_rounds,
        "stages": stages,
        "alias_pairs": alias_pairs,
        "attribution_ambiguous": bool(alias_with_accepted),
        "final_packet": final_packet,
        "policy": {
            "global_familywise_alpha": float(global_familywise_alpha),
            "uniform_round_alpha_budget": round_alpha,
            "maximum_alpha_budget": round_alpha * max_layers,
            "minimum_null_worlds_for_budget": minimum_null_worlds,
            "shared_synchronized_null_worlds": True,
            "familywise_adjusted_empirical_p": True,
            "candidate_must_be_frozen_before_fit": True,
            "target_derived_nuisance_forbidden": True,
            "joint_refit_after_acceptance": True,
            "mapping_order_authoritative": False,
            "destructive_denoising": False,
            "interpretation_last": True,
            "physical_mechanism_from_decomposition_only": False,
            "time_fluctuation_claim_allowed": False,
        },
    }
    result["decomposition_sha256"] = _canonical_sha(result)
    return result, final_model, final_residual


__all__ = ["SCHEMA", "VERSION", "recursive_residual_decomposition_v05"]
