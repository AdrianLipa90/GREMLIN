from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Callable, Mapping, Sequence

from .integrations import gremlin_stdio_entry
from .paths import GremlinPaths


PROVIDER_SCHEMA = "GREMLIN_MCP_PROVIDER_STATUS_V0_1"
PROVIDER_ACTION_SCHEMA = "GREMLIN_MCP_PROVIDER_ACTION_V0_1"
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
    if codex_home:
        return Path(codex_home) / "config.toml"
    return Path(_home(env)) / ".codex" / "config.toml"


def _opencode_config(env: Mapping[str, str]) -> Path:
    explicit = str(env.get("OPENCODE_CONFIG") or "").strip()
    if explicit:
        return Path(explicit)
    root = Path(_home(env)) / ".config" / "opencode"
    jsonc = root / "opencode.jsonc"
    if jsonc.exists():
        return jsonc
    return root / "opencode.json"


def _which(name: str, which: Callable[[str], str | None]) -> str | None:
    return which(name) or (which(f"{name}.exe") if os.name == "nt" else None)


def _run(
    command: Sequence[str],
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> subprocess.CompletedProcess[str]:
    try:
        return runner(
            list(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"provider command failed to launch: {exc}") from exc


def _env_pairs(paths: GremlinPaths) -> list[str]:
    entry = gremlin_stdio_entry(paths)
    env = dict(entry.get("env") or {})
    return [f"{key}={value}" for key, value in sorted(env.items())]


def _stdio_command(paths: GremlinPaths) -> list[str]:
    entry = gremlin_stdio_entry(paths)
    return [str(entry["command"]), *[str(v) for v in entry.get("args") or []]]


def _codex_status(
    executable: str | None,
    config_path: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> ProviderStatus:
    detected = executable is not None or config_path.exists()
    if executable is None:
        return ProviderStatus(
            provider_id="codex",
            display_name="OpenAI Codex",
            detected=detected,
            executable=None,
            config_path=str(config_path),
            connected=False,
            connection_status="CLIENT_NOT_ON_PATH" if detected else "NOT_DETECTED",
            detail="Codex config was found but the codex executable is not available on PATH." if detected else None,
        )
    result = _run([executable, "mcp", "get", SERVER_NAME, "--json"], runner=runner)
    if result.returncode != 0:
        return ProviderStatus(
            provider_id="codex",
            display_name="OpenAI Codex",
            detected=True,
            executable=executable,
            config_path=str(config_path),
            connected=False,
            connection_status="NOT_CONNECTED",
            detail=(result.stderr or result.stdout).strip() or None,
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ProviderStatus(
            provider_id="codex",
            display_name="OpenAI Codex",
            detected=True,
            executable=executable,
            config_path=str(config_path),
            connected=True,
            connection_status="REGISTERED_UNVERIFIED",
            detail="Codex returned non-JSON MCP registration output.",
        )
    transport = payload.get("transport") if isinstance(payload, dict) else None
    is_stdio = isinstance(transport, dict) and transport.get("type") == "stdio"
    return ProviderStatus(
        provider_id="codex",
        display_name="OpenAI Codex",
        detected=True,
        executable=executable,
        config_path=str(config_path),
        connected=True,
        connection_status="CONNECTED" if is_stdio else "REGISTERED_UNVERIFIED",
        detail=None if is_stdio else "GREMLIN is registered in Codex but the transport could not be verified as stdio.",
    )


def _opencode_status(
    executable: str | None,
    config_path: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> ProviderStatus:
    detected = executable is not None or config_path.exists()
    if executable is None:
        return ProviderStatus(
            provider_id="opencode",
            display_name="OpenCode",
            detected=detected,
            executable=None,
            config_path=str(config_path),
            connected=False,
            connection_status="CLIENT_NOT_ON_PATH" if detected else "NOT_DETECTED",
            detail="OpenCode config was found but the opencode executable is not available on PATH." if detected else None,
        )
    result = _run([executable, "mcp", "list"], runner=runner)
    text = f"{result.stdout}\n{result.stderr}".strip()
    registered = result.returncode == 0 and SERVER_NAME.casefold() in text.casefold()
    connected = registered and "connected" in text.casefold()
    return ProviderStatus(
        provider_id="opencode",
        display_name="OpenCode",
        detected=True,
        executable=executable,
        config_path=str(config_path),
        connected=registered,
        connection_status="CONNECTED" if connected else ("REGISTERED" if registered else "NOT_CONNECTED"),
        detail=None if registered else (text or None),
    )


def list_providers(
    paths: GremlinPaths,
    *,
    env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    environ = os.environ if env is None else env
    codex = _which("codex", which)
    opencode = _which("opencode", which)
    return {
        "schema": PROVIDER_SCHEMA,
        "providers": [
            _codex_status(codex, _codex_config(environ), runner=runner).as_dict(),
            _opencode_status(opencode, _opencode_config(environ), runner=runner).as_dict(),
        ],
        "custom": {
            "supported": True,
            "mode": "GENERIC_JSON_MCP",
        },
    }


def _provider_context(
    provider_id: str,
    *,
    env: Mapping[str, str],
    which: Callable[[str], str | None],
) -> tuple[str, Path]:
    provider = provider_id.strip().casefold()
    if provider == "codex":
        executable = _which("codex", which)
        config = _codex_config(env)
    elif provider == "opencode":
        executable = _which("opencode", which)
        config = _opencode_config(env)
    else:
        raise ValueError(f"unsupported MCP provider: {provider_id}")
    if executable is None:
        raise RuntimeError(f"{provider} executable is not available on PATH")
    return executable, config


def connect_provider(
    provider_id: str,
    paths: GremlinPaths,
    *,
    env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> ProviderAction:
    environ = os.environ if env is None else env
    executable, config_path = _provider_context(provider_id, env=environ, which=which)
    provider = provider_id.strip().casefold()
    env_pairs = _env_pairs(paths)
    stdio = _stdio_command(paths)

    if provider == "codex":
        command = [executable, "mcp", "add", SERVER_NAME]
        for pair in env_pairs:
            command.extend(["--env", pair])
        command.extend(["--", *stdio])
    else:
        command = [executable, "mcp", "add", SERVER_NAME]
        for pair in env_pairs:
            command.extend(["--env", pair])
        command.extend(["--", *stdio])

    result = _run(command, runner=runner)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip() or f"{provider} MCP registration failed")
    return ProviderAction(
        schema=PROVIDER_ACTION_SCHEMA,
        provider_id=provider,
        status="CONNECTED_CONFIGURED",
        executable=executable,
        config_path=str(config_path),
        detail=(result.stdout or result.stderr).strip() or None,
    )


def disconnect_provider(
    provider_id: str,
    paths: GremlinPaths,
    *,
    env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> ProviderAction:
    del paths
    environ = os.environ if env is None else env
    executable, config_path = _provider_context(provider_id, env=environ, which=which)
    provider = provider_id.strip().casefold()
    if provider == "codex":
        command = [executable, "mcp", "remove", SERVER_NAME]
    else:
        # Current OpenCode CLI has no stable non-interactive remove command. We do not
        # rewrite JSON/JSONC behind its back; surface this explicitly instead.
        return ProviderAction(
            schema=PROVIDER_ACTION_SCHEMA,
            provider_id=provider,
            status="MANUAL_REMOVE_REQUIRED",
            executable=executable,
            config_path=str(config_path),
            detail="OpenCode currently exposes mcp add/list but no stable non-interactive remove command; remove the GREMLIN entry in OpenCode or its config.",
        )
    result = _run(command, runner=runner)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip() or f"{provider} MCP removal failed")
    return ProviderAction(
        schema=PROVIDER_ACTION_SCHEMA,
        provider_id=provider,
        status="DISCONNECTED",
        executable=executable,
        config_path=str(config_path),
        detail=(result.stdout or result.stderr).strip() or None,
    )


def test_provider(
    provider_id: str,
    paths: GremlinPaths,
    *,
    env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> ProviderAction:
    environ = os.environ if env is None else env
    executable, config_path = _provider_context(provider_id, env=environ, which=which)
    provider = provider_id.strip().casefold()
    if provider == "codex":
        result = _run([executable, "mcp", "get", SERVER_NAME, "--json"], runner=runner)
        if result.returncode != 0:
            return ProviderAction(PROVIDER_ACTION_SCHEMA, provider, "NOT_CONNECTED", executable, str(config_path), (result.stderr or result.stdout).strip() or None)
        try:
            payload = json.loads(result.stdout)
            transport = payload.get("transport") if isinstance(payload, dict) else None
            ok = isinstance(transport, dict) and transport.get("type") == "stdio"
        except json.JSONDecodeError:
            ok = False
        return ProviderAction(PROVIDER_ACTION_SCHEMA, provider, "PASS" if ok else "REGISTERED_UNVERIFIED", executable, str(config_path), None)

    result = _run([executable, "mcp", "list"], runner=runner)
    text = f"{result.stdout}\n{result.stderr}".strip()
    if result.returncode != 0 or SERVER_NAME.casefold() not in text.casefold():
        return ProviderAction(PROVIDER_ACTION_SCHEMA, provider, "NOT_CONNECTED", executable, str(config_path), text or None)
    live = "connected" in text.casefold()
    return ProviderAction(
        PROVIDER_ACTION_SCHEMA,
        provider,
        "PASS" if live else "REGISTERED_RUNTIME_NOT_READY",
        executable,
        str(config_path),
        None if live else text or "GREMLIN is registered but OpenCode did not report a live MCP connection.",
    )
