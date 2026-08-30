from __future__ import annotations

import json
from pathlib import Path
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


def linux_paths(home: str = "/home/alice"):
    return resolve_paths(platform="linux", env={"HOME": home})


def windows_paths(home: str = r"C:\Users\Alice"):
    return resolve_paths(
        platform="windows",
        env={
            "USERPROFILE": home,
            "APPDATA": rf"{home}\AppData\Roaming",
            "LOCALAPPDATA": rf"{home}\AppData\Local",
            "ProgramData": r"C:\ProgramData",
        },
    )


def which_core(name: str) -> str | None:
    return {
        "codex": "/usr/bin/codex",
        "opencode": "/usr/bin/opencode",
        "claude": "/usr/bin/claude",
        "gemini": "/usr/bin/gemini",
        "code": "/usr/bin/code",
        "cursor": "/usr/bin/cursor",
        "windsurf": "/usr/bin/windsurf",
    }.get(name)


def test_linux_provider_matrix_excludes_windows_only_claude_desktop() -> None:
    runner = FakeRunner([
        cp(1, stderr="not found"),
        cp(0, stdout="No MCP servers configured"),
        cp(1, stderr="not found"),
        cp(0, stdout="No MCP servers configured"),
    ])
    payload = list_providers(
        linux_paths(), env={"HOME": "/home/alice"}, which=which_core, runner=runner,
    )
    providers = {item["provider_id"]: item for item in payload["providers"]}
    assert payload["platform"] == "linux"
    assert set(providers) == {"codex", "opencode", "claude-code", "gemini", "cursor", "vscode", "windsurf"}
    assert providers["codex"]["config_path"] == "/home/alice/.codex/config.toml"
    assert providers["opencode"]["config_path"] == "/home/alice/.config/opencode/opencode.json"
    assert providers["claude-code"]["config_path"] == "/home/alice/.claude.json"
    assert providers["gemini"]["config_path"] == "/home/alice/.gemini/settings.json"
    assert providers["cursor"]["config_path"] == "/home/alice/.cursor/mcp.json"
    assert providers["windsurf"]["config_path"] == "/home/alice/.codeium/windsurf/mcp_config.json"
    assert "claude-desktop" not in providers


def test_windows_provider_matrix_includes_claude_desktop() -> None:
    env = {
        "USERPROFILE": r"C:\Users\Alice",
        "APPDATA": r"C:\Users\Alice\AppData\Roaming",
        "LOCALAPPDATA": r"C:\Users\Alice\AppData\Local",
    }
    payload = list_providers(
        windows_paths(), env=env, which=lambda _name: None, runner=FakeRunner([]),
    )
    providers = {item["provider_id"]: item for item in payload["providers"]}
    assert payload["platform"] == "windows"
    assert "claude-desktop" in providers
    assert providers["claude-desktop"]["config_path"].replace("/", "\\").endswith(
        r"AppData\Roaming\Claude\claude_desktop_config.json"
    )


def test_codex_connect_uses_official_mcp_cli_and_gremlin_stdio() -> None:
    runner = FakeRunner([cp(0, stdout="Added global MCP server 'gremlin'.")])
    result = connect_provider(
        "codex", linux_paths(), env={"HOME": "/home/alice"}, which=which_core, runner=runner,
    )
    command = runner.commands[0]
    assert command[:4] == ["/usr/bin/codex", "mcp", "add", "gremlin"]
    assert "--env" in command
    assert "GREMLIN_LICENSE_PATH=/home/alice/.config/gremlin/license.json" in command
    assert command[-3:] == ["/usr/bin/gremlin-product-mcp", "--transport", "stdio"]
    assert result.status == "CONNECTED_CONFIGURED"


def test_claude_code_connect_is_user_scoped_stdio() -> None:
    runner = FakeRunner([cp(0, stdout="Added MCP server gremlin")])
    result = connect_provider(
        "claude-code", linux_paths(), env={"HOME": "/home/alice"}, which=which_core, runner=runner,
    )
    command = runner.commands[0]
    assert command[:7] == ["/usr/bin/claude", "mcp", "add", "--transport", "stdio", "--scope", "user"]
    assert "gremlin" in command
    assert command[-3:] == ["/usr/bin/gremlin-product-mcp", "--transport", "stdio"]
    assert result.status == "CONNECTED_CONFIGURED"


