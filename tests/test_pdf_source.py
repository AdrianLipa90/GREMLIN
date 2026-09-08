from __future__ import annotations

from gremlin_mcp.pdf_source import build_equation_regions_from_pages


def _span(text, x0, y0, x1, y1, *, block=0, line=0, size=12.0):
    return {
        "text": text,
        "bbox": [x0, y0, x1, y1],
        "size": size,
        "block_index": block,
        "line_index": line,
    }


def test_builds_safe_transcript_from_single_baseline_region() -> None:
    pages = [{
        "page_number": 2,
        "width": 600.0,
        "height": 800.0,
        "spans": [
            _span("q", 50, 100, 58, 112),
            _span("=", 64, 100, 72, 112),
            _span("a*b/c", 78, 100, 122, 112),
            _span("≈", 128, 100, 136, 112),
            _span("1.2", 142, 100, 164, 112),
            _span("(2.1)", 500, 100, 536, 112),
            _span("A prose year (2026) is not an equation label.", 50, 150, 300, 162, block=1),
        ],
    }]
    result = build_equation_regions_from_pages(pages, source_id="synthetic.pdf")
    assert result["equation_label_count"] == 1
    assert result["safe_region_count"] == 1
    assert result["simple_recovered_2d_count"] == 0
    assert result["composite_recovered_2d_count"] == 0
    assert result["recovered_2d_count"] == 0
    assert result["unresolved_region_count"] == 0
    assert result["safe_transcript"] == "Eq. (2.1): q = a*b/c ≈ 1.2"
    assert result["auditable_transcript"] == result["safe_transcript"]
    assert result["regions"][0]["source_locator"] == "page:2:eq:(2.1)"


def test_simple_stacked_fraction_is_recovered_but_not_counted_as_safe_linearization() -> None:
    pages = [{
        "page_number": 5,
        "width": 600.0,
        "height": 800.0,
        "spans": [
            _span("q", 50, 100, 58, 112),
            _span("=", 64, 100, 72, 112),
            _span("a*b", 90, 90, 116, 102),
            _span("c", 98, 114, 106, 126),
            _span("(5.4)", 500, 100, 536, 112),
        ],
    }]
    result = build_equation_regions_from_pages(pages, source_id="synthetic.pdf")
    assert result["safe_region_count"] == 0
    assert result["simple_recovered_2d_count"] == 1
    assert result["composite_recovered_2d_count"] == 0
    assert result["recovered_2d_count"] == 1
    assert result["unresolved_region_count"] == 0
    assert result["safe_transcript"] == ""
    assert result["simple_recovered_2d_transcript"] == "Eq. (5.4): q = (a*b)/(c)"
    assert result["recovered_2d_transcript"] == result["simple_recovered_2d_transcript"]
    assert result["auditable_transcript"] == result["recovered_2d_transcript"]
    assert result["regions"][0]["status"] == "TWO_DIMENSIONAL_MATH_UNRESOLVED"
    assert result["regions"][0]["simple_2d_solver"]["status"] == "SOLVED_SIMPLE_2D"
    assert result["regions"][0]["composite_2d_solver"] is None


def test_composite_relation_chain_is_second_recovery_fallback() -> None:
    pages = [{
        "page_number": 6,
        "width": 600.0,
        "height": 800.0,
        "spans": [
            _span("k", 10, 42, 16, 54),
            _span("a", 17, 42, 23, 54),
            _span("b", 24, 42, 30, 54),
            _span("x", 18, 62, 25, 74),
            _span("5", 25, 59, 30, 67, size=8.0),
            _span("=", 40, 50, 48, 62),
            _span("4", 58, 42, 64, 54),
            _span("*", 66, 42, 72, 54),
            _span("(6e-2)", 74, 42, 106, 54),
            _span("*", 108, 42, 114, 54),
            _span("(2e-3)", 116, 42, 148, 54),
            _span("(3e1)", 92, 62, 120, 74),
            _span("5", 120, 59, 125, 67, size=8.0),
            _span("≈", 158, 50, 166, 62),
            _span("1e-9", 174, 50, 198, 62),
            _span("(6.2)", 220, 50, 255, 62),
        ],
    }]
    result = build_equation_regions_from_pages(pages, source_id="synthetic.pdf")
    assert result["safe_region_count"] == 0
    assert result["simple_recovered_2d_count"] == 0
    assert result["composite_recovered_2d_count"] == 1
    assert result["recovered_2d_count"] == 1
    assert result["unresolved_region_count"] == 0
    expected = "Eq. (6.2): (k*a*b)/(x**5) = (4 * (6e-2) * (2e-3))/((3e1)**5) ≈ 1e-9"
    assert result["composite_recovered_2d_transcript"] == expected
    assert result["auditable_transcript"] == expected
    region = result["regions"][0]
    assert region["simple_2d_solver"]["status"] != "SOLVED_SIMPLE_2D"
    assert region["composite_2d_solver"]["status"] == "SOLVED_COMPOSITE_2D"


