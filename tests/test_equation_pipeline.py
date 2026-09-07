from __future__ import annotations

from gremlin_mcp.equation_pipeline import audit_equation_transcript


def test_pipeline_extracts_and_audits_without_manual_witness_bundle() -> None:
    text = """
    a = 2.0
    b = 3.0
    c = 5.0
    Eq. (1): q = a*b/c ~= 1200
    Eq. (2): y = 4*pi*k*x**2/c**5
    Eq. (3): y = 2*k*x**2/c**5
    """
    result = audit_equation_transcript(
        text,
        source_id="synthetic:pipeline:1",
        classification="SYNTHETIC_VALIDATION",
    )
    assert result["status"] == "AUDIT_COMPLETE"
    assert result["proposal_count"] == 2
    assert result["audited_witness_count"] == 2
    assert result["fail_count"] == 2
    assert result["pass_count"] == 0
    assert result["unresolved_count"] == 0
    assert len(result["detected_issue_ids"]) == 2
    assert result["authority"]["canon_allowed"] is False


def test_pipeline_preserves_unresolved_symbols_fail_closed() -> None:
    text = "Eq. (4): z = alpha*x**2 ~= 4.0"
    result = audit_equation_transcript(
        text,
        source_id="synthetic:pipeline:2",
        classification="SYNTHETIC_VALIDATION",
    )
    assert result["status"] == "AUDIT_COMPLETE_WITH_UNRESOLVED"
    assert result["proposal_count"] == 0
    assert result["audited_witness_count"] == 0
    assert result["unresolved_count"] == 1
    assert result["detected_issue_ids"] == []


def test_pipeline_handles_empty_text_without_fabricating_results() -> None:
    result = audit_equation_transcript(
        "",
        source_id="synthetic:pipeline:empty",
        classification="SYNTHETIC_VALIDATION",
    )
    assert result["status"] == "NO_TEXT_FAIL_CLOSED"
    assert result["audited_witness_count"] == 0
    assert result["detected_issue_ids"] == []
