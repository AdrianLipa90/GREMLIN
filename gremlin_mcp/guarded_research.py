from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

from gremlin_mcp.evidence_robustness import (
    CONTRADICTION_DETECTED_UNRESOLVED,
    assess_evidence_bundle,
    build_evidence_bundle,
    excerpt_commitment,
)
from gremlin_mcp.research_executor import execute_research
from gremlin_mcp.research_provenance import verify_source_receipt_set

SCHEMA = "GREMLIN_GUARDED_RESEARCH_V0_1"
VERSION = "0.1.3"
SOURCE_BINDING_FAILED = "CLAIM_EVIDENCE_SOURCE_BINDING_FAILED"
CONTENT_BINDING_FAILED = "CLAIM_EVIDENCE_CONTENT_BINDING_FAILED"
SOURCE_RECEIPT_INTEGRITY_FAILED = "SOURCE_RECEIPT_INTEGRITY_FAILED"


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
        raise ValueError("guarded research data must be finite JSON") from exc


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _authority() -> dict[str, bool]:
    return {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False}


def _strict_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field} must be non-empty")
    return text


def _strict_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field} must be boolean")
    return value


def _mapping_rows(values: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{field} must be a list/tuple of objects")
    if any(not isinstance(row, Mapping) for row in values):
        raise ValueError(f"{field} must contain only objects")
    return [dict(row) for row in values]


def _citation_binding(execution: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(execution, Mapping):
        raise ValueError("execution must be an object")
    citations = _mapping_rows(execution.get("citations"), "execution.citations")
    source_ids = [_strict_text(row.get("source_id"), "citation.source_id") for row in citations]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("execution citations contain duplicate source_id values")
    basis = [
        {
            "source_id": sid,
            "provider": row.get("provider"),
            "title": row.get("title"),
            "url": row.get("url"),
            "doi": row.get("doi"),
            "published": row.get("published"),
            "content_basis": row.get("content_basis"),
            "content_commitment": row.get("content_commitment"),
        }
        for sid, row in zip(source_ids, citations)
    ]
    basis.sort(key=lambda row: row["source_id"])
    return {
        "source_ids": source_ids,
        "source_set_commitment": _commit(b"GREMLIN-EXECUTION-SOURCE-SET/v0.2", basis),
        "citation_count": len(basis),
    }


def _content_binding(execution: Mapping[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    receipts = _mapping_rows(execution.get("source_receipts"), "execution.source_receipts")
    citations = execution.get("citations")
    receipt_integrity = verify_source_receipt_set(receipts, citations=citations)
    errors: list[dict[str, Any]] = list(receipt_integrity["errors"])
    by_id: dict[str, Mapping[str, Any]] = {}
    for receipt in receipts:
        sid = receipt.get("source_id")
        if not isinstance(sid, str) or not sid.strip():
            continue
        normalized_sid = sid.strip()
        if normalized_sid in by_id:
            continue
        by_id[normalized_sid] = receipt

    for row in rows:
        sid = _strict_text(row.get("evidence_id"), "evidence_id")
        receipt = by_id.get(sid)
        if receipt is None:
            errors.append({"evidence_id": sid, "code": "SOURCE_RECEIPT_MISSING"})
            continue

        supplied_content = _strict_text(row.get("content_commitment"), "content_commitment")
        expected_raw = receipt.get("content_commitment")
        if not isinstance(expected_raw, str) or not expected_raw.strip():
            errors.append({"evidence_id": sid, "code": "EXECUTION_CONTENT_COMMITMENT_INVALID"})
        elif supplied_content != expected_raw.strip():
            errors.append({"evidence_id": sid, "code": "CONTENT_COMMITMENT_MISMATCH"})

        excerpt = _strict_text(row.get("excerpt"), "excerpt")
        evidence_text = receipt.get("evidence_text")
        if not isinstance(evidence_text, str):
            errors.append({"evidence_id": sid, "code": "EXECUTION_EVIDENCE_TEXT_INVALID"})
        elif excerpt not in evidence_text:
            errors.append({"evidence_id": sid, "code": "EXCERPT_NOT_IN_EXECUTION_CONTENT"})

        expected_excerpt = excerpt_commitment(excerpt)
        supplied_excerpt = _strict_text(row.get("excerpt_commitment"), "excerpt_commitment")
        if supplied_excerpt != expected_excerpt:
            errors.append({"evidence_id": sid, "code": "EXCERPT_COMMITMENT_MISMATCH"})

        payload = _strict_text(row.get("payload_commitment"), "payload_commitment")
        if payload != expected_excerpt:
            errors.append({"evidence_id": sid, "code": "PAYLOAD_NOT_BOUND_TO_EXCERPT"})

    validation_by_id = {
        validation["source_id"]: validation
        for validation in receipt_integrity.get("receipt_validations", [])
        if isinstance(validation, Mapping)
        and isinstance(validation.get("source_id"), str)
        and validation.get("source_id")
    }
    receipt_basis = []
    for sid in sorted(by_id):
        receipt = by_id[sid]
        validation = validation_by_id.get(sid, {})
        receipt_basis.append(
            {
                "source_id": sid,
                "content_commitment": receipt.get("content_commitment"),
                "source_receipt_commitment": validation.get("expected_commitment"),
            }
        )
    return {
        "required": True,
        "valid": not errors,
        "errors": errors,
        "source_receipt_count": len(receipts),
        "source_receipt_set_commitment": _commit(b"GREMLIN-SOURCE-RECEIPT-SET/v0.1", receipt_basis),
        "receipt_integrity": receipt_integrity,
        "binding_rule": "VERIFIED_SOURCE_RECEIPT+SOURCE_ID+CONTENT_COMMITMENT+LITERAL_EXCERPT+EXCERPT_COMMITMENT",
    }


def _quarantine(
    execution: Mapping[str, Any],
    *,
    status: str,
    claim_id: str,
    bundle: Mapping[str, Any],
    source_binding: Mapping[str, Any],
    content_binding: Mapping[str, Any] | None,
    reason: str,
    assessment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    claim = _strict_text(claim_id, "claim_id")
    base = dict(execution)
    base["quarantined_synthesis"] = base.get("synthesis")
    base["synthesis"] = None
    base["status"] = status
    guard = {
        "schema": SCHEMA,
        "version": VERSION,
        "claim_id": claim,
        "evidence_bundle": dict(bundle),
        "assessment": None if assessment is None else dict(assessment),
        "source_binding": dict(source_binding),
        "content_binding": None if content_binding is None else dict(content_binding),
        "synthesis_authorized": False,
        "quarantine_reason": reason,
        "source_content_authority": "UNTRUSTED_EVIDENCE_ONLY",
        "semantic_stance_origin": "EXPLICIT_TYPED_INPUT_NOT_INFERRED_FROM_RETRIEVAL_METADATA",
        "authority": _authority(),
    }
    guard["guard_commitment"] = _commit(b"GREMLIN-GUARDED-RESEARCH/v0.1", guard)
    base["claim_evidence_guard"] = guard
    base["authority"] = _authority()
    base["guarded_execution_commitment"] = _commit(
        b"GREMLIN-GUARDED-EXECUTION/v0.1",
        {key: value for key, value in base.items() if key != "guarded_execution_commitment"},
    )
    return base


def apply_claim_evidence_guard(
    execution: Mapping[str, Any],
    *,
    claim_id: str,
    claim_evidence: Iterable[Mapping[str, Any]],
    hound_receipt: Mapping[str, Any] | None = None,
    require_execution_source_binding: bool = True,
    require_execution_content_binding: bool = True,
) -> dict[str, Any]:
    if not isinstance(execution, Mapping):
        raise ValueError("execution must be an object")
    claim = _strict_text(claim_id, "claim_id")
    require_source = _strict_bool(require_execution_source_binding, "require_execution_source_binding")
    require_content = _strict_bool(require_execution_content_binding, "require_execution_content_binding")
    input_rows = _mapping_rows(claim_evidence, "claim_evidence")
    bundle = build_evidence_bundle(claim_id=claim, evidence=input_rows)
    rows = [dict(row) for row in bundle["evidence"]]

    source_binding = _citation_binding(execution)
    allowed_source_ids = set(source_binding["source_ids"])
    evidence_ids = [_strict_text(row.get("evidence_id"), "evidence_id") for row in rows]
    unknown_source_ids = sorted({eid for eid in evidence_ids if eid not in allowed_source_ids})
    source_binding = {
        **source_binding,
        "required": require_source,
        "valid": not unknown_source_ids,
        "unknown_evidence_source_ids": unknown_source_ids,
    }

    if require_source and unknown_source_ids:
        return _quarantine(
            execution,
            status=SOURCE_BINDING_FAILED,
            claim_id=claim,
            bundle=bundle,
            source_binding=source_binding,
            content_binding=None,
            reason="CLAIM_EVIDENCE_MUST_REFERENCE_SOURCE_IDS_FROM_THIS_EXECUTION",
        )

    content_binding = _content_binding(execution, rows)
    content_binding["required"] = require_content
    if require_content and not content_binding["valid"]:
        receipt_integrity = content_binding["receipt_integrity"]
        status = CONTENT_BINDING_FAILED if receipt_integrity["valid"] else SOURCE_RECEIPT_INTEGRITY_FAILED
        reason = (
            "CLAIM_EVIDENCE_MUST_BIND_TO_EXACT_EXECUTION_CONTENT_AND_LITERAL_EXCERPT"
            if receipt_integrity["valid"]
            else "SOURCE_RECEIPT_INTEGRITY_MUST_VERIFY_BEFORE_SEMANTIC_ASSESSMENT"
        )
        return _quarantine(
            execution,
            status=status,
            claim_id=claim,
            bundle=bundle,
            source_binding=source_binding,
            content_binding=content_binding,
            reason=reason,
        )

    assessment = assess_evidence_bundle(bundle, hound_receipt=hound_receipt)
    if assessment["state"] == CONTRADICTION_DETECTED_UNRESOLVED:
        return _quarantine(
            execution,
            status=CONTRADICTION_DETECTED_UNRESOLVED,
            claim_id=claim,
            bundle=bundle,
            source_binding=source_binding,
            content_binding=content_binding,
            reason="TYPED_CLAIM_EVIDENCE_CONFLICT_REQUIRES_BOUND_HOUND_RECEIPT",
            assessment=assessment,
        )

    base = dict(execution)
    base["quarantined_synthesis"] = None
    guard = {
        "schema": SCHEMA,
        "version": VERSION,
        "claim_id": claim,
        "evidence_bundle": bundle,
        "assessment": assessment,
        "source_binding": source_binding,
        "content_binding": content_binding,
        "synthesis_authorized": base.get("synthesis") is not None,
        "quarantine_reason": None,
        "source_content_authority": "UNTRUSTED_EVIDENCE_ONLY",
        "semantic_stance_origin": "EXPLICIT_TYPED_INPUT_NOT_INFERRED_FROM_RETRIEVAL_METADATA",
        "authority": _authority(),
    }
    guard["guard_commitment"] = _commit(b"GREMLIN-GUARDED-RESEARCH/v0.1", guard)
    base["claim_evidence_guard"] = guard
    base["authority"] = _authority()
    base["guarded_execution_commitment"] = _commit(
        b"GREMLIN-GUARDED-EXECUTION/v0.1",
        {key: value for key, value in base.items() if key != "guarded_execution_commitment"},
    )
    return base


def execute_guarded_research(
    query: str,
    *,
    claim_id: str | None = None,
    claim_evidence: Iterable[Mapping[str, Any]] | None = None,
    hound_receipt: Mapping[str, Any] | None = None,
    providers: Iterable[str] = ("crossref", "arxiv", "duckduckgo"),
    limit_per_provider: int = 6,
    max_species: int = 4,
    max_sources: int = 12,
) -> dict[str, Any]:
    query_text = _strict_text(query, "query")
    result = execute_research(
        query_text,
        providers=providers,
        limit_per_provider=limit_per_provider,
        max_species=max_species,
        max_sources=max_sources,
    )
    if not isinstance(result, Mapping):
        raise ValueError("research execution must be an object")

    rows = [] if claim_evidence is None else _mapping_rows(claim_evidence, "claim_evidence")
    if not rows:
        base = dict(result)
        source_binding = _citation_binding(base)
        receipt_integrity = verify_source_receipt_set(
            base.get("source_receipts"),
            citations=base.get("citations"),
        )
        if not receipt_integrity["valid"] and (base.get("citations") or base.get("source_receipts")):
            base["quarantined_synthesis"] = base.get("synthesis")
            base["synthesis"] = None
            base["status"] = SOURCE_RECEIPT_INTEGRITY_FAILED
            synthesis_authorized = False
        else:
            synthesis_authorized = base.get("synthesis") is not None
        guard = {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "NO_TYPED_CLAIM_EVIDENCE" if receipt_integrity["valid"] else SOURCE_RECEIPT_INTEGRITY_FAILED,
            "semantic_contradiction_test_completed": False,
            "synthesis_authorized": synthesis_authorized,
            "source_binding": {**source_binding, "required": True},
            "content_binding": {
                "required": True,
                "completed": False,
                "receipt_integrity": receipt_integrity,
            },
            "source_content_authority": "UNTRUSTED_EVIDENCE_ONLY",
            "reason": (
                "RETRIEVAL_CONTENT_IS_NOT_AUTOMATICALLY_CLASSIFIED_AS_SUPPORT_OR_CONTRADICTION"
                if receipt_integrity["valid"]
                else "SOURCE_RECEIPT_INTEGRITY_FAILED_BEFORE_SEMANTIC_CLASSIFICATION"
            ),
            "authority": _authority(),
        }
        guard["guard_commitment"] = _commit(b"GREMLIN-GUARDED-RESEARCH/v0.1", guard)
        base["claim_evidence_guard"] = guard
        base["guarded_execution_commitment"] = _commit(
            b"GREMLIN-GUARDED-EXECUTION/v0.1",
            {key: value for key, value in base.items() if key != "guarded_execution_commitment"},
        )
        return base

    resolved_claim_id = f"query:{query_text}" if claim_id is None else _strict_text(claim_id, "claim_id")
    return apply_claim_evidence_guard(
        result,
        claim_id=resolved_claim_id,
        claim_evidence=rows,
        hound_receipt=hound_receipt,
        require_execution_source_binding=True,
        require_execution_content_binding=True,
    )
