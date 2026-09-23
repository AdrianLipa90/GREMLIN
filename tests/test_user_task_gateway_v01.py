from __future__ import annotations

import pytest

from gremlin_mcp.user_task_gateway import build_user_task_plan


def test_gateway_is_deterministic_without_live_surface() -> None:
    kwargs = dict(
        task="Analyse the dependency graph and audit contradictions.",
        context=["alpha causes beta. beta depends on gamma."],
        request_id="req-001",
        surface_root="/definitely/missing/noema",
    )
    a = build_user_task_plan(**kwargs)
    b = build_user_task_plan(**kwargs)
    assert a == b
    assert len(a["plan_sha256"]) == 64
    assert len(a["phasenav"]["phase36"]) == 36


def test_validation_policy_adds_hound_and_mantis() -> None:
    out = build_user_task_plan(
        "Run tests, benchmark the router and audit failures.",
        surface_root="/definitely/missing/noema",
    )
    final = out["octopus"]["final_species_membership"]
    assert "HOUND" in final
    assert "MANTIS" in final


def test_phasenav_reorders_but_never_changes_membership() -> None:
    out = build_user_task_plan(
        "Compare graph dependencies, contradictions and proof provenance.",
        surface_root="/definitely/missing/noema",
    )
    admitted = set(out["octopus"]["final_species_membership"])
    scheduled = set(out["phasenav"]["schedule_order"])
    assert scheduled == admitted
    assert out["phasenav"]["may_change_species_membership"] is False


def test_mutation_task_requires_external_authorization() -> None:
    out = build_user_task_plan(
        "Update the repository, commit the change and merge the branch.",
        surface_root="/definitely/missing/noema",
    )
    execution = out["execution"]
    assert execution["external_effects_authorized"] is False
    assert execution["requires_explicit_external_authorization"] is True
    assert execution["authority"] == "PLAN_ONLY_EXPLICIT_EXTERNAL_AUTHORIZATION_REQUIRED"
    assert "GITHUB" in execution["host_tool_hints"]


def test_context_is_compiled_and_raw_context_not_duplicated_into_worker_payload() -> None:
    context = ["alpha causes beta. beta supports gamma."]
    out = build_user_task_plan(
        "Inspect alpha and beta.",
        context=context,
        surface_root="/definitely/missing/noema",
    )
    payload = out["worker_payload"]
    assert len(payload["context_sha256"]) == 1
    assert context[0] not in repr(payload)
    assert payload["semantic_graph"]["active_nodes"] > 0


def test_bounds_fail_closed() -> None:
    with pytest.raises(ValueError):
        build_user_task_plan("", surface_root="/definitely/missing/noema")
    with pytest.raises(ValueError):
        build_user_task_plan("x", context=["x"] * 33, surface_root="/definitely/missing/noema")
    with pytest.raises(ValueError):
        build_user_task_plan("x", max_species=0, surface_root="/definitely/missing/noema")
