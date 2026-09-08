from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Iterable, Mapping

SCHEMA = "GREMLIN_SIMPLE_2D_MATH_SOLVER_V0_1"
VERSION = "0.1.0"
_LABEL_RE = re.compile(r"^\(\d+\.\d+(?:\.\d+)?\)$")
_OPERATOR_TOKENS = {"+", "-", "−", "*", "×", "·", "/", "=", "≈", "<", ">", "<=", ">="}


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


def _validate_spans(spans: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in spans:
        text = str(raw.get("text") or "").strip()
        if not text:
            continue
        bbox = list(raw.get("bbox") or [])
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
            raise ValueError("span size must be positive and finite")
        rows.append({"text": text, "bbox": coords, "size": size})
    return rows


def _cx(row: Mapping[str, Any]) -> float:
    box = row["bbox"]
    return (float(box[0]) + float(box[2])) / 2.0


def _cy(row: Mapping[str, Any]) -> float:
    box = row["bbox"]
    return (float(box[1]) + float(box[3])) / 2.0


def _height(row: Mapping[str, Any]) -> float:
    box = row["bbox"]
    return max(float(box[3]) - float(box[1]), 1e-9)


def _x_overlap(a: Mapping[str, Any], b: Mapping[str, Any]) -> float:
    ax0, _, ax1, _ = [float(v) for v in a["bbox"]]
    bx0, _, bx1, _ = [float(v) for v in b["bbox"]]
    overlap = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    smaller = max(min(ax1 - ax0, bx1 - bx0), 1e-9)
    return overlap / smaller


def _normalize_token(text: str) -> str:
    return str(text).strip().replace("×", "*").replace("·", "*").replace("−", "-")


def _operand_like(token: str) -> bool:
    value = token.strip()
    if not value or value in _OPERATOR_TOKENS:
        return False
    if value in {"(", "[", "{"}:
        return False
    return True


def _horizontal_render(rows: list[Mapping[str, Any]]) -> str:
    ordered = sorted(rows, key=lambda row: (float(row["bbox"][0]), float(row["bbox"][1])))
    tokens = [_normalize_token(row["text"]) for row in ordered]
    if not tokens:
        return ""
    out = tokens[0]
    previous = tokens[0]
    for token in tokens[1:]:
        if _operand_like(previous) and _operand_like(token):
            out += "*" + token
        else:
            out += " " + token
        previous = token
    return " ".join(out.split())


def _status(
    *,
    status: str,
    linear_text: str | None,
    constructs: list[str],
    flags: list[str],
    rows: list[dict[str, Any]],
    page_number: int,
    equation_label: str,
) -> dict[str, Any]:
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": status,
        "linear_text": linear_text,
        "constructs": constructs,
        "flags": flags,
        "source_locator": f"page:{page_number}:eq:{equation_label}",
        "provenance": {
            "page_number": page_number,
            "equation_label": equation_label,
            "spans": rows,
        },
        "scope_boundary": [
            "ONLY_SINGLE_STACKED_FRACTION_OR_SIMPLE_SUPERSCRIPT_SUPPORTED",
            "AMBIGUOUS_GEOMETRY_REMAINS_UNRESOLVED",
            "NO_SEMANTIC_OR_PHYSICAL_GUESSING",
            "NO_OCR_REPAIR",
            "NO_AUTOMATIC_CANON_PROMOTION",
        ],
        "authority": _authority(),
    }
    core["solver_commitment"] = _commit(b"GREMLIN-SIMPLE-2D-MATH/v0.1", core)
    return core


def _cluster_by_x(rows: list[dict[str, Any]], gap: float) -> list[list[dict[str, Any]]]:
    if not rows:
        return []
    ordered = sorted(rows, key=lambda row: float(row["bbox"][0]))
    clusters: list[list[dict[str, Any]]] = [[ordered[0]]]
    for row in ordered[1:]:
        previous = clusters[-1][-1]
        if float(row["bbox"][0]) - float(previous["bbox"][2]) <= gap:
            clusters[-1].append(row)
        else:
            clusters.append([row])
    return clusters


