from __future__ import annotations

import os
from pathlib import Path
import stat

import pytest

import gremlin_mcp.install.license_activation as license_activation_module
from gremlin_mcp.install.integrations import gremlin_stdio_entry
from gremlin_mcp.install.license_activation import activate_license_key, installed_license_status
from gremlin_mcp.install.paths import GremlinPaths
from gremlin_mcp.install.readiness import evaluate_readiness
from gremlin_mcp.product import ProductRuntime
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


def issue_test_key(tmp_path: Path, paths: GremlinPaths, *, profile_required: bool = False) -> str:
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
        "metadata": {"issuer": "Intention Lab", "profile_required": profile_required},
    }
    envelope = issue_license(payload, load_private_key(private_path))
    return encode_license_key(envelope)


def test_grm1_activation_verifies_and_persists_license(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    key = issue_test_key(tmp_path, paths)
    result = activate_license_key(key, paths)
    assert result.status == "ACTIVE"
    assert result.license_id == "LIC-EARLY-ACCESS-001"
    target = Path(paths.license_file)
    assert target.is_file()
    if os.name != "nt":
        assert stat.S_IMODE(target.stat().st_mode) & 0o077 == 0
    status = installed_license_status(paths)
    assert status["status"] == "ACTIVE"
    assert status["license"]["license_id"] == "LIC-EARLY-ACCESS-001"


def test_license_activation_fails_loudly_if_temp_permissions_cannot_be_set(tmp_path: Path, monkeypatch) -> None:
    if os.name == "nt":
        pytest.skip("POSIX permission hardening is not used on Windows")
    paths = make_paths(tmp_path)
    key = issue_test_key(tmp_path, paths)

    def fail_fchmod(_fd: int, _mode: int) -> None:
        raise OSError("simulated fchmod failure")

    monkeypatch.setattr(license_activation_module.os, "fchmod", fail_fchmod)
    with pytest.raises(OSError, match="simulated fchmod failure"):
        activate_license_key(key, paths)
    assert not Path(paths.license_file).exists()
    assert not list(Path(paths.config_dir).glob(".license.json.*.tmp"))


def test_tampered_customer_key_never_replaces_installed_license(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    key = issue_test_key(tmp_path, paths)
    activate_license_key(key, paths)
    before = Path(paths.license_file).read_bytes()
    tampered = key[:-1] + ("A" if key[-1] != "A" else "B")
    with pytest.raises(LicenseError):
        activate_license_key(tampered, paths)
    assert Path(paths.license_file).read_bytes() == before


def test_profile_path_is_stable_and_optional_by_default(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    key = issue_test_key(tmp_path, paths)
    activate_license_key(key, paths)
    entry = gremlin_stdio_entry(paths)
    assert entry["env"]["GREMLIN_CLIENT_PROFILE"] == paths.client_profile_file
    runtime = ProductRuntime.from_paths(
        license_path=paths.license_file,
        public_key_path=Path(paths.shared_data_root) / "issuer-public.pem",
        profile_path=paths.client_profile_file,
    )
    assert runtime.status()["status"] == "LICENSED"
    assert runtime.status()["profile"] is None


def test_signed_profile_required_flag_blocks_missing_profile(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    key = issue_test_key(tmp_path, paths, profile_required=True)
    activate_license_key(key, paths)
    runtime = ProductRuntime.from_paths(
        license_path=paths.license_file,
        public_key_path=Path(paths.shared_data_root) / "issuer-public.pem",
        profile_path=paths.client_profile_file,
    )
    status = runtime.status()
    assert status["status"] == "BLOCKED"
    assert status["reason"] == "required client profile is missing"


def _runtime_ready_setup(tmp_path: Path, monkeypatch) -> GremlinPaths:
    paths = make_paths(tmp_path)
    key = issue_test_key(tmp_path, paths)
    activate_license_key(key, paths)
    runtime = tmp_path / "gremlin-product-mcp"
    runtime.write_text("runtime", encoding="utf-8")
    if os.name != "nt":
        runtime.chmod(0o755)
    monkeypatch.setattr("gremlin_mcp.install.readiness.gremlin_stdio_entry", lambda _paths: {
        "command": str(runtime), "args": ["--transport", "stdio"], "env": {}
    })
    return paths


def test_readiness_reaches_ready_with_license_runtime_and_verified_provider(tmp_path: Path, monkeypatch) -> None:
    paths = _runtime_ready_setup(tmp_path, monkeypatch)
    monkeypatch.setattr("gremlin_mcp.install.readiness.list_providers", lambda _paths: {
        "providers": [{
            "provider_id": "opencode",
            "detected": True,
            "connected": True,
            "connection_status": "CONNECTED",
        }]
    })
    ready = evaluate_readiness(paths)
    assert ready["status"] == "READY"
    assert ready["providers"]["connected_ids"] == ["opencode"]
    assert ready["actions"] == []


def test_readiness_rejects_registered_but_unverified_provider(tmp_path: Path, monkeypatch) -> None:
    paths = _runtime_ready_setup(tmp_path, monkeypatch)
    monkeypatch.setattr("gremlin_mcp.install.readiness.list_providers", lambda _paths: {
        "providers": [{
            "provider_id": "codex",
            "detected": True,
            "connected": False,
            "connection_status": "REGISTERED_UNVERIFIED",
        }]
    })
    ready = evaluate_readiness(paths)
    assert ready["status"] == "ACTION_REQUIRED"
    assert ready["providers"]["connected"] == 0
    assert ready["providers"]["unverified_ids"] == ["codex"]
    assert "Verify a live GREMLIN MCP connection in one detected AI client" in ready["actions"]


def test_readiness_fails_loudly_on_non_boolean_provider_flags(tmp_path: Path, monkeypatch) -> None:
    paths = _runtime_ready_setup(tmp_path, monkeypatch)
    monkeypatch.setattr("gremlin_mcp.install.readiness.list_providers", lambda _paths: {
        "providers": [{
            "provider_id": "bad",
            "detected": "false",
            "connected": False,
            "connection_status": "NOT_DETECTED",
        }]
    })
    with pytest.raises(RuntimeError, match="non-boolean detected"):
        evaluate_readiness(paths)


def test_readiness_rejects_inconsistent_connected_status(tmp_path: Path, monkeypatch) -> None:
    paths = _runtime_ready_setup(tmp_path, monkeypatch)
    monkeypatch.setattr("gremlin_mcp.install.readiness.list_providers", lambda _paths: {
        "providers": [{
            "provider_id": "opencode",
            "detected": True,
            "connected": True,
            "connection_status": "REGISTERED_UNVERIFIED",
        }]
    })
    with pytest.raises(RuntimeError, match="inconsistent connected/connection_status"):
        evaluate_readiness(paths)


def test_readiness_rejects_duplicate_provider_identity(tmp_path: Path, monkeypatch) -> None:
    paths = _runtime_ready_setup(tmp_path, monkeypatch)
    monkeypatch.setattr("gremlin_mcp.install.readiness.list_providers", lambda _paths: {
        "providers": [
            {"provider_id": "codex", "detected": True, "connected": False, "connection_status": "NOT_CONNECTED"},
            {"provider_id": "codex", "detected": True, "connected": False, "connection_status": "NOT_CONNECTED"},
        ]
    })
    with pytest.raises(RuntimeError, match="duplicate provider_id"):
        evaluate_readiness(paths)


def test_readiness_does_not_treat_non_executable_file_as_runtime(tmp_path: Path, monkeypatch) -> None:
    if os.name == "nt":
        pytest.skip("POSIX execute-bit readiness check is not used on Windows")
    paths = make_paths(tmp_path)
    key = issue_test_key(tmp_path, paths)
    activate_license_key(key, paths)
    runtime = tmp_path / "gremlin-product-mcp"
    runtime.write_text("not executable", encoding="utf-8")
    runtime.chmod(0o644)
    monkeypatch.setattr("gremlin_mcp.install.readiness.gremlin_stdio_entry", lambda _paths: {
        "command": str(runtime), "args": ["--transport", "stdio"], "env": {}
    })
    monkeypatch.setattr("gremlin_mcp.install.readiness.list_providers", lambda _paths: {
        "providers": [{
            "provider_id": "opencode",
            "detected": True,
            "connected": True,
            "connection_status": "CONNECTED",
        }]
    })
    ready = evaluate_readiness(paths)
    assert ready["status"] == "ACTION_REQUIRED"
    assert ready["runtime"]["available"] is False
    assert "Repair the GREMLIN runtime installation" in ready["actions"]
