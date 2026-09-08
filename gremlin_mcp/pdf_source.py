from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from gremlin_mcp.composite_math_layout import solve_composite_2d_equation
from gremlin_mcp.math_layout_solver import solve_simple_2d_equation
from gremlin_mcp.pdf_math_layout import classify_equation_region

SCHEMA = "GREMLIN_PDF_SPAN_SOURCE_V0_1"
VERSION = "0.3.0"
_EQ_LABEL_RE = re.compile(r"^\(\d+\.\d+(?:\.\d+)?\)$")
_MATH_SIGNAL_CHARS = frozenset("=+-*/·×≈<>∑∫√^_[]{}")
_NUMERIC_TOKEN_RE = re.compile(r"^[0-9.,Ee+\-−]+$")


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


def _span_center_y(span: Mapping[str, Any]) -> float:
    bbox = list(span["bbox"])
    return (float(bbox[1]) + float(bbox[3])) / 2.0


def _span_height(span: Mapping[str, Any]) -> float:
    bbox = list(span["bbox"])
    return max(float(bbox[3]) - float(bbox[1]), 1e-9)


def _normalize_page(page: Mapping[str, Any]) -> dict[str, Any]:
    number = int(page.get("page_number") or 0)
    if number < 1:
        raise ValueError("page_number must be >= 1")
    width = float(page.get("width") or 0.0)
    height = float(page.get("height") or 0.0)
    if width <= 0 or height <= 0 or not math.isfinite(width) or not math.isfinite(height):
        raise ValueError("page width and height must be positive finite values")
    spans: list[dict[str, Any]] = []
    for raw in list(page.get("spans") or []):
        text = str(raw.get("text") or "").strip()
        if not text:
            continue
        bbox = [float(value) for value in list(raw.get("bbox") or [])]
        if len(bbox) != 4 or any(not math.isfinite(value) for value in bbox):
            raise ValueError("span bbox must contain four finite values")
        size = float(raw.get("size") or max(bbox[3] - bbox[1], 1.0))
        if not math.isfinite(size) or size <= 0:
            raise ValueError("span size must be positive and finite")
        spans.append({
            "text": text,
            "bbox": bbox,
            "size": size,
            "font": raw.get("font"),
            "flags": raw.get("flags"),
            "block_index": int(raw.get("block_index", -1)),
            "line_index": int(raw.get("line_index", -1)),
            "span_index": int(raw.get("span_index", -1)),
        })
    return {"page_number": number, "width": width, "height": height, "spans": spans}


def _math_span_candidate(span: Mapping[str, Any]) -> bool:
    text = str(span.get("text") or "").strip()
    if not text:
        return False
    if _EQ_LABEL_RE.fullmatch(text):
        return True
    if any(char in text for char in _MATH_SIGNAL_CHARS):
        return True
    if _NUMERIC_TOKEN_RE.fullmatch(text):
        return True
    if " " in text:
        return False
    # PDF math renderers commonly split compact symbols such as Ghf, pi, gamma, or a denominator
    # into short independent spans. Keep these candidates; later AST parsing remains the semantic gate.
    return len(text) <= 6


def _region_for_label(
    page_spans: list[dict[str, Any]],
    label_span: Mapping[str, Any],
    *,
    vertical_margin_factor: float,
) -> list[dict[str, Any]]:
    label_y = _span_center_y(label_span)
    # Use the equation label's own rendered height rather than a page-wide median. PDF generators often
    # split one displayed equation across several adjacent text blocks, so block identity is not a safe boundary.
    margin = max(4.0, _span_height(label_span) * float(vertical_margin_factor))
    return [
        span for span in page_spans
        if abs(_span_center_y(span) - label_y) <= margin and _math_span_candidate(span)
    ]


