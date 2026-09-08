from __future__ import annotations

import ast
import hashlib
import json
import math
from typing import Any, Mapping, Iterable

import sympy as sp

SCHEMA = "GREMLIN_EQUATION_AUDIT_V0_1"
VERSION = "0.1.0"
_ALLOWED_ASSUMPTIONS = {"positive", "real", "nonzero", "integer"}


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


def _symbol_table(names: Iterable[str], assumptions: Mapping[str, str] | None = None) -> dict[str, sp.Symbol]:
    assumptions = dict(assumptions or {})
    out: dict[str, sp.Symbol] = {}
    for raw_name in names:
        name = str(raw_name)
        mode = assumptions.get(name)
        kwargs: dict[str, bool] = {}
        if mode is not None:
            if mode not in _ALLOWED_ASSUMPTIONS:
                raise ValueError(f"unsupported assumption for {name}: {mode}")
            kwargs[mode] = True
        out[name] = sp.Symbol(name, **kwargs)
    return out


def _sym_from_ast(node: ast.AST, symbols: Mapping[str, sp.Symbol]) -> sp.Expr:
    if isinstance(node, ast.Expression):
        return _sym_from_ast(node.body, symbols)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("only numeric constants are allowed")
        return sp.Integer(node.value) if isinstance(node.value, int) else sp.Float(node.value)
    if isinstance(node, ast.Name):
        if node.id == "pi":
            return sp.pi
        if node.id not in symbols:
            raise ValueError(f"unknown symbol: {node.id}")
        return symbols[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _sym_from_ast(node.operand, symbols)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp):
        left = _sym_from_ast(node.left, symbols)
        right = _sym_from_ast(node.right, symbols)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left**right
        raise ValueError("unsupported binary operator")
    if isinstance(node, ast.Call):
        if (
            not isinstance(node.func, ast.Name)
            or node.func.id != "sqrt"
            or len(node.args) != 1
            or node.keywords
        ):
            raise ValueError("only sqrt(expr) is allowed")
        return sp.sqrt(_sym_from_ast(node.args[0], symbols))
    raise ValueError(f"unsupported expression node: {type(node).__name__}")


def _parse_symbolic(expression: str, symbols: Mapping[str, sp.Symbol]) -> sp.Expr:
    try:
        tree = ast.parse(str(expression), mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"invalid expression: {expression}") from exc
    return _sym_from_ast(tree, symbols)


def audit_numeric_formula_claim(
    *,
    expression: str,
    symbols: Mapping[str, float],
    reported_value: float,
    rel_tol: float = 1e-9,
    abs_tol: float = 0.0,
) -> dict[str, Any]:
    values = {str(key): float(value) for key, value in dict(symbols).items()}
    if any(not math.isfinite(value) for value in values.values()):
        raise ValueError("numeric symbols must be finite")
    reported = float(reported_value)
    if not math.isfinite(reported):
        raise ValueError("reported_value must be finite")
    if rel_tol < 0 or abs_tol < 0:
        raise ValueError("tolerances must be non-negative")

    symbolic = _symbol_table(values)
    parsed = _parse_symbolic(expression, symbolic)
    substitutions = {symbolic[name]: value for name, value in values.items()}
    computed = float(sp.N(parsed.subs(substitutions), 30))
    if not math.isfinite(computed):
        raise ValueError("computed value is not finite")

    absolute_error = abs(computed - reported)
    scale = max(abs(computed), abs(reported))
    matches = absolute_error <= max(float(abs_tol), float(rel_tol) * scale)
    orders_of_magnitude_error: float | None = None
    if computed != 0.0 and reported != 0.0:
        orders_of_magnitude_error = abs(math.log10(abs(reported / computed)))

    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "kind": "NUMERIC_FORMULA_CLAIM",
        "expression": str(expression),
        "computed_value": computed,
        "reported_value": reported,
        "absolute_error": absolute_error,
        "relative_error": (
            absolute_error / abs(computed)
            if computed != 0.0
            else (0.0 if reported == 0.0 else math.inf)
        ),
        "orders_of_magnitude_error": orders_of_magnitude_error,
        "matches": matches,
        "status": "PASS" if matches else "FAIL",
        "authority": _authority(),
    }
    core["audit_commitment"] = _commit(b"GREMLIN-EQUATION-NUMERIC/v0.1", core)
    return core


def _dim_add(
    left: Mapping[str, float],
    right: Mapping[str, float],
    sign: float = 1.0,
) -> dict[str, float]:
    out = dict(left)
    for key, value in right.items():
        out[key] = out.get(key, 0.0) + sign * float(value)
    return {key: value for key, value in out.items() if abs(value) > 1e-12}


def _dim_scale(value: Mapping[str, float], scale: float) -> dict[str, float]:
    return {
        key: float(power) * float(scale)
        for key, power in value.items()
        if abs(float(power) * float(scale)) > 1e-12
    }


def _constant_exponent(node: ast.AST) -> float:
    if (
        isinstance(node, ast.Constant)
        and not isinstance(node.value, bool)
        and isinstance(node.value, (int, float))
    ):
        return float(node.value)
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, (ast.UAdd, ast.USub))
        and isinstance(node.operand, ast.Constant)
        and not isinstance(node.operand.value, bool)
        and isinstance(node.operand.value, (int, float))
    ):
        value = float(node.operand.value)
        return value if isinstance(node.op, ast.UAdd) else -value
    raise ValueError("dimension analysis requires constant numeric exponent")


