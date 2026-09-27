from __future__ import annotations

import pytest

from gremlin_mcp.phase_memory_runtime import empty_memory_state, update_memory_state
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


def test_max_species_seven_is_admitted() -> None:
    out = build_user_task_plan(
        "Audit graph dependencies, derive proof equations, inspect provenance, enumerate variants and prune duplicates.",
        max_species=7,
        surface_root="/definitely/missing/noema",
    )
    assert out["status"] == "READY"
    assert len(out["octopus"]["final_species_membership"]) <= 7


def test_router_metadata_does_not_force_spider_on_simple_task() -> None:
    out = build_user_task_plan(
        "What is twelve times seventeen?",
        surface_root="/definitely/missing/noema",
    )
    assert out["mode"] == "DIRECT"
    assert out["octopus"]["semantic_route"] == []
    assert out["execution"]["route_species"] == []


def test_continuation_prompt_uses_context_for_routing() -> None:
    out = build_user_task_plan(
        "Kontynuuj",
        context=["Audit graph dependencies, benchmark the router, and inspect contradictions."],
        surface_root="/definitely/missing/noema",
    )
    assert out["context_routing"]["mode"] == "CONTINUATION_CONTEXT"
    assert out["mode"] == "GREMLIN_ROUTED"
    assert set(out["octopus"]["final_species_membership"]) & {"SPIDER", "HOUND"}


def test_explicit_new_task_is_not_contaminated_by_stale_context() -> None:
    out = build_user_task_plan(
        "What is twelve times seventeen?",
        context=["Audit graph dependencies, benchmark the router, and inspect contradictions."],
        surface_root="/definitely/missing/noema",
    )
    assert out["context_routing"]["mode"] == "TASK_ONLY"
    assert out["octopus"]["semantic_route"] == []
    assert out["execution"]["route_species"] == []
    assert out["mode"] == "DIRECT"


def test_memory_ontology_algebra_is_bound_to_default_gateway() -> None:
    out = build_user_task_plan(
        "Inspect the graph and preserve memory provenance.",
        request_id="req-memory-ontology",
        surface_root="/definitely/missing/noema",
    )
    mo = out["memory_ontology"]
    assert mo["authority"] == "CANDIDATE_ONLY"
    assert mo["canon_allowed"] is False
    assert mo["historical_signature"]["steps"] == []
    assert mo["behavioral_signature"]["reduced_path"] == []
    assert mo["certified_behavioral_core"]["morphism_ids"] == []
    assert len(mo["source_contract_sha256"]) == 64
    assert out["claims"]["memory_ontology_algebra_bound"] is True
    assert (
        out["worker_payload"]["memory_ontology"]["source_contract_sha256"]
        == mo["source_contract_sha256"]
    )


def test_phase_memory_bias_reorders_without_changing_octopus_membership(monkeypatch) -> None:
    baseline = build_user_task_plan(
        "Compare graph dependencies and audit contradictions.",
        surface_root="/definitely/missing/noema",
    )
    members = list(baseline["octopus"]["final_species_membership"])
    assert len(members) >= 2
    source, target = members[0], members[-1]

    def equal_phase_order(_phase36, species):
        names = list(species)
        return names, {name: 0.5 for name in names}

    monkeypatch.setattr(
        "gremlin_mcp.user_task_gateway._phase_schedule_order",
        equal_phase_order,
    )

    state = empty_memory_state()
    for _ in range(4):
        state = update_memory_state(state, (target, source))

    out = build_user_task_plan(
        "Compare graph dependencies and audit contradictions.",
        surface_root="/definitely/missing/noema",
        phase_memory_state=state,
    )
    assert set(out["phasenav"]["schedule_order"]) == set(members)
    assert set(out["octopus"]["final_species_membership"]) == set(members)
    assert out["phasenav"]["schedule_order"][0] == target
    assert out["phasenav"]["phase_memory"]["applied"] is True
    assert out["phasenav"]["phase_memory"]["membership_changed"] is False
    assert out["claims"]["phase_memory_changes_membership"] is False


def test_phase_memory_membership_firewall_fails_closed(monkeypatch) -> None:
    baseline = build_user_task_plan(
        "Compare graph dependencies and audit contradictions.",
        surface_root="/definitely/missing/noema",
    )
    members = list(baseline["octopus"]["final_species_membership"])
    assert members

    def malicious_memory_order(species, base_scores, state, **_kwargs):
        ordered = list(species) + ["FERRET"]
        scores = dict(base_scores)
        scores["FERRET"] = 1.0
        return ordered, scores

    monkeypatch.setattr(
        "gremlin_mcp.user_task_gateway.memory_order",
        malicious_memory_order,
    )
    state = update_memory_state(empty_memory_state(), (members[0],))
    with pytest.raises(
        ValueError,
        match="phase memory may reorder OCTOPUS membership but cannot change it",
    ):
        build_user_task_plan(
            "Compare graph dependencies and audit contradictions.",
            surface_root="/definitely/missing/noema",
            phase_memory_state=state,
        )
