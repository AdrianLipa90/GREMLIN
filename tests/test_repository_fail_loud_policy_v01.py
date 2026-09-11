from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOTS = (ROOT / "gremlin_mcp", ROOT / "tools", ROOT / "client")
_BROAD_EXCEPTION_NAMES = {"BaseException", "Exception", "OSError"}


def _python_files():
    for root in RUNTIME_ROOTS:
        if not root.exists():
            continue
        yield from sorted(path for path in root.rglob("*.py") if path.is_file())


def _exception_names(node: ast.expr | None) -> set[str]:
    if node is None:
        return set()
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.Tuple):
        names: set[str] = set()
        for item in node.elts:
            names.update(_exception_names(item))
        return names
    if isinstance(node, ast.Attribute):
        return {node.attr}
    return {"<dynamic>"}


def _function_body_without_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.stmt]:
    body = list(node.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    return body


def _is_pass_or_ellipsis(statement: ast.stmt) -> bool:
    if isinstance(statement, ast.Pass):
        return True
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and statement.value.value is Ellipsis
    )


def test_runtime_has_no_bare_or_broad_except_pass_blackholes() -> None:
    """Narrow expected-control-flow catches may be empty; broad error swallowing may not.

    Examples such as FileExistsError during create-if-absent, FileNotFoundError during idempotent
    cleanup, ValueError from Path.relative_to(), and KeyboardInterrupt at a CLI boundary are not
    error blackholes. Bare, Exception/BaseException and OSError pass-only handlers are.
    """
    findings: list[str] = []
    scanned = 0
    for path in _python_files():
        scanned += 1
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            relative = path.relative_to(ROOT)
            meaningful = [statement for statement in node.body if not isinstance(statement, ast.Pass)]
            names = _exception_names(node.type)
            if node.type is None:
                findings.append(f"{relative}:{node.lineno}: bare except")
            elif node.body and not meaningful and names & _BROAD_EXCEPTION_NAMES:
                findings.append(
                    f"{relative}:{node.lineno}: broad except-pass blackhole for {sorted(names)}"
                )
    assert scanned > 0
    assert not findings, "silent exception blackholes detected:\n" + "\n".join(findings)


def test_runtime_has_no_executable_pass_or_ellipsis_function_stubs() -> None:
    """Concrete runtime functions must contain executable behavior, not pass/ellipsis placeholders."""
    findings: list[str] = []
    scanned = 0
    for path in _python_files():
        scanned += 1
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        relative = path.relative_to(ROOT)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = _function_body_without_docstring(node)
            if body and all(_is_pass_or_ellipsis(statement) for statement in body):
                findings.append(f"{relative}:{node.lineno}: executable function stub {node.name}")
    assert scanned > 0
    assert not findings, "runtime pass/ellipsis function stubs detected:\n" + "\n".join(findings)


def test_runtime_does_not_import_mock_patch_frameworks() -> None:
    """Production/runtime surfaces must not depend on test mocking or monkeypatch frameworks."""
    findings: list[str] = []
    scanned = 0
    for path in _python_files():
        scanned += 1
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        relative = path.relative_to(ROOT)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "mock" or alias.name.startswith("unittest.mock"):
                        findings.append(f"{relative}:{node.lineno}: runtime mock import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "mock" or module.startswith("unittest.mock"):
                    findings.append(f"{relative}:{node.lineno}: runtime mock import from {module}")
    assert scanned > 0
    assert not findings, "runtime mock/patch framework imports detected:\n" + "\n".join(findings)


def test_runtime_python_sources_compile_under_ast_parser() -> None:
    failures: list[str] = []
    scanned = 0
    for path in _python_files():
        scanned += 1
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeError) as exc:
            failures.append(f"{path.relative_to(ROOT)}: {type(exc).__name__}: {exc}")
    assert scanned > 0
    assert not failures, "runtime Python parse failures:\n" + "\n".join(failures)
