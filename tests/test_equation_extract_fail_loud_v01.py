from __future__ import annotations

import pytest

from gremlin_mcp.equation_extract import propose_equation_witnesses


def test_equation_extractor_rejects_non_string_text_instead_of_stringifying() -> None:
    for value in (None, 123, True, ["Eq. (1): x = 1"], {"text": "Eq. (1): x = 1"}):
        with pytest.raises(ValueError, match="text must be a string"):
            propose_equation_witnesses(value, source_id="fixture:eq")  # type: ignore[arg-type]


def test_equation_extractor_rejects_non_string_source_id() -> None:
    for value in (123, True, ["source"]):
        with pytest.raises(ValueError, match="source_id must be a string"):
            propose_equation_witnesses("Eq. (1): x = 1", source_id=value)  # type: ignore[arg-type]


def test_equation_extractor_rejects_empty_source_id() -> None:
    with pytest.raises(ValueError, match="source_id must be non-empty"):
        propose_equation_witnesses("Eq. (1): x = 1", source_id="   ")


def test_empty_string_remains_explicit_no_text_fail_closed_state() -> None:
    result = propose_equation_witnesses("   ", source_id="fixture:empty")
    assert result["status"] == "NO_TEXT_FAIL_CLOSED"
    assert result["witness_proposals"] == []
    assert result["unresolved_proposals"] == []
    assert result["authority"] == {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