def build_equation_regions_from_pages(
    pages: Iterable[Mapping[str, Any]],
    *,
    source_id: str,
    vertical_margin_factor: float = 1.7,
) -> dict[str, Any]:
    source = str(source_id).strip()
    if not source:
        raise ValueError("source_id must be non-empty")
    if vertical_margin_factor <= 0:
        raise ValueError("vertical_margin_factor must be positive")

    normalized_pages = [_normalize_page(page) for page in pages]
    regions: list[dict[str, Any]] = []
    safe_transcript_rows: list[str] = []
    simple_recovered_rows: list[str] = []
    composite_recovered_rows: list[str] = []
    auditable_rows: list[str] = []

    for page in normalized_pages:
        labels = [span for span in page["spans"] if _EQ_LABEL_RE.fullmatch(span["text"])]
        for label_span in labels:
            label = label_span["text"]
            region_spans = _region_for_label(
                page["spans"],
                label_span,
                vertical_margin_factor=vertical_margin_factor,
            )
            classified = classify_equation_region(
                region_spans,
                page_number=page["page_number"],
                equation_label=label,
            )
            classified["pdf_block_index"] = int(label_span.get("block_index", -1))
            classified["region_selection"] = "GEOMETRIC_BAND_MATHLIKE_CROSS_BLOCK"
            classified["simple_2d_solver"] = None
            classified["composite_2d_solver"] = None

            if classified["status"] == "LINEARIZATION_SAFE" and classified["linear_text"]:
                rendered = f"Eq. {label}: {classified['linear_text']}"
                safe_transcript_rows.append(rendered)
                auditable_rows.append(rendered)
            elif classified["status"] == "TWO_DIMENSIONAL_MATH_UNRESOLVED":
                simple = solve_simple_2d_equation(
                    region_spans,
                    page_number=page["page_number"],
                    equation_label=label,
                )
                classified["simple_2d_solver"] = simple
                if simple["status"] == "SOLVED_SIMPLE_2D" and simple["linear_text"]:
                    rendered = f"Eq. {label}: {simple['linear_text']}"
                    simple_recovered_rows.append(rendered)
                    auditable_rows.append(rendered)
                else:
                    composite = solve_composite_2d_equation(
                        region_spans,
                        page_number=page["page_number"],
                        equation_label=label,
                    )
                    classified["composite_2d_solver"] = composite
                    if composite["status"] == "SOLVED_COMPOSITE_2D" and composite["linear_text"]:
                        rendered = f"Eq. {label}: {composite['linear_text']}"
                        composite_recovered_rows.append(rendered)
                        auditable_rows.append(rendered)

            regions.append(classified)

    safe_count = sum(region["status"] == "LINEARIZATION_SAFE" for region in regions)
    simple_count = sum(
        bool(region.get("simple_2d_solver"))
        and region["simple_2d_solver"]["status"] == "SOLVED_SIMPLE_2D"
        for region in regions
    )
    composite_count = sum(
        bool(region.get("composite_2d_solver"))
        and region["composite_2d_solver"]["status"] == "SOLVED_COMPOSITE_2D"
        for region in regions
    )
    recovered_2d_count = simple_count + composite_count
    unresolved_count = len(regions) - safe_count - recovered_2d_count
    simple_transcript = "\n".join(simple_recovered_rows)
    composite_transcript = "\n".join(composite_recovered_rows)
    recovered_transcript = "\n".join(simple_recovered_rows + composite_recovered_rows)
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "source_id": source,
        "status": "PDF_EQUATION_REGIONS_READY" if regions else "NO_EQUATION_LABELS_FAIL_CLOSED",
        "page_count": len(normalized_pages),
        "equation_label_count": len(regions),
        "safe_region_count": safe_count,
        "simple_recovered_2d_count": simple_count,
        "composite_recovered_2d_count": composite_count,
        "recovered_2d_count": recovered_2d_count,
        "unresolved_region_count": unresolved_count,
        "safe_transcript": "\n".join(safe_transcript_rows),
        "simple_recovered_2d_transcript": simple_transcript,
        "composite_recovered_2d_transcript": composite_transcript,
        "recovered_2d_transcript": recovered_transcript,
        "auditable_transcript": "\n".join(auditable_rows),
        "regions": regions,
        "scope_boundary": [
            "PDF_TEXT_SPANS_WITH_LAYOUT_PROVENANCE",
            "EQUATION_LABELS_REQUIRE_NUMBERED_PARENTHESES",
            "REGION_SELECTION_CROSSES_PDF_TEXT_BLOCKS_WITHIN_LOCAL_GEOMETRIC_BAND",
            "PROSE_LIKE_SPANS_ARE_EXCLUDED_BEFORE_LAYOUT_CLASSIFICATION",
            "SINGLE_BASELINE_MATH_MAY_BE_LINEARIZED",
            "RECOVERY_ORDER_IS_SIMPLE_2D_THEN_COMPOSITE_2D",
            "SIMPLE_AND_COMPOSITE_RECOVERY_COUNTS_REMAIN_SEPARATE",
            "AMBIGUOUS_TWO_DIMENSIONAL_MATH_REMAINS_UNRESOLVED",
            "NO_OCR_OR_SEMANTIC_GUESSING",
            "NO_AUTOMATIC_CANON_PROMOTION",
        ],
        "authority": _authority(),
    }
    core["source_commitment"] = _commit(b"GREMLIN-PDF-SPAN-SOURCE/v0.1", core)
    return core


