from __future__ import annotations

import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import gremlin_mcp.product_server as product_server
from gremlin_mcp.product.gate import ProductAuthorizationError
from gremlin_mcp.product.license import issue_license


def _configure(tmp_path, *, species: list[str]) -> None:
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
        "license_id": "GRM-PREFLIGHT-0001",
        "product": "GREMLIN",
        "edition": "COMMERCIAL",
        "customer": "preflight-test",
        "issued_at": "2026-08-30",
        "not_before": "2026-08-30",
        "expires_at": "2027-08-30",
        "updates_until": "2027-08-30",
        "seats": 1,
        "devices": 1,
        "features": ["MCP_STDIO", "RESEARCH_EXECUTE", "INTERNET_RESEARCH"],
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
                "client_id": "preflight-client",
                "label": "Preflight client",
                "tools": ["gremlin_research", "gremlin_research_execute"],
                "species": species,
                "providers": ["crossref"],
                "languages": ["en"],
                "internet_access": True,
                "custom_workers": False,
                "limits": {"max_workers": 4, "max_sources": 24},
                "metadata": {},
            }
        ),
        encoding="utf-8",
    )
    runtime = product_server.configure_product(
        license_path=str(license_path),
        public_key_path=str(public_path),
        profile_path=str(profile_path),
        require_license=True,
    )
    assert runtime.status()["status"] == "LICENSED"


def test_high_level_preflight_blocks_disallowed_mole_before_execution(tmp_path) -> None:
    _configure(tmp_path, species=["OWL", "BELZEBUB"])
    with pytest.raises(ProductAuthorizationError, match="SPECIES_NOT_ALLOWED_BY_PROFILE:MOLE"):
        product_server._authorize_research_plan(
            "gremlin_research_execute",
            "Review the evidence then derive an equation and mechanism.",
            max_species=4,
            synthesis=True,
        )


def test_high_level_preflight_accepts_allowed_plan_and_synthesis(tmp_path) -> None:
    _configure(tmp_path, species=["OWL", "MOLE", "BELZEBUB"])
    plan = product_server._authorize_research_plan(
        "gremlin_research_execute",
        "Review the evidence then derive an equation and mechanism.",
        max_species=4,
        synthesis=True,
    )
    assert "OWL" in plan["species_union"]
    assert "MOLE" in plan["species_union"]
