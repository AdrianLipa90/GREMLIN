from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

CLIENT_PROFILE_SCHEMA = "GREMLIN_CLIENT_PROFILE_V0_1"
PROFILE_DOMAIN = b"GREMLIN-CLIENT-PROFILE/v0.1\0"
KNOWN_SPECIES = frozenset({"SPIDER", "RAVEN", "HOUND", "MOLE", "OWL", "ANT", "MANTIS", "BELZEBUB"})


class ClientProfileError(ValueError):
    """Raised when a GREMLIN client profile is malformed or attempts to elevate rights."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ClientProfileError("client profile must be finite JSON") from exc


def _text(value: Any, field: str, *, max_len: int = 256) -> str:
    out = str(value or "").strip()
    if not out or len(out) > max_len:
        raise ClientProfileError(f"{field} must contain 1..{max_len} characters")
    return out


def _string_list(value: Any, field: str, *, upper: bool = False) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ClientProfileError(f"{field} must be a list")
    items = []
    for raw in value:
        item = _text(raw, field, max_len=128)
        item = item.upper() if upper else item
        if item not in items:
            items.append(item)
    return items


def _positive_int(value: Any, field: str, *, maximum: int) -> int:
    if isinstance(value, bool):
        raise ClientProfileError(f"{field} must be an integer")
    try:
        out = int(value)
    except (TypeError, ValueError) as exc:
        raise ClientProfileError(f"{field} must be an integer") from exc
    if out < 1 or out > maximum:
        raise ClientProfileError(f"{field} must be in 1..{maximum}")
    return out


def _boolean(value: Any, field: str, *, default: bool = False) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ClientProfileError(f"{field} must be boolean")
    return value


def normalize_client_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(profile, Mapping):
        raise ClientProfileError("client profile must be an object")
    body = dict(profile)
    if body.get("schema") != CLIENT_PROFILE_SCHEMA:
        raise ClientProfileError(f"client profile schema must be {CLIENT_PROFILE_SCHEMA}")

    species = _string_list(body.get("species"), "species", upper=True)
    unknown_species = sorted(set(species) - KNOWN_SPECIES)
    if unknown_species:
        raise ClientProfileError(f"unsupported species: {unknown_species}")

    tools = _string_list(body.get("tools"), "tools")
    providers = [item.casefold() for item in _string_list(body.get("providers"), "providers")]
    languages = [item.casefold() for item in _string_list(body.get("languages", ["en"]), "languages")]
    if not languages:
        raise ClientProfileError("languages must not be empty")

    limits = body.get("limits") or {}
    if not isinstance(limits, Mapping):
        raise ClientProfileError("limits must be an object")

    normalized = {
        "schema": CLIENT_PROFILE_SCHEMA,
        "client_id": _text(body.get("client_id"), "client_id", max_len=128),
        "label": str(body.get("label") or "").strip()[:256],
        "tools": tools,
        "species": species,
        "providers": providers,
        "languages": languages,
        "internet_access": _boolean(body.get("internet_access"), "internet_access"),
        "custom_workers": _boolean(body.get("custom_workers"), "custom_workers"),
        "limits": {
            "max_workers": _positive_int(limits.get("max_workers", 1), "limits.max_workers", maximum=100_000),
            "max_sources": _positive_int(limits.get("max_sources", 12), "limits.max_sources", maximum=10_000),
        },
        "metadata": dict(body.get("metadata") or {}),
    }
    _canonical(normalized["metadata"])
    return normalized


def profile_commitment(profile: Mapping[str, Any]) -> str:
    normalized = normalize_client_profile(profile)
    return hashlib.blake2b(PROFILE_DOMAIN + _canonical(normalized), digest_size=32).hexdigest()


def validate_profile_against_license(profile: Mapping[str, Any], license_payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = normalize_client_profile(profile)
    limits = license_payload.get("limits")
    features = set(license_payload.get("features") or [])
    if not isinstance(limits, Mapping):
        raise ClientProfileError("license limits are unavailable")

    if normalized["limits"]["max_workers"] > int(limits.get("max_workers", 0)):
        raise ClientProfileError("client profile max_workers exceeds license entitlement")
    if normalized["limits"]["max_sources"] > int(limits.get("max_sources", 0)):
        raise ClientProfileError("client profile max_sources exceeds license entitlement")
    if normalized["internet_access"] and "INTERNET_RESEARCH" not in features:
        raise ClientProfileError("client profile requests internet access not granted by license")
    if normalized["custom_workers"] and "CUSTOM_WORKERS" not in features:
        raise ClientProfileError("client profile requests custom workers not granted by license")

    return {
        **normalized,
        "profile_commitment": profile_commitment(normalized),
    }


def load_client_profile(path: str | Path, license_payload: Mapping[str, Any]) -> dict[str, Any]:
    try:
        profile = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClientProfileError("unable to load client profile") from exc
    return validate_profile_against_license(profile, license_payload)
