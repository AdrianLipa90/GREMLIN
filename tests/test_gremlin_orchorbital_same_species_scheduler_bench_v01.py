from __future__ import annotations

from tools.gremlin_orchorbital_same_species_scheduler_bench_v01 import run_benchmark


def test_same_species_scheduler_operation_count_matches_exact_greedy_formula() -> None:
    receipt = run_benchmark(
        queued_tasks=257,
        batch_limit=32,
    )
    summary = receipt["summary"]

    assert receipt["verdict"] == "PASS_EXACT_GREEDY_WORKLOAD_ACCOUNTING"
    assert summary["greedy_pairwise_state_distance_evaluations"] == (
        summary["expected_pairwise_state_distance_evaluations"]
    )
    assert summary["greedy_phase_axis_evaluations_proxy"] == (
        summary["expected_phase_axis_evaluations_proxy"]
    )
    assert summary["precomputed_state_cache_used"] is True
    assert summary["precomputed_centroid_used"] is True
    assert summary["distance_kernel"] == "SCALAR_EXACT_V0_1"
    assert summary["actual_wall_clock_speedup_claim"] is False
    assert summary["vectorized_kernel_enabled"] is False
    assert summary["end_to_end_speedup_claim"] is False


def test_same_species_scheduler_pairwise_work_scales_with_queue_and_batch() -> None:
    small = run_benchmark(queued_tasks=64, batch_limit=8)
    large = run_benchmark(queued_tasks=256, batch_limit=32)

    assert large["summary"]["greedy_pairwise_state_distance_evaluations"] > (
        small["summary"]["greedy_pairwise_state_distance_evaluations"]
    )
    assert large["summary"]["greedy_phase_axis_evaluations_proxy"] > (
        small["summary"]["greedy_phase_axis_evaluations_proxy"]
    )
