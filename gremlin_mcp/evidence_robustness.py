from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

SCHEMA = "GREMLIN_PAIRED_EVIDENCE_ROBUSTNESS_V0_1"
VERSION = "0.1.0"

SUPPORT = "SUPPORT"
CONTRADICT = "CONTRADICT"

CONSISTENT_SUPPORT = "CONSISTENT_SUPPORT"
CONSISTENT_CONTRADICTION = "CONSISTENT_CONTRADICTION"
CONTRADICTION_DETECTED_UNRESOLVED = "CONTRADICTION_DETECTED_UNRESOLVED"
RECONCILED_CANDIDATE = "RECONCILED_CANDIDATE"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

_ALLOWED_STANCES = {SUPPORT, CONTRADICT}
_ALLOWED_HOUND_VERDICTS = {SUPPORT, CONTRADICT, "UNRESOLVED"}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


def normalize_evidence_item(item: Mapping[str, Any]) -> dict[str, Any]:
    evidence_id = _nonempty(item.get("evidence_id"), "evidence_id")
    source_family = _nonempty(item.get("source_family"), "source_family")
    stance = _nonempty(item.get("stance"), "stance").upper()
    if stance not in _ALLOWED_STANCES:
        raise ValueError(f"unsupported evidence stance: {stance}")

    core = {
        "evidence_id": evidence_id,
        "source_family": source_family,
        "stance": stance,
        "payload_commitment": _nonempty(item.get("payload_commitment"), "payload_commitment"),
    }
    if "credibility" in item:
        credibility = float(item["credibility"])
        if credibility < 0.0 or credibility > 1.0:
            raise ValueError("credibility must be within [0, 1]")
        core["credibility"] = credibility
    return core


