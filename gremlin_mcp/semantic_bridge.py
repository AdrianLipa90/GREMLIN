from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from gremlin_mcp.guarded_research import apply_claim_evidence_guard
from gremlin_mcp.research_executor import execute_research
from gremlin_mcp.semantic_evidence import SemanticEvidenceProducer, normalize_producer_output, run_producer

SCHEMA = "GREMLIN_SEMANTIC_GUARDED_BRIDGE_V0_1"
VERSION = "0.1.0"
SEMANTIC_PRODUCER_OUTPUT_INVALID = "SEMANTIC_PRODUCER_OUTPUT_INVALID"
SEMANTIC_EVIDENCE_UNRESOLVED = "SEMANTIC_EVIDENCE_UNRESOLVED"


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


def verify_semantic_producer_output(
    output: Mapping[str, Any],
    *,
    claim_id: str,
    source_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    classifications = output.get("classifications")
    if not isinstance(classifications, list):
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "valid": False,
            "errors": ["CLASSIFICATIONS_MUST_BE_LIST"],
            "normalized": None,
            "authority": _authority(),
        }

    normalized = normalize_producer_output(
        claim_id=claim_id,
        source_receipts=source_receipts,
        classifications=classifications,
    )
    if normalized["status"] != "VALID":
        errors.append("CLASSIFICATIONS_FAIL_VALIDATION")
    if str(output.get("claim_id") or "").strip() != str(claim_id).strip():
        errors.append("CLAIM_ID_MISMATCH")
    if str(output.get("producer_output_commitment") or "").strip() != normalized["producer_output_commitment"]:
        errors.append("PRODUCER_OUTPUT_COMMITMENT_MISMATCH")
    if output.get("guard_evidence") != normalized["guard_evidence"]:
        errors.append("GUARD_EVIDENCE_DERIVATION_MISMATCH")
    if output.get("unresolved_classifications") != normalized["unresolved_classifications"]:
        errors.append("UNRESOLVED_DERIVATION_MISMATCH")
    for key in ("classification_count", "resolved_count", "unresolved_count", "invalid_count", "status"):
        if output.get(key) != normalized.get(key):
            errors.append(f"{key.upper()}_MISMATCH")

    authority = output.get("authority")
    if authority is not None and any(
        bool(authority.get(key))
        for key in ("production_runtime_write", "execution_admitted", "canon_allowed")
    ):
        errors.append("INVALID_AUTHORITY_ESCALATION")

    producer = output.get("producer")
    if producer is not None:
        declared_mode = str(producer.get("mode") or "").strip()
        if not declared_mode:
            errors.append("PRODUCER_MODE_MISSING")
        ids = {str(row.get("producer_id") or "") for row in classifications}
        versions = {str(row.get("producer_version") or "") for row in classifications}
        models = {row.get("model_id") for row in classifications}
        modes = {str(row.get("mode") or "") for row in classifications}
        if ids and ids != {str(producer.get("producer_id") or "")}:
            errors.append("PRODUCER_ID_ENVELOPE_MISMATCH")
        if versions and versions != {str(producer.get("producer_version") or "")}:
            errors.append("PRODUCER_VERSION_ENVELOPE_MISMATCH")
        if models and models != {producer.get("model_id")}:
            errors.append("MODEL_ID_ENVELOPE_MISMATCH")
        if modes and modes != {declared_mode}:
            errors.append("PRODUCER_MODE_ENVELOPE_MISMATCH")

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "valid": not errors,
        "errors": errors,
        "normalized": normalized,
        "integrity_scope": "UNKEYED_COMMITMENT_LOCAL_PIPELINE_BINDING_NOT_SENDER_AUTHENTICATION",
        "authority": _authority(),
    }


def _semantic_wrapper(
    *,
    validation: Mapping[str, Any],
    producer_output: Mapping[str, Any],
) -> dict[str, Any]:
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "validation": dict(validation),
        "producer": producer_output.get("producer"),
        "external_semantic_provider_executed": bool(producer_output.get("external_semantic_provider_executed", False)),
        "fixture_semantics_claimed_as_real": False,
        "unresolved_policy": "PRESERVE_NOT_COERCE",
        "source_family_policy": "PRODUCER_DECLARED_UNVERIFIED_NOT_INDEPENDENCE_PROOF",
        "authority": _authority(),
    }
    return {
        **core,
        "semantic_bridge_commitment": _commit(b"GREMLIN-SEMANTIC-GUARDED-BRIDGE/v0.1", core),
    }


