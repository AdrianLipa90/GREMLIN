from __future__ import annotations

import pytest

from gremlin_mcp.install.paths import resolve_paths
from gremlin_mcp.install.secrets import secret_store_status


def test_windows_secret_store_contract_is_dpapi() -> None:
    paths = resolve_paths(platform="windows", env={"USERPROFILE": r"C:\Users\Alice"})
    status = secret_store_status(paths, which=lambda _name: None)
    assert status["available"] is True
    assert status["backend"] == "WINDOWS_DPAPI"


def test_linux_secret_store_reports_missing_secret_tool() -> None:
    paths = resolve_paths(platform="linux", env={"HOME": "/home/alice"})
    status = secret_store_status(paths, which=lambda _name: None)
    assert status["available"] is False
    assert status["backend"] == "LINUX_SECRET_SERVICE"


def test_linux_secret_store_reports_detected_secret_tool() -> None:
    paths = resolve_paths(platform="linux", env={"HOME": "/home/alice"})
    status = secret_store_status(paths, which=lambda name: "/usr/bin/secret-tool" if name == "secret-tool" else None)
    assert status["available"] is True
    assert status["executable"] == "/usr/bin/secret-tool"
