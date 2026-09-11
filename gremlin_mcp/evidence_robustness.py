from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Iterable, Mapping

SCHEMA = "GREMLIN_PAIRED_EVIDENCE_ROBUSTNESS_V0_1"
VERSION = "0.1.1"

SUPPORT = "SUPPORT"
CONTRADICT = "CONTRADICT"

CONSISTENT_SUPPORT = "CONSISTENT_SUPPORT"
CONSISTENT_CONTRADICTION = "CONSISTENT_CONTRADICTION"
CONTRADICTION_DETECTED_UNRESOLVED = "CONTRADICTION_DETECTED_UNRESOLVED"
RECONCILED_CANDIDATE = "RECONCILED_CANDIDATE"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

_ALLOWED_STANCES = {SUPPORT, CONTRADICT}
_ALLOWED_HOUND_VERDICTS = {SUPPORT, CONTRADICT, "UNRESOLVED"}
_EVIDENCE_KEYS = frozenset(
    {
        "evidence_id", "source_family", "stance", "payload_commitment",
        "content_commitment", "excerpt", "excerpt_commitment", "credibility",
        "source_family_origin", "producer_declared_source_family",
    }
)
_BUNDLE_KEYS = frozenset({"schema", "version", "claim_id", "evidence", "evidence_bundle_commitment"})
_HOUND_KEYS = frozenset({"species", "evidence_bundle_commitment", "verdict", "rationale_codes", "receipt_commitment"})


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("evidence robustness data must be finite JSON") from exc


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


def _reject_unknown_keys(value: Mapping[Any, Any], allowed: frozenset[str], field: str) -> None:
    unknown = [key for key in value if not isinstance(key, str) or key not in allowed]
    if unknown:
        raise ValueError(f"{field} contains unsupported keys: {unknown}")


def _mapping_rows(values: Iterable[Mapping[str, Any]], field: str) -> list[Mapping[str, Any]]:
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError(f"{field} must be an iterable of objects")
    try:
        rows = list(values)
    except TypeError as exc:
        raise ValueError(f"{field} must be an iterable of objects") from exc
    if any(not isinstance(row, Mapping) for row in rows):
        raise ValueError(f"{field} must contain only objects")
    return rows


def _string_rows(values: Iterable[str], field: str) -> list[str]:
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError(f"{field} must be an iterable of strings")
    try:
        rows = list(values)
    except TypeError as exc:
        raise ValueError(f"{field} must be an iterable of strings") from exc
    return [_nonempty(row, field) for row in rows]


