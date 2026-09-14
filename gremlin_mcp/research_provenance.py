from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

SCHEMA = "GREMLIN_RESEARCH_PROVENANCE_V0_1"
VERSION = "0.1.0"
_SOURCE_RECEIPT_DOMAIN = b"GREMLIN-RESEARCH-SOURCE-RECEIPT/v0.1\0"
_RECEIPT_SET_DOMAIN = b"GREMLIN-RESEARCH-SOURCE-RECEIPT-SET/v0.1\0"
_RECEIPT_KEYS = frozenset(
    {
        "source_id",
        "content_basis",
        "content_commitment",
        "content_length_chars",
        "evidence_text",
        "source_receipt_commitment",
    }
)


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
        raise ValueError("research provenance data must be finite JSON") from exc


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _mapping_rows(values: Iterable[Mapping[str, Any]], field: str) -> list[dict[str, Any]]:
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError(f"{field} must be an iterable of objects")
    try:
        raw = list(values)
    except TypeError as exc:
        raise ValueError(f"{field} must be an iterable of objects") from exc
    if any(not isinstance(row, Mapping) for row in raw):
        raise ValueError(f"{field} must contain only objects")
    return [dict(row) for row in raw]


def _reject_unknown_keys(value: Mapping[Any, Any], allowed: frozenset[str], field: str) -> None:
    unknown = [key for key in value if not isinstance(key, str) or key not in allowed]
    if unknown:
        raise ValueError(f"{field} contains unsupported keys: {unknown}")


def _text(value: Any, field: str, *, strip: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value.strip() if strip else value


def _nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be a non-negative integer")
    if value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def source_receipt_core(receipt: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        raise ValueError("source receipt must be an object")
    _reject_unknown_keys(receipt, _RECEIPT_KEYS, "source receipt")
    return {
        "source_id": _text(receipt.get("source_id"), "source_id", strip=True),
        "content_basis": _text(receipt.get("content_basis"), "content_basis"),
        "content_commitment": _text(receipt.get("content_commitment"), "content_commitment", strip=True),
        "content_length_chars": _nonnegative_int(receipt.get("content_length_chars"), "content_length_chars"),
        "evidence_text": _text(receipt.get("evidence_text"), "evidence_text"),
    }


def source_receipt_commitment(receipt: Mapping[str, Any]) -> str:
    return _commit(_SOURCE_RECEIPT_DOMAIN, source_receipt_core(receipt))


def verify_source_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "valid": False,
            "source_id": "",
            "errors": ["RECEIPT_MUST_BE_OBJECT"],
            "expected_commitment": None,
        }

    errors: list[str] = []
    try:
        core = source_receipt_core(receipt)
    except (TypeError, ValueError):
        source_id = receipt.get("source_id")
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "valid": False,
            "source_id": source_id.strip() if isinstance(source_id, str) else "",
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
    supplied = receipt.get("source_receipt_commitment")
    if not isinstance(supplied, str) or not supplied.strip():
        errors.append("SOURCE_RECEIPT_COMMITMENT_MISSING")
    elif supplied.strip() != expected:
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
    try:
        rows = _mapping_rows(receipts, "receipts")
        citation_rows = _mapping_rows(citations, "citations")
    except ValueError as exc:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "valid": False,
            "errors": [{"source_id": "", "code": "INVALID_RECEIPT_SET_INPUT", "detail": str(exc)}],
            "receipt_count": 0,
            "citation_count": 0,
            "receipt_set_commitment": _commit(_RECEIPT_SET_DOMAIN, []),
            "receipt_validations": [],
            "authority": _authority(),
        }

    validations = [verify_source_receipt(row) for row in rows]
    errors: list[dict[str, Any]] = []

    source_ids = [
        row.get("source_id").strip()
        for row in rows
        if isinstance(row.get("source_id"), str) and row.get("source_id").strip()
    ]
    for sid in sorted({sid for sid in source_ids if source_ids.count(sid) > 1}):
        errors.append({"source_id": sid, "code": "DUPLICATE_SOURCE_RECEIPT"})

    for validation in validations:
        for code in validation["errors"]:
            errors.append({"source_id": validation["source_id"], "code": code})

    receipt_by_id: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        sid = row.get("source_id")
        if isinstance(sid, str) and sid.strip():
            receipt_by_id[sid.strip()] = row

    citation_ids: list[str] = []
    for citation in citation_rows:
        sid_raw = citation.get("source_id")
        if not isinstance(sid_raw, str) or not sid_raw.strip():
            errors.append({"source_id": "", "code": "CITATION_SOURCE_ID_INVALID"})
            continue
        sid = sid_raw.strip()
        citation_ids.append(sid)
        receipt = receipt_by_id.get(sid)
        if receipt is None:
            errors.append({"source_id": sid, "code": "CITATION_SOURCE_RECEIPT_MISSING"})
            continue

        citation_commitment = citation.get("content_commitment")
        receipt_commitment = receipt.get("content_commitment")
        if (
            not isinstance(citation_commitment, str)
            or not isinstance(receipt_commitment, str)
            or citation_commitment.strip() != receipt_commitment.strip()
        ):
            errors.append({"source_id": sid, "code": "CITATION_CONTENT_COMMITMENT_MISMATCH"})

        citation_basis = citation.get("content_basis")
        receipt_basis = receipt.get("content_basis")
        if (
            not isinstance(citation_basis, str)
            or not isinstance(receipt_basis, str)
            or citation_basis != receipt_basis
        ):
            errors.append({"source_id": sid, "code": "CITATION_CONTENT_BASIS_MISMATCH"})

    for sid in sorted(set(receipt_by_id) - set(citation_ids)):
        errors.append({"source_id": sid, "code": "ORPHAN_SOURCE_RECEIPT"})

    commitment_basis = [
        {
            "source_id": validation["source_id"],
            "source_receipt_commitment": validation["expected_commitment"],
        }
        for validation in validations
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
        "authority": _authority(),
    }
