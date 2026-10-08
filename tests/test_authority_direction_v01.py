from __future__ import annotations

from pathlib import Path

from gremlin_mcp.authority import authority_envelope, gremlin_system_authority
from gremlin_mcp.core import status
from gremlin_mcp.user_task_gateway import build_user_task_plan


LIVE_SURFACES = (
    Path("gremlin_mcp/core.py"),
    Path("gremlin_mcp/router.py"),
    Path("gremlin_mcp/pipeline.py"),
    Path("gremlin_mcp/workers.py"),
    Path("gremlin_mcp/web.py"),
    Path("gremlin_mcp/hive_authority.py"),
    Path("gremlin_mcp/user_task_gateway.py"),
    Path("gremlin_mcp/server.py"),
)


def test_gremlin_authority_direction_is_operator_gremlin_ai():
    state = gremlin_system_authority()
    assert state["authority_order"] == ["OPERATOR", "GREMLIN", "AI_CLIENT"]
    assert state["supervision_authority"] == "ACTIVE"
    assert state["internal_execution"] == "ACTIVE"
    assert state["internal_write"] == "ACTIVE"
    assert state["external_mutation_capability"] == "AVAILABLE"
    assert state["ai_self_authorization"] is False
    assert state["ai_override_gremlin"] is False
    assert state["mcp_self_grants_authority"] is False


def test_unadmitted_request_does_not_remove_gremlin_capability():
    envelope = authority_envelope()
    assert envelope["system"]["external_mutation_capability"] == "AVAILABLE"
    assert envelope["request"]["external_effect_admitted"] is False
    assert envelope["request"]["self_granted"] is False


def test_core_status_separates_system_authority_from_request_admission():
    authority = status()["authority"]
    assert authority["system"]["supervision_authority"] == "ACTIVE"
    assert authority["request"]["external_effect_admitted"] is False
    assert "production_runtime_write" not in authority
    assert "execution_admitted" not in authority
    assert "canon_allowed" not in authority


def test_mutation_intent_is_supervised_not_plan_only():
    out = build_user_task_plan(
        "Update the repository and commit the exact authorized patch.",
        surface_root="/definitely/missing/noema",
    )
    execution = out["execution"]
    assert execution["authority_mode"] == "GREMLIN_SUPERVISED_EXTERNAL_ADMISSION_REQUIRED"
    assert execution["authority"]["system"]["supervision_authority"] == "ACTIVE"
    assert execution["authority"]["request"]["external_effect_admitted"] is False


def test_live_mcp_surfaces_do_not_reintroduce_global_authority_denial():
    forbidden = (
        '"production_runtime_write": False',
        '"execution_admitted": False',
        "PLAN_ONLY_EXPLICIT_EXTERNAL_AUTHORIZATION_REQUIRED",
    )
    for path in LIVE_SURFACES:
        text = path.read_text("utf-8")
        for marker in forbidden:
            assert marker not in text, f"{path} reintroduced {marker}"
