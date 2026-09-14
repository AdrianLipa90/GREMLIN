from __future__ import annotations

import pytest

import gremlin_mcp.guarded_research as guarded
from gremlin_mcp.evidence_robustness import SUPPORT, excerpt_commitment
from gremlin_mcp.research_provenance import source_receipt_commitment


def _text(source_id: str) -> str:
    return f"Fixture source {source_id}. This exact passage belongs to source {source_id}."


def _receipt(source_id: str) -> dict[str, object]:
    text = _text(source_id)
    receipt: dict[str, object] = {
        "source_id": source_id,
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": f"content:{source_id}:v1",
        "content_length_chars": len(text),
        "evidence_text": text,
    }
    receipt["source_receipt_commitment"] = source_receipt_commitment(receipt)
    return receipt


def _citation(source_id: str) -> dict[str, object]:
    return {
        "source_id": source_id,
        "provider": "fixture",
        "title": f"Fixture {source_id}",
        "url": f"https://example.org/{source_id}",
        "doi": None,
        "published": "2026-09-11",
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": f"content:{source_id}:v1",
    }


def _execution() -> dict[str, object]:
    receipt = _receipt("a")
    return {
        "schema": "GREMLIN_RESEARCH_EXECUTOR_V0_1",
        "version": "0.1.2",
        "query": "test query",
        "status": "CANDIDATE_SYNTHESIS_READY",
        "synthesis": {"candidate": "ok"},
        "citations": [_citation("a")],
        "source_receipts": [receipt],
        "authority": {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False},
    }


def _evidence() -> dict[str, object]:
    excerpt = "This exact passage belongs to source a."
    commitment = excerpt_commitment(excerpt)
    return {
        "evidence_id": "a",
        "source_family": "family-a",
        "stance": SUPPORT,
        "content_commitment": "content:a:v1",
        "excerpt": excerpt,
        "excerpt_commitment": commitment,
        "payload_commitment": commitment,
        "credibility": 0.8,
    }


def test_guard_binding_flags_reject_truthy_strings_and_bool_int_aliases() -> None:
    with pytest.raises(ValueError, match="require_execution_source_binding must be boolean"):
        guarded.apply_claim_evidence_guard(
            _execution(),
            claim_id="claim-a",
            claim_evidence=[_evidence()],
            require_execution_source_binding="false",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="require_execution_content_binding must be boolean"):
        guarded.apply_claim_evidence_guard(
            _execution(),
            claim_id="claim-a",
            claim_evidence=[_evidence()],
            require_execution_content_binding=1,  # type: ignore[arg-type]
        )


def test_claim_id_does_not_coerce_integer() -> None:
    with pytest.raises(ValueError, match="claim_id must be a string"):
        guarded.apply_claim_evidence_guard(
            _execution(),
            claim_id=123,  # type: ignore[arg-type]
            claim_evidence=[_evidence()],
        )


def test_claim_evidence_container_rejects_mapping_string_and_non_object_rows() -> None:
    for value in ({"evidence_id": "a"}, "not-evidence", [_evidence(), "bad-row"]):
        with pytest.raises(ValueError, match="claim_evidence"):
            guarded.apply_claim_evidence_guard(
                _execution(),
                claim_id="claim-a",
                claim_evidence=value,  # type: ignore[arg-type]
            )


def test_execution_citation_source_id_does_not_coerce_integer() -> None:
    execution = _execution()
    execution["citations"][0]["source_id"] = 123  # type: ignore[index]
    with pytest.raises(ValueError, match="citation.source_id must be a string"):
        guarded.apply_claim_evidence_guard(
            execution,
            claim_id="claim-a",
            claim_evidence=[_evidence()],
        )


def test_invalid_receipt_field_type_quarantines_before_semantic_assessment() -> None:
    execution = _execution()
    execution["source_receipts"][0]["content_length_chars"] = "70"  # type: ignore[index]
    result = guarded.apply_claim_evidence_guard(
        execution,
        claim_id="claim-a",
        claim_evidence=[_evidence()],
    )
    assert result["status"] == guarded.SOURCE_RECEIPT_INTEGRITY_FAILED
    assert result["synthesis"] is None
    guard = result["claim_evidence_guard"]
    assert guard["assessment"] is None
    codes = {row["code"] for row in guard["content_binding"]["receipt_integrity"]["errors"]}
    assert "INVALID_RECEIPT_FIELD_TYPE" in codes


def test_evidence_is_bound_using_normalized_bundle_rows() -> None:
    evidence = _evidence()
    evidence["evidence_id"] = " a "
    evidence["source_family"] = " family-a "
    evidence["stance"] = "support"
    result = guarded.apply_claim_evidence_guard(
        _execution(),
        claim_id="claim-a",
        claim_evidence=[evidence],
    )
    bundle_row = result["claim_evidence_guard"]["evidence_bundle"]["evidence"][0]
    assert bundle_row["evidence_id"] == "a"
    assert bundle_row["source_family"] == "family-a"
    assert bundle_row["stance"] == SUPPORT
    assert result["claim_evidence_guard"]["source_binding"]["unknown_evidence_source_ids"] == []


def test_execute_wrapper_rejects_non_string_query_and_non_string_explicit_claim_id(monkeypatch) -> None:
    with pytest.raises(ValueError, match="query must be a string"):
        guarded.execute_guarded_research(123)  # type: ignore[arg-type]

    monkeypatch.setattr(guarded, "execute_research", lambda *args, **kwargs: _execution())
    with pytest.raises(ValueError, match="claim_id must be a string"):
        guarded.execute_guarded_research(
            "test query",
            claim_id=123,  # type: ignore[arg-type]
            claim_evidence=[_evidence()],
        )
