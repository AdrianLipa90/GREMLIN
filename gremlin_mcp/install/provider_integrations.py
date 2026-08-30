from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import ntpath
import os
from pathlib import Path
import shutil
import subprocess
from typing import Callable, Mapping, Sequence

from .integrations import (
    gremlin_stdio_entry,
    inspect_json_mcp,
    install_json_mcp,
    remove_json_mcp,
)
from .paths import GremlinPaths


PROVIDER_SCHEMA = "GREMLIN_MCP_PROVIDER_STATUS_V0_2"
PROVIDER_ACTION_SCHEMA = "GREMLIN_MCP_PROVIDER_ACTION_V0_2"
SERVER_NAME = "gremlin"


@dataclass(frozen=True)
class ProviderStatus:
    provider_id: str
    display_name: str
    detected: bool
    executable: str | None
    config_path: str
    connected: bool
    connection_status: str
    integration_mode: str
    platform: str
    detail: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderAction:
    schema: str
    provider_id: str
    status: str
    executable: str | None
    config_path: str
    detail: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _home(env: Mapping[str, str]) -> str:
    home = str(env.get("USERPROFILE") or env.get("HOME") or "").strip()
    if not home:
        raise RuntimeError("USERPROFILE/HOME is required for MCP provider discovery")
    return home


def _codex_config(env: Mapping[str, str]) -> Path:
    codex_home = str(env.get("CODEX_HOME") or "").strip()
    return Path(codex_home or (Path(_home(env)) / ".codex")) / "config.toml"


def _opencode_config(env: Mapping[str, str]) -> Path:
    explicit = str(env.get("OPENCODE_CONFIG") or "").strip()
    if explicit:
        return Path(explicit)
    root = Path(_home(env)) / ".config" / "opencode"
    jsonc = root / "opencode.jsonc"
    return jsonc if jsonc.exists() else root / "opencode.json"


def _claude_code_config(env: Mapping[str, str]) -> Path:
    explicit = str(env.get("CLAUDE_CONFIG_DIR") or "").strip()
    return Path(explicit) / ".claude.json" if explicit else Path(_home(env)) / ".claude.json"


def _gemini_config(env: Mapping[str, str]) -> Path:
    return Path(_home(env)) / ".gemini" / "settings.json"


def _cursor_config(env: Mapping[str, str]) -> Path:
    return Path(_home(env)) / ".cursor" / "mcp.json"


def _windsurf_config(env: Mapping[str, str]) -> Path:
    return Path(_home(env)) / ".codeium" / "windsurf" / "mcp_config.json"


def _claude_desktop_config(env: Mapping[str, str], platform: str) -> Path:
    if platform != "windows":
        raise RuntimeError("Claude Desktop integration is currently packaged for Windows only")
    appdata = str(env.get("APPDATA") or "").strip()
    if not appdata:
        appdata = ntpath.join(_home(env), "AppData", "Roaming")
    return Path(appdata) / "Claude" / "claude_desktop_config.json"


def _vscode_config_label(env: Mapping[str, str]) -> str:
    return str(Path(_home(env)) / ".copilot" / "mcp-config.json") + " (portable/user profile managed by VS Code)"


def _which(name: str, which: Callable[[str], str | None]) -> str | None:
    return which(name) or (which(f"{name}.exe") if os.name == "nt" else None)


def _candidate_windows_executable(env: Mapping[str, str], *parts: str) -> str | None:
    local = str(env.get("LOCALAPPDATA") or "").strip()
    if not local:
        return None
    for rel in parts:
        path = Path(local) / Path(rel)
        if path.exists():
            return str(path)
    return None


