from __future__ import annotations

from gremlin_mcp.constitutional_surface_registry import manifest
from tools.gremlin_runtime_constitutional_proof_v01 import (
    audit_runtime_constitutional_coverage,
)


def test_runtime_registry_is_explicit_and_has_25_declared_surfaces() -> None:
    row = manifest()
    assert row["schema"] == "GREMLIN_CONSTITUTIONAL_RUNTIME_SURFACE_REGISTRY_V0_1"
    assert row["surface_count"] == 25
    assert row["registry_is_explicit_policy"] is True
    assert row["registry_exhaustiveness_proven"] is False


def test_every_declared_runtime_mutation_is_constitutionally_guarded_before_mutation() -> None:
    receipt = audit_runtime_constitutional_coverage()
    summary = receipt["summary"]
    assert summary["declared_surface_count"] == 25
    assert summary["constitutional_covered_count"] == 25
    assert summary["constitutional_gap_count"] == 0
    assert summary["coverage_fraction"] == 1.0
    assert summary["coverage_complete"] is True

    for row in receipt["rows"]:
        assert row["present"] is True, row
        assert row["packet_argument_present"] is True, row
        assert row["guard_count"] == 1, row
        assert row["guard_before_first_mutation"] is True, row
        assert row["guard_endpoint_exact"] is True, row
        assert row["guard_consequence_exact"] is True, row
        assert row["guard_packet_argument_exact"] is True, row
        assert row["all_declared_mutation_calls_found"] is True, row
        assert row["status"] == "CONSTITUTIONALLY_COVERED", row


def test_runtime_coverage_proof_does_not_overclaim_registry_exhaustiveness() -> None:
    summary = audit_runtime_constitutional_coverage()["summary"]
    assert summary["registry_exhaustiveness_proven"] is False
    assert summary["whole_repository_mutation_reachability_proven"] is False
