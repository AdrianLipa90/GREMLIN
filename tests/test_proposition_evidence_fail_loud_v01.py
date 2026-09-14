from __future__ import annotations

import pytest

from gremlin_mcp.claim_proposition import AFFIRM
from gremlin_mcp.evidence_robustness import SUPPORT
from gremlin_mcp.proposition_evidence import (
    PROPOSITIONS,
    FixturePropositionDecision,
    FixturePropositionProducer,
    normalize_proposition_producer_output,
    run_proposition_producer,
    support_span_commitment,
    verify_grounded_proposition,
)
from gremlin_mcp.research_provenance import source_receipt_commitment
from gremlin_mcp.semantic_evidence import build_classification


def _receipt() -> dict[str, object]:
    excerpt = "Information describes geometry."
    text = f"Source a. {excerpt}"
    receipt: dict[str, object] = {
        "source_id": "a",
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": "content:a:v1",
        "content_length_chars": len(text),
        "evidence_text": text,
    }
    receipt["source_receipt_commitment"] = source_receipt_commitment(receipt)
    return receipt


def _classification(receipt: dict[str, object]) -> dict[str, object]:
    return build_classification(
        claim_id="claim-1",
        source_receipt=receipt,
        source_family="family-a",
        excerpt="Information describes geometry.",
        stance=SUPPORT,
        confidence=0.9,
        producer_id="semantic-fixture",
        producer_version="0.1",
        model_id=None,
        mode="FIXTURE_ONLY_NO_SEMANTIC_INFERENCE",
    )


def _decision(classification: dict[str, object]) -> dict[str, object]:
    return {
        "source_id": "a",
        "classification_commitment": classification["classification_commitment"],
        "decision": PROPOSITIONS,
        "frames": [
            {
                "subject": "Information",
                "predicate": "DESCRIBES",
                "object": "geometry",
                "polarity": AFFIRM,
                "modality": "ASSERTED",
                "support_span": "Information describes geometry",
            }
        ],
    }


def _normalize(decisions, **overrides):
    receipt = _receipt()
    classification = _classification(receipt)
    kwargs = {
        "claim_id": "claim-1",
        "classifications": [classification],
        "source_receipts": [receipt],
        "decisions": decisions(classification) if callable(decisions) else decisions,
        "producer": {"producer_id": "p", "producer_version": "1", "model_id": None, "mode": "TEST"},
        "require_complete_coverage": True,
    }
    kwargs.update(overrides)
    return normalize_proposition_producer_output(**kwargs)


def test_support_span_commitment_rejects_non_string() -> None:
    with pytest.raises(ValueError, match="support_span must be a string"):
        support_span_commitment(123)  # type: ignore[arg-type]


def test_claim_and_coverage_flag_do_not_coerce() -> None:
    receipt = _receipt()
    classification = _classification(receipt)
    with pytest.raises(ValueError, match="claim_id must be a string"):
        normalize_proposition_producer_output(
            claim_id=123,  # type: ignore[arg-type]
            classifications=[classification],
            source_receipts=[receipt],
            decisions=[_decision(classification)],
            producer={"producer_id": "p", "producer_version": "1", "model_id": None, "mode": "TEST"},
        )
    with pytest.raises(ValueError, match="require_complete_coverage must be boolean"):
        normalize_proposition_producer_output(
            claim_id="claim-1",
            classifications=[classification],
            source_receipts=[receipt],
            decisions=[_decision(classification)],
            producer={"producer_id": "p", "producer_version": "1", "model_id": None, "mode": "TEST"},
            require_complete_coverage="true",  # type: ignore[arg-type]
        )


def test_producer_descriptor_fields_do_not_coerce() -> None:
    receipt = _receipt()
    classification = _classification(receipt)
    for field, value, pattern in (
        ("producer_id", 1, "producer_id must be a string"),
        ("producer_version", False, "producer_version must be a string"),
        ("model_id", 7, "model_id must be a string"),
        ("mode", ["TEST"], "producer mode must be a string"),
    ):
        producer = {"producer_id": "p", "producer_version": "1", "model_id": None, "mode": "TEST"}
        producer[field] = value
        with pytest.raises(ValueError, match=pattern):
            normalize_proposition_producer_output(
                claim_id="claim-1",
                classifications=[classification],
                source_receipts=[receipt],
                decisions=[_decision(classification)],
                producer=producer,
            )


