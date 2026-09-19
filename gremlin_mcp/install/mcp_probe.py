from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

from mcp import Client, StdioServerParameters

from gremlin_mcp.core import PRODUCT_MCP_TOOLS

from .integrations import gremlin_stdio_entry
from .paths import GremlinPaths

SCHEMA = "GREMLIN_MCP_RUNTIME_PROBE_V0_1"
DEFAULT_TIMEOUT_SECONDS = 10.0


def _tool_set(value: Iterable[str]) -> set[str]:
    if isinstance(value, (str, bytes, bytearray, Mapping)):
        raise ValueError("expected_tools must be an iterable of tool names")
    out: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"expected_tools[{index}] must be a non-empty string")
        name = item.strip()
        if name in out:
            raise ValueError(f"duplicate expected tool: {name}")
        out.add(name)
    if not out:
        raise ValueError("expected_tools must not be empty")
    return out


def _entry(entry: Mapping[str, Any]) -> tuple[str, list[str], dict[str, str]]:
    if not isinstance(entry, Mapping):
        raise ValueError("stdio entry must be an object")
    command = entry.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ValueError("stdio entry command must be a non-empty string")
    raw_args = entry.get("args", [])
    if not isinstance(raw_args, list) or any(not isinstance(item, str) for item in raw_args):
        raise ValueError("stdio entry args must be a list of strings")
    raw_env = entry.get("env", {})
    if not isinstance(raw_env, Mapping):
        raise ValueError("stdio entry env must be an object")
    env: dict[str, str] = dict(os.environ)
    for key, value in raw_env.items():
        if not isinstance(key, str) or not key:
            raise ValueError("stdio entry env keys must be non-empty strings")
        if not isinstance(value, str):
            raise ValueError(f"stdio entry env value for {key} must be a string")
        env[key] = value
    return command.strip(), list(raw_args), env


def _available(command: str, platform: str | None = None) -> bool:
    target = Path(command)
    if not target.is_file():
        return False
    if platform == "windows" or os.name == "nt":
        return True
    return os.access(target, os.X_OK)


async def _probe_async(
    *,
    command: str,
    args: list[str],
    env: dict[str, str],
    expected_tools: set[str],
) -> dict[str, Any]:
    params = StdioServerParameters(command=command, args=args, env=env)
    async with Client(params) as client:
        listed = await client.list_tools()
        names = {tool.name for tool in listed.tools}
        missing = sorted(expected_tools - names)
        unexpected = sorted(names - expected_tools)
        exact = not missing and not unexpected
        server_info = getattr(client, "server_info", None)
        server_name = getattr(server_info, "name", None) if server_info is not None else None
        protocol = getattr(client, "protocol_version", None)
        return {
            "schema": SCHEMA,
            "status": "PASS" if exact else "FAIL",
            "transport": "stdio",
            "server_name": server_name if isinstance(server_name, str) else None,
            "protocol_version": str(protocol) if protocol is not None else None,
            "tool_count": len(names),
            "expected_tool_count": len(expected_tools),
            "registry_exact": exact,
            "missing_tools": missing,
            "unexpected_tools": unexpected,
            "detail": None if exact else "MCP tool registry differs from the declared product contract",
        }


def probe_stdio_mcp(
    entry: Mapping[str, Any],
    *,
    expected_tools: Iterable[str],
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    platform: str | None = None,
) -> dict[str, Any]:
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
        raise ValueError("timeout_seconds must be a positive number")
    timeout = float(timeout_seconds)
    if not 0.0 < timeout <= 60.0:
        raise ValueError("timeout_seconds must be in (0, 60]")

    expected = _tool_set(expected_tools)
    command, args, env = _entry(entry)
    if not _available(command, platform):
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "transport": "stdio",
            "server_name": None,
            "protocol_version": None,
            "tool_count": 0,
            "expected_tool_count": len(expected),
            "registry_exact": False,
            "missing_tools": sorted(expected),
            "unexpected_tools": [],
            "detail": "GREMLIN MCP executable is unavailable or not executable",
        }

    try:
        return asyncio.run(
            asyncio.wait_for(
                _probe_async(
                    command=command,
                    args=args,
                    env=env,
                    expected_tools=expected,
                ),
                timeout=timeout,
            )
        )
    except TimeoutError:
        detail = f"MCP stdio handshake timed out after {timeout:g} seconds"
    except Exception as exc:
        detail = f"{type(exc).__name__}: MCP stdio handshake failed"

    return {
        "schema": SCHEMA,
        "status": "FAIL",
        "transport": "stdio",
        "server_name": None,
        "protocol_version": None,
        "tool_count": 0,
        "expected_tool_count": len(expected),
        "registry_exact": False,
        "missing_tools": sorted(expected),
        "unexpected_tools": [],
        "detail": detail,
    }


def probe_product_mcp(
    paths: GremlinPaths,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    if not isinstance(paths, GremlinPaths):
        raise ValueError("paths must be GremlinPaths")
    return probe_stdio_mcp(
        gremlin_stdio_entry(paths),
        expected_tools=PRODUCT_MCP_TOOLS,
        timeout_seconds=timeout_seconds,
        platform=paths.platform,
    )
