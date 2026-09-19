from __future__ import annotations

import base64
import binascii
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from gremlin_mcp.product.license import (
    LicenseError,
    load_public_key,
    public_key_id,
)

MANIFEST_SCHEMA = "GREMLIN_UPDATE_MANIFEST_V0_1"
ENVELOPE_SCHEMA = "GREMLIN_UPDATE_ENVELOPE_V0_1"
SIGNATURE_ALGORITHM = "Ed25519"
DOMAIN = b"GREMLIN-UPDATE-MANIFEST/v0.1\0"

_PLATFORMS = frozenset({"linux", "windows"})
_ARCHITECTURES = frozenset({"amd64"})
_CHANNELS = frozenset({"PREVIEW", "EARLY_ACCESS", "STABLE"})
_MANIFEST_KEYS = frozenset({
    "schema",
    "product",
    "version",
    "release_sequence",
    "channel",
    "platform",
    "architecture",
    "artifact_name",
    "artifact_sha256",
    "artifact_size",
    "released_on",
})
_ENVELOPE_KEYS = frozenset({"schema", "manifest", "signature"})
_SIGNATURE_KEYS = frozenset({"algorithm", "key_id", "value"})
_VERSION_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._+-]{0,127}$")
_ARTIFACT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,191}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_B64URL_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class UpdateManifestError(ValueError):
    """Raised when a GREMLIN update manifest is malformed or fails verification."""


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
        raise UpdateManifestError("update manifest data must be finite JSON") from exc


def _reject_unknown(value: Mapping[str, Any], allowed: frozenset[str], field: str) -> None:
    unknown = sorted(key for key in value if not isinstance(key, str) or key not in allowed)
    if unknown:
        raise UpdateManifestError(f"{field} contains unsupported keys: {unknown}")


def _nonempty(value: Any, field: str, *, max_len: int) -> str:
    if not isinstance(value, str):
        raise UpdateManifestError(f"{field} must be a string")
    text = value.strip()
    if not text or len(text) > max_len:
        raise UpdateManifestError(f"{field} must contain 1..{max_len} characters")
    return text


