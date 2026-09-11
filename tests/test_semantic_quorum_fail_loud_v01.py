from __future__ import annotations

import pytest

import gremlin_mcp.semantic_quorum_bridge as bridge


def _base_with_synthesis(*, semantic_evidence):
    return {
        "status": "CANDIDATE_SYNTHESIS_READY",
        "synthesis": {"candidate": "ok"},
        "semantic_evidence": semantic_evidence,
        "authority": {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False},
    }


def test_minimum_rejects_bool_float_and_string_before_base_execution(monkeypatch) -> None:
    called = False

    def fake_apply(*args, **kwargs):
        nonlocal called
        called = True
        return _base_with_synthesis(semantic_evidence={})

    monkeypatch.setattr(bridge, "apply_semantic_producer_output", fake_apply)
    for value in (True, 2.0, "2"):
        called = False
        with pytest.raises(ValueError, match="min_unipolar_families must be an integer"):
            bridge.apply_semantic_producer_output_with_quorum(
                {},
                producer_output={},
                min_unipolar_families=value,  # type: ignore[arg-type]
            )
        assert called is False


def test_missing_semantic_evidence_cannot_bypass_quorum_when_synthesis_exists(monkeypatch) -> None:
    monkeypatch.setattr(
        bridge,
        "apply_semantic_producer_output",
        lambda *args, **kwargs: {
            "status": "CANDIDATE_SYNTHESIS_READY",
            "synthesis": {"candidate": "ok"},
            "authority": {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False},
        },
    )
    result = bridge.apply_semantic_producer_output_with_quorum({}, producer_output={})
    assert result["status"] == bridge.SEMANTIC_FAMILY_QUORUM_BINDING_INVALID
    assert result["synthesis"] is None
    assert result["quarantined_synthesis"] is not None
    assert result["semantic_evidence"]["synthesis_authorized"] is False


def test_missing_provenance_family_binding_cannot_bypass_quorum(monkeypatch) -> None:
    monkeypatch.setattr(
        bridge,
        "apply_semantic_producer_output",
        lambda *args, **kwargs: _base_with_synthesis(semantic_evidence={"validation": {"valid": True}}),
    )
    result = bridge.apply_semantic_producer_output_with_quorum({}, producer_output={})
    assert result["status"] == bridge.SEMANTIC_FAMILY_QUORUM_BINDING_INVALID
    assert result["synthesis"] is None
    assert "PROVENANCE_FAMILY_BINDING_REQUIRED" in result["semantic_evidence"]["quarantine_reason"]


def test_missing_family_bound_guard_evidence_cannot_bypass_quorum(monkeypatch) -> None:
    monkeypatch.setattr(
        bridge,
        "apply_semantic_producer_output",
        lambda *args, **kwargs: _base_with_synthesis(
            semantic_evidence={"provenance_families": {"status": "VALID"}}
        ),
    )
    result = bridge.apply_semantic_producer_output_with_quorum({}, producer_output={})
    assert result["status"] == bridge.SEMANTIC_FAMILY_QUORUM_BINDING_INVALID
    assert result["synthesis"] is None
    assert "FAMILY_BOUND_GUARD_EVIDENCE_REQUIRED" in result["semantic_evidence"]["quarantine_reason"]


def test_earlier_fail_closed_result_is_preserved_without_reauthorizing_synthesis(monkeypatch) -> None:
    earlier = {
        "status": "SEMANTIC_PRODUCER_OUTPUT_INVALID",
        "synthesis": None,
        "semantic_evidence": {},
        "authority": {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False},
    }
    monkeypatch.setattr(bridge, "apply_semantic_producer_output", lambda *args, **kwargs: earlier)
    result = bridge.apply_semantic_producer_output_with_quorum({}, producer_output={})
    assert result["status"] == "SEMANTIC_PRODUCER_OUTPUT_INVALID"
    assert result["synthesis"] is None
