from __future__ import annotations

import argparse
from typing import Any
from mcp.server import MCPServer

from gremlin_mcp import __version__
from gremlin_mcp.semantic_graph_transformer import SemanticGraphTransformer
from gremlin_mcp.semantic_graph_bestiary import build_bestiary_handoff, build_hive_exchange_candidate

mcp = MCPServer(
    "GREMLIN-SGT",
    title="GREMLIN Semantic Graph Transformer",
    description="Compile unstructured text into compact typed relation-token graphs.",
    instructions=(
        "Read-only candidate compiler. It does not mutate Hive, repositories, canon, or external systems. "
        "V0.1 is a deterministic reference kernel, not a trained neural transformer."
    ),
    version=__version__,
)

@mcp.tool()
def gremlin_semantic_graph_compile(
    documents: list[str],
    max_neighbors: int = 8,
    min_confidence: float = 0.52,
) -> dict[str, Any]:
    """Compile text into a compact typed semantic graph and relation bytecode."""
    return SemanticGraphTransformer(
        max_neighbors=max_neighbors,
        min_confidence=min_confidence,
    ).compile(documents)

@mcp.tool()
def gremlin_semantic_graph_causal_cone(
    compiled: dict[str, Any],
    seeds: list[str],
    depth: int = 2,
) -> dict[str, Any]:
    """Select the minimal bounded neighborhood needed around seed concepts."""
    return SemanticGraphTransformer.causal_cone(compiled, seeds, depth=depth)


@mcp.tool()
def gremlin_semantic_graph_handoff(
    compiled: dict[str, Any],
    subject_id: str,
    generation_id: str,
    task_id: str,
) -> dict[str, Any]:
    """Build the read-only SPIDER -> ELEPHANT -> BEES capability handoff plan."""
    return build_bestiary_handoff(
        compiled,
        subject_id=subject_id,
        generation_id=generation_id,
        task_id=task_id,
    )


@mcp.tool()
def gremlin_semantic_graph_hive_exchange_candidate(
    compiled: dict[str, Any],
    subject_id: str,
    generation_id: str,
) -> dict[str, Any]:
    """Build a content-addressed candidate envelope for the existing Hive ingest protocol."""
    return build_hive_exchange_candidate(
        compiled,
        subject_id=subject_id,
        generation_id=generation_id,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="GREMLIN Semantic Graph Transformer MCP server")
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8774, type=int)
    parser.add_argument("--path", default="/mcp")
    args = parser.parse_args()
    if args.transport == "stdio":
        mcp.run("stdio")
        return
    mcp.run("streamable-http", host=args.host, port=args.port, streamable_http_path=args.path, json_response=True)

if __name__ == "__main__":
    main()
