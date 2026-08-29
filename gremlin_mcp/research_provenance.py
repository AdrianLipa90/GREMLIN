from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

SCHEMA = "GREMLIN_RESEARCH_PROVENANCE_V0_1"
VERSION = "0.1.0"
_SOURCE_RECEIPT_DOMAIN = b"GREMLIN-RESEARCH-SOURCE-RECEIPT/v0.1\0"
_RECEIPT_SET_DOMAIN = b"GREMLIN-RESEARCH-SOURCE-RECEIPT-SET/v0.1\0"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def source_receipt_core(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_id": str(receipt.get("source_id") or "").strip(),
        "content_basis": str(receipt.get("content_basis") or ""),
        "content_commitment": str(receipt.get("content_commitment") or "").strip(),
        "content_length_chars": int(receipt.get("content_length_chars") or 0),
        "evidence_text": str(receipt.get("evidence_text") or ""),
    }


def source_receipt_commitment(receipt: Mapping[str, Any]) -> str:
    return _commit(_SOURCE_RECEIPT_DOMAIN, source_receipt_core(receipt))


def verify_source_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        core = source_receipt_core(receipt)
    except (TypeError, ValueError):
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "valid": False,
            "source_id": str(receipt.get("source_id") or ""),
            "errors": ["INVALID_RECEIPT_FIELD_TYPE"],
            "expected_commitment": None,
        }

    if not core["source_id"]:
        errors.append("SOURCE_ID_MISSING")
    if not core["content_basis"]:
        errors.append("CONTENT_BASIS_MISSING")
    if not core["content_commitment"]:
        errors.append("CONTENT_COMMITMENT_MISSING")
    if not core["evidence_text"]:
        errors.append("EVIDENCE_TEXT_MISSING")
    if core["content_length_chars"] != len(core["evidence_text"]):
        errors.append("CONTENT_LENGTH_MISMATCH")

    expected = _commit(_SOURCE_RECEIPT_DOMAIN, core)
    supplied = str(receipt.get("source_receipt_commitment") or "").strip()
    if not supplied:
        errors.append("SOURCE_RECEIPT_COMMITMENT_MISSING")
    elif supplied != expected:
        errors.append("SOURCE_RECEIPT_COMMITMENT_MISMATCH")

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "valid": not errors,
        "source_id": core["source_id"],
        "errors": errors,
        "expected_commitment": expected,
    }


def verify_source_receipt_set(
    receipts: Iterable[Mapping[str, Any]],
    *,
    citations: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    rows = [dict(row) for row in receipts]
    citation_rows = [dict(row) for row in citations]
    validations = [verify_source_receipt(row) for row in rows]
    errors: list[dict[str, Any]] = []

    source_ids = [str(row.get("source_id") or "").strip() for row in rows]
    for sid in sorted({sid for sid in source_ids if sid and source_ids.count(sid) > 1}):
        errors.append({"source_id": sid, "code": "DUPLICATE_SOURCE_RECEIPT"})

    for validation in validations:
        for code in validation["errors"]:
            errors.append({"source_id": validation["source_id"], "code": code})

    receipt_by_id = {
        str(row.get("source_id") or "").strip(): row
        for row in rows
        if str(row.get("source_id") or "").strip()
    }
    citation_ids: list[str] = []
    for citation in citation_rows:
        sid = str(citation.get("source_id") or "").strip()
        if not sid:
            errors.append({"source_id": "", "code": "CITATION_SOURCE_ID_MISSING"})
            continue
        citation_ids.append(sid)
        receipt = receipt_by_id.get(sid)
        if receipt is None:
            errors.append({"source_id": sid, "code": "CITATION_SOURCE_RECEIPT_MISSING"})
            continue
        if str(citation.get("content_commitment") or "").strip() != str(receipt.get("content_commitment") or "").strip():
            errors.append({"source_id": sid, "code": "CITATION_CONTENT_COMMITMENT_MISMATCH"})
        if str(citation.get("content_basis") or "") != str(receipt.get("content_basis") or ""):
            errors.append({"source_id": sid, "code": "CITATION_CONTENT_BASIS_MISMATCH"})

    for sid in sorted(set(receipt_by_id) - set(citation_ids)):
        errors.append({"source_id": sid, "code": "ORPHAN_SOURCE_RECEIPT"})

    commitment_basis = [
        {
            "source_id": str(row.get("source_id") or "").strip(),
            "source_receipt_commitment": str(row.get("source_receipt_commitment") or "").strip(),
        }
        for row in rows
    ]
    commitment_basis.sort(key=lambda row: row["source_id"])
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "valid": not errors,
        "errors": errors,
        "receipt_count": len(rows),
        "citation_count": len(citation_rows),
        "receipt_set_commitment": _commit(_RECEIPT_SET_DOMAIN, commitment_basis),
        "receipt_validations": validations,
        "authority": {
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        },
    }
