from gremlin_mcp import chatgpt_install_preflight as preflight


def test_blocked_when_both_routes_are_missing():
    result = preflight.build_preflight(
        endpoint=None,
        env={},
        which=lambda _: None,
    )
    assert result.status == "BLOCKED"
    assert result.selected_route is None
    assert result.routes[0].blocker == "REMOTE_ENDPOINT_REQUIRED"
    assert result.routes[1].status == "BLOCKED"
    assert result.host_gate["status"] == "EXTERNAL_REQUIRED"


def test_remote_route_wins_when_public_endpoint_is_ready():
    result = preflight.build_preflight(
        endpoint="https://gremlin.example/mcp",
        env={},
        which=lambda _: None,
    )
    assert result.status == "PACKAGE_READY"
    assert result.selected_route == "REMOTE_HTTPS_MCP"
    assert result.routes[0].status == "PACKAGE_READY"


def test_tunnel_route_selected_when_prerequisites_exist():
    env = {
        "HOME": "/tmp/tester",
        "GREMLIN_OPENAI_TUNNEL_ID": "tunnel_0123456789abcdef",
        "CONTROL_PLANE_API_KEY": "sk-not-emitted",
    }
    result = preflight.build_preflight(
        endpoint=None,
        env=env,
        which=lambda name: "/opt/tunnel-client" if name == "tunnel-client" else None,
    )
    assert result.status == "TUNNEL_PREREQUISITES_READY"
    assert result.selected_route == "SECURE_MCP_TUNNEL"
    rendered = str(result.as_dict())
    assert "sk-not-emitted" not in rendered


def test_remote_route_has_precedence_if_both_are_available():
    env = {
        "GREMLIN_OPENAI_TUNNEL_ID": "tunnel_0123456789abcdef",
        "CONTROL_PLANE_API_KEY": "key",
    }
    result = preflight.build_preflight(
        endpoint="https://gremlin.example/mcp",
        env=env,
        which=lambda _: "/opt/tunnel-client",
    )
    assert result.status == "PACKAGE_READY"
    assert result.selected_route == "REMOTE_HTTPS_MCP"
