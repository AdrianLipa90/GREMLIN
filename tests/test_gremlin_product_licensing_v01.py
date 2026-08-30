from __future__ import annotations

import asyncio
from datetime import date
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from gremlin_mcp.product.gate import ProductAuthorizationError, ProductRuntime
from gremlin_mcp.product.license import LicenseError, issue_license, verify_license
from gremlin_mcp.product.profile import ClientProfileError, validate_profile_against_license


def _payload(**overrides):
    payload = {
        "schema": "GREMLIN_LICENSE_V0_1",
        "license_id": "GRM-TEST-0001",
        "product": "GREMLIN",
        "edition": "COMMERCIAL",
        "customer": "test-customer",
        "issued_at": "2026-08-30",
        "not_before": "2026-08-30",
        "expires_at": "2027-08-30",
        "updates_until": "2027-08-30",
        "seats": 5,
        "devices": 10,
        "features": [
            "MCP_STDIO",
            "MCP_HTTP",
            "INTERNET_RESEARCH",
            "RESEARCH_EXECUTE",
            "WORKER_ORCHESTRATION",
            "CUSTOM_WORKERS",
            "PERSISTENT_STATE",
            "GUARDED_RESEARCH",
        ],
        "limits": {"max_workers": 8, "max_sources": 24},
        "usage": {"commercial_use": True, "production_use": True, "hosted_service": False},
        "metadata": {},
    }
    payload.update(overrides)
    return payload


def _profile(**overrides):
    profile = {
        "schema": "GREMLIN_CLIENT_PROFILE_V0_1",
        "client_id": "client-a",
        "label": "Client A",
        "tools": ["gremlin_route", "gremlin_research", "gremlin_auto_fanout"],
        "species": ["OWL", "HOUND", "SPIDER", "MOLE"],
        "providers": ["crossref", "arxiv"],
        "languages": ["en"],
        "internet_access": True,
        "custom_workers": False,
        "limits": {"max_workers": 4, "max_sources": 12},
        "metadata": {},
    }
    profile.update(overrides)
    return profile


def _write_runtime_files(tmp_path, *, profile=None, payload=None):
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    public_path = tmp_path / "issuer-public.pem"
    public_path.write_bytes(
        public.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    envelope = issue_license(payload or _payload(), private)
    license_path = tmp_path / "license.json"
    license_path.write_text(json.dumps(envelope), encoding="utf-8")
    profile_path = None
    if profile is not None:
        profile_path = tmp_path / "client.json"
        profile_path.write_text(json.dumps(profile), encoding="utf-8")
    return license_path, public_path, profile_path


def test_signed_license_verifies_and_tamper_fails() -> None:
    private = Ed25519PrivateKey.generate()
    envelope = issue_license(_payload(), private)
    verified = verify_license(envelope, private.public_key(), today=date(2026, 8, 30))
    assert verified["edition"] == "COMMERCIAL"
    assert verified["limits"]["max_workers"] == 8

    tampered = json.loads(json.dumps(envelope))
    tampered["payload"]["limits"]["max_workers"] = 8000
    with pytest.raises(LicenseError, match="signature is invalid"):
        verify_license(tampered, private.public_key(), today=date(2026, 8, 30))


def test_expired_license_fails_closed() -> None:
    private = Ed25519PrivateKey.generate()
    envelope = issue_license(
        _payload(issued_at="2026-08-01", not_before="2026-08-01", expires_at="2026-08-29"),
        private,
    )
    with pytest.raises(LicenseError, match="expired"):
        verify_license(envelope, private.public_key(), today=date(2026, 8, 30))


def test_client_profile_can_restrict_but_not_elevate() -> None:
    payload = _payload()
    profile = validate_profile_against_license(_profile(), payload)
    assert profile["limits"]["max_workers"] == 4
    assert len(profile["profile_commitment"]) == 64

    with pytest.raises(ClientProfileError, match="max_workers exceeds"):
        validate_profile_against_license(_profile(limits={"max_workers": 9, "max_sources": 12}), payload)

    no_worker_license = _payload(features=["MCP_STDIO", "WORKER_ORCHESTRATION"])
    with pytest.raises(ClientProfileError, match="custom workers"):
        validate_profile_against_license(_profile(custom_workers=True, internet_access=False), no_worker_license)


def test_product_runtime_enforces_tool_species_provider_and_limits(tmp_path) -> None:
    license_path, public_path, profile_path = _write_runtime_files(tmp_path, profile=_profile())
    runtime = ProductRuntime.from_paths(
        license_path=license_path,
        public_key_path=public_path,
        profile_path=profile_path,
        require_license=True,
    )
    assert runtime.status()["status"] == "LICENSED"

    runtime.authorize(tool="gremlin_route", species="OWL", requested_workers=4)
    runtime.authorize(tool="gremlin_research", feature="INTERNET_RESEARCH", provider="arxiv", requested_sources=12)

    with pytest.raises(ProductAuthorizationError, match="TOOL_NOT_ALLOWED_BY_PROFILE"):
        runtime.authorize(tool="gremlin_worker_register", feature="CUSTOM_WORKERS")
    with pytest.raises(ProductAuthorizationError, match="SPECIES_NOT_ALLOWED_BY_PROFILE"):
        runtime.authorize(tool="gremlin_route", species="ANT")
    with pytest.raises(ProductAuthorizationError, match="PROVIDER_NOT_ALLOWED_BY_PROFILE"):
        runtime.authorize(tool="gremlin_research", provider="duckduckgo")
    with pytest.raises(ProductAuthorizationError, match="WORKER_LIMIT_EXCEEDED"):
        runtime.authorize(tool="gremlin_route", requested_workers=5)
    with pytest.raises(ProductAuthorizationError, match="SOURCE_LIMIT_EXCEEDED"):
        runtime.authorize(tool="gremlin_research", requested_sources=13)


def test_missing_license_blocks_product_runtime() -> None:
    runtime = ProductRuntime.unconfigured(require_license=True)
    with pytest.raises(ProductAuthorizationError, match="LICENSE_REQUIRED"):
        runtime.authorize(tool="gremlin_route")


def test_product_mcp_discovery_exposes_license_tools(tmp_path) -> None:
    from mcp import Client
    import gremlin_mcp.product_server as product_server

    license_path, public_path, profile_path = _write_runtime_files(
        tmp_path,
        profile=_profile(tools=["gremlin_status", "gremlin_route", "gremlin_research", "gremlin_auto_fanout"]),
    )
    product_server.configure_product(
        license_path=str(license_path),
        public_key_path=str(public_path),
        profile_path=str(profile_path),
        require_license=True,
    )

    async def exercise() -> None:
        async with Client(product_server.mcp) as client:
            listed = await client.list_tools()
            names = {tool.name for tool in listed.tools}
            assert {"gremlin_product_status", "gremlin_license_status", "gremlin_route"} <= names
            status_result = await client.call_tool("gremlin_product_status", {})
            assert status_result.is_error is False
            routed = await client.call_tool(
                "gremlin_route",
                {"payload": {"query": "audit evidence provenance and citations"}, "max_species": 4},
            )
            assert routed.is_error is False

    asyncio.run(exercise())
