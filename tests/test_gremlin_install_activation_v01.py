from __future__ import annotations

from pathlib import Path

import pytest

from gremlin_mcp.install.integrations import gremlin_stdio_entry
from gremlin_mcp.install.license_activation import activate_license_key, installed_license_status
from gremlin_mcp.install.paths import GremlinPaths
from gremlin_mcp.install.readiness import evaluate_readiness
from gremlin_mcp.product.keycodec import encode_license_key
from gremlin_mcp.product.license import LicenseError, generate_keypair, issue_license, load_private_key


def make_paths(tmp_path: Path) -> GremlinPaths:
    config = tmp_path / "config"
    state = tmp_path / "state"
    data = tmp_path / "data"
    resources = tmp_path / "resources"
    install = tmp_path / "install"
    return GremlinPaths(
        platform="linux",
        config_dir=str(config),
        state_dir=str(state),
        cache_dir=str(tmp_path / "cache"),
        data_dir=str(data),
        logs_dir=str(state / "logs"),
        diagnostics_dir=str(data / "diagnostics"),
        config_file=str(config / "config.toml"),
        license_file=str(config / "license.json"),
        client_profile_file=str(config / "client-profile.json"),
        integrations_file=str(config / "integrations.json"),
        state_db=str(state / "gremlin.sqlite3"),
        machine_policy_file=str(tmp_path / "policy.toml"),
        install_root=str(install),
        shared_data_root=str(resources),
    )


def issue_test_key(tmp_path: Path, paths: GremlinPaths) -> str:
    private_pem, public_pem, _ = generate_keypair()
    private_path = tmp_path / "issuer-private.pem"
    public_path = Path(paths.shared_data_root) / "issuer-public.pem"
    private_path.write_bytes(private_pem)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_bytes(public_pem)
    payload = {
        "schema": "GREMLIN_LICENSE_V0_1",
        "license_id": "LIC-EARLY-ACCESS-001",
        "product": "GREMLIN",
        "edition": "COMMERCIAL",
        "customer": "customer-001",
        "issued_at": "2026-01-01",
        "not_before": "2026-01-01",
        "expires_at": "2030-12-31",
        "updates_until": "2030-12-31",
        "seats": 1,
        "devices": 2,
        "features": ["MCP_STDIO", "PERSISTENT_STATE"],
        "limits": {"max_workers": 4, "max_sources": 24},
        "usage": {"commercial_use": True, "production_use": False, "hosted_service": False},
        "metadata": {"issuer": "Intention Lab"},
    }
    envelope = issue_license(payload, load_private_key(private_path))
    return encode_license_key(envelope)


def test_grm1_activation_verifies_and_persists_license(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    key = issue_test_key(tmp_path, paths)
    result = activate_license_key(key, paths)
    assert result.status == "ACTIVE"
    assert result.license_id == "LIC-EARLY-ACCESS-001"
    assert Path(paths.license_file).is_file()
    status = installed_license_status(paths)
    assert status["status"] == "ACTIVE"
    assert status["license"]["license_id"] == "LIC-EARLY-ACCESS-001"


def test_tampered_customer_key_never_replaces_installed_license(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    key = issue_test_key(tmp_path, paths)
    activate_license_key(key, paths)
    before = Path(paths.license_file).read_bytes()
    tampered = key[:-1] + ("A" if key[-1] != "A" else "B")
    with pytest.raises(LicenseError):
        activate_license_key(tampered, paths)
    assert Path(paths.license_file).read_bytes() == before


def test_missing_profile_is_not_advertised_to_mcp_client(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    entry = gremlin_stdio_entry(paths)
    assert "GREMLIN_CLIENT_PROFILE" not in entry["env"]
    profile = Path(paths.client_profile_file)
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_text("{}", encoding="utf-8")
    entry_with_profile = gremlin_stdio_entry(paths)
    assert entry_with_profile["env"]["GREMLIN_CLIENT_PROFILE"] == paths.client_profile_file


def test_readiness_reaches_ready_with_license_runtime_and_connected_provider(tmp_path: Path, monkeypatch) -> None:
    paths = make_paths(tmp_path)
    key = issue_test_key(tmp_path, paths)
    activate_license_key(key, paths)
    runtime = tmp_path / "gremlin-product-mcp"
    runtime.write_text("runtime", encoding="utf-8")

    monkeypatch.setattr("gremlin_mcp.install.readiness.gremlin_stdio_entry", lambda _paths: {
        "command": str(runtime), "args": ["--transport", "stdio"], "env": {}
    })
    monkeypatch.setattr("gremlin_mcp.install.readiness.list_providers", lambda _paths: {
        "providers": [{"provider_id": "codex", "detected": True, "connected": True}]
    })
    ready = evaluate_readiness(paths)
    assert ready["status"] == "READY"
    assert ready["providers"]["connected_ids"] == ["codex"]
    assert ready["actions"] == []
