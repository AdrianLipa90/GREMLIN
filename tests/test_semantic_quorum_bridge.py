from __future__ import annotations

from gremlin_mcp.evidence_robustness import SUPPORT
from gremlin_mcp.research_provenance import source_receipt_commitment
from gremlin_mcp.semantic_evidence import UNRESOLVED, FixtureAssignment, FixtureSemanticEvidenceProducer, run_producer
from gremlin_mcp.semantic_quorum_bridge import (
    SEMANTIC_FAMILY_QUORUM_INSUFFICIENT,
    apply_semantic_producer_output_with_quorum,
)


def _receipt(source_id: str, sentence: str) -> dict[str, object]:
    text = f"Source {source_id}. {sentence}"
    receipt: dict[str, object] = {
        "source_id": source_id,
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": f"content:{source_id}:v1",
        "content_length_chars": len(text),
        "evidence_text": text,
    }
    receipt["source_receipt_commitment"] = source_receipt_commitment(receipt)
    return receipt


def _citation(receipt, *, doi=None, url=None):
    return {
        "source_id": receipt["source_id"],
        "provider": "fixture",
        "title": f"Fixture source {receipt['source_id']} evidence record",
        "url": url or f"https://example.org/{receipt['source_id']}",
        "doi": doi,
        "published": "2026-08-30",
        "content_basis": receipt["content_basis"],
        "content_commitment": receipt["content_commitment"],
    }


def _execution(*, shared_doi=False):
    receipts = [
        _receipt("src-a", "The first observation supports the claim."),
        _receipt("src-b", "The second observation supports the claim."),
        _receipt("src-u", "The available text is unresolved."),
    ]
    doi = "10.1234/shared-work" if shared_doi else None
    citations = [
        _citation(receipts[0], doi=doi),
        _citation(receipts[1], doi=doi),
        _citation(receipts[2]),
    ]
    return {
        "schema": "GREMLIN_RESEARCH_EXECUTOR_V0_1",
        "version": "0.1.2",
        "query": "test query",
        "status": "CANDIDATE_SYNTHESIS_READY",
        "synthesis": {"state": "DONE", "species": "BELZEBUB", "result": {"answer": "candidate"}},
        "citations": citations,
        "source_receipts": receipts,
        "authority": {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False},
    }


def _producer_two_supports():
    return FixtureSemanticEvidenceProducer(
        [
            FixtureAssignment("src-a", "producer-family-a", "The first observation supports the claim.", SUPPORT, 0.95),
            FixtureAssignment("src-b", "producer-family-b", "The second observation supports the claim.", SUPPORT, 0.99),
            FixtureAssignment("src-u", "producer-family-u", "The available text is unresolved.", UNRESOLVED, 1.0),
        ]
    )


def test_two_distinct_execution_families_allow_candidate_synthesis():
    execution = _execution(shared_doi=False)
    output = run_producer(_producer_two_supports(), claim_id="claim-q1", source_receipts=execution["source_receipts"])
    result = apply_semantic_producer_output_with_quorum(
        execution,
        producer_output=output,
        min_unipolar_families=2,
    )
    assert result["synthesis"] is not None
    quorum = result["semantic_evidence"]["family_quorum"]
    assert quorum["quorum_satisfied"] is True
    assert quorum["support_family_count"] >= 2
    assert result["authority"]["canon_allowed"] is False


def test_two_source_ids_for_same_doi_collapse_to_one_family_and_quarantine():
    execution = _execution(shared_doi=True)
    output = run_producer(_producer_two_supports(), claim_id="claim-q2", source_receipts=execution["source_receipts"])
    result = apply_semantic_producer_output_with_quorum(
        execution,
        producer_output=output,
        min_unipolar_families=2,
    )
    assert result["status"] == SEMANTIC_FAMILY_QUORUM_INSUFFICIENT
    assert result["synthesis"] is None
    assert result["quarantined_synthesis"] is not None
    quorum = result["semantic_evidence"]["family_quorum"]
    assert quorum["support_family_count"] == 1
    family_binding = result["semantic_evidence"]["provenance_families"]
    assert family_binding["producer_family_authority"] == "NONE"
    assert len(family_binding["producer_family_overrides"]) >= 2


def test_single_support_plus_unresolved_is_quarantined_under_strict_quorum():
    execution = _execution(shared_doi=False)
    producer = FixtureSemanticEvidenceProducer(
        [
            FixtureAssignment("src-a", "producer-family-a", "The first observation supports the claim.", SUPPORT, 0.999),
            FixtureAssignment("src-b", "producer-family-b", "The second observation supports the claim.", UNRESOLVED, 0.2),
            FixtureAssignment("src-u", "producer-family-u", "The available text is unresolved.", UNRESOLVED, 1.0),
        ]
    )
    output = run_producer(producer, claim_id="claim-q3", source_receipts=execution["source_receipts"])
    result = apply_semantic_producer_output_with_quorum(execution, producer_output=output)
    assert result["status"] == SEMANTIC_FAMILY_QUORUM_INSUFFICIENT
    assert result["synthesis"] is None
    assert result["semantic_evidence"]["family_quorum"]["support_family_count"] == 1
