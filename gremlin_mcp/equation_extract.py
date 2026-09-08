from __future__ import annotations

import ast
from collections import defaultdict
import hashlib
import json
import math
import re
from typing import Any

SCHEMA = "GREMLIN_EQUATION_WITNESS_PROPOSAL_V0_1"
VERSION = "0.3.0"

_EQ_PREFIX_RE = re.compile(r"^\s*(?P<label>Eq\.\s*\([^)]{1,32}\))\s*:\s*(?P<body>.+?)\s*$", re.I)
_ASSIGN_RE = re.compile(r"^\s*(?P<lhs>[A-Za-z][A-Za-z0-9_]*)\s*=\s*(?P<rhs>.+?)\s*$")
_APPROX_SPLIT_RE = re.compile(r"^(?P<expr>.+?)\s*~=\s*(?P<reported>.+?)\s*$")
_SIMPLE_NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
_SCI_RE = re.compile(
    r"(?P<mant>[+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*\*\s*10\s*\*\*\s*(?P<exp>[+-]?\d+)"
)
_REPORTED_QUANTITY_RE = re.compile(
    r"^(?P<number>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
    r"(?:\s*\*\s*(?P<unit>[A-Za-z][A-Za-z0-9_]*(?:\*\*[+-]?\d+)?(?:[*/][A-Za-z][A-Za-z0-9_]*(?:\*\*[+-]?\d+)?)*))?$"
)
_ALLOWED_BINARY = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
_ALLOWED_UNARY = (ast.UAdd, ast.USub)


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


def _normalize_math(value: str) -> str:
    text = str(value)
    text = text.replace("×", "*").replace("·", "*").replace("⋅", "*")
    text = text.replace("−", "-").replace("–", "-")
    text = text.replace("≈", "~=")
    text = text.replace("^", "**")
    text = _SCI_RE.sub(lambda match: f"{match.group('mant')}e{match.group('exp')}", text)
    return " ".join(text.strip().split())


def _safe_expression_symbols(expression: str) -> set[str]:
    try:
        tree = ast.parse(str(expression), mode="eval")
    except SyntaxError as exc:
        raise ValueError("invalid mathematical expression") from exc

    symbols: set[str] = set()

    def walk(node: ast.AST) -> None:
        if isinstance(node, ast.Expression):
            walk(node.body)
            return
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise ValueError("non-numeric literal")
            return
        if isinstance(node, ast.Name):
            if node.id != "pi":
                symbols.add(node.id)
            return
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, _ALLOWED_UNARY):
            walk(node.operand)
            return
        if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BINARY):
            walk(node.left)
            walk(node.right)
            return
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "sqrt" and len(node.args) == 1 and not node.keywords:
                walk(node.args[0])
                return
            raise ValueError("function call rejected")
        raise ValueError(f"unsupported syntax: {type(node).__name__}")

    walk(tree)
    return symbols


def _parse_number(value: str) -> float:
    normalized = _normalize_math(value)
    if not _SIMPLE_NUMBER_RE.fullmatch(normalized):
        raise ValueError("not a numeric literal")
    number = float(normalized)
    if not math.isfinite(number):
        raise ValueError("numeric literal must be finite")
    return number


def _parse_reported_quantity(value: str) -> tuple[float, str | None]:
    normalized = _normalize_math(value)
    match = _REPORTED_QUANTITY_RE.fullmatch(normalized)
    if not match:
        raise ValueError("reported approximation is not a numeric scalar with optional explicit unit")
    number = float(match.group("number"))
    if not math.isfinite(number):
        raise ValueError("reported numeric scalar must be finite")
    unit = match.group("unit") or None
    return number, unit


def _proposal_id(source_id: str, kind: str, basis: Any) -> str:
    return "EQP-" + _commit(b"GREMLIN-EQUATION-PROPOSAL/v0.1", {"source": source_id, "kind": kind, "basis": basis})[:16]