def _quarantine_semantic(
    execution: Mapping[str, Any],
    *,
    status: str,
    validation: Mapping[str, Any],
    producer_output: Mapping[str, Any],
    reason: str,
) -> dict[str, Any]:
    result = dict(execution)
    result["quarantined_synthesis"] = result.get("synthesis")
    result["synthesis"] = None
    result["status"] = status
    result["semantic_evidence"] = {
        **_semantic_wrapper(validation=validation, producer_output=producer_output),
        "synthesis_authorized": False,
        "quarantine_reason": reason,
    }
    result["authority"] = _authority()
    result["semantic_guarded_execution_commitment"] = _commit(
        b"GREMLIN-SEMANTIC-GUARDED-EXECUTION/v0.1",
        {key: value for key, value in result.items() if key != "semantic_guarded_execution_commitment"},
    )
    return result


def apply_semantic_producer_output(
    execution: Mapping[str, Any],
    *,
    producer_output: Mapping[str, Any],
    hound_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    claim_id = str(producer_output.get("claim_id") or "").strip()
    if not claim_id:
        raise ValueError("producer output claim_id must be non-empty")
    source_receipts = list(execution.get("source_receipts") or [])
    validation = verify_semantic_producer_output(
        producer_output,
        claim_id=claim_id,
        source_receipts=source_receipts,
    )
    if not validation["valid"]:
        return _quarantine_semantic(
            execution,
            status=SEMANTIC_PRODUCER_OUTPUT_INVALID,
            validation=validation,
            producer_output=producer_output,
            reason="SEMANTIC_PRODUCER_OUTPUT_MUST_REVALIDATE_AGAINST_CURRENT_EXECUTION_RECEIPTS",
        )

    normalized = validation["normalized"]
    if normalized["resolved_count"] == 0:
        return _quarantine_semantic(
            execution,
            status=SEMANTIC_EVIDENCE_UNRESOLVED,
            validation=validation,
            producer_output=producer_output,
            reason="NO_SUPPORT_OR_CONTRADICT_CLASSIFICATION_AVAILABLE_AFTER_PRESERVING_UNRESOLVED",
        )

    guarded = apply_claim_evidence_guard(
        execution,
        claim_id=claim_id,
        claim_evidence=normalized["guard_evidence"],
        hound_receipt=hound_receipt,
        require_execution_source_binding=True,
        require_execution_content_binding=True,
    )
    result = dict(guarded)
    result["semantic_evidence"] = {
        **_semantic_wrapper(validation=validation, producer_output=producer_output),
        "synthesis_authorized": result.get("synthesis") is not None,
        "quarantine_reason": result.get("claim_evidence_guard", {}).get("quarantine_reason"),
        "resolved_count": normalized["resolved_count"],
        "unresolved_count": normalized["unresolved_count"],
    }
    result["semantic_guarded_execution_commitment"] = _commit(
        b"GREMLIN-SEMANTIC-GUARDED-EXECUTION/v0.1",
        {key: value for key, value in result.items() if key != "semantic_guarded_execution_commitment"},
    )
    return result


def execute_research_with_semantic_producer(
    query: str,
    *,
    claim_id: str,
    producer: SemanticEvidenceProducer,
    hound_receipt: Mapping[str, Any] | None = None,
    providers: Sequence[str] = ("crossref", "arxiv", "duckduckgo"),
    limit_per_provider: int = 6,
    max_species: int = 4,
    max_sources: int = 12,
) -> dict[str, Any]:
    execution = execute_research(
        query,
        providers=providers,
        limit_per_provider=limit_per_provider,
        max_species=max_species,
        max_sources=max_sources,
    )
    source_receipts = list(execution.get("source_receipts") or [])
    if not source_receipts:
        result = dict(execution)
        result["semantic_evidence"] = {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "NO_SOURCE_RECEIPTS_FAIL_CLOSED",
            "synthesis_authorized": False,
            "authority": _authority(),
        }
        result["synthesis"] = None
        result["status"] = "NO_SOURCE_RECEIPTS_FAIL_CLOSED"
        return result

    producer_output = run_producer(
        producer,
        claim_id=claim_id,
        source_receipts=source_receipts,
    )
    return apply_semantic_producer_output(
        execution,
        producer_output=producer_output,
        hound_receipt=hound_receipt,
    )
