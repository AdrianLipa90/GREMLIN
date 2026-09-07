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
    assert result["unresolved_region_count"] == 0
    assert result["safe_transcript"] == "Eq. (2.1): q = a*b/c ≈ 1.2"
    assert result["regions"][0]["source_locator"] == "page:2:eq:(2.1)"


def test_stacked_equation_is_preserved_as_unresolved_region() -> None:
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
    assert result["unresolved_region_count"] == 1
    assert result["safe_transcript"] == ""
    assert result["regions"][0]["status"] == "TWO_DIMENSIONAL_MATH_UNRESOLVED"


def test_cross_block_fraction_is_not_mistaken_for_label_block_only() -> None:
    pages = [{
        "page_number": 7,
        "width": 600.0,
        "height": 800.0,
        "spans": [
            _span("q", 50, 100, 58, 112, block=10),
            _span("=", 64, 100, 72, 112, block=10),
            _span("a*b", 90, 92, 116, 104, block=11),
            _span("c", 98, 112, 106, 124, block=12),
            _span("2", 107, 108, 112, 116, block=12, size=8.0),
            _span("(7.3)", 500, 100, 536, 112, block=13),
        ],
    }]
    result = build_equation_regions_from_pages(pages, source_id="synthetic.pdf", vertical_margin_factor=1.7)
    region = result["regions"][0]
    assert region["status"] == "TWO_DIMENSIONAL_MATH_UNRESOLVED"
    texts = {span["text"] for span in region["provenance"]["spans"]}
    assert {"q", "=", "a*b", "c", "2", "(7.3)"} <= texts


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
