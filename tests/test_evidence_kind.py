from __future__ import annotations

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
