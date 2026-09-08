from __future__ import annotations

from gremlin_mcp.composite_math_layout import solve_composite_2d_equation


def _span(text, x0, y0, x1, y1, *, size=12.0):
    return {"text": text, "bbox": [x0, y0, x1, y1], "size": size}


def test_renders_subscript_and_fraction_on_rhs() -> None:
    spans = [
        _span("r", 10, 50, 18, 62),
        _span("s", 18, 55, 23, 63, size=8.0),
        _span("=", 30, 50, 38, 62),
        _span("2", 50, 42, 56, 54),
        _span("G", 57, 42, 65, 54),
        _span("M", 66, 42, 75, 54),
        _span("c", 58, 62, 66, 74),
        _span("2", 66, 59, 71, 67, size=8.0),
        _span("(1.1)", 180, 50, 215, 62),
    ]
    result = solve_composite_2d_equation(spans, page_number=1, equation_label="(1.1)")
    assert result["status"] == "SOLVED_COMPOSITE_2D"
    assert result["linear_text"] == "r_s = (2*G*M)/(c**2)"
    assert {"SUBSCRIPT", "SUPERSCRIPT", "STACKED_FRACTION"} <= set(result["constructs"])
    assert result["authority"]["canon_allowed"] is False


def test_renders_fraction_equals_fraction_approximately_numeric_chain() -> None:
    spans = [
        # left fraction: k*a*b / x^5
        _span("k", 10, 42, 16, 54),
        _span("a", 17, 42, 23, 54),
        _span("b", 24, 42, 30, 54),
        _span("x", 18, 62, 25, 74),
        _span("5", 25, 59, 30, 67, size=8.0),
        _span("=", 40, 50, 48, 62),
        # middle fraction: 4*(6e-2)*(2e-3) / (3e1)^5
        _span("4", 58, 42, 64, 54),
        _span("*", 66, 42, 72, 54),
        _span("(6e-2)", 74, 42, 106, 54),
        _span("*", 108, 42, 114, 54),
        _span("(2e-3)", 116, 42, 148, 54),
        _span("(3e1)", 92, 62, 120, 74),
        _span("5", 120, 59, 125, 67, size=8.0),
        _span("≈", 158, 50, 166, 62),
        _span("1e-9", 174, 50, 198, 62),
        _span("(2.4)", 220, 50, 255, 62),
    ]
    result = solve_composite_2d_equation(spans, page_number=2, equation_label="(2.4)")
    assert result["status"] == "SOLVED_COMPOSITE_2D"
    assert result["linear_text"] == "(k*a*b)/(x**5) = (4*(6e-2)*(2e-3))/((3e1)**5) ≈ 1e-9"
    assert result["relation_count"] == 2
    assert "STACKED_FRACTION" in result["constructs"]
    assert "SUPERSCRIPT" in result["constructs"]


def test_ambiguous_three_level_fraction_fails_closed() -> None:
    spans = [
        _span("q", 10, 50, 18, 62),
        _span("=", 30, 50, 38, 62),
        _span("a", 50, 35, 58, 47),
        _span("b", 50, 52, 58, 64),
        _span("c", 50, 69, 58, 81),
        _span("(3.1)", 180, 50, 215, 62),
    ]
    result = solve_composite_2d_equation(spans, page_number=3, equation_label="(3.1)")
    assert result["status"] == "AMBIGUOUS_COMPOSITE_2D_UNRESOLVED"
    assert result["linear_text"] is None
    assert result["authority"]["canon_allowed"] is False
