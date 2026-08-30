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
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _authority() -> dict[str, bool]:
    return {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False}


def _citation_binding(execution: Mapping[str, Any]) -> dict[str, Any]:
    citations = list(execution.get("citations") or [])
    source_ids = [str(row.get("source_id") or "").strip() for row in citations]
    source_ids = [sid for sid in source_ids if sid]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("execution citations contain duplicate source_id values")
    basis = [
        {
            "source_id": str(row.get("source_id") or "").strip(),
            "provider": row.get("provider"),
            "title": row.get("title"),
            "url": row.get("url"),
            "doi": row.get("doi"),
            "published": row.get("published"),
            "content_basis": row.get("content_basis"),
            "content_commitment": row.get("content_commitment"),
        }
        for row in citations if str(row.get("source_id") or "").strip()
    ]
    basis.sort(key=lambda row: row["source_id"])
    return {
        "source_ids": source_ids,
        "source_set_commitment": _commit(b"GREMLIN-EXECUTION-SOURCE-SET/v0.2", basis),
        "citation_count": len(basis),
    }


def _content_binding(execution: Mapping[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    receipts = list(execution.get("source_receipts") or [])
    receipt_integrity = verify_source_receipt_set(receipts, citations=execution.get("citations") or [])
    errors: list[dict[str, Any]] = list(receipt_integrity["errors"])
    by_id: dict[str, Mapping[str, Any]] = {
        str(receipt.get("source_id") or "").strip(): receipt
        for receipt in receipts
        if str(receipt.get("source_id") or "").strip()
    }

    for row in rows:
        sid = str(row.get("evidence_id") or "").strip()
        receipt = by_id.get(sid)
        if receipt is None:
            errors.append({"evidence_id": sid, "code": "SOURCE_RECEIPT_MISSING"})
            continue

        supplied_content = str(row.get("content_commitment") or "").strip()
        expected_content = str(receipt.get("content_commitment") or "").strip()
        if not supplied_content:
            errors.append({"evidence_id": sid, "code": "CONTENT_COMMITMENT_MISSING"})
        elif supplied_content != expected_content:
            errors.append({"evidence_id": sid, "code": "CONTENT_COMMITMENT_MISMATCH"})

        excerpt = str(row.get("excerpt") or "")
        if not excerpt.strip():
            errors.append({"evidence_id": sid, "code": "EXCERPT_MISSING"})
            continue
        evidence_text = str(receipt.get("evidence_text") or "")
        if excerpt not in evidence_text:
            errors.append({"evidence_id": sid, "code": "EXCERPT_NOT_IN_EXECUTION_CONTENT"})

        expected_excerpt = excerpt_commitment(excerpt)
        supplied_excerpt = str(row.get("excerpt_commitment") or "").strip()
        if not supplied_excerpt:
            errors.append({"evidence_id": sid, "code": "EXCERPT_COMMITMENT_MISSING"})
        elif supplied_excerpt != expected_excerpt:
            errors.append({"evidence_id": sid, "code": "EXCERPT_COMMITMENT_MISMATCH"})

        payload = str(row.get("payload_commitment") or "").strip()
        if payload != expected_excerpt:
            errors.append({"evidence_id": sid, "code": "PAYLOAD_NOT_BOUND_TO_EXCERPT"})

    receipt_basis = [
        {
            "source_id": str(row.get("source_id") or ""),
            "content_commitment": str(row.get("content_commitment") or ""),
            "source_receipt_commitment": str(row.get("source_receipt_commitment") or ""),
        }
        for row in receipts
    ]
    receipt_basis.sort(key=lambda row: row["source_id"])
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
    base = dict(execution)
    base["quarantined_synthesis"] = base.get("synthesis")
    base["synthesis"] = None
    base["status"] = status
    guard = {
        "schema": SCHEMA,
        "version": VERSION,
        "claim_id": str(claim_id),
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
    rows = [dict(row) for row in claim_evidence]
    bundle = build_evidence_bundle(claim_id=claim_id, evidence=rows)
    source_binding = _citation_binding(execution)
    allowed_source_ids = set(source_binding["source_ids"])
    evidence_ids = [str(row.get("evidence_id") or "").strip() for row in rows]
    unknown_source_ids = sorted({eid for eid in evidence_ids if eid not in allowed_source_ids})
    source_binding = {
        **source_binding,
        "required": bool(require_execution_source_binding),
        "valid": not unknown_source_ids,
        "unknown_evidence_source_ids": unknown_source_ids,
    }

    if require_execution_source_binding and unknown_source_ids:
        return _quarantine(
            execution,
            status=SOURCE_BINDING_FAILED,
            claim_id=claim_id,
            bundle=bundle,
            source_binding=source_binding,
            content_binding=None,
            reason="CLAIM_EVIDENCE_MUST_REFERENCE_SOURCE_IDS_FROM_THIS_EXECUTION",
        )

    content_binding = _content_binding(execution, rows)
    if require_execution_content_binding and not content_binding["valid"]:
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
            claim_id=claim_id,
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
            claim_id=claim_id,
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
        "claim_id": str(claim_id),
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
    result = execute_research(
        query,
        providers=providers,
        limit_per_provider=limit_per_provider,
        max_species=max_species,
        max_sources=max_sources,
    )
    rows = list(claim_evidence or [])
    if not rows:
        base = dict(result)
        source_binding = _citation_binding(base)
        receipt_integrity = verify_source_receipt_set(
            base.get("source_receipts") or [],
            citations=base.get("citations") or [],
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
    resolved_claim_id = str(claim_id or f"query:{query}").strip()
    if not resolved_claim_id:
        raise ValueError("claim_id must be non-empty when claim_evidence is supplied")
    return apply_claim_evidence_guard(
        result,
        claim_id=resolved_claim_id,
        claim_evidence=rows,
        hound_receipt=hound_receipt,
        require_execution_source_binding=True,
        require_execution_content_binding=True,
    )
