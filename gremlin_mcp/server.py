from __future__ import annotations

import argparse
from typing import Any

from mcp.server import MCPServer

from gremlin_mcp import __version__
from gremlin_mcp.core import (
    bestiary_manifest,
    plan_bestiary,
    run_prototype,
    species_profile,
    status,
)

mcp = MCPServer(
    "GREMLIN",
    title="GREMLIN Bestiary",
    description="Standalone research MCP adapter for GREMLIN Bestiary scheduling and reference execution.",
    instructions=(
        "GREMLIN MCP is a research/candidate interface. Use gremlin_bestiary to inspect "
        "the animal topology, gremlin_species for one role, gremlin_plan to build a "
        "mass-orbit/vector lane plan, and gremlin_prototype for the existing fail-closed "
        "reference prototype pipeline. MCP calls never grant production execution or canon authority."
    ),
    version=__version__,
)


@mcp.tool()
def gremlin_status() -> dict[str, Any]:
    """Return MCP mode, capabilities, topology and fail-closed authority state."""
    return status()


@mcp.tool()
def gremlin_bestiary() -> dict[str, Any]:
    """List GREMLIN animals, their roles, scheduler mass/orbit and cadence data."""
    return bestiary_manifest()


@mcp.tool()
def gremlin_species(species: str) -> dict[str, Any]:
    """Inspect one GREMLIN animal by name, for example SPIDER, OWL or BELZEBUB."""
    return species_profile(species)


@mcp.tool()
def gremlin_plan(route_counts: dict[str, int], vector_width: int = 8) -> dict[str, Any]:
    """Build a deterministic mass-orbit/vector-lane execution plan for routed work."""
    return plan_bestiary(route_counts, vector_width=vector_width)


@mcp.tool()
def gremlin_prototype(request: dict[str, Any]) -> dict[str, Any]:
    """Run GREMLIN's existing reference candidate -> PhaseNav IR -> prototype -> test pipeline."""
    return run_prototype(request)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GREMLIN Bestiary MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host")
    parser.add_argument("--port", default=8766, type=int, help="HTTP bind port")
    parser.add_argument("--path", default="/mcp", help="Streamable HTTP MCP path")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.transport == "stdio":
        mcp.run("stdio")
        return
    mcp.run(
        "streamable-http",
        host=args.host,
        port=args.port,
        streamable_http_path=args.path,
        json_response=True,
    )


if __name__ == "__main__":
    main()
