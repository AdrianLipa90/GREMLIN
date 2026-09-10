import math

import pytest

from gremlin_mcp.evidence_robustness import (
    CONTRADICT,
    CONTRADICTION_DETECTED_UNRESOLVED,
    RECONCILED_CANDIDATE,
    SUPPORT,
    assess_evidence_bundle,
    build_evidence_bundle,
    build_hound_receipt,
    score_paired_probe,
    verify_hound_receipt,
)


def evidence(evidence_id: str, source_family: str, stance: str, credibility: float = 0.8):
    return {
        "evidence_id": evidence_id,
        "source_family": source_family,
        "stance": stance,
        "payload_commitment": f"payload:{evidence_id}",
        "credibility": credibility,
    }


def clean_pair(prefix: str):
    return [
        evidence(f"{prefix}-a", f"{prefix}-journal", SUPPORT, 0.72),
        evidence(f"{prefix}-b", f"{prefix}-registry", SUPPORT, 0.76),
    ]


def noisy_pair(prefix: str):
    return clean_pair(prefix) + [
        evidence(f"{prefix}-noise", f"{prefix}-authoritative-looking", CONTRADICT, 0.99),
    ]


def test_high_credibility_contradiction_cannot_auto_flip():
    bundle = build_evidence_bundle(claim_id="claim-1", evidence=noisy_pair("x"))
    result = assess_evidence_bundle(bundle)
    assert result["contradiction_detected"] is True
    assert result["state"] == CONTRADICTION_DETECTED_UNRESOLVED
    assert result["candidate_stance"] is None
    assert result["hound_required"] is True


def test_wrong_bundle_hound_receipt_is_rejected_fail_closed():
    clean = build_evidence_bundle(claim_id="claim-2", evidence=clean_pair("y"))
    noisy = build_evidence_bundle(claim_id="claim-2", evidence=noisy_pair("y"))
    receipt = build_hound_receipt(
        evidence_bundle_commitment=clean["evidence_bundle_commitment"],
        verdict=CONTRADICT,
        rationale_codes=["WRONG_BUNDLE_TEST"],
    )
    result = assess_evidence_bundle(noisy, hound_receipt=receipt)
    assert result["hound_receipt_accepted"] is False
    assert "BUNDLE_COMMITMENT_MISMATCH" in result["hound_receipt_errors"]
    assert result["state"] == CONTRADICTION_DETECTED_UNRESOLVED
    assert result["candidate_stance"] is None


def test_tampered_hound_receipt_is_rejected():
    bundle = build_evidence_bundle(claim_id="claim-3", evidence=noisy_pair("z"))
    receipt = build_hound_receipt(
        evidence_bundle_commitment=bundle["evidence_bundle_commitment"],
        verdict=SUPPORT,
        rationale_codes=["VALID_TEST"],
    )
    receipt["verdict"] = CONTRADICT
    validation = verify_hound_receipt(
        receipt,
        evidence_bundle_commitment=bundle["evidence_bundle_commitment"],
    )
    assert validation["valid"] is False
    assert "RECEIPT_COMMITMENT_MISMATCH" in validation["errors"]


def test_valid_bound_hound_receipt_can_reconcile_only_as_candidate():
    bundle = build_evidence_bundle(claim_id="claim-4", evidence=noisy_pair("r"))
    receipt = build_hound_receipt(
        evidence_bundle_commitment=bundle["evidence_bundle_commitment"],
        verdict=SUPPORT,
        rationale_codes=["INDEPENDENT_CHAIN_WEIGHT", "DIRECT_CONFLICT_AUDITED"],
    )
    result = assess_evidence_bundle(bundle, hound_receipt=receipt)
    assert result["hound_receipt_accepted"] is True
    assert result["state"] == RECONCILED_CANDIDATE
    assert result["candidate_stance"] == SUPPORT


