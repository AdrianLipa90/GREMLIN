from __future__ import annotations

import os
from pathlib import Path
import stat

import pytest

import gremlin_mcp.product.cli as license_cli
from gremlin_mcp.product.keycodec import verify_license_key
from gremlin_mcp.product.license import load_public_key
from tools.bootstrap_gremlin_issuer_v01 import bootstrap


def test_issuer_bootstrap_creates_stable_verifier_and_matching_smoke_key(tmp_path: Path) -> None:
    output = tmp_path / "issuer"
    result = bootstrap(output)
    private_key = output / "issuer-private.pem"
    public_key = output / "issuer-public.pem"
    smoke_key = output / "release-smoke-license.key"
    settings = output / "GITHUB-RELEASE-SETTINGS.txt"

    assert result["status"] == "READY"
    assert private_key.is_file()
    assert public_key.is_file()
    assert smoke_key.is_file()
    load_public_key(public_key)
    payload = verify_license_key(smoke_key.read_text(encoding="utf-8").strip(), public_key)
    assert payload["metadata"]["purpose"] == "release-pipeline-smoke-only"
    assert payload["features"] == ["MCP_STDIO", "PERSISTENT_STATE"]

    settings_text = settings.read_text(encoding="utf-8")
    assert "GREMLIN_ISSUER_PUBLIC_KEY_B64=" in settings_text
    assert "GREMLIN_RELEASE_SMOKE_GRM1=GRM1-" in settings_text
    assert "BEGIN PRIVATE KEY" not in settings_text
    assert private_key.read_text(encoding="utf-8") not in settings_text

    if os.name != "nt":
        for private_artifact in (
            private_key,
            output / "release-smoke-license.json",
            smoke_key,
            settings,
            output / "KEEP-PRIVATE-README.txt",
        ):
            assert stat.S_IMODE(private_artifact.stat().st_mode) & 0o077 == 0


def test_issuer_bootstrap_refuses_to_overwrite_authority(tmp_path: Path) -> None:
    output = tmp_path / "issuer"
    bootstrap(output)
    with pytest.raises(FileExistsError):
        bootstrap(output)


def test_product_keygen_creates_non_world_accessible_private_key(tmp_path: Path) -> None:
    private_key = tmp_path / "issuer-private.pem"
    public_key = tmp_path / "issuer-public.pem"
    assert license_cli.main([
        "keygen",
        "--private",
        str(private_key),
        "--public",
        str(public_key),
    ]) == 0
    assert private_key.is_file()
    assert public_key.is_file()
    if os.name != "nt":
        assert stat.S_IMODE(private_key.stat().st_mode) & 0o077 == 0


def test_product_keygen_removes_partial_private_key_if_public_write_fails(tmp_path: Path, monkeypatch) -> None:
    private_key = tmp_path / "issuer-private.pem"
    public_key = tmp_path / "issuer-public.pem"
    real_write = license_cli._write_new_file

    def fail_public(path: Path, data: bytes, *, private: bool) -> None:
        if not private:
            raise OSError("simulated public-key write failure")
        real_write(path, data, private=private)

    monkeypatch.setattr(license_cli, "_write_new_file", fail_public)
    with pytest.raises(OSError, match="simulated public-key write failure"):
        license_cli.main([
            "keygen",
            "--private",
            str(private_key),
            "--public",
            str(public_key),
        ])
    assert not private_key.exists()
    assert not public_key.exists()
