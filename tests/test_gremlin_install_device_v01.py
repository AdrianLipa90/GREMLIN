from __future__ import annotations

import pytest

from gremlin_mcp.install.device import build_activation_request, ensure_device_identity, verify_activation_request


class MemorySecretStore:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    def set(self, name: str, value: bytes) -> None:
        self.values[name] = bytes(value)

    def get(self, name: str) -> bytes | None:
        return self.values.get(name)

    def delete(self, name: str) -> None:
        self.values.pop(name, None)


class DroppingSecretStore(MemorySecretStore):
    def set(self, name: str, value: bytes) -> None:
        return None


class ReplacingSecretStore(MemorySecretStore):
    def set(self, name: str, value: bytes) -> None:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from gremlin_mcp.install.device import private_pem

        self.values[name] = private_pem(Ed25519PrivateKey.generate())


def test_device_identity_is_stable_after_first_creation() -> None:
    store = MemorySecretStore()
    first = ensure_device_identity(store)
    second = ensure_device_identity(store)
    assert first["status"] == "CREATED"
    assert second["status"] == "EXISTING"
    assert first["device_id"] == second["device_id"]
    assert first["public_key"] == second["public_key"]
    assert first["device_id"].startswith("GRD-")


def test_device_identity_creation_verifies_secret_store_readback() -> None:
    with pytest.raises(RuntimeError, match="did not persist"):
        ensure_device_identity(DroppingSecretStore())
    with pytest.raises(RuntimeError, match="read-back does not match"):
        ensure_device_identity(ReplacingSecretStore())


def test_activation_request_proves_possession_and_detects_tamper() -> None:
    store = MemorySecretStore()
    request = build_activation_request(
        license_id="GRM-2026-000001",
        store=store,
        nonce="fixed-test-nonce",
        created_at="2026-08-30T10:00:00+00:00",
    )
    verified = verify_activation_request(request)
    assert verified["license_id"] == "GRM-2026-000001"

    tampered = dict(request)
    tampered["license_id"] = "GRM-2026-999999"
    with pytest.raises(ValueError, match="proof is invalid"):
        verify_activation_request(tampered)


def test_activation_request_rejects_input_coercion() -> None:
    store = MemorySecretStore()
    with pytest.raises(ValueError, match="license_id must be a string"):
        build_activation_request(license_id=123, store=store)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="nonce must contain"):
        build_activation_request(license_id="GRM-1", store=store, nonce="")
    with pytest.raises(ValueError, match="timezone offset"):
        build_activation_request(
            license_id="GRM-1",
            store=store,
            nonce="n",
            created_at="2026-08-30T10:00:00",
        )


def test_activation_verifier_rejects_noncanonical_signature_encoding() -> None:
    store = MemorySecretStore()
    request = build_activation_request(
        license_id="GRM-2026-000001",
        store=store,
        nonce="fixed-test-nonce",
        created_at="2026-08-30T10:00:00+00:00",
    )
    tampered = dict(request)
    tampered["proof"] = dict(request["proof"])
    tampered["proof"]["signature"] = request["proof"]["signature"] + "="
    with pytest.raises(ValueError, match="proof is invalid"):
        verify_activation_request(tampered)


def test_activation_verifier_rejects_wrong_field_types_before_signature_check() -> None:
    store = MemorySecretStore()
    request = build_activation_request(
        license_id="GRM-2026-000001",
        store=store,
        nonce="fixed-test-nonce",
        created_at="2026-08-30T10:00:00+00:00",
    )
    malformed = dict(request)
    malformed["nonce"] = 123
    with pytest.raises(ValueError, match="nonce must be a string"):
        verify_activation_request(malformed)


def test_activation_verifier_rejects_unknown_top_level_fields() -> None:
    store = MemorySecretStore()
    request = build_activation_request(
        license_id="GRM-2026-000001",
        store=store,
        nonce="fixed-test-nonce",
        created_at="2026-08-30T10:00:00+00:00",
    )
    request["authority"] = "production"
    with pytest.raises(ValueError, match="unsupported fields"):
        verify_activation_request(request)


def test_activation_verifier_rejects_unknown_or_missing_proof_fields() -> None:
    store = MemorySecretStore()
    request = build_activation_request(
        license_id="GRM-2026-000001",
        store=store,
        nonce="fixed-test-nonce",
        created_at="2026-08-30T10:00:00+00:00",
    )

    extra = dict(request)
    extra["proof"] = {**request["proof"], "authority": "production"}
    with pytest.raises(ValueError, match="unsupported fields"):
        verify_activation_request(extra)

    missing = dict(request)
    missing["proof"] = {"alg": "Ed25519"}
    with pytest.raises(ValueError, match="missing fields"):
        verify_activation_request(missing)
