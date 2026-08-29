from __future__ import annotations

import gremlin_mcp.research_executor as executor


def _fake_acquisition(*, with_evidence: bool = True):
    rows = [
        {
            "provider": "crossref",
            "title": "Shannon entropy and information geometry in gravity",
            "url": "https://doi.org/10.1/a",
            "doi": "10.1/a",
            "published": "2026-01-01",
        },
        {
            "provider": "arxiv",
            "title": "Information geometry, entropy and emergent gravity",
            "url": "https://arxiv.org/abs/2601.00001v1",
            "published": "2026-01-02T00:00:00Z",
            "summary": "A candidate bridge between entropy geometry and gravity is studied.",
        },
        {
            "provider": "arxiv",
            "title": "Information geometry, entropy and emergent gravity",
            "url": "https://arxiv.org/abs/2601.00001v2",
            "published": "2026-01-03T00:00:00Z",
            "summary": "A revised candidate bridge between entropy geometry and gravity is studied.",
        },
        {
            "provider": "crossref",
            "title": "Geometry and entropy constraints in gravitational systems",
            "url": "https://doi.org/10.1/b",
            "doi": "10.1/b",
            "published": "2025-12-20",
        },
    ] if with_evidence else []
    return {
        "schema": "GREMLIN_RESEARCH_ENGINE_V0_1",
        "query": "audit derive relation",
        "octopus": {"route_mask": ["OWL", "SPIDER"], "route_commitment": "a" * 64},
        "research_plan": {
            "plan_commitment": "b" * 64,
            "species_union": ["OWL", "SPIDER", "MOLE", "HOUND"],
            "stages": [
                {"stage_id": "ACQUIRE_EVIDENCE", "route_mask": ["OWL", "SPIDER"], "route_commitment": "c" * 64},
                {"stage_id": "MAP_RELATIONS", "route_mask": ["SPIDER"], "route_commitment": "d" * 64},
                {"stage_id": "DERIVE_CANDIDATE", "route_mask": ["MOLE"], "route_commitment": "e" * 64},
                {"stage_id": "ADVERSARIAL_CHECK", "route_mask": ["HOUND"], "route_commitment": "f" * 64},
            ],
        },
        "evidence": {
            "results": rows,
            "provider_errors": [],
            "evidence_commitment": "1" * 64,
            "deduped_result_count": len(rows),
        },
        "status": "EVIDENCE_READY" if rows else "NO_EVIDENCE",
        "authority": {
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        },
        "research_commitment": "2" * 64,
    }


def test_execute_research_uses_worker_abi_and_belzebub(monkeypatch) -> None:
    monkeypatch.setattr(executor, "research", lambda *args, **kwargs: _fake_acquisition())
    result = executor.execute_research(
        "audit evidence contradictions dependencies graph derive relation between entropy geometry and gravity",
        providers=["crossref", "arxiv"],
        max_sources=8,
    )

    assert result["status"] == "CANDIDATE_SYNTHESIS_READY"
    assert result["worker_abi_exercised"] is True
    assert [stage["stage_id"] for stage in result["stage_executions"]] == [
        "ACQUIRE_EVIDENCE",
        "MAP_RELATIONS",
        "DERIVE_CANDIDATE",
        "ADVERSARIAL_CHECK",
    ]
    assert all(stage["status"] == "CANDIDATE_STAGE_COMPLETE" for stage in result["stage_executions"])
    assert result["synthesis"]["state"] == "DONE"
    assert result["synthesis"]["species"] == "BELZEBUB"
    candidate = result["synthesis"]["result"]
    assert candidate["epistemic_status"] == "CANDIDATE_SYNTHESIS"
    assert candidate["candidate_bridge"]
    assert candidate["equation_status"] == "UNRESOLVED_FROM_METADATA"
    assert candidate["contradiction_status"] == "TEXT_LEVEL_CHECK_REQUIRED"
    assert candidate["authority"]["canon_allowed"] is False
    assert len(result["citations"]) == 4
    assert all(row["source_id"].startswith("SRC-") for row in result["citations"])
    assert len(result["execution_commitment"]) == 64

    hound = result["stage_executions"][-1]["results"][0]["candidate"]
    assert hound["species"] == "HOUND"
    assert len(hound["version_or_duplicate_clusters"]) == 1
    assert hound["contradictions"] == []


def test_execute_research_fails_closed_without_evidence(monkeypatch) -> None:
    monkeypatch.setattr(executor, "research", lambda *args, **kwargs: _fake_acquisition(with_evidence=False))
    result = executor.execute_research("derive relation", providers=["crossref"])
    assert result["status"] == "NO_EVIDENCE_FAIL_CLOSED"
    assert result["stage_executions"] == []
    assert result["synthesis"] is None
    assert result["citations"] == []
    assert result["authority"]["canon_allowed"] is False
