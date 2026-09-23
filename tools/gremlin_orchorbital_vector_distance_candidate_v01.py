from __future__ import annotations

import json
import math
from pathlib import Path
import time
from typing import Any

import numpy as np

from tools.gremlin_geometry_phase_scheduler_v01 import (
    DIM,
    TAU,
    SCHEDULER_KEY,
    TaskPhaseState,
    state_distance,
    task_phase_state,
)

OUT = Path("provenance/GREMLIN_ORCHORBITAL_VECTOR_DISTANCE_CANDIDATE_V0_1.json")
SCHEMA = "GREMLIN_ORCHORBITAL_VECTOR_DISTANCE_CANDIDATE_V0_1"


def _positive_int(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _state(index: int) -> TaskPhaseState:
    phase = [
        (
            0.019 * index
            + 0.0031 * axis
            + 0.000071 * index * axis
            + 0.0000003 * index * index
        )
        % TAU
        for axis in range(DIM)
    ]
    row = {
        "task_id": f"vec-{index:06d}",
        "species": "SPIDER",
        "payload": {
            "index": index,
            SCHEDULER_KEY: {
                "phase36": phase,
                "ready": True,
                "readiness": 0.25 + 0.75 * ((index % 19) / 18.0),
                "temperature": (index % 23) / 22.0,
                "urgency": (index % 7) / 6.0,
                "noise": (index % 17) / 20.0,
            },
        },
        "task_commitment": f"commit-vec-{index:06d}",
        "created_ns": index + 1,
    }
    return task_phase_state(row)


def vector_state_distances(
    current: TaskPhaseState,
    candidates: list[TaskPhaseState],
) -> np.ndarray:
    if not candidates:
        return np.empty(0, dtype=np.float64)
    phases = np.asarray([state.phase36 for state in candidates], dtype=np.float64)
    current_phase = np.asarray(current.phase36, dtype=np.float64)
    delta = np.remainder(phases - current_phase + math.pi, TAU) - math.pi
    rms = np.sqrt(np.mean(delta * delta, axis=1))
    geometry = np.minimum(1.0, rms / math.pi)
    temperature = np.abs(
        np.asarray([state.temperature for state in candidates], dtype=np.float64)
        - current.temperature
    )
    readiness = np.abs(
        np.asarray([state.readiness for state in candidates], dtype=np.float64)
        - current.readiness
    )
    return np.minimum(
        1.0,
        0.76 * geometry + 0.14 * temperature + 0.10 * readiness,
    )


def run_benchmark(
    *,
    candidate_count: int = 4096,
    repeats: int = 8,
) -> dict[str, Any]:
    candidate_count = _positive_int(candidate_count, "candidate_count")
    repeats = _positive_int(repeats, "repeats")

    current = _state(0)
    candidates = [_state(index + 1) for index in range(candidate_count)]

    scalar_reference = np.asarray(
        [state_distance(current, state) for state in candidates],
        dtype=np.float64,
    )
    vector_reference = vector_state_distances(current, candidates)
    absolute_error = np.abs(scalar_reference - vector_reference)
    max_abs_error = float(np.max(absolute_error))
    mean_abs_error = float(np.mean(absolute_error))
    same_nearest_index = int(np.argmin(scalar_reference)) == int(
        np.argmin(vector_reference)
    )
    same_farthest_index = int(np.argmax(scalar_reference)) == int(
        np.argmax(vector_reference)
    )

    # Warm both kernels before measuring.
    _ = [state_distance(current, state) for state in candidates[:64]]
    _ = vector_state_distances(current, candidates[:64])

    scalar_start = time.perf_counter()
    scalar_checksum = 0.0
    for _ in range(repeats):
        scalar_checksum += sum(
            state_distance(current, state)
            for state in candidates
        )
    scalar_seconds = time.perf_counter() - scalar_start

    vector_start = time.perf_counter()
    vector_checksum = 0.0
    for _ in range(repeats):
        vector_checksum += float(
            np.sum(vector_state_distances(current, candidates))
        )
    vector_seconds = time.perf_counter() - vector_start

    checksum_error = abs(scalar_checksum - vector_checksum)
    observed_microkernel_speedup = (
        float("inf")
        if vector_seconds <= 0.0
        else scalar_seconds / vector_seconds
    )

    numerical_gate = max_abs_error <= 1e-12 and checksum_error <= 1e-8
    verdict = (
        "PASS_NUMERICAL_EQUIVALENCE_CANDIDATE"
        if (
            numerical_gate
            and same_nearest_index
            and same_farthest_index
        )
        else "FAIL_NUMERICAL_EQUIVALENCE_CANDIDATE"
    )

    return {
        "schema": SCHEMA,
        "fixture": {
            "candidate_count": candidate_count,
            "repeats": repeats,
            "dimension": DIM,
            "dtype": "float64",
        },
        "summary": {
            "max_abs_error": max_abs_error,
            "mean_abs_error": mean_abs_error,
            "checksum_error": checksum_error,
            "same_nearest_index": same_nearest_index,
            "same_farthest_index": same_farthest_index,
            "scalar_seconds": scalar_seconds,
            "vector_seconds": vector_seconds,
            "observed_microkernel_speedup": observed_microkernel_speedup,
            "routing_enabled": False,
            "selection_equivalence_proven": False,
            "end_to_end_speedup_claim": False,
            "two_hundred_x_end_to_end_claim": False,
        },
        "verdict": verdict,
        "claim_scope": (
            "NUMERICAL_AND_MICROKERNEL_RESULT_FOR_THIS_SYNTHETIC_DISTANCE_FIXTURE_ONLY; "
            "VECTOR KERNEL IS NOT ENABLED IN ROUTING; NOT END_TO_END SPEEDUP"
        ),
        "authority": {
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        },
    }


def main() -> int:
    receipt = run_benchmark()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt["summary"], sort_keys=True))
    print(f"verdict={receipt['verdict']}")
    print(f"claim_scope={receipt['claim_scope']}")
    print(f"receipt={OUT}")
    return 0 if receipt["verdict"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
