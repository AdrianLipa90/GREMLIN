from __future__ import annotations

import pytest

import gremlin_mcp.semantic_kind_bridge as bridge


def test_assignments_container_rejects_mapping_string_and_nonobject_rows_before_lower_bridge(monkeypatch) -> None:
    called = False

    def fake_lower(*args, **kwargs):
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(bridge, "apply_semantic_producer_output_with_quorum", fake_lower)
    for value in ({"source_id": "a"}, "not-assignments", [{"source_id": "a"}, "bad-row"]):
        called = False
        with pytest.raises(ValueError, match="evidence_kind_assignments"):
            bridge.apply_semantic_producer_output_with_kind_policy(
                {},
                producer_output={},
                evidence_kind_assignments=value,  # type: ignore[arg-type]
                claim_mode="EMPIRICAL",
            )
        assert called is False


def test_direct_family_minimum_rejects_bool_float_and_string_before_lower_bridge(monkeypatch) -> None:
    called = False

    def fake_lower(*args, **kwargs):
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(bridge, "apply_semantic_producer_output_with_quorum", fake_lower)
    for value in (True, 1.0, "1"):
        called = False
        with pytest.raises(ValueError, match="min_direct_families must be an integer"):
            bridge.apply_semantic_producer_output_with_kind_policy(
                {},
                producer_output={},
                evidence_kind_assignments=[],
                claim_mode="EMPIRICAL",
                min_direct_families=value,  # type: ignore[arg-type]
            )
        assert called is False


def test_claim_mode_rejects_non_string_before_lower_bridge(monkeypatch) -> None:
    called = False

    def fake_lower(*args, **kwargs):
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(bridge, "apply_semantic_producer_output_with_quorum", fake_lower)
    with pytest.raises(ValueError, match="claim mode must be a string or None"):
        bridge.apply_semantic_producer_output_with_kind_policy(
            {},
            producer_output={},
            evidence_kind_assignments=[],
            claim_mode=7,  # type: ignore[arg-type]
        )
    assert called is False


def test_execution_and_producer_output_must_be_objects() -> None:
    with pytest.raises(ValueError, match="execution must be an object"):
        bridge.apply_semantic_producer_output_with_kind_policy(
            [],  # type: ignore[arg-type]
            producer_output={},
            evidence_kind_assignments=[],
            claim_mode="EMPIRICAL",
        )
    with pytest.raises(ValueError, match="producer_output must be an object"):
        bridge.apply_semantic_producer_output_with_kind_policy(
            {},
            producer_output=[],  # type: ignore[arg-type]
            evidence_kind_assignments=[],
            claim_mode="EMPIRICAL",
        )
