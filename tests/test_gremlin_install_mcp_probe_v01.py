from __future__ import annotations

import os
from pathlib import Path
import sys

from gremlin_mcp.install.mcp_probe import probe_stdio_mcp


def _server(tmp_path: Path) -> Path:
    script = tmp_path / "probe_server.py"
    script.write_text(
        """
from mcp.server import MCPServer

mcp = MCPServer("GREMLIN-PROBE-TEST")

@mcp.tool()
def ping() -> dict[str, bool]:
    return {"ok": True}

if __name__ == "__main__":
    mcp.run("stdio")
""".lstrip(),
        encoding="utf-8",
    )
    return script


def test_stdio_probe_negotiates_real_subprocess_and_exact_registry(tmp_path) -> None:
    server = _server(tmp_path)
    result = probe_stdio_mcp(
        {
            "command": sys.executable,
            "args": [str(server)],
            "env": {},
        },
        expected_tools={"ping"},
        timeout_seconds=5,
        platform="windows" if os.name == "nt" else "linux",
    )
    assert result["status"] == "PASS"
    assert result["transport"] == "stdio"
    assert result["registry_exact"] is True
    assert result["tool_count"] == 1
    assert result["expected_tool_count"] == 1
    assert result["missing_tools"] == []
    assert result["unexpected_tools"] == []


def test_stdio_probe_fails_closed_on_registry_mismatch(tmp_path) -> None:
    server = _server(tmp_path)
    result = probe_stdio_mcp(
        {
            "command": sys.executable,
            "args": [str(server)],
            "env": {},
        },
        expected_tools={"ping", "required-but-missing"},
        timeout_seconds=5,
        platform="windows" if os.name == "nt" else "linux",
    )
    assert result["status"] == "FAIL"
    assert result["registry_exact"] is False
    assert result["missing_tools"] == ["required-but-missing"]
    assert result["unexpected_tools"] == []


def test_stdio_probe_rejects_unavailable_executable(tmp_path) -> None:
    result = probe_stdio_mcp(
        {
            "command": str(tmp_path / "missing-gremlin-product-mcp"),
            "args": ["--transport", "stdio"],
            "env": {},
        },
        expected_tools={"gremlin_status"},
        timeout_seconds=1,
        platform="linux",
    )
    assert result["status"] == "FAIL"
    assert result["registry_exact"] is False
    assert "unavailable" in result["detail"]
