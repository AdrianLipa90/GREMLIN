from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

from gremlin_mcp.evidence_kind import (
    CLAIM_MODE_UNKNOWN_FAIL_CLOSED,
    CONFLICT_DEFER_TO_HOUND,
    KIND_ASSIGNMENT_INCOMPLETE,
    KIND_POLICY_INSUFFICIENT,
    KIND_POLICY_SUFFICIENT,
    assess_evidence_kind_policy,
    normalize_evidence_kind_assignments,
)
from gremlin_mcp.semantic_quorum_bridge import apply_semantic_producer_output_with_quorum

SCHEMA = "GREMLIN_SEMANTIC_EVIDENCE_KIND_BRIDGE_V0_1"
VERSION = "0.1.0"

SEMANTIC_EVIDENCE_KIND_ASSIGNMENT_INVALID = "SEMANTIC_EVIDENCE_KIND_ASSIGNMENT_INVALID"
SEMANTIC_EVIDENCE_KIND_ASSIGNMENT_INCOMPLETE = "SEMANTIC_EVIDENCE_KIND_ASSIGNMENT_INCOMPLETE"
SEMANTIC_EVIDENCE_KIND_POLICY_INSUFFICIENT = "SEMANTIC_EVIDENCE_KIND_POLICY_INSUFFICIENT"
SEMANTIC_CLAIM_MODE_UNKNOWN = "SEMANTIC_CLAIM_MODE_UNKNOWN_FAIL_CLOSED"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _authority() -> dict[str, bool]:
    return {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False}


def _finalize(result: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(result)
    out["authority"] = _authority()
    out["semantic_kind_execution_commitment"] = _commit(
        b"GREMLIN-SEMANTIC-EVIDENCE-KIND-EXECUTION/v0.1",
        {key: value for key, value in out.items() if key != "semantic_kind_execution_commitment"},
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
    semantic["evidence_kind_assignments"] = dict(assignment_validation)
    semantic["evidence_kind_policy"] = None if policy is None else dict(policy)
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
    semantic["evidence_kind_assignments"] = dict(assignment_validation)
    semantic["evidence_kind_policy"] = None if policy is None else dict(policy)
    semantic["synthesis_authorized"] = False
    semantic["evidence_kind_quarantine_reason"] = reason
    out["semantic_evidence"] = semantic
    return _finalize(out)


def apply_semantic_producer_output_with_kind_policy(
    execution: Mapping[str, Any],
    *,
    producer_output: Mapping[str, Any],
    evidence_kind_assignments: Iterable[Mapping[str, Any]],
    claim_mode: str | None,
    hound_receipt: Mapping[str, Any] | None = None,
    require_complete_coverage: bool = True,
    min_unipolar_families: int = 2,
    min_direct_families: int = 1,
) -> dict[str, Any]:
    """Apply semantic guard + provenance-family quorum + explicit evidence-kind policy.

    Evidence kinds are caller/producer-supplied candidate metadata bound to exact source
    content commitments. This function never infers evidence kind from title/provider metadata.
    """
    base = apply_semantic_producer_output_with_quorum(
        execution,
        producer_output=producer_output,
        hound_receipt=hound_receipt,
        require_complete_coverage=require_complete_coverage,
        min_unipolar_families=min_unipolar_families,
    )

    assignments = list(evidence_kind_assignments)
    validation = normalize_evidence_kind_assignments(
        assignments,
        source_receipts=execution.get("source_receipts") or [],
    )

    # Preserve an earlier fail-closed semantic/source/content/quorum decision.
    if base.get("synthesis") is None:
        return _attach(base, assignment_validation=validation, policy=None)

    if validation["status"] != "VALID":
        return _quarantine(
            base,
            status=SEMANTIC_EVIDENCE_KIND_ASSIGNMENT_INVALID,
            assignment_validation=validation,
            policy=None,
            reason="EVIDENCE_KIND_ASSIGNMENTS_MUST_VERIFY_AGAINST_EXACT_EXECUTION_SOURCE_RECEIPTS",
        )

    semantic = dict(base.get("semantic_evidence") or {})
    family_binding = semantic.get("provenance_families")
    if not isinstance(family_binding, Mapping):
        return _quarantine(
            base,
            status=SEMANTIC_EVIDENCE_KIND_ASSIGNMENT_INCOMPLETE,
            assignment_validation=validation,
            policy=None,
            reason="DETERMINISTIC_PROVENANCE_FAMILY_BINDING_REQUIRED_BEFORE_EVIDENCE_KIND_POLICY",
        )
    guard_evidence = family_binding.get("guard_evidence")
    if not isinstance(guard_evidence, list):
        return _quarantine(
            base,
            status=SEMANTIC_EVIDENCE_KIND_ASSIGNMENT_INCOMPLETE,
            assignment_validation=validation,
            policy=None,
            reason="FAMILY_BOUND_GUARD_EVIDENCE_REQUIRED_BEFORE_EVIDENCE_KIND_POLICY",
        )

    policy = assess_evidence_kind_policy(
        guard_evidence,
        assignments=validation["assignments"],
        claim_mode=claim_mode,
        min_direct_families=min_direct_families,
    )

    # Mixed SUPPORT/CONTRADICT remains under HOUND authority; kind policy never votes it away.
    if policy["state"] == CONFLICT_DEFER_TO_HOUND:
        return _attach(base, assignment_validation=validation, policy=policy)

    if policy["state"] == KIND_POLICY_SUFFICIENT:
        return _attach(base, assignment_validation=validation, policy=policy)

    status_by_state = {
        KIND_ASSIGNMENT_INCOMPLETE: SEMANTIC_EVIDENCE_KIND_ASSIGNMENT_INCOMPLETE,
        KIND_POLICY_INSUFFICIENT: SEMANTIC_EVIDENCE_KIND_POLICY_INSUFFICIENT,
        CLAIM_MODE_UNKNOWN_FAIL_CLOSED: SEMANTIC_CLAIM_MODE_UNKNOWN,
    }
    return _quarantine(
        base,
        status=status_by_state.get(policy["state"], SEMANTIC_EVIDENCE_KIND_POLICY_INSUFFICIENT),
        assignment_validation=validation,
        policy=policy,
        reason="CLAIM_MODE_REQUIRES_COMMITMENT_BOUND_DIRECT_EVIDENCE_KIND_DIVERSITY",
    )
