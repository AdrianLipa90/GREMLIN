from __future__ import annotations

from gremlin_mcp.math_token_normalize import normalize_math_tokens


def test_stitches_fragmented_decimal_atoms_without_crossing_operators() -> None:
    result = normalize_math_tokens(["6", ".", "674", "×", "10**-11"])
    assert result["tokens"] == ["6.674", "*", "10**-11"]
    assert "DECIMAL_FRAGMENT_STITCHED" in result["transforms"]


def test_stitches_decimal_when_open_parenthesis_shares_first_digit_span() -> None:
    result = normalize_math_tokens(["(6", ".", "674", "*", "10**-11", ")"])
    assert result["tokens"] == ["(6.674", "*", "10**-11", ")"]
    assert "DECIMAL_FRAGMENT_STITCHED" in result["transforms"]


def test_normalizes_pi_and_unicode_minus_conservatively() -> None:
    result = normalize_math_tokens(["4", "π", "G", "h", "/", "c", "**", "−5"])
    assert result["tokens"] == ["4", "pi", "G", "h", "/", "c", "**", "-5"]
    assert "UNICODE_PI_NORMALIZED" in result["transforms"]
    assert "UNICODE_MINUS_NORMALIZED" in result["transforms"]


def test_does_not_merge_decimal_fragments_across_multiplication() -> None:
    result = normalize_math_tokens(["6", "*", ".", "674"])
    assert result["tokens"] == ["6", "*", ".", "674"]
    assert "DECIMAL_FRAGMENT_STITCHED" not in result["transforms"]


def test_stitches_leading_decimal_when_adjacent() -> None:
    result = normalize_math_tokens([".", "125", "+", "2"])
    assert result["tokens"] == ["0.125", "+", "2"]


def test_preserves_units_as_tokens_instead_of_dropping_them() -> None:
    result = normalize_math_tokens(["2", ".", "052", "×", "10**-95", "s**2"])
    assert result["tokens"] == ["2.052", "*", "10**-95", "s**2"]
    assert result["authority"]["canon_allowed"] is False
