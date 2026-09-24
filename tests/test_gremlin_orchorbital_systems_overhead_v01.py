from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools.gremlin_orchorbital_systems_overhead_v01 import (
    ROOT,
    SIZES,
    TOPOLOGIES,
    benchmark_cell,
    topology_plan,
    validate_checkout,
)


def test_topology_plans_are_deterministic_and_dependency_ordered() -> None:
    for topology in TOPOLOGIES:
        for n in SIZES:
            first = topology_plan(topology, n)
            second = topology_plan(topology, n)
            assert first == second
            assert len(first.node_ids) == n
            assert len(set(first.node_ids)) == n
            assert set(first.close_order) == set(first.node_ids)
            order = {node_id: i for i, node_id in enumerate(first.close_order)}
            for consumer, dependency in first.causal_edges:
                assert order[dependency] < order[consumer]


def test_known_edge_counts_for_small_topologies() -> None:
    assert len(topology_plan("chain", 10).causal_edges) == 9
    assert len(topology_plan("wide", 10).causal_edges) == 9
    assert len(topology_plan("diamond", 10).causal_edges) == 16
    assert len(topology_plan("layered", 10).causal_edges) == 7


def test_real_fabric_smoke_cell_has_zero_external_io_and_clean_run_timer() -> None:
    row = benchmark_cell("chain", 10, warmups=0, samples=1)
    assert row["status"] == "PASS"
    assert row["workload_nodes"] == 10
    assert row["model_calls"] == 0
    assert row["network_calls"] == 0
    assert row["tool_io_calls"] == 0
    assert row["invariant_checks_enabled"] is True
    assert row["post_run_audit_inside_timed_run"] is False
    assert set(row["phases"]) == {
        "build",
        "snapshot",
        "commitment",
        "checkpoint",
        "restore",
        "state_transition_run",
    }
    for phase in row["phases"].values():
        assert len(phase["raw_ns"]) == 1
        assert phase["median_ms"] >= 0


def test_invalid_expected_commit_sha_fails_closed() -> None:
    with pytest.raises(ValueError, match="expected_commit_sha"):
        validate_checkout(ROOT, "not-a-sha")


def test_checkout_binding_matches_real_clean_head_when_checkout_is_clean() -> None:
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    if proc.stdout.strip():
        pytest.skip("checkout is dirty; clean-binding test is intentionally skipped")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    binding = validate_checkout(ROOT, head)
    assert binding["git_head"] == head
    assert binding["git_head_verified"] is True
    assert binding["working_tree_clean"] is True
