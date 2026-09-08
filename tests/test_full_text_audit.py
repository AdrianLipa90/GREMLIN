from __future__ import annotations

from gremlin_mcp.full_text_audit import audit_full_text


def test_full_text_audit_flags_conflicting_repeated_numeric_assignment() -> None:
    text = """
    The threshold is defined below.
    f_limit = 2.0e42 Hz.
    A later section reports the same threshold again.
    f_limit = 1.0e47 Hz.
    """
    result = audit_full_text(text, source_id="fixture:numeric")
    assert result["status"] == "CANDIDATE_AUDIT_COMPLETE"
    assert result["numeric_conflicts"]
    conflict = result["numeric_conflicts"][0]
    assert conflict["lhs"] == "f_limit"
    assert conflict["ratio"] >= 1e4
    assert conflict["classification"] == "INTERNAL_NUMERIC_CONFLICT_CANDIDATE"


def test_full_text_audit_flags_direct_negation_as_candidate_not_fact() -> None:
    text = (
        "The boundary is a causal horizon for every observer. "
        "The boundary is not a causal horizon for every observer."
    )
    result = audit_full_text(text, source_id="fixture:negation")
    assert result["contradiction_candidates"]
    row = result["contradiction_candidates"][0]
    assert row["classification"] == "DIRECT_NEGATION_CANDIDATE"
    assert row["requires_domain_review"] is True


def test_full_text_audit_requires_witness_for_strong_uniqueness_claim() -> None:
    text = "The proposed interpolation is the unique exact solution satisfying the stated conditions."
    result = audit_full_text(text, source_id="fixture:strength")
    assert any(row["claim_strength"] == "UNIQUENESS" for row in result["strong_claims"])
    assert any(row["gate"] == "REQUIRES_UNIQUENESS_WITNESS" for row in result["strong_claims"])


def test_full_text_audit_preserves_open_question_status() -> None:
    text = "Whether the two descriptions remain equivalent is an open question and is not resolved here."
    result = audit_full_text(text, source_id="fixture:open")
    assert result["open_or_limited_claims"]
    assert result["open_or_limited_claims"][0]["epistemic_status"] == "OPEN_OR_EXPLICITLY_LIMITED"


def test_full_text_audit_fails_closed_on_empty_input() -> None:
    result = audit_full_text("   ", source_id="fixture:empty")
    assert result["status"] == "NO_TEXT_FAIL_CLOSED"
    assert result["authority"]["canon_allowed"] is False
    assert result["authority"]["execution_admitted"] is False


def test_full_text_audit_never_promotes_candidate_to_canon() -> None:
    result = audit_full_text("A = 1.0. A = 2.0.", source_id="fixture:authority")
    assert result["authority"] == {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
