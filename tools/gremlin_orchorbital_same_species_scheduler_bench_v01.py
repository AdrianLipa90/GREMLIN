from __future__ import annotations

import json
import math
from pathlib import Path

from tools.gremlin_geometry_phase_scheduler_v01 import (
    DIM,
    SCHEDULER_KEY,
    queue_metrics,
    select_batch,
    task_phase_state,
)

OUT = Path("provenance/GREMLIN_ORCHORBITAL_SAME_SPECIES_SCHEDULER_BENCHMARK_V0_1.json")
SCHEMA = "GREMLIN_ORCHORBITAL_SAME_SPECIES_SCHEDULER_BENCHMARK_V0_1"


def _positive_int(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _row(index: int) -> dict[str, object]:
    phase = [
        (0.013 * index + 0.0017 * axis + 0.00003 * index * axis)
        % (2.0 * math.pi)
        for axis in range(DIM)
    ]
    return {
        "task_id": f"same-{index:05d}",
        "species": "SPIDER",
        "payload": {
            "index": index,
            SCHEDULER_KEY: {
                "phase36": phase,
                "ready": True,
                "readiness": 1.0,
                "temperature": (index % 17) / 16.0,
                "urgency": (index % 11) / 10.0,
                "noise": (index % 13) / 20.0,
            },
        },
        "task_commitment": f"commit-{index:05d}",
        "created_ns": index + 1,
    }


def run_benchmark(
    *,
    queued_tasks: int = 1024,
    batch_limit: int = 64,
) -> dict[str, object]:
    queued_tasks = _positive_int(queued_tasks, "queued_tasks")
    batch_limit = _positive_int(batch_limit, "batch_limit")
    batch_limit = min(batch_limit, queued_tasks)

    rows = [_row(index) for index in range(queued_tasks)]
    states = {
        str(row["task_id"]): task_phase_state(row)
        for row in rows
    }
    metrics = queue_metrics(
        rows,
        now_ns=10_000_000_000,
        precomputed_states=states,
    )
    selected, receipt = select_batch(
        rows,
        limit=batch_limit,
        now_ns=10_000_000_000,
        precomputed_states=states,
        precomputed_centroid=metrics["centroid"],
    )

    expected_pairwise = (
        (batch_limit - 1) * queued_tasks
        - ((batch_limit - 1) * batch_limit) // 2
    )
    measured_pairwise = int(
        receipt["greedy_pairwise_state_distance_evaluations"]
    )
    expected_axis = expected_pairwise * DIM
    measured_axis = int(receipt["greedy_phase_axis_evaluations_proxy"])

    verdict = (
        "PASS_EXACT_GREEDY_WORKLOAD_ACCOUNTING"
        if (
            len(selected) == batch_limit
            and measured_pairwise == expected_pairwise
            and measured_axis == expected_axis
            and receipt["distance_kernel"] == "SCALAR_EXACT_V0_1"
        )
        else "FAIL_EXACT_GREEDY_WORKLOAD_ACCOUNTING"
    )

    return {
        "schema": SCHEMA,
        "fixture": {
            "species": "SPIDER",
            "queued_tasks": queued_tasks,
            "batch_limit": batch_limit,
            "dimension": DIM,
            "explicit_phase36": True,
        },
        "summary": {
            "selected_count": len(selected),
            "greedy_pairwise_state_distance_evaluations": measured_pairwise,
            "expected_pairwise_state_distance_evaluations": expected_pairwise,
            "greedy_phase_axis_evaluations_proxy": measured_axis,
            "expected_phase_axis_evaluations_proxy": expected_axis,
            "precomputed_state_cache_used": receipt[
                "precomputed_state_cache_used"
            ],
            "precomputed_centroid_used": receipt[
                "precomputed_centroid_used"
            ],
            "distance_kernel": receipt["distance_kernel"],
            "actual_wall_clock_speedup_claim": False,
            "vectorized_kernel_enabled": False,
            "end_to_end_speedup_claim": False,
        },
        "verdict": verdict,
        "claim_scope": (
            "EXACT_SCALAR_GREEDY_OPERATION_COUNT_FOR_THIS_SYNTHETIC_"
            "SAME_SPECIES_FIXTURE_ONLY; NOT LATENCY OR END_TO_END SPEEDUP"
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
