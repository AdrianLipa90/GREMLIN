from __future__ import annotations

import hashlib
import json
import math
import statistics
from typing import Any, Iterable, Mapping

SCHEMA = "GREMLIN_PDF_MATH_LAYOUT_V0_1"
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


def _validated_spans(spans: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in spans:
        text = str(raw.get("text") or "").strip()
        bbox = list(raw.get("bbox") or [])
        if not text:
            continue
        if len(bbox) != 4:
            raise ValueError("span bbox must have four coordinates")
        coords = [float(value) for value in bbox]
        if any(not math.isfinite(value) for value in coords):
            raise ValueError("span bbox coordinates must be finite")
        x0, y0, x1, y1 = coords
        if x1 < x0 or y1 < y0:
            raise ValueError("span bbox coordinates are inverted")
        size = float(raw.get("size") or max(y1 - y0, 1.0))
        if not math.isfinite(size) or size <= 0:
            raise ValueError("span font size must be positive and finite")
        rows.append({"text": text, "bbox": coords, "size": size})
    return rows


def _center_y(row: Mapping[str, Any]) -> float:
    bbox = row["bbox"]
    return (float(bbox[1]) + float(bbox[3])) / 2.0


def _height(row: Mapping[str, Any]) -> float:
    bbox = row["bbox"]
    return max(float(bbox[3]) - float(bbox[1]), 1e-9)


def _horizontal_overlap(a: Mapping[str, Any], b: Mapping[str, Any]) -> float:
    ax0, _, ax1, _ = [float(v) for v in a["bbox"]]
    bx0, _, bx1, _ = [float(v) for v in b["bbox"]]
    overlap = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    smaller = max(min(ax1 - ax0, bx1 - bx0), 1e-9)
    return overlap / smaller


def _union_bbox(rows: list[Mapping[str, Any]]) -> list[float] | None:
    if not rows:
        return None
    return [
        min(float(row["bbox"][0]) for row in rows),
        min(float(row["bbox"][1]) for row in rows),
        max(float(row["bbox"][2]) for row in rows),
        max(float(row["bbox"][3]) for row in rows),
    ]


def classify_equation_region(
    spans: Iterable[Mapping[str, Any]],
    *,
    page_number: int,
    equation_label: str,
) -> dict[str, Any]:
    page = int(page_number)
    if page < 1:
        raise ValueError("page_number must be >= 1")
    label = str(equation_label).strip()
    if not label:
        raise ValueError("equation_label must be non-empty")

    rows = _validated_spans(spans)
    label_rows = [row for row in rows if row["text"] == label]
    content = [row for row in rows if row["text"] != label]
    source_locator = f"page:{page}:eq:{label}"

    if not label_rows:
        core = {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "LABEL_NOT_FOUND_FAIL_CLOSED",
            "linear_text": None,
            "flags": ["EQUATION_LABEL_NOT_PRESENT_IN_REGION"],
            "source_locator": source_locator,
            "provenance": {
                "page_number": page,
                "equation_label": label,
                "region_bbox": _union_bbox(rows),
                "spans": rows,
            },
            "authority": _authority(),
        }
        core["layout_commitment"] = _commit(b"GREMLIN-PDF-MATH-LAYOUT/v0.1", core)
        return core

    if not content:
        status = "EMPTY_EQUATION_REGION_FAIL_CLOSED"
        flags = ["NO_MATH_SPANS_BESIDE_LABEL"]
        linear_text = None
    else:
        median_height = statistics.median(_height(row) for row in content)
        centers = [_center_y(row) for row in content]
        center_spread = max(centers) - min(centers)
        baseline_tol = max(1.5, median_height * 0.35)
        mixed_baselines = center_spread > baseline_tol

        vertical_stacking = False
        for index, left in enumerate(content):
            for right in content[index + 1 :]:
                if (
                    abs(_center_y(left) - _center_y(right)) > median_height * 0.60
                    and _horizontal_overlap(left, right) >= 0.25
                ):
                    vertical_stacking = True
                    break
            if vertical_stacking:
                break

        flags = []
        if mixed_baselines:
            flags.append("MIXED_BASELINES_DETECTED")
        if vertical_stacking:
            flags.append("VERTICAL_STACKING_DETECTED")

        if mixed_baselines or vertical_stacking:
            status = "TWO_DIMENSIONAL_MATH_UNRESOLVED"
            linear_text = None
        else:
            ordered = sorted(content, key=lambda row: (float(row["bbox"][0]), float(row["bbox"][1])))
            linear_text = " ".join(row["text"] for row in ordered)
            status = "LINEARIZATION_SAFE"
            flags.append("SINGLE_BASELINE_LAYOUT")

    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": status,
        "linear_text": linear_text,
        "flags": flags,
        "source_locator": source_locator,
        "provenance": {
            "page_number": page,
            "equation_label": label,
            "region_bbox": _union_bbox(rows),
            "spans": rows,
        },
        "scope_boundary": [
            "GEOMETRY_CLASSIFICATION_ONLY",
            "SINGLE_BASELINE_MATH_MAY_BE_LINEARIZED",
            "TWO_DIMENSIONAL_LAYOUT_IS_NOT_GUESSED",
            "NO_OCR_SEMANTIC_REPAIR",
            "NO_AUTOMATIC_CANON_PROMOTION",
        ],
        "authority": _authority(),
    }
    core["layout_commitment"] = _commit(b"GREMLIN-PDF-MATH-LAYOUT/v0.1", core)
    return core
