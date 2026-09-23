from __future__ import annotations

import pytest

from tools.gremlin_orchorbital_local_join_span_bench_v01 import (
    evaluate_schedule,
    run_benchmark,
)


def test_rotating_straggler_fixture_exceeds_200x_structural_span_without_speedup_claim() -> None:
    receipt = run_benchmark()
    summary = receipt["summary"]

    assert receipt["verdict"] == "PASS_LOCAL_JOIN_STRUCTURAL_SPAN_MODEL"
    assert summary["same_total_work"] is True
    assert summary["global_barriers_removed"] == 255
    assert summary["structural_span_ratio"] > 200.0
    assert summary["uniform_control_span_ratio"] == 1.0
    assert summary["arithmetic_exact"] is True
    assert summary["uniform_control_exact"] is True
    assert summary["wall_clock_speedup_claim"] is False
    assert summary["end_to_end_speedup_claim"] is False
    assert summary["two_hundred_x_end_to_end_claim"] is False


def test_non_divisible_rotating_fixture_has_exact_ceil_straggler_count() -> None:
    receipt = run_benchmark(
        branches=3,
        stages=5,
        fast_cost=1.0,
        straggler_cost=20.0,
    )
    summary = receipt["summary"]

    assert receipt["verdict"].startswith("PASS_")
    assert summary["global_barrier_span"] == 100.0
    assert summary["local_join_span"] == 43.0
    assert summary["structural_span_ratio"] == pytest.approx(100.0 / 43.0)


def test_uniform_schedule_is_control_with_no_structural_span_gain() -> None:
    evaluated = evaluate_schedule(
        [
            [3.0, 3.0, 3.0],
            [3.0, 3.0, 3.0],
            [3.0, 3.0, 3.0],
        ]
    )

    assert evaluated["same_total_work"] is True
    assert evaluated["global_barrier_span"] == 9.0
    assert evaluated["local_join_span"] == 9.0
    assert evaluated["structural_span_ratio"] == 1.0


def test_span_model_rejects_invalid_costs() -> None:
    with pytest.raises(ValueError, match="positive"):
        run_benchmark(fast_cost=0.0)

    with pytest.raises(ValueError, match="straggler_cost"):
        run_benchmark(fast_cost=2.0, straggler_cost=1.0)

    with pytest.raises(ValueError, match="rectangular"):
        evaluate_schedule([[1.0, 2.0], [1.0]])
