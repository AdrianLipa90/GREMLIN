from __future__ import annotations

import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from gremlin_mcp.product.gate import ProductAuthorizationError, ProductRuntime
from gremlin_mcp.product.license import issue_license


def test_present_profile_empty_allowlists_deny_tools_species_and_providers(tmp_path) -> None:
    private = Ed25519PrivateKey.generate()
    public_path = tmp_path / "public.pem"
    public_path.write_bytes(
        private.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    license_payload = {
        "schema": "GREMLIN_LICENSE_V0_1",
        "license_id": "GRM-STRICT-0001",
        "product": "GREMLIN",
        "edition": "COMMERCIAL",
        "customer": "strict-test",
        "issued_at": "2026-08-30",
        "not_before": "2026-08-30",
        "expires_at": "2027-08-30",
        "updates_until": "2027-08-30",
        "seats": 1,
        "devices": 1,
        "features": ["MCP_STDIO", "INTERNET_RESEARCH"],
        "limits": {"max_workers": 4, "max_sources": 24},
        "usage": {"commercial_use": True, "production_use": False, "hosted_service": False},
        "metadata": {},
    }
    license_path = tmp_path / "license.json"
    license_path.write_text(json.dumps(issue_license(license_payload, private)), encoding="utf-8")
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "schema": "GREMLIN_CLIENT_PROFILE_V0_1",
                "client_id": "strict-client",
                "label": "Strict client",
                "tools": [],
                "species": [],
                "providers": [],
                "languages": ["en"],
                "internet_access": True,
                "custom_workers": False,
                "limits": {"max_workers": 4, "max_sources": 24},
                "metadata": {},
            }
        ),
        encoding="utf-8",
    )
    runtime = ProductRuntime.from_paths(
        license_path=license_path,
        public_key_path=public_path,
        profile_path=profile_path,
        require_license=True,
    )
    assert runtime.status()["status"] == "LICENSED"
    runtime.authorize_feature("MCP_STDIO")

    with pytest.raises(ProductAuthorizationError, match="TOOL_NOT_ALLOWED_BY_PROFILE"):
        runtime.authorize(tool="gremlin_route")
    with pytest.raises(ProductAuthorizationError, match="SPECIES_NOT_ALLOWED_BY_PROFILE"):
        runtime.authorize(tool=None, species="OWL")
    with pytest.raises(ProductAuthorizationError, match="PROVIDER_NOT_ALLOWED_BY_PROFILE"):
        runtime.authorize(tool=None, provider="arxiv")
