from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from tools.gremlin_client_protocol_v01 import run_client_request


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gremlin-client-v01",
        description="Compile an audited GREMLIN candidate into PhaseNav IR, build a reference prototype, and return its experiment receipt.",
    )
    parser.add_argument("request", type=Path, help="Path to GREMLIN_CLIENT_PROTOTYPE_REQUEST_V0_1 JSON")
    parser.add_argument("--output", type=Path, default=None, help="Optional response JSON path")
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    request = json.loads(args.request.read_text(encoding="utf-8"))
    response = run_client_request(request)
    if args.compact:
        payload = json.dumps(response, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    else:
        payload = json.dumps(response, sort_keys=True, indent=2, ensure_ascii=False)
    payload += "\n"

    if args.output is None:
        print(payload, end="")
    else:
        args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
