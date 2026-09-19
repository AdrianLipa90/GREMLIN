from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import stat
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

import gremlin_mcp.workspace as workspace
from gremlin_mcp.install.paths import resolve_paths
from gremlin_mcp.product import ProductAuthorizationError
from tools.gremlin_client_protocol_v01 import REQUEST_SCHEMA


class FakeRuntime:
    def __init__(self, *, licensed: bool = True, prototype_allowed: bool = True) -> None:
        self.licensed = licensed
        self.prototype_allowed = prototype_allowed
        self.calls: list[dict[str, object]] = []

    def status(self) -> dict[str, object]:
        if self.licensed:
            return {
                "status": "LICENSED",
                "license": {
                    "license_id": "TEST-SECRET-ID",
                    "edition": "RESEARCH",
                    "expires_at": "2030-12-31",
                    "features": ["MCP_STDIO", "PROTOTYPE_PIPELINE"],
                    "limits": {"max_workers": 4, "max_sources": 24},
                },
                "profile": {
                    "client_id": "test-client-secret-id",
                    "label": "Test Customer Profile",
                    "profile_commitment": "a" * 64,
                },
            }
        return {"status": "BLOCKED", "reason": "LICENSE_REQUIRED"}

    def authorize(self, **kwargs) -> None:
        self.calls.append(dict(kwargs))
        if not self.prototype_allowed:
            raise ProductAuthorizationError("FEATURE_NOT_ENTITLED:PROTOTYPE_PIPELINE")


def _paths(tmp_path: Path):
    home = tmp_path / "home"
    home.mkdir()
    base = resolve_paths(
        platform="linux",
        env={
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_STATE_HOME": str(home / ".state"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "XDG_DATA_HOME": str(home / ".data"),
        },
    )
    return replace(
        base,
        install_root=str(tmp_path / "install"),
        shared_data_root=str(tmp_path / "shared"),
        diagnostics_dir=str(tmp_path / "diagnostics"),
    )


def _stage_assets(paths) -> tuple[Path, Path]:
    root = Path(paths.shared_data_root) / "workspace"
    root.mkdir(parents=True)
    (root / "index.html").write_text("<!doctype html><title>GREMLIN</title>", encoding="utf-8")
    (root / "app.js").write_text('"use strict";', encoding="utf-8")
    (root / "styles.css").write_text("body{}", encoding="utf-8")
    example = {
        "schema": REQUEST_SCHEMA,
        "request_id": "workspace-test",
        "target": "python_reference",
        "sample_count": 1,
        "candidate": {"candidate_id": "fixture"},
    }
    example_path = root / "example-request.json"
    example_path.write_text(json.dumps(example), encoding="utf-8")
    return root, example_path


