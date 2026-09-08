from __future__ import annotations

from gremlin_mcp.pdf_equation_pipeline import audit_equations_from_pages


def _span(text, x0, y0, x1, y1, *, block=0, line=0, size=12.0):
    return {
        "text": text,
        "bbox": [x0, y0, x1, y1],
        "size": size,
        "block_index": block,
        "line_index": line,
    }


def test_pdf_regions_feed_equation_audit_with_commitment_lineage() -> None:
    pages = [{
        "page_number": 1,
        "width": 600.0,
        "height": 800.0,
        "spans": [
            _span("x", 50, 100, 58, 112),
            _span("=", 64, 100, 72, 112),
            _span("2+3", 78, 100, 104, 112),
            _span("≈", 110, 100, 118, 112),
            _span("5", 124, 100, 132, 112),
            _span("(1.1)", 500, 100, 536, 112),
        ],
    }]
    result = audit_equations_from_pages(
        pages,
        source_id="synthetic.pdf",
        classification="SYNTHETIC_EXTERNAL_PAPER_AUDIT",
    )

    assert result["status"] == "PDF_EQUATION_AUDIT_COMPLETE"
    assert result["pdf_source"]["safe_region_count"] == 1
    assert result["pdf_source"]["recovered_2d_count"] == 0
    assert result["auditable_transcript"] == "Eq. (1.1): x = 2+3 ≈ 5"
    assert result["equation_pipeline"]["proposal_count"] == 1
    assert result["equation_pipeline"]["pass_count"] == 1
    assert result["equation_pipeline"]["fail_count"] == 0
    assert result["lineage"]["pdf_source_commitment"] == result["pdf_source"]["source_commitment"]
    assert result["lineage"]["equation_pipeline_commitment"] == result["equation_pipeline"]["pipeline_commitment"]
    assert len(result["lineage"]["auditable_transcript_commitment"]) == 64
    assert len(result["pipeline_commitment"]) == 64
    assert result["authority"]["canon_allowed"] is False


def test_pdf_equation_pipeline_fails_closed_without_numbered_equations() -> None:
    pages = [{
        "page_number": 1,
        "width": 600.0,
        "height": 800.0,
        "spans": [
            _span("ordinary prose", 50, 100, 160, 112),
            _span("2026", 170, 100, 200, 112),
        ],
    }]
    result = audit_equations_from_pages(
        pages,
        source_id="no-equations.pdf",
        classification="SYNTHETIC_EXTERNAL_PAPER_AUDIT",
    )
    assert result["status"] == "NO_AUDITABLE_EQUATIONS_FAIL_CLOSED"
    assert result["auditable_transcript"] == ""
    assert result["equation_pipeline"]["status"] == "NO_TEXT_FAIL_CLOSED"
    assert result["equation_pipeline"]["proposal_count"] == 0
    assert result["authority"]["canon_allowed"] is False


def test_recovered_2d_equation_enters_audit_but_retains_recovery_provenance() -> None:
    pages = [{
        "page_number": 2,
        "width": 600.0,
        "height": 800.0,
        "spans": [
            _span("q", 50, 100, 58, 112),
            _span("=", 64, 100, 72, 112),
            _span("6*4", 90, 90, 116, 102),
            _span("3", 98, 114, 106, 126),
            _span("(2.1)", 500, 100, 536, 112),
        ],
    }]
    result = audit_equations_from_pages(
        pages,
        source_id="fraction.pdf",
        classification="SYNTHETIC_EXTERNAL_PAPER_AUDIT",
    )
    assert result["pdf_source"]["safe_region_count"] == 0
    assert result["pdf_source"]["recovered_2d_count"] == 1
    assert result["pdf_source"]["unresolved_region_count"] == 0
    assert result["auditable_transcript"] == "Eq. (2.1): q = (6*4)/(3)"
    assert result["equation_pipeline"]["status"] == "NO_EXECUTABLE_WITNESSES_FAIL_CLOSED"
    region = result["pdf_source"]["regions"][0]
    assert region["simple_2d_solver"]["status"] == "SOLVED_SIMPLE_2D"
    assert region["status"] == "TWO_DIMENSIONAL_MATH_UNRESOLVED"
