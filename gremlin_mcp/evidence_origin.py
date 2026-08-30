from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

from gremlin_mcp.evidence_kind import (
    CLAIM_MODE_UNKNOWN_FAIL_CLOSED,
    DIRECT_KINDS_BY_CLAIM_MODE,
    UNKNOWN_CLAIM_MODE,
    normalize_claim_mode,
    normalize_evidence_kind,
)
from gremlin_mcp.evidence_robustness import CONTRADICT, SUPPORT
from gremlin_mcp.research_provenance import verify_source_receipt

SCHEMA = "GREMLIN_EVIDENCE_ORIGIN_LINEAGE_V0_1"
VERSION = "0.1.0"

EXPERIMENT = "EXPERIMENT"
DATASET = "DATASET"
OBSERVATION_CAMPAIGN = "OBSERVATION_CAMPAIGN"
SIMULATION_RUN = "SIMULATION_RUN"
DERIVATION_LINEAGE = "DERIVATION_LINEAGE"
ENGINEERING_TEST_SERIES = "ENGINEERING_TEST_SERIES"
UNKNOWN_ORIGIN = "UNKNOWN"

ORIGIN_KINDS = {
    EXPERIMENT,
    DATASET,
    OBSERVATION_CAMPAIGN,
    SIMULATION_RUN,
    DERIVATION_LINEAGE,
    ENGINEERING_TEST_SERIES,
    UNKNOWN_ORIGIN,
}

PRIMARY_GENERATION = "PRIMARY_GENERATION"
REANALYSIS = "REANALYSIS"
REUSE = "REUSE"
REPLICATION = "REPLICATION"
DERIVED = "DERIVED"
UNKNOWN_USAGE = "UNKNOWN"
ORIGIN_USAGES = {
    PRIMARY_GENERATION,
    REANALYSIS,
    REUSE,
    REPLICATION,
    DERIVED,
    UNKNOWN_USAGE,
}

ORIGIN_POLICY_SUFFICIENT = "EVIDENCE_ORIGIN_LINEAGE_SUFFICIENT"
ORIGIN_POLICY_INSUFFICIENT = "EVIDENCE_ORIGIN_LINEAGE_INSUFFICIENT"
ORIGIN_ASSIGNMENT_INCOMPLETE = "EVIDENCE_ORIGIN_ASSIGNMENT_INCOMPLETE"
ORIGIN_ASSIGNMENT_INVALID = "EVIDENCE_ORIGIN_ASSIGNMENT_INVALID"
ORIGIN_UNKNOWN_FAIL_CLOSED = "EVIDENCE_ORIGIN_UNKNOWN_FAIL_CLOSED"
CONFLICT_DEFER_TO_HOUND = "EVIDENCE_ORIGIN_CONFLICT_DEFER_TO_HOUND"
NO_DIRECT_EVIDENCE = "NO_DIRECT_EVIDENCE_FOR_ORIGIN_POLICY"

DEFAULT_MIN_ORIGIN_GROUPS_BY_CLAIM_MODE = {
    "EMPIRICAL": 2,
    "THEORETICAL": 1,
    "ENGINEERING": 2,
    UNKNOWN_CLAIM_MODE: 1,
}


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


def _normalize_origin_ref(ref: Mapping[str, Any]) -> dict[str, str]:
    kind = str(ref.get("origin_kind") or UNKNOWN_ORIGIN).strip().upper() or UNKNOWN_ORIGIN
    if kind not in ORIGIN_KINDS:
        raise ValueError(f"unsupported origin kind: {kind}")
    usage = str(ref.get("usage") or UNKNOWN_USAGE).strip().upper() or UNKNOWN_USAGE
    if usage not in ORIGIN_USAGES:
        raise ValueError(f"unsupported origin usage: {usage}")
    origin_id = str(ref.get("origin_id") or "").strip()
    if kind == UNKNOWN_ORIGIN:
        origin_id = origin_id or "UNKNOWN"
    elif not origin_id:
        raise ValueError("known origin_kind requires non-empty origin_id")
    return {
        "origin_id": origin_id,
        "origin_kind": kind,
        "usage": usage,
    }


