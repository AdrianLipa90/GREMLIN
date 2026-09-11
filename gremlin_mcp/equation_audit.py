from __future__ import annotations

import ast
import hashlib
import json
import math
from typing import Any, Iterable, Mapping

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
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("equation audit data must be finite JSON") from exc


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field} must be non-empty")
    return text


def _finite_number(value: Any, field: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number")
    if nonnegative and number < 0:
        raise ValueError(f"{field} must be non-negative")
    return number


def _string_names(values: Iterable[str], field: str) -> list[str]:
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError(f"{field} must be an iterable of strings")
    try:
        raw = list(values)
    except TypeError as exc:
        raise ValueError(f"{field} must be an iterable of strings") from exc
    names = [_nonempty(value, field) for value in raw]
    if len(set(names)) != len(names):
        raise ValueError(f"{field} must not contain duplicate names")
    return names


def _assumption_map(value: Mapping[str, str] | None) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("assumptions must be an object")
    out: dict[str, str] = {}
    for raw_name, raw_mode in value.items():
        name = _nonempty(raw_name, "assumption symbol")
        mode = _nonempty(raw_mode, f"assumption for {name}")
        if mode not in _ALLOWED_ASSUMPTIONS:
            raise ValueError(f"unsupported assumption for {name}: {mode}")
        if name in out:
            raise ValueError(f"duplicate assumption symbol: {name}")
        out[name] = mode
    return out


def _symbol_table(names: Iterable[str], assumptions: Mapping[str, str] | None = None) -> dict[str, sp.Symbol]:
    assumption_rows = _assumption_map(assumptions)
    out: dict[str, sp.Symbol] = {}
    for name in _string_names(names, "symbol name"):
        mode = assumption_rows.get(name)
        kwargs: dict[str, bool] = {}
        if mode is not None:
            kwargs[mode] = True
        out[name] = sp.Symbol(name, **kwargs)
    unknown_assumptions = sorted(set(assumption_rows) - set(out))
    if unknown_assumptions:
        raise ValueError(f"assumptions reference undeclared symbols: {unknown_assumptions}")
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
    text = _nonempty(expression, "expression")
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"invalid expression: {text}") from exc
    return _sym_from_ast(tree, symbols)


def _numeric_symbol_map(symbols: Mapping[str, float]) -> dict[str, float]:
    if not isinstance(symbols, Mapping):
        raise ValueError("symbols must be an object")
    values: dict[str, float] = {}
    for raw_key, raw_value in symbols.items():
        key = _nonempty(raw_key, "symbol name")
        if key in values:
            raise ValueError(f"duplicate numeric symbol: {key}")
        values[key] = _finite_number(raw_value, f"numeric symbol {key}")
    return values


def audit_numeric_formula_claim(
    *,
    expression: str,
    symbols: Mapping[str, float],
    reported_value: float,
    rel_tol: float = 1e-9,
    abs_tol: float = 0.0,
) -> dict[str, Any]:
    expression_text = _nonempty(expression, "expression")
    values = _numeric_symbol_map(symbols)
    reported = _finite_number(reported_value, "reported_value")
    relative_tolerance = _finite_number(rel_tol, "rel_tol", nonnegative=True)
    absolute_tolerance = _finite_number(abs_tol, "abs_tol", nonnegative=True)

    symbolic = _symbol_table(values)
    parsed = _parse_symbolic(expression_text, symbolic)
    substitutions = {symbolic[name]: value for name, value in values.items()}
    computed = float(sp.N(parsed.subs(substitutions), 30))
    if not math.isfinite(computed):
        raise ValueError("computed value is not finite")

    absolute_error = abs(computed - reported)
    scale = max(abs(computed), abs(reported))
    matches = absolute_error <= max(absolute_tolerance, relative_tolerance * scale)
    orders_of_magnitude_error: float | None = None
    if computed != 0.0 and reported != 0.0:
        orders_of_magnitude_error = abs(math.log10(abs(reported / computed)))
    relative_error: float | None
    if computed != 0.0:
        relative_error = absolute_error / abs(computed)
    elif reported == 0.0:
        relative_error = 0.0
    else:
        relative_error = None

    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "kind": "NUMERIC_FORMULA_CLAIM",
        "expression": expression_text,
        "computed_value": computed,
        "reported_value": reported,
        "absolute_error": absolute_error,
        "relative_error": relative_error,
        "orders_of_magnitude_error": orders_of_magnitude_error,
        "matches": matches,
        "status": "PASS" if matches else "FAIL",
        "authority": _authority(),
    }
    core["audit_commitment"] = _commit(b"GREMLIN-EQUATION-NUMERIC/v0.1", core)
    return core


