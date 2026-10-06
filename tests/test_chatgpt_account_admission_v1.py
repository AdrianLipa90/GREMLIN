from __future__ import annotations

from gremlin_mcp import chatgpt_account_admission as clean


def test_blank_clean_account_is_blocked_at_surface_and_has_no_hidden_state_dependencies():
    plan = clean.build_plan(env={}, which=lambda _: None)
    assert plan.status == "BLOCKED:SURFACE"
    assert plan.assumptions == {
        "requires_prior_chat_history": False,
        "requires_chatgpt_memory": False,
        "requires_noema_library": False,
        "requires_existing_gremlin_account_state": False,
        "requires_successful_tool_scan_for_ready": True,
    }


def test_remote_https_path_reaches_ready_only_after_registration_scan_and_capability():
    env = {
        "GREMLIN_CHATGPT_SURFACE": "web",
        "GREMLIN_CHATGPT_DEVELOPER_MODE": "true",
        "GREMLIN_CHATGPT_REMOTE_MCP_URL": "https://gremlin.example/mcp",
        "GREMLIN_CHATGPT_APP_CREATED": "true",
        "GREMLIN_CHATGPT_TOOL_SCAN_STATUS": "PASS",
        "GREMLIN_CHATGPT_CAPABILITY_MODE": "full",
    }
    plan = clean.build_plan(env=env, which=lambda _: None)
    assert plan.status == "READY"
    assert plan.transport == "remote"
    assert all(g.status == "PASS" for g in plan.gates)


def test_ready_is_impossible_before_tool_scan_passes():
    env = {
        "GREMLIN_CHATGPT_SURFACE": "web",
        "GREMLIN_CHATGPT_DEVELOPER_MODE": "true",
        "GREMLIN_CHATGPT_REMOTE_MCP_URL": "https://gremlin.example/mcp",
        "GREMLIN_CHATGPT_APP_CREATED": "true",
        "GREMLIN_CHATGPT_CAPABILITY_MODE": "read",
    }
    plan = clean.build_plan(env=env, which=lambda _: None)
    assert plan.status == "BLOCKED:TOOL_SCAN"
    assert "Scan Tools" in plan.next_action


def test_remote_transport_rejects_localhost_http_and_private_ips():
    for url in (
        "http://gremlin.example/mcp",
        "https://localhost:8766/mcp",
        "https://127.0.0.1:8766/mcp",
        "https://192.168.1.5/mcp",
    ):
        ok, _ = clean.validate_remote_mcp_url(url)
        assert ok is False


def test_remote_transport_requires_mcp_path():
    ok, detail = clean.validate_remote_mcp_url("https://gremlin.example/api")
    assert ok is False
    assert "/mcp" in detail


def test_secure_tunnel_path_can_satisfy_transport_without_public_remote_url():
    env = {
        "GREMLIN_CHATGPT_SURFACE": "web",
        "GREMLIN_CHATGPT_DEVELOPER_MODE": "true",
        "GREMLIN_OPENAI_TUNNEL_ID": "tunnel_0123456789abcdef",
        "CONTROL_PLANE_API_KEY": "sk-secret-never-render",
        "GREMLIN_CHATGPT_APP_CREATED": "true",
        "GREMLIN_CHATGPT_TOOL_SCAN_STATUS": "PASS",
        "GREMLIN_CHATGPT_CAPABILITY_MODE": "read",
    }
    plan = clean.build_plan(
        env=env,
        transport="secure-tunnel",
        which=lambda name: "/opt/tunnel-client" if name == "tunnel-client" else None,
    )
    assert plan.status == "READY"
    assert plan.transport == "secure-tunnel"
    assert "sk-secret-never-render" not in str(plan.as_dict())


def test_mobile_surface_fails_closed_even_if_other_gates_are_green():
    env = {
        "GREMLIN_CHATGPT_SURFACE": "mobile",
        "GREMLIN_CHATGPT_DEVELOPER_MODE": "true",
        "GREMLIN_CHATGPT_REMOTE_MCP_URL": "https://gremlin.example/mcp",
        "GREMLIN_CHATGPT_APP_CREATED": "true",
        "GREMLIN_CHATGPT_TOOL_SCAN_STATUS": "PASS",
        "GREMLIN_CHATGPT_CAPABILITY_MODE": "read",
    }
    plan = clean.build_plan(env=env, which=lambda _: None)
    assert plan.status == "BLOCKED:SURFACE"


def test_capability_is_never_inferred_from_prior_account():
    env = {
        "GREMLIN_CHATGPT_SURFACE": "web",
        "GREMLIN_CHATGPT_DEVELOPER_MODE": "true",
        "GREMLIN_CHATGPT_REMOTE_MCP_URL": "https://gremlin.example/mcp",
        "GREMLIN_CHATGPT_APP_CREATED": "true",
        "GREMLIN_CHATGPT_TOOL_SCAN_STATUS": "PASS",
    }
    plan = clean.build_plan(env=env, which=lambda _: None)
    assert plan.status == "BLOCKED:CAPABILITY_MODE"
    assert plan.capability_mode == "unknown"
