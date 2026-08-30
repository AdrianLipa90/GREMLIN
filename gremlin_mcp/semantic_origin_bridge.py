from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

from gremlin_mcp.evidence_origin import (
    CLAIM_MODE_UNKNOWN_FAIL_CLOSED,
    CONFLICT_DEFER_TO_HOUND,
    NO_DIRECT_EVIDENCE,
    ORIGIN_ASSIGNMENT_INCOMPLETE,
    ORIGIN_POLICY_INSUFFICIENT,
    ORIGIN_POLICY_SUFFICIENT,
    ORIGIN_UNKNOWN_FAIL_CLOSED,
    assess_evidence_origin_lineage,
    normalize_evidence_origin_assignments,
)
from gremlin_mcp.semantic_kind_bridge import apply_semantic_producer_output_with_kind_policy

SCHEMA = "GREMLIN_SEMANTIC_EVIDENCE_ORIGIN_BRIDGE_V0_1"
VERSION = "0.1.0"

SEMANTIC_EVIDENCE_ORIGIN_ASSIGNMENT_INVALID = "SEMANTIC_EVIDENCE_ORIGIN_ASSIGNMENT_INVALID"
SEMANTIC_EVIDENCE_ORIGIN_ASSIGNMENT_INCOMPLETE = "SEMANTIC_EVIDENCE_ORIGIN_ASSIGNMENT_INCOMPLETE"
SEMANTIC_EVIDENCE_ORIGIN_UNKNOWN = "SEMANTIC_EVIDENCE_ORIGIN_UNKNOWN_FAIL_CLOSED"
SEMANTIC_EVIDENCE_ORIGIN_POLICY_INSUFFICIENT = "SEMANTIC_EVIDENCE_ORIGIN_LINEAGE_INSUFFICIENT"
SEMANTIC_EVIDENCE_ORIGIN_NO_DIRECT_EVIDENCE = "SEMANTIC_EVIDENCE_ORIGIN_NO_DIRECT_EVIDENCE"
SEMANTIC_EVIDENCE_ORIGIN_CLAIM_MODE_UNKNOWN = "SEMANTIC_EVIDENCE_ORIGIN_CLAIM_MODE_UNKNOWN"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _authority() -> dict[str, bool]:
    return {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False}


