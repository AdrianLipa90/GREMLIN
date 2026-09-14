from __future__ import annotations

import pytest

from gremlin_mcp.composite_math_layout import solve_composite_2d_equation


def _span(text="x", bbox=None, size=12.0):
    return {
        "text": text,
        "bbox": [0.0, 0.0, 10.0, 10.0] if bbox is None else bbox,
        "size": size,
    }


def test_spans_container_and_rows_require_objects() -> None:
    with pytest.raises(ValueError, match="spans must be an iterable of objects"):
        solve_composite_2d_equation("bad", page_number=1, equation_label="(1.1)")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="spans must contain only objects"):
        solve_composite_2d_equation(["bad"], page_number=1, equation_label="(1.1)")  # type: ignore[list-item]


def test_span_text_does_not_stringify() -> None:
    with pytest.raises(ValueError, match="text must be a string"):
        solve_composite_2d_equation([_span(text=123)], page_number=1, equation_label="(1.1)")


def test_bbox_coordinates_do_not_float_coerce_strings_or_booleans() -> None:
    with pytest.raises(ValueError, match="span bbox coordinate must be a finite number"):
        solve_composite_2d_equation([_span(bbox=["0", 0, 10, 10])], page_number=1, equation_label="(1.1)")
    with pytest.raises(ValueError, match="span bbox coordinate must be a finite number"):
        solve_composite_2d_equation([_span(bbox=[False, 0, 10, 10])], page_number=1, equation_label="(1.1)")


def test_explicit_zero_or_string_size_is_not_replaced_by_default() -> None:
    with pytest.raises(ValueError, match="span size must be positive"):
        solve_composite_2d_equation([_span(size=0)], page_number=1, equation_label="(1.1)")
    with pytest.raises(ValueError, match="span size must be a finite number"):
        solve_composite_2d_equation([_span(size="12")], page_number=1, equation_label="(1.1)")


def test_page_number_is_exact_positive_integer() -> None:
    for value in (True, 1.0, "1"):
        with pytest.raises(ValueError, match="page_number must be an integer"):
            solve_composite_2d_equation([], page_number=value, equation_label="(1.1)")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="page_number must be >= 1"):
        solve_composite_2d_equation([], page_number=0, equation_label="(1.1)")


def test_equation_label_is_exact_nonempty_string() -> None:
    with pytest.raises(ValueError, match="equation_label must be a string"):
        solve_composite_2d_equation([], page_number=1, equation_label=123)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="equation_label must be non-empty"):
        solve_composite_2d_equation([], page_number=1, equation_label="   ")


def test_missing_label_remains_explicit_unresolved_state() -> None:
    result = solve_composite_2d_equation([_span("x")], page_number=1, equation_label="(1.1)")
    assert result["status"] == "AMBIGUOUS_COMPOSITE_2D_UNRESOLVED"
    assert result["flags"] == ["EQUATION_LABEL_NOT_FOUND"]
    assert result["authority"]["canon_allowed"] is False