def test_decision_container_and_unknown_fields_fail_loud() -> None:
    receipt = _receipt()
    classification = _classification(receipt)
    with pytest.raises(ValueError, match="decisions must be an iterable of objects"):
        normalize_proposition_producer_output(
            claim_id="claim-1",
            classifications=[classification],
            source_receipts=[receipt],
            decisions="bad",  # type: ignore[arg-type]
            producer={"producer_id": "p", "producer_version": "1", "model_id": None, "mode": "TEST"},
        )
    decision = _decision(classification)
    decision["remote_authority"] = {"canon_allowed": True}
    result = normalize_proposition_producer_output(
        claim_id="claim-1",
        classifications=[classification],
        source_receipts=[receipt],
        decisions=[decision],
        producer={"producer_id": "p", "producer_version": "1", "model_id": None, "mode": "TEST"},
    )
    assert result["status"] == "INVALID_FAIL_CLOSED"
    assert "unsupported keys" in result["decision_errors"][0]["errors"][0]


def test_remote_frame_typed_fields_do_not_stringify() -> None:
    receipt = _receipt()
    classification = _classification(receipt)
    for field, value in (
        ("subject", 123),
        ("predicate", ["DESCRIBES"]),
        ("object", 42),
        ("polarity", True),
        ("modality", 1),
        ("support_span", 99),
    ):
        decision = _decision(classification)
        decision["frames"][0][field] = value  # type: ignore[index]
        result = normalize_proposition_producer_output(
            claim_id="claim-1",
            classifications=[classification],
            source_receipts=[receipt],
            decisions=[decision],
            producer={"producer_id": "p", "producer_version": "1", "model_id": None, "mode": "TEST"},
        )
        assert result["status"] == "INVALID_FAIL_CLOSED"
        assert result["propositions"] == []


def test_unknown_remote_frame_field_is_not_silently_ignored() -> None:
    receipt = _receipt()
    classification = _classification(receipt)
    decision = _decision(classification)
    decision["frames"][0]["execute"] = True  # type: ignore[index]
    result = normalize_proposition_producer_output(
        claim_id="claim-1",
        classifications=[classification],
        source_receipts=[receipt],
        decisions=[decision],
        producer={"producer_id": "p", "producer_version": "1", "model_id": None, "mode": "TEST"},
    )
    assert result["status"] == "INVALID_FAIL_CLOSED"
    assert "unsupported keys" in result["decision_errors"][0]["errors"][0]


def test_grounding_unknown_fields_and_non_string_span_are_rejected() -> None:
    receipt = _receipt()
    classification = _classification(receipt)
    result = normalize_proposition_producer_output(
        claim_id="claim-1",
        classifications=[classification],
        source_receipts=[receipt],
        decisions=[_decision(classification)],
        producer={"producer_id": "p", "producer_version": "1", "model_id": None, "mode": "TEST"},
    )
    frame = result["propositions"][0]
    frame["producer_grounding"]["unexpected"] = True
    validation = verify_grounded_proposition(
        frame,
        claim_id="claim-1",
        classifications=[classification],
        source_receipts=[receipt],
    )
    assert validation["valid"] is False
    assert "GROUNDING_FIELD_TYPE_INVALID" in validation["errors"]

    frame = result["propositions"][0]
    frame["producer_grounding"] = dict(frame["producer_grounding"])
    frame["producer_grounding"]["support_span"] = 123
    validation = verify_grounded_proposition(
        frame,
        claim_id="claim-1",
        classifications=[classification],
        source_receipts=[receipt],
    )
    assert validation["valid"] is False
    assert "GROUNDING_FIELD_TYPE_INVALID" in validation["errors"]


def test_fixture_producer_rejects_wrong_decision_container_types() -> None:
    with pytest.raises(ValueError, match="fixture decisions must be an iterable"):
        FixturePropositionProducer("bad")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="FixturePropositionDecision"):
        FixturePropositionProducer([{"source_id": "a"}])  # type: ignore[list-item]


def test_run_producer_rejects_non_boolean_coverage_before_provider_execution() -> None:
    receipt = _receipt()
    classification = _classification(receipt)
    decision = FixturePropositionDecision(
        source_id="a",
        classification_commitment=classification["classification_commitment"],  # type: ignore[arg-type]
        decision=PROPOSITIONS,
        frames=(
            {
                "subject": "Information",
                "predicate": "DESCRIBES",
                "object": "geometry",
                "polarity": AFFIRM,
                "modality": "ASSERTED",
                "support_span": "Information describes geometry",
            },
        ),
    )
    producer = FixturePropositionProducer([decision])
    with pytest.raises(ValueError, match="require_complete_coverage must be boolean"):
        run_proposition_producer(
            producer,
            claim_id="claim-1",
            classifications=[classification],
            source_receipts=[receipt],
            require_complete_coverage=1,  # type: ignore[arg-type]
        )