def _finalize(result: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(result)
    out["authority"] = _authority()
    out["semantic_origin_execution_commitment"] = _commit(
        b"GREMLIN-SEMANTIC-EVIDENCE-ORIGIN-EXECUTION/v0.1",
        {key: value for key, value in out.items() if key != "semantic_origin_execution_commitment"},
    )
    return out


def _attach(
    result: Mapping[str, Any],
    *,
    assignment_validation: Mapping[str, Any],
    policy: Mapping[str, Any] | None,
) -> dict[str, Any]:
    out = dict(result)
    semantic = dict(out.get("semantic_evidence") or {})
    semantic["evidence_origin_assignments"] = dict(assignment_validation)
    semantic["evidence_origin_policy"] = None if policy is None else dict(policy)
    out["semantic_evidence"] = semantic
    return _finalize(out)


def _quarantine(
    result: Mapping[str, Any],
    *,
    status: str,
    assignment_validation: Mapping[str, Any],
    policy: Mapping[str, Any] | None,
    reason: str,
) -> dict[str, Any]:
    out = dict(result)
    out["quarantined_synthesis"] = out.get("synthesis")
    out["synthesis"] = None
    out["status"] = status
    semantic = dict(out.get("semantic_evidence") or {})
    semantic["evidence_origin_assignments"] = dict(assignment_validation)
    semantic["evidence_origin_policy"] = None if policy is None else dict(policy)
    semantic["synthesis_authorized"] = False
    semantic["evidence_origin_quarantine_reason"] = reason
    out["semantic_evidence"] = semantic
    return _finalize(out)


def apply_semantic_producer_output_with_origin_lineage(
    execution: Mapping[str, Any],
    *,
    producer_output: Mapping[str, Any],
    evidence_kind_assignments: Iterable[Mapping[str, Any]],
    evidence_origin_assignments: Iterable[Mapping[str, Any]],
    claim_mode: str | None,
    hound_receipt: Mapping[str, Any] | None = None,
    require_complete_coverage: bool = True,
    min_unipolar_families: int = 2,
    min_direct_families: int = 1,
    min_origin_groups: int | None = None,
) -> dict[str, Any]:
    """Apply semantic, family, kind and explicit underlying-origin lineage gates."""
    kind_assignments = list(evidence_kind_assignments)
    base = apply_semantic_producer_output_with_kind_policy(
        execution,
        producer_output=producer_output,
        evidence_kind_assignments=kind_assignments,
        claim_mode=claim_mode,
        hound_receipt=hound_receipt,
        require_complete_coverage=require_complete_coverage,
        min_unipolar_families=min_unipolar_families,
        min_direct_families=min_direct_families,
    )

    origin_assignments = list(evidence_origin_assignments)
    validation = normalize_evidence_origin_assignments(
        origin_assignments,
        source_receipts=execution.get("source_receipts") or [],
    )

    # Earlier contradiction/source/content/family/kind quarantines remain authoritative.
    if base.get("synthesis") is None:
        return _attach(base, assignment_validation=validation, policy=None)

    if validation["status"] != "VALID":
        return _quarantine(
            base,
            status=SEMANTIC_EVIDENCE_ORIGIN_ASSIGNMENT_INVALID,
            assignment_validation=validation,
            policy=None,
            reason="EVIDENCE_ORIGIN_ASSIGNMENTS_MUST_VERIFY_AGAINST_EXACT_EXECUTION_SOURCE_RECEIPTS",
        )

    semantic = dict(base.get("semantic_evidence") or {})
    family_binding = semantic.get("provenance_families")
    kind_binding = semantic.get("evidence_kind_assignments")
    if not isinstance(family_binding, Mapping) or not isinstance(kind_binding, Mapping):
        return _quarantine(
            base,
            status=SEMANTIC_EVIDENCE_ORIGIN_ASSIGNMENT_INCOMPLETE,
            assignment_validation=validation,
            policy=None,
            reason="FAMILY_AND_EVIDENCE_KIND_BINDINGS_REQUIRED_BEFORE_ORIGIN_LINEAGE_POLICY",
        )
    guard_evidence = family_binding.get("guard_evidence")
    validated_kind_assignments = kind_binding.get("assignments")
    if not isinstance(guard_evidence, list) or not isinstance(validated_kind_assignments, list):
        return _quarantine(
            base,
            status=SEMANTIC_EVIDENCE_ORIGIN_ASSIGNMENT_INCOMPLETE,
            assignment_validation=validation,
            policy=None,
            reason="FAMILY_BOUND_GUARD_EVIDENCE_AND_VALIDATED_KIND_ASSIGNMENTS_REQUIRED",
        )

    policy = assess_evidence_origin_lineage(
        guard_evidence,
        evidence_kind_assignments=validated_kind_assignments,
        origin_assignments=validation["assignments"],
        claim_mode=claim_mode,
        min_origin_groups=min_origin_groups,
    )

    # Mixed stance evidence remains HOUND-owned. Origin lineage cannot vote it away.
    if policy["state"] == CONFLICT_DEFER_TO_HOUND:
        return _attach(base, assignment_validation=validation, policy=policy)

    if policy["state"] == ORIGIN_POLICY_SUFFICIENT:
        return _attach(base, assignment_validation=validation, policy=policy)

    status_by_state = {
        ORIGIN_ASSIGNMENT_INCOMPLETE: SEMANTIC_EVIDENCE_ORIGIN_ASSIGNMENT_INCOMPLETE,
        ORIGIN_UNKNOWN_FAIL_CLOSED: SEMANTIC_EVIDENCE_ORIGIN_UNKNOWN,
        ORIGIN_POLICY_INSUFFICIENT: SEMANTIC_EVIDENCE_ORIGIN_POLICY_INSUFFICIENT,
        NO_DIRECT_EVIDENCE: SEMANTIC_EVIDENCE_ORIGIN_NO_DIRECT_EVIDENCE,
        CLAIM_MODE_UNKNOWN_FAIL_CLOSED: SEMANTIC_EVIDENCE_ORIGIN_CLAIM_MODE_UNKNOWN,
    }
    return _quarantine(
        base,
        status=status_by_state.get(policy["state"], SEMANTIC_EVIDENCE_ORIGIN_POLICY_INSUFFICIENT),
        assignment_validation=validation,
        policy=policy,
        reason="DIRECT_EVIDENCE_REQUIRES_SUFFICIENT_EXPLICIT_UNDERLYING_ORIGIN_LINEAGE_GROUPS",
    )
