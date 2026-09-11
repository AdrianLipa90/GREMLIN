from __future__ import annotations

import pytest

from gremlin_mcp.research_provenance import (
    source_receipt_commitment,
    verify_source_receipt,
    verify_source_receipt_set,
)


def _receipt(source_id: str = "src-a", text: str = "Evidence text") -> dict[str, object]:
    receipt: dict[str, object] = {
        "source_id": source_id,
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": f"content:{source_id}:v1",
        "content_length_chars": len(text),
        "evidence_text": text,
    }
    receipt["source_receipt_commitment"] = source_receipt_commitment(receipt)
    return receipt


def _citation(receipt: dict[str, object]) -> dict[str, object]:
    return {
        "source_id": receipt["source_id"],
        "content_basis": receipt["content_basis"],
        "content_commitment": receipt["content_commitment"],
    }


def test_valid_receipt_and_bound_citation_pass() -> None:
    receipt = _receipt()
    validation = verify_source_receipt(receipt)
    assert validation["valid"] is True
    result = verify_source_receipt_set([receipt], citations=[_citation(receipt)])
    assert result["valid"] is True
    assert result["errors"] == []
    assert result["receipt_count"] == 1
    assert result["citation_count"] == 1


def test_content_length_rejects_bool_string_and_float_instead_of_coercing() -> None:
    for value in (True, "13", 13.0):
        receipt = _receipt()
        receipt["content_length_chars"] = value
        result = verify_source_receipt(receipt)
        assert result["valid"] is False
        assert result["errors"] == ["INVALID_RECEIPT_FIELD_TYPE"]
        with pytest.raises(ValueError, match="non-negative integer"):
            source_receipt_commitment(receipt)


def test_source_id_and_text_fields_do_not_coerce_non_strings() -> None:
    for field, value in (
        ("source_id", 17),
        ("content_basis", ["metadata"]),
        ("content_commitment", 99),
        ("evidence_text", b"Evidence text"),
    ):
        receipt = _receipt()
        receipt[field] = value
        result = verify_source_receipt(receipt)
        assert result["valid"] is False
        assert result["errors"] == ["INVALID_RECEIPT_FIELD_TYPE"]


def test_unknown_receipt_field_is_rejected() -> None:
    receipt = _receipt()
    receipt["silent_override"] = True
    result = verify_source_receipt(receipt)
    assert result["valid"] is False
    assert result["errors"] == ["INVALID_RECEIPT_FIELD_TYPE"]


def test_supplied_commitment_must_be_a_string() -> None:
    receipt = _receipt()
    receipt["source_receipt_commitment"] = 123
    result = verify_source_receipt(receipt)
    assert result["valid"] is False
    assert "SOURCE_RECEIPT_COMMITMENT_MISSING" in result["errors"]


def test_receipt_set_rejects_wrong_container_shapes_fail_closed() -> None:
    result = verify_source_receipt_set("not-a-receipt-list")  # type: ignore[arg-type]
    assert result["valid"] is False
    assert result["errors"][0]["code"] == "INVALID_RECEIPT_SET_INPUT"

    receipt = _receipt()
    result = verify_source_receipt_set([receipt, "bad-row"])  # type: ignore[list-item]
    assert result["valid"] is False
    assert result["errors"][0]["code"] == "INVALID_RECEIPT_SET_INPUT"


def test_citation_source_id_does_not_coerce_integer() -> None:
    receipt = _receipt()
    citation = _citation(receipt)
    citation["source_id"] = 123
    result = verify_source_receipt_set([receipt], citations=[citation])
    assert result["valid"] is False
    codes = {row["code"] for row in result["errors"]}
    assert "CITATION_SOURCE_ID_INVALID" in codes
    assert "ORPHAN_SOURCE_RECEIPT" in codes


def test_citation_commitment_and_basis_must_be_strings() -> None:
    receipt = _receipt()
    citation = _citation(receipt)
    citation["content_commitment"] = 123
    citation["content_basis"] = False
    result = verify_source_receipt_set([receipt], citations=[citation])
    assert result["valid"] is False
    codes = {row["code"] for row in result["errors"]}
    assert "CITATION_CONTENT_COMMITMENT_MISMATCH" in codes
    assert "CITATION_CONTENT_BASIS_MISMATCH" in codes


def test_tampered_receipt_commitment_is_detected_without_reusing_supplied_value_in_set_commitment() -> None:
    receipt = _receipt()
    expected = verify_source_receipt(receipt)["expected_commitment"]
    receipt["source_receipt_commitment"] = "0" * 64
    validation = verify_source_receipt(receipt)
    assert validation["valid"] is False
    assert validation["expected_commitment"] == expected
    result = verify_source_receipt_set([receipt], citations=[_citation(receipt)])
    assert result["valid"] is False
    assert "SOURCE_RECEIPT_COMMITMENT_MISMATCH" in {row["code"] for row in result["errors"]}
    assert len(result["receipt_set_commitment"]) == 64
