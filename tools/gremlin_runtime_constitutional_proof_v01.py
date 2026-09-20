from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

from gremlin_mcp.constitutional_surface_registry import SURFACES, manifest as registry_manifest

SCHEMA = "GREMLIN_RUNTIME_CONSTITUTIONAL_COVERAGE_PROOF_V0_1"
VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parents[1]
GUARD_NAME = "require_constitutional_admission"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _functions(tree: ast.AST) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    out: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in tree.body if isinstance(tree, ast.Module) else ():
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = node
    return out


def _argument_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    args = node.args
    values = [
        *(item.arg for item in args.posonlyargs),
        *(item.arg for item in args.args),
        *(item.arg for item in args.kwonlyargs),
    ]
    if args.vararg is not None:
        values.append(args.vararg.arg)
    if args.kwarg is not None:
        values.append(args.kwarg.arg)
    return set(values)


def _literal_keyword(call: ast.Call, name: str) -> Any:
    for keyword in call.keywords:
        if keyword.arg == name:
            try:
                return ast.literal_eval(keyword.value)
            except (ValueError, TypeError):
                return None
    return None


def _name_keyword(call: ast.Call, name: str) -> str | None:
    for keyword in call.keywords:
        if keyword.arg == name and isinstance(keyword.value, ast.Name):
            return keyword.value.id
    return None


def _calls_without_nested_functions(node: ast.AST) -> list[ast.Call]:
    calls: list[ast.Call] = []

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, child: ast.FunctionDef) -> None:
            return

        def visit_AsyncFunctionDef(self, child: ast.AsyncFunctionDef) -> None:
            return

        def visit_Lambda(self, child: ast.Lambda) -> None:
            return

        def visit_Call(self, child: ast.Call) -> None:
            calls.append(child)
            self.generic_visit(child)

    Visitor().visit(node)
    return calls


