from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOTS = (ROOT / "gremlin_mcp", ROOT / "tools", ROOT / "client")


def _python_files():
    for root in RUNTIME_ROOTS:
        if not root.exists():
            continue
        yield from sorted(path for path in root.rglob("*.py") if path.is_file())


def test_runtime_has_no_bare_except_or_except_pass_blackholes() -> None:
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
            if node.type is None:
                findings.append(f"{relative}:{node.lineno}: bare except")
            meaningful = [statement for statement in node.body if not isinstance(statement, ast.Pass)]
            if node.body and not meaningful:
                findings.append(f"{relative}:{node.lineno}: except handler contains only pass")
    assert scanned > 0
    assert not findings, "silent exception blackholes detected:\n" + "\n".join(findings)


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
