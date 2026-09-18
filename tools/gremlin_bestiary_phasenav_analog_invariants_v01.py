from __future__ import annotations

import math
from typing import Callable

from tools import gremlin_bestiary_phasenav_phase_gates_v01 as g
from tools.gremlin_bestiary_phasenav_threeway_v01 import (
    ANALOG_CORE_SPECIES,
    rk4_continuous_batch,
)

CONTRACT_ID = "GREMLIN_BESTIARY_PHASENAV_ANALOG_INVARIANTS_V0_1"


def _state(offset: float = 0.0, slope: float = 0.01) -> g.PhaseState36:
    return g.PhaseState36([((offset + slope * i) % g.TAU) for i in range(g.DIM)])


def _shifted(
    state: g.PhaseState36,
    delta: float,
    axes: tuple[int, ...] | None = None,
) -> g.PhaseState36:
    theta = list(state.theta)
    selected = range(g.DIM) if axes is None else axes
    for i in selected:
        theta[i] = (theta[i] + delta) % g.TAU
    return g.PhaseState36(theta)


def _flow(
    species: str,
    states: tuple[g.PhaseState36, ...],
    *,
    horizon: float = 0.12,
    substeps: int = 128,
    target: tuple[float, ...] | None = None,
) -> tuple[g.PhaseState36, ...]:
    if species not in ANALOG_CORE_SPECIES:
        raise g.PhaseGateError(f"{species} is not an analog-core candidate")
    gate = g.PhaseGate36(species)
    return rk4_continuous_batch(
        gate,
        states,
        horizon=horizon,
        substeps=substeps,
        target=target,
    )


def spider_invariant() -> dict[str, object]:
    a = _state(0.1)
    b = _shifted(a, 0.02)
    c = _state(2.7, 0.19)
    flowed = _flow("SPIDER", (a, b, c))
    out = g.spider_scan(flowed, threshold=0.95)
    close_edge = any(
        edge["left"] == 0 and edge["right"] == 1 for edge in out["data"]["edges"]
    )
    return {
        "species": "SPIDER",
        "invariant": "CLOSE_RELATION_EDGE_PRESERVED",
        "pass": close_edge,
        "edge_count": len(out["data"]["edges"]),
    }


def raven_invariant() -> dict[str, object]:
    query = _state(0.3)
    memory = (_state(2.5, 0.17), g.PhaseState36(query.theta), _shifted(query, 0.12))
    flowed = _flow("RAVEN", (query, *memory))
    out = g.raven_recall(flowed[0], flowed[1:], k=2)
    first = out["data"]["matches"][0]
    passed = first["index"] == 1 and abs(float(first["score"]) - 1.0) <= 1e-12
    return {
        "species": "RAVEN",
        "invariant": "EXACT_MEMORY_REMAINS_TOP_RECALL",
        "pass": passed,
        "top_index": first["index"],
        "top_score": first["score"],
    }


def hound_invariant() -> dict[str, object]:
    baseline = _state(0.2)
    near = _shifted(baseline, 0.02, (0,))
    far = _shifted(baseline, 0.9, (0, 1, 2, 3, 4))
    flowed = _flow("HOUND", (baseline, near, far))
    near_score = float(g.hound_scan(flowed[1], flowed[0])["data"]["rms_residual"])
    far_score = float(g.hound_scan(flowed[2], flowed[0])["data"]["rms_residual"])
    return {
        "species": "HOUND",
        "invariant": "LARGER_ANOMALY_REMAINS_LARGER",
        "pass": far_score > near_score > 0.0,
        "near_rms": near_score,
        "far_rms": far_score,
    }


def mole_invariant() -> dict[str, object]:
    start = _state(0.1)
    target = _state(1.0, 0.014)
    before = g.torus_distance(start.theta, target.theta)
    flowed = _flow("MOLE", (start,), horizon=0.8, substeps=256, target=target.theta)
    after = g.torus_distance(flowed[0].theta, target.theta)
    return {
        "species": "MOLE",
        "invariant": "TARGET_DISTANCE_DECREASES",
        "pass": after < before,
        "before": before,
        "after": after,
        "ratio": after / before,
    }


def fox_invariant() -> dict[str, object]:
    start = _state(0.2)
    goal = _state(1.1, 0.017)
    horizons = (0.10, 0.20, 0.40, 0.80)
    distances = []
    for horizon in horizons:
        state = _flow(
            "FOX",
            (start,),
            horizon=horizon,
            substeps=max(64, int(256 * horizon)),
            target=goal.theta,
        )[0]
        distances.append(g.torus_distance(state.theta, goal.theta))
    monotone = all(b < a for a, b in zip(distances, distances[1:]))
    return {
        "species": "FOX",
        "invariant": "CONTINUOUS_PLAN_PROGRESS_MONOTONE",
        "pass": monotone,
        "horizons": list(horizons),
        "goal_distances": distances,
    }


