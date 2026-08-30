from __future__ import annotations

from datetime import date

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from gremlin_mcp.product import ProductRuntime, decode_license_key, encode_license_key
from gremlin_mcp.product.license import LicenseError, issue_license


def _payload() -> dict:
    return {
        "schema": "GREMLIN_LICENSE_V0_1",
        "license_id": "GRM-KEY-0001",
        "product": "GREMLIN",
        "edition": "COMMERCIAL",
        "customer": "key-test",
        "issued_at": "2026-08-30",
        "not_before": "2026-08-30",
        "expires_at": "2027-08-30",
        "updates_until": "2027-08-30",
        "seats": 1,
        "devices": 2,
        "features": ["MCP_STDIO", "WORKER_ORCHESTRATION"],
        "limits": {"max_workers": 4, "max_sources": 24},
        "usage": {"commercial_use": True, "production_use": False, "hosted_service": False},
        "metadata": {},
    }


def test_compact_key_round_trip_and_runtime_admission(tmp_path) -> None:
    private = Ed25519PrivateKey.generate()
    envelope = issue_license(_payload(), private)
    compact = encode_license_key(envelope)
    assert compact.startswith("GRM1-")
    assert decode_license_key(compact) == envelope

    public_path = tmp_path / "public.pem"
    public_path.write_bytes(
        private.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    runtime = ProductRuntime.from_configuration(
        license_key=compact,
        public_key_path=public_path,
        require_license=True,
    )
    assert runtime.status()["status"] == "LICENSED"
    runtime.authorize(tool="gremlin_route", requested_workers=4)


def test_compact_key_tamper_fails_closed(tmp_path) -> None:
    private = Ed25519PrivateKey.generate()
    envelope = issue_license(_payload(), private)
    compact = encode_license_key(envelope)
    public_path = tmp_path / "public.pem"
    public_path.write_bytes(
        private.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    # Change one transport character while keeping the GRM1 envelope shape.
    replacement = "A" if compact[-1] != "A" else "B"
    tampered = compact[:-1] + replacement
    runtime = ProductRuntime.from_configuration(
        license_key=tampered,
        public_key_path=public_path,
        require_license=True,
    )
    assert runtime.status()["status"] == "BLOCKED"
    with pytest.raises(PermissionError):
        runtime.authorize(tool="gremlin_route")


def test_compact_key_rejects_wrong_prefix() -> None:
    with pytest.raises(LicenseError, match="GRM1"):
        decode_license_key("BAD1-abc")