def test_gemini_connect_is_user_scoped_stdio() -> None:
    runner = FakeRunner([cp(0, stdout='MCP server "gremlin" added to user settings')])
    result = connect_provider(
        "gemini", linux_paths(), env={"HOME": "/home/alice"}, which=which_core, runner=runner,
    )
    command = runner.commands[0]
    assert command[:7] == ["/usr/bin/gemini", "mcp", "add", "--scope", "user", "--transport", "stdio"]
    assert "gremlin" in command
    assert result.status == "CONNECTED_CONFIGURED"


def test_vscode_connect_uses_add_mcp_cli() -> None:
    runner = FakeRunner([cp(0)])
    result = connect_provider(
        "vscode", linux_paths(), env={"HOME": "/home/alice"}, which=which_core, runner=runner,
    )
    command = runner.commands[0]
    assert command[:2] == ["/usr/bin/code", "--add-mcp"]
    payload = json.loads(command[2])
    assert payload["name"] == "gremlin"
    assert payload["command"] == "/usr/bin/gremlin-product-mcp"
    assert payload["args"] == ["--transport", "stdio"]
    assert result.status == "REGISTERED_RESTART_REQUIRED"


def test_cursor_json_connect_test_disconnect_roundtrip(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    paths = resolve_paths(
        platform="linux",
        env={
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_STATE_HOME": str(home / ".local/state"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "XDG_DATA_HOME": str(home / ".local/share"),
        },
    )
    config = home / ".cursor" / "mcp.json"
    config.parent.mkdir(parents=True)
    config.write_text('{"mcpServers":{"existing":{"command":"example"}}}', encoding="utf-8")

    result = connect_provider("cursor", paths, env={"HOME": str(home)}, which=lambda _name: None, runner=FakeRunner([]))
    assert result.status == "CONNECTED_CONFIGURED"
    payload = json.loads(config.read_text(encoding="utf-8"))
    assert "existing" in payload["mcpServers"]
    assert payload["mcpServers"]["gremlin"]["command"] == "/usr/bin/gremlin-product-mcp"
    assert run_provider_test("cursor", paths, env={"HOME": str(home)}, which=lambda _name: None, runner=FakeRunner([])).status == "PASS"
    assert disconnect_provider("cursor", paths, env={"HOME": str(home)}, which=lambda _name: None, runner=FakeRunner([])).status == "DISCONNECTED"
    payload = json.loads(config.read_text(encoding="utf-8"))
    assert "existing" in payload["mcpServers"]
    assert "gremlin" not in payload["mcpServers"]


def test_opencode_disconnect_fails_closed_instead_of_rewriting_jsonc() -> None:
    runner = FakeRunner([])
    result = disconnect_provider(
        "opencode", linux_paths(), env={"HOME": "/home/alice"}, which=which_core, runner=runner,
    )
    assert result.status == "MANUAL_REMOVE_REQUIRED"
    assert runner.commands == []


def test_codex_test_verifies_stdio_transport() -> None:
    payload = {"name": "gremlin", "enabled": True, "transport": {"type": "stdio", "command": "/usr/bin/gremlin-product-mcp"}}
    runner = FakeRunner([cp(0, stdout=json.dumps(payload))])
    result = run_provider_test(
        "codex", linux_paths(), env={"HOME": "/home/alice"}, which=which_core, runner=runner,
    )
    assert result.status == "PASS"


def test_opencode_test_distinguishes_registered_from_live() -> None:
    runner = FakeRunner([cp(0, stdout="gremlin failed /usr/bin/gremlin-product-mcp")])
    result = run_provider_test(
        "opencode", linux_paths(), env={"HOME": "/home/alice"}, which=which_core, runner=runner,
    )
    assert result.status == "REGISTERED_RUNTIME_NOT_READY"
