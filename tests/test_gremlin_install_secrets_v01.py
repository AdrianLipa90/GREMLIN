from __future__ import annotations

import os

import pytest

from gremlin_mcp.install.paths import resolve_paths
from gremlin_mcp.install.secrets import WindowsDpapiStore, secret_store_status


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


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI integration test")
def test_windows_dpapi_roundtrip_is_user_bound_and_not_plaintext(tmp_path) -> None:
    store = WindowsDpapiStore(tmp_path)
    secret = b"GREMLIN-device-private-test-secret"
    store.set("device-test", secret)
    blobs = list(tmp_path.glob("*.dpapi"))
    assert len(blobs) == 1
    assert blobs[0].read_bytes() != secret
    assert secret not in blobs[0].read_bytes()
    assert store.get("device-test") == secret
    store.delete("device-test")
    assert store.get("device-test") is None