def test_paired_probe_preregistered_gates_pass_on_reference_cases():
    cases = [
        {
            "claim_id": f"paired-{i}",
            "clean_evidence": clean_pair(f"p{i}"),
            "noisy_evidence": noisy_pair(f"p{i}"),
        }
        for i in range(1, 5)
    ]
    receipt = score_paired_probe(cases)
    assert receipt["status"] == "PASS"
    assert receipt["metrics"]["clean_stability_rate"] == 1.0
    assert receipt["metrics"]["contradiction_detection_rate"] == 1.0
    assert receipt["metrics"]["unresolved_without_hound_rate"] == 1.0
    assert receipt["metrics"]["unsafe_auto_flip_rate"] == 0.0
    assert receipt["metrics"]["invalid_receipt_rejection_rate"] == 1.0
    assert receipt["official_drnoise_dataset_executed"] is False
    assert receipt["official_drnoise_score_claimed"] is False


def test_stale_bundle_commitment_cannot_cover_mutated_evidence():
    bundle = build_evidence_bundle(claim_id="claim-stale", evidence=clean_pair("s"))
    stale_commitment = bundle["evidence_bundle_commitment"]
    bundle["evidence"][0]["stance"] = CONTRADICT
    assert bundle["evidence_bundle_commitment"] == stale_commitment
    with pytest.raises(ValueError, match="bundle commitment mismatch"):
        assess_evidence_bundle(bundle)


def test_stale_bundle_commitment_cannot_be_reconciled_by_hound():
    bundle = build_evidence_bundle(claim_id="claim-stale-hound", evidence=noisy_pair("h"))
    receipt = build_hound_receipt(
        evidence_bundle_commitment=bundle["evidence_bundle_commitment"],
        verdict=SUPPORT,
        rationale_codes=["AUDITED_ORIGINAL"],
    )
    bundle["evidence"][0]["source_family"] = "mutated-family"
    with pytest.raises(ValueError, match="bundle commitment mismatch"):
        assess_evidence_bundle(bundle, hound_receipt=receipt)


def test_evidence_identifiers_and_credibility_are_not_coerced():
    with pytest.raises(ValueError, match="evidence_id must be a string"):
        build_evidence_bundle(
            claim_id="claim-types",
            evidence=[evidence(123, "family", SUPPORT)],  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="credibility must be a finite number"):
        build_evidence_bundle(
            claim_id="claim-types",
            evidence=[evidence("e1", "family", SUPPORT, credibility="0.8")],  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="credibility must be a finite number"):
        build_evidence_bundle(
            claim_id="claim-types",
            evidence=[evidence("e1", "family", SUPPORT, credibility=math.nan)],
        )


def test_evidence_unknown_fields_are_rejected_before_commitment():
    row = evidence("e1", "family", SUPPORT)
    row["execution_admitted"] = True
    with pytest.raises(ValueError, match="unsupported keys"):
        build_evidence_bundle(claim_id="claim-extra", evidence=[row])


def test_hound_receipt_rejects_scalar_rationale_codes_and_unknown_fields():
    with pytest.raises(ValueError, match="iterable of strings"):
        build_hound_receipt(
            evidence_bundle_commitment="bundle",
            verdict=SUPPORT,
            rationale_codes="ONE_CODE",  # type: ignore[arg-type]
        )

    receipt = build_hound_receipt(
        evidence_bundle_commitment="bundle",
        verdict=SUPPORT,
        rationale_codes=["ONE_CODE"],
    )
    receipt["execution_admitted"] = True
    validation = verify_hound_receipt(receipt, evidence_bundle_commitment="bundle")
    assert validation["valid"] is False
    assert "UNSUPPORTED_RECEIPT_FIELD" in validation["errors"]


def test_paired_probe_rejects_scalar_case_collection():
    with pytest.raises(ValueError, match="iterable of objects"):
        score_paired_probe("not-a-case-list")  # type: ignore[arg-type]
