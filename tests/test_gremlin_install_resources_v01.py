from __future__ import annotations

import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools.prepare_installer_resources_v01 import prepare


def test_installer_resources_stage_complete_workspace(tmp_path) -> None:
    private = Ed25519PrivateKey.generate()
    public = tmp_path / "issuer-public.pem"
    public.write_bytes(
        private.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    output = tmp_path / "resources"

    prepared = prepare(
        public_key=public,
        output=output,
        version="0.5.0-test",
        preview=True,
    )
    assert prepared == output
    assert (output / "issuer-public.pem").is_file()
    assert (output / "README-FIRST.txt").is_file()
    assert (output / "MCP-SETUP.md").is_file()
    assert (output / "PREVIEW_BUILD.txt").is_file()

    workspace = output / "workspace"
    for name in ("index.html", "app.js", "styles.css", "example-request.json"):
        assert (workspace / name).is_file(), name

    example = json.loads((workspace / "example-request.json").read_text(encoding="utf-8"))
    assert example["schema"] == "GREMLIN_CLIENT_PROTOTYPE_REQUEST_V0_1"

    metadata = json.loads((output / "build-metadata.json").read_text(encoding="utf-8"))
    assert metadata["schema"] == "GREMLIN_INSTALLER_RESOURCES_V0_2"
    assert metadata["onboarding"]["workspace"] is True
    assert metadata["private_key_included"] is False
