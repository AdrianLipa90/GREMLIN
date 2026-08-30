from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile
from typing import Any, Iterable

from .keycodec import verify_license_key
from .license import load_license, load_public_key
from .profile import load_client_profile

BUNDLE_SCHEMA = "GREMLIN_CUSTOMER_BUNDLE_V0_1"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read(path: str | Path, *, field: str) -> tuple[Path, bytes]:
    p = Path(path)
    if not p.is_file():
        raise ValueError(f"{field} must point to an existing file")
    return p, p.read_bytes()


def _safe_leaf(name: str) -> str:
    leaf = Path(name).name
    if not leaf or leaf in {".", ".."}:
        raise ValueError("bundle filename must be a safe leaf name")
    return leaf


def _config_template(*, use_compact_key: bool) -> dict[str, Any]:
    env = {
        "GREMLIN_LICENSE_PUBLIC_KEY": "__GREMLIN_BUNDLE_DIR__/issuer-public.pem",
        "GREMLIN_CLIENT_PROFILE": "__GREMLIN_BUNDLE_DIR__/client-profile.json",
        "GREMLIN_MCP_STATE_PATH": "__GREMLIN_DATA_DIR__/gremlin-worker.sqlite3",
    }
    if use_compact_key:
        env["GREMLIN_LICENSE_KEY"] = "__PASTE_CONTENTS_OF_LICENSE_KEY_FILE__"
    else:
        env["GREMLIN_LICENSE_PATH"] = "__GREMLIN_BUNDLE_DIR__/license.json"
    return {
        "mcpServers": {
            "gremlin": {
                "command": "gremlin-product-mcp",
                "args": ["--transport", "stdio"],
                "env": env,
            }
        }
    }


def build_customer_bundle(
    *,
    distribution_path: str | Path,
    public_key_path: str | Path,
    profile_path: str | Path,
    output_path: str | Path,
    license_path: str | Path | None = None,
    license_key_path: str | Path | None = None,
    extra_paths: Iterable[str | Path] = (),
) -> dict[str, Any]:
    """Create a validated, hash-manifested customer ZIP without issuer private material."""
    if bool(license_path) == bool(license_key_path):
        raise ValueError("configure exactly one of license_path or license_key_path")

    distribution, distribution_bytes = _read(distribution_path, field="distribution_path")
    public_key_file, public_key_bytes = _read(public_key_path, field="public_key_path")
    profile_file, profile_bytes = _read(profile_path, field="profile_path")
    # Parse the configured public key now so a private/wrong key cannot be shipped by accident.
    load_public_key(public_key_file)

    if license_path is not None:
        license_file, license_bytes = _read(license_path, field="license_path")
        payload = load_license(license_file, public_key_file)
        license_arcname = "license.json"
        compact = False
    else:
        license_file, license_bytes = _read(license_key_path, field="license_key_path")  # type: ignore[arg-type]
        compact_key = license_bytes.decode("utf-8").strip()
        payload = verify_license_key(compact_key, public_key_file)
        license_arcname = "license.key"
        compact = True

    profile = load_client_profile(profile_file, payload)

    entries: dict[str, bytes] = {
        f"distribution/{_safe_leaf(distribution.name)}": distribution_bytes,
        "issuer-public.pem": public_key_bytes,
        license_arcname: license_bytes,
        "client-profile.json": profile_bytes,
        "mcp-stdio-config.example.json": (
            json.dumps(_config_template(use_compact_key=compact), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8"),
    }

    for raw in extra_paths:
        extra, data = _read(raw, field="extra_path")
        leaf = _safe_leaf(extra.name)
        lowered = leaf.casefold()
        if "private" in lowered and (lowered.endswith(".pem") or lowered.endswith(".key")):
            raise ValueError("refusing to include a file that appears to be private key material")
        arcname = f"extras/{leaf}"
        if arcname in entries:
            raise ValueError(f"duplicate customer bundle path: {arcname}")
        entries[arcname] = data

    readme = f"""GREMLIN AI Research Orchestrator — Customer Bundle v0.1

License ID: {payload['license_id']}
Edition: {payload['edition']}
Client profile: {profile['client_id']}

1. Install the GREMLIN distribution from distribution/.
2. Place this bundle in a customer-controlled directory.
3. Configure your MCP client using mcp-stdio-config.example.json.
4. Replace __GREMLIN_BUNDLE_DIR__ and __GREMLIN_DATA_DIR__ placeholders with absolute paths.
5. Call gremlin_product_status or gremlin_license_status to verify admission.

The issuer private signing key is not part of a customer bundle.
Streamable HTTP v0.1 is loopback-only; remote transport requires a separate authenticated layer.
"""
    entries["README.txt"] = readme.encode("utf-8")

    files_manifest = {
        name: {"sha256": _sha256(data), "size": len(data)}
        for name, data in sorted(entries.items())
    }
    manifest_core = {
        "schema": BUNDLE_SCHEMA,
        "product": "GREMLIN",
        "license_id": payload["license_id"],
        "edition": payload["edition"],
        "client_id": profile["client_id"],
        "profile_commitment": profile["profile_commitment"],
        "files": files_manifest,
    }
    manifest_core["bundle_commitment"] = hashlib.blake2b(
        b"GREMLIN-CUSTOMER-BUNDLE/v0.1\0"
        + json.dumps(manifest_core, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
        digest_size=32,
    ).hexdigest()
    entries["manifest.json"] = (
        json.dumps(manifest_core, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        raise ValueError("output customer bundle already exists")
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(entries.items()):
            archive.writestr(name, data)

    return {
        "schema": BUNDLE_SCHEMA,
        "status": "CREATED",
        "output": str(out),
        "license_id": payload["license_id"],
        "edition": payload["edition"],
        "client_id": profile["client_id"],
        "file_count": len(entries),
        "bundle_commitment": manifest_core["bundle_commitment"],
        "zip_sha256": _sha256(out.read_bytes()),
    }
