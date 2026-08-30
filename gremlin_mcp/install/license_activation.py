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
    load_public_key,
    verify_license,
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
    override = str(environ.get("GREMLIN_LICENSE_PUBLIC_KEY") or "").strip()
    return Path(override) if override else Path(paths.shared_data_root) / "issuer-public.pem"


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


def _result(payload: Mapping[str, Any], envelope: Mapping[str, Any], license_path: Path) -> LicenseActivationResult:
    signature = envelope.get("signature") if isinstance(envelope, Mapping) else None
    key_id = str(signature.get("key_id")) if isinstance(signature, Mapping) and signature.get("key_id") else None
    return LicenseActivationResult(
        schema=LICENSE_ACTIVATION_SCHEMA,
        status="ACTIVE",
        license_id=str(payload.get("license_id") or ""),
        edition=str(payload.get("edition") or ""),
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
    public_path = Path(public_key_path) if public_key_path else resolve_public_key_path(paths, env=env)
    if not public_path.is_file():
        raise LicenseError(f"issuer public key is unavailable: {public_path}")
    payload = verify_license_key(key, public_path)
    envelope = decode_license_key(key)
    target = Path(paths.license_file)
    _atomic_json_write(target, envelope)
    # Re-read from disk through the production verifier so activation cannot report
    # success for bytes that were not actually persisted correctly.
    persisted = load_license(target, public_path)
    if persisted.get("license_id") != payload.get("license_id"):
        raise LicenseError("persisted license verification mismatch")
    return _result(persisted, envelope, target)


def import_license_file(
    source: str | Path,
    paths: GremlinPaths,
    *,
    public_key_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> LicenseActivationResult:
    public_path = Path(public_key_path) if public_key_path else resolve_public_key_path(paths, env=env)
    if not public_path.is_file():
        raise LicenseError(f"issuer public key is unavailable: {public_path}")
    try:
        envelope = json.loads(Path(source).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LicenseError("unable to read signed GREMLIN license file") from exc
    if not isinstance(envelope, dict):
        raise LicenseError("signed GREMLIN license must be a JSON object")
    payload = verify_license(envelope, load_public_key(public_path))
    target = Path(paths.license_file)
    _atomic_json_write(target, envelope)
    persisted = load_license(target, public_path)
    if persisted.get("license_id") != payload.get("license_id"):
        raise LicenseError("persisted license verification mismatch")
    return _result(persisted, envelope, target)


def installed_license_status(
    paths: GremlinPaths,
    *,
    public_key_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    target = Path(paths.license_file)
    public_path = Path(public_key_path) if public_key_path else resolve_public_key_path(paths, env=env)
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
    except (LicenseError, OSError) as exc:
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
