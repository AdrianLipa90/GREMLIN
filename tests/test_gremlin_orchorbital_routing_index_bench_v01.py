from __future__ import annotations

from tools.gremlin_orchorbital_routing_index_bench_v01 import run_benchmark


def test_indexed_routing_exceeds_200x_candidate_scan_reduction_on_skewed_fixture() -> None:
    receipt = run_benchmark(
        target_tasks=4,
        unrelated_tasks=2048,
    )
    summary = receipt["summary"]

    assert receipt["verdict"] == "PASS_INDEXED_ROUTING_SCAN_REDUCTION"
    assert summary["scheduler_task_views"] == 4
    assert summary["naive_global_scan_candidates_proxy"] == 2052
    assert summary["structural_scan_reduction_ratio"] > 200.0
    assert summary["candidate_inspection_reduction_fraction"] > 0.99
    assert summary["exact_target_species_only"] is True
    assert summary["no_cross_species_claim"] is True
    assert summary["actual_wall_clock_speedup_claim"] is False
    assert summary["end_to_end_speedup_claim"] is False
    assert summary["two_hundred_x_end_to_end_claim"] is False


def test_indexed_routing_benchmark_is_deterministic_in_structural_metrics() -> None:
    first = run_benchmark(target_tasks=3, unrelated_tasks=99)
    second = run_benchmark(target_tasks=3, unrelated_tasks=99)

    keys = (
        "scheduler_task_views",
        "naive_global_scan_candidates_proxy",
        "avoided_candidate_inspections",
        "candidate_inspection_reduction_fraction",
        "structural_scan_reduction_ratio",
        "exact_target_species_only",
        "no_cross_species_claim",
    )
    for key in keys:
        assert first["summary"][key] == second["summary"][key]
