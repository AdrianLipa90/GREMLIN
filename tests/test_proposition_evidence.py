from __future__ import annotations

from gremlin_mcp.claim_proposition import AFFIRM, NEGATE, verify_proposition
from gremlin_mcp.evidence_robustness import SUPPORT, UNRESOLVED as _UNUSED
from gremlin_mcp.proposition_evidence import (
    PROPOSITIONS,
    UNRESOLVED,
    FixturePropositionDecision,
    FixturePropositionProducer,
    normalize_proposition_producer_output,
    run_proposition_producer,
)
from gremlin_mcp.research_provenance import source_receipt_commitment
from gremlin_mcp.semantic_evidence import UNRESOLVED as SEMANTIC_UNRESOLVED, build_classification


def _receipt(source_id: str, excerpt: str) -> dict[str, object]:
    evidence_text = f"Source {source_id}. {excerpt} Additional context."
    receipt: dict[str, object] = {
        "source_id": source_id,
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": f"content:{source_id}:v1",
        "content_length_chars": len(evidence_text),
        "evidence_text": evidence_text,
    }
    receipt["source_receipt_commitment"] = source_receipt_commitment(receipt)
    return receipt


def _classification(receipt, excerpt, *, stance=SUPPORT):
    return build_classification(
        claim_id="claim-1",
        source_receipt=receipt,
        source_family=f"producer-family:{receipt['source_id']}",
        excerpt=excerpt,
        stance=stance,
        confidence=0.9,
        producer_id="semantic-fixture",
        producer_version="0.1",
        model_id=None,
        mode="FIXTURE_ONLY_NO_SEMANTIC_INFERENCE",
    )


def _setup_two_sources():
    excerpt_a = "Informacja opisuje geometrię w tym modelu."
    excerpt_b = "Informacja nie opisuje geometrii w tym modelu."
    receipt_a = _receipt("src-a", excerpt_a)
    receipt_b = _receipt("src-b", excerpt_b)
    class_a = _classification(receipt_a, excerpt_a)
    class_b = _classification(receipt_b, excerpt_b)
    return [receipt_a, receipt_b], [class_a, class_b]


def _frame(*, polarity=AFFIRM, subject="Informacja", predicate="DESCRIBES", object="geometria"):
    return {
        "subject": subject,
        "predicate": predicate,
        "object": object,
        "polarity": polarity,
        "modality": "ASSERTED",
    }


def test_provider_supplied_commitment_and_authority_are_ignored_and_rebuilt_locally():
    receipts, classifications = _setup_two_sources()
    decisions = [
        {
            "source_id": "src-a",
            "classification_commitment": classifications[0]["classification_commitment"],
            "decision": PROPOSITIONS,
            "frames": [
                {
                    **_frame(),
                    "proposition_commitment": "attacker-controlled",
                    "authority": {"canon_allowed": True, "execution_admitted": True},
                }
            ],
        },
        {
            "source_id": "src-b",
            "classification_commitment": classifications[1]["classification_commitment"],
            "decision": UNRESOLVED,
            "frames": [],
        },
    ]
    result = normalize_proposition_producer_output(
        claim_id="claim-1",
        classifications=classifications,
        source_receipts=receipts,
        decisions=decisions,
        producer={
            "producer_id": "untrusted-provider",
            "producer_version": "9.9",
            "model_id": "model-x",
            "mode": "EXTERNAL_CANDIDATE_PROVIDER",
        },
    )
    assert result["status"] == "VALID"
    assert result["proposition_count"] == 1
    proposition = result["propositions"][0]
    assert proposition["proposition_commitment"] != "attacker-controlled"
    assert proposition["producer_supplied_proposition_commitment_ignored"] == "attacker-controlled"
    assert proposition["producer_authority_ignored"]["canon_allowed"] is True
    assert proposition["authority"]["canon_allowed"] is False
    assert verify_proposition(proposition)["valid"] is True
    assert result["producer_commitment_authority"] == "NONE_REBUILT_LOCALLY"


def test_cross_source_classification_commitment_is_rejected_fail_closed():
    receipts, classifications = _setup_two_sources()
    decisions = [
        {
            "source_id": "src-a",
            "classification_commitment": classifications[1]["classification_commitment"],
            "decision": PROPOSITIONS,
            "frames": [_frame()],
        },
        {
            "source_id": "src-b",
            "classification_commitment": classifications[1]["classification_commitment"],
            "decision": UNRESOLVED,
            "frames": [],
        },
    ]
    result = normalize_proposition_producer_output(
        claim_id="claim-1",
        classifications=classifications,
        source_receipts=receipts,
        decisions=decisions,
        producer={"producer_id": "p", "producer_version": "1", "model_id": None, "mode": "TEST"},
    )
    assert result["status"] == "INVALID_FAIL_CLOSED"
    assert result["propositions"] == []
    assert any(
        "CLASSIFICATION_COMMITMENT_MISMATCH" in row["errors"]
        for row in result["decision_errors"]
    )


