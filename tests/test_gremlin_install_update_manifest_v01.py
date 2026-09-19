from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path

import pytest

from gremlin_mcp.install.update_manifest import (
    ENVELOPE_SCHEMA,
    MANIFEST_SCHEMA,
    UpdateManifestError,
    issue_update_manifest,
    load_update_manifest,
    normalize_manifest,
    update_eligibility,
    verify_artifact,
    verify_update_manifest,
)
from gremlin_mcp.product.license import generate_keypair, load_private_key, load_public_key


def _keys(tmp_path: Path):
    private_pem, public_pem, _ = generate_keypair()
    private_path = tmp_path / "issuer-private.pem"
    public_path = tmp_path / "issuer-public.pem"
    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)
    return private_path, public_path


def _artifact(tmp_path: Path, name: str = "GREMLIN-Early-Access-Linux-amd64.deb") -> Path:
    target = tmp_path / name
    target.write_bytes(b"GREMLIN-update-fixture\x00" * 37)
    return target


def _manifest(artifact: Path, **overrides):
    raw = artifact.read_bytes()
    value = {
        "schema": MANIFEST_SCHEMA,
        "product": "GREMLIN",
        "version": "0.5.0-ea.2",
        "release_sequence": 2,
        "channel": "EARLY_ACCESS",
        "platform": "linux",
        "architecture": "amd64",
        "artifact_name": artifact.name,
        "artifact_sha256": hashlib.sha256(raw).hexdigest(),
        "artifact_size": len(raw),
        "released_on": "2026-09-19",
    }
    value.update(overrides)
    return value


def test_signed_update_manifest_roundtrip_and_artifact_digest(tmp_path) -> None:
    private_path, public_path = _keys(tmp_path)
    artifact = _artifact(tmp_path)
    envelope = issue_update_manifest(_manifest(artifact), load_private_key(private_path))

    assert envelope["schema"] == ENVELOPE_SCHEMA
    verified = verify_update_manifest(
        envelope,
        load_public_key(public_path),
        today=date(2026, 9, 19),
    )
    assert verified["version"] == "0.5.0-ea.2"
    assert verified["release_sequence"] == 2

    artifact_receipt = verify_artifact(verified, artifact)
    assert artifact_receipt["status"] == "PASS"
    assert artifact_receipt["artifact_sha256"] == verified["artifact_sha256"]


def test_update_manifest_signature_fails_after_payload_tamper(tmp_path) -> None:
    private_path, public_path = _keys(tmp_path)
    artifact = _artifact(tmp_path)
    envelope = issue_update_manifest(_manifest(artifact), load_private_key(private_path))
    envelope["manifest"]["version"] = "9.9.9"

    with pytest.raises(UpdateManifestError, match="signature is invalid"):
        verify_update_manifest(envelope, load_public_key(public_path), today=date(2026, 9, 19))


def test_update_manifest_rejects_future_release_and_path_traversal(tmp_path) -> None:
    private_path, public_path = _keys(tmp_path)
    artifact = _artifact(tmp_path)
    future = issue_update_manifest(
        _manifest(artifact, released_on="2026-09-20"),
        load_private_key(private_path),
    )
    with pytest.raises(UpdateManifestError, match="future"):
        verify_update_manifest(future, load_public_key(public_path), today=date(2026, 9, 19))

    with pytest.raises(UpdateManifestError, match="safe basename"):
        normalize_manifest(_manifest(artifact, artifact_name="../evil.deb"))


def test_update_artifact_size_and_digest_are_both_bound(tmp_path) -> None:
    private_path, public_path = _keys(tmp_path)
    artifact = _artifact(tmp_path)
    envelope = issue_update_manifest(_manifest(artifact), load_private_key(private_path))
    manifest = verify_update_manifest(
        envelope,
        load_public_key(public_path),
        today=date(2026, 9, 19),
    )

    artifact.write_bytes(artifact.read_bytes() + b"tamper")
    with pytest.raises(UpdateManifestError, match="size mismatch"):
        verify_artifact(manifest, artifact)

    artifact = _artifact(tmp_path)
    original = artifact.read_bytes()
    artifact.write_bytes(bytes([original[0] ^ 1]) + original[1:])
    with pytest.raises(UpdateManifestError, match="SHA-256 mismatch"):
        verify_artifact(manifest, artifact)


def test_update_eligibility_separates_signature_from_entitlement(tmp_path) -> None:
    artifact = _artifact(tmp_path)
    manifest = _manifest(artifact)

    eligible = update_eligibility(
        manifest,
        license_payload={"updates_until": "2026-12-31"},
        platform="linux",
        architecture="amd64",
    )
    assert eligible["eligible"] is True
    assert eligible["reasons"] == []

    expired = update_eligibility(
        manifest,
        license_payload={"updates_until": "2026-09-18"},
        platform="linux",
        architecture="amd64",
    )
    assert expired["eligible"] is False
    assert expired["reasons"] == ["UPDATE_WINDOW_EXPIRED"]

    wrong_platform = update_eligibility(
        manifest,
        license_payload={"updates_until": "2026-12-31"},
        platform="windows",
        architecture="amd64",
    )
    assert wrong_platform["eligible"] is False
    assert wrong_platform["reasons"] == ["PLATFORM_MISMATCH"]


def test_load_update_manifest_rejects_duplicate_json_keys(tmp_path) -> None:
    _private_path, public_path = _keys(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        '{"schema":"GREMLIN_UPDATE_ENVELOPE_V0_1","schema":"GREMLIN_UPDATE_ENVELOPE_V0_1"}',
        encoding="utf-8",
    )
    with pytest.raises(UpdateManifestError, match="duplicate JSON key"):
        load_update_manifest(manifest_path, public_path, today=date(2026, 9, 19))
