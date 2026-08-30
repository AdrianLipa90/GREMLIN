from __future__ import annotations

import json
import subprocess

from gremlin_mcp.install.paths import resolve_paths
from gremlin_mcp.install.provider_integrations import (
    connect_provider,
    disconnect_provider,
    list_providers,
    test_provider as run_provider_test,
)


class FakeRunner:
    def __init__(self, replies: list[subprocess.CompletedProcess[str]]) -> None:
        self.replies = list(replies)
        self.commands: list[list[str]] = []

    def __call__(self, command, **_kwargs):
        self.commands.append(list(command))
        if not self.replies:
            raise AssertionError("unexpected provider command")
        return self.replies.pop(0)


def cp(code: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], code, stdout=stdout, stderr=stderr)


def linux_paths():
    return resolve_paths(platform="linux", env={"HOME": "/home/alice"})


def which_all(name: str) -> str | None:
    return {"codex": "/usr/bin/codex", "opencode": "/usr/bin/opencode"}.get(name)


def test_provider_discovery_surfaces_codex_and_opencode() -> None:
    runner = FakeRunner([
        cp(1, stderr="not found"),
        cp(0, stdout="No MCP servers configured"),
    ])
    payload = list_providers(
        linux_paths(),
        env={"HOME": "/home/alice"},
        which=which_all,
        runner=runner,
    )
    providers = {item["provider_id"]: item for item in payload["providers"]}
    assert providers["codex"]["detected"] is True
    assert providers["codex"]["config_path"] == "/home/alice/.codex/config.toml"
    assert providers["opencode"]["detected"] is True
    assert providers["opencode"]["config_path"] == "/home/alice/.config/opencode/opencode.json"


def test_codex_connect_uses_official_mcp_cli_and_gremlin_stdio() -> None:
    runner = FakeRunner([cp(0, stdout="Added global MCP server 'gremlin'.")])
    result = connect_provider(
        "codex",
        linux_paths(),
        env={"HOME": "/home/alice"},
        which=which_all,
        runner=runner,
    )
    command = runner.commands[0]
    assert command[:4] == ["/usr/bin/codex", "mcp", "add", "gremlin"]
    assert "--env" in command
    assert "GREMLIN_LICENSE_PATH=/home/alice/.config/gremlin/license.json" in command
    assert command[-3:] == ["/usr/bin/gremlin-product-mcp", "--transport", "stdio"]
    assert result.status == "CONNECTED_CONFIGURED"


def test_opencode_connect_uses_noninteractive_mcp_cli() -> None:
    runner = FakeRunner([cp(0, stdout='MCP server "gremlin" added')])
    result = connect_provider(
        "opencode",
        linux_paths(),
        env={"HOME": "/home/alice"},
        which=which_all,
        runner=runner,
    )
    command = runner.commands[0]
    assert command[:4] == ["/usr/bin/opencode", "mcp", "add", "gremlin"]
    assert command[-3:] == ["/usr/bin/gremlin-product-mcp", "--transport", "stdio"]
    assert result.status == "CONNECTED_CONFIGURED"


def test_opencode_disconnect_fails_closed_instead_of_rewriting_jsonc() -> None:
    runner = FakeRunner([])
    result = disconnect_provider(
        "opencode",
        linux_paths(),
        env={"HOME": "/home/alice"},
        which=which_all,
        runner=runner,
    )
    assert result.status == "MANUAL_REMOVE_REQUIRED"
    assert runner.commands == []


def test_codex_test_verifies_stdio_transport() -> None:
    payload = {"name": "gremlin", "enabled": True, "transport": {"type": "stdio", "command": "/usr/bin/gremlin-product-mcp"}}
    runner = FakeRunner([cp(0, stdout=json.dumps(payload))])
    result = run_provider_test(
        "codex",
        linux_paths(),
        env={"HOME": "/home/alice"},
        which=which_all,
        runner=runner,
    )
    assert result.status == "PASS"


def test_opencode_test_distinguishes_registered_from_live() -> None:
    runner = FakeRunner([cp(0, stdout="gremlin failed /usr/bin/gremlin-product-mcp")])
    result = run_provider_test(
        "opencode",
        linux_paths(),
        env={"HOME": "/home/alice"},
        which=which_all,
        runner=runner,
    )
    assert result.status == "REGISTERED_RUNTIME_NOT_READY"