def _dim_from_ast(
    node: ast.AST,
    dimensions: Mapping[str, Mapping[str, float]],
) -> dict[str, float]:
    if isinstance(node, ast.Expression):
        return _dim_from_ast(node.body, dimensions)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("only numeric constants are allowed")
        return {}
    if isinstance(node, ast.Name):
        if node.id == "pi":
            return {}
        if node.id not in dimensions:
            raise ValueError(f"unknown symbol: {node.id}")
        return {
            str(key): float(value)
            for key, value in dict(dimensions[node.id]).items()
            if float(value) != 0.0
        }
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        return _dim_from_ast(node.operand, dimensions)
    if isinstance(node, ast.BinOp):
        left = _dim_from_ast(node.left, dimensions)
        if isinstance(node.op, ast.Pow):
            return _dim_scale(left, _constant_exponent(node.right))
        right = _dim_from_ast(node.right, dimensions)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            if left != right:
                raise ValueError(
                    f"dimension mismatch inside additive expression: {left} vs {right}"
                )
            return left
        if isinstance(node.op, ast.Mult):
            return _dim_add(left, right)
        if isinstance(node.op, ast.Div):
            return _dim_add(left, right, -1.0)
        raise ValueError("unsupported binary operator")
    if isinstance(node, ast.Call):
        if (
            not isinstance(node.func, ast.Name)
            or node.func.id != "sqrt"
            or len(node.args) != 1
            or node.keywords
        ):
            raise ValueError("only sqrt(expr) is allowed")
        return _dim_scale(_dim_from_ast(node.args[0], dimensions), 0.5)
    raise ValueError(f"unsupported expression node: {type(node).__name__}")


def _dimension_of(
    expression: str,
    dimensions: Mapping[str, Mapping[str, float]],
) -> dict[str, float]:
    try:
        tree = ast.parse(str(expression), mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"invalid expression: {expression}") from exc
    return _dim_from_ast(tree, dimensions)


def _clean_dimension(value: Mapping[str, float]) -> dict[str, int | float]:
    cleaned: dict[str, int | float] = {}
    for key, power in sorted(value.items()):
        if abs(power) <= 1e-12:
            continue
        nearest = round(power)
        cleaned[key] = int(nearest) if abs(power - nearest) < 1e-12 else power
    return cleaned


def audit_dimensional_identity(
    lhs: str,
    rhs: str,
    *,
    dimensions: Mapping[str, Mapping[str, float]],
) -> dict[str, Any]:
    left = _clean_dimension(_dimension_of(lhs, dimensions))
    right = _clean_dimension(_dimension_of(rhs, dimensions))
    consistent = left == right
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "kind": "DIMENSIONAL_IDENTITY",
        "lhs": str(lhs),
        "rhs": str(rhs),
        "lhs_dimension": left,
        "rhs_dimension": right,
        "dimensionally_consistent": consistent,
        "status": "PASS" if consistent else "FAIL",
        "authority": _authority(),
    }
    core["audit_commitment"] = _commit(b"GREMLIN-EQUATION-DIM/v0.1", core)
    return core


def audit_symbolic_identity(
    lhs: str,
    rhs: str,
    *,
    symbols: Iterable[str],
) -> dict[str, Any]:
    names = [str(value) for value in symbols]
    symbolic = _symbol_table(names)
    left = _parse_symbolic(lhs, symbolic)
    right = _parse_symbolic(rhs, symbolic)
    difference = sp.simplify(left - right)
    identical = bool(difference == 0)
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "kind": "SYMBOLIC_IDENTITY",
        "lhs": str(lhs),
        "rhs": str(rhs),
        "difference": str(difference),
        "identical": identical,
        "status": "PASS" if identical else "FAIL",
        "authority": _authority(),
    }
    core["audit_commitment"] = _commit(b"GREMLIN-EQUATION-IDENTITY/v0.1", core)
    return core


def audit_derivation_claim(
    *,
    equation: str,
    target: str,
    claimed_expression: str,
    assumptions: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    assumptions = dict(assumptions or {})
    target_name = str(target)
    names = set(assumptions) | {target_name}
    symbolic = _symbol_table(names, assumptions)

    equation_text = str(equation)
    if equation_text.count("=") != 1:
        raise ValueError("equation must contain exactly one '='")
    lhs_text, rhs_text = [part.strip() for part in equation_text.split("=", 1)]
    lhs = _parse_symbolic(lhs_text, symbolic)
    rhs = _parse_symbolic(rhs_text, symbolic)
    claim = _parse_symbolic(claimed_expression, symbolic)

    solutions = sp.solve(sp.Eq(lhs, rhs), symbolic[target_name])
    simplified = [sp.simplify(solution) for solution in solutions]
    claim_matches_solution = any(
        sp.simplify(solution - claim) == 0 for solution in simplified
    )
    status = (
        "UNRESOLVED"
        if not simplified
        else ("PASS" if claim_matches_solution else "FAIL")
    )

    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "kind": "DERIVATION_CLAIM",
        "equation": equation_text,
        "target": target_name,
        "claimed_expression": str(claimed_expression),
        "derived_solutions": [str(solution) for solution in simplified],
        "claim_matches_solution": claim_matches_solution,
        "status": status,
        "scope_boundary": [
            "STRUCTURED_EQUATION_WITNESS_REQUIRED",
            "NO_UNSAFE_EVAL",
            "NO_AUTOMATIC_PHYSICAL_INTERPRETATION",
            "NO_CANON_PROMOTION",
        ],
        "authority": _authority(),
    }
    core["audit_commitment"] = _commit(
        b"GREMLIN-EQUATION-DERIVATION/v0.1",
        core,
    )
    return core
