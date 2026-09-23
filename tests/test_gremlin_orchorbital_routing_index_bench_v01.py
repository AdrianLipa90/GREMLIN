from __future__ import annotations

from tools.gremlin_orchorbital_routing_index_bench_v01 import run_benchmark


def test_same_species_orchorbital_index_exceeds_200x_candidate_scan_reduction() -> None:
    receipt = run_benchmark(
        target_tasks=4,
        unrelated_tasks=2048,
    )
    summary = receipt["summary"]

    assert receipt["verdict"] == "PASS_SAME_SPECIES_ORCHORBITAL_INDEX_REDUCTION"
    assert summary["same_species_fixture"] is True
    assert summary["naive_same_species_scan_candidates_proxy"] == 2052
    assert summary["scheduler_task_views"] <= 8
    assert summary["indexed_candidate_count"] == summary["scheduler_task_views"]
    assert summary["indexed_local_count"] == 4
    assert summary["fairness_candidate_count"] <= 4
    assert summary["structural_scan_reduction_ratio"] > 200.0
    assert summary["candidate_inspection_reduction_fraction"] > 0.99
    assert summary["exact_target_orbit_only"] is True
    assert summary["no_cross_orbit_claim"] is True
    assert summary["context_ancestry_index_active"] is True
    assert summary["selected_smallest_warm_bucket"] is True
    assert summary["actual_wall_clock_speedup_claim"] is False
    assert summary["end_to_end_speedup_claim"] is False
    assert summary["two_hundred_x_end_to_end_claim"] is False


def test_same_species_routing_index_benchmark_is_deterministic_in_structural_metrics() -> None:
    first = run_benchmark(target_tasks=3, unrelated_tasks=99)
    second = run_benchmark(target_tasks=3, unrelated_tasks=99)

    keys = (
        "scheduler_task_views",
        "naive_same_species_scan_candidates_proxy",
        "indexed_candidate_count",
        "indexed_local_count",
        "fairness_candidate_count",
        "avoided_candidate_inspections",
        "candidate_inspection_reduction_fraction",
        "structural_scan_reduction_ratio",
        "exact_target_orbit_only",
        "no_cross_orbit_claim",
        "context_ancestry_index_active",
        "selected_smallest_warm_bucket",
    )
    for key in keys:
        assert first["summary"][key] == second["summary"][key]


def test_cold_receiver_keeps_full_same_species_candidate_semantics() -> None:
    # The benchmark itself is warm-context by construction. This assertion
    # protects claim scope: it must never describe the structural ratio as an
    # end-to-end or wall-clock speedup.
    receipt = run_benchmark(target_tasks=2, unrelated_tasks=16)
    summary = receipt["summary"]

    assert "WARM_CONTEXT_FIXTURE_ONLY" in receipt["claim_scope"]
    assert summary["actual_wall_clock_speedup_claim"] is False
    assert summary["end_to_end_speedup_claim"] is False
