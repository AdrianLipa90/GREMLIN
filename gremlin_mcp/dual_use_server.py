from __future__ import annotations

from typing import Any

from gremlin_mcp.dual_use_policy import policy_api
from gremlin_mcp.server import mcp, main as _server_main


@mcp.tool()
def gremlin_dual_use_policy(
    operation: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate GREMLIN dual-use risk inheritance, policy envelopes or capability firewall decisions."""
    return policy_api(operation, payload)


def main() -> None:
    """Run the normal GREMLIN MCP server with the DUCL policy tool registered."""
    _server_main()


if __name__ == "__main__":
    main()