def normalize_origin_refs(refs: Iterable[Mapping[str, Any]] | None) -> list[dict[str, str]]:
    rows = [_normalize_origin_ref(ref) for ref in (refs or [])]
    if not rows:
        rows = [{"origin_id": "UNKNOWN", "origin_kind": UNKNOWN_ORIGIN, "usage": UNKNOWN_USAGE}]
    unique = {
        (row["origin_id"], row["origin_kind"], row["usage"]): row
        for row in rows
    }
    return [
        unique[key]
        for key in sorted(unique)
    ]


def evidence_origin_assignment_core(assignment: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_id": str(assignment.get("source_id") or "").strip(),
        "content_commitment": str(assignment.get("content_commitment") or "").strip(),
        "origin_refs": normalize_origin_refs(assignment.get("origin_refs")),
        "producer_id": str(assignment.get("producer_id") or "").strip(),
        "producer_version": str(assignment.get("producer_version") or "").strip(),
        "model_id": None if assignment.get("model_id") is None else str(assignment.get("model_id")),
        "mode": str(assignment.get("mode") or "").strip(),
        "rationale_code": str(assignment.get("rationale_code") or "UNSPECIFIED").strip().upper(),
    }


def evidence_origin_assignment_commitment(assignment: Mapping[str, Any]) -> str:
    return _commit(
        b"GREMLIN-EVIDENCE-ORIGIN-ASSIGNMENT/v0.1",
        evidence_origin_assignment_core(assignment),
    )


def build_evidence_origin_assignment(
    *,
    source_receipt: Mapping[str, Any],
    origin_refs: Iterable[Mapping[str, Any]] | None,
    producer_id: str,
    producer_version: str,
    mode: str,
    rationale_code: str = "EXPLICIT_ORIGIN_ASSIGNMENT",
    model_id: str | None = None,
) -> dict[str, Any]:
    receipt_validation = verify_source_receipt(source_receipt)
    if not receipt_validation["valid"]:
        raise ValueError(f"source receipt failed integrity validation: {receipt_validation['errors']}")
    core = {
        "source_id": _nonempty(source_receipt.get("source_id"), "source_id"),
        "content_commitment": _nonempty(source_receipt.get("content_commitment"), "content_commitment"),
        "origin_refs": normalize_origin_refs(origin_refs),
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
        "assignment_commitment": _commit(b"GREMLIN-EVIDENCE-ORIGIN-ASSIGNMENT/v0.1", core),
        "origin_authority": "CANDIDATE_METADATA_ONLY",
        "inference_policy": "NO_AUTOMATIC_ORIGIN_INFERENCE_FROM_TITLE_PROVIDER_OR_CITATION_COUNT",
        "authority": _authority(),
    }


def verify_evidence_origin_assignment(
    assignment: Mapping[str, Any],
    *,
    source_receipts: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        core = evidence_origin_assignment_core(assignment)
    except (TypeError, ValueError):
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "valid": False,
            "errors": ["INVALID_EVIDENCE_ORIGIN_ASSIGNMENT_FIELD"],
            "source_id": str(assignment.get("source_id") or ""),
            "authority": _authority(),
        }

    receipt_by_id: dict[str, Mapping[str, Any]] = {}
    duplicates: set[str] = set()
    for receipt in source_receipts:
        sid = str(receipt.get("source_id") or "").strip()
        if not sid:
            continue
        if sid in receipt_by_id:
            duplicates.add(sid)
        receipt_by_id[sid] = receipt

    sid = core["source_id"]
    if not sid:
        errors.append("SOURCE_ID_MISSING")
    if sid in duplicates:
        errors.append("DUPLICATE_SOURCE_RECEIPT")
    receipt = receipt_by_id.get(sid)
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

    expected = _commit(b"GREMLIN-EVIDENCE-ORIGIN-ASSIGNMENT/v0.1", core)
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

    known_origins = [
        ref for ref in core["origin_refs"]
        if ref["origin_kind"] != UNKNOWN_ORIGIN and ref["origin_id"] != "UNKNOWN"
    ]
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "valid": not errors,
        "errors": errors,
        "source_id": sid,
        "known_origin_count": len(known_origins),
        "expected_assignment_commitment": expected,
        "authority": _authority(),
    }


