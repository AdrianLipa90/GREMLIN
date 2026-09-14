from __future__ import annotations

import pytest

from gremlin_mcp.math_token_normalize import normalize_math_tokens


def test_token_container_does_not_accept_string_or_mapping_iteration() -> None:
    with pytest.raises(ValueError, match="tokens must be an iterable of strings"):
        normalize_math_tokens("6.674")
    with pytest.raises(ValueError, match="tokens must be an iterable of strings"):
        normalize_math_tokens({"token": "6"})  # type: ignore[arg-type]


def test_non_string_tokens_do_not_stringify() -> None:
    for value in (123, True, ["6"], {"value": "6"}):
        with pytest.raises(ValueError, match="tokens must contain only strings"):
            normalize_math_tokens(["x", value])  # type: ignore[list-item]


def test_empty_string_tokens_are_dropped_but_never_coerced() -> None:
    result = normalize_math_tokens(["", "   ", "π"])
    assert result["input_tokens"] == ["π"]
    assert result["tokens"] == ["pi"]
    assert result["authority"]["canon_allowed"] is False
