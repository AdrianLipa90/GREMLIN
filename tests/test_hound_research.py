from __future__ import annotations

import copy

import gremlin_mcp.hound_research as hound_research
from gremlin_mcp.source_family import derive_source_families


def _execution():
    title = "Information Geometry and Entropy Relations in Quantum Gravity"
    citations = [
        {
            "source_id": "v1",
            "provider": "arxiv",
            "title": title,
            "url": "https://arxiv.org/abs/2608.54321v1",
            "doi": None,
            "published": "2026-08-29",
        },
        {
            "source_id": "v2",
            "provider": "arxiv",
            "title": title,
            "url": "https://arxiv.org/abs/2608.54321v2",
            "doi": None,
            "published": "2026-08-30",
        },
        {
            "source_id": "other",
            "provider": "fixture",
            "title": "A Distinct Work On Open Quantum Geometry",
            "url": "https://example.org/other",
            "doi": None,
            "published": "2026-08-30",
        },
    ]
    return {
        "schema": "GREMLIN_RESEARCH_EXECUTOR_V0_1",
        "version": "0.1.2",
        "query": "test",
        "status": "CANDIDATE_SYNTHESIS_READY",
        "execution_commitment": "execution:exact:v1",
        "stage_executions": [
            {
                "stage_id": "ADVERSARIAL_CHECK",
                "results": [
                    {
                        "species": "HOUND",
                        "task_id": "task-hound",
                        "result_commitment": "hound-result:immutable",
                        "candidate": {"version_or_duplicate_clusters": [{"legacy": True}]},
                    }
                ],
            }
        ],
        "citations": citations,
        "synthesis": {"state": "DONE", "result_commitment": "belzebub:immutable"},
        "authority": {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False},
    }


def test_attached_hound_provenance_uses_same_family_topology_without_mutating_worker_results():
    execution = _execution()
    original_stages = copy.deepcopy(execution["stage_executions"])
    original_synthesis = copy.deepcopy(execution["synthesis"])
    expected_family = derive_source_families(execution["citations"])

    result = hound_research.attach_hound_provenance(execution)

    assert result["stage_executions"] == original_stages
    assert result["synthesis"] == original_synthesis
    assert result["hound_provenance"]["worker_result_mutation"] is False
    assert result["hound_provenance"]["family_set_commitment"] == expected_family["family_set_commitment"]
    audit = result["hound_provenance"]["provenance_audit"]
    assert audit["family_count"] == 2
    assert audit["collapsed_duplicate_or_version_count"] == 1
    assert audit["duplicate_or_version_clusters"][0]["source_ids"] == ["v1", "v2"]
    assert result["authority"]["canon_allowed"] is False


def test_no_citations_fails_closed_without_inventing_provenance():
    execution = {
        "status": "NO_EVIDENCE_FAIL_CLOSED",
        "execution_commitment": "execution:none",
        "citations": [],
        "synthesis": None,
    }
    result = hound_research.attach_hound_provenance(execution)
    audit = result["hound_provenance"]
    assert audit["status"] == "NO_CITATIONS_FAIL_CLOSED"
    assert audit["source_count"] == 0
    assert audit["family_count"] == 0
    assert audit["duplicate_or_version_clusters"] == []


def test_execute_wrapper_attaches_hound_topology_without_network(monkeypatch):
    execution = _execution()
    monkeypatch.setattr(hound_research, "execute_research", lambda *args, **kwargs: execution)
    result = hound_research.execute_research_with_hound_provenance(
        "test query",
        providers=["fixture"],
    )
    assert result["hound_provenance"]["status"] == "BOUND_TO_EXECUTION_CITATIONS"
    assert result["hound_provenance"]["execution_commitment"] == "execution:exact:v1"
    assert result["hound_provenance"]["citation_source_ids"] == ["other", "v1", "v2"]