def _top_level_guard_calls(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[tuple[int, ast.Call]]:
    out: list[tuple[int, ast.Call]] = []
    for index, statement in enumerate(node.body):
        if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
            continue
        if _call_name(statement.value) == GUARD_NAME:
            out.append((index, statement.value))
    return out


def _all_calls(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for statement in node.body:
        calls.extend(_calls_without_nested_functions(statement))
    return calls


def audit_runtime_constitutional_coverage(root: Path = ROOT) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []

    for relative_path, functions in SURFACES.items():
        path = root / relative_path
        if not path.is_file():
            for function_name, policy in functions.items():
                rows.append(
                    {
                        "path": relative_path,
                        "function": function_name,
                        "endpoint": policy["endpoint"],
                        "consequence_class": policy["consequence_class"],
                        "present": False,
                        "packet_argument_present": False,
                        "guard_count": 0,
                        "guard_before_first_mutation": False,
                        "guard_endpoint_exact": False,
                        "guard_consequence_exact": False,
                        "guard_packet_argument_exact": False,
                        "mutation_calls_found": [],
                        "declared_mutation_calls": list(policy["mutation_calls"]),
                        "status": "MISSING_FAIL_CLOSED",
                    }
                )
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        fmap = _functions(tree)
        for function_name, policy in functions.items():
            node = fmap.get(function_name)
            if node is None:
                rows.append(
                    {
                        "path": relative_path,
                        "function": function_name,
                        "endpoint": policy["endpoint"],
                        "consequence_class": policy["consequence_class"],
                        "present": False,
                        "packet_argument_present": False,
                        "guard_count": 0,
                        "guard_before_first_mutation": False,
                        "guard_endpoint_exact": False,
                        "guard_consequence_exact": False,
                        "guard_packet_argument_exact": False,
                        "mutation_calls_found": [],
                        "declared_mutation_calls": list(policy["mutation_calls"]),
                        "status": "MISSING_FAIL_CLOSED",
                    }
                )
                continue

            calls = _all_calls(node)
            guards = _top_level_guard_calls(node)
            declared_mutations = tuple(str(x) for x in policy["mutation_calls"])
            mutation_calls = [
                call for call in calls if _call_name(call) in set(declared_mutations)
            ]

            guard_index, guard = guards[0] if len(guards) == 1 else (None, None)
            guard_line = None if guard is None else int(guard.lineno)
            mutation_lines = sorted(int(call.lineno) for call in mutation_calls)
            first_mutation = None if not mutation_lines else mutation_lines[0]

            mutation_statement_indices = []
            for index, statement in enumerate(node.body):
                statement_calls = _calls_without_nested_functions(statement)
                if any(
                    _call_name(call) in set(declared_mutations)
                    for call in statement_calls
                ):
                    mutation_statement_indices.append(index)
            first_mutation_statement = (
                None
                if not mutation_statement_indices
                else min(mutation_statement_indices)
            )

            packet_argument_present = "constitutional_packet" in _argument_names(node)
            guard_before = (
                guard_index is not None
                and first_mutation_statement is not None
                and guard_index < first_mutation_statement
            )
            endpoint_exact = (
                guard is not None
                and _literal_keyword(guard, "endpoint") == policy["endpoint"]
            )
            consequence_exact = (
                guard is not None
                and _literal_keyword(guard, "consequence_class")
                == policy["consequence_class"]
            )
            packet_exact = (
                guard is not None
                and _name_keyword(guard, "constitutional_packet")
                == "constitutional_packet"
            )
            declared_calls_found = sorted(
                {
                    str(_call_name(call))
                    for call in mutation_calls
                    if _call_name(call) is not None
                }
            )
            all_declared_mutations_found = set(declared_mutations).issubset(
                set(declared_calls_found)
            )

            covered = bool(
                packet_argument_present
                and len(guards) == 1
                and guard_before
                and endpoint_exact
                and consequence_exact
                and packet_exact
                and all_declared_mutations_found
            )
            rows.append(
                {
                    "path": relative_path,
                    "function": function_name,
                    "endpoint": policy["endpoint"],
                    "consequence_class": policy["consequence_class"],
                    "present": True,
                    "packet_argument_present": packet_argument_present,
                    "guard_count": len(guards),
                    "guard_line": guard_line,
                    "guard_top_level_statement_index": guard_index,
                    "first_mutation_line": first_mutation,
                    "first_mutation_top_level_statement_index": first_mutation_statement,
                    "guard_is_unconditional_top_level_statement": guard_index is not None,
                    "guard_before_first_mutation": guard_before,
                    "guard_endpoint_exact": endpoint_exact,
                    "guard_consequence_exact": consequence_exact,
                    "guard_packet_argument_exact": packet_exact,
                    "mutation_calls_found": declared_calls_found,
                    "declared_mutation_calls": list(declared_mutations),
                    "all_declared_mutation_calls_found": all_declared_mutations_found,
                    "status": (
                        "CONSTITUTIONALLY_COVERED"
                        if covered
                        else "CONSTITUTIONAL_GAP"
                    ),
                }
            )

    total = len(rows)
    covered = sum(1 for row in rows if row["status"] == "CONSTITUTIONALLY_COVERED")
    gaps = [row for row in rows if row["status"] != "CONSTITUTIONALLY_COVERED"]
    summary = {
        "declared_surface_count": total,
        "constitutional_covered_count": covered,
        "constitutional_gap_count": len(gaps),
        "coverage_fraction": 1.0 if total == 0 else covered / total,
        "coverage_complete": total > 0 and not gaps,
        "registry_manifest": registry_manifest(),
        "proof_scope": (
            "EXPLICIT_REGISTRY_UNCONDITIONAL_TOP_LEVEL_GUARD_"
            "DOMINANCE_OVER_DECLARED_MUTATION_CALLS"
        ),
        "registry_exhaustiveness_proven": False,
        "whole_repository_mutation_reachability_proven": False,
    }
    receipt = {
        "schema": SCHEMA,
        "version": VERSION,
        "rows": rows,
        "summary": summary,
    }
    receipt["receipt_sha256"] = _sha256(receipt)
    return receipt


def main() -> int:
    receipt = audit_runtime_constitutional_coverage()
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["summary"]["coverage_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
