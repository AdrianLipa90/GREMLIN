from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_AUDIT_ROOTS = (
    ROOT / "gremlin_mcp",
    ROOT / "tools",
    ROOT / "client",
    ROOT / "examples",
    ROOT / "benchmarks",
)
_BROAD = {"BaseException", "Exception", "OSError"}


def _files():
    for root in PYTHON_AUDIT_ROOTS:
        if root.exists():
            yield from sorted(path for path in root.rglob("*.py") if path.is_file())


def _names(node: ast.expr | None) -> set[str]:
    if node is None:
        return {"<bare>"}
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.Attribute):
        return {node.attr}
    if isinstance(node, ast.Tuple):
        out: set[str] = set()
        for item in node.elts:
            out.update(_names(item))
        return out
    return {"<dynamic>"}


def _observable(handler: ast.ExceptHandler) -> bool:
    """A broad handler must raise, return an explicit result, or record/report through a call.

    Pure pass/continue/break/assignment handlers erase the error channel and therefore violate the
    repository fail-loud contract. Calls include explicit logging, receipt/error collection, cleanup
    and wrapping paths; those remain auditable by their surrounding tests.
    """
    for child in ast.walk(handler):
        if child is handler:
            continue
        if isinstance(child, (ast.Raise, ast.Return, ast.Call)):
            return True
    return False


def test_broad_exception_handlers_do_not_silently_continue_or_fallback() -> None:
    findings: list[str] = []
    scanned = 0
    for path in _files():
        scanned += 1
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative = path.relative_to(ROOT)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            names = _names(node.type)
            if "<bare>" in names or names & _BROAD:
                if not _observable(node):
                    findings.append(
                        f"{relative}:{node.lineno}: broad handler erases failure channel: {sorted(names)}"
                    )
    assert scanned > 0
    assert not findings, "silent broad exception fallbacks detected:\n" + "\n".join(findings)
