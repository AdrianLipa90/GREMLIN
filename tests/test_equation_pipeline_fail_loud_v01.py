from __future__ import annotations

import pytest

import gremlin_mcp.equation_pipeline as pipeline


def test_pipeline_rejects_non_string_boundary_fields() -> None:
    with pytest.raises(ValueError, match="text must be a string"):
        pipeline.audit_equation_transcript(123, source_id="src", classification="SYNTHETIC")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="source_id must be a string"):
        pipeline.audit_equation_transcript("Eq. (1): x = 1", source_id=123, classification="SYNTHETIC")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="classification must be a string"):
        pipeline.audit_equation_transcript("Eq. (1): x = 1", source_id="src", classification=True)  # type: ignore[arg-type]


def test_pipeline_rejects_non_mapping_extractor_result(monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "propose_equation_witnesses", lambda *args, **kwargs: "bad")
    with pytest.raises(RuntimeError, match="extractor returned a non-object"):
        pipeline.audit_equation_transcript("Eq. (1): x = 1", source_id="src", classification="SYNTHETIC")


def test_pipeline_rejects_unknown_extractor_status(monkeypatch) -> None:
    monkeypatch.setattr(
        pipeline,
        "propose_equation_witnesses",
        lambda *args, **kwargs: {"status": "MAGIC", "witness_proposals": [], "unresolved_proposals": []},
    )
    with pytest.raises(RuntimeError, match="unsupported status"):
        pipeline.audit_equation_transcript("Eq. (1): x = 1", source_id="src", classification="SYNTHETIC")


def test_no_text_state_cannot_hide_proposals(monkeypatch) -> None:
    monkeypatch.setattr(
        pipeline,
        "propose_equation_witnesses",
        lambda *args, **kwargs: {
            "status": "NO_TEXT_FAIL_CLOSED",
            "witness_proposals": [{"id": "hidden"}],
            "unresolved_proposals": [],
        },
    )
    with pytest.raises(RuntimeError, match="must not contain proposals"):
        pipeline.audit_equation_transcript("", source_id="src", classification="SYNTHETIC")


def _extraction_with_one_proposal():
    return {
        "status": "CANDIDATE_PROPOSALS_READY",
        "witness_proposals": [
            {
                "id": "W-1",
                "kind": "numeric",
                "expression": "1+1",
                "symbols": {},
                "reported_value": 2.0,
            }
        ],
        "unresolved_proposals": [],
    }


def test_pipeline_does_not_int_coerce_downstream_counts(monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "propose_equation_witnesses", lambda *args, **kwargs: _extraction_with_one_proposal())
    monkeypatch.setattr(
        pipeline,
        "run_equation_witness_bundle",
        lambda *args, **kwargs: {
            "status": "AUDIT_COMPLETE",
            "witness_count": 1,
            "pass_count": "1",
            "fail_count": 0,
            "unresolved_count": 0,
            "detected_issue_ids": [],
            "unresolved_issue_ids": [],
        },
    )
    with pytest.raises(RuntimeError, match="pass_count must be a non-negative integer"):
        pipeline.audit_equation_transcript("Eq. (1): x = 1", source_id="src", classification="SYNTHETIC")


def test_pipeline_rejects_inconsistent_audit_count_topology(monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "propose_equation_witnesses", lambda *args, **kwargs: _extraction_with_one_proposal())
    monkeypatch.setattr(
        pipeline,
        "run_equation_witness_bundle",
        lambda *args, **kwargs: {
            "status": "AUDIT_COMPLETE",
            "witness_count": 1,
            "pass_count": 1,
            "fail_count": 1,
            "unresolved_count": 0,
            "detected_issue_ids": ["W-1"],
            "unresolved_issue_ids": [],
        },
    )
    with pytest.raises(RuntimeError, match="outcome counts do not sum"):
        pipeline.audit_equation_transcript("Eq. (1): x = 1", source_id="src", classification="SYNTHETIC")


def test_pipeline_rejects_non_string_issue_ids(monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "propose_equation_witnesses", lambda *args, **kwargs: _extraction_with_one_proposal())
    monkeypatch.setattr(
        pipeline,
        "run_equation_witness_bundle",
        lambda *args, **kwargs: {
            "status": "AUDIT_COMPLETE",
            "witness_count": 1,
            "pass_count": 0,
            "fail_count": 1,
            "unresolved_count": 0,
            "detected_issue_ids": [123],
            "unresolved_issue_ids": [],
        },
    )
    with pytest.raises(RuntimeError, match="detected_issue_ids must contain only non-empty strings"):
        pipeline.audit_equation_transcript("Eq. (1): x = 1", source_id="src", classification="SYNTHETIC")
