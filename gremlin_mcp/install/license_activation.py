from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from gremlin_mcp.product.keycodec import decode_license_key, verify_license_key
from gremlin_mcp.product.license import (
    LicenseError,
    license_status as product_license_status,
    load_license,
)

from .paths import GremlinPaths


LICENSE_ACTIVATION_SCHEMA = "GREMLIN_LICENSE_ACTIVATION_V0_1"
LICENSE_STATUS_SCHEMA = "GREMLIN_INSTALLED_LICENSE_STATUS_V0_1"


@dataclass(frozen=True)
class LicenseActivationResult:
    schema: str
    status: str
    license_id: str
    edition: str
    license_path: str
    key_id: str | None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "schema": self.schema,
            "status": self.status,
            "license_id": self.license_id,
            "edition": self.edition,
            "license_path": self.license_path,
            "key_id": self.key_id,
        }


def resolve_public_key_path(paths: GremlinPaths, *, env: Mapping[str, str] | None = None) -> Path:
    environ = os.environ if env is None else env
    override = environ.get("GREMLIN_LICENSE_PUBLIC_KEY")
    if override is None or override == "":
        return Path(paths.shared_data_root) / "issuer-public.pem"
    if not isinstance(override, str):
        raise LicenseError("GREMLIN_LICENSE_PUBLIC_KEY must be a string path")
    normalized = override.strip()
    if not normalized:
        return Path(paths.shared_data_root) / "issuer-public.pem"
    return Path(normalized)


def _selected_public_key_path(
    paths: GremlinPaths,
    public_key_path: str | Path | None,
    env: Mapping[str, str] | None,
) -> Path:
    if public_key_path is None:
        return resolve_public_key_path(paths, env=env)
    if isinstance(public_key_path, str) and not public_key_path.strip():
        raise LicenseError("explicit issuer public key path must be non-empty")
    if not isinstance(public_key_path, (str, Path)):
        raise LicenseError("issuer public key path must be a string or Path")
    return Path(public_key_path)


def _license_bytes(value: Mapping[str, Any]) -> bytes:
    if not isinstance(value, Mapping):
        raise LicenseError("signed GREMLIN license must be a JSON object")
    try:
        return (json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise LicenseError("signed GREMLIN license must be finite JSON") from exc


def _atomic_verified_license_write(
    path: Path,
    payload: bytes,
    *,
    public_key_path: Path,
) -> dict[str, Any]:
    """Verify the exact temporary bytes before replacing an installed license.

    A malformed write therefore cannot destroy a previously valid installed
    license and then fail only during the post-write verification step.
    """
    if not isinstance(payload, bytes):
        raise LicenseError("license persistence payload must be bytes")
    path.parent.mkdir(parents=True, exist_ok=True)
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

        # Production verification is performed against the exact bytes/inode
        # that will become the installed file. The old target still exists here.
        persisted = load_license(temp, public_key_path)
        os.replace(temp, path)
        return persisted
    finally:
        if fd_open:
            os.close(fd)
        if temp.exists():
            temp.unlink()


def _result(payload: Mapping[str, Any], envelope: Mapping[str, Any], license_path: Path) -> LicenseActivationResult:
    if not isinstance(payload, Mapping):
        raise LicenseError("verified license payload must be an object")
    license_id = payload.get("license_id")
    edition = payload.get("edition")
    if not isinstance(license_id, str) or not license_id:
        raise LicenseError("verified license_id is malformed")
    if not isinstance(edition, str) or not edition:
        raise LicenseError("verified license edition is malformed")
    signature = envelope.get("signature") if isinstance(envelope, Mapping) else None
    if not isinstance(signature, Mapping):
        raise LicenseError("verified license signature block is missing")
    key_id = signature.get("key_id")
    if not isinstance(key_id, str) or not key_id:
        raise LicenseError("verified license key_id is malformed")
    return LicenseActivationResult(
        schema=LICENSE_ACTIVATION_SCHEMA,
        status="ACTIVE",
        license_id=license_id,
        edition=edition,
        license_path=str(license_path),
        key_id=key_id,
    )


def activate_license_key(
    key: str,
    paths: GremlinPaths,
    *,
    public_key_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> LicenseActivationResult:
    public_path = _selected_public_key_path(paths, public_key_path, env)
    if not public_path.is_file():
        raise LicenseError(f"issuer public key is unavailable: {public_path}")
    expected = verify_license_key(key, public_path)
    envelope = decode_license_key(key)
    target = Path(paths.license_file)
    persisted = _atomic_verified_license_write(
        target,
        _license_bytes(envelope),
        public_key_path=public_path,
    )
    if persisted != expected:
        raise LicenseError("persisted license verification mismatch")
    return _result(persisted, envelope, target)


def import_license_file(
    source: str | Path,
    paths: GremlinPaths,
    *,
    public_key_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> LicenseActivationResult:
    public_path = _selected_public_key_path(paths, public_key_path, env)
    if not public_path.is_file():
        raise LicenseError(f"issuer public key is unavailable: {public_path}")
    try:
        source_bytes = Path(source).read_bytes()
    except OSError as exc:
        raise LicenseError("unable to read signed GREMLIN license file") from exc

    # Parse only after the exact source bytes have been captured. Duplicate JSON
    # keys, unknown fields and signature malleability are rejected by load_license
    # when the temporary target bytes are verified below.
    target = Path(paths.license_file)
    persisted = _atomic_verified_license_write(
        target,
        source_bytes,
        public_key_path=public_path,
    )
    try:
        envelope = json.loads(source_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        # This path is defensive: exact-byte verification above should already
        # have rejected such input without replacing the previous target.
        raise LicenseError("unable to read signed GREMLIN license file") from exc
    if not isinstance(envelope, dict):
        raise LicenseError("signed GREMLIN license must be a JSON object")
    return _result(persisted, envelope, target)


def installed_license_status(
    paths: GremlinPaths,
    *,
    public_key_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    target = Path(paths.license_file)
    public_path = _selected_public_key_path(paths, public_key_path, env)
    if not target.is_file():
        return {
            "schema": LICENSE_STATUS_SCHEMA,
            "status": "NOT_ACTIVATED",
            "license_path": str(target),
            "public_key_path": str(public_path),
        }
    if not public_path.is_file():
        return {
            "schema": LICENSE_STATUS_SCHEMA,
            "status": "BLOCKED",
            "reason": "ISSUER_PUBLIC_KEY_UNAVAILABLE",
            "license_path": str(target),
            "public_key_path": str(public_path),
        }
    try:
        payload = load_license(target, public_path)
    except (LicenseError, OSError, UnicodeError) as exc:
        return {
            "schema": LICENSE_STATUS_SCHEMA,
            "status": "BLOCKED",
            "reason": str(exc),
            "license_path": str(target),
            "public_key_path": str(public_path),
        }
    safe = product_license_status(payload)
    return {
        "schema": LICENSE_STATUS_SCHEMA,
        "status": "ACTIVE",
        "license_path": str(target),
        "public_key_path": str(public_path),
        "license": safe,
    }
