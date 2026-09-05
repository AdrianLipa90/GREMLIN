from __future__ import annotations

import argparse
from dataclasses import asdict
import os
from typing import Any

from mcp.server import MCPServer

from gremlin_mcp import __version__
from gremlin_mcp.hive_authority import HiveAuthorityRuntime

runtime = HiveAuthorityRuntime()

mcp = MCPServer(
    "GREMLIN-HIVE",
    title="GREMLIN Orbital Hive Memory",
    description=(
        "Single-authority shared semantic/orbital/phase working memory for GREMLIN components."
    ),
    instructions=(
        "This server is shared cognition only. It cannot grant repository-write, publication, "
        "production execution or canon authority. Durable mutations serialize through one "
        "SQLite/WAL subject-head authority and fail closed on stale or forked lineage."
    ),
    version=__version__,
)


def configure_state(state_path: str | None) -> HiveAuthorityRuntime:
    global runtime
    runtime.close()
    runtime = HiveAuthorityRuntime(state_path, orbit_count=36)
    return runtime


@mcp.tool()
def gremlin_hive_status() -> dict[str, Any]:
    return runtime.status()


@mcp.tool()
def gremlin_hive_place(
    subject_id: str,
    payload: dict[str, Any],
    priority: float,
    semantic_key: str,
    relation_phase: float,
    provenance: list[str] | None = None,
    dependencies: list[str] | None = None,
) -> dict[str, Any]:
    return asdict(
        runtime.place(
            subject_id=subject_id,
            payload=payload,
            priority=priority,
            semantic_key=semantic_key,
            relation_phase=relation_phase,
            provenance=provenance or (),
            dependencies=dependencies or (),
        )
    )


@mcp.tool()
def gremlin_hive_gates(
    subject_id: str,
    evidence_ready: bool | None = None,
    dependencies_closed: bool | None = None,
    contradiction_audited: bool | None = None,
    provenance_complete: bool | None = None,
    phase_coherent: bool | None = None,
) -> dict[str, Any]:
    changes = {
        key: value
        for key, value in {
            "evidence_ready": evidence_ready,
            "dependencies_closed": dependencies_closed,
            "contradiction_audited": contradiction_audited,
            "provenance_complete": provenance_complete,
            "phase_coherent": phase_coherent,
        }.items()
        if value is not None
    }
    if not changes:
        raise ValueError("at least one closure gate must be supplied")
    return asdict(runtime.update_gates(subject_id, **changes))


@mcp.tool()
def gremlin_hive_dispute(subject_id: str, contradiction_ref: str) -> dict[str, Any]:
    return asdict(runtime.dispute(subject_id, contradiction_ref))


@mcp.tool()
def gremlin_hive_latch(subject_id: str) -> dict[str, Any]:
    return asdict(runtime.latch(subject_id))


@mcp.tool()
def gremlin_hive_head(subject_id: str) -> dict[str, Any]:
    return asdict(runtime.head(subject_id))


@mcp.tool()
def gremlin_hive_table() -> dict[str, Any]:
    return {
        "schema": runtime.status()["hive_schema"],
        "ordering": "INNER_TO_OUTER_THEN_SEMANTIC_ANGLE_THEN_RELATION_PHASE",
        "authority": "SHARED_COGNITION_ONLY",
        "records": [asdict(record) for record in runtime.table()],
    }


@mcp.tool()
def gremlin_hive_history(subject_id: str) -> dict[str, Any]:
    return {
        "subject_id": subject_id,
        "authority": "SHARED_COGNITION_ONLY",
        "records": [asdict(record) for record in runtime.history(subject_id)],
    }


@mcp.tool()
def gremlin_hive_persisted(subject_id: str | None = None) -> dict[str, Any]:
    return {
        "authority": "SHARED_COGNITION_ONLY",
        "persistence": runtime.status()["persistence"],
        "records": list(runtime.persisted(subject_id)),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GREMLIN Orbital Hive Memory MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host")
    parser.add_argument("--port", default=8767, type=int, help="HTTP bind port")
    parser.add_argument("--path", default="/mcp", help="Streamable HTTP MCP path")
    parser.add_argument(
        "--state-path",
        default=os.environ.get("GREMLIN_HIVE_STATE_PATH"),
        help="authoritative Hive SQLite/WAL path; also read from GREMLIN_HIVE_STATE_PATH",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    configure_state(args.state_path)
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
