from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

import gremlin_mcp.workspace as workspace
from gremlin_mcp.install.paths import resolve_paths
from gremlin_mcp.product import ProductAuthorizationError
from tools.gremlin_client_protocol_v01 import REQUEST_SCHEMA


class FakeRuntime:
    def __init__(
        self,
        *,
        licensed: bool = True,
        prototype_allowed: bool = True,
        denied_tools: set[str] | None = None,
    ) -> None:
        self.licensed = licensed
        self.prototype_allowed = prototype_allowed
        self.denied_tools = set(denied_tools or set())
        self.calls: list[dict[str, object]] = []

    def status(self) -> dict[str, object]:
        if self.licensed:
            return {"status": "LICENSED"}
        return {"status": "BLOCKED", "reason": "LICENSE_REQUIRED"}

    def authorize(self, **kwargs) -> None:
        self.calls.append(dict(kwargs))
        tool = kwargs.get("tool")
        if isinstance(tool, str) and tool in self.denied_tools:
            raise ProductAuthorizationError(f"TOOL_NOT_ALLOWED_BY_PROFILE:{tool}")
        if not self.prototype_allowed and kwargs.get("feature") == "PROTOTYPE_PIPELINE":
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
    monkeypatch.setattr(workspace, "_probe_existing_workspace", lambda _host, _port: False)
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


def test_workspace_status_and_bestiary_reauthorize_read_only_surfaces() -> None:
    runtime = FakeRuntime()

    status = workspace.workspace_status_payload(runtime)  # type: ignore[arg-type]
    bestiary = workspace.workspace_bestiary_payload(runtime)  # type: ignore[arg-type]

    assert status["status"] == "READY"
    assert status["product"]["status"] == "LICENSED"
    assert status["capabilities"]["surface"] == "product"
    assert status["capabilities"]["tool_count"] == 29
    assert bestiary["status"] == "READY"
    assert bestiary["species_count"] == 18
    assert len(bestiary["species"]) == 18
    assert runtime.calls == [
        {"tool": "gremlin_status"},
        {"tool": "gremlin_bestiary"},
    ]


def test_workspace_read_only_introspection_respects_profile_denial() -> None:
    runtime = FakeRuntime(denied_tools={"gremlin_bestiary"})
    with pytest.raises(ProductAuthorizationError, match="TOOL_NOT_ALLOWED_BY_PROFILE:gremlin_bestiary"):
        workspace.workspace_bestiary_payload(runtime)  # type: ignore[arg-type]


def test_workspace_error_payload_reuses_shared_mcp_contract() -> None:
    payload = workspace.workspace_error_payload(
        ProductAuthorizationError("FEATURE_NOT_ENTITLED:PROTOTYPE_PIPELINE"),
        tool="gremlin_prototype",
        request_id="workspace-req-1",
    )
    contract = payload["error_contract"]
    assert payload["schema"] == workspace.WORKSPACE_SCHEMA
    assert payload["status"] == "ERROR"
    assert payload["request_id"] == "workspace-req-1"
    assert contract["schema"] == "GREMLIN_MCP_ERROR_V0_1"
    assert contract["tool"] == "gremlin_prototype"
    assert contract["error_code"] == "FEATURE_NOT_ENTITLED"
    assert contract["category"] == "AUTHORIZATION"
    assert contract["retryable"] is False
    assert contract["request_id"] == "workspace-req-1"
    assert "entitled" in contract["user_action"]
    assert contract["authority"]["execution_admitted"] is False


def test_workspace_internal_error_payload_is_sanitized_and_actionable() -> None:
    payload = workspace.workspace_error_payload(
        RuntimeError("WORKSPACE_INTERNAL_ERROR"),
        tool="gremlin_status",
    )
    contract = payload["error_contract"]
    assert contract["error_code"] == "WORKSPACE_INTERNAL_ERROR"
    assert contract["category"] == "RUNTIME"
    assert "support report" in contract["user_action"]
    assert contract["retryable"] is False


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
            assert response.headers["X-Frame-Options"] == "DENY"
            assert response.headers["Referrer-Policy"] == "no-referrer"
            assert "default-src 'self'" in response.headers["Content-Security-Policy"]

        with urlopen(f"{base}/api/status", timeout=2.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert response.status == 200
            assert payload["capabilities"]["surface"] == "product"
            assert payload["capabilities"]["tool_count"] == 29

        with urlopen(f"{base}/api/bestiary", timeout=2.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert response.status == 200
            assert payload["species_count"] == 18
            assert len(payload["species"]) == 18

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
        denied_payload = json.loads(denied.value.read().decode("utf-8"))
        denied_contract = denied_payload["error_contract"]
        assert denied_contract["schema"] == "GREMLIN_MCP_ERROR_V0_1"
        assert denied_contract["tool"] == "gremlin_prototype"
        assert denied_contract["error_code"] == "CROSS_ORIGIN_WORKSPACE_REQUEST"
        assert denied_contract["category"] == "AUTHORIZATION"
        assert denied_contract["retryable"] is False
        assert "local GREMLIN Workspace origin" in denied_contract["user_action"]

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
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)
