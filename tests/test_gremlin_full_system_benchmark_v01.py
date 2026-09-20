from __future__ import annotations

from benchmarks.gremlin_memory_governance_v01 import (
    run_durable_hive_benchmark,
    run_memory_convergence_benchmark,
    run_raphael_governance_benchmark,
)
from benchmarks.gremlin_full_system_v01 import (
    run_constitution_ablation,
    run_constitution_microbench,
    run_fault_injection_matrix,
    run_ledger_scaling,
)
from tools.gremlin_runtime_coverage_audit_v01 import audit_runtime_coverage


def test_constitution_ablation_exposes_every_removed_guard_channel() -> None:
    result = run_constitution_ablation()
    assert result["pass"] is True
    assert result["exact_invariants"]["full_false_allow_count_eq_0"] is True
    assert result["exact_invariants"]["full_false_deny_count_eq_0"] is True
    assert result["exact_invariants"]["all_pass_is_allow"] is True
    assert result["exact_invariants"]["each_single_channel_ablation_exposes_false_allow"] is True
    for row in result["ablations"].values():
        assert row["false_allows"] >= 1


def test_fault_injection_matrix_is_exact() -> None:
    result = run_fault_injection_matrix()
    assert result["pass"] is True
    assert result["failed_count"] == 0
    assert result["passed_count"] == result["case_count"]
    assert result["case_count"] >= 10


def test_runtime_coverage_audit_is_accounting_complete_even_when_system_is_not() -> None:
    receipt = audit_runtime_coverage()
    summary = receipt["summary"]
    assert summary["auto_discovered_high_consequence_root_count"] > 0
    assert (
        summary["constitutional_covered_count"]
        + summary["constitutional_gap_count"]
        == summary["auto_discovered_high_consequence_root_count"]
    )
    assert summary["algorithm"] == "AST_CALL_GRAPH_PATH_SENSITIVE_GUARD_BEFORE_SINK"
    assert 0.0 <= summary["coverage_fraction"] <= 1.0
    assert isinstance(summary["coverage_complete"], bool)


def test_constitution_microbench_executes_without_semantic_drift() -> None:
    result = run_constitution_microbench(repetitions=50)
    assert result["admission"]["count"] == 50
    assert result["capability_validation"]["count"] == 50
    assert result["transition_certificate"]["count"] >= 50
    for key in ("admission", "capability_validation", "transition_certificate"):
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
