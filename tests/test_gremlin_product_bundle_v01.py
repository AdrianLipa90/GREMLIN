from __future__ import annotations

import json
import zipfile

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from gremlin_mcp.product.bundle import build_customer_bundle
from gremlin_mcp.product.license import issue_license


def _fixtures(tmp_path):
    private = Ed25519PrivateKey.generate()
    public_path = tmp_path / "issuer-public.pem"
    public_path.write_bytes(
        private.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    payload = {
        "schema": "GREMLIN_LICENSE_V0_1",
        "license_id": "GRM-BUNDLE-0001",
        "product": "GREMLIN",
        "edition": "COMMERCIAL",
        "customer": "bundle-test",
        "issued_at": "2026-08-30",
        "not_before": "2026-08-30",
        "expires_at": "2027-08-30",
        "updates_until": "2027-08-30",
        "seats": 1,
        "devices": 2,
        "features": ["MCP_STDIO", "INTERNET_RESEARCH", "RESEARCH_EXECUTE"],
        "limits": {"max_workers": 4, "max_sources": 24},
        "usage": {"commercial_use": True, "production_use": False, "hosted_service": False},
        "metadata": {},
    }
    license_path = tmp_path / "license.json"
    license_path.write_text(json.dumps(issue_license(payload, private)), encoding="utf-8")
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "schema": "GREMLIN_CLIENT_PROFILE_V0_1",
                "client_id": "bundle-client",
                "label": "Bundle client",
                "tools": ["gremlin_research"],
                "species": ["OWL"],
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
    distribution = tmp_path / "gremlin-mcp.whl"
    distribution.write_bytes(b"fake-wheel-for-bundle-test")
    return private, public_path, license_path, profile_path, distribution


def test_customer_bundle_contains_validated_manifest_and_no_private_key(tmp_path) -> None:
    _, public_path, license_path, profile_path, distribution = _fixtures(tmp_path)
    benchmark = tmp_path / "benchmark.pdf"
    benchmark.write_bytes(b"benchmark")
    out = tmp_path / "customer.zip"
    result = build_customer_bundle(
        distribution_path=distribution,
        public_key_path=public_path,
        profile_path=profile_path,
        license_path=license_path,
        extra_paths=[benchmark],
        output_path=out,
    )
    assert result["status"] == "CREATED"
    assert result["license_id"] == "GRM-BUNDLE-0001"
    with zipfile.ZipFile(out) as archive:
        names = set(archive.namelist())
        assert "manifest.json" in names
        assert "README.txt" in names
        assert "issuer-public.pem" in names
        assert "license.json" in names
        assert "client-profile.json" in names
        assert "mcp-stdio-config.example.json" in names
        assert "extras/benchmark.pdf" in names
        assert not any("private" in name.casefold() for name in names)
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["bundle_commitment"] == result["bundle_commitment"]
        assert manifest["client_id"] == "bundle-client"


def test_customer_bundle_rejects_private_key_extra(tmp_path) -> None:
    private, public_path, license_path, profile_path, distribution = _fixtures(tmp_path)
    private_extra = tmp_path / "issuer-private.pem"
    private_extra.write_bytes(
        private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    with pytest.raises(ValueError, match="private key"):
        build_customer_bundle(
            distribution_path=distribution,
            public_key_path=public_path,
            profile_path=profile_path,
            license_path=license_path,
            extra_paths=[private_extra],
            output_path=tmp_path / "blocked.zip",
        )
