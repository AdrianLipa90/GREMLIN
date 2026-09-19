from __future__ import annotations

from datetime import date
import json
from pathlib import Path

from gremlin_mcp.install.update_manifest import load_update_manifest, verify_artifact
from gremlin_mcp.product.cli import main as issuer_main
from gremlin_mcp.product.license import generate_keypair


def test_update_issue_cli_hashes_artifact_and_emits_verifiable_manifest(tmp_path: Path) -> None:
    private_pem, public_pem, _ = generate_keypair()
    private = tmp_path / "issuer-private.pem"
    public = tmp_path / "issuer-public.pem"
    private.write_bytes(private_pem)
    public.write_bytes(public_pem)

    artifact = tmp_path / "GREMLIN-Early-Access-Linux-amd64.deb"
    artifact.write_bytes(b"release-artifact-v1" * 100)
    manifest_path = tmp_path / "GREMLIN-Early-Access-Linux-amd64.update.json"

    code = issuer_main([
        "update-issue",
        "--private", str(private),
        "--artifact", str(artifact),
        "--out", str(manifest_path),
        "--version", "0.5.0-ea.2",
        "--release-sequence", "2",
        "--channel", "EARLY_ACCESS",
        "--platform", "linux",
        "--architecture", "amd64",
        "--released-on", "2026-09-19",
    ])
    assert code == 0
    assert manifest_path.is_file()

    verified = load_update_manifest(
        manifest_path,
        public,
        today=date(2026, 9, 19),
    )
    assert verified["artifact_name"] == artifact.name
    assert verified["artifact_size"] == artifact.stat().st_size
    assert verified["release_sequence"] == 2
    assert verify_artifact(verified, artifact)["status"] == "PASS"

    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert raw["signature"]["algorithm"] == "Ed25519"
