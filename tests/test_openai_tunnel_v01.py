from __future__ import annotations

import subprocess

from gremlin_mcp import openai_tunnel as tunnel


def test_blocked_without_identity_and_credentials():
    plan = tunnel.build_plan(
        env={}, which=lambda _: None,
        mcp_command="python -m gremlin_mcp.server_with_hive --transport stdio",
    )
    assert plan.ready is False
    assert [g.status for g in plan.gates[:3]] == ["FAIL", "FAIL", "FAIL"]


def test_ready_plan_never_exposes_runtime_key():
    env = {
        "HOME": "/tmp/tester",
        "GREMLIN_OPENAI_TUNNEL_ID": "tunnel_0123456789abcdef",
        "CONTROL_PLANE_API_KEY": "sk-super-secret",
    }
    plan = tunnel.build_plan(
        env=env, which=lambda _: "/usr/bin/tunnel-client",
        mcp_command="gremlin-mcp --transport stdio",
    )
    assert plan.ready is True
    rendered = str(plan.as_dict())
    assert "sk-super-secret" not in rendered
    assert plan.state_paths["GREMLIN_MCP_STATE_PATH"].endswith("worker.sqlite3")
    assert plan.state_paths["GREMLIN_HIVE_STATE_PATH"].endswith("hive.sqlite3")


def test_commands_are_exact_and_shell_free():
    env = {
        "GREMLIN_OPENAI_TUNNEL_ID": "tunnel_0123456789abcdef",
        "CONTROL_PLANE_API_KEY": "key",
    }
    plan = tunnel.build_plan(
        env=env, which=lambda _: "/opt/tunnel-client",
        mcp_command="python -m gremlin_mcp.server_with_hive --transport stdio",
    )
    assert tunnel.init_command(plan) == [
        "/opt/tunnel-client", "init", "--sample", "sample_mcp_stdio_local",
        "--profile", "gremlin-chatgpt", "--tunnel-id", "tunnel_0123456789abcdef",
        "--mcp-command", "python -m gremlin_mcp.server_with_hive --transport stdio",
    ]
    assert tunnel.doctor_command(plan) == [
        "/opt/tunnel-client", "doctor", "--profile", "gremlin-chatgpt", "--explain"
    ]
    assert tunnel.run_command(plan) == [
        "/opt/tunnel-client", "run", "--profile", "gremlin-chatgpt"
    ]


def test_setup_fail_loud_on_doctor_failure():
    env = {
        "GREMLIN_OPENAI_TUNNEL_ID": "tunnel_0123456789abcdef",
        "CONTROL_PLANE_API_KEY": "key",
    }
    plan = tunnel.build_plan(
        env=env, which=lambda _: "/opt/tunnel-client",
        mcp_command="gremlin-mcp --transport stdio",
    )
    replies = iter([
        subprocess.CompletedProcess([], 0, "init ok", ""),
        subprocess.CompletedProcess([], 3, "", "doctor failed"),
    ])

    def runner(*args, **kwargs):
        return next(replies)

    result = tunnel.setup_and_doctor(plan, env=env, runner=runner)
    assert result["status"] == "FAIL"
    assert result["steps"][-1]["name"] == "doctor"
    assert result["steps"][-1]["returncode"] == 3


def test_setup_ready_only_after_init_and_doctor_pass():
    env = {
        "GREMLIN_OPENAI_TUNNEL_ID": "tunnel_0123456789abcdef",
        "CONTROL_PLANE_API_KEY": "key",
    }
    plan = tunnel.build_plan(
        env=env, which=lambda _: "/opt/tunnel-client",
        mcp_command="gremlin-mcp --transport stdio",
    )
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "ok", "")

    result = tunnel.setup_and_doctor(plan, env=env, runner=runner)
    assert result["status"] == "READY"
    assert len(calls) == 2
    assert calls[0][1] == "init"
    assert calls[1][1] == "doctor"
