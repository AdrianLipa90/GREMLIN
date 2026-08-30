from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from gremlin_mcp.product.license import load_public_key


def prepare(*, public_key: Path, output: Path, version: str, preview: bool) -> Path:
    if not public_key.is_file():
        raise ValueError("issuer public key file is required")
    # Fail closed if a private/non-Ed25519 key is supplied.
    load_public_key(public_key)

    output.mkdir(parents=True, exist_ok=True)
    destination = output / "issuer-public.pem"
    shutil.copy2(public_key, destination)

    profiles = output / "profiles"
    profiles.mkdir(exist_ok=True)
    for source_name in (
        "client_profile_research_lab.json",
        "client_profile_software_engineering.json",
    ):
        source = Path("examples/product") / source_name
        if source.is_file():
            shutil.copy2(source, profiles / source_name)

    license_source = Path("LICENSE")
    if not license_source.is_file():
        raise ValueError("repository LICENSE is required for installer resources")
    shutil.copy2(license_source, output / "LICENSE.txt")

    for name in ("README-FIRST.txt", "MCP-SETUP.md"):
        source = Path("packaging/common") / name
        if not source.is_file():
            raise ValueError(f"customer onboarding resource is required: {source}")
        shutil.copy2(source, output / name)

    metadata = {
        "schema": "GREMLIN_INSTALLER_RESOURCES_V0_2",
        "version": str(version),
        "preview": bool(preview),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "private_key_included": False,
        "onboarding": {
            "control_center": True,
            "license_activation": "GRM1_OR_SIGNED_JSON",
            "provider_autodetect": True,
            "ready_gate": True,
        },
    }
    (output / "build-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if preview:
        (output / "PREVIEW_BUILD.txt").write_text(
            "GREMLIN PREVIEW BUILD\nThis package uses an ephemeral CI verifier and is not a commercial release.\n",
            encoding="utf-8",
        )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage GREMLIN installer resources")
    parser.add_argument("--public-key", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    print(prepare(public_key=args.public_key, output=args.output, version=args.version, preview=args.preview))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
