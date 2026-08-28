from __future__ import annotations

import ast
import hashlib
import json
import math
import random
from typing import Any, Mapping

from tools.gremlin_phasenav_compiler_v01 import DIM, evaluate_ir, validate_phasenav_ir
from tools.gremlin_prototype_builder_v01 import validate_prototype

RECEIPT_SCHEMA = "GREMLIN_PROTOTYPE_EXPERIMENT_RECEIPT_V0_1"
RECEIPT_DOMAIN = b"GREMLIN-PROTOTYPE-EXPERIMENT/v0.1\x00"


class GremlinExperimentHarnessError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _validate_generated_ast(source: str) -> ast.Module:
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as exc:
        raise GremlinExperimentHarnessError("generated prototype is not valid Python") from exc

    forbidden = (
        ast.Import,
        ast.ImportFrom,
        ast.With,
        ast.AsyncWith,
        ast.Try,
        ast.Lambda,
        ast.ClassDef,
        ast.Global,
        ast.Nonlocal,
        ast.Delete,
        ast.While,
        ast.For,
        ast.AsyncFor,
        ast.Await,
        ast.Yield,
        ast.YieldFrom,
    )
    if any(isinstance(node, forbidden) for node in ast.walk(tree)):
        raise GremlinExperimentHarnessError("generated prototype contains forbidden syntax")

    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(tree.body) != 1 or len(functions) != 1 or functions[0].name != "evaluate":
        raise GremlinExperimentHarnessError("prototype must contain only evaluate(theta)")

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if not isinstance(node.value, ast.Name):
                raise GremlinExperimentHarnessError("nested attribute access forbidden")
            allowed = {
                ("math", "cos"),
                ("math", "sin"),
                ("float", "fromhex"),
            }
            if (node.value.id, node.attr) not in allowed:
                raise GremlinExperimentHarnessError("attribute access outside prototype whitelist")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id not in {"len", "ValueError", "tuple"}:
                raise GremlinExperimentHarnessError("call outside prototype whitelist")
            if not isinstance(node.func, (ast.Name, ast.Attribute)):
                raise GremlinExperimentHarnessError("dynamic call target forbidden")
    return tree


def _load_evaluator(source: str):
    tree = _validate_generated_ast(source)
    code = compile(tree, "<gremlin-untrusted-prototype>", "exec")
    sandbox_globals = {
        "__builtins__": {
            "len": len,
            "ValueError": ValueError,
            "tuple": tuple,
            "float": float,
        },
        "math": math,
    }
    local_scope: dict[str, Any] = {}
    exec(code, sandbox_globals, local_scope)
    evaluator = local_scope.get("evaluate")
    if not callable(evaluator):
        raise GremlinExperimentHarnessError("prototype evaluator missing after sandbox compile")
    return evaluator


def _samples(ir_commitment: str, count: int) -> list[tuple[float, ...]]:
    if count < 1 or count > 512:
        raise GremlinExperimentHarnessError("sample_count outside v0.1 bound")
    seed = int(ir_commitment[:16], 16)
    rng = random.Random(seed)
    out = [tuple(0.0 for _ in range(DIM))]
    for _ in range(count - 1):
        out.append(tuple(rng.uniform(-math.pi, math.pi) for _ in range(DIM)))
    return out


def run_reference_experiment(
    ir: Mapping[str, Any],
    prototype: Mapping[str, Any],
    *,
    sample_count: int = 64,
    tolerance: float = 1e-12,
) -> dict[str, Any]:
    validate_phasenav_ir(ir)
    validate_prototype(prototype, ir)
    tol = float(tolerance)
    if not math.isfinite(tol) or tol <= 0.0:
        raise GremlinExperimentHarnessError("tolerance must be positive and finite")

    evaluator = _load_evaluator(str(prototype["source"]))
    max_potential_error = 0.0
    max_force_error = 0.0
    finite = True

    for theta in _samples(str(ir["ir_commitment"]), int(sample_count)):
        ref_potential, ref_force = evaluate_ir(theta, ir)
        got_potential, got_force = evaluator(theta)
        if len(got_force) != DIM:
            raise GremlinExperimentHarnessError("prototype force dimension mismatch")
        values = [ref_potential, got_potential, *ref_force, *got_force]
        finite = finite and all(math.isfinite(float(v)) for v in values)
        max_potential_error = max(max_potential_error, abs(float(got_potential) - ref_potential))
        max_force_error = max(
            max_force_error,
            max(abs(float(a) - float(b)) for a, b in zip(got_force, ref_force)),
        )

    passed = finite and max_potential_error <= tol and max_force_error <= tol
    core = {
        "schema": RECEIPT_SCHEMA,
        "source_ir_commitment": str(ir["ir_commitment"]),
        "prototype_commitment": str(prototype["prototype_commitment"]),
        "sample_count": int(sample_count),
        "tolerance": tol.hex(),
        "tests": {
            "ast_whitelist": "PASS",
            "finite_outputs": "PASS" if finite else "FAIL",
            "potential_reference_conformance": "PASS" if max_potential_error <= tol else "FAIL",
            "force_reference_conformance": "PASS" if max_force_error <= tol else "FAIL",
        },
        "max_potential_abs_error": max_potential_error.hex(),
        "max_force_abs_error": max_force_error.hex(),
        "status": "VALIDATED_PROTOTYPE" if passed else "TESTED_PROTOTYPE_FAIL",
        "validation_scope": "REFERENCE_CONFORMANCE_ONLY",
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
    receipt_id = hashlib.blake2b(RECEIPT_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    return {**core, "receipt_id": receipt_id}
