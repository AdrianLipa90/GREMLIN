from __future__ import annotations

import json
from pathlib import Path

import pytest

from gremlin_mcp.install.license_activation import activate_license_key
from gremlin_mcp.install.paths import GremlinPaths
from gremlin_mcp.install.profile_activation import import_client_profile, installed_profile_status
from gremlin_mcp.product import ProductRuntime
from gremlin_mcp.product.keycodec import encode_license_key
from gremlin_mcp.product.license import generate_keypair, issue_license, load_private_key
from gremlin_mcp.product.profile import ClientProfileError


def make_paths(tmp_path: Path) -> GremlinPaths:
    return GremlinPaths(
        platform="linux",
        config_dir=str(tmp_path / "config"),
        state_dir=str(tmp_path / "state"),
        cache_dir=str(tmp_path / "cache"),
        data_dir=str(tmp_path / "data"),
        logs_dir=str(tmp_path / "state" / "logs"),
        diagnostics_dir=str(tmp_path / "data" / "diagnostics"),
        config_file=str(tmp_path / "config" / "config.toml"),
        license_file=str(tmp_path / "config" / "license.json"),
        client_profile_file=str(tmp_path / "config" / "client-profile.json"),
        integrations_file=str(tmp_path / "config" / "integrations.json"),
        state_db=str(tmp_path / "state" / "gremlin.sqlite3"),
        machine_policy_file=str(tmp_path / "policy.toml"),
        install_root=str(tmp_path / "install"),
        shared_data_root=str(tmp_path / "resources"),
    )


def activate_required_profile_license(tmp_path: Path, paths: GremlinPaths) -> None:
    private_pem, public_pem, _ = generate_keypair()
    private_path = tmp_path / "issuer-private.pem"
    public_path = Path(paths.shared_data_root) / "issuer-public.pem"
    private_path.write_bytes(private_pem)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_bytes(public_pem)
    envelope = issue_license(
        {
            "schema": "GREMLIN_LICENSE_V0_1",
            "license_id": "LIC-PROFILE-001",
            "product": "GREMLIN",
            "edition": "COMMERCIAL",
            "customer": "customer-profile-001",
            "issued_at": "2026-01-01",
            "not_before": "2026-01-01",
            "expires_at": "2030-12-31",
            "updates_until": "2030-12-31",
            "seats": 1,
            "devices": 1,
            "features": ["MCP_STDIO", "PERSISTENT_STATE"],
            "limits": {"max_workers": 4, "max_sources": 24},
            "usage": {"commercial_use": True, "production_use": False, "hosted_service": False},
            "metadata": {"profile_required": True},
        },
        load_private_key(private_path),
    )
    activate_license_key(encode_license_key(envelope), paths)


def valid_profile() -> dict:
    return {
        "schema": "GREMLIN_CLIENT_PROFILE_V0_1",
        "client_id": "customer-profile-001",
        "label": "Early Access Customer",
        "tools": ["gremlin_status"],
        "species": ["SPIDER"],
        "providers": ["crossref"],
        "languages": ["en"],
        "internet_access": False,
        "custom_workers": False,
        "limits": {"max_workers": 2, "max_sources": 12},
        "metadata": {"channel": "early-access"},
    }


def test_required_profile_hot_plugs_without_provider_reconfiguration(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    activate_required_profile_license(tmp_path, paths)
    before = ProductRuntime.from_paths(
        license_path=paths.license_file,
        public_key_path=Path(paths.shared_data_root) / "issuer-public.pem",
        profile_path=paths.client_profile_file,
    )
    assert before.status()["status"] == "BLOCKED"

    source = tmp_path / "customer-profile.json"
    source.write_text(json.dumps(valid_profile()), encoding="utf-8")
    result = import_client_profile(source, paths)
    assert result["status"] == "ACTIVE"

    after = ProductRuntime.from_paths(
        license_path=paths.license_file,
        public_key_path=Path(paths.shared_data_root) / "issuer-public.pem",
        profile_path=paths.client_profile_file,
    )
    status = after.status()
    assert status["status"] == "LICENSED"
    assert status["profile"]["client_id"] == "customer-profile-001"
    assert installed_profile_status(paths)["status"] == "ACTIVE"


def test_profile_cannot_elevate_signed_license_limits(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    activate_required_profile_license(tmp_path, paths)
    profile = valid_profile()
    profile["limits"]["max_workers"] = 999
    source = tmp_path / "bad-profile.json"
    source.write_text(json.dumps(profile), encoding="utf-8")
    with pytest.raises(ClientProfileError):
        import_client_profile(source, paths)
    assert not Path(paths.client_profile_file).exists()
