from __future__ import annotations

import heapq
import json
from pathlib import Path
from typing import Any, Iterable

from tools.gremlin_orchorbital_local_join_span_bench_v01 import (
    rotating_straggler_costs,
)

OUT = Path("provenance/GREMLIN_ORCHORBITAL_FINITE_WORKER_SPAN_BENCHMARK_V0_1.json")
SCHEMA = "GREMLIN_ORCHORBITAL_FINITE_WORKER_SPAN_BENCHMARK_V0_1"


def _positive_int(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _worker_counts(values: Iterable[int], maximum: int) -> tuple[int, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError("worker_counts must be an iterable of integers")
    out: list[int] = []
    for raw in values:
        value = _positive_int(raw, "worker_count")
        if value > maximum:
            raise ValueError("worker_count cannot exceed branch count in this fixture")
        if value not in out:
            out.append(value)
    if not out:
        raise ValueError("worker_counts must be non-empty")
    return tuple(sorted(out))


def _stage_makespan(
    costs: list[float],
    *,
    workers: int,
    start: float,
) -> float:
    """Deterministic work-conserving LPT list scheduling for one barrier stage."""

    worker_heap = [(start, worker_id) for worker_id in range(workers)]
    heapq.heapify(worker_heap)
    tasks = sorted(
        enumerate(costs),
        key=lambda row: (-row[1], row[0]),
    )
    max_finish = start
    for branch, cost in tasks:
        available, worker_id = heapq.heappop(worker_heap)
        finish = available + cost
        heapq.heappush(worker_heap, (finish, worker_id))
        max_finish = max(max_finish, finish)
    return max_finish


def global_barrier_span(
    costs: list[list[float]],
    *,
    workers: int,
) -> float:
    branches = len(costs)
    stages = len(costs[0])
    current = 0.0
    for stage in range(stages):
        current = _stage_makespan(
            [costs[branch][stage] for branch in range(branches)],
            workers=workers,
            start=current,
        )
    return current


def local_dependency_schedule(
    costs: list[list[float]],
    *,
    workers: int,
) -> dict[str, float]:
    """Finite-worker list schedule for independent per-branch precedence chains."""

    branches = len(costs)
    stages = len(costs[0])
    releases: list[tuple[float, int, int]] = [
        (0.0, branch, 0) for branch in range(branches)
    ]
    heapq.heapify(releases)
    worker_heap = [(0.0, worker_id) for worker_id in range(workers)]
    heapq.heapify(worker_heap)
    ready: list[tuple[float, float, int, int]] = []
    branch_completion = [0.0] * branches
    scheduled = 0
    total_tasks = branches * stages

    while scheduled < total_tasks:
        available, worker_id = heapq.heappop(worker_heap)
        while releases and releases[0][0] <= available:
            release, branch, stage = heapq.heappop(releases)
            heapq.heappush(
                ready,
                (-costs[branch][stage], release, branch, stage),
            )

        if not ready:
            if not releases:
                raise RuntimeError("finite-worker scheduler has no ready or released task")
            available = max(available, releases[0][0])
            while releases and releases[0][0] <= available:
                release, branch, stage = heapq.heappop(releases)
                heapq.heappush(
                    ready,
                    (-costs[branch][stage], release, branch, stage),
                )

        negative_cost, release, branch, stage = heapq.heappop(ready)
        cost = -negative_cost
        start = max(available, release)
        finish = start + cost
        if stage + 1 < stages:
            heapq.heappush(releases, (finish, branch, stage + 1))
        else:
            branch_completion[branch] = finish
        heapq.heappush(worker_heap, (finish, worker_id))
        scheduled += 1

    return {
        "span": max(branch_completion),
        "mean_completion": sum(branch_completion) / branches,
        "first_completion": min(branch_completion),
    }


def run_benchmark(
    *,
    branches: int = 256,
    stages: int = 256,
    fast_cost: float = 1.0,
    straggler_cost: float = 1000.0,
    worker_counts: tuple[int, ...] = (1, 8, 32, 64, 128, 192, 224, 240, 248, 252, 256),
) -> dict[str, Any]:
    branches = _positive_int(branches, "branches")
    stages = _positive_int(stages, "stages")
    counts = _worker_counts(worker_counts, branches)
    costs = rotating_straggler_costs(
        branches=branches,
        stages=stages,
        fast_cost=fast_cost,
        straggler_cost=straggler_cost,
    )
    total_work = sum(sum(row) for row in costs)

    rows: list[dict[str, Any]] = []
    for workers in counts:
        global_span = global_barrier_span(costs, workers=workers)
        local = local_dependency_schedule(costs, workers=workers)
        local_span = local["span"]
        rows.append(
            {
                "workers": workers,
                "global_barrier_span": global_span,
                "local_join_span": local_span,
                "local_mean_completion": local["mean_completion"],
                "local_first_completion": local["first_completion"],
                "span_ratio": global_span / local_span,
                "mean_completion_ratio": global_span / local["mean_completion"],
                "work_lower_bound": total_work / workers,
                "local_efficiency_vs_work_bound": (
                    (total_work / workers) / local_span
                ),
            }
        )

    by_workers = {row["workers"]: row for row in rows}
    single = by_workers.get(1)
    full = by_workers.get(branches)
    if single is None or full is None:
        raise ValueError(
            "worker_counts must include both 1 and branch-count for control gates"
        )
    single_worker_control = abs(single["span_ratio"] - 1.0) <= 1e-15
    full_width_matches_unlimited = (
        full["local_join_span"]
        == max(sum(row) for row in costs)
    )

    first_over_200 = next(
        (
            row["workers"]
            for row in rows
            if row["span_ratio"] > 200.0
        ),
        None,
    )
    verdict = (
        "PASS_FINITE_WORKER_LOCAL_JOIN_MODEL"
        if single_worker_control and full_width_matches_unlimited
        else "FAIL_FINITE_WORKER_LOCAL_JOIN_MODEL"
    )

    return {
        "schema": SCHEMA,
        "fixture": {
            "pattern": "ROTATING_STAGE_STRAGGLER",
            "branches": branches,
            "stages": stages,
            "fast_cost": fast_cost,
            "straggler_cost": straggler_cost,
            "worker_counts": list(counts),
            "scheduler": "DETERMINISTIC_WORK_CONSERVING_LPT_LIST_SCHEDULING",
        },
        "summary": {
            "total_work": total_work,
            "single_worker_span_ratio": single["span_ratio"],
            "full_width_span_ratio": full["span_ratio"],
            "first_worker_count_over_200x_span_ratio": first_over_200,
            "single_worker_control_exact": single_worker_control,
            "full_width_matches_unlimited_local_span": full_width_matches_unlimited,
            "finite_worker_capacity_modeled": True,
            "scheduler_overhead_modeled": False,
            "communication_overhead_modeled": False,
            "wall_clock_speedup_claim": False,
            "end_to_end_speedup_claim": False,
            "two_hundred_x_end_to_end_claim": False,
        },
        "rows": rows,
        "verdict": verdict,
        "claim_scope": (
            "DETERMINISTIC FINITE-WORKER SCHEDULING MODEL FOR THE LISTED SYNTHETIC "
            "ROTATING-STRAGGLER FIXTURE. RATIOS ARE MODELED MAKESPAN RATIOS, NOT "
            "OBSERVED WALL-CLOCK OR END-TO-END SPEEDUP."
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
