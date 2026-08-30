from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

from gremlin_mcp.evidence_robustness import CONTRADICT, SUPPORT
from gremlin_mcp.research_provenance import verify_source_receipt

SCHEMA = "GREMLIN_EVIDENCE_KIND_POLICY_V0_1"
VERSION = "0.1.0"

PRIMARY_EXPERIMENT = "PRIMARY_EXPERIMENT"
OBSERVATIONAL = "OBSERVATIONAL"
REPLICATION = "REPLICATION"
DATASET_MEASUREMENT = "DATASET_MEASUREMENT"
THEORY_DERIVATION = "THEORY_DERIVATION"
SIMULATION = "SIMULATION"
ENGINEERING_TEST = "ENGINEERING_TEST"
REVIEW_META = "REVIEW_META"
UNKNOWN = "UNKNOWN"

EVIDENCE_KINDS = {
    PRIMARY_EXPERIMENT,
    OBSERVATIONAL,
    REPLICATION,
    DATASET_MEASUREMENT,
    THEORY_DERIVATION,
    SIMULATION,
    ENGINEERING_TEST,
    REVIEW_META,
    UNKNOWN,
}

EMPIRICAL = "EMPIRICAL"
THEORETICAL = "THEORETICAL"
ENGINEERING = "ENGINEERING"
UNKNOWN_CLAIM_MODE = "UNKNOWN"
CLAIM_MODES = {EMPIRICAL, THEORETICAL, ENGINEERING, UNKNOWN_CLAIM_MODE}

DIRECT_KINDS_BY_CLAIM_MODE = {
    EMPIRICAL: {PRIMARY_EXPERIMENT, OBSERVATIONAL, REPLICATION, DATASET_MEASUREMENT},
    THEORETICAL: {THEORY_DERIVATION},
    ENGINEERING: {ENGINEERING_TEST, REPLICATION},
    UNKNOWN_CLAIM_MODE: set(),
}

