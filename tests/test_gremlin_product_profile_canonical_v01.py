from __future__ import annotations

import json

import pytest

from gremlin_mcp.product.profile import (
    ClientProfileError,
    load_client_profile,
    normalize_client_profile,
    validate_profile_against_license,
)


def _profile() -> dict:
    return {
        "schema": "GREMLIN_CLIENT_PROFILE_V0_1",
        "client_id": "canonical-client",
        "label": "Canonical client",
        "tools": ["gremlin_route"],
        "species": ["OWL"],
        "providers": ["arxiv"],
        "languages": ["en"],
        "internet_access": True,
        "custom_workers": False,
        "limits": {"max_workers": 2, "max_sources": 8},
        "metadata": {},
    }


def _license() -> dict:
    return {
        "features": ["MCP_STDIO", "INTERNET_RESEARCH"],
        "limits": {"max_workers": 4, "max_sources": 24},
    }


def test_unknown_profile_key_is_rejected_instead_of_ignored() -> None:
    profile = _profile()
    profile["internet_acess"] = False
    with pytest.raises(ClientProfileError, match="unsupported keys"):
        normalize_client_profile(profile)


def test_unknown_profile_limit_is_rejected() -> None:
    profile = _profile()
    profile["limits"]["max_gpu"] = 1
    with pytest.raises(ClientProfileError, match="limits contains unsupported keys"):
        normalize_client_profile(profile)


def test_falsey_nonmapping_limits_do_not_fall_back_to_defaults() -> None:
    profile = _profile()
    profile["limits"] = []
    with pytest.raises(ClientProfileError, match="limits must be an object"):
        normalize_client_profile(profile)


def test_malformed_license_feature_container_is_rejected() -> None:
    with pytest.raises(ClientProfileError, match="features entitlement is malformed"):
        validate_profile_against_license(_profile(), {"features": "INTERNET_RESEARCH", "limits": {"max_workers": 4, "max_sources": 24}})


def test_duplicate_json_keys_are_rejected_when_loading_profile(tmp_path) -> None:
    path = tmp_path / "profile.json"
    profile = _profile()
    text = json.dumps(profile, separators=(",", ":"))
    text = text.replace(
        '"client_id":"canonical-client"',
        '"client_id":"first","client_id":"canonical-client"',
        1,
    )
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ClientProfileError, match="duplicate JSON key"):
        load_client_profile(path, _license())
