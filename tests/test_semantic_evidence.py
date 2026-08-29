from __future__ import annotations

import pytest

from gremlin_mcp.evidence_robustness import CONTRADICT, SUPPORT
from gremlin_mcp.research_provenance import source_receipt_commitment
from gremlin_mcp.semantic_evidence import (
    UNRESOLVED,
    FixtureAssignment,
    FixtureSemanticEvidenceProducer,
    build_classification,
    normalize_producer_output,
    run_producer,
    verify_classification,
)


def _receipt(source_id: str, text: str | None = None) -> dict[str, object]:
    evidence_text = text or f"Source {source_id}. The measured relation supports the candidate claim."
    receipt: dict[str, object] = {
        "source_id": source_id,
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": f"content:{source_id}:v1",
        "content_length_chars": len(evidence_text),
        "evidence_text": evidence_text,
    }
    receipt["source_receipt_commitment"] = source_receipt_commitment(receipt)
    return receipt


def _classification(receipt, *, stance=SUPPORT, excerpt=None, source_family="family-a"):
    text = excerpt or "The measured relation supports the candidate claim."
    return build_classification(
        claim_id="claim-1",
        source_receipt=receipt,
        source_family=source_family,
        excerpt=text,
        stance=stance,
        confidence=0.91,
        producer_id="fixture-producer",
        producer_version="0.1",
        model_id=None,
        mode="FIXTURE_ONLY_NO_SEMANTIC_INFERENCE",
    )


def test_fixture_producer_preserves_unresolved_without_coercion():
    support = _receipt("src-support")
    unresolved = _receipt("src-unresolved", "Source unresolved. The available text is insufficient to decide the claim.")
    producer = FixtureSemanticEvidenceProducer(
        [
            FixtureAssignment(
                source_id="src-support",
                source_family="journal-a",
                excerpt="The measured relation supports the candidate claim.",
                stance=SUPPORT,
                confidence=0.88,
            ),
            FixtureAssignment(
                source_id="src-unresolved",
                source_family="journal-b",
                excerpt="The available text is insufficient to decide the claim.",
                stance=UNRESOLVED,
                confidence=0.97,
            ),
        ]
    )
    result = run_producer(producer, claim_id="claim-1", source_receipts=[support, unresolved])
    assert result["status"] == "VALID"
    assert result["resolved_count"] == 1
    assert result["unresolved_count"] == 1
    assert len(result["guard_evidence"]) == 1
    assert result["guard_evidence"][0]["stance"] == SUPPORT
    assert result["unresolved_classifications"][0]["stance"] == UNRESOLVED
    assert result["unresolved_policy"] == "PRESERVE_NOT_COERCE"
    assert result["external_semantic_provider_executed"] is False
    assert result["fixture_semantics_claimed_as_real"] is False


def test_stance_tamper_after_classification_commitment_is_rejected():
    receipt = _receipt("src-a")
    classification = _classification(receipt)
    classification["stance"] = CONTRADICT
    validation = verify_classification(classification, claim_id="claim-1", source_receipts=[receipt])
    assert validation["valid"] is False
    assert "CLASSIFICATION_COMMITMENT_MISMATCH" in validation["errors"]


def test_excerpt_must_exist_in_exact_source_receipt():
    receipt = _receipt("src-a")
    with pytest.raises(ValueError, match="literal substring"):
        build_classification(
            claim_id="claim-1",
            source_receipt=receipt,
            source_family="family-a",
            excerpt="This sentence does not exist in the source receipt.",
            stance=SUPPORT,
            confidence=0.5,
            producer_id="fixture-producer",
            producer_version="0.1",
            model_id=None,
            mode="FIXTURE_ONLY_NO_SEMANTIC_INFERENCE",
        )


def test_content_commitment_tamper_is_rejected():
    receipt = _receipt("src-a")
    classification = _classification(receipt)
    classification["content_commitment"] = "content:other"
    validation = verify_classification(classification, claim_id="claim-1", source_receipts=[receipt])
    assert validation["valid"] is False
    assert "CONTENT_COMMITMENT_MISMATCH" in validation["errors"]
    assert "CLASSIFICATION_COMMITMENT_MISMATCH" in validation["errors"]


def test_authority_escalation_is_rejected():
    receipt = _receipt("src-a")
    classification = _classification(receipt)
    classification["authority"]["canon_allowed"] = True
    validation = verify_classification(classification, claim_id="claim-1", source_receipts=[receipt])
    assert validation["valid"] is False
    assert "INVALID_AUTHORITY_ESCALATION" in validation["errors"]


def test_duplicate_claim_source_classification_fails_closed():
    receipt = _receipt("src-a")
    a = _classification(receipt, stance=SUPPORT)
    b = _classification(receipt, stance=CONTRADICT)
    result = normalize_producer_output(
        claim_id="claim-1",
        source_receipts=[receipt],
        classifications=[a, b],
    )
    assert result["status"] == "INVALID_FAIL_CLOSED"
    assert result["invalid_count"] >= 1
    assert result["guard_evidence"] == []
    assert result["classifications"] == []


def test_unresolved_high_confidence_never_becomes_support_or_contradict():
    receipt = _receipt("src-u", "Source u. The text is ambiguous and does not resolve the requested claim.")
    classification = build_classification(
        claim_id="claim-1",
        source_receipt=receipt,
        source_family="family-u",
        excerpt="The text is ambiguous and does not resolve the requested claim.",
        stance=UNRESOLVED,
        confidence=1.0,
        producer_id="fixture-producer",
        producer_version="0.1",
        model_id=None,
        mode="FIXTURE_ONLY_NO_SEMANTIC_INFERENCE",
    )
    result = normalize_producer_output(
        claim_id="claim-1",
        source_receipts=[receipt],
        classifications=[classification],
    )
    assert result["status"] == "VALID"
    assert result["resolved_count"] == 0
    assert result["unresolved_count"] == 1
    assert result["guard_evidence"] == []
