from __future__ import annotations

import pytest

from gremlin_mcp.claim_proposition import (
    AFFIRM,
    ASSERTED,
    NEGATE,
    POSSIBLE,
    build_proposition,
    compare_propositions,
    scan_proposition_conflicts,
    verify_proposition,
)
from gremlin_mcp.evidence_robustness import SUPPORT
from gremlin_mcp.research_provenance import source_receipt_commitment
from gremlin_mcp.semantic_evidence import build_classification


def _receipt(source_id: str, excerpt: str) -> dict[str, object]:
    evidence_text = f"Source {source_id}. {excerpt} Additional context remains untrusted evidence."
    receipt: dict[str, object] = {
        "source_id": source_id,
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": f"content:{source_id}:v1",
        "content_length_chars": len(evidence_text),
        "evidence_text": evidence_text,
    }
    receipt["source_receipt_commitment"] = source_receipt_commitment(receipt)
    return receipt


def _classification(receipt, excerpt):
    return build_classification(
        claim_id="claim-1",
        source_receipt=receipt,
        source_family=f"family:{receipt['source_id']}",
        excerpt=excerpt,
        stance=SUPPORT,
        confidence=0.9,
        producer_id="fixture-producer",
        producer_version="0.1",
        model_id=None,
        mode="FIXTURE_ONLY_NO_SEMANTIC_INFERENCE",
    )


def _frame(source_id, excerpt, *, predicate="DESCRIBES", polarity=AFFIRM, modality=ASSERTED, object="geometry"):
    receipt = _receipt(source_id, excerpt)
    classification = _classification(receipt, excerpt)
    frame = build_proposition(
        classification=classification,
        claim_id="claim-1",
        source_receipts=[receipt],
        subject="Information",
        predicate=predicate,
        object=object,
        polarity=polarity,
        modality=modality,
        extraction_mode="FIXTURE_EXPLICIT_TYPED_SPO",
    )
    return receipt, classification, frame


def test_relation_verb_remains_first_class_predicate_operator():
    _, _, frame = _frame("src-a", "Information describes geometry in the stated model.")
    assert frame["normalized_predicate"] == "DESCRIBES"
    assert frame["normalized_subject"] == "information"
    assert frame["normalized_object"] == "geometry"
    assert frame["directionality"] == "EXPLICIT_TYPED_SUBJECT_PREDICATE_OBJECT"
    assert frame["epistemic_status"] == "CANDIDATE_PROPOSITION_FRAME"


def test_names_is_preserved_as_operator_not_merged_into_entity_nodes():
    receipt = _receipt("src-name", "The agent names the entity Zosia in this context.")
    classification = _classification(receipt, "The agent names the entity Zosia in this context.")
    frame = build_proposition(
        classification=classification,
        claim_id="claim-1",
        source_receipts=[receipt],
        subject="agent",
        predicate="NAMES",
        object="Zosia",
        polarity=AFFIRM,
    )
    assert frame["normalized_predicate"] == "NAMES"
    assert frame["normalized_object"] == "zosia"
    assert frame["semantic_equivalence_policy"] == "EXACT_NORMALIZED_FRAME_ONLY_NO_SYNONYM_INFERENCE"


def test_exact_same_frame_opposite_asserted_polarity_is_conflict_candidate():
    _, _, support = _frame("src-a", "Information describes geometry in the stated model.", polarity=AFFIRM)
    _, _, contradict = _frame("src-b", "Information does not describe geometry in the stated model.", polarity=NEGATE)
    result = compare_propositions(support, contradict)
    assert result["status"] == "DIRECT_EXACT_FRAME_POLARITY_CONFLICT_CANDIDATE"
    assert result["logical_conflict_candidate"] is True
    assert result["semantic_equivalence_inferred"] is False
    assert result["object_exclusivity_inferred"] is False


def test_possible_opposite_polarity_does_not_become_direct_logical_contradiction():
    _, _, asserted = _frame("src-a", "Information describes geometry in the stated model.", polarity=AFFIRM)
    _, _, possible = _frame(
        "src-b",
        "Information may fail to describe geometry in some extension.",
        polarity=NEGATE,
        modality=POSSIBLE,
    )
    result = compare_propositions(asserted, possible)
    assert result["status"] == "POLARITY_DIFF_BUT_MODALITY_BLOCKS_DIRECT_CONTRADICTION"
    assert result["logical_conflict_candidate"] is False


def test_different_predicate_is_not_conflated_by_semantic_guessing():
    _, _, describes = _frame("src-a", "Information describes geometry in the stated model.", predicate="DESCRIBES")
    _, _, causes = _frame(
        "src-b",
        "Information does not cause geometry in the stated model.",
        predicate="CAUSES",
        polarity=NEGATE,
    )
    result = compare_propositions(describes, causes)
    assert result["status"] == "DISTINCT_PROPOSITION_FRAMES"
    assert result["logical_conflict_candidate"] is False


def test_tampered_proposition_is_rejected_fail_closed():
    _, _, frame = _frame("src-a", "Information describes geometry in the stated model.")
    frame["polarity"] = NEGATE
    validation = verify_proposition(frame)
    assert validation["valid"] is False
    assert "PROPOSITION_COMMITMENT_MISMATCH" in validation["errors"]
    comparison = compare_propositions(frame, frame)
    assert comparison["status"] == "INVALID_PROPOSITION_FAIL_CLOSED"
    assert comparison["logical_conflict_candidate"] is False


def test_invalid_semantic_classification_cannot_be_promoted_to_proposition():
    excerpt = "Information describes geometry in the stated model."
    receipt = _receipt("src-a", excerpt)
    classification = _classification(receipt, excerpt)
    classification["content_commitment"] = "tampered"
    with pytest.raises(ValueError, match="classification failed integrity validation"):
        build_proposition(
            classification=classification,
            claim_id="claim-1",
            source_receipts=[receipt],
            subject="information",
            predicate="DESCRIBES",
            object="geometry",
            polarity=AFFIRM,
        )


def test_scan_reports_only_exact_modality_gated_conflict_candidates():
    _, _, a = _frame("src-a", "Information describes geometry in the stated model.", polarity=AFFIRM)
    _, _, b = _frame("src-b", "Information does not describe geometry in the stated model.", polarity=NEGATE)
    _, _, c = _frame(
        "src-c",
        "Information may fail to describe geometry in an extension.",
        polarity=NEGATE,
        modality=POSSIBLE,
    )
    scan = scan_proposition_conflicts([a, b, c])
    assert scan["frame_count"] == 3
    assert scan["comparison_count"] == 3
    assert scan["direct_exact_frame_conflict_candidate_count"] == 1
    assert scan["policy"] == "EXACT_SPO_POLARITY_ONLY_MODALITY_GATED_NO_SEMANTIC_EQUIVALENCE_INFERENCE"
