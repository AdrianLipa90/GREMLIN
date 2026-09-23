from __future__ import annotations

from gremlin_mcp.user_task_admission import build_user_turn_admission


def test_admission_continuation_uses_current_task() -> None:
    out = build_user_turn_admission(
        "Kontynuuj",
        current_task="Audit graph dependencies and benchmark contradictions.",
        active_path="GREMLIN_USER_TASK_GATEWAY_V0_1",
        surface_root="/definitely/missing/noema",
    )
    assert out["status"] == "READY"
    assert out["context_routing"]["mode"] == "CONTINUATION_CONTEXT"
    assert out["route_species"]
    assert set(out["route_species"]) & {"SPIDER", "HOUND"}


def test_admission_explicit_new_task_does_not_inherit_old_route() -> None:
    out = build_user_turn_admission(
        "What is twelve times seventeen?",
        current_task="Audit graph dependencies and benchmark contradictions.",
        active_path="GREMLIN_USER_TASK_GATEWAY_V0_1",
        surface_root="/definitely/missing/noema",
    )
    assert out["context_routing"]["mode"] == "TASK_ONLY"
    assert out["route_species"] == []
    assert out["plan"]["mode"] == "DIRECT"


def test_admission_is_deterministic() -> None:
    kwargs = dict(
        prompt="Kontynuuj",
        current_task="Audit graph dependencies and benchmark contradictions.",
        active_path="GREMLIN_USER_TASK_GATEWAY_V0_1",
        request_id="turn-001",
        surface_root="/definitely/missing/noema",
    )
    assert build_user_turn_admission(**kwargs) == build_user_turn_admission(**kwargs)


def test_admission_never_grants_external_or_canon_authority() -> None:
    out = build_user_turn_admission(
        "Merge the repository after testing.",
        current_task="Continue gateway integration.",
        surface_root="/definitely/missing/noema",
    )
    assert out["external_effects_authorized"] is False
    assert out["canon_allowed"] is False
    assert out["plan"]["execution"]["external_effects_authorized"] is False
