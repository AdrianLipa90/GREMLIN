from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from gremlin_mcp.product.profile import ClientProfileError, load_client_profile, validate_profile_against_license
from gremlin_mcp.product.license import LicenseError, load_license

from .license_activation import resolve_public_key_path
from .paths import GremlinPaths


PROFILE_IMPORT_SCHEMA = "GREMLIN_CUSTOMER_PROFILE_IMPORT_V0_1"
PROFILE_STATUS_SCHEMA = "GREMLIN_CUSTOMER_PROFILE_STATUS_V0_1"


def _atomic_json_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(temp, 0o600)
        except OSError:
            pass
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def _license_payload(paths: GremlinPaths) -> dict[str, Any]:
    license_path = Path(paths.license_file)
    public_key = resolve_public_key_path(paths)
    if not license_path.is_file():
        raise ClientProfileError("activate the GREMLIN license before importing a customer profile")
    if not public_key.is_file():
        raise ClientProfileError("issuer public key is unavailable")
    try:
        return load_license(license_path, public_key)
    except (LicenseError, OSError) as exc:
        raise ClientProfileError("installed GREMLIN license is not valid") from exc


def import_client_profile(source: str | Path, paths: GremlinPaths) -> dict[str, Any]:
    try:
        raw = json.loads(Path(source).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClientProfileError("unable to read customer profile JSON") from exc
    if not isinstance(raw, dict):
        raise ClientProfileError("customer profile must be a JSON object")

    payload = _license_payload(paths)
    validated = validate_profile_against_license(raw, payload)
    commitment = str(validated["profile_commitment"])
    persisted = {key: value for key, value in validated.items() if key != "profile_commitment"}
    target = Path(paths.client_profile_file)
    _atomic_json_write(target, persisted)

    reread = load_client_profile(target, payload)
    if reread.get("profile_commitment") != commitment:
        raise ClientProfileError("persisted customer profile verification mismatch")

    return {
        "schema": PROFILE_IMPORT_SCHEMA,
        "status": "ACTIVE",
        "client_id": reread["client_id"],
        "label": reread["label"],
        "profile_commitment": reread["profile_commitment"],
        "profile_path": str(target),
        "limits": dict(reread["limits"]),
    }


def installed_profile_status(paths: GremlinPaths) -> dict[str, Any]:
    target = Path(paths.client_profile_file)
    if not target.is_file():
        return {
            "schema": PROFILE_STATUS_SCHEMA,
            "status": "NOT_CONFIGURED",
            "profile_path": str(target),
        }
    try:
        payload = _license_payload(paths)
        profile = load_client_profile(target, payload)
    except (ClientProfileError, OSError) as exc:
        return {
            "schema": PROFILE_STATUS_SCHEMA,
            "status": "BLOCKED",
            "reason": str(exc),
            "profile_path": str(target),
        }
    return {
        "schema": PROFILE_STATUS_SCHEMA,
        "status": "ACTIVE",
        "client_id": profile["client_id"],
        "label": profile["label"],
        "profile_commitment": profile["profile_commitment"],
        "profile_path": str(target),
        "limits": dict(profile["limits"]),
    }
