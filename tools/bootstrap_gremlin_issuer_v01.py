from __future__ import annotations

import argparse
import base64
from datetime import date
import json
import os
from pathlib import Path
import secrets

from gremlin_mcp.product.keycodec import encode_license_key
from gremlin_mcp.product.license import generate_keypair, issue_license, load_private_key


def _write_new(path: Path, data: bytes, *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing issuer bootstrap file: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if private and os.name != "nt":
        fd = os.open(path, flags, 0o600)
    else:
        fd = os.open(path, flags, 0o644)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    if private:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def bootstrap(output_dir: Path) -> dict[str, str]:
    output_dir = output_dir.expanduser().resolve()
    private_path = output_dir / "issuer-private.pem"
    public_path = output_dir / "issuer-public.pem"
    smoke_json = output_dir / "release-smoke-license.json"
    smoke_key = output_dir / "release-smoke-license.key"
    github_values = output_dir / "GITHUB-RELEASE-SETTINGS.txt"
    instructions = output_dir / "KEEP-PRIVATE-README.txt"

    for target in (private_path, public_path, smoke_json, smoke_key, github_values, instructions):
        if target.exists():
            raise FileExistsError(f"refusing to overwrite existing issuer bootstrap file: {target}")

    private_pem, public_pem, key_id = generate_keypair()
    _write_new(private_path, private_pem, private=True)
    _write_new(public_path, public_pem)

    today = date.today().isoformat()
    envelope = issue_license(
        {
            "schema": "GREMLIN_LICENSE_V0_1",
            "license_id": f"CI-SMOKE-{secrets.token_hex(8).upper()}",
            "product": "GREMLIN",
            "edition": "RESEARCH",
            "customer": "release-smoke-ci",
            "issued_at": today,
            "not_before": today,
            "expires_at": "2036-12-31",
            "updates_until": "2036-12-31",
            "seats": 1,
            "devices": 1,
            "features": ["MCP_STDIO", "PERSISTENT_STATE"],
            "limits": {"max_workers": 1, "max_sources": 1},
            "usage": {
                "commercial_use": False,
                "production_use": False,
                "hosted_service": False,
            },
            "metadata": {
                "issuer": "Adrian Lipa / Intention Lab",
                "purpose": "release-pipeline-smoke-only",
                "profile_required": False,
            },
        },
        load_private_key(private_path),
    )
    compact = encode_license_key(envelope)
    _write_new(smoke_json, (json.dumps(envelope, indent=2, sort_keys=True) + "\n").encode("utf-8"), private=True)
    _write_new(smoke_key, (compact + "\n").encode("utf-8"), private=True)

    public_b64 = base64.b64encode(public_pem).decode("ascii")
    settings_text = (
        "GREMLIN EARLY ACCESS RELEASE — ONE-TIME GITHUB SETTINGS\n"
        "========================================================\n\n"
        "Repository variable (not secret):\n"
        f"GREMLIN_ISSUER_PUBLIC_KEY_B64={public_b64}\n\n"
        "Actions secret:\n"
        f"GREMLIN_RELEASE_SMOKE_GRM1={compact}\n\n"
        "After these two values are configured, run the manual workflow:\n"
        "GREMLIN Early Access Release v0.1\n"
    )
    _write_new(github_values, settings_text.encode("utf-8"), private=True)

    private_readme = (
        "KEEP THIS DIRECTORY PRIVATE AND BACKED UP.\n\n"
        "issuer-private.pem is the GREMLIN commercial signing authority.\n"
        "Do not commit it to GitHub, attach it to a customer bundle, email it,\n"
        "or place it inside an installer. Losing it means future customer keys\n"
        "cannot be signed for installers containing this issuer public key.\n\n"
        "issuer-public.pem is safe to publish and is embedded in release installers.\n"
        "release-smoke-license.key is only for the protected release CI smoke test.\n"
        "GITHUB-RELEASE-SETTINGS.txt contains the values to configure once in GitHub.\n"
    )
    _write_new(instructions, private_readme.encode("utf-8"), private=True)

    return {
        "status": "READY",
        "output_dir": str(output_dir),
        "issuer_private_key": str(private_path),
        "issuer_public_key": str(public_path),
        "key_id": key_id,
        "release_smoke_key": str(smoke_key),
        "github_settings": str(github_values),
        "next_step": "Configure the two GitHub values from GITHUB-RELEASE-SETTINGS.txt, then run GREMLIN Early Access Release v0.1.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create the one-time GREMLIN Early Access issuer authority locally. Never run this in CI."
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="new private directory outside the repository, e.g. ~/gremlin-issuer",
    )
    args = parser.parse_args()
    print(json.dumps(bootstrap(args.output_dir), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
