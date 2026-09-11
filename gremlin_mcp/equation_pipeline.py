from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from gremlin_mcp.equation_bundle import run_equation_witness_bundle
from gremlin_mcp.equation_extract import propose_equation_witnesses

SCHEMA = "GREMLIN_TEXT_TO_EQUATION_AUDIT_V0_1"
VERSION = "0.1.0"


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


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
        raise ValueError("equation pipeline data must be finite JSON") from exc


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field} must be non-empty")
    return text


def _mapping_list(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise RuntimeError(f"{field} must be a list")
    if any(not isinstance(row, Mapping) for row in value):
        raise RuntimeError(f"{field} must contain only objects")
    return [dict(row) for row in value]


def _nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(f"{field} must be a non-negative integer")
    return value


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise RuntimeError(f"{field} must be a list")
    rows: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RuntimeError(f"{field} must contain only non-empty strings")
        rows.append(item.strip())
    return rows


def audit_equation_transcript(
    text: str,
    *,
    source_id: str,
    classification: str,
) -> dict[str, Any]:
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    source = _nonempty(source_id, "source_id")
    class_name = _nonempty(classification, "classification")

    extraction = propose_equation_witnesses(text, source_id=source)
    if not isinstance(extraction, Mapping):
        raise RuntimeError("equation extractor returned a non-object result")
    extraction_status = extraction.get("status")
    if extraction_status not in {"NO_TEXT_FAIL_CLOSED", "CANDIDATE_PROPOSALS_READY"}:
        raise RuntimeError(f"equation extractor returned unsupported status: {extraction_status!r}")

    if extraction_status == "NO_TEXT_FAIL_CLOSED":
        proposals = _mapping_list(extraction.get("witness_proposals"), "witness_proposals")
        unresolved = _mapping_list(extraction.get("unresolved_proposals"), "unresolved_proposals")
        if proposals or unresolved:
            raise RuntimeError("NO_TEXT_FAIL_CLOSED extractor result must not contain proposals")
        core = {
            "schema": SCHEMA,
            "version": VERSION,
            "source_id": source,
            "classification": class_name,
            "status": "NO_TEXT_FAIL_CLOSED",
            "proposal_count": 0,
            "audited_witness_count": 0,
            "pass_count": 0,
            "fail_count": 0,
            "unresolved_count": 0,
            "detected_issue_ids": [],
            "extraction": dict(extraction),
            "equation_audit": None,
            "authority": _authority(),
        }
        core["pipeline_commitment"] = _commit(b"GREMLIN-TEXT-EQUATION-PIPELINE/v0.1", core)
        return core

    proposals = _mapping_list(extraction.get("witness_proposals"), "witness_proposals")
    extraction_unresolved = _mapping_list(extraction.get("unresolved_proposals"), "unresolved_proposals")

    equation_audit: dict[str, Any] | None = None
    pass_count = 0
    fail_count = 0
    audit_unresolved = 0
    detected: list[str] = []
    audited_witness_count = 0

    if proposals:
        raw_audit = run_equation_witness_bundle(
            {
                "bundle_id": f"AUTO:{source}",
                "classification": class_name,
                "witnesses": proposals,
            }
        )
        if not isinstance(raw_audit, Mapping):
            raise RuntimeError("equation witness bundle returned a non-object result")
        equation_audit = dict(raw_audit)
        if equation_audit.get("status") != "AUDIT_COMPLETE":
            raise RuntimeError(
                f"equation witness bundle returned unsupported status: {equation_audit.get('status')!r}"
            )
        audited_witness_count = _nonnegative_int(
            equation_audit.get("witness_count"), "equation_audit.witness_count"
        )
        pass_count = _nonnegative_int(equation_audit.get("pass_count"), "equation_audit.pass_count")
        fail_count = _nonnegative_int(equation_audit.get("fail_count"), "equation_audit.fail_count")
        audit_unresolved = _nonnegative_int(
            equation_audit.get("unresolved_count"), "equation_audit.unresolved_count"
        )
        detected = _string_list(
            equation_audit.get("detected_issue_ids"), "equation_audit.detected_issue_ids"
        )
        unresolved_ids = _string_list(
            equation_audit.get("unresolved_issue_ids"), "equation_audit.unresolved_issue_ids"
        )
        if audited_witness_count != len(proposals):
            raise RuntimeError("equation audit witness_count does not match submitted proposal count")
        if pass_count + fail_count + audit_unresolved != audited_witness_count:
            raise RuntimeError("equation audit outcome counts do not sum to witness_count")
        if len(detected) != fail_count:
            raise RuntimeError("equation audit detected_issue_ids count does not match fail_count")
        if len(unresolved_ids) != audit_unresolved:
            raise RuntimeError("equation audit unresolved_issue_ids count does not match unresolved_count")

    unresolved_count = len(extraction_unresolved) + audit_unresolved
    if unresolved_count:
        status = "AUDIT_COMPLETE_WITH_UNRESOLVED"
    elif proposals:
        status = "AUDIT_COMPLETE"
    else:
        status = "NO_EXECUTABLE_WITNESSES_FAIL_CLOSED"

    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "source_id": source,
        "classification": class_name,
        "status": status,
        "proposal_count": len(proposals),
        "audited_witness_count": audited_witness_count,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "unresolved_count": unresolved_count,
        "detected_issue_ids": sorted(detected),
        "extraction": dict(extraction),
        "equation_audit": equation_audit,
        "scope_boundary": [
            "TEXT_EXTRACTION_PRODUCES_CANDIDATE_WITNESSES_ONLY",
            "ONLY_EXECUTABLE_CANDIDATES_REACH_EQUATION_AUDIT",
            "UNRESOLVED_SYMBOLS_ARE_NOT_GUESSED",
            "FAIL_MEANS_LOCAL_WITNESS_INCONSISTENCY",
            "NO_GLOBAL_PAPER_VERDICT_FROM_THIS_LAYER",
            "NO_AUTOMATIC_CANON_PROMOTION",
        ],
        "authority": _authority(),
    }
    core["pipeline_commitment"] = _commit(b"GREMLIN-TEXT-EQUATION-PIPELINE/v0.1", core)
    return core
