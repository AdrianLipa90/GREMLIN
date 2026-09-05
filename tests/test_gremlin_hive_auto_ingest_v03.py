from __future__ import annotations

import pytest

from gremlin_mcp.hive_authority import HiveAuthorityRuntime
from gremlin_mcp.hive_ingest import (
    PHASE_BASIS,
    commitment_phase,
    ingest_research_execution,
    observation_priority,
)


def _result() -> dict:
    return {
        "schema": "GREMLIN_RESEARCH_EXECUTOR_V0_1",
        "version": "0.1.2",
        "mode": "BUILTIN_REFERENCE_BESTIARY_EXECUTOR",
        "query": "orbital hive benchmark",
        "status": "CANDIDATE_SYNTHESIS_READY",
        "execution_commitment": "exec-commit-001",
        "citations": [
            {
                "source_id": "SRC-A",
                "content_commitment": "content-A",
            },
            {
                "source_id": "SRC-B",
                "content_commitment": "content-B",
            },
        ],
        "stage_executions": [
            {
                "stage_id": "STAGE-1",
                "route_commitment": "route-001",
                "results": [
                    {
                        "species": "HOUND",
                        "task_id": "hound-1",
                        "task_commitment": "task-hound-1",
                        "result_commitment": "result-hound-1",
                        "candidate": {
                            "species": "HOUND",
                            "epistemic_status": "ADVERSARIAL_AUDIT",
                            "contradictions": ["counterexample:1"],
                            "provider_errors": [],
                        },
                    },
                    {
                        "species": "MOLE",
                        "task_id": "mole-1",
                        "task_commitment": "task-mole-1",
                        "result_commitment": "result-mole-1",
                        "candidate": {
                            "species": "MOLE",
                            "epistemic_status": "STRUCTURAL_DERIVATION_CANDIDATE",
                            "candidate_concept_path": ["a", "b"],
                        },
                    },
                ],
            }
        ],
        "synthesis": {
            "status": "CANDIDATE",
            "result_commitment": "result-belzebub-1",
            "result": {
                "species": "BELZEBUB",
                "epistemic_status": "CANDIDATE_SYNTHESIS",
                "answer": "candidate only",
            },
        },
        "authority": {
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        },
    }


def test_commitment_phase_is_deterministic_bounded_reference_only() -> None:
    first = commitment_phase("abc")
    second = commitment_phase("abc")
    assert first == second
    assert 0.0 <= first < 2.0 * 3.141592653589793
    assert PHASE_BASIS == "COMMITMENT_REFERENCE_PHASE_NOT_PHYSICAL"


def test_operational_priority_places_hound_inside_mole() -> None:
    assert observation_priority("HOUND") > observation_priority("MOLE")
    assert observation_priority("HOUND", {"contradictions": ["x"]}) <= 1.0


def test_ingest_creates_execution_specialists_and_synthesis_without_latch() -> None:
    runtime = HiveAuthorityRuntime()
    summary = ingest_research_execution(runtime, _result())

    assert summary["created_count"] == 4
    assert summary["existing_count"] == 0
    assert summary["automatic_latch"] is False
    assert summary["phase_basis"] == PHASE_BASIS

    table = runtime.table()
    assert len(table) == 4
    assert all(record.state == "OPEN" for record in table)
    assert all(record.seal_receipt is None for record in table)
    assert all(record.authority == "SHARED_COGNITION_ONLY" for record in table)

    hound = runtime.head("research:exec-commit-001:specialist:hound-1")
    mole = runtime.head("research:exec-commit-001:specialist:mole-1")
    assert hound.coordinate.radius < mole.coordinate.radius
    assert hound.payload["phase_basis"] == PHASE_BASIS

    synthesis = runtime.head("research:exec-commit-001:synthesis")
    assert "result:result-hound-1" in synthesis.dependencies
    assert "result:result-mole-1" in synthesis.dependencies


def test_same_execution_is_idempotent() -> None:
    runtime = HiveAuthorityRuntime()
    first = ingest_research_execution(runtime, _result())
    second = ingest_research_execution(runtime, _result())

    assert first["created_count"] == 4
    assert second["created_count"] == 0
    assert second["existing_count"] == 4
    assert len(runtime.table()) == 4
    assert len(runtime.history("research:exec-commit-001:execution")) == 1


def test_same_subject_with_different_content_fails_closed() -> None:
    runtime = HiveAuthorityRuntime()
    ingest_research_execution(runtime, _result())
    changed = _result()
    changed["query"] = "mutated query under same commitment"

    with pytest.raises(RuntimeError, match="different content"):
        ingest_research_execution(runtime, changed)


def test_root_dependencies_preserve_source_content_commitments() -> None:
    runtime = HiveAuthorityRuntime()
    ingest_research_execution(runtime, _result())
    root = runtime.head("research:exec-commit-001:execution")
    assert root.dependencies == ("content-A", "content-B")
