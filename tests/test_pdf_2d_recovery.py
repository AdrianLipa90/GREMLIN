from __future__ import annotations

from gremlin_mcp.pdf_source import build_equation_regions_from_pages


def _s(text, x0, y0, x1, y1, *, size=12.0, block=0):
    return {
        "text": text,
        "bbox": [x0, y0, x1, y1],
        "size": size,
        "block_index": block,
        "line_index": 0,
    }


def test_pdf_adapter_recovers_simple_fraction_but_keeps_safe_count_separate() -> None:
    pages = [{
        "page_number": 2,
        "width": 600.0,
        "height": 800.0,
        "spans": [
            _s("q", 50, 100, 58, 112, block=1),
            _s("=", 64, 100, 72, 112, block=1),
            _s("a*b", 90, 90, 116, 102, block=2),
            _s("c", 98, 114, 106, 126, block=3),
            _s("(2.1)", 500, 100, 536, 112, block=4),
        ],
    }]
    result = build_equation_regions_from_pages(pages, source_id="synthetic.pdf")
    assert result["safe_region_count"] == 0
    assert result["recovered_2d_count"] == 1
    assert result["unresolved_region_count"] == 0
    assert result["safe_transcript"] == ""
    assert result["auditable_transcript"] == "Eq. (2.1): q = (a*b)/(c)"
    assert result["regions"][0]["simple_2d_solver"]["status"] == "SOLVED_SIMPLE_2D"


def test_pdf_adapter_recovers_superscript() -> None:
    pages = [{
        "page_number": 3,
        "width": 600.0,
        "height": 800.0,
        "spans": [
            _s("E", 50, 100, 58, 112),
            _s("=", 64, 100, 72, 112),
            _s("m", 78, 100, 86, 112),
            _s("c", 92, 100, 100, 112),
            _s("2", 101, 92, 106, 100, size=8.0),
            _s("(3.1)", 500, 100, 536, 112),
        ],
    }]
    result = build_equation_regions_from_pages(pages, source_id="synthetic.pdf")
    assert result["recovered_2d_count"] == 1
    assert result["auditable_transcript"] == "Eq. (3.1): E = m*c**2"


def test_ambiguous_2d_stays_unresolved_and_never_enters_auditable_transcript() -> None:
    pages = [{
        "page_number": 4,
        "width": 600.0,
        "height": 800.0,
        "spans": [
            _s("q", 50, 100, 58, 112),
            _s("=", 64, 100, 72, 112),
            _s("a", 90, 90, 98, 102),
            _s("b", 92, 114, 100, 126),
            _s("c", 130, 90, 138, 102),
            _s("d", 132, 114, 140, 126),
            _s("(4.1)", 500, 100, 536, 112),
        ],
    }]
    result = build_equation_regions_from_pages(pages, source_id="synthetic.pdf")
    assert result["safe_region_count"] == 0
    assert result["recovered_2d_count"] == 0
    assert result["unresolved_region_count"] == 1
    assert result["auditable_transcript"] == ""
    assert result["regions"][0]["simple_2d_solver"]["status"] == "AMBIGUOUS_2D_LAYOUT_UNRESOLVED"
