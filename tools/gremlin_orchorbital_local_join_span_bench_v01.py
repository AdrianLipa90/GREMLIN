from __future__ import annotations

import json
from pathlib import Path
from typing import Any

OUT = Path("provenance/GREMLIN_ORCHORBITAL_LOCAL_JOIN_SPAN_BENCHMARK_V0_1.json")
SCHEMA = "GREMLIN_ORCHORBITAL_LOCAL_JOIN_SPAN_BENCHMARK_V0_1"


def _positive_int(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _positive_cost(value: float, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    out = float(value)
    if out <= 0.0:
        raise ValueError(f"{field} must be positive")
    return out


def rotating_straggler_costs(
    *,
    branches: int,
    stages: int,
    fast_cost: float,
    straggler_cost: float,
) -> list[list[float]]:
    """Each stage has one slow branch; the slow branch rotates by stage."""

    return [
        [
            straggler_cost if branch == stage % branches else fast_cost
            for stage in range(stages)
        ]
        for branch in range(branches)
    ]


def uniform_costs(
    *,
    branches: int,
    stages: int,
    cost: float,
) -> list[list[float]]:
    return [[cost for _ in range(stages)] for _ in range(branches)]


def evaluate_schedule(costs: list[list[float]]) -> dict[str, Any]:
    if not costs or not costs[0]:
        raise ValueError("cost matrix must be non-empty")
    stages = len(costs[0])
    if any(len(row) != stages for row in costs):
        raise ValueError("cost matrix must be rectangular")
    if any(value <= 0.0 for row in costs for value in row):
        raise ValueError("all costs must be positive")

    branches = len(costs)
    total_work = sum(sum(row) for row in costs)

    # Legacy wave/global-barrier schedule:
    # no branch may enter stage k+1 until every branch completed stage k.
    stage_barriers = [
        max(costs[branch][stage] for branch in range(branches))
        for stage in range(stages)
    ]
    global_barrier_span = sum(stage_barriers)

    # Orchorbital local-join schedule:
    # each branch advances as soon as its own local prerequisite closes.
    branch_completion = [sum(row) for row in costs]
    local_join_span = max(branch_completion)
    local_first_completion = min(branch_completion)
    local_mean_completion = sum(branch_completion) / branches

    structural_span_ratio = global_barrier_span / local_join_span
    mean_completion_ratio = global_barrier_span / local_mean_completion
    first_completion_ratio = global_barrier_span / local_first_completion

    return {
        "branches": branches,
        "stages": stages,
        "total_work": total_work,
        "global_barrier_span": global_barrier_span,
        "local_join_span": local_join_span,
        "local_first_completion": local_first_completion,
        "local_mean_completion": local_mean_completion,
        "structural_span_ratio": structural_span_ratio,
        "mean_completion_ratio": mean_completion_ratio,
        "first_completion_ratio": first_completion_ratio,
        "same_total_work": True,
        "global_barrier_count": max(0, stages - 1),
        "local_global_barrier_count": 0,
        "local_join_semantics": True,
        "unlimited_parallelism_model": True,
        "scheduler_overhead_modeled": False,
        "communication_overhead_modeled": False,
        "worker_capacity_modeled": False,
        "wall_clock_speedup_claim": False,
        "end_to_end_speedup_claim": False,
        "two_hundred_x_end_to_end_claim": False,
    }


def run_benchmark(
    *,
    branches: int = 256,
    stages: int = 256,
    fast_cost: float = 1.0,
    straggler_cost: float = 1000.0,
) -> dict[str, Any]:
    branches = _positive_int(branches, "branches")
    stages = _positive_int(stages, "stages")
    fast_cost = _positive_cost(fast_cost, "fast_cost")
    straggler_cost = _positive_cost(straggler_cost, "straggler_cost")
    if straggler_cost < fast_cost:
        raise ValueError("straggler_cost must be >= fast_cost")

    rotating = evaluate_schedule(
        rotating_straggler_costs(
            branches=branches,
            stages=stages,
            fast_cost=fast_cost,
            straggler_cost=straggler_cost,
        )
    )
    uniform = evaluate_schedule(
        uniform_costs(
            branches=branches,
            stages=stages,
            cost=fast_cost,
        )
    )

    expected_local_span = (
        (stages // branches) * straggler_cost
        + (stages - stages // branches) * fast_cost
    )
    if stages % branches:
        # Some branches receive one extra rotating straggler. The maximum
        # branch completion therefore includes ceil(stages / branches).
        slow_count = (stages + branches - 1) // branches
        expected_local_span = (
            slow_count * straggler_cost
            + (stages - slow_count) * fast_cost
        )
    expected_global_span = stages * straggler_cost

    arithmetic_exact = (
        rotating["global_barrier_span"] == expected_global_span
        and rotating["local_join_span"] == expected_local_span
    )
    uniform_control_exact = (
        abs(uniform["structural_span_ratio"] - 1.0) <= 1e-15
        and uniform["global_barrier_span"] == uniform["local_join_span"]
    )
    verdict = (
        "PASS_LOCAL_JOIN_STRUCTURAL_SPAN_MODEL"
        if (
            arithmetic_exact
            and uniform_control_exact
            and rotating["same_total_work"]
            and rotating["global_barrier_count"] == max(0, stages - 1)
            and rotating["local_global_barrier_count"] == 0
        )
        else "FAIL_LOCAL_JOIN_STRUCTURAL_SPAN_MODEL"
    )

    return {
        "schema": SCHEMA,
        "fixture": {
            "pattern": "ROTATING_STAGE_STRAGGLER",
            "branches": branches,
            "stages": stages,
            "fast_cost": fast_cost,
            "straggler_cost": straggler_cost,
        },
        "rotating_straggler": rotating,
        "uniform_control": uniform,
        "summary": {
            "same_total_work": rotating["same_total_work"],
            "global_barrier_span": rotating["global_barrier_span"],
            "local_join_span": rotating["local_join_span"],
            "structural_span_ratio": rotating["structural_span_ratio"],
            "mean_completion_ratio": rotating["mean_completion_ratio"],
            "first_completion_ratio": rotating["first_completion_ratio"],
            "global_barriers_removed": rotating["global_barrier_count"],
            "uniform_control_span_ratio": uniform["structural_span_ratio"],
            "arithmetic_exact": arithmetic_exact,
            "uniform_control_exact": uniform_control_exact,
            "wall_clock_speedup_claim": False,
            "end_to_end_speedup_claim": False,
            "two_hundred_x_end_to_end_claim": False,
        },
        "verdict": verdict,
        "claim_scope": (
            "DETERMINISTIC WORK_SPAN MODEL WITH UNLIMITED PARALLELISM; SAME TASK "
            "WORK UNDER GLOBAL-STAGE BARRIERS VS LOCAL PER-BRANCH DEPENDENCIES. "
            "STRUCTURAL SPAN RATIO ONLY; NOT OBSERVED WALL-CLOCK OR END-TO-END SPEEDUP."
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
