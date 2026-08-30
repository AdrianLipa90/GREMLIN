from __future__ import annotations

from pathlib import Path

import pytest

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


def test_issuer_bootstrap_refuses_to_overwrite_authority(tmp_path: Path) -> None:
    output = tmp_path / "issuer"
    bootstrap(output)
    with pytest.raises(FileExistsError):
        bootstrap(output)