def _server(paths, *, token: str = "t" * 48, instance_id: str = "i" * 32):
    web_root, example = _stage_assets(paths)
    server = workspace.GremlinWorkspaceServer(
        ("127.0.0.1", 0),
        web_root=web_root,
        example_path=example,
        runtime=FakeRuntime(),  # type: ignore[arg-type]
        instance_id=instance_id,
        shutdown_token=token,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, token, instance_id


def test_workspace_prefers_installed_resources(tmp_path) -> None:
    paths = _paths(tmp_path)
    root, example = _stage_assets(paths)
    web_root, example_path, mode = workspace.resolve_workspace_assets(paths)
    assert web_root == root
    assert example_path == example
    assert mode == "INSTALLED_RESOURCES"


def test_workspace_rejects_non_loopback_bind() -> None:
    with pytest.raises(workspace.GremlinWorkspaceError, match="loopback"):
        workspace._assert_loopback("0.0.0.0")
    with pytest.raises(workspace.GremlinWorkspaceError, match="loopback"):
        workspace._assert_loopback("example.com")
    assert workspace._assert_loopback("127.0.0.1") == "127.0.0.1"
    assert workspace._assert_loopback("::1") == "::1"


def test_workspace_check_requires_product_feature(tmp_path, monkeypatch) -> None:
    paths = _paths(tmp_path)
    _stage_assets(paths)
    runtime = FakeRuntime(licensed=True, prototype_allowed=False)
    monkeypatch.setattr(workspace, "_runtime", lambda _paths: runtime)

    check = workspace.workspace_check(paths=paths)
    assert check["status"] == "BLOCKED"
    assert check["reason"] == "FEATURE_NOT_ENTITLED:PROTOTYPE_PIPELINE"
    assert check["authority"] == {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
    assert runtime.calls == [{
        "tool": "gremlin_prototype",
        "feature": "PROTOTYPE_PIPELINE",
    }]


def test_workspace_check_is_ready_only_after_assets_license_feature_and_port(tmp_path, monkeypatch) -> None:
    paths = _paths(tmp_path)
    _stage_assets(paths)
    runtime = FakeRuntime()
    monkeypatch.setattr(workspace, "_runtime", lambda _paths: runtime)
    monkeypatch.setattr(workspace, "_probe_health", lambda _host, _port, timeout=0.35: None)
    monkeypatch.setattr(workspace, "_port_available", lambda _host, _port: True)

    check = workspace.workspace_check(paths=paths, host="127.0.0.1", port=8765)
    assert check["status"] == "READY"
    assert check["already_running"] is False
    assert check["port_available"] is True
    assert check["assets"]["mode"] == "INSTALLED_RESOURCES"
    assert check["product_status"] == "LICENSED"


def test_prototype_endpoint_reauthorizes_every_request(monkeypatch) -> None:
    runtime = FakeRuntime()
    returned = {
        "status": "VALIDATED_PROTOTYPE",
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
    monkeypatch.setattr(workspace, "run_client_request", lambda payload: {**returned, "request_id": payload["request_id"]})

    request = {
        "schema": REQUEST_SCHEMA,
        "request_id": "req-1",
        "candidate": {"candidate_id": "candidate-1"},
    }
    result = workspace.process_prototype_request(request, runtime)  # type: ignore[arg-type]

    assert runtime.calls == [{
        "tool": "gremlin_prototype",
        "feature": "PROTOTYPE_PIPELINE",
    }]
    assert result["ui_schema"] == workspace.WORKSPACE_SCHEMA
    assert result["response"]["request_id"] == "req-1"
    assert result["authority"] == {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def test_workspace_system_payload_is_safe_exact_product_dashboard() -> None:
    payload = workspace.system_payload(FakeRuntime())  # type: ignore[arg-type]
    assert payload["schema"] == workspace.SYSTEM_SCHEMA
    assert payload["surface"] == "product"
    assert payload["product"]["status"] == "LICENSED"
    assert payload["product"]["license"]["edition"] == "RESEARCH"
    assert payload["product"]["profile"] == {
        "configured": True,
        "label": "Test Customer Profile",
    }
    assert payload["mcp"]["tool_count"] == 29
    assert payload["mcp"]["capability_contract"] == "EXACT_PRODUCT_REGISTRY_V0_1"
    assert payload["bestiary"]["species_count"] == 18
    assert len(payload["bestiary"]["species"]) == 18
    assert {row["name"] for row in payload["bestiary"]["species"]} >= {
        "HUMMINGBIRD", "OCTOPUS", "SPIDER", "BELZEBUB", "FERRET", "GREMLIN"
    }
    serialized = json.dumps(payload, sort_keys=True)
    assert "TEST-SECRET-ID" not in serialized
    assert "test-client-secret-id" not in serialized
    assert payload["authority"]["production_runtime_write"] is False
    assert payload["authority"]["execution_admitted"] is False
    assert payload["authority"]["canon_allowed"] is False


def test_reference_dashboard_uses_reference_registry_without_product_identity() -> None:
    payload = workspace.system_payload(surface="reference")
    assert payload["surface"] == "reference"
    assert payload["product"]["status"] == "UNLICENSED_RESEARCH"
    assert payload["mcp"]["tool_count"] == 32
    assert payload["mcp"]["capability_contract"] == "EXACT_REFERENCE_REGISTRY_V0_1"
    assert payload["bestiary"]["species_count"] == 18
    assert payload["product"]["license"]["edition"] is None


def test_workspace_http_surface_has_security_headers_and_blocks_cross_origin(tmp_path, monkeypatch) -> None:
    paths = _paths(tmp_path)
    web_root, example = _stage_assets(paths)
    runtime = FakeRuntime()
    monkeypatch.setattr(
        workspace,
        "run_client_request",
        lambda payload: {
            "status": "VALIDATED_PROTOTYPE",
            "request_id": payload["request_id"],
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        },
    )

    server = workspace.GremlinWorkspaceServer(
        ("127.0.0.1", 0),
        web_root=web_root,
        example_path=example,
        runtime=runtime,  # type: ignore[arg-type]
        instance_id="a" * 32,
        shutdown_token="b" * 48,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    base = f"http://{host}:{port}"

    try:
        with urlopen(f"{base}/api/health", timeout=2.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert response.status == 200
            assert payload["schema"] == workspace.WORKSPACE_SCHEMA
            assert payload["status"] == "READY"
            assert payload["instance_id"] == "a" * 32
            assert response.headers["X-Frame-Options"] == "DENY"
            assert response.headers["Referrer-Policy"] == "no-referrer"
            assert "default-src 'self'" in response.headers["Content-Security-Policy"]

        with urlopen(f"{base}/api/system", timeout=2.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert response.status == 200
            assert payload["schema"] == workspace.SYSTEM_SCHEMA
            assert payload["surface"] == "product"
            assert payload["mcp"]["tool_count"] == 29
            assert payload["bestiary"]["species_count"] == 18
            assert "TEST-SECRET-ID" not in json.dumps(payload)

        body = json.dumps({
            "schema": REQUEST_SCHEMA,
            "request_id": "http-1",
            "candidate": {"candidate_id": "c-1"},
        }).encode("utf-8")
        hostile = Request(
            f"{base}/api/prototype",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Origin": "https://evil.example",
            },
        )
        with pytest.raises(HTTPError) as denied:
            urlopen(hostile, timeout=2.0)
        assert denied.value.code == 403

        allowed = Request(
            f"{base}/api/prototype",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Origin": base,
            },
        )
        with urlopen(allowed, timeout=2.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert response.status == 200
            assert payload["response"]["request_id"] == "http-1"
            assert payload["authority"]["execution_admitted"] is False

        unauthorized_stop = Request(
            f"{base}/api/shutdown",
            data=b"{}",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(HTTPError) as denied_stop:
            urlopen(unauthorized_stop, timeout=2.0)
        assert denied_stop.value.code == 403
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)


def test_workspace_managed_lifecycle_status_and_authenticated_stop(tmp_path) -> None:
    paths = _paths(tmp_path)
    server, thread, token, instance_id = _server(paths)
    host, port = server.server_address[:2]
    state = {
        "schema": workspace.INSTANCE_SCHEMA,
        "instance_id": instance_id,
        "shutdown_token": token,
        "pid": os.getpid(),
        "host": host,
        "port": port,
        "url": f"http://{host}:{port}",
        "started_at": "2026-09-19T00:00:00+00:00",
    }
    workspace._write_private_json(workspace._instance_path(paths), state)

    try:
        status = workspace.workspace_status(paths, host=host, port=port)
        assert status["status"] == "RUNNING"
        assert status["instance_id"] == instance_id
        assert status["can_stop"] is True
        if os.name != "nt":
            mode = stat.S_IMODE(workspace._instance_path(paths).stat().st_mode)
            assert mode & 0o077 == 0

        stopped = workspace.workspace_stop(paths, timeout=2.0)
        assert stopped["status"] == "STOPPED"
        assert stopped["instance_id"] == instance_id
        assert not workspace._instance_path(paths).exists()
        thread.join(timeout=2.0)
        assert not thread.is_alive()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)


def test_workspace_status_marks_unreachable_instance_state_stale(tmp_path) -> None:
    paths = _paths(tmp_path)
    state = {
        "schema": workspace.INSTANCE_SCHEMA,
        "instance_id": "c" * 32,
        "shutdown_token": "d" * 48,
        "pid": 999999,
        "host": "127.0.0.1",
        "port": 65530,
        "url": "http://127.0.0.1:65530",
        "started_at": "2026-09-19T00:00:00+00:00",
    }
    workspace._write_private_json(workspace._instance_path(paths), state)
    status = workspace.workspace_status(paths)
    assert status["status"] == "STALE"
    assert status["can_stop"] is False


def test_workspace_stop_clears_stale_instance_state(tmp_path) -> None:
    paths = _paths(tmp_path)
    state = {
        "schema": workspace.INSTANCE_SCHEMA,
        "instance_id": "e" * 32,
        "shutdown_token": "f" * 48,
        "pid": 999999,
        "host": "127.0.0.1",
        "port": 65529,
        "url": "http://127.0.0.1:65529",
        "started_at": "2026-09-19T00:00:00+00:00",
    }
    workspace._write_private_json(workspace._instance_path(paths), state)
    stopped = workspace.workspace_stop(paths)
    assert stopped["status"] == "STALE_CLEARED"
    assert stopped["can_stop"] is False
    assert not workspace._instance_path(paths).exists()
