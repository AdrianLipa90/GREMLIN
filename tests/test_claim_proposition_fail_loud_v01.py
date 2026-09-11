from __future__ import annotations

import pytest

from gremlin_mcp.claim_proposition import (
    AFFIRM,
    ASSERTED,
    build_proposition,
    normalize_predicate,
    normalize_term,
    proposition_core,
    scan_proposition_conflicts,
    verify_proposition,
)
from gremlin_mcp.evidence_robustness import SUPPORT
from gremlin_mcp.research_provenance import source_receipt_commitment
from gremlin_mcp.semantic_evidence import build_classification


def _receipt() -> dict[str, object]:
    excerpt = "Information describes geometry."
    text = f"Source src-a. {excerpt}"
    receipt: dict[str, object] = {
        "source_id": "src-a",
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": "content:src-a:v1",
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
        producer_id="fixture",
        producer_version="0.1",
        model_id=None,
        mode="FIXTURE_ONLY_NO_SEMANTIC_INFERENCE",
    )


def _frame() -> dict[str, object]:
    receipt = _receipt()
    return build_proposition(
        classification=_classification(receipt),
        claim_id="claim-1",
        source_receipts=[receipt],
        subject="Information",
        predicate="DESCRIBES",
        object="geometry",
        polarity=AFFIRM,
        modality=ASSERTED,
    )


def test_term_and_predicate_normalization_reject_non_strings() -> None:
    for value in (None, 123, True, ["term"]):
        with pytest.raises(ValueError, match="term must be a string"):
            normalize_term(value)
    for value in (None, 123, True, ["predicate"]):
        with pytest.raises(ValueError, match="predicate must be a string"):
            normalize_predicate(value)


def test_builder_rejects_non_string_typed_fields_instead_of_coercing() -> None:
    receipt = _receipt()
    classification = _classification(receipt)
    base = {
        "classification": classification,
        "claim_id": "claim-1",
        "source_receipts": [receipt],
        "subject": "Information",
        "predicate": "DESCRIBES",
        "object": "geometry",
        "polarity": AFFIRM,
        "modality": ASSERTED,
        "extraction_mode": "EXPLICIT_TYPED_INPUT",
    }
    for field, value, pattern in (
        ("claim_id", 123, "claim_id must be a string"),
        ("subject", 123, "subject must be a string"),
        ("predicate", ["DESCRIBES"], "predicate must be a string"),
        ("object", 42, "object must be a string"),
        ("polarity", True, "polarity must be a string"),
        ("modality", 1, "modality must be a string"),
        ("extraction_mode", False, "extraction_mode must be a string"),
    ):
        kwargs = dict(base)
        kwargs[field] = value
        with pytest.raises(ValueError, match=pattern):
            build_proposition(**kwargs)  # type: ignore[arg-type]


def test_proposition_core_rejects_synthetic_type_coercion() -> None:
    frame = _frame()
    frame["source_id"] = 123
    with pytest.raises(ValueError, match="source_id must be a string"):
        proposition_core(frame)
    assert verify_proposition(frame)["valid"] is False
    assert verify_proposition(frame)["errors"] == ["INVALID_PROPOSITION_FIELD_TYPE"]


def test_unknown_frame_fields_and_malformed_authority_are_rejected() -> None:
    frame = _frame()
    frame["silent_override"] = True
    validation = verify_proposition(frame)
    assert validation["valid"] is False
    assert validation["errors"] == ["INVALID_PROPOSITION_FIELD_TYPE"]

    frame = _frame()
    frame["authority"] = {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": "false",
    }
    validation = verify_proposition(frame)
    assert validation["valid"] is False
    assert "INVALID_AUTHORITY_ENVELOPE" in validation["errors"]


def test_directionality_and_policy_metadata_are_integrity_checked() -> None:
    for field, value, code in (
        ("directionality", "UNKNOWN", "DIRECTIONALITY_MISMATCH"),
        ("epistemic_status", "CANON", "EPISTEMIC_STATUS_MISMATCH"),
        ("semantic_equivalence_policy", "INFER_SYNONYMS", "SEMANTIC_EQUIVALENCE_POLICY_MISMATCH"),
        ("term_normalization", "LOSSY_ASCII", "TERM_NORMALIZATION_POLICY_MISMATCH"),
        ("source_content_authority", "TRUSTED_INSTRUCTION", "SOURCE_CONTENT_AUTHORITY_MISMATCH"),
    ):
        frame = _frame()
        frame[field] = value
        validation = verify_proposition(frame)
        assert validation["valid"] is False
        assert code in validation["errors"]


def test_scan_rejects_bad_container_and_rows_instead_of_dict_coercion() -> None:
    with pytest.raises(ValueError, match="frames must be an iterable of objects"):
        scan_proposition_conflicts("bad")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="frames must contain only objects"):
        scan_proposition_conflicts([_frame(), "bad-row"])  # type: ignore[list-item]