def _run(command: Sequence[str], *, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> subprocess.CompletedProcess[str]:
    try:
        return runner(
            list(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=False, timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"provider command failed to launch: {exc}") from exc


def _env_pairs(paths: GremlinPaths) -> list[str]:
    entry = gremlin_stdio_entry(paths)
    return [f"{key}={value}" for key, value in sorted(dict(entry.get("env") or {}).items())]


def _stdio_command(paths: GremlinPaths) -> list[str]:
    entry = gremlin_stdio_entry(paths)
    return [str(entry["command"]), *[str(v) for v in entry.get("args") or []]]


def _json_status(
    *, provider_id: str, display_name: str, executable: str | None,
    config_path: Path, paths: GremlinPaths, detected_hint: bool = False,
) -> ProviderStatus:
    detected = bool(executable or config_path.exists() or config_path.parent.exists() or detected_hint)
    try:
        inspected = inspect_json_mcp(config_path, server_name=SERVER_NAME)
        connected = bool(inspected.get("gremlin_present"))
    except ValueError as exc:
        return ProviderStatus(provider_id, display_name, detected, executable, str(config_path), False,
                              "CONFIG_INVALID", "JSON_MCP", paths.platform, str(exc))
    return ProviderStatus(
        provider_id, display_name, detected, executable, str(config_path), connected,
        "CONNECTED" if connected else ("READY_TO_CONNECT" if detected else "NOT_DETECTED"),
        "JSON_MCP", paths.platform, None,
    )


def _cli_status(
    *, provider_id: str, display_name: str, executable: str | None, config_path: str,
    paths: GremlinPaths, command: Sequence[str], runner: Callable[..., subprocess.CompletedProcess[str]],
    live_word: str | None = None,
) -> ProviderStatus:
    detected = executable is not None
    if executable is None:
        return ProviderStatus(provider_id, display_name, False, None, config_path, False,
                              "NOT_DETECTED", "NATIVE_CLI", paths.platform, None)
    result = _run(command, runner=runner)
    text = f"{result.stdout}\n{result.stderr}".strip()
    registered = result.returncode == 0 and SERVER_NAME.casefold() in text.casefold()
    if provider_id == "codex" and result.returncode == 0:
        try:
            payload = json.loads(result.stdout)
            transport = payload.get("transport") if isinstance(payload, dict) else None
            registered = isinstance(transport, dict) and transport.get("type") == "stdio"
        except json.JSONDecodeError:
            registered = False
    live = registered and (live_word is None or live_word.casefold() in text.casefold())
    return ProviderStatus(
        provider_id, display_name, True, executable, config_path, registered,
        "CONNECTED" if live else ("REGISTERED" if registered else "NOT_CONNECTED"),
        "NATIVE_CLI", paths.platform, None if registered else (text or None),
    )


def _provider_executables(paths: GremlinPaths, env: Mapping[str, str], which: Callable[[str], str | None]) -> dict[str, str | None]:
    result = {
        "codex": _which("codex", which),
        "opencode": _which("opencode", which),
        "claude-code": _which("claude", which),
        "gemini": _which("gemini", which),
        "cursor": _which("cursor-agent", which) or _which("cursor", which),
        "vscode": _which("code", which),
        "windsurf": _which("windsurf", which),
        "claude-desktop": None,
    }
    if paths.platform == "windows":
        result["cursor"] = result["cursor"] or _candidate_windows_executable(
            env, r"Programs\cursor\Cursor.exe", r"Programs\Cursor\Cursor.exe")
        result["windsurf"] = result["windsurf"] or _candidate_windows_executable(
            env, r"Programs\Windsurf\Windsurf.exe", r"Programs\windsurf\Windsurf.exe")
        result["claude-desktop"] = _candidate_windows_executable(
            env, r"AnthropicClaude\Claude.exe", r"Programs\Claude\Claude.exe")
    return result


def list_providers(
    paths: GremlinPaths, *, env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    environ = os.environ if env is None else env
    exe = _provider_executables(paths, environ, which)
    providers: list[ProviderStatus] = []

    providers.append(_cli_status(
        provider_id="codex", display_name="OpenAI Codex", executable=exe["codex"],
        config_path=str(_codex_config(environ)), paths=paths,
        command=[exe["codex"] or "codex", "mcp", "get", SERVER_NAME, "--json"], runner=runner,
    ))
    providers.append(_cli_status(
        provider_id="opencode", display_name="OpenCode", executable=exe["opencode"],
        config_path=str(_opencode_config(environ)), paths=paths,
        command=[exe["opencode"] or "opencode", "mcp", "list"], runner=runner, live_word="connected",
    ))
    providers.append(_cli_status(
        provider_id="claude-code", display_name="Anthropic Claude Code", executable=exe["claude-code"],
        config_path=str(_claude_code_config(environ)), paths=paths,
        command=[exe["claude-code"] or "claude", "mcp", "get", SERVER_NAME], runner=runner,
    ))
    providers.append(_cli_status(
        provider_id="gemini", display_name="Google Gemini CLI", executable=exe["gemini"],
        config_path=str(_gemini_config(environ)), paths=paths,
        command=[exe["gemini"] or "gemini", "mcp", "list"], runner=runner,
    ))
    providers.append(_json_status(
        provider_id="cursor", display_name="Cursor", executable=exe["cursor"],
        config_path=_cursor_config(environ), paths=paths,
    ))
    providers.append(ProviderStatus(
        "vscode", "Visual Studio Code / GitHub Copilot", exe["vscode"] is not None,
        exe["vscode"], _vscode_config_label(environ), False,
        "READY_TO_CONNECT" if exe["vscode"] else "NOT_DETECTED", "NATIVE_CLI", paths.platform,
        "VS Code exposes code --add-mcp; live MCP status is verified inside VS Code after registration.",
    ))
    providers.append(_json_status(
        provider_id="windsurf", display_name="Windsurf Cascade", executable=exe["windsurf"],
        config_path=_windsurf_config(environ), paths=paths,
    ))
    if paths.platform == "windows":
        providers.append(_json_status(
            provider_id="claude-desktop", display_name="Anthropic Claude Desktop",
            executable=exe["claude-desktop"], config_path=_claude_desktop_config(environ, paths.platform),
            paths=paths,
        ))

    return {
        "schema": PROVIDER_SCHEMA,
        "platform": paths.platform,
        "providers": [p.as_dict() for p in providers],
        "custom": {"supported": True, "mode": "GENERIC_JSON_MCP"},
    }


def _config_for(provider: str, env: Mapping[str, str], paths: GremlinPaths) -> Path | None:
    return {
        "codex": _codex_config,
        "opencode": _opencode_config,
        "claude-code": _claude_code_config,
        "gemini": _gemini_config,
        "cursor": _cursor_config,
        "windsurf": _windsurf_config,
    }.get(provider, lambda _env: None)(env) if provider != "claude-desktop" else _claude_desktop_config(env, paths.platform)


def _provider_context(
    provider_id: str, paths: GremlinPaths, *, env: Mapping[str, str], which: Callable[[str], str | None],
) -> tuple[str | None, Path | None]:
    provider = provider_id.strip().casefold()
    supported = {"codex", "opencode", "claude-code", "gemini", "cursor", "vscode", "windsurf"}
    if paths.platform == "windows":
        supported.add("claude-desktop")
    if provider not in supported:
        raise ValueError(f"unsupported MCP provider for {paths.platform}: {provider_id}")
    exe = _provider_executables(paths, env, which).get(provider)
    config = None if provider == "vscode" else _config_for(provider, env, paths)
    return exe, config


def _json_provider_action(
    provider: str, action: str, paths: GremlinPaths, config: Path,
) -> ProviderAction:
    backup_root = Path(paths.data_dir) / "integration-backups"
    if action == "connect":
        receipt = install_json_mcp(
            client_id=provider, config_path=config, entry=gremlin_stdio_entry(paths),
            backup_root=backup_root, server_name=SERVER_NAME,
        )
        return ProviderAction(PROVIDER_ACTION_SCHEMA, provider, "CONNECTED_CONFIGURED", None, str(config), receipt.backup_path)
    if action == "disconnect":
        receipt = remove_json_mcp(
            client_id=provider, config_path=config, backup_root=backup_root, server_name=SERVER_NAME,
        )
        return ProviderAction(PROVIDER_ACTION_SCHEMA, provider, "DISCONNECTED", None, str(config), receipt.backup_path)
    inspected = inspect_json_mcp(config, server_name=SERVER_NAME)
    ok = bool(inspected.get("gremlin_present"))
    return ProviderAction(PROVIDER_ACTION_SCHEMA, provider, "PASS" if ok else "NOT_CONNECTED", None, str(config), None)


def connect_provider(
    provider_id: str, paths: GremlinPaths, *, env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> ProviderAction:
    environ = os.environ if env is None else env
    provider = provider_id.strip().casefold()
    executable, config = _provider_context(provider, paths, env=environ, which=which)
    if provider in {"cursor", "windsurf", "claude-desktop"}:
        assert config is not None
        return _json_provider_action(provider, "connect", paths, config)
    if executable is None:
        raise RuntimeError(f"{provider} client executable is not available on PATH or a known install location")

    env_pairs = _env_pairs(paths)
    stdio = _stdio_command(paths)
    if provider in {"codex", "opencode"}:
        command = [executable, "mcp", "add", SERVER_NAME]
        for pair in env_pairs:
            command.extend(["--env", pair])
        command.extend(["--", *stdio])
    elif provider == "claude-code":
        command = [executable, "mcp", "add", "--transport", "stdio", "--scope", "user"]
        for pair in env_pairs:
            command.extend(["--env", pair])
        command.extend([SERVER_NAME, "--", *stdio])
    elif provider == "gemini":
        command = [executable, "mcp", "add", "--scope", "user", "--transport", "stdio"]
        for pair in env_pairs:
            command.extend(["--env", pair])
        command.extend([SERVER_NAME, *stdio])
    elif provider == "vscode":
        entry = gremlin_stdio_entry(paths)
        payload = json.dumps({
            "name": SERVER_NAME, "command": entry["command"],
            "args": entry.get("args") or [], "env": entry.get("env") or {},
        }, separators=(",", ":"))
        command = [executable, "--add-mcp", payload]
    else:
        raise ValueError(f"unsupported provider action: {provider}")

    result = _run(command, runner=runner)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip() or f"{provider} MCP registration failed")
    config_label = str(config) if config is not None else _vscode_config_label(environ)
    status = "REGISTERED_RESTART_REQUIRED" if provider == "vscode" else "CONNECTED_CONFIGURED"
    return ProviderAction(PROVIDER_ACTION_SCHEMA, provider, status, executable, config_label, (result.stdout or result.stderr).strip() or None)


def disconnect_provider(
    provider_id: str, paths: GremlinPaths, *, env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> ProviderAction:
    environ = os.environ if env is None else env
    provider = provider_id.strip().casefold()
    executable, config = _provider_context(provider, paths, env=environ, which=which)
    if provider in {"cursor", "windsurf", "claude-desktop"}:
        assert config is not None
        return _json_provider_action(provider, "disconnect", paths, config)
    if executable is None:
        raise RuntimeError(f"{provider} client executable is not available")
    if provider == "codex":
        command = [executable, "mcp", "remove", SERVER_NAME]
    elif provider == "claude-code":
        command = [executable, "mcp", "remove", SERVER_NAME, "--scope", "user"]
    elif provider == "gemini":
        command = [executable, "mcp", "remove", SERVER_NAME, "--scope", "user"]
    elif provider in {"opencode", "vscode"}:
        return ProviderAction(
            PROVIDER_ACTION_SCHEMA, provider, "MANUAL_REMOVE_REQUIRED", executable,
            str(config) if config is not None else _vscode_config_label(environ),
            "This client currently lacks a stable non-interactive remove surface used by GREMLIN; Control Center will not rewrite its private config blindly.",
        )
    else:
        raise ValueError(f"unsupported provider action: {provider}")
    result = _run(command, runner=runner)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip() or f"{provider} MCP removal failed")
    return ProviderAction(PROVIDER_ACTION_SCHEMA, provider, "DISCONNECTED", executable, str(config), (result.stdout or result.stderr).strip() or None)


def test_provider(
    provider_id: str, paths: GremlinPaths, *, env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> ProviderAction:
    environ = os.environ if env is None else env
    provider = provider_id.strip().casefold()
    executable, config = _provider_context(provider, paths, env=environ, which=which)
    if provider in {"cursor", "windsurf", "claude-desktop"}:
        assert config is not None
        return _json_provider_action(provider, "test", paths, config)
    if executable is None:
        raise RuntimeError(f"{provider} client executable is not available")
    if provider == "codex":
        result = _run([executable, "mcp", "get", SERVER_NAME, "--json"], runner=runner)
        if result.returncode != 0:
            return ProviderAction(PROVIDER_ACTION_SCHEMA, provider, "NOT_CONNECTED", executable, str(config), (result.stderr or result.stdout).strip() or None)
        try:
            payload = json.loads(result.stdout)
            transport = payload.get("transport") if isinstance(payload, dict) else None
            ok = isinstance(transport, dict) and transport.get("type") == "stdio"
        except json.JSONDecodeError:
            ok = False
        return ProviderAction(PROVIDER_ACTION_SCHEMA, provider, "PASS" if ok else "REGISTERED_UNVERIFIED", executable, str(config), None)
    if provider == "claude-code":
        result = _run([executable, "mcp", "get", SERVER_NAME], runner=runner)
    elif provider in {"opencode", "gemini"}:
        result = _run([executable, "mcp", "list"], runner=runner)
    elif provider == "vscode":
        return ProviderAction(PROVIDER_ACTION_SCHEMA, provider, "REGISTERED_UNVERIFIED", executable, _vscode_config_label(environ), "Open VS Code and run MCP: List Servers to verify the live server after registration.")
    else:
        raise ValueError(f"unsupported provider action: {provider}")
    text = f"{result.stdout}\n{result.stderr}".strip()
    registered = result.returncode == 0 and SERVER_NAME.casefold() in text.casefold()
    live = registered and (provider not in {"opencode"} or "connected" in text.casefold())
    return ProviderAction(
        PROVIDER_ACTION_SCHEMA, provider, "PASS" if live else ("REGISTERED_RUNTIME_NOT_READY" if registered else "NOT_CONNECTED"),
        executable, str(config), None if live else (text or None),
    )
