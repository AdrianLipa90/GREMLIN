from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from gremlin_mcp.equation_pipeline import audit_equation_transcript
from gremlin_mcp.pdf_source import build_equation_regions_from_pages, build_equation_regions_from_pdf

SCHEMA = "GREMLIN_PDF_TO_EQUATION_AUDIT_V0_1"
VERSION = "0.1.0"


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


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


def _finish(
    pdf_source: Mapping[str, Any],
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

    source_result = dict(pdf_source)
    transcript = str(source_result.get("auditable_transcript") or "")
    transcript_commitment = _commit(
        b"GREMLIN-PDF-AUDITABLE-TRANSCRIPT/v0.1",
        {
            "source_id": source,
            "pdf_source_commitment": source_result.get("source_commitment"),
            "text": transcript,
        },
    )
    equation_pipeline = audit_equation_transcript(
        transcript,
        source_id=source,
        classification=class_name,
    )

    if not transcript:
        status = "NO_AUDITABLE_EQUATIONS_FAIL_CLOSED"
    elif int(equation_pipeline.get("fail_count", 0)) > 0:
        status = "PDF_EQUATION_AUDIT_COMPLETE_WITH_FINDINGS"
    elif (
        int(equation_pipeline.get("unresolved_count", 0)) > 0
        or equation_pipeline.get("status") == "NO_EXECUTABLE_WITNESSES_FAIL_CLOSED"
    ):
        status = "PDF_EQUATION_AUDIT_COMPLETE_WITH_UNRESOLVED"
    else:
        status = "PDF_EQUATION_AUDIT_COMPLETE"

    lineage = {
        "file_sha256": source_result.get("file_sha256"),
        "pdf_extraction_commitment": source_result.get("extraction_commitment"),
        "pdf_source_commitment": source_result.get("source_commitment"),
        "auditable_transcript_commitment": transcript_commitment,
        "equation_pipeline_commitment": equation_pipeline.get("pipeline_commitment"),
    }
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "source_id": source,
        "classification": class_name,
        "status": status,
        "auditable_transcript": transcript,
        "pdf_source": source_result,
        "equation_pipeline": equation_pipeline,
        "lineage": lineage,
        "scope_boundary": [
            "ONLY_PDF_REGIONS_ADMITTED_BY_PDF_SOURCE_ENTER_EQUATION_AUDIT",
            "SAFE_1D_AND_CONSERVATIVELY_RECOVERED_2D_TRANSCRIPTS_REMAIN_DISTINGUISHABLE_IN_PDF_SOURCE",
            "AMBIGUOUS_2D_MATH_NEVER_ENTERS_AUDITABLE_TRANSCRIPT",
            "PDF_EXTRACTION_AND_EQUATION_AUDIT_ARE_COMMITMENT_LINKED",
            "FAIL_MEANS_LOCAL_EQUATION_WITNESS_INCONSISTENCY_ONLY",
            "NO_GLOBAL_PAPER_VERDICT",
            "NO_AUTOMATIC_CANON_PROMOTION",
        ],
        "authority": _authority(),
    }
    core["pipeline_commitment"] = _commit(b"GREMLIN-PDF-EQUATION-PIPELINE/v0.1", core)
    return core


def audit_equations_from_pages(
    pages: Iterable[Mapping[str, Any]],
    *,
    source_id: str,
    classification: str,
    vertical_margin_factor: float = 1.7,
) -> dict[str, Any]:
    pdf_source = build_equation_regions_from_pages(
        pages,
        source_id=source_id,
        vertical_margin_factor=vertical_margin_factor,
    )
    return _finish(pdf_source, source_id=source_id, classification=classification)


def audit_equations_from_pdf(
    path: str | Path,
    *,
    source_id: str | None = None,
    classification: str,
    vertical_margin_factor: float = 1.7,
) -> dict[str, Any]:
    pdf_source = build_equation_regions_from_pdf(
        path,
        source_id=source_id,
        vertical_margin_factor=vertical_margin_factor,
    )
    resolved_source = str(source_id).strip() if source_id is not None else str(pdf_source["source_id"])
    return _finish(pdf_source, source_id=resolved_source, classification=classification)
