from __future__ import annotations

import pytest

from gremlin_mcp.evidence_kind import (
    CLAIM_MODE_UNKNOWN_FAIL_CLOSED,
    EMPIRICAL,
    ENGINEERING,
    ENGINEERING_TEST,
    KIND_POLICY_INSUFFICIENT,
    KIND_POLICY_SUFFICIENT,
    OBSERVATIONAL,
    PRIMARY_EXPERIMENT,
    REVIEW_META,
    SIMULATION,
    THEORETICAL,
    THEORY_DERIVATION,
    UNKNOWN,
    assess_evidence_kind_policy,
    build_evidence_kind_assignment,
    normalize_evidence_kind,
    verify_evidence_kind_assignment,
)
from gremlin_mcp.evidence_robustness import CONTRADICT, SUPPORT
from gremlin_mcp.research_provenance import source_receipt_commitment


def _receipt(source_id: str, text: str = "Evidence text") -> dict:
    receipt = {
        "source_id": source_id,
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": f"content:{source_id}:v1",
        "content_length_chars": len(text),
        "evidence_text": text,
    }
    receipt["source_receipt_commitment"] = source_receipt_commitment(receipt)
    return receipt


def _assignment(receipt, kind):
    return build_evidence_kind_assignment(
        source_receipt=receipt,
        evidence_kind=kind,
        producer_id="fixture-kind-producer",
        producer_version="0.1.0",
        mode="FIXTURE_ONLY_EXPLICIT_KIND_ASSIGNMENT",
    )


def _guard(source_id, family, stance=SUPPORT):
    return {
        "evidence_id": source_id,
        "source_family": family,
        "stance": stance,
        "payload_commitment": f"payload:{source_id}",
    }


def test_missing_kind_normalizes_to_unknown_not_guessed():
    assert normalize_evidence_kind(None) == UNKNOWN
    assert normalize_evidence_kind("") == UNKNOWN


def test_assignment_is_bound_to_exact_source_content_commitment():
    receipt = _receipt("src-a")
    assignment = _assignment(receipt, PRIMARY_EXPERIMENT)
    validation = verify_evidence_kind_assignment(assignment, source_receipts=[receipt])
    assert validation["valid"] is True
    tampered = dict(assignment)
    tampered["content_commitment"] = "content:tampered"
    validation = verify_evidence_kind_assignment(tampered, source_receipts=[receipt])
    assert validation["valid"] is False
    assert "CONTENT_COMMITMENT_MISMATCH" in validation["errors"]
    assert "ASSIGNMENT_COMMITMENT_MISMATCH" in validation["errors"]


def test_empirical_claim_rejects_review_only_even_across_two_families():
    r1, r2 = _receipt("a"), _receipt("b")
    policy = assess_evidence_kind_policy(
        [_guard("a", "fam-a"), _guard("b", "fam-b")],
        assignments=[_assignment(r1, REVIEW_META), _assignment(r2, REVIEW_META)],
        claim_mode=EMPIRICAL,
    )
    assert policy["state"] == KIND_POLICY_INSUFFICIENT
    assert policy["direct_family_count"] == 0
    assert policy["policy_satisfied"] is False


def test_empirical_claim_accepts_one_direct_empirical_family_after_family_quorum():
    r1, r2 = _receipt("a"), _receipt("b")
    policy = assess_evidence_kind_policy(
        [_guard("a", "fam-a"), _guard("b", "fam-b")],
        assignments=[_assignment(r1, PRIMARY_EXPERIMENT), _assignment(r2, REVIEW_META)],
        claim_mode=EMPIRICAL,
        min_direct_families=1,
    )
    assert policy["state"] == KIND_POLICY_SUFFICIENT
    assert policy["direct_family_count"] == 1


def test_theoretical_claim_requires_theory_derivation_not_simulation_only():
    r1, r2 = _receipt("a"), _receipt("b")
    insufficient = assess_evidence_kind_policy(
        [_guard("a", "fam-a"), _guard("b", "fam-b")],
        assignments=[_assignment(r1, SIMULATION), _assignment(r2, REVIEW_META)],
        claim_mode=THEORETICAL,
    )
    assert insufficient["state"] == KIND_POLICY_INSUFFICIENT

    sufficient = assess_evidence_kind_policy(
        [_guard("a", "fam-a"), _guard("b", "fam-b")],
        assignments=[_assignment(r1, THEORY_DERIVATION), _assignment(r2, REVIEW_META)],
        claim_mode=THEORETICAL,
    )
    assert sufficient["state"] == KIND_POLICY_SUFFICIENT


def test_engineering_claim_requires_engineering_test_or_replication():
    r1, r2 = _receipt("a"), _receipt("b")
    insufficient = assess_evidence_kind_policy(
        [_guard("a", "fam-a"), _guard("b", "fam-b")],
        assignments=[_assignment(r1, SIMULATION), _assignment(r2, REVIEW_META)],
        claim_mode=ENGINEERING,
    )
    assert insufficient["state"] == KIND_POLICY_INSUFFICIENT

    sufficient = assess_evidence_kind_policy(
        [_guard("a", "fam-a"), _guard("b", "fam-b")],
        assignments=[_assignment(r1, ENGINEERING_TEST), _assignment(r2, REVIEW_META)],
        claim_mode=ENGINEERING,
    )
    assert sufficient["state"] == KIND_POLICY_SUFFICIENT


