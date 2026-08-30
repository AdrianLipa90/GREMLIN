from __future__ import annotations

from gremlin_mcp.evidence_kind import (
    EMPIRICAL,
    PRIMARY_EXPERIMENT,
    REVIEW_META,
    build_evidence_kind_assignment,
)
from gremlin_mcp.evidence_robustness import SUPPORT
from gremlin_mcp.research_provenance import source_receipt_commitment
from gremlin_mcp.semantic_evidence import FixtureAssignment, FixtureSemanticEvidenceProducer, run_producer
from gremlin_mcp.semantic_kind_bridge import (
    SEMANTIC_CLAIM_MODE_UNKNOWN,
    SEMANTIC_EVIDENCE_KIND_ASSIGNMENT_INVALID,
    SEMANTIC_EVIDENCE_KIND_POLICY_INSUFFICIENT,
    apply_semantic_producer_output_with_kind_policy,
)


def _receipt(source_id: str, sentence: str) -> dict:
    text = f"Source {source_id}. {sentence}"
    receipt = {
        "source_id": source_id,
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": f"content:{source_id}:v1",
        "content_length_chars": len(text),
        "evidence_text": text,
    }
    receipt["source_receipt_commitment"] = source_receipt_commitment(receipt)
    return receipt


def _execution():
    receipts = [
        _receipt("src-a", "Direct measurement supports the claim."),
        _receipt("src-b", "Independent review discusses support for the claim."),
    ]
    citations = [
        {
            "source_id": receipts[0]["source_id"],
            "provider": "fixture",
            "title": "Primary evidence record alpha",
            "url": "https://alpha.example.org/work-a",
            "doi": "10.1000/work-a",
            "published": "2026-08-30",
            "content_basis": receipts[0]["content_basis"],
            "content_commitment": receipts[0]["content_commitment"],
        },
        {
            "source_id": receipts[1]["source_id"],
            "provider": "fixture",
            "title": "Review evidence record beta",
            "url": "https://beta.example.org/work-b",
            "doi": "10.2000/work-b",
            "published": "2026-08-30",
            "content_basis": receipts[1]["content_basis"],
            "content_commitment": receipts[1]["content_commitment"],
        },
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


def _semantic_output(execution, claim_id):
    producer = FixtureSemanticEvidenceProducer(
        [
            FixtureAssignment(
                "src-a",
                "untrusted-family-a",
                "Direct measurement supports the claim.",
                SUPPORT,
                0.96,
            ),
            FixtureAssignment(
                "src-b",
                "untrusted-family-b",
                "Independent review discusses support for the claim.",
                SUPPORT,
                0.95,
            ),
        ]
    )
    return run_producer(
        producer,
        claim_id=claim_id,
        source_receipts=execution["source_receipts"],
    )


def _kind(receipt, evidence_kind):
    return build_evidence_kind_assignment(
        source_receipt=receipt,
        evidence_kind=evidence_kind,
        producer_id="fixture-evidence-kind-producer",
        producer_version="0.1.0",
        mode="FIXTURE_ONLY_EXPLICIT_KIND_ASSIGNMENT",
    )


def test_empirical_review_only_quarantines_after_family_quorum_passes():
    execution = _execution()
    producer_output = _semantic_output(execution, "claim-kind-a")
    assignments = [
        _kind(execution["source_receipts"][0], REVIEW_META),
        _kind(execution["source_receipts"][1], REVIEW_META),
    ]
    result = apply_semantic_producer_output_with_kind_policy(
        execution,
        producer_output=producer_output,
        evidence_kind_assignments=assignments,
        claim_mode=EMPIRICAL,
        min_unipolar_families=2,
        min_direct_families=1,
    )
    assert result["status"] == SEMANTIC_EVIDENCE_KIND_POLICY_INSUFFICIENT
    assert result["synthesis"] is None
    assert result["quarantined_synthesis"] is not None
    assert result["semantic_evidence"]["family_quorum"]["quorum_satisfied"] is True
    assert result["semantic_evidence"]["evidence_kind_policy"]["direct_family_count"] == 0


def test_empirical_primary_plus_review_passes_kind_policy_after_two_family_quorum():
    execution = _execution()
    producer_output = _semantic_output(execution, "claim-kind-b")
    assignments = [
        _kind(execution["source_receipts"][0], PRIMARY_EXPERIMENT),
        _kind(execution["source_receipts"][1], REVIEW_META),
    ]
    result = apply_semantic_producer_output_with_kind_policy(
        execution,
        producer_output=producer_output,
        evidence_kind_assignments=assignments,
        claim_mode=EMPIRICAL,
    )
    assert result["synthesis"] is not None
    assert result["semantic_evidence"]["family_quorum"]["quorum_satisfied"] is True
    assert result["semantic_evidence"]["evidence_kind_policy"]["policy_satisfied"] is True
    assert result["authority"]["canon_allowed"] is False


def test_tampered_kind_assignment_quarantines_before_kind_policy():
    execution = _execution()
    producer_output = _semantic_output(execution, "claim-kind-c")
    first = _kind(execution["source_receipts"][0], PRIMARY_EXPERIMENT)
    first["content_commitment"] = "tampered-content"
    assignments = [first, _kind(execution["source_receipts"][1], REVIEW_META)]
    result = apply_semantic_producer_output_with_kind_policy(
        execution,
        producer_output=producer_output,
        evidence_kind_assignments=assignments,
        claim_mode=EMPIRICAL,
    )
    assert result["status"] == SEMANTIC_EVIDENCE_KIND_ASSIGNMENT_INVALID
    assert result["synthesis"] is None
    invalid = result["semantic_evidence"]["evidence_kind_assignments"]["invalid"]
    assert invalid


def test_unknown_claim_mode_quarantines_even_when_direct_evidence_exists():
    execution = _execution()
    producer_output = _semantic_output(execution, "claim-kind-d")
    assignments = [
        _kind(execution["source_receipts"][0], PRIMARY_EXPERIMENT),
        _kind(execution["source_receipts"][1], REVIEW_META),
    ]
    result = apply_semantic_producer_output_with_kind_policy(
        execution,
        producer_output=producer_output,
        evidence_kind_assignments=assignments,
        claim_mode=None,
    )
    assert result["status"] == SEMANTIC_CLAIM_MODE_UNKNOWN
    assert result["synthesis"] is None