def solve_simple_2d_equation(
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

    rows = _validate_spans(spans)
    labels = [row for row in rows if row["text"] == label]
    if not labels:
        return _status(
            status="UNSUPPORTED_2D_LAYOUT_UNRESOLVED",
            linear_text=None,
            constructs=[],
            flags=["EQUATION_LABEL_NOT_FOUND"],
            rows=rows,
            page_number=page,
            equation_label=label,
        )

    content = [row for row in rows if row["text"] != label]
    equals = [row for row in content if _normalize_token(row["text"]) == "="]
    if len(equals) != 1:
        return _status(
            status="UNSUPPORTED_2D_LAYOUT_UNRESOLVED",
            linear_text=None,
            constructs=[],
            flags=["EXACTLY_ONE_EQUALS_REQUIRED"],
            rows=rows,
            page_number=page,
            equation_label=label,
        )

    eq = equals[0]
    eq_x = _cx(eq)
    baseline_y = _cy(eq)
    base_height = _height(eq)
    baseline_tol = max(1.5, base_height * 0.35)

    lhs_rows = [row for row in content if float(row["bbox"][2]) < float(eq["bbox"][0])]
    rhs_rows = [row for row in content if float(row["bbox"][0]) > float(eq["bbox"][2])]
    if not lhs_rows or not rhs_rows:
        return _status(
            status="UNSUPPORTED_2D_LAYOUT_UNRESOLVED",
            linear_text=None,
            constructs=[],
            flags=["BOTH_SIDES_OF_EQUALS_REQUIRED"],
            rows=rows,
            page_number=page,
            equation_label=label,
        )

    if any(abs(_cy(row) - baseline_y) > baseline_tol for row in lhs_rows):
        return _status(
            status="UNSUPPORTED_2D_LAYOUT_UNRESOLVED",
            linear_text=None,
            constructs=[],
            flags=["NONBASELINE_LEFT_HAND_SIDE"],
            rows=rows,
            page_number=page,
            equation_label=label,
        )
    lhs = _horizontal_render(lhs_rows)

    base = [row for row in rhs_rows if abs(_cy(row) - baseline_y) <= baseline_tol]
    above = [row for row in rhs_rows if _cy(row) < baseline_y - baseline_tol]
    below = [row for row in rhs_rows if _cy(row) > baseline_y + baseline_tol]

    # Case 1: one stacked fraction and no baseline RHS token.
    if above and below and not base:
        cluster_gap = max(4.0, base_height * 0.75)
        above_clusters = _cluster_by_x(above, cluster_gap)
        below_clusters = _cluster_by_x(below, cluster_gap)
        if len(above_clusters) != 1 or len(below_clusters) != 1:
            return _status(
                status="AMBIGUOUS_2D_LAYOUT_UNRESOLVED",
                linear_text=None,
                constructs=[],
                flags=["MULTIPLE_VERTICAL_GROUPS"],
                rows=rows,
                page_number=page,
                equation_label=label,
            )
        numerator_group = above_clusters[0]
        denominator_group = below_clusters[0]
        if max((_x_overlap(a, b) for a in numerator_group for b in denominator_group), default=0.0) < 0.20:
            return _status(
                status="AMBIGUOUS_2D_LAYOUT_UNRESOLVED",
                linear_text=None,
                constructs=[],
                flags=["NUMERATOR_DENOMINATOR_NOT_ALIGNED"],
                rows=rows,
                page_number=page,
                equation_label=label,
            )
        numerator = _horizontal_render(numerator_group)
        denominator = _horizontal_render(denominator_group)
        return _status(
            status="SOLVED_SIMPLE_2D",
            linear_text=f"{lhs} = ({numerator})/({denominator})",
            constructs=["SINGLE_STACKED_FRACTION"],
            flags=["GEOMETRIC_FRACTION_RECONSTRUCTION"],
            rows=rows,
            page_number=page,
            equation_label=label,
        )

    # Case 2: baseline expression plus one or more small, raised superscript tokens.
    if base and above and not below:
        ordered_base = sorted(base, key=lambda row: float(row["bbox"][0]))
        ordered_above = sorted(above, key=lambda row: float(row["bbox"][0]))
        if len(ordered_above) != 1:
            return _status(
                status="AMBIGUOUS_2D_LAYOUT_UNRESOLVED",
                linear_text=None,
                constructs=[],
                flags=["MULTIPLE_SUPERSCRIPT_GROUPS_UNSUPPORTED"],
                rows=rows,
                page_number=page,
                equation_label=label,
            )
        exponent = ordered_above[0]
        candidates = [row for row in ordered_base if float(row["bbox"][2]) <= float(exponent["bbox"][0]) + 1.0]
        if not candidates:
            return _status(
                status="AMBIGUOUS_2D_LAYOUT_UNRESOLVED",
                linear_text=None,
                constructs=[],
                flags=["SUPERSCRIPT_HAS_NO_BASE"],
                rows=rows,
                page_number=page,
                equation_label=label,
            )
        target = max(candidates, key=lambda row: float(row["bbox"][2]))
        horizontal_gap = float(exponent["bbox"][0]) - float(target["bbox"][2])
        if horizontal_gap > max(5.0, base_height * 0.60) or float(exponent["size"]) >= float(target["size"]) * 0.95:
            return _status(
                status="AMBIGUOUS_2D_LAYOUT_UNRESOLVED",
                linear_text=None,
                constructs=[],
                flags=["SUPERSCRIPT_GEOMETRY_NOT_DECISIVE"],
                rows=rows,
                page_number=page,
                equation_label=label,
            )
        rendered_tokens: list[str] = []
        for row in ordered_base:
            token = _normalize_token(row["text"])
            if row is target:
                token = f"{token}**{_normalize_token(exponent['text'])}"
            rendered_tokens.append(token)
        rhs = rendered_tokens[0]
        previous = rendered_tokens[0]
        for token in rendered_tokens[1:]:
            if _operand_like(previous) and _operand_like(token):
                rhs += "*" + token
            else:
                rhs += " " + token
            previous = token
        return _status(
            status="SOLVED_SIMPLE_2D",
            linear_text=f"{lhs} = {' '.join(rhs.split())}",
            constructs=["SUPERSCRIPT"],
            flags=["GEOMETRIC_SUPERSCRIPT_RECONSTRUCTION"],
            rows=rows,
            page_number=page,
            equation_label=label,
        )

    return _status(
        status="UNSUPPORTED_2D_LAYOUT_UNRESOLVED",
        linear_text=None,
        constructs=[],
        flags=["LAYOUT_OUTSIDE_SIMPLE_2D_SOLVER_SCOPE"],
        rows=rows,
        page_number=page,
        equation_label=label,
    )
