from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from gremlin_mcp.hound_claims import hound_claim_audit
from gremlin_mcp.proposition_provider_policy import (
    PropositionProducerAdmissionError,
    PropositionProducerRegistry,
    run_registered_proposition_producer,
)

SCHEMA = "GREMLIN_PROPOSITION_HOUND_BRIDGE_V0_1"
VERSION = "0.1.0"

SEMANTIC_PRECONDITION_FAILED = "SEMANTIC_PRECONDITION_FAILED"
PROPOSITION_PROVIDER_ADMISSION_FAILED = "PROPOSITION_PROVIDER_ADMISSION_FAILED"
PROPOSITION_PRODUCER_OUTPUT_INVALID = "PROPOSITION_PRODUCER_OUTPUT_INVALID"
PROPOSITION_EVIDENCE_UNRESOLVED = "PROPOSITION_EVIDENCE_UNRESOLVED"
PROPOSITION_HOUND_AUDIT_FAILED = "PROPOSITION_HOUND_AUDIT_FAILED"
PROPOSITION_FAMILY_TOPOLOGY_MISMATCH = "PROPOSITION_FAMILY_TOPOLOGY_MISMATCH"
PROPOSITION_CONFLICT_DETECTED_UNRESOLVED = "PROPOSITION_CONFLICT_DETECTED_UNRESOLVED"
PROPOSITION_ANALYSIS_READY = "PROPOSITION_ANALYSIS_READY"


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
        raise ValueError("proposition bridge data must be finite JSON") from exc


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _strict_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field} must be boolean")
    return value


def _nonempty_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field} must be non-empty")
    return text


def _mapping_list(value: Any, field: str, *, require_nonempty: bool = False) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    if require_nonempty and not value:
        raise ValueError(f"{field} must be non-empty")
    if any(not isinstance(row, Mapping) for row in value):
        raise ValueError(f"{field} must contain only objects")
    return value


def _nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _semantic_precondition(execution: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(execution, Mapping):
        raise ValueError("execution must be an object")
    errors: list[str] = []
    semantic = execution.get("semantic_evidence")
    if not isinstance(semantic, Mapping):
        return {
            "valid": False,
            "errors": ["SEMANTIC_EVIDENCE_MISSING"],
            "claim_id": None,
            "classifications": [],
            "source_receipts": [],
            "semantic_family_set_commitment": None,
            "authority": _authority(),
        }

    validation = semantic.get("validation")
    if not isinstance(validation, Mapping):
        errors.append("SEMANTIC_VALIDATION_MISSING")
        normalized = None
        coverage = semantic.get("coverage")
    else:
        if validation.get("valid") is not True:
            errors.append("SEMANTIC_VALIDATION_NOT_VALID")
        normalized = validation.get("normalized")
        coverage = semantic.get("coverage") or validation.get("coverage")

    if not isinstance(coverage, Mapping) or coverage.get("complete") is not True:
        errors.append("SEMANTIC_COVERAGE_NOT_COMPLETE")

    if not isinstance(normalized, Mapping):
        errors.append("SEMANTIC_NORMALIZED_OUTPUT_MISSING")
        classifications: list[Mapping[str, Any]] = []
        claim_id = None
    else:
        if normalized.get("status") != "VALID":
            errors.append("SEMANTIC_NORMALIZED_OUTPUT_NOT_VALID")
        raw_classifications = normalized.get("classifications")
        try:
            classifications = _mapping_list(raw_classifications, "semantic classifications")
        except ValueError:
            errors.append("SEMANTIC_CLASSIFICATIONS_MUST_BE_LIST_OF_OBJECTS")
            classifications = []
        raw_claim_id = normalized.get("claim_id")
        if not isinstance(raw_claim_id, str) or not raw_claim_id.strip():
            claim_id = None
            errors.append("SEMANTIC_CLAIM_ID_INVALID")
        else:
            claim_id = raw_claim_id.strip()

    try:
        source_receipts = _mapping_list(
            execution.get("source_receipts"),
            "source_receipts",
            require_nonempty=True,
        )
    except ValueError:
        errors.append("SOURCE_RECEIPTS_MISSING_OR_INVALID")
        source_receipts = []

    try:
        _mapping_list(execution.get("citations"), "citations", require_nonempty=True)
    except ValueError:
        errors.append("CITATIONS_MISSING_OR_INVALID")

    family_binding = semantic.get("provenance_families")
    semantic_family_set_commitment = None
    if isinstance(family_binding, Mapping):
        family_receipt = family_binding.get("family_receipt")
        if isinstance(family_receipt, Mapping):
            raw_family_commitment = family_receipt.get("family_set_commitment")
            if raw_family_commitment is not None:
                if not isinstance(raw_family_commitment, str) or not raw_family_commitment.strip():
                    errors.append("SEMANTIC_FAMILY_SET_COMMITMENT_INVALID")
                else:
                    semantic_family_set_commitment = raw_family_commitment.strip()

    return {
        "valid": not errors,
        "errors": errors,
        "claim_id": claim_id,
        "classifications": classifications,
        "source_receipts": source_receipts,
        "semantic_family_set_commitment": semantic_family_set_commitment,
        "authority": _authority(),
    }


def _analysis_wrapper(
    *,
    precondition: Mapping[str, Any],
    proposition_output: Mapping[str, Any] | None,
    hound_audit: Mapping[str, Any] | None,
    status: str,
    reason: str | None,
) -> dict[str, Any]:
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": status,
        "reason": reason,
        "semantic_precondition": dict(precondition),
        "proposition_output": None if proposition_output is None else dict(proposition_output),
        "hound_claim_audit": None if hound_audit is None else dict(hound_audit),
        "truth_resolution": "UNRESOLVED",
        "source_content_authority": "UNTRUSTED_EVIDENCE_ONLY",
        "provider_selection_authority": "OPERATOR_CONFIGURED_LOCAL_REGISTRY_ONLY",
        "authority": _authority(),
    }
    return {
        **core,
        "proposition_bridge_commitment": _commit(
            b"GREMLIN-PROPOSITION-HOUND-BRIDGE/v0.1",
            core,
        ),
    }