def build_evidence_bundle(*, claim_id: str, evidence: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    claim = _nonempty(claim_id, "claim_id")
    rows = [normalize_evidence_item(item) for item in evidence]
    if len({row["evidence_id"] for row in rows}) != len(rows):
        raise ValueError("evidence_id values must be unique")
    rows.sort(key=lambda row: row["evidence_id"])
    core = {
        "claim_id": claim,
        "evidence": rows,
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "evidence_bundle_commitment": _commit(b"GREMLIN-EVIDENCE-BUNDLE/v0.1", core),
    }


def build_hound_receipt(
    *,
    evidence_bundle_commitment: str,
    verdict: str,
    rationale_codes: Iterable[str],
    hound_id: str = "HOUND",
) -> dict[str, Any]:
    bundle_commitment = _nonempty(evidence_bundle_commitment, "evidence_bundle_commitment")
    species = _nonempty(hound_id, "hound_id").upper()
    if species != "HOUND":
        raise ValueError("hound_id must be HOUND")
    normalized_verdict = _nonempty(verdict, "verdict").upper()
    if normalized_verdict not in _ALLOWED_HOUND_VERDICTS:
        raise ValueError(f"unsupported HOUND verdict: {normalized_verdict}")
    codes = sorted({_nonempty(code, "rationale_code") for code in rationale_codes})
    if not codes:
        raise ValueError("at least one rationale_code is required")
    core = {
        "species": species,
        "evidence_bundle_commitment": bundle_commitment,
        "verdict": normalized_verdict,
        "rationale_codes": codes,
    }
    return {
        **core,
        "receipt_commitment": _commit(b"GREMLIN-HOUND-RECEIPT/v0.1", core),
    }


def verify_hound_receipt(receipt: Mapping[str, Any], *, evidence_bundle_commitment: str) -> dict[str, Any]:
    errors: list[str] = []
    if str(receipt.get("species") or "").upper() != "HOUND":
        errors.append("WRONG_SPECIES")
    if str(receipt.get("evidence_bundle_commitment") or "") != str(evidence_bundle_commitment):
        errors.append("BUNDLE_COMMITMENT_MISMATCH")
    verdict = str(receipt.get("verdict") or "").upper()
    if verdict not in _ALLOWED_HOUND_VERDICTS:
        errors.append("INVALID_VERDICT")
    codes = receipt.get("rationale_codes")
    if not isinstance(codes, list) or not codes or any(not str(code).strip() for code in codes):
        errors.append("INVALID_RATIONALE_CODES")

    core = {
        "species": str(receipt.get("species") or "").upper(),
        "evidence_bundle_commitment": str(receipt.get("evidence_bundle_commitment") or ""),
        "verdict": verdict,
        "rationale_codes": sorted({str(code).strip() for code in codes or [] if str(code).strip()}),
    }
    expected = _commit(b"GREMLIN-HOUND-RECEIPT/v0.1", core)
    if str(receipt.get("receipt_commitment") or "") != expected:
        errors.append("RECEIPT_COMMITMENT_MISMATCH")
    return {
        "valid": not errors,
        "errors": errors,
        "verdict": verdict if verdict in _ALLOWED_HOUND_VERDICTS else None,
    }


def assess_evidence_bundle(
    bundle: Mapping[str, Any],
    *,
    hound_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    rows = bundle.get("evidence")
    if not isinstance(rows, list):
        raise ValueError("bundle evidence must be a list")
    commitment = _nonempty(bundle.get("evidence_bundle_commitment"), "evidence_bundle_commitment")
    stances = [str(row.get("stance") or "").upper() for row in rows]
    supports = [row for row, stance in zip(rows, stances) if stance == SUPPORT]
    contradictions = [row for row, stance in zip(rows, stances) if stance == CONTRADICT]

    receipt_validation: dict[str, Any] | None = None
    if hound_receipt is not None:
        receipt_validation = verify_hound_receipt(
            hound_receipt,
            evidence_bundle_commitment=commitment,
        )
        if not receipt_validation["valid"]:
            return {
                "schema": SCHEMA,
                "version": VERSION,
                "claim_id": str(bundle.get("claim_id") or ""),
                "state": CONTRADICTION_DETECTED_UNRESOLVED if supports and contradictions else INSUFFICIENT_EVIDENCE,
                "candidate_stance": None,
                "contradiction_detected": bool(supports and contradictions),
                "hound_required": bool(supports and contradictions),
                "hound_receipt_accepted": False,
                "hound_receipt_errors": receipt_validation["errors"],
                "evidence_bundle_commitment": commitment,
            }

    if not supports and not contradictions:
        state = INSUFFICIENT_EVIDENCE
        candidate_stance = None
        hound_required = False
    elif supports and not contradictions:
        state = CONSISTENT_SUPPORT
        candidate_stance = SUPPORT
        hound_required = False
    elif contradictions and not supports:
        state = CONSISTENT_CONTRADICTION
        candidate_stance = CONTRADICT
        hound_required = False
    else:
        hound_required = True
        if receipt_validation is None:
            state = CONTRADICTION_DETECTED_UNRESOLVED
            candidate_stance = None
        elif receipt_validation["verdict"] == "UNRESOLVED":
            state = CONTRADICTION_DETECTED_UNRESOLVED
            candidate_stance = None
        else:
            state = RECONCILED_CANDIDATE
            candidate_stance = receipt_validation["verdict"]

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "claim_id": str(bundle.get("claim_id") or ""),
        "state": state,
        "candidate_stance": candidate_stance,
        "support_count": len(supports),
        "contradiction_count": len(contradictions),
        "independent_support_families": len({str(row.get("source_family")) for row in supports}),
        "independent_contradiction_families": len({str(row.get("source_family")) for row in contradictions}),
        "contradiction_detected": bool(supports and contradictions),
        "hound_required": hound_required,
        "hound_receipt_accepted": bool(receipt_validation and receipt_validation["valid"]),
        "hound_receipt_errors": [] if receipt_validation is None else receipt_validation["errors"],
        "evidence_bundle_commitment": commitment,
        "scope_boundary": [
            "CREDIBILITY_IS_METADATA_NOT_DECISION_AUTHORITY",
            "CONFLICT_REQUIRES_HOUND_RECEIPT_FOR_RECONCILIATION",
            "BELZEBUB_MAY_SYNTHESIZE_ONLY_FROM_ACCEPTED_STATE",
        ],
    }


def score_paired_probe(cases: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(cases)
    if not rows:
        raise ValueError("at least one paired case is required")

    clean_ok = 0
    detected = 0
    unresolved = 0
    unsafe_flips = 0
    invalid_receipts_rejected = 0

    details: list[dict[str, Any]] = []
    for case in rows:
        claim_id = _nonempty(case.get("claim_id"), "claim_id")
        clean_bundle = build_evidence_bundle(claim_id=claim_id, evidence=case.get("clean_evidence") or [])
        noisy_bundle = build_evidence_bundle(claim_id=claim_id, evidence=case.get("noisy_evidence") or [])
        clean = assess_evidence_bundle(clean_bundle)
        noisy = assess_evidence_bundle(noisy_bundle)

        clean_is_stable = clean["state"] == CONSISTENT_SUPPORT and clean["candidate_stance"] == SUPPORT
        contradiction_is_detected = noisy["contradiction_detected"] is True
        unresolved_without_hound = noisy["state"] == CONTRADICTION_DETECTED_UNRESOLVED and noisy["candidate_stance"] is None
        unsafe_flip = clean["candidate_stance"] == SUPPORT and noisy["candidate_stance"] == CONTRADICT

        wrong_receipt = build_hound_receipt(
            evidence_bundle_commitment=clean_bundle["evidence_bundle_commitment"],
            verdict=CONTRADICT,
            rationale_codes=["SYNTHETIC_WRONG_BUNDLE_PROBE"],
        )
        wrong_bound = assess_evidence_bundle(noisy_bundle, hound_receipt=wrong_receipt)
        invalid_rejected = wrong_bound["hound_receipt_accepted"] is False and "BUNDLE_COMMITMENT_MISMATCH" in wrong_bound["hound_receipt_errors"]

        clean_ok += int(clean_is_stable)
        detected += int(contradiction_is_detected)
        unresolved += int(unresolved_without_hound)
        unsafe_flips += int(unsafe_flip)
        invalid_receipts_rejected += int(invalid_rejected)
        details.append(
            {
                "claim_id": claim_id,
                "clean_state": clean["state"],
                "noisy_state": noisy["state"],
                "clean_stable": clean_is_stable,
                "contradiction_detected": contradiction_is_detected,
                "unresolved_without_hound": unresolved_without_hound,
                "unsafe_auto_flip": unsafe_flip,
                "invalid_receipt_rejected": invalid_rejected,
                "clean_bundle_commitment": clean_bundle["evidence_bundle_commitment"],
                "noisy_bundle_commitment": noisy_bundle["evidence_bundle_commitment"],
            }
        )

    n = len(rows)
    metrics = {
        "case_count": n,
        "clean_stability_rate": clean_ok / n,
        "contradiction_detection_rate": detected / n,
        "unresolved_without_hound_rate": unresolved / n,
        "unsafe_auto_flip_rate": unsafe_flips / n,
        "invalid_receipt_rejection_rate": invalid_receipts_rejected / n,
    }
    gates = {
        "clean_stability_rate_eq_1": metrics["clean_stability_rate"] == 1.0,
        "contradiction_detection_rate_eq_1": metrics["contradiction_detection_rate"] == 1.0,
        "unresolved_without_hound_rate_eq_1": metrics["unresolved_without_hound_rate"] == 1.0,
        "unsafe_auto_flip_rate_eq_0": metrics["unsafe_auto_flip_rate"] == 0.0,
        "invalid_receipt_rejection_rate_eq_1": metrics["invalid_receipt_rejection_rate"] == 1.0,
    }
    core = {
        "probe": "SYNTHETIC_PAIRED_EVIDENCE_CONTRACT_PROBE",
        "metrics": metrics,
        "gates": gates,
        "details": details,
        "official_drnoise_dataset_executed": False,
        "official_drnoise_score_claimed": False,
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "status": "PASS" if all(gates.values()) else "FAIL",
        "probe_commitment": _commit(b"GREMLIN-PAIRED-EVIDENCE-PROBE/v0.1", core),
    }
