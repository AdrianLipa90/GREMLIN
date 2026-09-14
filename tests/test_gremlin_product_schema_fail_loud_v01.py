from __future__ import annotations

import pytest

from gremlin_mcp.product.license import LicenseError, normalize_payload
from gremlin_mcp.product.profile import ClientProfileError, normalize_client_profile, validate_profile_against_license


def _license_payload() -> dict:
    return {
        "schema": "GREMLIN_LICENSE_V0_1",
        "license_id": "GRM-STRICT-TYPES",
        "product": "GREMLIN",
        "edition": "COMMERCIAL",
        "customer": "strict-types",
        "issued_at": "2026-09-10",
        "not_before": "2026-09-10",
        "expires_at": "2027-09-10",
        "updates_until": "2027-09-10",
        "seats": 1,
        "devices": 1,
        "features": ["MCP_STDIO", "INTERNET_RESEARCH"],
        "limits": {"max_workers": 4, "max_sources": 24},
        "usage": {"commercial_use": True, "production_use": False, "hosted_service": False},
        "metadata": {},
    }


def _profile() -> dict:
    return {
        "schema": "GREMLIN_CLIENT_PROFILE_V0_1",
        "client_id": "strict-client",
        "label": "Strict client",
        "tools": ["gremlin_route"],
        "species": ["OWL"],
        "providers": ["crossref"],
        "languages": ["en"],
        "internet_access": True,
        "custom_workers": False,
        "limits": {"max_workers": 2, "max_sources": 12},
        "metadata": {},
    }


@pytest.mark.parametrize("value", [1.5, "2", True])
def test_license_integer_fields_reject_coercible_non_integers(value) -> None:
    payload = _license_payload()
    payload["seats"] = value
    with pytest.raises(LicenseError, match="seats must be an integer"):
        normalize_payload(payload)


def test_license_string_fields_reject_non_strings() -> None:
    payload = _license_payload()
    payload["customer"] = 12345
    with pytest.raises(LicenseError, match="customer must be a string"):
        normalize_payload(payload)


def test_license_metadata_requires_object() -> None:
    payload = _license_payload()
    payload["metadata"] = ["not", "an", "object"]
    with pytest.raises(LicenseError, match="metadata must be an object"):
        normalize_payload(payload)


@pytest.mark.parametrize("value", [1.5, "2", True])
def test_profile_integer_fields_reject_coercible_non_integers(value) -> None:
    profile = _profile()
    profile["limits"]["max_workers"] = value
    with pytest.raises(ClientProfileError, match="limits.max_workers must be an integer"):
        normalize_client_profile(profile)


def test_profile_list_items_reject_non_strings() -> None:
    profile = _profile()
    profile["providers"] = [123]
    with pytest.raises(ClientProfileError, match="providers must be a string"):
        normalize_client_profile(profile)


def test_profile_label_is_rejected_not_silently_truncated() -> None:
    profile = _profile()
    profile["label"] = "x" * 257
    with pytest.raises(ClientProfileError, match="label must contain at most 256 characters"):
        normalize_client_profile(profile)


def test_profile_metadata_requires_object() -> None:
    profile = _profile()
    profile["metadata"] = ["not", "an", "object"]
    with pytest.raises(ClientProfileError, match="metadata must be an object"):
        normalize_client_profile(profile)


def test_profile_rejects_coercible_malformed_license_limits() -> None:
    license_payload = _license_payload()
    license_payload["limits"]["max_workers"] = "4"
    with pytest.raises(ClientProfileError, match="license max_workers entitlement is malformed"):
        validate_profile_against_license(_profile(), license_payload)
