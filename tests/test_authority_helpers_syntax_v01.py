"""Protect against literal '\\n' corruption in authority helper definitions.

Importing the server has side effects; parse all affected source units with
the Python AST without executing module-level imports or live runtime code.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
AFFECTED = (
    "gremlin_mcp/ferret.py",
    "gremlin_mcp/pipeline.py",
    "gremlin_mcp/router.py",
    "gremlin_mcp/web.py",
)


@pytest.mark.parametrize("relative_path", AFFECTED)
def test_authority_helper_is_valid_python_with_real_newlines(relative_path: str) -> None:
    path = ROOT / relative_path
    source = path.read_text(encoding="utf-8")
    # The previous regression accidentally wrote literal backslash-n bytes
    # into source text, causing SyntaxError during module import.
    assert "def _authority() -> dict[str, Any]:\\n" not in source
    parsed = ast.parse(source, filename=str(path))
    helpers = [
        node for node in parsed.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "_authority"
    ]
    assert len(helpers) == 1
    body = helpers[0].body
    assert len(body) == 1
    assert isinstance(body[0], ast.Return)
    assert isinstance(body[0].value, ast.Call)
    assert isinstance(body[0].value.func, ast.Name)
    assert body[0].value.func.id == "authority_envelope"
