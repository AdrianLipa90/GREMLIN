from __future__ import annotations

import pytest

from tools.gremlin_orchorbital_finite_worker_span_bench_v01 import (
    global_barrier_span,
    local_dependency_schedule,
    run_benchmark,
)


def test_finite_worker_fixture_exposes_capacity_requirement_for_200x_span() -> None:
    receipt = run_benchmark()
    summary = receipt["summary"]

    assert receipt["verdict"] == "PASS_FINITE_WORKER_LOCAL_JOIN_MODEL"
    assert summary["single_worker_span_ratio"] == 1.0
    assert summary["full_width_span_ratio"] > 200.0
    assert summary["first_worker_count_over_200x_span_ratio"] == 256
    assert summary["finite_worker_capacity_modeled"] is True
    assert summary["wall_clock_speedup_claim"] is False
    assert summary["end_to_end_speedup_claim"] is False
    assert summary["two_hundred_x_end_to_end_claim"] is False


def test_finite_worker_model_has_exact_single_worker_control() -> None:
    costs = [
        [9.0, 1.0, 1.0],
        [1.0, 9.0, 1.0],
        [1.0, 1.0, 9.0],
    ]
    global_span = global_barrier_span(costs, workers=1)
    local = local_dependency_schedule(costs, workers=1)

    assert global_span == pytest.approx(sum(sum(row) for row in costs))
    assert local["span"] == pytest.approx(global_span)


def test_full_branch_width_local_schedule_matches_longest_branch_chain() -> None:
    costs = [
        [10.0, 1.0, 1.0],
        [1.0, 10.0, 1.0],
        [1.0, 1.0, 10.0],
    ]
    local = local_dependency_schedule(costs, workers=3)

    assert local["span"] == pytest.approx(12.0)


def test_finite_worker_benchmark_requires_control_worker_counts() -> None:
    with pytest.raises(ValueError, match="include both 1 and branch-count"):
        run_benchmark(
            branches=8,
            stages=8,
            worker_counts=(1, 2, 4),
        )

    with pytest.raises(ValueError, match="include both 1 and branch-count"):
        run_benchmark(
            branches=8,
            stages=8,
            worker_counts=(2, 4, 8),
        )
