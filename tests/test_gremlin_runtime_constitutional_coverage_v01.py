from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

SURFACES = {
    "gremlin_mcp/hive_server.py": {
        "gremlin_hive_exchange_ingest": {"ingest_exchange_envelope"},
        "gremlin_hive_exchange_bundle_ingest": {"ingest_exchange_bundle"},
        "gremlin_hive_sync_apply": {"apply_hive_delta"},
        "gremlin_hive_place": {"place"},
        "gremlin_hive_gates": {"update_gates"},
        "gremlin_hive_dispute": {"dispute"},
        "gremlin_hive_latch": {"latch"},
    },
    "gremlin_mcp/hive_authority_server.py": {
        "gremlin_hive_exchange_ingest": {"ingest_exchange_envelope"},
        "gremlin_hive_exchange_bundle_ingest": {"ingest_exchange_bundle"},
        "gremlin_hive_sync_apply": {"apply_hive_delta"},
        "gremlin_hive_place": {"place"},
        "gremlin_hive_gates": {"update_gates"},
        "gremlin_hive_dispute": {"dispute"},
        "gremlin_hive_latch": {"latch"},
    },
    "gremlin_mcp/server_with_hive.py": {
        "gremlin_hive_exchange_ingest": {"ingest_exchange_envelope"},
        "gremlin_hive_exchange_bundle_ingest": {"ingest_exchange_bundle"},
        "gremlin_hive_sync_apply": {"apply_hive_delta"},
        "gremlin_hive_place": {"place"},
        "gremlin_hive_gates": {"update_gates"},
        "gremlin_hive_dispute": {"dispute"},
        "gremlin_hive_latch": {"latch"},
    },
    "gremlin_mcp/bestiary_memory_gateway.py": {
        "ingest_exchange_envelope_as_beast": {"ingest_exchange_envelope"},
        "ingest_exchange_bundle_as_beast": {"ingest_exchange_bundle"},
    },
    "gremlin_mcp/raphael.py": {
        "execute": {"apply_operation"},
    },
}


def _call_name(node: ast.Call) -> str | None:
    fn = node.func
    if isinstance(fn, ast.Name):
        return fn.id
    if isinstance(fn, ast.Attribute):
        return fn.attr
    return None


def _functions(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


@pytest.mark.parametrize(
    ("relative_path", "function_name", "mutation_calls"),
    [
        (path, function, mutation_calls)
        for path, functions in SURFACES.items()
        for function, mutation_calls in functions.items()
    ],
)
def test_constitutional_guard_precedes_every_declared_high_consequence_mutation(
    relative_path: str,
    function_name: str,
    mutation_calls: set[str],
) -> None:
    path = ROOT / relative_path
    funcs = _functions(path)
    assert function_name in funcs, f"missing declared runtime surface: {relative_path}:{function_name}"
    fn = funcs[function_name]

    guard_lines = []
    mutation_lines = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name == "require_constitutional_admission":
            guard_lines.append(node.lineno)
        if name in mutation_calls:
            mutation_lines.append(node.lineno)

    assert guard_lines, f"no constitutional guard in {relative_path}:{function_name}"
    assert mutation_lines, f"no declared mutation call in {relative_path}:{function_name}"
    assert min(guard_lines) < min(mutation_lines), (
        f"constitutional guard occurs after mutation in {relative_path}:{function_name}"
    )


@pytest.mark.parametrize(
    ("relative_path", "function_name"),
    [
        (path, function)
        for path, functions in SURFACES.items()
        for function in functions
    ],
)
def test_declared_runtime_mutators_expose_constitutional_packet_input(
    relative_path: str,
    function_name: str,
) -> None:
    fn = _functions(ROOT / relative_path)[function_name]
    args = {
        arg.arg
        for arg in (
            list(fn.args.posonlyargs)
            + list(fn.args.args)
            + list(fn.args.kwonlyargs)
        )
    }
    assert "constitutional_packet" in args


def test_declared_surface_registry_is_not_empty() -> None:
    count = sum(len(functions) for functions in SURFACES.values())
    assert count == 24