def test_partial_coverage_is_fail_closed_not_implicit_neutral():
    receipts, classifications = _setup_two_sources()
    decisions = [
        {
            "source_id": "src-a",
            "classification_commitment": classifications[0]["classification_commitment"],
            "decision": PROPOSITIONS,
            "frames": [_frame()],
        }
    ]
    result = normalize_proposition_producer_output(
        claim_id="claim-1",
        classifications=classifications,
        source_receipts=receipts,
        decisions=decisions,
        producer={"producer_id": "p", "producer_version": "1", "model_id": None, "mode": "TEST"},
        require_complete_coverage=True,
    )
    assert result["status"] == "INCOMPLETE_COVERAGE_FAIL_CLOSED"
    assert result["coverage"]["missing_source_ids"] == ["src-b"]
    assert result["propositions"] == []
    assert result["unresolved_source_ids"] == []


def test_explicit_unresolved_preserves_coverage_without_inventing_proposition():
    receipts, classifications = _setup_two_sources()
    decisions = [
        {
            "source_id": "src-a",
            "classification_commitment": classifications[0]["classification_commitment"],
            "decision": UNRESOLVED,
            "frames": [],
        },
        {
            "source_id": "src-b",
            "classification_commitment": classifications[1]["classification_commitment"],
            "decision": UNRESOLVED,
            "frames": [],
        },
    ]
    result = normalize_proposition_producer_output(
        claim_id="claim-1",
        classifications=classifications,
        source_receipts=receipts,
        decisions=decisions,
        producer={"producer_id": "p", "producer_version": "1", "model_id": None, "mode": "TEST"},
    )
    assert result["status"] == "VALID"
    assert result["coverage"]["complete"] is True
    assert result["propositions"] == []
    assert result["unresolved_source_ids"] == ["src-a", "src-b"]


def test_multiple_propositions_from_one_source_are_allowed_when_explicit():
    excerpt = "Informacja opisuje geometrię i ogranicza dynamikę."
    receipt = _receipt("src-a", excerpt)
    classification = _classification(receipt, excerpt)
    decisions = [
        {
            "source_id": "src-a",
            "classification_commitment": classification["classification_commitment"],
            "decision": PROPOSITIONS,
            "frames": [
                _frame(predicate="DESCRIBES", object="geometria"),
                _frame(predicate="CONSTRAINS", object="dynamika"),
            ],
        }
    ]
    result = normalize_proposition_producer_output(
        claim_id="claim-1",
        classifications=[classification],
        source_receipts=[receipt],
        decisions=decisions,
        producer={"producer_id": "p", "producer_version": "1", "model_id": None, "mode": "TEST"},
    )
    assert result["status"] == "VALID"
    assert result["proposition_count"] == 2
    assert [row["normalized_predicate"] for row in result["propositions"]] == ["DESCRIBES", "CONSTRAINS"]


def test_unicode_terms_survive_provider_proposal_and_local_rebuild():
    excerpt = "Sprzężenie źródła opisuje zależność geometryczną."
    receipt = _receipt("src-pl", excerpt)
    classification = _classification(receipt, excerpt)
    producer = FixturePropositionProducer(
        [
            FixturePropositionDecision(
                source_id="src-pl",
                classification_commitment=classification["classification_commitment"],
                decision=PROPOSITIONS,
                frames=(
                    _frame(subject="Sprzężenie źródła", predicate="DESCRIBES", object="zależność geometryczna"),
                ),
            )
        ]
    )
    result = run_proposition_producer(
        producer,
        claim_id="claim-1",
        classifications=[classification],
        source_receipts=[receipt],
    )
    assert result["status"] == "VALID"
    frame = result["propositions"][0]
    assert frame["normalized_subject"] == "sprzężenie źródła"
    assert frame["normalized_object"] == "zależność geometryczna"
    assert result["external_proposition_provider_executed"] is False
    assert result["fixture_propositions_claimed_as_real"] is False


def test_semantic_unresolved_classification_can_only_be_used_as_bound_excerpt_not_truth_authority():
    excerpt = "Źródło formułuje relację, lecz jej zgodność z claimem pozostaje nierozstrzygnięta."
    receipt = _receipt("src-u", excerpt)
    classification = _classification(receipt, excerpt, stance=SEMANTIC_UNRESOLVED)
    producer = FixturePropositionProducer(
        [
            FixturePropositionDecision(
                source_id="src-u",
                classification_commitment=classification["classification_commitment"],
                decision=PROPOSITIONS,
                frames=(_frame(subject="źródło", predicate="DESCRIBES", object="relacja"),),
            )
        ]
    )
    result = run_proposition_producer(
        producer,
        claim_id="claim-1",
        classifications=[classification],
        source_receipts=[receipt],
    )
    assert result["status"] == "VALID"
    assert result["proposition_count"] == 1
    assert result["propositions"][0]["source_content_authority"] == "UNTRUSTED_EVIDENCE_ONLY"
    assert result["authority"]["canon_allowed"] is False