def normalize_evidence_origin_assignments(
    assignments: Iterable[Mapping[str, Any]],
    *,
    source_receipts: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = [dict(row) for row in assignments]
    receipts = [dict(row) for row in source_receipts]
    validations = [
        verify_evidence_origin_assignment(row, source_receipts=receipts)
        for row in rows
    ]
    invalid = [
        {"index": index, "source_id": validation["source_id"], "errors": validation["errors"]}
        for index, validation in enumerate(validations)
        if not validation["valid"]
    ]
    source_ids = [str(row.get("source_id") or "").strip() for row in rows]
    duplicates = sorted({sid for sid in source_ids if sid and source_ids.count(sid) > 1})
    if duplicates:
        invalid.extend(
            {"index": -1, "source_id": sid, "errors": ["DUPLICATE_SOURCE_ORIGIN_ASSIGNMENT"]}
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
        "origin_authority": "CANDIDATE_METADATA_ONLY",
        "inference_policy": "NO_AUTOMATIC_ORIGIN_INFERENCE_FROM_TITLE_PROVIDER_OR_CITATION_COUNT",
        "authority": _authority(),
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "assignment_set_commitment": _commit(b"GREMLIN-EVIDENCE-ORIGIN-ASSIGNMENT-SET/v0.1", core),
    }


def _components(source_origin_sets: Mapping[str, set[str]]) -> list[list[str]]:
    parent = {sid: sid for sid in source_origin_sets}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    source_ids = sorted(source_origin_sets)
    for i, left in enumerate(source_ids):
        for right in source_ids[i + 1 :]:
            if source_origin_sets[left] & source_origin_sets[right]:
                union(left, right)

    groups: dict[str, list[str]] = {}
    for sid in source_ids:
        groups.setdefault(find(sid), []).append(sid)
    return sorted((sorted(members) for members in groups.values()), key=lambda row: row)


def assess_evidence_origin_lineage(
    guard_evidence: Iterable[Mapping[str, Any]],
    *,
    evidence_kind_assignments: Iterable[Mapping[str, Any]],
    origin_assignments: Iterable[Mapping[str, Any]],
    claim_mode: str | None,
    min_origin_groups: int | None = None,
) -> dict[str, Any]:
    mode = normalize_claim_mode(claim_mode)
    if mode == UNKNOWN_CLAIM_MODE:
        minimum = 1 if min_origin_groups is None else int(min_origin_groups)
    else:
        minimum = (
            DEFAULT_MIN_ORIGIN_GROUPS_BY_CLAIM_MODE[mode]
            if min_origin_groups is None
            else int(min_origin_groups)
        )
    if not 1 <= minimum <= 8:
        raise ValueError("min_origin_groups must be in [1, 8]")

    rows = [dict(row) for row in guard_evidence]
    support = [row for row in rows if str(row.get("stance") or "").strip().upper() == SUPPORT]
    contradict = [row for row in rows if str(row.get("stance") or "").strip().upper() == CONTRADICT]
    conflict = bool(support and contradict)
    candidate_rows = support if support else contradict
    candidate_stance = SUPPORT if support and not contradict else CONTRADICT if contradict and not support else None

    kind_by_source = {
        str(row.get("source_id") or "").strip(): normalize_evidence_kind(row.get("evidence_kind"))
        for row in evidence_kind_assignments
        if str(row.get("source_id") or "").strip()
    }
    origin_by_source = {
        str(row.get("source_id") or "").strip(): normalize_origin_refs(row.get("origin_refs"))
        for row in origin_assignments
        if str(row.get("source_id") or "").strip()
    }

    if conflict:
        state = CONFLICT_DEFER_TO_HOUND
        direct_source_ids: list[str] = []
        missing_origin_source_ids: list[str] = []
        unknown_origin_source_ids: list[str] = []
        groups: list[list[str]] = []
        satisfied = None
    elif mode == UNKNOWN_CLAIM_MODE:
        state = CLAIM_MODE_UNKNOWN_FAIL_CLOSED
        direct_source_ids = []
        missing_origin_source_ids = []
        unknown_origin_source_ids = []
        groups = []
        satisfied = False
    else:
        direct_kinds = DIRECT_KINDS_BY_CLAIM_MODE[mode]
        direct_source_ids = sorted(
            {
                str(row.get("evidence_id") or "").strip()
                for row in candidate_rows
                if kind_by_source.get(str(row.get("evidence_id") or "").strip()) in direct_kinds
            }
        )
        if not direct_source_ids:
            state = NO_DIRECT_EVIDENCE
            missing_origin_source_ids = []
            unknown_origin_source_ids = []
            groups = []
            satisfied = False
        else:
            missing_origin_source_ids = sorted(
                sid for sid in direct_source_ids if sid not in origin_by_source
            )
            source_origin_sets: dict[str, set[str]] = {}
            unknown_origin_source_ids = []
            for sid in direct_source_ids:
                refs = origin_by_source.get(sid)
                if refs is None:
                    continue
                known = {
                    ref["origin_id"]
                    for ref in refs
                    if ref["origin_kind"] != UNKNOWN_ORIGIN and ref["origin_id"] != "UNKNOWN"
                }
                if not known:
                    unknown_origin_source_ids.append(sid)
                else:
                    source_origin_sets[sid] = known

            if missing_origin_source_ids:
                state = ORIGIN_ASSIGNMENT_INCOMPLETE
                groups = _components(source_origin_sets) if source_origin_sets else []
                satisfied = False
            elif unknown_origin_source_ids:
                state = ORIGIN_UNKNOWN_FAIL_CLOSED
                groups = _components(source_origin_sets) if source_origin_sets else []
                satisfied = False
            else:
                groups = _components(source_origin_sets)
                satisfied = len(groups) >= minimum
                state = ORIGIN_POLICY_SUFFICIENT if satisfied else ORIGIN_POLICY_INSUFFICIENT

    assignment_refs = {
        str(row.get("source_id") or "").strip(): normalize_origin_refs(row.get("origin_refs"))
        for row in origin_assignments
        if str(row.get("source_id") or "").strip()
    }
    group_rows = []
    for members in groups:
        origins = sorted(
            {
                ref["origin_id"]
                for sid in members
                for ref in assignment_refs.get(sid, [])
                if ref["origin_kind"] != UNKNOWN_ORIGIN and ref["origin_id"] != "UNKNOWN"
            }
        )
        group_rows.append({"source_ids": members, "origin_ids": origins})

    core = {
        "state": state,
        "claim_mode": mode,
        "candidate_stance": candidate_stance,
        "minimum_origin_lineage_groups": minimum,
        "direct_source_ids": direct_source_ids,
        "missing_origin_source_ids": missing_origin_source_ids,
        "unknown_origin_source_ids": sorted(unknown_origin_source_ids),
        "origin_lineage_group_count": len(groups),
        "origin_lineage_groups": group_rows,
        "policy_satisfied": satisfied,
        "conflict_present": conflict,
        "origin_semantics": "EXPLICIT_CANDIDATE_LINEAGE_METADATA_NOT_PROOF_OF_CAUSAL_OR_STATISTICAL_INDEPENDENCE",
        "grouping_rule": "DIRECT_EVIDENCE_SOURCES_SHARING_ANY_KNOWN_ORIGIN_ID_COLLAPSE_TO_ONE_CONNECTED_LINEAGE_GROUP",
        "unknown_origin_policy": "UNKNOWN_ORIGIN_DOES_NOT_COUNT_AS_INDEPENDENT_LINEAGE",
        "inference_policy": "NO_AUTOMATIC_ORIGIN_INFERENCE_FROM_TITLE_PROVIDER_OR_CITATION_COUNT",
        "conflict_policy": "STANCE_CONFLICT_ALWAYS_DEFERRED_TO_HOUND_BEFORE_ORIGIN_POLICY",
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "lineage_commitment": _commit(b"GREMLIN-EVIDENCE-ORIGIN-LINEAGE/v0.1", core),
        "authority": _authority(),
    }
