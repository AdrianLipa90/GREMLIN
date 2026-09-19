from __future__ import annotations

import argparse
import hashlib
from datetime import date
import json
import os
from pathlib import Path
from typing import Sequence

from .keycodec import encode_license_key
from .license import generate_keypair, issue_license, load_private_key
from gremlin_mcp.install.update_manifest import issue_update_manifest


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _write_new_file(path: Path, data: bytes, *, private: bool) -> None:
    """Create one key file exclusively and durably without permissive defaults."""
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    mode = 0o600 if private else 0o644
    fd = os.open(path, flags, mode)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _keygen(args: argparse.Namespace) -> int:
    private_pem, public_pem, key_id = generate_keypair()
    private_path = Path(args.private)
    public_path = Path(args.public)
    if private_path.exists() or public_path.exists():
        raise SystemExit("refusing to overwrite an existing key file")

    created_private = False
    try:
        _write_new_file(private_path, private_pem, private=True)
        created_private = True
        _write_new_file(public_path, public_pem, private=False)
    except BaseException as exc:
        if created_private:
            try:
                private_path.unlink(missing_ok=True)
            except OSError as cleanup_exc:
                raise RuntimeError(
                    f"issuer key generation failed and private-key cleanup also failed: {cleanup_exc}"
                ) from exc
        raise

    print(json.dumps({"status": "CREATED", "key_id": key_id, "private": str(private_path), "public": str(public_path)}, sort_keys=True))
    return 0


def _issue(args: argparse.Namespace) -> int:
    features = _split_csv(args.features)
    payload = {
        "schema": "GREMLIN_LICENSE_V0_1",
        "license_id": args.license_id,
        "product": "GREMLIN",
        "edition": args.edition,
        "customer": args.customer,
        "issued_at": args.issued_at or date.today().isoformat(),
        "not_before": args.not_before or args.issued_at or date.today().isoformat(),
        "expires_at": args.expires_at,
        "updates_until": args.updates_until,
        "seats": args.seats,
        "devices": args.devices,
        "features": features,
        "limits": {
            "max_workers": args.max_workers,
            "max_sources": args.max_sources,
        },
        "usage": {
            "commercial_use": args.commercial_use,
            "production_use": args.production_use,
            "hosted_service": args.hosted_service,
        },
        "metadata": {
            "issuer": args.issuer,
        },
    }
    envelope = issue_license(payload, load_private_key(args.private))
    compact_key = encode_license_key(envelope)
    out = Path(args.out)
    if out.exists() and not args.force:
        raise SystemExit("output license already exists; pass --force to replace it")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    key_out = None
    if args.key_out:
        key_path = Path(args.key_out)
        if key_path.exists() and not args.force:
            raise SystemExit("output license key already exists; pass --force to replace it")
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text(compact_key + "\n", encoding="utf-8")
        key_out = str(key_path)
    result = {
        "status": "ISSUED",
        "license_id": payload["license_id"],
        "out": str(out),
        "key_out": key_out,
        "key_id": envelope["signature"]["key_id"],
    }
    if args.print_key:
        result["license_key"] = compact_key
    print(json.dumps(result, sort_keys=True))
    return 0


def _file_sha256_and_size(path: Path) -> tuple[str, int]:
    if not path.is_file():
        raise SystemExit(f"artifact is missing or not a regular file: {path}")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    if size < 1:
        raise SystemExit("refusing to issue an update manifest for an empty artifact")
    return digest.hexdigest(), size


def _issue_update(args: argparse.Namespace) -> int:
    artifact = Path(args.artifact)
    digest, size = _file_sha256_and_size(artifact)
    manifest = {
        "schema": "GREMLIN_UPDATE_MANIFEST_V0_1",
        "product": "GREMLIN",
        "version": args.version,
        "release_sequence": args.release_sequence,
        "channel": args.channel,
        "platform": args.platform,
        "architecture": args.architecture,
        "artifact_name": artifact.name,
        "artifact_sha256": digest,
        "artifact_size": size,
        "released_on": args.released_on or date.today().isoformat(),
    }
    envelope = issue_update_manifest(manifest, load_private_key(args.private))
    out = Path(args.out)
    if out.exists() and not args.force:
        raise SystemExit("output update manifest already exists; pass --force to replace it")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "ISSUED",
        "out": str(out),
        "version": manifest["version"],
        "release_sequence": manifest["release_sequence"],
        "platform": manifest["platform"],
        "architecture": manifest["architecture"],
        "artifact_name": manifest["artifact_name"],
        "artifact_sha256": digest,
        "artifact_size": size,
        "key_id": envelope["signature"]["key_id"],
    }, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GREMLIN product license issuer")
    sub = parser.add_subparsers(dest="command", required=True)

    keygen = sub.add_parser("keygen", help="generate an Ed25519 issuer keypair")
    keygen.add_argument("--private", required=True, help="private key PEM output path")
    keygen.add_argument("--public", required=True, help="public key PEM output path")
    keygen.set_defaults(func=_keygen)

    issue = sub.add_parser("issue", help="issue one signed GREMLIN license")
    issue.add_argument("--private", required=True, help="issuer private key PEM path")
    issue.add_argument("--out", required=True, help="license JSON output path")
    issue.add_argument("--key-out", help="optional compact GRM1 license-key output path")
    issue.add_argument("--print-key", action="store_true", help="include compact GRM1 key in stdout JSON")
    issue.add_argument("--license-id", required=True)
    issue.add_argument("--customer", required=True, help="customer label or pseudonymous customer hash")
    issue.add_argument("--edition", required=True, choices=("RESEARCH", "PERSONAL_PRO", "COMMERCIAL", "ENTERPRISE"))
    issue.add_argument("--features", required=True, help="comma-separated entitlement names")
    issue.add_argument("--issued-at")
    issue.add_argument("--not-before")
    issue.add_argument("--expires-at")
    issue.add_argument("--updates-until")
    issue.add_argument("--seats", type=int, default=1)
    issue.add_argument("--devices", type=int, default=1)
    issue.add_argument("--max-workers", type=int, default=4)
    issue.add_argument("--max-sources", type=int, default=24)
    issue.add_argument("--commercial-use", action="store_true")
    issue.add_argument("--production-use", action="store_true")
    issue.add_argument("--hosted-service", action="store_true")
    issue.add_argument("--issuer", default="Adrian Lipa / Intention Lab")
    issue.add_argument("--force", action="store_true")
    issue.set_defaults(func=_issue)

    update_issue = sub.add_parser("update-issue", help="issue one signed offline GREMLIN update manifest")
    update_issue.add_argument("--private", required=True, help="issuer private key PEM path")
    update_issue.add_argument("--artifact", required=True, help="release artifact to hash and bind")
    update_issue.add_argument("--out", required=True, help="signed update manifest JSON output path")
    update_issue.add_argument("--version", required=True)
    update_issue.add_argument("--release-sequence", required=True, type=int)
    update_issue.add_argument("--channel", required=True, choices=("PREVIEW", "EARLY_ACCESS", "STABLE"))
    update_issue.add_argument("--platform", required=True, choices=("windows", "linux"))
    update_issue.add_argument("--architecture", default="amd64", choices=("amd64",))
    update_issue.add_argument("--released-on")
    update_issue.add_argument("--force", action="store_true")
    update_issue.set_defaults(func=_issue_update)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