def _quarantine(
    execution: Mapping[str, Any],
    *,
    precondition: Mapping[str, Any],
    proposition_output: Mapping[str, Any] | None,
    hound_audit: Mapping[str, Any] | None,
    status: str,
    reason: str,
) -> dict[str, Any]:
    result = dict(execution)
    if result.get("quarantined_synthesis") is None and result.get("synthesis") is not None:
        result["quarantined_synthesis"] = result.get("synthesis")
    result["synthesis"] = None
    result["status"] = status
    result["proposition_analysis"] = _analysis_wrapper(
        precondition=precondition,
        proposition_output=proposition_output,
        hound_audit=hound_audit,
        status=status,
        reason=reason,
    )
    result["authority"] = _authority()
    result["proposition_guarded_execution_commitment"] = _commit(
        b"GREMLIN-PROPOSITION-GUARDED-EXECUTION/v0.1",
        {
            key: value
            for key, value in result.items()
            if key != "proposition_guarded_execution_commitment"
        },
    )
    return result


def apply_registered_proposition_audit(
    execution: Mapping[str, Any],
    *,
    registry: PropositionProducerRegistry,
    producer_id: str,
    require_complete_coverage: bool = True,
    quarantine_on_direct_conflict: bool = True,
) -> dict[str, Any]:
    """Run admitted proposition extraction over an already validated semantic execution."""
    coverage_required = _strict_bool(require_complete_coverage, "require_complete_coverage")
    quarantine_conflict = _strict_bool(quarantine_on_direct_conflict, "quarantine_on_direct_conflict")
    precondition = _semantic_precondition(execution)
    if not precondition["valid"]:
        return _quarantine(
            execution,
            precondition=precondition,
            proposition_output=None,
            hound_audit=None,
            status=SEMANTIC_PRECONDITION_FAILED,
            reason="VALID_COMPLETE_SEMANTIC_EVIDENCE_AND_EXECUTION_PROVENANCE_REQUIRED",
        )

    claim_id = _nonempty_text(precondition["claim_id"], "semantic claim_id")
    try:
        proposition_output = run_registered_proposition_producer(
            registry,
            producer_id=producer_id,
            claim_id=claim_id,
            classifications=precondition["classifications"],
            source_receipts=precondition["source_receipts"],
            require_complete_coverage=coverage_required,
        )
    except PropositionProducerAdmissionError as exc:
        return _quarantine(
            execution,
            precondition=precondition,
            proposition_output=None,
            hound_audit=None,
            status=PROPOSITION_PROVIDER_ADMISSION_FAILED,
            reason=f"SEALED_REGISTRY_ADMISSION_REQUIRED:{exc}",
        )

    if not isinstance(proposition_output, Mapping) or proposition_output.get("status") != "VALID":
        return _quarantine(
            execution,
            precondition=precondition,
            proposition_output=proposition_output if isinstance(proposition_output, Mapping) else None,
            hound_audit=None,
            status=PROPOSITION_PRODUCER_OUTPUT_INVALID,
            reason="PROPOSITION_PROVIDER_OUTPUT_MUST_PASS_LOCAL_COVERAGE_INTEGRITY_AND_GROUNDING",
        )

    raw_propositions = proposition_output.get("propositions")
    if not isinstance(raw_propositions, list) or any(not isinstance(row, Mapping) for row in raw_propositions):
        return _quarantine(
            execution,
            precondition=precondition,
            proposition_output=proposition_output,
            hound_audit=None,
            status=PROPOSITION_PRODUCER_OUTPUT_INVALID,
            reason="VALID_PROPOSITION_OUTPUT_REQUIRES_A_LIST_OF_PROPOSITION_OBJECTS",
        )
    propositions = raw_propositions
    if not propositions:
        return _quarantine(
            execution,
            precondition=precondition,
            proposition_output=proposition_output,
            hound_audit=None,
            status=PROPOSITION_EVIDENCE_UNRESOLVED,
            reason="NO_GROUNDED_PROPOSITION_FRAME_AVAILABLE_AFTER_EXPLICIT_SOURCE_DECISIONS",
        )

    hound_audit = hound_claim_audit(
        propositions,
        citations=execution.get("citations"),
    )
    if not isinstance(hound_audit, Mapping) or hound_audit.get("status") in {
        "INVALID_PROPOSITION_SET_FAIL_CLOSED",
        "PROPOSITION_SOURCE_FAMILY_BINDING_FAILED",
    }:
        return _quarantine(
            execution,
            precondition=precondition,
            proposition_output=proposition_output,
            hound_audit=hound_audit if isinstance(hound_audit, Mapping) else None,
            status=PROPOSITION_HOUND_AUDIT_FAILED,
            reason="HOUND_CLAIM_AUDIT_MUST_BIND_TO_CURRENT_PROVENANCE_FAMILIES",
        )

    semantic_family = precondition.get("semantic_family_set_commitment")
    hound_family = hound_audit.get("family_set_commitment")
    if semantic_family is not None:
        if not isinstance(hound_family, str) or hound_family.strip() != semantic_family:
            return _quarantine(
                execution,
                precondition=precondition,
                proposition_output=proposition_output,
                hound_audit=hound_audit,
                status=PROPOSITION_FAMILY_TOPOLOGY_MISMATCH,
                reason="SEMANTIC_AND_HOUND_LAYERS_MUST_SHARE_THE_EXACT_FAMILY_SET_COMMITMENT",
            )

    try:
        direct_conflicts = _nonnegative_int(
            hound_audit.get("cross_family_conflict_candidate_count"),
            "cross_family_conflict_candidate_count",
        ) + _nonnegative_int(
            hound_audit.get("intra_family_conflict_candidate_count"),
            "intra_family_conflict_candidate_count",
        )
    except ValueError:
        return _quarantine(
            execution,
            precondition=precondition,
            proposition_output=proposition_output,
            hound_audit=hound_audit,
            status=PROPOSITION_HOUND_AUDIT_FAILED,
            reason="HOUND_CONFLICT_COUNTS_MUST_BE_EXACT_NONNEGATIVE_INTEGERS",
        )

    if quarantine_conflict and direct_conflicts > 0:
        return _quarantine(
            execution,
            precondition=precondition,
            proposition_output=proposition_output,
            hound_audit=hound_audit,
            status=PROPOSITION_CONFLICT_DETECTED_UNRESOLVED,
            reason="EXACT_FRAME_POLARITY_CONFLICT_REQUIRES_EXPLICIT_RECONCILIATION_BEFORE_SYNTHESIS",
        )

    result = dict(execution)
    result["proposition_analysis"] = _analysis_wrapper(
        precondition=precondition,
        proposition_output=proposition_output,
        hound_audit=hound_audit,
        status=PROPOSITION_ANALYSIS_READY,
        reason=None,
    )
    result["proposition_analysis"]["synthesis_authorized"] = result.get("synthesis") is not None
    result["proposition_analysis"]["upstream_quarantine_preserved"] = (
        result.get("synthesis") is None and result.get("quarantined_synthesis") is not None
    )
    result["authority"] = _authority()
    result["proposition_guarded_execution_commitment"] = _commit(
        b"GREMLIN-PROPOSITION-GUARDED-EXECUTION/v0.1",
        {
            key: value
            for key, value in result.items()
            if key != "proposition_guarded_execution_commitment"
        },
    )
    return result
