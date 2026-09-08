from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
from typing import Any, Iterable, Mapping

SCHEMA = "GREMLIN_COMPOSITE_2D_MATH_LAYOUT_V0_1"
VERSION = "0.1.0"
_LABEL_RE = re.compile(r"^\(\d+\.\d+(?:\.\d+)?\)$")
_RELATIONS = {"=", "≈"}
_OPERATORS = {"+", "-", "*", "/", "≈", "=", "<", ">", "<=", ">="}


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


def _norm(text: str) -> str:
    return (
        str(text).strip()
        .replace("×", "*")
        .replace("·", "*")
        .replace("⋅", "*")
        .replace("−", "-")
        .replace("–", "-")
    )


def _validate(spans: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in spans:
        text = str(raw.get("text") or "").strip()
        if not text:
            continue
        bbox = [float(value) for value in list(raw.get("bbox") or [])]
        if len(bbox) != 4 or any(not math.isfinite(value) for value in bbox):
            raise ValueError("span bbox must contain four finite coordinates")
        if bbox[2] < bbox[0] or bbox[3] < bbox[1]:
            raise ValueError("span bbox coordinates are inverted")
        size = float(raw.get("size") or max(bbox[3] - bbox[1], 1.0))
        if not math.isfinite(size) or size <= 0:
            raise ValueError("span size must be positive and finite")
        rows.append({"text": text, "bbox": bbox, "size": size})
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
    ax0, _, ax1, _ = [float(value) for value in a["bbox"]]
    bx0, _, bx1, _ = [float(value) for value in b["bbox"]]
    overlap = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    smaller = max(min(ax1 - ax0, bx1 - bx0), 1e-9)
    return overlap / smaller


def _operand_like(token: str) -> bool:
    value = str(token).strip()
    if not value or value in _OPERATORS:
        return False
    if value in {"(", "[", "{"}:
        return False
    return True


def _join_tokens(tokens: list[str]) -> str:
    clean = [_norm(token) for token in tokens if _norm(token)]
    if not clean:
        return ""
    out = clean[0]
    previous = clean[0]
    for token in clean[1:]:
        if token in {')', ']', '}'}:
            out += token
        elif previous in {'(', '[', '{'}:
            out += token
        elif _operand_like(previous) and _operand_like(token):
            out += "*" + token
        else:
            out += " " + token
        previous = token
    normalized = " ".join(out.split())
    return normalized.replace(" * ", "*")


def _group_scripts(rows: list[dict[str, Any]], reference_size: float) -> tuple[list[dict[str, Any]], list[str]]:
    script_threshold = reference_size * 0.84
    small = sorted(
        [row for row in rows if float(row["size"]) <= script_threshold],
        key=lambda row: (float(row["bbox"][0]), _cy(row)),
    )
    main = [dict(row) for row in rows if float(row["size"]) > script_threshold]
    constructs: list[str] = []
    if not small or not main:
        return main + [dict(row) for row in small], constructs

    # Consecutive small glyphs at the same vertical level form one script, e.g. -11.
    groups: list[list[dict[str, Any]]] = []
    for row in small:
        if not groups:
            groups.append([row])
            continue
        previous = groups[-1][-1]
        same_level = abs(_cy(previous) - _cy(row)) <= max(2.0, reference_size * 0.30)
        gap = float(row["bbox"][0]) - float(previous["bbox"][2])
        if same_level and gap <= max(3.0, reference_size * 0.45):
            groups[-1].append(row)
        else:
            groups.append([row])

    unattached: list[dict[str, Any]] = []
    for group in groups:
        gx0 = min(float(row["bbox"][0]) for row in group)
        gy = statistics.mean(_cy(row) for row in group)
        candidates = [
            row for row in main
            if float(row["bbox"][2]) <= gx0 + 1.0
            and gx0 - float(row["bbox"][2]) <= max(6.0, reference_size * 0.75)
        ]
        if not candidates:
            unattached.extend(dict(row) for row in group)
            continue
        base = max(candidates, key=lambda row: float(row["bbox"][2]))
        script_text = "".join(_norm(row["text"]) for row in sorted(group, key=lambda row: float(row["bbox"][0])))
        if not script_text:
            unattached.extend(dict(row) for row in group)
            continue
        if gy < _cy(base):
            base["text"] = f"{_norm(base['text'])}**{script_text}"
            constructs.append("SUPERSCRIPT")
        else:
            base["text"] = f"{_norm(base['text'])}_{script_text}"
            constructs.append("SUBSCRIPT")

    return main + unattached, constructs


def _y_clusters(rows: list[dict[str, Any]], tolerance: float) -> list[list[dict[str, Any]]]:
    if not rows:
        return []
    ordered = sorted(rows, key=lambda row: (_cy(row), float(row["bbox"][0])))
    clusters: list[list[dict[str, Any]]] = [[ordered[0]]]
    for row in ordered[1:]:
        center = statistics.mean(_cy(value) for value in clusters[-1])
        if abs(_cy(row) - center) <= tolerance:
            clusters[-1].append(row)
        else:
            clusters.append([row])
    return clusters


def _render_horizontal(rows: list[dict[str, Any]]) -> str:
    ordered = sorted(rows, key=lambda row: (float(row["bbox"][0]), float(row["bbox"][1])))
    return _join_tokens([str(row["text"]) for row in ordered])


def _render_segment(rows: list[dict[str, Any]], reference_size: float) -> tuple[str | None, list[str], str | None]:
    if not rows:
        return None, [], "EMPTY_RELATION_SEGMENT"
    scripted, constructs = _group_scripts(rows, reference_size)
    main_heights = [_height(row) for row in scripted]
    tolerance = max(2.0, statistics.median(main_heights) * 0.42)
    clusters = _y_clusters(scripted, tolerance)
    if len(clusters) == 1:
        return _render_horizontal(clusters[0]), constructs, None
    if len(clusters) != 2:
        return None, constructs, "MORE_THAN_TWO_PRIMARY_VERTICAL_LEVELS"

    upper, lower = clusters
    if statistics.mean(_cy(row) for row in upper) >= statistics.mean(_cy(row) for row in lower):
        upper, lower = lower, upper
    alignment = max((_x_overlap(a, b) for a in upper for b in lower), default=0.0)
    if alignment < 0.20:
        return None, constructs, "VERTICAL_LEVELS_NOT_FRACTION_ALIGNED"
    numerator = _render_horizontal(upper)
    denominator = _render_horizontal(lower)
    if not numerator or not denominator:
        return None, constructs, "EMPTY_FRACTION_COMPONENT"
    constructs.append("STACKED_FRACTION")
    return f"({numerator})/({denominator})", constructs, None


def _status(
    *,
    status: str,
    linear_text: str | None,
    relation_count: int,
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
        "relation_count": int(relation_count),
        "constructs": sorted(set(constructs)),
        "flags": flags,
        "source_locator": f"page:{page_number}:eq:{equation_label}",
        "provenance": {
            "page_number": int(page_number),
            "equation_label": str(equation_label),
            "spans": rows,
        },
        "scope_boundary": [
            "TOP_LEVEL_RELATIONS_MUST_BE_EXPLICIT_SPANS",
            "COMPOSITE_SOLVER_SUPPORTS_ONE_OR_TWO_PRIMARY_VERTICAL_LEVELS_PER_RELATION_SEGMENT",
            "SMALL_ADJACENT_GLYPHS_MAY_FORM_GEOMETRIC_SUBSCRIPT_OR_SUPERSCRIPT",
            "TWO_ALIGNED_PRIMARY_LEVELS_MAY_FORM_ONE_STACKED_FRACTION",
            "THREE_OR_MORE_PRIMARY_VERTICAL_LEVELS_REMAIN_UNRESOLVED",
            "NO_SEMANTIC_OR_PHYSICAL_GUESSING",
            "NO_OCR_REPAIR",
            "NO_AUTOMATIC_CANON_PROMOTION",
        ],
        "authority": _authority(),
    }
    core["solver_commitment"] = _commit(b"GREMLIN-COMPOSITE-2D-MATH/v0.1", core)
    return core


def solve_composite_2d_equation(
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

    rows = _validate(spans)
    if not any(row["text"] == label for row in rows):
        return _status(
            status="AMBIGUOUS_COMPOSITE_2D_UNRESOLVED",
            linear_text=None,
            relation_count=0,
            constructs=[],
            flags=["EQUATION_LABEL_NOT_FOUND"],
            rows=rows,
            page_number=page,
            equation_label=label,
        )

    content = [row for row in rows if row["text"] != label]
    relation_rows = sorted(
        [row for row in content if _norm(row["text"]) in _RELATIONS],
        key=lambda row: float(row["bbox"][0]),
    )
    if not relation_rows:
        return _status(
            status="AMBIGUOUS_COMPOSITE_2D_UNRESOLVED",
            linear_text=None,
            relation_count=0,
            constructs=[],
            flags=["NO_EXPLICIT_TOP_LEVEL_RELATION"],
            rows=rows,
            page_number=page,
            equation_label=label,
        )

    reference_size = statistics.median(float(row["size"]) for row in relation_rows)
    segments: list[list[dict[str, Any]]] = []
    left_bound = -math.inf
    for relation in relation_rows:
        right_bound = float(relation["bbox"][0])
        segments.append([
            row for row in content
            if row not in relation_rows
            and _cx(row) > left_bound
            and _cx(row) < right_bound
        ])
        left_bound = float(relation["bbox"][2])
    segments.append([
        row for row in content
        if row not in relation_rows and _cx(row) > left_bound
    ])

    rendered: list[str] = []
    constructs: list[str] = []
    flags: list[str] = []
    for index, segment in enumerate(segments):
        text, found_constructs, error = _render_segment(segment, reference_size)
        constructs.extend(found_constructs)
        if error or not text:
            flags.append(f"SEGMENT_{index}_{error or 'UNRENDERABLE'}")
            return _status(
                status="AMBIGUOUS_COMPOSITE_2D_UNRESOLVED",
                linear_text=None,
                relation_count=len(relation_rows),
                constructs=constructs,
                flags=flags,
                rows=rows,
                page_number=page,
                equation_label=label,
            )
        rendered.append(text)

    output = rendered[0]
    for relation, segment_text in zip(relation_rows, rendered[1:]):
        output += f" {_norm(relation['text'])} {segment_text}"

    return _status(
        status="SOLVED_COMPOSITE_2D",
        linear_text=output,
        relation_count=len(relation_rows),
        constructs=constructs,
        flags=["GEOMETRIC_COMPOSITE_RECONSTRUCTION"],
        rows=rows,
        page_number=page,
        equation_label=label,
    )