def test_ambiguous_composite_region_remains_unresolved() -> None:
    pages = [{
        "page_number": 7,
        "width": 600.0,
        "height": 800.0,
        "spans": [
            _span("q", 10, 50, 18, 62),
            _span("=", 30, 50, 38, 62),
            _span("a", 50, 35, 58, 47),
            _span("b", 50, 52, 58, 64),
            _span("c", 50, 69, 58, 81),
            _span("(7.3)", 180, 50, 215, 62),
        ],
    }]
    result = build_equation_regions_from_pages(pages, source_id="synthetic.pdf")
    assert result["safe_region_count"] == 0
    assert result["recovered_2d_count"] == 0
    assert result["unresolved_region_count"] == 1
    region = result["regions"][0]
    assert region["simple_2d_solver"]["status"] != "SOLVED_SIMPLE_2D"
    assert region["composite_2d_solver"]["status"] == "AMBIGUOUS_COMPOSITE_2D_UNRESOLVED"


def test_cross_block_fraction_is_not_mistaken_for_label_block_only() -> None:
    pages = [{
        "page_number": 8,
        "width": 600.0,
        "height": 800.0,
        "spans": [
            _span("q", 50, 100, 58, 112, block=10),
            _span("=", 64, 100, 72, 112, block=10),
            _span("a*b", 90, 92, 116, 104, block=11),
            _span("c", 98, 112, 106, 124, block=12),
            _span("2", 107, 108, 112, 116, block=12, size=8.0),
            _span("(8.3)", 500, 100, 536, 112, block=13),
        ],
    }]
    result = build_equation_regions_from_pages(pages, source_id="synthetic.pdf", vertical_margin_factor=1.7)
    region = result["regions"][0]
    assert region["status"] == "TWO_DIMENSIONAL_MATH_UNRESOLVED"
    texts = {span["text"] for span in region["provenance"]["spans"]}
    assert {"q", "=", "a*b", "c", "2", "(8.3)"} <= texts


def test_region_selection_excludes_prose_from_adjacent_blocks() -> None:
    pages = [{
        "page_number": 1,
        "width": 600.0,
        "height": 800.0,
        "spans": [
            _span("x", 50, 100, 58, 112, block=3),
            _span("=", 64, 100, 72, 112, block=3),
            _span("2", 78, 100, 86, 112, block=3),
            _span("(1.1)", 500, 100, 536, 112, block=3),
            _span("unrelated", 100, 101, 160, 113, block=4),
        ],
    }]
    result = build_equation_regions_from_pages(pages, source_id="synthetic.pdf")
    assert result["safe_transcript"] == "Eq. (1.1): x = 2"
    assert all(span["text"] != "unrelated" for span in result["regions"][0]["provenance"]["spans"])


def test_source_receipt_is_deterministic_and_noncanonical() -> None:
    pages = [{
        "page_number": 1,
        "width": 100.0,
        "height": 100.0,
        "spans": [
            _span("x", 10, 20, 18, 32),
            _span("=", 24, 20, 32, 32),
            _span("2", 38, 20, 46, 32),
            _span("(1.1)", 60, 20, 90, 32),
        ],
    }]
    a = build_equation_regions_from_pages(pages, source_id="synthetic.pdf")
    b = build_equation_regions_from_pages(pages, source_id="synthetic.pdf")
    assert a["source_commitment"] == b["source_commitment"]
    assert len(a["source_commitment"]) == 64
    assert a["authority"]["canon_allowed"] is False
