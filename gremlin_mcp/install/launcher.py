from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Sequence


def _mode(argv0: str, args: Sequence[str]) -> tuple[str, list[str]]:
    stem = Path(argv0).stem.casefold()
    if stem in {"gremlinctl", "gremlinctl.exe"}:
        return "ctl", list(args)
    if stem in {"gremlin-product-mcp", "gremlin-product-mcp.exe"}:
        return "product-mcp", list(args)
    if args and args[0] in {"ctl", "product-mcp"}:
        return str(args[0]), list(args[1:])
    configured = os.environ.get("GREMLIN_RUNTIME_MODE", "").strip().casefold()
    if configured in {"ctl", "product-mcp"}:
        return configured, list(args)
    raise SystemExit("GREMLIN runtime mode is unresolved; invoke as gremlinctl or gremlin-product-mcp")


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    mode, forwarded = _mode(sys.argv[0], args)
    original = sys.argv
    try:
        sys.argv = [original[0], *forwarded]
        if mode == "ctl":
            from gremlin_mcp.install.cli import main as ctl_main

            return int(ctl_main(forwarded))
        from gremlin_mcp.product_server import main as product_main

        product_main()
        return 0
    finally:
        sys.argv = original


if __name__ == "__main__":
    raise SystemExit(main())