def test_unknown_claim_mode_fails_closed():
    receipt = _receipt("a")
    policy = assess_evidence_kind_policy(
        [_guard("a", "fam-a")],
        assignments=[_assignment(receipt, OBSERVATIONAL)],
        claim_mode=None,
    )
    assert policy["state"] == CLAIM_MODE_UNKNOWN_FAIL_CLOSED
    assert policy["policy_satisfied"] is False


def test_mixed_stance_defers_to_hound_before_kind_policy():
    r1, r2 = _receipt("a"), _receipt("b")
    policy = assess_evidence_kind_policy(
        [_guard("a", "fam-a", SUPPORT), _guard("b", "fam-b", CONTRADICT)],
        assignments=[_assignment(r1, PRIMARY_EXPERIMENT), _assignment(r2, PRIMARY_EXPERIMENT)],
        claim_mode=EMPIRICAL,
    )
    assert policy["conflict_present"] is True
    assert policy["policy_satisfied"] is None
    assert "DEFER_TO_HOUND" in policy["state"]


def test_evidence_kind_does_not_coerce_non_string_values():
    with pytest.raises(ValueError, match="evidence kind must be a string"):
        normalize_evidence_kind(1)  # type: ignore[arg-type]


def test_assignment_builder_rejects_numeric_provenance_identifiers():
    receipt = _receipt("src-a")
    with pytest.raises(ValueError, match="producer_id must be a string"):
        build_evidence_kind_assignment(
            source_receipt=receipt,
            evidence_kind=PRIMARY_EXPERIMENT,
            producer_id=123,  # type: ignore[arg-type]
            producer_version="0.1.0",
            mode="FIXTURE_ONLY_EXPLICIT_KIND_ASSIGNMENT",
        )


def test_assignment_verifier_rejects_unknown_unsigned_fields():
    receipt = _receipt("src-a")
    assignment = _assignment(receipt, PRIMARY_EXPERIMENT)
    assignment["execution_admitted"] = True
    validation = verify_evidence_kind_assignment(assignment, source_receipts=[receipt])
    assert validation["valid"] is False
    assert "INVALID_EVIDENCE_KIND_ASSIGNMENT_FIELD" in validation["errors"]


def test_assignment_verifier_requires_exact_false_boolean_authority():
    receipt = _receipt("src-a")
    assignment = _assignment(receipt, PRIMARY_EXPERIMENT)
    assignment["authority"] = {
        "production_runtime_write": 0,
        "execution_admitted": False,
        "canon_allowed": False,
    }
    validation = verify_evidence_kind_assignment(assignment, source_receipts=[receipt])
    assert validation["valid"] is False
    assert "INVALID_AUTHORITY_ENVELOPE" in validation["errors"]


def test_assignment_verifier_rejects_schema_or_policy_label_tamper():
    receipt = _receipt("src-a")
    assignment = _assignment(receipt, PRIMARY_EXPERIMENT)
    assignment["schema"] = "OTHER"
    assignment["kind_authority"] = "TRUTH"
    validation = verify_evidence_kind_assignment(assignment, source_receipts=[receipt])
    assert validation["valid"] is False
    assert "ASSIGNMENT_SCHEMA_MISMATCH" in validation["errors"]
    assert "KIND_AUTHORITY_MISMATCH" in validation["errors"]


def test_minimum_direct_family_threshold_rejects_bool_and_fractional_values():
    receipt = _receipt("a")
    assignment = _assignment(receipt, PRIMARY_EXPERIMENT)
    guard = [_guard("a", "fam-a")]
    with pytest.raises(ValueError, match="must be an integer"):
        assess_evidence_kind_policy(
            guard,
            assignments=[assignment],
            claim_mode=EMPIRICAL,
            min_direct_families=True,  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="must be an integer"):
        assess_evidence_kind_policy(
            guard,
            assignments=[assignment],
            claim_mode=EMPIRICAL,
            min_direct_families=1.9,  # type: ignore[arg-type]
        )


def test_policy_rejects_non_string_and_unknown_guard_stances():
    receipt = _receipt("a")
    assignment = _assignment(receipt, PRIMARY_EXPERIMENT)
    with pytest.raises(ValueError, match="stance must be a string"):
        assess_evidence_kind_policy(
            [_guard("a", "fam-a", stance=1)],  # type: ignore[arg-type]
            assignments=[assignment],
            claim_mode=EMPIRICAL,
        )
    with pytest.raises(ValueError, match="unsupported guard evidence stance"):
        assess_evidence_kind_policy(
            [_guard("a", "fam-a", stance="MAYBE")],
            assignments=[assignment],
            claim_mode=EMPIRICAL,
        )
