from __future__ import annotations

import argparse
import json
from typing import Sequence

from .bundle import build_customer_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a validated GREMLIN customer delivery bundle")
    parser.add_argument("--distribution", required=True, help="wheel/source archive/customer distribution file")
    parser.add_argument("--public-key", required=True, help="issuer Ed25519 public key PEM")
    parser.add_argument("--profile", required=True, help="validated customer profile JSON")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--license", help="signed license JSON")
    group.add_argument("--license-key", help="file containing a compact GRM1 key")
    parser.add_argument("--extra", action="append", default=[], help="extra customer-visible file; repeatable")
    parser.add_argument("--out", required=True, help="output ZIP path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_customer_bundle(
        distribution_path=args.distribution,
        public_key_path=args.public_key,
        profile_path=args.profile,
        license_path=args.license,
        license_key_path=args.license_key,
        extra_paths=args.extra,
        output_path=args.out,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
