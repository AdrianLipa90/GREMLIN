from __future__ import annotations

from gremlin_mcp.hound_claims import hound_claim_audit


def test_hound_rejects_non_iterable_proposition_container_fail_closed() -> None:
    audit = hound_claim_audit("bad", citations=[])  # type: ignore[arg-type]
    assert audit["status"] == "INVALID_PROPOSITION_SET_FAIL_CLOSED"
    assert "propositions must be an iterable of objects" in audit["invalid"][0]["errors"][0]
    assert audit["cross_family_conflict_candidate_count"] == 0


def test_hound_rejects_non_mapping_proposition_row_fail_closed() -> None:
    audit = hound_claim_audit(["bad"], citations=[])  # type: ignore[list-item]
    assert audit["status"] == "INVALID_PROPOSITION_SET_FAIL_CLOSED"
    assert "propositions must contain only objects" in audit["invalid"][0]["errors"][0]


def test_hound_family_derivation_error_is_explicit_fail_closed_state() -> None:
    # Empty propositions are valid as a set, so malformed citation input reaches the family layer.
    audit = hound_claim_audit([], citations="bad")  # type: ignore[arg-type]
    assert audit["status"] == "PROPOSITION_SOURCE_FAMILY_BINDING_FAILED"
    assert audit["family_set_commitment"] is None
    assert "citations must be an iterable of objects" in audit["family_errors"][0]
    assert audit["conflict_candidates"] == []


def test_hound_rejects_non_mapping_citation_row_as_family_binding_failure() -> None:
    audit = hound_claim_audit([], citations=["bad"])  # type: ignore[list-item]
    assert audit["status"] == "PROPOSITION_SOURCE_FAMILY_BINDING_FAILED"
    assert "citations must contain only objects" in audit["family_errors"][0]