def _positive_int(value: Any, field: str, *, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise UpdateManifestError(f"{field} must be an integer")
    if value < 1 or value > maximum:
        raise UpdateManifestError(f"{field} must be in 1..{maximum}")
    return value


def _date(value: Any, field: str) -> str:
    text = _nonempty(value, field, max_len=32)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise UpdateManifestError(f"{field} must be YYYY-MM-DD") from exc
    return parsed.isoformat()


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64u_decode(value: Any) -> bytes:
    if not isinstance(value, str) or not value or not _B64URL_RE.fullmatch(value):
        raise UpdateManifestError("signature must be canonical unpadded base64url")
    padding = "=" * ((4 - len(value) % 4) % 4)
    try:
        raw = base64.b64decode((value + padding).encode("ascii"), altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as exc:
        raise UpdateManifestError("invalid base64url signature") from exc
    if _b64u(raw) != value:
        raise UpdateManifestError("signature must use canonical unpadded base64url encoding")
    return raw


def _json_no_duplicates(text: str) -> Any:
    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise UpdateManifestError(f"duplicate JSON key in update manifest: {key}")
            out[key] = value
        return out

    try:
        return json.loads(text, object_pairs_hook=hook)
    except UpdateManifestError:
        raise
    except json.JSONDecodeError as exc:
        raise UpdateManifestError("update manifest JSON is malformed") from exc


def normalize_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        raise UpdateManifestError("update manifest must be an object")
    body = dict(manifest)
    _reject_unknown(body, _MANIFEST_KEYS, "update manifest")
    if body.get("schema") != MANIFEST_SCHEMA:
        raise UpdateManifestError(f"update manifest schema must be {MANIFEST_SCHEMA}")
    if body.get("product") != "GREMLIN":
        raise UpdateManifestError("update manifest product must be GREMLIN")

    version = _nonempty(body.get("version"), "version", max_len=128)
    if not _VERSION_RE.fullmatch(version):
        raise UpdateManifestError("version contains unsupported characters")

    channel = _nonempty(body.get("channel"), "channel", max_len=32).upper()
    if channel not in _CHANNELS:
        raise UpdateManifestError(f"unsupported update channel: {channel}")

    platform = _nonempty(body.get("platform"), "platform", max_len=16).casefold()
    if platform not in _PLATFORMS:
        raise UpdateManifestError(f"unsupported update platform: {platform}")

    architecture = _nonempty(body.get("architecture"), "architecture", max_len=16).casefold()
    if architecture not in _ARCHITECTURES:
        raise UpdateManifestError(f"unsupported update architecture: {architecture}")

    artifact_name = _nonempty(body.get("artifact_name"), "artifact_name", max_len=192)
    if not _ARTIFACT_RE.fullmatch(artifact_name) or Path(artifact_name).name != artifact_name:
        raise UpdateManifestError("artifact_name must be a safe basename")

    digest = _nonempty(body.get("artifact_sha256"), "artifact_sha256", max_len=64)
    if not _SHA256_RE.fullmatch(digest):
        raise UpdateManifestError("artifact_sha256 must be 64 lowercase hexadecimal characters")

    return {
        "schema": MANIFEST_SCHEMA,
        "product": "GREMLIN",
        "version": version,
        "release_sequence": _positive_int(body.get("release_sequence"), "release_sequence", maximum=2_147_483_647),
        "channel": channel,
        "platform": platform,
        "architecture": architecture,
        "artifact_name": artifact_name,
        "artifact_sha256": digest,
        "artifact_size": _positive_int(body.get("artifact_size"), "artifact_size", maximum=100_000_000_000),
        "released_on": _date(body.get("released_on"), "released_on"),
    }


def issue_update_manifest(
    manifest: Mapping[str, Any],
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    if not isinstance(private_key, Ed25519PrivateKey):
        raise UpdateManifestError("private key must be Ed25519")
    normalized = normalize_manifest(manifest)
    signature = private_key.sign(DOMAIN + _canonical(normalized))
    return {
        "schema": ENVELOPE_SCHEMA,
        "manifest": normalized,
        "signature": {
            "algorithm": SIGNATURE_ALGORITHM,
            "key_id": public_key_id(private_key.public_key()),
            "value": _b64u(signature),
        },
    }


def verify_update_manifest(
    envelope: Mapping[str, Any],
    public_key: Ed25519PublicKey,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    if not isinstance(envelope, Mapping):
        raise UpdateManifestError("update envelope must be an object")
    _reject_unknown(envelope, _ENVELOPE_KEYS, "update envelope")
    if envelope.get("schema") != ENVELOPE_SCHEMA:
        raise UpdateManifestError(f"update envelope schema must be {ENVELOPE_SCHEMA}")

    raw_manifest = envelope.get("manifest")
    if not isinstance(raw_manifest, Mapping):
        raise UpdateManifestError("update envelope manifest must be an object")
    manifest = normalize_manifest(raw_manifest)

    signature = envelope.get("signature")
    if not isinstance(signature, Mapping):
        raise UpdateManifestError("update signature must be an object")
    _reject_unknown(signature, _SIGNATURE_KEYS, "update signature")
    if signature.get("algorithm") != SIGNATURE_ALGORITHM:
        raise UpdateManifestError("update signature algorithm must be Ed25519")
    expected_key_id = public_key_id(public_key)
    if signature.get("key_id") != expected_key_id:
        raise UpdateManifestError("update key_id does not match configured public key")
    raw_signature = _b64u_decode(signature.get("value"))
    if len(raw_signature) != 64:
        raise UpdateManifestError("update signature must decode to 64 bytes")
    try:
        public_key.verify(raw_signature, DOMAIN + _canonical(manifest))
    except InvalidSignature as exc:
        raise UpdateManifestError("update signature is invalid") from exc

    if today is not None and type(today) is not date:
        raise UpdateManifestError("today must be a date")
    current = today if today is not None else datetime.now(timezone.utc).date()
    if date.fromisoformat(manifest["released_on"]) > current:
        raise UpdateManifestError("update manifest release date is in the future")
    return manifest


def load_update_manifest(
    manifest_path: str | Path,
    public_key_path: str | Path,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    try:
        text = Path(manifest_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise UpdateManifestError("unable to load update manifest file") from exc
    envelope = _json_no_duplicates(text)
    if not isinstance(envelope, Mapping):
        raise UpdateManifestError("update envelope must be an object")
    try:
        public_key = load_public_key(public_key_path)
    except LicenseError as exc:
        raise UpdateManifestError("unable to load update verifier key") from exc
    return verify_update_manifest(envelope, public_key, today=today)


def verify_artifact(manifest: Mapping[str, Any], artifact_path: str | Path) -> dict[str, Any]:
    normalized = normalize_manifest(manifest)
    target = Path(artifact_path)
    if not target.is_file():
        raise UpdateManifestError("update artifact is missing or not a regular file")
    if target.name != normalized["artifact_name"]:
        raise UpdateManifestError("update artifact filename does not match signed manifest")

    digest = hashlib.sha256()
    size = 0
    try:
        with target.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                digest.update(chunk)
    except OSError as exc:
        raise UpdateManifestError("unable to read update artifact") from exc

    actual_digest = digest.hexdigest()
    if size != normalized["artifact_size"]:
        raise UpdateManifestError(
            f"update artifact size mismatch: expected {normalized['artifact_size']}, got {size}"
        )
    if actual_digest != normalized["artifact_sha256"]:
        raise UpdateManifestError("update artifact SHA-256 mismatch")
    return {
        "status": "PASS",
        "artifact_name": normalized["artifact_name"],
        "artifact_size": size,
        "artifact_sha256": actual_digest,
    }


def update_eligibility(
    manifest: Mapping[str, Any],
    *,
    license_payload: Mapping[str, Any] | None,
    platform: str,
    architecture: str = "amd64",
) -> dict[str, Any]:
    normalized = normalize_manifest(manifest)
    target_platform = _nonempty(platform, "platform", max_len=16).casefold()
    target_arch = _nonempty(architecture, "architecture", max_len=16).casefold()

    reasons: list[str] = []
    if normalized["platform"] != target_platform:
        reasons.append("PLATFORM_MISMATCH")
    if normalized["architecture"] != target_arch:
        reasons.append("ARCHITECTURE_MISMATCH")

    updates_until: str | None = None
    if license_payload is not None:
        if not isinstance(license_payload, Mapping):
            raise UpdateManifestError("license_payload must be an object when provided")
        raw_updates_until = license_payload.get("updates_until")
        if raw_updates_until is not None:
            updates_until = _date(raw_updates_until, "license.updates_until")
            if date.fromisoformat(normalized["released_on"]) > date.fromisoformat(updates_until):
                reasons.append("UPDATE_WINDOW_EXPIRED")

    return {
        "eligible": not reasons,
        "reasons": reasons,
        "updates_until": updates_until,
        "release_sequence": normalized["release_sequence"],
        "version": normalized["version"],
        "platform": normalized["platform"],
        "architecture": normalized["architecture"],
    }
