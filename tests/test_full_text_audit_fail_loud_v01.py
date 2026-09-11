from __future__ import annotations

import pytest

from gremlin_mcp.full_text_audit import audit_full_text


def test_full_text_audit_rejects_non_string_text_instead_of_stringifying() -> None:
    for value in (None, 123, True, ["text"], {"text": "value"}):
        with pytest.raises(ValueError, match="text must be a string"):
            audit_full_text(value, source_id="fixture:type")  # type: ignore[arg-type]


def test_full_text_audit_rejects_non_string_source_id_instead_of_stringifying() -> None:
    for value in (123, True, ["source"]):
        with pytest.raises(ValueError, match="source_id must be a string"):
            audit_full_text("Evidence text.", source_id=value)  # type: ignore[arg-type]


def test_full_text_audit_rejects_empty_source_id() -> None:
    with pytest.raises(ValueError, match="source_id must be non-empty"):
        audit_full_text("Evidence text.", source_id="   ")


def test_empty_string_remains_explicit_fail_closed_state() -> None:
    result = audit_full_text("   ", source_id="fixture:empty")
    assert result["status"] == "NO_TEXT_FAIL_CLOSED"
    assert result["authority"] == {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