KIND_POLICY_SUFFICIENT = "EVIDENCE_KIND_POLICY_SUFFICIENT"
KIND_POLICY_INSUFFICIENT = "EVIDENCE_KIND_POLICY_INSUFFICIENT"
KIND_ASSIGNMENT_INCOMPLETE = "EVIDENCE_KIND_ASSIGNMENT_INCOMPLETE"
KIND_ASSIGNMENT_INVALID = "EVIDENCE_KIND_ASSIGNMENT_INVALID"
CLAIM_MODE_UNKNOWN_FAIL_CLOSED = "CLAIM_MODE_UNKNOWN_FAIL_CLOSED"
CONFLICT_DEFER_TO_HOUND = "EVIDENCE_KIND_CONFLICT_DEFER_TO_HOUND"
NO_RESOLVED_EVIDENCE = "NO_RESOLVED_EVIDENCE"


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


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _nonempty(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


def normalize_evidence_kind(value: str | None) -> str:
    if value is None:
        return UNKNOWN
    kind = str(value).strip().upper()
    if not kind:
        return UNKNOWN
    if kind not in EVIDENCE_KINDS:
        raise ValueError(f"unsupported evidence kind: {kind}")
    return kind


def normalize_claim_mode(value: str | None) -> str:
    if value is None:
        return UNKNOWN_CLAIM_MODE
    mode = str(value).strip().upper()
    if not mode:
        return UNKNOWN_CLAIM_MODE
    if mode not in CLAIM_MODES:
        raise ValueError(f"unsupported claim mode: {mode}")
    return mode


def evidence_kind_assignment_core(assignment: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_id": str(assignment.get("source_id") or "").strip(),
        "content_commitment": str(assignment.get("content_commitment") or "").strip(),
        "evidence_kind": normalize_evidence_kind(assignment.get("evidence_kind")),
        "producer_id": str(assignment.get("producer_id") or "").strip(),
        "producer_version": str(assignment.get("producer_version") or "").strip(),
        "model_id": None if assignment.get("model_id") is None else str(assignment.get("model_id")),
        "mode": str(assignment.get("mode") or "").strip(),
        "rationale_code": str(assignment.get("rationale_code") or "UNSPECIFIED").strip().upper(),
    }


def evidence_kind_assignment_commitment(assignment: Mapping[str, Any]) -> str:
    return _commit(
        b"GREMLIN-EVIDENCE-KIND-ASSIGNMENT/v0.1",
        evidence_kind_assignment_core(assignment),
    )


def build_evidence_kind_assignment(
    *,
    source_receipt: Mapping[str, Any],
    evidence_kind: str | None,
    producer_id: str,
    producer_version: str,
    mode: str,
    rationale_code: str = "EXPLICIT_TYPED_ASSIGNMENT",
    model_id: str | None = None,
) -> dict[str, Any]:
    receipt_validation = verify_source_receipt(source_receipt)
    if not receipt_validation["valid"]:
        raise ValueError(f"source receipt failed integrity validation: {receipt_validation['errors']}")

    core = {
        "source_id": _nonempty(source_receipt.get("source_id"), "source_id"),
        "content_commitment": _nonempty(source_receipt.get("content_commitment"), "content_commitment"),
        "evidence_kind": normalize_evidence_kind(evidence_kind),
        "producer_id": _nonempty(producer_id, "producer_id"),
        "producer_version": _nonempty(producer_version, "producer_version"),
        "model_id": None if model_id is None else str(model_id),
        "mode": _nonempty(mode, "mode"),
        "rationale_code": _nonempty(rationale_code, "rationale_code").upper(),
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "assignment_commitment": _commit(b"GREMLIN-EVIDENCE-KIND-ASSIGNMENT/v0.1", core),
        "kind_authority": "CANDIDATE_METADATA_ONLY",
        "inference_policy": "NO_AUTOMATIC_KIND_INFERENCE_FROM_TITLE_OR_PROVIDER_METADATA",
        "authority": _authority(),
    }


def verify_evidence_kind_assignment(
    assignment: Mapping[str, Any],
    *,
    source_receipts: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        core = evidence_kind_assignment_core(assignment)
    except (TypeError, ValueError):
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "valid": False,
            "errors": ["INVALID_EVIDENCE_KIND_ASSIGNMENT_FIELD"],
            "source_id": str(assignment.get("source_id") or ""),
            "authority": _authority(),
        }

    by_id: dict[str, Mapping[str, Any]] = {}
    duplicates: set[str] = set()
    for receipt in source_receipts:
        sid = str(receipt.get("source_id") or "").strip()
        if not sid:
            continue
        if sid in by_id:
            duplicates.add(sid)
        by_id[sid] = receipt

    if not core["source_id"]:
        errors.append("SOURCE_ID_MISSING")
    if core["source_id"] in duplicates:
        errors.append("DUPLICATE_SOURCE_RECEIPT")
    receipt = by_id.get(core["source_id"])
    if receipt is None:
        errors.append("SOURCE_RECEIPT_MISSING")
    else:
        receipt_validation = verify_source_receipt(receipt)
        if not receipt_validation["valid"]:
            errors.append("SOURCE_RECEIPT_INTEGRITY_FAILED")
        if core["content_commitment"] != str(receipt.get("content_commitment") or "").strip():
            errors.append("CONTENT_COMMITMENT_MISMATCH")

    if not core["producer_id"]:
        errors.append("PRODUCER_ID_MISSING")
    if not core["producer_version"]:
        errors.append("PRODUCER_VERSION_MISSING")
    if not core["mode"]:
        errors.append("MODE_MISSING")

    expected = _commit(b"GREMLIN-EVIDENCE-KIND-ASSIGNMENT/v0.1", core)
    supplied = str(assignment.get("assignment_commitment") or "").strip()
    if not supplied:
        errors.append("ASSIGNMENT_COMMITMENT_MISSING")
    elif supplied != expected:
        errors.append("ASSIGNMENT_COMMITMENT_MISMATCH")

    authority = assignment.get("authority")
    if authority is not None and any(
        bool(authority.get(key))
        for key in ("production_runtime_write", "execution_admitted", "canon_allowed")
    ):
        errors.append("INVALID_AUTHORITY_ESCALATION")

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "valid": not errors,
        "errors": errors,
        "source_id": core["source_id"],
        "evidence_kind": core["evidence_kind"],
        "expected_assignment_commitment": expected,
        "authority": _authority(),
    }


