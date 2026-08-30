from __future__ import annotations

from datetime import datetime, timezone
import base64
import hashlib
import json
import secrets
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .secrets import SecretStore


DEVICE_PRIVATE_SECRET = "device-ed25519-private-v01"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    encoded = value.encode("ascii")
    encoded += b"=" * ((4 - len(encoded) % 4) % 4)
    return base64.urlsafe_b64decode(encoded)


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


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
        private = Ed25519PrivateKey.generate()
        store.set(DEVICE_PRIVATE_SECRET, private_pem(private))
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
        "license_id": str(license_id).strip(),
        "device_id": device_id(public),
        "device_public_key": _b64(_public_raw(public)),
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        "nonce": nonce or secrets.token_urlsafe(24),
    }
    if not core["license_id"]:
        raise ValueError("license_id must be non-empty")
    signature = private.sign(b"GREMLIN-DEVICE-ACTIVATION/v0.1\0" + _canonical(core))
    return {**core, "proof": {"alg": "Ed25519", "signature": _b64(signature)}}


def verify_activation_request(request: Mapping[str, Any]) -> dict[str, Any]:
    core = {key: request[key] for key in ("schema", "license_id", "device_id", "device_public_key", "created_at", "nonce")}
    if core["schema"] != "GREMLIN_DEVICE_ACTIVATION_REQUEST_V0_1":
        raise ValueError("unsupported device activation request schema")
    raw = _unb64(str(core["device_public_key"]))
    if len(raw) != 32:
        raise ValueError("invalid Ed25519 device public key length")
    public = Ed25519PublicKey.from_public_bytes(raw)
    if device_id(public) != core["device_id"]:
        raise ValueError("device_id does not match device public key")
    proof = dict(request.get("proof") or {})
    if proof.get("alg") != "Ed25519":
        raise ValueError("unsupported activation proof algorithm")
    try:
        public.verify(
            _unb64(str(proof.get("signature") or "")),
            b"GREMLIN-DEVICE-ACTIVATION/v0.1\0" + _canonical(core),
        )
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("device activation proof is invalid") from exc
    return core
