from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from gremlin_mcp.product.profile import ClientProfileError, load_client_profile
from gremlin_mcp.product.license import LicenseError, load_license

from .license_activation import resolve_public_key_path
from .paths import GremlinPaths


PROFILE_IMPORT_SCHEMA = "GREMLIN_CUSTOMER_PROFILE_IMPORT_V0_1"
PROFILE_STATUS_SCHEMA = "GREMLIN_CUSTOMER_PROFILE_STATUS_V0_1"


def _atomic_verified_profile_write(
    path: Path,
    value: Mapping[str, Any],
    *,
    license_payload: Mapping[str, Any],
    expected_commitment: str,
) -> dict[str, Any]:
    """Persist a validated profile without risking replacement before re-verification."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(
            dict(value),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp = Path(temp_name)
    fd_open = True
    try:
        if os.name != "nt":
            os.fchmod(fd, 0o600)
        handle = os.fdopen(fd, "wb")
        fd_open = False
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        # Verify the exact staged bytes through the production loader before the
        # destination is touched. A verifier failure therefore preserves any
        # previously active profile.
        verified = load_client_profile(temp, license_payload)
        actual_commitment = verified.get("profile_commitment")
        if not isinstance(actual_commitment, str) or actual_commitment != expected_commitment:
            raise ClientProfileError("staged customer profile verification mismatch")

        os.replace(temp, path)
        return verified
    finally:
        if fd_open:
            os.close(fd)
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
    payload = _license_payload(paths)

    # Use the production parser for the source as well: duplicate JSON keys,
    # unknown fields, malformed types and entitlement elevation all fail closed.
    validated = load_client_profile(source, payload)
    commitment = validated.get("profile_commitment")
    if not isinstance(commitment, str) or not commitment:
        raise ClientProfileError("validated customer profile commitment is unavailable")

    persisted = {key: value for key, value in validated.items() if key != "profile_commitment"}
    target = Path(paths.client_profile_file)
    reread = _atomic_verified_profile_write(
        target,
        persisted,
        license_payload=payload,
        expected_commitment=commitment,
    )

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
