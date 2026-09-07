from __future__ import annotations

from gremlin_mcp.pdf_math_layout import classify_equation_region


def _span(text: str, x0: float, y0: float, x1: float, y1: float, size: float = 12.0):
    return {"text": text, "bbox": [x0, y0, x1, y1], "size": size}


def test_single_baseline_equation_is_safe_to_linearize() -> None:
    spans = [
        _span("q", 10, 100, 18, 112),
        _span("=", 24, 100, 32, 112),
        _span("a*b/c", 38, 100, 82, 112),
        _span("≈", 88, 100, 96, 112),
        _span("1.2", 102, 100, 124, 112),
        _span("(1.1)", 180, 100, 214, 112),
    ]
    result = classify_equation_region(spans, page_number=3, equation_label="(1.1)")
    assert result["status"] == "LINEARIZATION_SAFE"
    assert result["linear_text"] == "q = a*b/c ≈ 1.2"
    assert result["source_locator"] == "page:3:eq:(1.1)"
    assert result["provenance"]["page_number"] == 3


def test_stacked_fraction_is_not_guessed() -> None:
    spans = [
        _span("q", 10, 100, 18, 112),
        _span("=", 24, 100, 32, 112),
        _span("a*b", 50, 90, 76, 102),
        _span("c", 58, 114, 66, 126),
        _span("(1.2)", 180, 100, 214, 112),
    ]
    result = classify_equation_region(spans, page_number=3, equation_label="(1.2)")
    assert result["status"] == "TWO_DIMENSIONAL_MATH_UNRESOLVED"
    assert result["linear_text"] is None
    assert "VERTICAL_STACKING_DETECTED" in result["flags"]


def test_superscript_layout_is_not_silently_flattened() -> None:
    spans = [
        _span("E", 10, 100, 18, 112),
        _span("=", 24, 100, 32, 112),
        _span("m", 38, 100, 46, 112),
        _span("c", 52, 100, 60, 112),
        _span("2", 61, 92, 66, 100, size=8),
        _span("(1.3)", 180, 100, 214, 112),
    ]
    result = classify_equation_region(spans, page_number=4, equation_label="(1.3)")
    assert result["status"] == "TWO_DIMENSIONAL_MATH_UNRESOLVED"
    assert result["linear_text"] is None
    assert "MIXED_BASELINES_DETECTED" in result["flags"]


def test_missing_label_fails_closed() -> None:
    spans = [_span("q", 10, 100, 18, 112), _span("=", 24, 100, 32, 112)]
    result = classify_equation_region(spans, page_number=1, equation_label="(9.9)")
    assert result["status"] == "LABEL_NOT_FOUND_FAIL_CLOSED"
    assert result["linear_text"] is None


def test_layout_receipt_is_deterministic() -> None:
    spans = [
        _span("x", 10, 20, 18, 32),
        _span("=", 24, 20, 32, 32),
        _span("2", 38, 20, 46, 32),
        _span("(2.1)", 100, 20, 130, 32),
    ]
    a = classify_equation_region(spans, page_number=2, equation_label="(2.1)")
    b = classify_equation_region(spans, page_number=2, equation_label="(2.1)")
    assert a["layout_commitment"] == b["layout_commitment"]
    assert len(a["layout_commitment"]) == 64
