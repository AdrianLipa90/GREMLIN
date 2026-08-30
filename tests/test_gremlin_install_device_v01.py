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


def test_device_identity_is_stable_after_first_creation() -> None:
    store = MemorySecretStore()
    first = ensure_device_identity(store)
    second = ensure_device_identity(store)
    assert first["status"] == "CREATED"
    assert second["status"] == "EXISTING"
    assert first["device_id"] == second["device_id"]
    assert first["public_key"] == second["public_key"]
    assert first["device_id"].startswith("GRD-")


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
