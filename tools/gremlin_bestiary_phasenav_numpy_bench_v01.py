from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from tools.gremlin_bestiary_phasenav_phase_gates_v01 import DIM, SPECIES, TAU, PhaseState36
from tools.gremlin_bestiary_phasenav_numpy_v01 import (
    CONTRACT_ID,
    analog_kernel_continuity_probe,
    benchmark_scalar_vs_vector,
    scalar_vector_equivalence,
)

SCHEMA = "GREMLIN_BESTIARY_PHASENAV_NUMPY_BENCHMARK_SUITE_V0_1"


def frozen_workload(n: int = 512) -> tuple[PhaseState36, ...]:
    if n < 1:
        raise ValueError("n must be positive")
    states = []
    for j in range(n):
        theta = []
        for i in range(DIM):
            x = (
                0.173 * (i + 1)
                + 0.071 * (j + 1)
                + 0.019 * math.sin((i + 1) * (j + 1) / 17.0)
                + 0.013 * math.cos((i + 3) * (j + 5) / 29.0)
            ) % TAU
            theta.append(x)
        states.append(PhaseState36(theta))
    return tuple(states)


def workload_sha256(states: tuple[PhaseState36, ...]) -> str:
    payload = [[float(x) for x in s.theta] for s in states]
    raw = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def run_suite(n: int = 512, repeats: int = 7) -> dict[str, object]:
    states = frozen_workload(n)
    equivalence = []
    continuity = []
    benchmarks = []

    for species in SPECIES:
        equivalence.append(scalar_vector_equivalence(species, states))
        continuity.append(analog_kernel_continuity_probe(species, states[0]))
        benchmarks.append(benchmark_scalar_vs_vector(species, states, repeats=repeats))

    max_error = max(float(x["max_torus_error"]) for x in equivalence)
    all_continuous = all(bool(x["phase_kernel_continuity_candidate"]) for x in continuity)
    speedups = [float(x["speedup"]) for x in benchmarks]

    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "workload": {
            "batch_size": n,
            "dimension": DIM,
            "sha256": workload_sha256(states),
            "construction": "deterministic_trigonometric_fixture",
        },
        "repeats": repeats,
        "species_count": len(SPECIES),
        "equivalence": equivalence,
        "continuity": continuity,
        "benchmarks": benchmarks,
        "summary": {
            "max_scalar_vector_torus_error": max_error,
            "all_species_scalar_vector_equivalent_1e_12": max_error < 1e-12,
            "all_phase_kernels_continuity_candidates": all_continuous,
            "min_measured_speedup": min(speedups),
            "median_measured_speedup": sorted(speedups)[len(speedups) // 2],
            "max_measured_speedup": max(speedups),
            "performance_gate": "MEASURE_ONLY_NO_PROMOTION_THRESHOLD",
            "physical_analog_claim": False,
            "external_effects": False,
        },
    }


def main() -> int:
    receipt = run_suite()
    out = Path("provenance/GREMLIN_BESTIARY_PHASENAV_NUMPY_BENCHMARK_V0_1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt["summary"], sort_keys=True))
    print(f"receipt={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
