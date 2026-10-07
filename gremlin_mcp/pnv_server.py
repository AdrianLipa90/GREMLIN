from __future__ import annotations

import os

# Native PNV admission is the default for this entrypoint.
# The legacy MCP remains available explicitly as gremlin-legacy-mcp.
os.environ.setdefault("GREMLIN_PNV_NATIVE", "1")

from gremlin_mcp.server_with_hive import main as _legacy_hive_main


def main() -> None:
    _legacy_hive_main()


if __name__ == "__main__":
    main()