def normalize_evidence_kind_assignments(
    assignments: Iterable[Mapping[str, Any]],
    *,
    source_receipts: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = [dict(row) for row in assignments]
    receipts = [dict(row) for row in source_receipts]
    validations = [
        verify_evidence_kind_assignment(row, source_receipts=receipts)
        for row in rows
    ]
    invalid = [
        {
            "index": index,
            "source_id": validation["source_id"],
            "errors": validation["errors"],
        }
        for index, validation in enumerate(validations)
        if not validation["valid"]
    ]
    source_ids = [str(row.get("source_id") or "").strip() for row in rows]
    duplicates = sorted({sid for sid in source_ids if sid and source_ids.count(sid) > 1})
    if duplicates:
        invalid.extend(
            {"index": -1, "source_id": sid, "errors": ["DUPLICATE_SOURCE_KIND_ASSIGNMENT"]}
            for sid in duplicates
        )
    accepted = [] if invalid else rows
    core = {
        "status": "VALID" if not invalid else "INVALID_FAIL_CLOSED",
        "assignment_count": len(rows),
        "invalid_count": len(invalid),
        "invalid": invalid,
        "assignments": accepted,
        "validations": validations,
        "kind_authority": "CANDIDATE_METADATA_ONLY",
        "inference_policy": "NO_AUTOMATIC_KIND_INFERENCE_FROM_TITLE_OR_PROVIDER_METADATA",
        "authority": _authority(),
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "assignment_set_commitment": _commit(b"GREMLIN-EVIDENCE-KIND-ASSIGNMENT-SET/v0.1", core),
    }


def assess_evidence_kind_policy(
    guard_evidence: Iterable[Mapping[str, Any]],
    *,
    assignments: Iterable[Mapping[str, Any]],
    claim_mode: str | None,
    min_direct_families: int = 1,
) -> dict[str, Any]:
    minimum = int(min_direct_families)
    if not 1 <= minimum <= 8:
        raise ValueError("min_direct_families must be in [1, 8]")
    mode = normalize_claim_mode(claim_mode)
    rows = [dict(row) for row in guard_evidence]
    assignment_rows = [dict(row) for row in assignments]
    assignment_by_source = {
        str(row.get("source_id") or "").strip(): row
        for row in assignment_rows
        if str(row.get("source_id") or "").strip()
    }

    support = [row for row in rows if str(row.get("stance") or "").strip().upper() == SUPPORT]
    contradict = [row for row in rows if str(row.get("stance") or "").strip().upper() == CONTRADICT]
    conflict = bool(support and contradict)
    resolved = support + contradict
    missing_source_ids = sorted(
        {
            str(row.get("evidence_id") or "").strip()
            for row in resolved
            if str(row.get("evidence_id") or "").strip() not in assignment_by_source
        }
    )

    if conflict:
        state = CONFLICT_DEFER_TO_HOUND
        candidate_stance = None
        direct_family_count = 0
        satisfied = None
    elif not resolved:
        state = NO_RESOLVED_EVIDENCE
        candidate_stance = None
        direct_family_count = 0
        satisfied = False
    elif missing_source_ids:
        state = KIND_ASSIGNMENT_INCOMPLETE
        candidate_stance = SUPPORT if support else CONTRADICT
        direct_family_count = 0
        satisfied = False
    elif mode == UNKNOWN_CLAIM_MODE:
        state = CLAIM_MODE_UNKNOWN_FAIL_CLOSED
        candidate_stance = SUPPORT if support else CONTRADICT
        direct_family_count = 0
        satisfied = False
    else:
        candidate_rows = support if support else contradict
        candidate_stance = SUPPORT if support else CONTRADICT
        direct_kinds = DIRECT_KINDS_BY_CLAIM_MODE[mode]
        direct_families: set[str] = set()
        for row in candidate_rows:
            sid = str(row.get("evidence_id") or "").strip()
            family = str(row.get("source_family") or "").strip()
            if not family:
                raise ValueError("guard evidence requires deterministic source_family")
            kind = normalize_evidence_kind(assignment_by_source[sid].get("evidence_kind"))
            if kind in direct_kinds:
                direct_families.add(family)
        direct_family_count = len(direct_families)
        satisfied = direct_family_count >= minimum
        state = KIND_POLICY_SUFFICIENT if satisfied else KIND_POLICY_INSUFFICIENT

    observed_kinds = sorted(
        {
            normalize_evidence_kind(row.get("evidence_kind"))
            for row in assignment_rows
        }
    )
    direct_kinds_for_mode = sorted(DIRECT_KINDS_BY_CLAIM_MODE.get(mode, set()))
    core = {
        "state": state,
        "claim_mode": mode,
        "candidate_stance": candidate_stance,
        "minimum_direct_provenance_families": minimum,
        "direct_family_count": direct_family_count,
        "policy_satisfied": satisfied,
        "missing_assignment_source_ids": missing_source_ids,
        "observed_evidence_kinds": observed_kinds,
        "direct_evidence_kinds_for_claim_mode": direct_kinds_for_mode,
        "conflict_present": conflict,
        "kind_semantics": "EXPLICIT_COMMITMENT_BOUND_CANDIDATE_METADATA_NOT_AUTOMATIC_TRUTH",
        "family_semantics": "PROVENANCE_DIVERSITY_HEURISTIC_NOT_INDEPENDENCE_PROOF",
        "inference_policy": "NO_AUTOMATIC_EVIDENCE_KIND_INFERENCE_FROM_TITLE_OR_PROVIDER_METADATA",
        "conflict_policy": "STANCE_CONFLICT_ALWAYS_DEFERRED_TO_HOUND_BEFORE_KIND_POLICY",
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "policy_commitment": _commit(b"GREMLIN-EVIDENCE-KIND-POLICY/v0.1", core),
        "authority": _authority(),
    }
