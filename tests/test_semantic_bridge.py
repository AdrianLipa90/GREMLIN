from __future__ import annotations

import gremlin_mcp.semantic_bridge as bridge
from gremlin_mcp.evidence_robustness import CONTRADICT, CONTRADICTION_DETECTED_UNRESOLVED, SUPPORT
from gremlin_mcp.research_provenance import source_receipt_commitment
from gremlin_mcp.semantic_evidence import (
    UNRESOLVED,
    FixtureAssignment,
    FixtureSemanticEvidenceProducer,
    run_producer,
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


def _citation(receipt):
    return {
        "source_id": receipt["source_id"],
        "provider": "fixture",
        "title": f"Fixture {receipt['source_id']}",
        "url": f"https://example.org/{receipt['source_id']}",
        "doi": None,
        "published": "2026-08-30",
        "content_basis": receipt["content_basis"],
        "content_commitment": receipt["content_commitment"],
    }


def _execution():
    receipts = [
        _receipt("src-a", "The observation supports the claim."),
        _receipt("src-b", "The independent analysis contradicts the claim."),
        _receipt("src-u", "The available text is insufficient to resolve the claim."),
    ]
    return {
        "schema": "GREMLIN_RESEARCH_EXECUTOR_V0_1",
        "version": "0.1.2",
        "query": "test query",
        "status": "CANDIDATE_SYNTHESIS_READY",
        "synthesis": {"state": "DONE", "species": "BELZEBUB", "result": {"answer": "candidate"}},
        "citations": [_citation(row) for row in receipts],
        "source_receipts": receipts,
        "authority": {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False},
    }


def _all_unresolved_assignments():
    return [
        FixtureAssignment("src-a", "journal-a", "The observation supports the claim.", UNRESOLVED, 0.3),
        FixtureAssignment("src-b", "journal-b", "The independent analysis contradicts the claim.", UNRESOLVED, 0.4),
        FixtureAssignment("src-u", "journal-u", "The available text is insufficient to resolve the claim.", UNRESOLVED, 1.0),
    ]


def _support_plus_unresolved_assignments():
    return [
        FixtureAssignment("src-a", "journal-a", "The observation supports the claim.", SUPPORT, 0.8),
        FixtureAssignment("src-b", "journal-b", "The independent analysis contradicts the claim.", UNRESOLVED, 0.2),
        FixtureAssignment("src-u", "journal-u", "The available text is insufficient to resolve the claim.", UNRESOLVED, 1.0),
    ]


def test_resolved_support_and_contradict_flow_into_hound_guard_with_complete_coverage():
    execution = _execution()
    producer = FixtureSemanticEvidenceProducer(
        [
            FixtureAssignment("src-a", "journal-a", "The observation supports the claim.", SUPPORT, 0.8),
            FixtureAssignment("src-b", "journal-b", "The independent analysis contradicts the claim.", CONTRADICT, 0.9),
            FixtureAssignment("src-u", "journal-u", "The available text is insufficient to resolve the claim.", UNRESOLVED, 1.0),
        ]
    )
    output = run_producer(producer, claim_id="claim-x", source_receipts=execution["source_receipts"])
    result = bridge.apply_semantic_producer_output(execution, producer_output=output)
    assert result["status"] == CONTRADICTION_DETECTED_UNRESOLVED
    assert result["synthesis"] is None
    assert result["quarantined_synthesis"] is not None
    assert result["claim_evidence_guard"]["assessment"]["contradiction_detected"] is True
    semantic = result["semantic_evidence"]
    assert semantic["validation"]["valid"] is True
    assert semantic["coverage"]["complete"] is True
    assert semantic["coverage"]["coverage_rate"] == 1.0
    assert semantic["resolved_count"] == 2
    assert semantic["unresolved_count"] == 1


def test_partial_semantic_coverage_quarantines_instead_of_treating_missing_sources_as_neutral():
    execution = _execution()
    producer = FixtureSemanticEvidenceProducer(
        [FixtureAssignment("src-a", "journal-a", "The observation supports the claim.", SUPPORT, 0.8)]
    )
    output = run_producer(producer, claim_id="claim-partial", source_receipts=execution["source_receipts"])
    result = bridge.apply_semantic_producer_output(execution, producer_output=output)
    assert result["status"] == bridge.SEMANTIC_COVERAGE_INCOMPLETE
    assert result["synthesis"] is None
    assert result["quarantined_synthesis"] is not None
    coverage = result["semantic_evidence"]["coverage"]
    assert coverage["complete"] is False
    assert coverage["coverage_rate"] == 1 / 3
    assert coverage["missing_source_ids"] == ["src-b", "src-u"]
    assert coverage["unclassified_source_policy"] == "QUARANTINE_NOT_NEUTRAL"


def test_all_unresolved_with_complete_coverage_quarantines_instead_of_silently_releasing_synthesis():
    execution = _execution()
    producer = FixtureSemanticEvidenceProducer(_all_unresolved_assignments())
    output = run_producer(producer, claim_id="claim-u", source_receipts=execution["source_receipts"])
    result = bridge.apply_semantic_producer_output(execution, producer_output=output)
    assert result["status"] == bridge.SEMANTIC_EVIDENCE_UNRESOLVED
    assert result["synthesis"] is None
    assert result["quarantined_synthesis"] is not None
    assert result["semantic_evidence"]["synthesis_authorized"] is False
    assert result["semantic_evidence"]["coverage"]["complete"] is True
    assert result["semantic_evidence"]["validation"]["normalized"]["unresolved_count"] == 3


def test_tampered_derived_guard_evidence_is_rejected_before_coverage_or_guard_execution():
    execution = _execution()
    producer = FixtureSemanticEvidenceProducer(_support_plus_unresolved_assignments())
    output = run_producer(producer, claim_id="claim-t", source_receipts=execution["source_receipts"])
    output["guard_evidence"][0]["stance"] = CONTRADICT
    result = bridge.apply_semantic_producer_output(execution, producer_output=output)
    assert result["status"] == bridge.SEMANTIC_PRODUCER_OUTPUT_INVALID
    assert result["synthesis"] is None
    errors = result["semantic_evidence"]["validation"]["errors"]
    assert "GUARD_EVIDENCE_DERIVATION_MISMATCH" in errors


def test_producer_envelope_identity_mismatch_is_rejected():
    execution = _execution()
    producer = FixtureSemanticEvidenceProducer(_support_plus_unresolved_assignments())
    output = run_producer(producer, claim_id="claim-p", source_receipts=execution["source_receipts"])
    output["producer"]["producer_id"] = "different-producer"
    result = bridge.apply_semantic_producer_output(execution, producer_output=output)
    assert result["status"] == bridge.SEMANTIC_PRODUCER_OUTPUT_INVALID
    assert "PRODUCER_ID_ENVELOPE_MISMATCH" in result["semantic_evidence"]["validation"]["errors"]


def test_support_plus_explicit_unresolved_can_pass_to_candidate_but_never_canon():
    execution = _execution()
    producer = FixtureSemanticEvidenceProducer(_support_plus_unresolved_assignments())
    output = run_producer(producer, claim_id="claim-s", source_receipts=execution["source_receipts"])
    result = bridge.apply_semantic_producer_output(execution, producer_output=output)
    assert result["synthesis"] is not None
    assert result["claim_evidence_guard"]["assessment"]["candidate_stance"] == SUPPORT
    assert result["semantic_evidence"]["coverage"]["complete"] is True
    assert result["semantic_evidence"]["external_semantic_provider_executed"] is False
    assert result["semantic_evidence"]["fixture_semantics_claimed_as_real"] is False
    assert result["authority"]["canon_allowed"] is False


def test_strict_coverage_can_only_be_disabled_explicitly():
    execution = _execution()
    producer = FixtureSemanticEvidenceProducer(
        [FixtureAssignment("src-a", "journal-a", "The observation supports the claim.", SUPPORT, 0.8)]
    )
    output = run_producer(producer, claim_id="claim-nonstrict", source_receipts=execution["source_receipts"])
    result = bridge.apply_semantic_producer_output(
        execution,
        producer_output=output,
        require_complete_coverage=False,
    )
    assert result["synthesis"] is not None
    assert result["semantic_evidence"]["coverage"]["complete"] is False
    assert result["authority"]["canon_allowed"] is False


def test_execute_wrapper_uses_strict_coverage_by_default_without_network(monkeypatch):
    execution = _execution()
    monkeypatch.setattr(bridge, "execute_research", lambda *args, **kwargs: execution)
    partial = FixtureSemanticEvidenceProducer(
        [FixtureAssignment("src-a", "journal-a", "The observation supports the claim.", SUPPORT, 0.8)]
    )
    result = bridge.execute_research_with_semantic_producer(
        "test query",
        claim_id="claim-wrapper",
        producer=partial,
        providers=["fixture"],
    )
    assert result["status"] == bridge.SEMANTIC_COVERAGE_INCOMPLETE
    assert result["synthesis"] is None
    assert result["semantic_evidence"]["validation"]["valid"] is True
    assert result["semantic_evidence"]["external_semantic_provider_executed"] is False


def test_execute_wrapper_passes_complete_fixture_coverage_without_network(monkeypatch):
    execution = _execution()
    monkeypatch.setattr(bridge, "execute_research", lambda *args, **kwargs: execution)
    producer = FixtureSemanticEvidenceProducer(_support_plus_unresolved_assignments())
    result = bridge.execute_research_with_semantic_producer(
        "test query",
        claim_id="claim-wrapper-full",
        producer=producer,
        providers=["fixture"],
    )
    assert result["synthesis"] is not None
    assert result["semantic_evidence"]["coverage"]["complete"] is True
    assert result["semantic_evidence"]["external_semantic_provider_executed"] is False
