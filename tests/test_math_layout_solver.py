from __future__ import annotations

from gremlin_mcp.math_layout_solver import solve_simple_2d_equation


def _s(text, x0, y0, x1, y1, size=12.0):
    return {"text": text, "bbox": [x0, y0, x1, y1], "size": size}


def test_solves_single_stacked_fraction() -> None:
    spans = [
        _s("q", 10, 100, 18, 112),
        _s("=", 24, 100, 32, 112),
        _s("a*b", 50, 90, 76, 102),
        _s("c", 58, 114, 66, 126),
        _s("(1.1)", 180, 100, 214, 112),
    ]
    result = solve_simple_2d_equation(spans, page_number=1, equation_label="(1.1)")
    assert result["status"] == "SOLVED_SIMPLE_2D"
    assert result["linear_text"] == "q = (a*b)/(c)"
    assert result["constructs"] == ["SINGLE_STACKED_FRACTION"]


def test_solves_simple_superscript_without_flattening_it() -> None:
    spans = [
        _s("E", 10, 100, 18, 112),
        _s("=", 24, 100, 32, 112),
        _s("m", 38, 100, 46, 112),
        _s("c", 52, 100, 60, 112),
        _s("2", 61, 92, 66, 100, size=8.0),
        _s("(1.2)", 180, 100, 214, 112),
    ]
    result = solve_simple_2d_equation(spans, page_number=1, equation_label="(1.2)")
    assert result["status"] == "SOLVED_SIMPLE_2D"
    assert result["linear_text"] == "E = m*c**2"
    assert result["constructs"] == ["SUPERSCRIPT"]


def test_ambiguous_multiple_vertical_groups_remain_unresolved() -> None:
    spans = [
        _s("q", 10, 100, 18, 112),
        _s("=", 24, 100, 32, 112),
        _s("a", 50, 90, 58, 102),
        _s("b", 52, 114, 60, 126),
        _s("c", 90, 90, 98, 102),
        _s("d", 92, 114, 100, 126),
        _s("(1.3)", 180, 100, 214, 112),
    ]
    result = solve_simple_2d_equation(spans, page_number=1, equation_label="(1.3)")
    assert result["status"] == "AMBIGUOUS_2D_LAYOUT_UNRESOLVED"
    assert result["linear_text"] is None


def test_missing_or_multiple_equals_fail_closed() -> None:
    missing = [_s("q", 10, 100, 18, 112), _s("(1.4)", 180, 100, 214, 112)]
    result = solve_simple_2d_equation(missing, page_number=1, equation_label="(1.4)")
    assert result["status"] == "UNSUPPORTED_2D_LAYOUT_UNRESOLVED"

    multiple = [
        _s("q", 10, 100, 18, 112), _s("=", 24, 100, 32, 112),
        _s("x", 38, 100, 46, 112), _s("=", 52, 100, 60, 112),
        _s("2", 66, 100, 74, 112), _s("(1.5)", 180, 100, 214, 112),
    ]
    result = solve_simple_2d_equation(multiple, page_number=1, equation_label="(1.5)")
    assert result["status"] == "UNSUPPORTED_2D_LAYOUT_UNRESOLVED"


def test_solver_receipt_is_deterministic_and_noncanonical() -> None:
    spans = [
        _s("q", 10, 100, 18, 112), _s("=", 24, 100, 32, 112),
        _s("a", 50, 90, 58, 102), _s("b", 50, 114, 58, 126),
        _s("(2.1)", 180, 100, 214, 112),
    ]
    a = solve_simple_2d_equation(spans, page_number=2, equation_label="(2.1)")
    b = solve_simple_2d_equation(spans, page_number=2, equation_label="(2.1)")
    assert a["solver_commitment"] == b["solver_commitment"]
    assert len(a["solver_commitment"]) == 64
    assert a["authority"]["canon_allowed"] is False
