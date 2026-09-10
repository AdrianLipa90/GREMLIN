from __future__ import annotations

from datetime import datetime, timezone
import base64
import binascii
import hashlib
import json
import re
import secrets
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .secrets import SecretStore


DEVICE_PRIVATE_SECRET = "device-ed25519-private-v01"
_B64URL_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(value: Any, field: str) -> bytes:
    if not isinstance(value, str) or not value or not _B64URL_RE.fullmatch(value):
        raise ValueError(f"{field} must be canonical unpadded base64url")
    encoded = value.encode("ascii")
    encoded += b"=" * ((4 - len(encoded) % 4) % 4)
    try:
        raw = base64.b64decode(encoded, altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{field} is not valid base64url") from exc
    if _b64(raw) != value:
        raise ValueError(f"{field} must use canonical unpadded base64url encoding")
    return raw


def _canonical(value: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("device activation payload must be finite JSON") from exc


def _strict_text(value: Any, field: str, *, max_len: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text or len(text) > max_len:
        raise ValueError(f"{field} must contain 1..{max_len} characters")
    return text


def _timestamp(value: Any | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    text = _strict_text(value, "created_at", max_len=64)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("created_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("created_at must include a timezone offset")
    return text


def _public_raw(public_key: Ed25519PublicKey) -> bytes:
    return public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def device_id(public_key: Ed25519PublicKey) -> str:
    digest = hashlib.blake2b(_public_raw(public_key), digest_size=16).hexdigest()
    return f"GRD-{digest}"


def private_pem(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def load_device_private(data: bytes) -> Ed25519PrivateKey:
    if not isinstance(data, bytes):
        raise ValueError("stored GREMLIN device key must be bytes")
    key = serialization.load_pem_private_key(data, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("stored GREMLIN device key is not Ed25519")
    return key


def device_identity_status(store: SecretStore) -> dict[str, str | None]:
    stored = store.get(DEVICE_PRIVATE_SECRET)
    if stored is None:
        return {
            "schema": "GREMLIN_DEVICE_IDENTITY_V0_1",
            "status": "UNINITIALIZED",
            "device_id": None,
            "public_key": None,
        }
    private = load_device_private(stored)
    public = private.public_key()
    return {
        "schema": "GREMLIN_DEVICE_IDENTITY_V0_1",
        "status": "READY",
        "device_id": device_id(public),
        "public_key": _b64(_public_raw(public)),
    }


def ensure_device_identity(store: SecretStore) -> dict[str, str]:
    stored = store.get(DEVICE_PRIVATE_SECRET)
    if stored is None:
        generated = Ed25519PrivateKey.generate()
        generated_pem = private_pem(generated)
        store.set(DEVICE_PRIVATE_SECRET, generated_pem)
        persisted = store.get(DEVICE_PRIVATE_SECRET)
        if persisted is None:
            raise RuntimeError("GREMLIN device identity secret store did not persist the generated key")
        private = load_device_private(persisted)
        if _public_raw(private.public_key()) != _public_raw(generated.public_key()):
            raise RuntimeError("GREMLIN device identity read-back does not match the generated key")
        created = "CREATED"
    else:
        private = load_device_private(stored)
        created = "EXISTING"
    public = private.public_key()
    return {
        "schema": "GREMLIN_DEVICE_IDENTITY_V0_1",
        "status": created,
        "device_id": device_id(public),
        "public_key": _b64(_public_raw(public)),
    }


def build_activation_request(
    *,
    license_id: str,
    store: SecretStore,
    nonce: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    stored = store.get(DEVICE_PRIVATE_SECRET)
    if stored is None:
        ensure_device_identity(store)
        stored = store.get(DEVICE_PRIVATE_SECRET)
    if stored is None:
        raise RuntimeError("GREMLIN device identity could not be persisted")
    private = load_device_private(stored)
    public = private.public_key()
    core = {
        "schema": "GREMLIN_DEVICE_ACTIVATION_REQUEST_V0_1",
        "license_id": _strict_text(license_id, "license_id", max_len=128),
        "device_id": device_id(public),
        "device_public_key": _b64(_public_raw(public)),
        "created_at": _timestamp(created_at),
        "nonce": secrets.token_urlsafe(24) if nonce is None else _strict_text(nonce, "nonce", max_len=256),
    }
    signature = private.sign(b"GREMLIN-DEVICE-ACTIVATION/v0.1\0" + _canonical(core))
    return {**core, "proof": {"alg": "Ed25519", "signature": _b64(signature)}}


def verify_activation_request(request: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        raise ValueError("device activation request must be an object")
    required = ("schema", "license_id", "device_id", "device_public_key", "created_at", "nonce")
    missing = [key for key in required if key not in request]
    if missing:
        raise ValueError(f"device activation request is missing fields: {missing}")
    core = {key: request[key] for key in required}
    if core["schema"] != "GREMLIN_DEVICE_ACTIVATION_REQUEST_V0_1":
        raise ValueError("unsupported device activation request schema")
    core["license_id"] = _strict_text(core["license_id"], "license_id", max_len=128)
    core["device_id"] = _strict_text(core["device_id"], "device_id", max_len=64)
    core["created_at"] = _timestamp(core["created_at"])
    core["nonce"] = _strict_text(core["nonce"], "nonce", max_len=256)
    device_public_key = _strict_text(core["device_public_key"], "device_public_key", max_len=128)
    core["device_public_key"] = device_public_key
    raw = _unb64(device_public_key, "device_public_key")
    if len(raw) != 32:
        raise ValueError("invalid Ed25519 device public key length")
    public = Ed25519PublicKey.from_public_bytes(raw)
    if device_id(public) != core["device_id"]:
        raise ValueError("device_id does not match device public key")
    proof = request.get("proof")
    if not isinstance(proof, Mapping):
        raise ValueError("activation proof must be an object")
    if proof.get("alg") != "Ed25519":
        raise ValueError("unsupported activation proof algorithm")
    try:
        signature = _unb64(proof.get("signature"), "proof.signature")
        if len(signature) != 64:
            raise ValueError("invalid Ed25519 signature length")
        public.verify(
            signature,
            b"GREMLIN-DEVICE-ACTIVATION/v0.1\0" + _canonical(core),
        )
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("device activation proof is invalid") from exc
    return core