def _credibility(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("credibility must be a finite number within [0, 1]")
    score = float(value)
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError("credibility must be a finite number within [0, 1]")
    return score


def excerpt_commitment(excerpt: str) -> str:
    text = _nonempty(excerpt, "excerpt")
    return _commit(b"GREMLIN-EVIDENCE-EXCERPT/v0.1", text)


def normalize_evidence_item(item: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        raise ValueError("evidence item must be an object")
    _reject_unknown_keys(item, _EVIDENCE_KEYS, "evidence item")
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
    for field in (
        "content_commitment", "excerpt", "excerpt_commitment",
        "source_family_origin", "producer_declared_source_family",
    ):
        if field in item:
            core[field] = _nonempty(item.get(field), field)
    if "credibility" in item:
        core["credibility"] = _credibility(item["credibility"])
    return core


def _normalize_evidence_rows(evidence: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = [normalize_evidence_item(item) for item in _mapping_rows(evidence, "evidence")]
    ids = [row["evidence_id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("evidence_id values must be unique")
    rows.sort(key=lambda row: row["evidence_id"])
    return rows


def build_evidence_bundle(*, claim_id: str, evidence: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    claim = _nonempty(claim_id, "claim_id")
    rows = _normalize_evidence_rows(evidence)
    core = {"claim_id": claim, "evidence": rows}
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "evidence_bundle_commitment": _commit(b"GREMLIN-EVIDENCE-BUNDLE/v0.1", core),
    }


def _verified_bundle(bundle: Mapping[str, Any]) -> tuple[str, list[dict[str, Any]], str]:
    if not isinstance(bundle, Mapping):
        raise ValueError("evidence bundle must be an object")
    _reject_unknown_keys(bundle, _BUNDLE_KEYS, "evidence bundle")
    if bundle.get("schema") != SCHEMA:
        raise ValueError("evidence bundle schema mismatch")
    if bundle.get("version") != VERSION:
        raise ValueError("evidence bundle version mismatch")
    claim = _nonempty(bundle.get("claim_id"), "claim_id")
    raw_rows = bundle.get("evidence")
    if not isinstance(raw_rows, list):
        raise ValueError("bundle evidence must be a list")
    rows = _normalize_evidence_rows(raw_rows)
    core = {"claim_id": claim, "evidence": rows}
    expected = _commit(b"GREMLIN-EVIDENCE-BUNDLE/v0.1", core)
    supplied = _nonempty(bundle.get("evidence_bundle_commitment"), "evidence_bundle_commitment")
    if supplied != expected:
        raise ValueError("evidence bundle commitment mismatch")
    return claim, rows, expected


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
    codes = sorted(set(_string_rows(rationale_codes, "rationale_code")))
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
    if not isinstance(receipt, Mapping):
        return {"valid": False, "errors": ["RECEIPT_MUST_BE_OBJECT"], "verdict": None}
    try:
        _reject_unknown_keys(receipt, _HOUND_KEYS, "HOUND receipt")
    except ValueError:
        errors.append("UNSUPPORTED_RECEIPT_FIELD")
    try:
        expected_bundle = _nonempty(evidence_bundle_commitment, "evidence_bundle_commitment")
    except ValueError:
        return {"valid": False, "errors": ["EXPECTED_BUNDLE_COMMITMENT_INVALID"], "verdict": None}

    try:
        species = _nonempty(receipt.get("species"), "species").upper()
    except ValueError:
        species = ""
        errors.append("WRONG_SPECIES")
    if species != "HOUND" and "WRONG_SPECIES" not in errors:
        errors.append("WRONG_SPECIES")

    try:
        supplied_bundle = _nonempty(receipt.get("evidence_bundle_commitment"), "receipt evidence_bundle_commitment")
    except ValueError:
        supplied_bundle = ""
        errors.append("BUNDLE_COMMITMENT_MISMATCH")
    if supplied_bundle != expected_bundle and "BUNDLE_COMMITMENT_MISMATCH" not in errors:
        errors.append("BUNDLE_COMMITMENT_MISMATCH")

    try:
        verdict = _nonempty(receipt.get("verdict"), "verdict").upper()
    except ValueError:
        verdict = ""
        errors.append("INVALID_VERDICT")
    if verdict not in _ALLOWED_HOUND_VERDICTS and "INVALID_VERDICT" not in errors:
        errors.append("INVALID_VERDICT")

    raw_codes = receipt.get("rationale_codes")
    try:
        codes = sorted(set(_string_rows(raw_codes, "rationale_code")))
        if not codes:
            raise ValueError("empty rationale")
    except (TypeError, ValueError):
        codes = []
        errors.append("INVALID_RATIONALE_CODES")

    if species and supplied_bundle and verdict in _ALLOWED_HOUND_VERDICTS and codes:
        core = {
            "species": species,
            "evidence_bundle_commitment": supplied_bundle,
            "verdict": verdict,
            "rationale_codes": codes,
        }
        supplied_receipt_commitment = receipt.get("receipt_commitment")
        if not isinstance(supplied_receipt_commitment, str) or supplied_receipt_commitment.strip() != _commit(
            b"GREMLIN-HOUND-RECEIPT/v0.1", core
        ):
            errors.append("RECEIPT_COMMITMENT_MISMATCH")
    else:
        errors.append("RECEIPT_COMMITMENT_MISMATCH")

    return {
        "valid": not errors,
        "errors": list(dict.fromkeys(errors)),
        "verdict": verdict if verdict in _ALLOWED_HOUND_VERDICTS else None,
    }


def assess_evidence_bundle(
    bundle: Mapping[str, Any],
    *,
    hound_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    claim_id, rows, commitment = _verified_bundle(bundle)
    supports = [row for row in rows if row["stance"] == SUPPORT]
    contradictions = [row for row in rows if row["stance"] == CONTRADICT]
    receipt_validation = None
    if hound_receipt is not None:
        receipt_validation = verify_hound_receipt(hound_receipt, evidence_bundle_commitment=commitment)
        if not receipt_validation["valid"]:
            return {
                "schema": SCHEMA,
                "version": VERSION,
                "claim_id": claim_id,
                "state": CONTRADICTION_DETECTED_UNRESOLVED if supports and contradictions else INSUFFICIENT_EVIDENCE,
                "candidate_stance": None,
                "contradiction_detected": bool(supports and contradictions),
                "hound_required": bool(supports and contradictions),
                "hound_receipt_accepted": False,
                "hound_receipt_errors": receipt_validation["errors"],
                "evidence_bundle_commitment": commitment,
            }
    if not supports and not contradictions:
        state, candidate_stance, hound_required = INSUFFICIENT_EVIDENCE, None, False
    elif supports and not contradictions:
        state, candidate_stance, hound_required = CONSISTENT_SUPPORT, SUPPORT, False
    elif contradictions and not supports:
        state, candidate_stance, hound_required = CONSISTENT_CONTRADICTION, CONTRADICT, False
    else:
        hound_required = True
        if receipt_validation is None or receipt_validation["verdict"] == "UNRESOLVED":
            state, candidate_stance = CONTRADICTION_DETECTED_UNRESOLVED, None
        else:
            state, candidate_stance = RECONCILED_CANDIDATE, receipt_validation["verdict"]
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "claim_id": claim_id,
        "state": state,
        "candidate_stance": candidate_stance,
        "support_count": len(supports),
        "contradiction_count": len(contradictions),
        "independent_support_families": len({row["source_family"] for row in supports}),
        "independent_contradiction_families": len({row["source_family"] for row in contradictions}),
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
    rows = _mapping_rows(cases, "cases")
    if not rows:
        raise ValueError("at least one paired case is required")
    clean_ok = detected = unresolved = unsafe_flips = invalid_receipts_rejected = 0
    details: list[dict[str, Any]] = []
    for case in rows:
        claim_id = _nonempty(case.get("claim_id"), "claim_id")
        clean_evidence = case.get("clean_evidence")
        noisy_evidence = case.get("noisy_evidence")
        if clean_evidence is None or noisy_evidence is None:
            raise ValueError("paired case requires clean_evidence and noisy_evidence")
        clean_bundle = build_evidence_bundle(claim_id=claim_id, evidence=clean_evidence)
        noisy_bundle = build_evidence_bundle(claim_id=claim_id, evidence=noisy_evidence)
        clean, noisy = assess_evidence_bundle(clean_bundle), assess_evidence_bundle(noisy_bundle)
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
        invalid_rejected = (
            wrong_bound["hound_receipt_accepted"] is False
            and "BUNDLE_COMMITMENT_MISMATCH" in wrong_bound["hound_receipt_errors"]
        )
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