def beaver_invariant() -> dict[str, object]:
    a = _state(0.4, 0.015)
    b = _shifted(a, 0.18)
    fa, fb = _flow("BEAVER", (a, b))
    out = g.beaver_construct((fa, fb))
    candidate = g.PhaseState36(out["data"]["theta"])
    pair = g.torus_distance(fa.theta, fb.theta)
    da = g.torus_distance(candidate.theta, fa.theta)
    db = g.torus_distance(candidate.theta, fb.theta)
    return {
        "species": "BEAVER",
        "invariant": "CONSTRUCTION_REMAINS_BETWEEN_CLOSE_PARTS",
        "pass": da < pair and db < pair,
        "part_distance": pair,
        "candidate_to_left": da,
        "candidate_to_right": db,
    }


def bat_invariant() -> dict[str, object]:
    n = 32
    harmonic = 4
    history = tuple(
        g.PhaseState36([
            (1.2 + 0.30 * math.sin(2.0 * math.pi * harmonic * t / n)) % g.TAU
            for _ in range(g.DIM)
        ])
        for t in range(n)
    )
    flowed = _flow("BAT", history, horizon=0.04, substeps=64)
    out = g.bat_scan(flowed)
    observed = int(out["data"]["dominant_harmonic"])
    power_fraction = float(out["data"]["power_fraction"])
    return {
        "species": "BAT",
        "invariant": "INJECTED_WEAK_HARMONIC_REMAINS_DOMINANT",
        "pass": observed == harmonic and power_fraction > 0.80,
        "injected_harmonic": harmonic,
        "observed_harmonic": observed,
        "power_fraction": power_fraction,
    }


def canary_invariant() -> dict[str, object]:
    base = _state(0.1)
    history = (
        base,
        _shifted(base, 0.01),
        _shifted(base, 0.02),
        _shifted(base, 0.80),
        _shifted(base, 1.50),
    )
    flowed = _flow("CANARY", history, horizon=0.04, substeps=64)
    out = g.canary_watch(flowed, slack=0.005, threshold=0.35)
    return {
        "species": "CANARY",
        "invariant": "SUDDEN_DRIFT_REMAINS_BLOCKING",
        "pass": out["data"]["verdict"] == "BLOCK_CANDIDATE",
        "verdict": out["data"]["verdict"],
        "peak_cusum": out["data"]["peak_cusum"],
    }


def serpent_invariant() -> dict[str, object]:
    base = _state(0.1)
    small = _shifted(base, 0.01)
    hot = _shifted(small, 0.80)
    flowed = _flow("SERPENT", (base, small, hot), horizon=0.05, substeps=64)
    cold = g.serpent_sense((flowed[0], flowed[1]), reference=(flowed[0],))
    warm = g.serpent_sense((flowed[1], flowed[2]), reference=(flowed[0],))
    cold_t = float(cold["data"]["temperature"])
    warm_t = float(warm["data"]["temperature"])
    cold_n = float(cold["data"]["novelty"])
    warm_n = float(warm["data"]["novelty"])
    return {
        "species": "SERPENT",
        "invariant": "HOTTER_NOVEL_OBJECT_REMAINS_HOTTER_AND_MORE_NOVEL",
        "pass": warm_t > cold_t and warm_n > cold_n,
        "cold_temperature": cold_t,
        "warm_temperature": warm_t,
        "cold_novelty": cold_n,
        "warm_novelty": warm_n,
    }


CHECKS: dict[str, Callable[[], dict[str, object]]] = {
    "SPIDER": spider_invariant,
    "RAVEN": raven_invariant,
    "HOUND": hound_invariant,
    "MOLE": mole_invariant,
    "FOX": fox_invariant,
    "BEAVER": beaver_invariant,
    "BAT": bat_invariant,
    "CANARY": canary_invariant,
    "SERPENT": serpent_invariant,
}

if frozenset(CHECKS) != ANALOG_CORE_SPECIES:
    raise RuntimeError("analog invariant suite must cover every analog-core species exactly")


def run_analog_invariant_suite() -> dict[str, object]:
    results = [CHECKS[name]() for name in sorted(CHECKS)]
    failed = [str(r["species"]) for r in results if not bool(r["pass"])]
    return {
        "schema": "GREMLIN_BESTIARY_PHASENAV_ANALOG_INVARIANT_SUITE_V0_1",
        "contract_id": CONTRACT_ID,
        "species_count": len(results),
        "results": results,
        "summary": {
            "all_analog_core_specialist_invariants_pass": not failed,
            "passed": len(results) - len(failed),
            "failed": len(failed),
            "failed_species": failed,
            "scope": "CONTINUOUS_PHASE_PRECONDITIONING_PLUS_EXISTING_SPECIALIST_OPERATOR",
            "fully_analog_specialist_semantics_claim": False,
            "physical_analog_claim": False,
            "hardware_analog_witness": False,
            "external_effects": False,
            "canon_allowed": False,
        },
    }