def extract_pdf_span_pages(path: str | Path) -> dict[str, Any]:
    pdf_path = Path(path)
    if not pdf_path.is_file():
        raise FileNotFoundError(pdf_path)
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("source file must be a PDF")

    try:
        import fitz  # PyMuPDF, imported lazily to keep pure layout tests lightweight.
    except ImportError as exc:  # pragma: no cover - packaging/runtime guard
        raise RuntimeError("PyMuPDF is required for PDF span extraction") from exc

    raw_bytes = pdf_path.read_bytes()
    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    pages: list[dict[str, Any]] = []
    document = fitz.open(pdf_path)
    try:
        for page_index, page in enumerate(document):
            tree = page.get_text("dict")
            spans: list[dict[str, Any]] = []
            for block_index, block in enumerate(tree.get("blocks") or []):
                if int(block.get("type", 0)) != 0:
                    continue
                for line_index, line in enumerate(block.get("lines") or []):
                    for span_index, span in enumerate(line.get("spans") or []):
                        text = str(span.get("text") or "").strip()
                        if not text:
                            continue
                        spans.append({
                            "text": text,
                            "bbox": [float(value) for value in span["bbox"]],
                            "size": float(span.get("size") or 0.0),
                            "font": span.get("font"),
                            "flags": span.get("flags"),
                            "block_index": block_index,
                            "line_index": line_index,
                            "span_index": span_index,
                        })
            pages.append({
                "page_number": page_index + 1,
                "width": float(page.rect.width),
                "height": float(page.rect.height),
                "spans": spans,
            })
    finally:
        document.close()

    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "source_name": pdf_path.name,
        "file_sha256": sha256,
        "page_count": len(pages),
        "pages": pages,
        "authority": _authority(),
    }
    core["extraction_commitment"] = _commit(b"GREMLIN-PDF-SPAN-EXTRACTION/v0.1", core)
    return core


def build_equation_regions_from_pdf(
    path: str | Path,
    *,
    source_id: str | None = None,
    vertical_margin_factor: float = 1.7,
) -> dict[str, Any]:
    extracted = extract_pdf_span_pages(path)
    resolved_source = str(source_id).strip() if source_id is not None else f"{extracted['source_name']}:{extracted['file_sha256'][:16]}"
    result = build_equation_regions_from_pages(
        extracted["pages"],
        source_id=resolved_source,
        vertical_margin_factor=vertical_margin_factor,
    )
    result["file_sha256"] = extracted["file_sha256"]
    result["extraction_commitment"] = extracted["extraction_commitment"]
    return result
