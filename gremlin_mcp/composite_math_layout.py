from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
from collections import defaultdict
from typing import Any, Iterable, Mapping

from gremlin_mcp.math_token_normalize import normalize_math_tokens

SCHEMA = "GREMLIN_COMPOSITE_2D_MATH_LAYOUT_V0_1"
VERSION = "0.3.2"
_LABEL_RE = re.compile(r"^\(\d+\.\d+(?:\.\d+)?\)$")
_RELATIONS = {"=", "≈"}
_OPERATORS = {"+", "-", "*", "/", "≈", "=", "<", ">", "<=", ">="}


def _authority() -> dict[str, bool]:
    return {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False}


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
        raise ValueError("composite math layout data must be finite JSON") from exc


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _text(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not allow_empty and not text:
        raise ValueError(f"{field} must be non-empty")
    return text


def _number(value: Any, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number")
    if positive and number <= 0:
        raise ValueError(f"{field} must be positive and finite")
    return number


def _norm(value: Any) -> str:
    text = _text(value, "math token", allow_empty=True)
    return text.replace("×", "*").replace("·", "*").replace("⋅", "*").replace("−", "-").replace("–", "-")


def _bbox(row: Mapping[str, Any]) -> list[float]:
    value = row.get("bbox")
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError("span bbox must contain four finite coordinates")
    coordinates = [_number(item, "span bbox coordinate") for item in value]
    if coordinates[2] < coordinates[0] or coordinates[3] < coordinates[1]:
        raise ValueError("span bbox coordinates are inverted")
    return coordinates


def _cx(row: Mapping[str, Any]) -> float:
    box = row["bbox"]
    return (box[0] + box[2]) / 2


def _cy(row: Mapping[str, Any]) -> float:
    box = row["bbox"]
    return (box[1] + box[3]) / 2


def _height(row: Mapping[str, Any]) -> float:
    box = row["bbox"]
    return max(box[3] - box[1], 1e-9)


def _x_overlap(a: Mapping[str, Any], b: Mapping[str, Any]) -> float:
    ax0, _, ax1, _ = a["bbox"]
    bx0, _, bx1, _ = b["bbox"]
    return max(0.0, min(ax1, bx1) - max(ax0, bx0)) / max(min(ax1 - ax0, bx1 - bx0), 1e-9)


def _operand_like(token: str) -> bool:
    return bool(token) and token not in _OPERATORS and token not in {"(", "[", "{"}


def _closing_with_script(token: str) -> bool:
    return any(token.startswith(prefix) for prefix in (")**", "]**", "}**", ")_", "]_", "}_"))


def _validate(spans: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(spans, (str, bytes, Mapping)):
        raise ValueError("spans must be an iterable of objects")
    try:
        raw_rows = list(spans)
    except TypeError as exc:
        raise ValueError("spans must be an iterable of objects") from exc
    if any(not isinstance(raw, Mapping) for raw in raw_rows):
        raise ValueError("spans must contain only objects")

    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_rows):
        text_value = raw.get("text")
        if not isinstance(text_value, str):
            raise ValueError(f"span {index} text must be a string")
        text = text_value.strip()
        if not text:
            continue
        bbox = _bbox(raw)
        raw_size = raw.get("size")
        size = max(bbox[3] - bbox[1], 1.0) if raw_size is None else _number(raw_size, "span size", positive=True)
        rows.append({"text": text, "bbox": bbox, "size": size})
    return rows


def _join_tokens(tokens: Iterable[str]) -> str:
    clean = list(normalize_math_tokens(tokens)["tokens"])
    if not clean:
        return ""
    if any(not isinstance(token, str) for token in clean):
        raise RuntimeError("math token normalizer returned a non-string token")
    out = clean[0]
    prev = clean[0]
    for token in clean[1:]:
        if token in {")", "]", "}"} or _closing_with_script(token):
            out += token
        elif prev in {"(", "[", "{"}:
            out += token
        elif _operand_like(prev) and _operand_like(token):
            out += "*" + token
        else:
            out += " " + token
        prev = token
    return " ".join(out.split())


def _nearest_left_base(script: Mapping[str, Any], main: list[dict[str, Any]], reference_size: float):
    sx0 = script["bbox"][0]
    limit = max(6.0, reference_size * 0.85)
    candidates = [
        row
        for row in main
        if row["bbox"][2] <= sx0 + 1 and sx0 - row["bbox"][2] <= limit
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda row: (abs(_cy(script) - _cy(row)), max(0.0, sx0 - row["bbox"][2])))


def _group_scripts(rows: list[dict[str, Any]], reference_size: float):
    threshold = reference_size * 0.84
    small = sorted(
        [dict(row) for row in rows if row["size"] <= threshold],
        key=lambda row: (row["bbox"][0], _cy(row)),
    )
    main = [dict(row) for row in rows if row["size"] > threshold]
    constructs: list[str] = []
    if not small or not main:
        return main + small, constructs
    assigned: dict[int, list[dict[str, Any]]] = defaultdict(list)
    unattached: list[dict[str, Any]] = []
    for script in small:
        base = _nearest_left_base(script, main, reference_size)
        if base is None:
            unattached.append(script)
        else:
            assigned[id(base)].append(script)
    for base in main:
        glyphs = assigned.get(id(base), [])
        if not glyphs:
            continue
        sides: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for glyph in glyphs:
            sides["SUPERSCRIPT" if _cy(glyph) < _cy(base) else "SUBSCRIPT"].append(glyph)
        for side, group in sides.items():
            centers = [_cy(row) for row in group]
            if max(centers) - min(centers) > max(2.0, reference_size * 0.35):
                unattached.extend(group)
                continue
            script_text = "".join(_norm(row["text"]) for row in sorted(group, key=lambda row: row["bbox"][0]))
            if not script_text:
                unattached.extend(group)
                continue
            base["text"] = f"{_norm(base['text'])}{'**' if side == 'SUPERSCRIPT' else '_'}{script_text}"
            constructs.append(side)
    return main + unattached, constructs


def _y_clusters(rows: list[dict[str, Any]], tolerance: float):
    if not rows:
        return []
    ordered = sorted(rows, key=lambda row: (_cy(row), row["bbox"][0]))
    clusters = [[ordered[0]]]
    for row in ordered[1:]:
        center = statistics.mean(_cy(value) for value in clusters[-1])
        if abs(_cy(row) - center) <= tolerance:
            clusters[-1].append(row)
        else:
            clusters.append([row])
    return clusters


def _render_horizontal(rows: list[dict[str, Any]]) -> str:
    return _join_tokens([row["text"] for row in sorted(rows, key=lambda row: (row["bbox"][0], row["bbox"][1]))])


def _has_connector(rows: list[dict[str, Any]]) -> bool:
    return any(_norm(row["text"]) in _OPERATORS for row in rows)


def _render_segment(rows: list[dict[str, Any]], reference_size: float):
    if not rows:
        return None, [], "EMPTY_RELATION_SEGMENT"
    scripted, constructs = _group_scripts(rows, reference_size)
    clusters = _y_clusters(scripted, max(2.0, statistics.median([_height(row) for row in scripted]) * 0.42))
    if len(clusters) == 1:
        return _render_horizontal(clusters[0]), constructs, None
    if len(clusters) != 2:
        return None, constructs, "MORE_THAN_TWO_PRIMARY_VERTICAL_LEVELS"
    upper, lower = clusters
    if statistics.mean(_cy(row) for row in upper) >= statistics.mean(_cy(row) for row in lower):
        upper, lower = lower, upper
    if max((_x_overlap(a, b) for a in upper for b in lower), default=0) < 0.20:
        return None, constructs, "VERTICAL_LEVELS_NOT_FRACTION_ALIGNED"
    if len(upper) > 1 and len(lower) > 1 and not _has_connector(upper) and not _has_connector(lower):
        ux = sorted(row["bbox"][0] for row in upper)
        lx = sorted(row["bbox"][0] for row in lower)
        limit = max(8.0, reference_size * 1.5)
        if any(b - a > limit for a, b in zip(ux, ux[1:])) and any(b - a > limit for a, b in zip(lx, lx[1:])):
            return None, constructs, "MULTIPLE_UNCONNECTED_VERTICAL_STACKS"
    numerator = _render_horizontal(upper)
    denominator = _render_horizontal(lower)
    if not numerator or not denominator:
        return None, constructs, "EMPTY_FRACTION_COMPONENT"
    constructs.append("STACKED_FRACTION")
    return f"({numerator})/({denominator})", constructs, None


def _status(*, status: str, linear_text: str | None, relation_count: int, constructs: list[str], flags: list[str], rows: list[dict[str, Any]], page_number: int, equation_label: str):
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": status,
        "linear_text": linear_text,
        "relation_count": relation_count,
        "constructs": sorted(set(constructs)),
        "flags": flags,
        "source_locator": f"page:{page_number}:eq:{equation_label}",
        "provenance": {"page_number": page_number, "equation_label": equation_label, "spans": rows},
        "scope_boundary": [
            "TOP_LEVEL_RELATIONS_MUST_BE_EXPLICIT_SPANS",
            "COMPOSITE_SOLVER_SUPPORTS_ONE_OR_TWO_PRIMARY_VERTICAL_LEVELS_PER_RELATION_SEGMENT",
            "SMALL_GLYPHS_BIND_TO_NEAREST_LEFT_GEOMETRIC_BASE_USING_2D_PROXIMITY",
            "TWO_ALIGNED_PRIMARY_LEVELS_MAY_FORM_ONE_STACKED_FRACTION",
            "MULTIPLE_UNCONNECTED_VERTICAL_STACKS_REMAIN_UNRESOLVED",
            "LEXICAL_NORMALIZATION_RUNS_ONLY_AFTER_GEOMETRIC_RECOVERY",
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
    if isinstance(page_number, bool) or not isinstance(page_number, int):
        raise ValueError("page_number must be an integer >= 1")
    if page_number < 1:
        raise ValueError("page_number must be >= 1")
    label = _text(equation_label, "equation_label")
    rows = _validate(spans)
    if not any(row["text"] == label for row in rows):
        return _status(status="AMBIGUOUS_COMPOSITE_2D_UNRESOLVED", linear_text=None, relation_count=0, constructs=[], flags=["EQUATION_LABEL_NOT_FOUND"], rows=rows, page_number=page_number, equation_label=label)
    content = [row for row in rows if row["text"] != label]
    relations = sorted(
        [row for row in content if _norm(row["text"]) in _RELATIONS],
        key=lambda row: row["bbox"][0],
    )
    if not relations:
        return _status(status="AMBIGUOUS_COMPOSITE_2D_UNRESOLVED", linear_text=None, relation_count=0, constructs=[], flags=["NO_EXPLICIT_TOP_LEVEL_RELATION"], rows=rows, page_number=page_number, equation_label=label)
    reference_size = statistics.median(row["size"] for row in relations)
    segments: list[list[dict[str, Any]]] = []
    left = -math.inf
    for relation in relations:
        right = relation["bbox"][0]
        segments.append([
            row for row in content if row not in relations and _cx(row) > left and _cx(row) < right
        ])
        left = relation["bbox"][2]
    segments.append([row for row in content if row not in relations and _cx(row) > left])
    rendered: list[str] = []
    constructs: list[str] = []
    for index, segment in enumerate(segments):
        text, found, error = _render_segment(segment, reference_size)
        constructs.extend(found)
        if error or not text:
            return _status(status="AMBIGUOUS_COMPOSITE_2D_UNRESOLVED", linear_text=None, relation_count=len(relations), constructs=constructs, flags=[f"SEGMENT_{index}_{error or 'UNRENDERABLE'}"], rows=rows, page_number=page_number, equation_label=label)
        rendered.append(text)
    output = rendered[0]
    for relation, text in zip(relations, rendered[1:]):
        output += f" {_norm(relation['text'])} {text}"
    return _status(status="SOLVED_COMPOSITE_2D", linear_text=output, relation_count=len(relations), constructs=constructs, flags=["GEOMETRIC_COMPOSITE_RECONSTRUCTION"], rows=rows, page_number=page_number, equation_label=label)
