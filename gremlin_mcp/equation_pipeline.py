from __future__ import annotations

import hashlib
import json
from typing import Any

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
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def audit_equation_transcript(
    text: str,
    *,
    source_id: str,
    classification: str,
) -> dict[str, Any]:
    source = str(source_id).strip()
    if not source:
        raise ValueError("source_id must be non-empty")
    class_name = str(classification).strip()
    if not class_name:
        raise ValueError("classification must be non-empty")

    extraction = propose_equation_witnesses(text, source_id=source)
    if extraction["status"] == "NO_TEXT_FAIL_CLOSED":
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
            "extraction": extraction,
            "equation_audit": None,
            "authority": _authority(),
        }
        core["pipeline_commitment"] = _commit(b"GREMLIN-TEXT-EQUATION-PIPELINE/v0.1", core)
        return core

    proposals = list(extraction.get("witness_proposals") or [])
    extraction_unresolved = list(extraction.get("unresolved_proposals") or [])

    equation_audit: dict[str, Any] | None = None
    pass_count = 0
    fail_count = 0
    audit_unresolved = 0
    detected: list[str] = []

    if proposals:
        equation_audit = run_equation_witness_bundle(
            {
                "bundle_id": f"AUTO:{source}",
                "classification": class_name,
                "witnesses": proposals,
            }
        )
        pass_count = int(equation_audit["pass_count"])
        fail_count = int(equation_audit["fail_count"])
        audit_unresolved = int(equation_audit["unresolved_count"])
        detected = list(equation_audit["detected_issue_ids"])

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
        "audited_witness_count": len(proposals),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "unresolved_count": unresolved_count,
        "detected_issue_ids": sorted(detected),
        "extraction": extraction,
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