def _dimension_map(value: Mapping[str, Mapping[str, float]]) -> dict[str, dict[str, float]]:
    if not isinstance(value, Mapping):
        raise ValueError("dimensions must be an object")
    out: dict[str, dict[str, float]] = {}
    for raw_symbol, raw_dimensions in value.items():
        symbol = _nonempty(raw_symbol, "dimension symbol")
        if not isinstance(raw_dimensions, Mapping):
            raise ValueError(f"dimensions for {symbol} must be an object")
        dimension: dict[str, float] = {}
        for raw_axis, raw_power in raw_dimensions.items():
            axis = _nonempty(raw_axis, f"dimension axis for {symbol}")
            power = _finite_number(raw_power, f"dimension power {symbol}.{axis}")
            if power != 0.0:
                dimension[axis] = power
        out[symbol] = dimension
    return out


def _dim_add(
    left: Mapping[str, float],
    right: Mapping[str, float],
    sign: float = 1.0,
) -> dict[str, float]:
    out = dict(left)
    for key, value in right.items():
        out[key] = out.get(key, 0.0) + sign * value
    return {key: value for key, value in out.items() if abs(value) > 1e-12}


def _dim_scale(value: Mapping[str, float], scale: float) -> dict[str, float]:
    return {
        key: power * scale
        for key, power in value.items()
        if abs(power * scale) > 1e-12
    }


def _constant_exponent(node: ast.AST) -> float:
    if (
        isinstance(node, ast.Constant)
        and not isinstance(node.value, bool)
        and isinstance(node.value, (int, float))
    ):
        value = float(node.value)
        if not math.isfinite(value):
            raise ValueError("dimension exponent must be finite")
        return value
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, (ast.UAdd, ast.USub))
        and isinstance(node.operand, ast.Constant)
        and not isinstance(node.operand.value, bool)
        and isinstance(node.operand.value, (int, float))
    ):
        value = float(node.operand.value)
        if not math.isfinite(value):
            raise ValueError("dimension exponent must be finite")
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
        return dict(dimensions[node.id])
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
    text = _nonempty(expression, "expression")
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"invalid expression: {text}") from exc
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
    lhs_text = _nonempty(lhs, "lhs")
    rhs_text = _nonempty(rhs, "rhs")
    dimension_rows = _dimension_map(dimensions)
    left = _clean_dimension(_dimension_of(lhs_text, dimension_rows))
    right = _clean_dimension(_dimension_of(rhs_text, dimension_rows))
    consistent = left == right
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "kind": "DIMENSIONAL_IDENTITY",
        "lhs": lhs_text,
        "rhs": rhs_text,
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
    lhs_text = _nonempty(lhs, "lhs")
    rhs_text = _nonempty(rhs, "rhs")
    names = _string_names(symbols, "symbols")
    symbolic = _symbol_table(names)
    left = _parse_symbolic(lhs_text, symbolic)
    right = _parse_symbolic(rhs_text, symbolic)
    difference = sp.simplify(left - right)
    identical = difference == 0
    if not isinstance(identical, (bool, sp.logic.boolalg.BooleanTrue, sp.logic.boolalg.BooleanFalse)):
        identical = bool(identical)
    identical_bool = bool(identical)
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "kind": "SYMBOLIC_IDENTITY",
        "lhs": lhs_text,
        "rhs": rhs_text,
        "difference": str(difference),
        "identical": identical_bool,
        "status": "PASS" if identical_bool else "FAIL",
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
    equation_text = _nonempty(equation, "equation")
    target_name = _nonempty(target, "target")
    claim_text = _nonempty(claimed_expression, "claimed_expression")
    assumption_rows = _assumption_map(assumptions)
    names = set(assumption_rows) | {target_name}
    symbolic = _symbol_table(sorted(names), assumption_rows)

    if equation_text.count("=") != 1:
        raise ValueError("equation must contain exactly one '='")
    lhs_text, rhs_text = [part.strip() for part in equation_text.split("=", 1)]
    if not lhs_text or not rhs_text:
        raise ValueError("equation sides must be non-empty")
    lhs = _parse_symbolic(lhs_text, symbolic)
    rhs = _parse_symbolic(rhs_text, symbolic)
    claim = _parse_symbolic(claim_text, symbolic)

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
        "claimed_expression": claim_text,
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