def propose_equation_witnesses(text: str, *, source_id: str) -> dict[str, Any]:
    source = str(source_id).strip()
    if not source:
        raise ValueError("source_id must be non-empty")
    body = str(text or "")
    if not body.strip():
        core = {
            "schema": SCHEMA,
            "version": VERSION,
            "source_id": source,
            "status": "NO_TEXT_FAIL_CLOSED",
            "declared_constants": {},
            "formula_spans": [],
            "relation_chain_spans": [],
            "witness_proposals": [],
            "unresolved_proposals": [],
            "rejected_spans": [],
            "authority": _authority(),
        }
        core["proposal_commitment"] = _commit(b"GREMLIN-EQUATION-PROPOSALS/v0.1", core)
        return core

    constants: dict[str, float] = {}
    formula_spans: list[dict[str, Any]] = []
    relation_chain_spans: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for line_no, raw in enumerate(body.splitlines(), start=1):
        line = _normalize_math(raw)
        if not line or _EQ_PREFIX_RE.match(line):
            continue
        match = _ASSIGN_RE.match(line)
        if not match:
            continue
        try:
            constants[match.group("lhs")] = _parse_number(match.group("rhs"))
        except ValueError:
            continue

    for line_no, raw in enumerate(body.splitlines(), start=1):
        line = _normalize_math(raw)
        if not line:
            continue
        prefixed = _EQ_PREFIX_RE.match(line)
        if not prefixed:
            continue
        label = prefixed.group("label")
        equation_body = prefixed.group("body")
        assignment = _ASSIGN_RE.match(equation_body)
        if not assignment:
            chain_approx = _APPROX_SPLIT_RE.match(equation_body)
            if chain_approx:
                pre_approx = chain_approx.group("expr").strip()
                final_expression = pre_approx.rsplit("=", 1)[-1].strip()
                try:
                    reported, reported_unit = _parse_reported_quantity(chain_approx.group("reported"))
                    symbols = sorted(_safe_expression_symbols(final_expression))
                except ValueError as exc:
                    rejected.append({
                        "line": line_no,
                        "label": label,
                        "text": raw.strip(),
                        "reason": "UNSAFE_OR_UNSUPPORTED_RELATION_CHAIN",
                        "detail": str(exc),
                    })
                    continue
                relation_chain_spans.append({
                    "line": line_no,
                    "label": label,
                    "expression": final_expression.replace(" ", ""),
                    "symbols": symbols,
                    "reported_value": reported,
                    "reported_unit": reported_unit,
                    "source_excerpt": raw.strip(),
                    "extraction_basis": "FINAL_NUMERIC_SUBSTITUTION_BEFORE_APPROXIMATION",
                })
                continue
            rejected.append({
                "line": line_no,
                "label": label,
                "text": raw.strip(),
                "reason": "EQUATION_LABEL_WITHOUT_SIMPLE_ASSIGNMENT_OR_NUMERIC_RELATION_CHAIN",
            })
            continue

        lhs = assignment.group("lhs")
        rhs_raw = assignment.group("rhs")
        approx = _APPROX_SPLIT_RE.match(rhs_raw)
        expression = approx.group("expr").strip() if approx else rhs_raw.strip()
        reported: float | None = None
        reported_unit: str | None = None
        if approx:
            try:
                reported, reported_unit = _parse_reported_quantity(approx.group("reported"))
            except ValueError:
                rejected.append({
                    "line": line_no,
                    "label": label,
                    "text": raw.strip(),
                    "reason": "INVALID_REPORTED_NUMERIC_QUANTITY",
                })
                continue
        try:
            symbols = sorted(_safe_expression_symbols(expression))
        except ValueError as exc:
            rejected.append({
                "line": line_no,
                "label": label,
                "text": raw.strip(),
                "reason": "UNSAFE_OR_UNSUPPORTED_EXPRESSION",
                "detail": str(exc),
            })
            continue
        formula_spans.append({
            "line": line_no,
            "label": label,
            "lhs": lhs,
            "expression": expression.replace(" ", ""),
            "symbols": symbols,
            "reported_value": reported,
            "reported_unit": reported_unit,
            "source_excerpt": raw.strip(),
        })

    proposals: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    for row in formula_spans:
        if row["reported_value"] is None:
            continue
        missing = sorted(symbol for symbol in row["symbols"] if symbol not in constants)
        basis = {
            "label": row["label"], "lhs": row["lhs"], "expression": row["expression"],
            "reported": row["reported_value"], "reported_unit": row["reported_unit"],
        }
        common = {
            "id": _proposal_id(source, "numeric", basis),
            "kind": "numeric",
            "expression": row["expression"],
            "reported_value": row["reported_value"],
            "reported_unit": row["reported_unit"],
            "source_locator": f"{source}:{row['label']}",
            "source_excerpt": row["source_excerpt"],
            "epistemic_status": "CANDIDATE_WITNESS",
        }
        bound = {symbol: constants[symbol] for symbol in row["symbols"] if symbol in constants}
        if missing:
            unresolved.append({**common, "missing_symbols": missing, "symbols": bound})
        else:
            proposals.append({**common, "symbols": bound})

    for row in relation_chain_spans:
        missing = sorted(symbol for symbol in row["symbols"] if symbol not in constants)
        basis = {
            "label": row["label"], "expression": row["expression"], "reported": row["reported_value"],
            "reported_unit": row["reported_unit"], "extraction_basis": row["extraction_basis"],
        }
        common = {
            "id": _proposal_id(source, "numeric_relation_chain", basis),
            "kind": "numeric",
            "expression": row["expression"],
            "reported_value": row["reported_value"],
            "reported_unit": row["reported_unit"],
            "source_locator": f"{source}:{row['label']}",
            "source_excerpt": row["source_excerpt"],
            "extraction_basis": row["extraction_basis"],
            "epistemic_status": "CANDIDATE_WITNESS",
        }
        bound = {symbol: constants[symbol] for symbol in row["symbols"] if symbol in constants}
        if missing:
            unresolved.append({**common, "missing_symbols": missing, "symbols": bound})
        else:
            proposals.append({**common, "symbols": bound})

    by_lhs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in formula_spans:
        by_lhs[row["lhs"]].append(row)
    for lhs, rows in sorted(by_lhs.items()):
        for index, left in enumerate(rows):
            for right in rows[index + 1 :]:
                if left["expression"] == right["expression"]:
                    continue
                symbols = sorted(set(left["symbols"]) | set(right["symbols"]))
                basis = {"lhs": lhs, "left": left["expression"], "right": right["expression"], "labels": [left["label"], right["label"]]}
                proposals.append({
                    "id": _proposal_id(source, "symbolic_identity", basis),
                    "kind": "symbolic_identity",
                    "lhs": left["expression"],
                    "rhs": right["expression"],
                    "symbols": symbols,
                    "source_locator": f"{source}:{left['label']} <-> {right['label']}",
                    "source_excerpt": f"{left['source_excerpt']} || {right['source_excerpt']}",
                    "epistemic_status": "CANDIDATE_WITNESS",
                })

    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "source_id": source,
        "status": "CANDIDATE_PROPOSALS_READY",
        "declared_constants": dict(sorted(constants.items())),
        "formula_spans": formula_spans,
        "relation_chain_spans": relation_chain_spans,
        "witness_proposals": proposals,
        "unresolved_proposals": unresolved,
        "rejected_spans": rejected,
        "scope_boundary": [
            "EQUATION_LABELLED_LINES_ONLY",
            "NO_PROSE_TO_EQUATION_HALLUCINATION",
            "NO_UNSAFE_EVAL_OR_ARBITRARY_FUNCTION_CALLS",
            "NUMERIC_RELATION_CHAIN_AUDITS_ONLY_FINAL_EXPRESSION_BEFORE_EXPLICIT_APPROXIMATION",
            "OPTIONAL_REPORTED_UNIT_IS_PRESERVED_BUT_NOT_USED_IN_NUMERIC_SCALAR_COMPARISON",
            "EARLIER_RELATIONS_IN_CHAIN_ARE_NOT_PROMOTED_BY_THE_NUMERIC_WITNESS",
            "MISSING_SYMBOLS_REMAIN_UNRESOLVED",
            "CANDIDATE_WITNESSES_REQUIRE_EQUATION_AUDIT",
            "NO_AUTOMATIC_CANON_PROMOTION",
        ],
        "authority": _authority(),
    }
    core["proposal_commitment"] = _commit(b"GREMLIN-EQUATION-PROPOSALS/v0.1", core)
    return core
