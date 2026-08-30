from __future__ import annotations

import base64
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

LICENSE_PAYLOAD_SCHEMA = "GREMLIN_LICENSE_V0_1"
LICENSE_ENVELOPE_SCHEMA = "GREMLIN_LICENSE_ENVELOPE_V0_1"
SIGNATURE_ALGORITHM = "Ed25519"
LICENSE_DOMAIN = b"GREMLIN-LICENSE/v0.1\0"

KNOWN_EDITIONS = frozenset({"RESEARCH", "PERSONAL_PRO", "COMMERCIAL", "ENTERPRISE"})
KNOWN_FEATURES = frozenset(
    {
        "MCP_STDIO",
        "MCP_HTTP",
        "INTERNET_RESEARCH",
        "RESEARCH_EXECUTE",
        "WORKER_ORCHESTRATION",
        "CUSTOM_WORKERS",
        "PERSISTENT_STATE",
        "GUARDED_RESEARCH",
        "RELATIONAL_RESEARCH",
        "PROTOTYPE_PIPELINE",
    }
)


class LicenseError(ValueError):
    """Raised when a GREMLIN product license is malformed, invalid, or expired."""


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
        raise LicenseError("license data must be finite JSON") from exc


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64u_decode(value: str) -> bytes:
    text = str(value).strip()
    if not text:
        raise LicenseError("signature must be non-empty")
    padding = "=" * ((4 - len(text) % 4) % 4)
    try:
        return base64.urlsafe_b64decode((text + padding).encode("ascii"))
    except Exception as exc:  # noqa: BLE001 - normalized into a product error
        raise LicenseError("invalid base64url signature") from exc


def public_key_id(public_key: Ed25519PublicKey) -> str:
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return "ed25519:" + hashlib.blake2b(raw, digest_size=12).hexdigest()


def load_private_key(path: str | Path) -> Ed25519PrivateKey:
    data = Path(path).read_bytes()
    try:
        key = serialization.load_pem_private_key(data, password=None)
    except Exception as exc:  # noqa: BLE001
        raise LicenseError("unable to load Ed25519 private key") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise LicenseError("private key is not Ed25519")
    return key


def load_public_key(path: str | Path) -> Ed25519PublicKey:
    data = Path(path).read_bytes()
    try:
        key = serialization.load_pem_public_key(data)
    except Exception as exc:  # noqa: BLE001
        raise LicenseError("unable to load Ed25519 public key") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise LicenseError("public key is not Ed25519")
    return key


def generate_keypair() -> tuple[bytes, bytes, str]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem, public_key_id(public_key)


def _nonempty_string(value: Any, field: str, *, max_len: int = 256) -> str:
    text = str(value or "").strip()
    if not text or len(text) > max_len:
        raise LicenseError(f"{field} must contain 1..{max_len} characters")
    return text


def _positive_int(value: Any, field: str, *, minimum: int = 1, maximum: int = 1_000_000) -> int:
    if isinstance(value, bool):
        raise LicenseError(f"{field} must be an integer")
    try:
        out = int(value)
    except (TypeError, ValueError) as exc:
        raise LicenseError(f"{field} must be an integer") from exc
    if out < minimum or out > maximum:
        raise LicenseError(f"{field} must be in {minimum}..{maximum}")
    return out


