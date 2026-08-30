from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
from typing import Sequence

from .license import generate_keypair, issue_license, load_private_key


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _keygen(args: argparse.Namespace) -> int:
    private_pem, public_pem, key_id = generate_keypair()
    private_path = Path(args.private)
    public_path = Path(args.public)
    if private_path.exists() or public_path.exists():
        raise SystemExit("refusing to overwrite an existing key file")
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_bytes(private_pem)
    try:
        private_path.chmod(0o600)
    except OSError:
        pass
    public_path.write_bytes(public_pem)
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
    out = Path(args.out)
    if out.exists() and not args.force:
        raise SystemExit("output license already exists; pass --force to replace it")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ISSUED", "license_id": payload["license_id"], "out": str(out), "key_id": envelope["signature"]["key_id"]}, sort_keys=True))
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
    issue.add_argument("--max-sources", type=int, default=12)
    issue.add_argument("--commercial-use", action="store_true")
    issue.add_argument("--production-use", action="store_true")
    issue.add_argument("--hosted-service", action="store_true")
    issue.add_argument("--issuer", default="Adrian Lipa / Intention Lab")
    issue.add_argument("--force", action="store_true")
    issue.set_defaults(func=_issue)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
