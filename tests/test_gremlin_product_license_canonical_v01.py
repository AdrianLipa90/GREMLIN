from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from gremlin_mcp.product.license import LicenseError, issue_license, verify_license


def _payload() -> dict:
    return {
        "schema": "GREMLIN_LICENSE_V0_1",
        "license_id": "GRM-CANON-0001",
        "product": "GREMLIN",
        "edition": "COMMERCIAL",
        "customer": "canonical-test",
        "issued_at": "2026-09-10",
        "not_before": "2026-09-10",
        "expires_at": "2027-09-10",
        "updates_until": "2027-09-10",
        "seats": 1,
        "devices": 1,
        "features": ["MCP_STDIO"],
        "limits": {"max_workers": 4, "max_sources": 24},
        "usage": {"commercial_use": True, "production_use": False, "hosted_service": False},
        "metadata": {},
    }


def test_verifier_rejects_unsigned_extra_payload_field_before_signature_admission() -> None:
    private = Ed25519PrivateKey.generate()
    envelope = issue_license(_payload(), private)
    tampered = json.loads(json.dumps(envelope))
    tampered["payload"]["unexpected_entitlement"] = True
    with pytest.raises(LicenseError, match="unsupported keys"):
        verify_license(tampered, private.public_key())


def test_issuer_rejects_unknown_v01_payload_limit_and_usage_fields() -> None:
    private = Ed25519PrivateKey.generate()
    payload = _payload()
    payload["unexpected"] = "ignored-before"
    with pytest.raises(LicenseError, match="unsupported keys"):
        issue_license(payload, private)

    payload = _payload()
    payload["limits"]["max_gpu"] = 1
    with pytest.raises(LicenseError, match="limits contains unsupported keys"):
        issue_license(payload, private)

    payload = _payload()
    payload["usage"]["resale"] = False
    with pytest.raises(LicenseError, match="usage contains unsupported keys"):
        issue_license(payload, private)


def test_signature_encoding_must_be_canonical_unpadded_base64url() -> None:
    private = Ed25519PrivateKey.generate()
    envelope = issue_license(_payload(), private)
    padded = json.loads(json.dumps(envelope))
    padded["signature"]["value"] += "="
    with pytest.raises(LicenseError, match="canonical unpadded base64url"):
        verify_license(padded, private.public_key())


def test_verifier_rejects_unknown_envelope_and_signature_fields() -> None:
    private = Ed25519PrivateKey.generate()
    envelope = issue_license(_payload(), private)
    extra_envelope = json.loads(json.dumps(envelope))
    extra_envelope["verified"] = True
    with pytest.raises(LicenseError, match="license envelope contains unsupported keys"):
        verify_license(extra_envelope, private.public_key())

    extra_signature = json.loads(json.dumps(envelope))
    extra_signature["signature"]["note"] = "unsigned metadata"
    with pytest.raises(LicenseError, match="signature contains unsupported keys"):
        verify_license(extra_signature, private.public_key())


def test_today_parameter_rejects_datetime_instead_of_implicitly_comparing_types() -> None:
    private = Ed25519PrivateKey.generate()
    envelope = issue_license(_payload(), private)
    with pytest.raises(LicenseError, match="today must be a date"):
        verify_license(envelope, private.public_key(), today=datetime.now(timezone.utc))