def _iso_date(value: Any, field: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    text = _nonempty_string(value, field, max_len=32)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise LicenseError(f"{field} must be YYYY-MM-DD") from exc
    return parsed.isoformat()


def normalize_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise LicenseError("license payload must be an object")
    body = dict(payload)
    if body.get("schema") != LICENSE_PAYLOAD_SCHEMA:
        raise LicenseError(f"license payload schema must be {LICENSE_PAYLOAD_SCHEMA}")
    if body.get("product") != "GREMLIN":
        raise LicenseError("license product must be GREMLIN")

    edition = _nonempty_string(body.get("edition"), "edition", max_len=32).upper()
    if edition not in KNOWN_EDITIONS:
        raise LicenseError(f"unsupported edition: {edition}")

    raw_features = body.get("features")
    if not isinstance(raw_features, list) or not raw_features:
        raise LicenseError("features must be a non-empty list")
    features = sorted({_nonempty_string(v, "feature", max_len=64).upper() for v in raw_features})
    unknown = sorted(set(features) - KNOWN_FEATURES)
    if unknown:
        raise LicenseError(f"unsupported license features: {unknown}")

    usage = body.get("usage")
    if not isinstance(usage, Mapping):
        raise LicenseError("usage must be an object")
    normalized_usage: dict[str, bool] = {}
    for name in ("commercial_use", "production_use", "hosted_service"):
        value = usage.get(name)
        if not isinstance(value, bool):
            raise LicenseError(f"usage.{name} must be boolean")
        normalized_usage[name] = value

    limits = body.get("limits")
    if not isinstance(limits, Mapping):
        raise LicenseError("limits must be an object")

    normalized = {
        "schema": LICENSE_PAYLOAD_SCHEMA,
        "license_id": _nonempty_string(body.get("license_id"), "license_id", max_len=128),
        "product": "GREMLIN",
        "edition": edition,
        "customer": _nonempty_string(body.get("customer"), "customer", max_len=256),
        "issued_at": _iso_date(body.get("issued_at"), "issued_at"),
        "not_before": _iso_date(body.get("not_before", body.get("issued_at")), "not_before"),
        "expires_at": _iso_date(body.get("expires_at"), "expires_at", optional=True),
        "seats": _positive_int(body.get("seats", 1), "seats", maximum=100_000),
        "devices": _positive_int(body.get("devices", 1), "devices", maximum=100_000),
        "limits": {
            "max_workers": _positive_int(limits.get("max_workers", 1), "limits.max_workers", maximum=100_000),
            "max_sources": _positive_int(limits.get("max_sources", 12), "limits.max_sources", maximum=10_000),
        },
        "features": features,
        "usage": normalized_usage,
        "updates_until": _iso_date(body.get("updates_until"), "updates_until", optional=True),
        "metadata": dict(body.get("metadata") or {}),
    }
    _canonical(normalized["metadata"])
    if normalized["expires_at"] is not None and normalized["not_before"] > normalized["expires_at"]:
        raise LicenseError("not_before must not be after expires_at")
    return normalized


def issue_license(payload: Mapping[str, Any], private_key: Ed25519PrivateKey) -> dict[str, Any]:
    normalized = normalize_payload(payload)
    signature = private_key.sign(LICENSE_DOMAIN + _canonical(normalized))
    return {
        "schema": LICENSE_ENVELOPE_SCHEMA,
        "payload": normalized,
        "signature": {
            "algorithm": SIGNATURE_ALGORITHM,
            "key_id": public_key_id(private_key.public_key()),
            "value": _b64u(signature),
        },
    }


def verify_license(
    envelope: Mapping[str, Any],
    public_key: Ed25519PublicKey,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    if not isinstance(envelope, Mapping) or envelope.get("schema") != LICENSE_ENVELOPE_SCHEMA:
        raise LicenseError(f"license envelope schema must be {LICENSE_ENVELOPE_SCHEMA}")
    payload = normalize_payload(envelope.get("payload") or {})
    signature = envelope.get("signature")
    if not isinstance(signature, Mapping):
        raise LicenseError("signature must be an object")
    if signature.get("algorithm") != SIGNATURE_ALGORITHM:
        raise LicenseError("signature algorithm must be Ed25519")
    expected_key_id = public_key_id(public_key)
    if signature.get("key_id") != expected_key_id:
        raise LicenseError("license key_id does not match configured public key")
    raw_signature = _b64u_decode(str(signature.get("value") or ""))
    try:
        public_key.verify(raw_signature, LICENSE_DOMAIN + _canonical(payload))
    except InvalidSignature as exc:
        raise LicenseError("license signature is invalid") from exc

    current = today or datetime.now(timezone.utc).date()
    not_before = date.fromisoformat(str(payload["not_before"]))
    if current < not_before:
        raise LicenseError("license is not active yet")
    if payload["expires_at"] is not None and current > date.fromisoformat(str(payload["expires_at"])):
        raise LicenseError("license has expired")
    return payload


def load_license(
    license_path: str | Path,
    public_key_path: str | Path,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    try:
        envelope = json.loads(Path(license_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LicenseError("unable to load license file") from exc
    return verify_license(envelope, load_public_key(public_key_path), today=today)


def license_status(payload: Mapping[str, Any]) -> dict[str, Any]:
    body = normalize_payload(payload)
    return {
        "schema": "GREMLIN_LICENSE_STATUS_V0_1",
        "status": "VALID",
        "license_id": body["license_id"],
        "edition": body["edition"],
        "expires_at": body["expires_at"],
        "features": list(body["features"]),
        "limits": dict(body["limits"]),
        "usage": dict(body["usage"]),
    }
