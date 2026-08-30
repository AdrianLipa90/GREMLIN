from __future__ import annotations

import gremlin_mcp.research_executor as executor
from gremlin_mcp.research_provenance import verify_source_receipt_set


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
            "summary": "The geometry describes an entropy relation and connects it with gravity.",
        },
        {
            "provider": "arxiv",
            "title": "Information geometry, entropy and emergent gravity",
            "url": "https://arxiv.org/abs/2601.00001v2",
            "published": "2026-01-03T00:00:00Z",
            "summary": "A revised model describes the geometry and relates entropy to gravity.",
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
    assert "DESCRIBES" in candidate["observed_relation_operators"]
    assert "CONNECTS" in candidate["observed_relation_operators"]
    assert "RELATES" in candidate["observed_relation_operators"]
    assert candidate["relation_directionality"] == "UNRESOLVED_PENDING_SENTENCE_OR_FULL_TEXT_PARSE"
    assert candidate["equation_status"] == "UNRESOLVED_FROM_METADATA"
    assert candidate["contradiction_status"] == "TEXT_LEVEL_CHECK_REQUIRED"
    assert candidate["authority"]["canon_allowed"] is False
    assert len(result["citations"]) == 4
    assert all(row["source_id"].startswith("SRC-") for row in result["citations"])
    assert len(result["source_receipts"]) == 4
    receipts = {row["source_id"]: row for row in result["source_receipts"]}
    for citation in result["citations"]:
        receipt = receipts[citation["source_id"]]
        assert len(citation["content_commitment"]) == 64
        assert citation["content_commitment"] == receipt["content_commitment"]
        assert receipt["content_length_chars"] == len(receipt["evidence_text"])
        assert len(receipt["source_receipt_commitment"]) == 64
    provenance = verify_source_receipt_set(result["source_receipts"], citations=result["citations"])
    assert provenance["valid"] is True
    assert provenance["errors"] == []
    assert provenance["receipt_count"] == 4
    assert provenance["citation_count"] == 4
    assert len(provenance["receipt_set_commitment"]) == 64
    assert len(result["execution_commitment"]) == 64

    spider = result["stage_executions"][0]["results"][1]["candidate"]
    operators = {row["operator"] for row in spider["relation_predicates"]}
    assert {"DESCRIBES", "CONNECTS", "RELATES"} <= operators
    assert all(row["directionality"] == "UNRESOLVED_FROM_TERM_LEVEL_EXTRACTION" for row in spider["relation_edges"])

    hound = result["stage_executions"][-1]["results"][0]["candidate"]
    assert hound["species"] == "HOUND"
    assert len(hound["version_or_duplicate_clusters"]) == 1
    assert hound["contradictions"] == []
    assert any(row["target"] == "SUBJECT_PREDICATE_OBJECT_PARSE" for row in hound["test_targets"])


def test_execute_research_fails_closed_without_evidence(monkeypatch) -> None:
    monkeypatch.setattr(executor, "research", lambda *args, **kwargs: _fake_acquisition(with_evidence=False))
    result = executor.execute_research("derive relation", providers=["crossref"])
    assert result["status"] == "NO_EVIDENCE_FAIL_CLOSED"
    assert result["stage_executions"] == []
    assert result["synthesis"] is None
    assert result["citations"] == []
    assert result["source_receipts"] == []
    provenance = verify_source_receipt_set(result["source_receipts"], citations=result["citations"])
    assert provenance["valid"] is True
    assert result["authority"]["canon_allowed"] is False
