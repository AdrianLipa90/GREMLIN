from __future__ import annotations

from benchmarks.gremlin_full_system_v01 import (
    _semantic_regression_summary,
    run_constitution_ablation,
    run_constitution_microbench,
    run_fault_injection_matrix,
    run_ledger_scaling,
)
from benchmarks.gremlin_memory_governance_v01 import (
    run_durable_hive_benchmark,
    run_ferret_governance_benchmark,
    run_memory_convergence_benchmark,
    run_raphael_governance_benchmark,
)
from tools.gremlin_runtime_constitutional_proof_v01 import (
    audit_runtime_constitutional_coverage,
)


def test_constitution_ablation_exposes_every_removed_guard_channel() -> None:
    result = run_constitution_ablation()
    assert result["pass"] is True
    assert result["exact_invariants"]["all_pass_is_allow"] is True
    assert result["exact_invariants"]["every_nonpass_case_not_allow"] is True
    assert result["exact_invariants"]["each_single_channel_ablation_exposes_false_allow"] is True
    for row in result["ablations"].values():
        assert row["false_allows"] >= 1


def test_fault_injection_matrix_is_exact() -> None:
    result = run_fault_injection_matrix()
    assert result["pass"] is True
    assert result["failed_count"] == 0
    assert result["passed_count"] == result["case_count"]
    assert result["case_count"] >= 10


def test_runtime_coverage_theorem_is_reused_by_benchmark() -> None:
    receipt = audit_runtime_constitutional_coverage()
    summary = receipt["summary"]
    assert summary["declared_surface_count"] == 26
    assert summary["constitutional_covered_count"] == 26
    assert summary["constitutional_gap_count"] == 0
    assert summary["coverage_fraction"] == 1.0
    assert summary["coverage_complete"] is True


def test_constitution_microbench_executes_without_semantic_drift() -> None:
    result = run_constitution_microbench(repetitions=50)
    assert result["admission"]["count"] == 50
    assert result["capability_validation"]["count"] == 50
    assert result["runtime_request_guard"]["count"] == 50
    assert result["transition_certificate"]["count"] >= 50
    for key in (
        "admission",
        "capability_validation",
        "runtime_request_guard",
        "transition_certificate",
    ):
        assert result[key]["median_ns"] > 0
        assert result[key]["p95_ns"] >= result[key]["min_ns"]


def test_ledger_scaling_preserves_every_event() -> None:
    result = run_ledger_scaling()
    rows = result["rows"]
    assert [row["events"] for row in rows] == [1, 10, 100, 1000, 5000]
    assert all(row["all_events_preserved"] for row in rows)
    assert all(row["join_ns"] > 0 for row in rows)


def test_memory_convergence_transfers_exact_missing_set() -> None:
    result = run_memory_convergence_benchmark(sizes=(8, 32))
    assert result["pass"] is True
    assert result["exact_invariants"]["all_delta_transfers_equal_missing_set"] is True
    assert result["exact_invariants"]["all_receivers_converge"] is True
    for row in result["rows"]:
        assert row["delta_transfer_count"] == row["expected_missing_items"]
        assert row["divergent_bucket_count_after"] == 0


def test_durable_hive_reopens_without_record_loss() -> None:
    result = run_durable_hive_benchmark(sizes=(8, 32))
    assert result["pass"] is True
    assert result["exact_invariants"]["all_records_recovered"] is True
    assert result["exact_invariants"]["all_modes_sqlite_wal"] is True
    for row in result["rows"]:
        assert row["recovered_record_count"] == row["records"]


def test_raphael_success_and_rollback_lanes_are_exact() -> None:
    result = run_raphael_governance_benchmark(repetitions=5)
    assert result["pass"] is True
    assert result["success_lane"]["exact_success_count"] == 5
    assert result["rollback_lane"]["exact_rollback_count"] == 5
    assert result["exact_invariants"]["all_successes_expire_authority"] is True
    assert result["exact_invariants"]["all_bad_operation_receipts_rollback"] is True


def test_ferret_single_use_lane_is_exact() -> None:
    result = run_ferret_governance_benchmark(repetitions=5)
    assert result["pass"] is True
    assert result["success_lane"]["exact_success_count"] == 5
    assert result["replay_lane"]["exact_replay_block_count"] == 5
    assert result["exact_invariants"]["all_valid_actions_execute_once"] is True
    assert result["exact_invariants"]["all_authorization_replays_blocked"] is True


def test_legacy_magic_thresholds_cannot_control_aggregate_readiness() -> None:
    existing = {
        "research_orchestrator_v0_2": {
            "gremlin": {
                "precision": 1.0,
                "recall": 1.0,
                "exact_route_rate": 1.0,
                "stage_exact_rate": 1.0,
            },
            "comparison": {"fanout_reduction_fraction": 0.01},
        },
        "ood_routing_v0_6": {
            "semantic": {"fp": 0, "fn": 0, "exact_rate": 1.0},
            "ambiguity_false_additions": 0,
            "fanout": {"reduction_fraction": 0.01},
            "all_gates_pass": False,
        },
        "bestiary_virtual_topology_v0_1": {
            "throughput_speedup": 1.0,
            "candidate_threshold": 10.0,
            "candidate": False,
        },
        "geometry_phase_scheduler_v0_1": {
            "summary": {
                "transition_reduction_vs_fifo_proxy": 0.0,
                "noise_reduction_vs_fifo_proxy": 0.0,
                "lexical_overlap_gain": 0.0,
                "topic_purity_gain": 0.0,
                "context_pack_advantage_vs_fifo_proxy": 0.0,
            },
            "verdict": "FAIL_SYNTHETIC_GEOMETRY_SCHEDULING",
        },
        "phasenav_numpy_v0_1": {
            "summary": {
                "max_scalar_vector_torus_error": 1.0,
                "all_species_scalar_vector_equivalent_1e_12": False,
            }
        },
    }
    result = _semantic_regression_summary(existing)
    assert result["semantic_regression_pass"] is True
    assert result["legacy_report_only"]["ood_legacy_threshold_gate"]["controls_readiness"] is False
    assert result["legacy_report_only"]["bestiary_legacy_10x_candidate"]["controls_readiness"] is False
    assert result["legacy_report_only"]["scheduler_legacy_threshold_verdict"]["controls_readiness"] is False
    assert result["legacy_report_only"]["phasenav_legacy_1e_12_equivalence"]["controls_readiness"] is False
    assert result["open_numeric_bindings"]["phasenav_roundoff_bound"]["status"] == "OPEN"
