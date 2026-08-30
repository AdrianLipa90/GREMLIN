from __future__ import annotations

import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from gremlin_mcp.product import ProductRuntime
from gremlin_mcp.product.license import issue_license
from gremlin_mcp.product_server import _assert_local_http_bind


def _runtime(tmp_path) -> ProductRuntime:
    private = Ed25519PrivateKey.generate()
    public_path = tmp_path / "public.pem"
    public_path.write_bytes(
        private.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    payload = {
        "schema": "GREMLIN_LICENSE_V0_1",
        "license_id": "GRM-TRANSPORT-0001",
        "product": "GREMLIN",
        "edition": "COMMERCIAL",
        "customer": "transport-test",
        "issued_at": "2026-08-30",
        "not_before": "2026-08-30",
        "expires_at": "2027-08-30",
        "updates_until": "2027-08-30",
        "seats": 1,
        "devices": 1,
        "features": ["MCP_STDIO", "MCP_HTTP", "PERSISTENT_STATE"],
        "limits": {"max_workers": 4, "max_sources": 24},
        "usage": {"commercial_use": True, "production_use": False, "hosted_service": False},
        "metadata": {},
    }
    license_path = tmp_path / "license.json"
    license_path.write_text(json.dumps(issue_license(payload, private)), encoding="utf-8")
    profile_path = tmp_path / "client.json"
    profile_path.write_text(
        json.dumps(
            {
                "schema": "GREMLIN_CLIENT_PROFILE_V0_1",
                "client_id": "transport-client",
                "label": "Transport client",
                "tools": ["gremlin_route"],
                "species": [],
                "providers": [],
                "languages": ["en"],
                "internet_access": False,
                "custom_workers": False,
                "limits": {"max_workers": 4, "max_sources": 24},
                "metadata": {},
            }
        ),
        encoding="utf-8",
    )
    return ProductRuntime.from_paths(
        license_path=license_path,
        public_key_path=public_path,
        profile_path=profile_path,
        require_license=True,
    )


def test_internal_feature_gate_is_not_blocked_by_client_tool_allowlist(tmp_path) -> None:
    runtime = _runtime(tmp_path)
    assert runtime.status()["status"] == "LICENSED"
    runtime.authorize_feature("PERSISTENT_STATE")
    runtime.authorize_feature("MCP_STDIO")
    runtime.authorize_feature("MCP_HTTP")


def test_http_v01_accepts_loopback_only() -> None:
    for host in ("localhost", "127.0.0.1", "127.12.34.56", "::1"):
        _assert_local_http_bind(host)

    for host in ("0.0.0.0", "192.168.1.50", "10.0.0.2", "8.8.8.8", "example.com"):
        with pytest.raises(RuntimeError, match="REMOTE_HTTP_AUTH_REQUIRED"):
            _assert_local_http_bind(host)
