from __future__ import annotations

import argparse
from dataclasses import asdict
import os
from typing import Any

from mcp.server import MCPServer

from gremlin_mcp import __version__
from gremlin_mcp.hive_authority import HiveAuthorityRuntime
from gremlin_mcp.memory_exchange import ingest_exchange_bundle, ingest_exchange_envelope
from gremlin_mcp.memory_consolidation import build_consolidation_route
from gremlin_mcp.memory_anti_entropy import (
    apply_hive_delta,
    build_hive_inventory,
    build_hive_manifest,
    divergent_hive_buckets,
    export_hive_delta,
    plan_hive_delta,
)

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
    result = runtime.status()
    result["memory_information_exchange"] = {
        "status": "AVAILABLE",
        "tool": "gremlin_hive_exchange_ingest",
        "protocol_schema": "PHASENAV_MEMORY_INFORMATION_EXCHANGE_V0_1",
        "target_layer": "RELATIONAL",
        "automatic_latch": False,
    }
    result["memory_anti_entropy"] = {
        "status": "AVAILABLE",
        "inventory_tool": "gremlin_hive_sync_inventory",
        "manifest_tool": "gremlin_hive_sync_manifest",
        "delta_tool": "gremlin_hive_sync_delta",
        "apply_tool": "gremlin_hive_sync_apply",
        "scope": "EXCHANGE_MEMORY_ONLY_APPEND_ONLY",
        "automatic_latch": False,
    }
    result["memory_consolidation"] = {
        "status": "AVAILABLE_READ_ONLY",
        "route_tool": "gremlin_hive_consolidation_route",
        "source_layer": "EPISODIC",
        "derived_layer": "SEMANTIC",
        "direct_hive_ingest_allowed": False,
    }
    return result


@mcp.tool()
def gremlin_hive_exchange_ingest(
    envelope: dict[str, Any],
    priority: float = 0.82,
) -> dict[str, Any]:
    """Ingest a typed PhaseNav envelope into RELATIONAL Hive memory."""
    return ingest_exchange_envelope(
        runtime,
        envelope,
        priority=priority,
        consumer_id="GREMLIN-HIVE",
    )


@mcp.tool()
def gremlin_hive_exchange_bundle_ingest(
    bundle: dict[str, Any],
    priority: float = 0.82,
) -> dict[str, Any]:
    """Verify a portable lineage proof and ingest only its RELATIONAL target."""
    return ingest_exchange_bundle(
        runtime,
        bundle,
        priority=priority,
        consumer_id="GREMLIN-HIVE",
    )


@mcp.tool()
def gremlin_hive_sync_inventory(
    node_id: str = "GREMLIN-HIVE",
) -> dict[str, Any]:
    return build_hive_inventory(runtime, node_id=node_id)


@mcp.tool()
def gremlin_hive_sync_manifest(
    prefixes: list[str],
    node_id: str = "GREMLIN-HIVE",
) -> dict[str, Any]:
    return build_hive_manifest(runtime, node_id=node_id, prefixes=prefixes)


@mcp.tool()
def gremlin_hive_sync_delta(
    receiver_inventory: dict[str, Any],
    receiver_manifest: dict[str, Any],
    node_id: str = "GREMLIN-HIVE",
) -> dict[str, Any]:
    sender_inventory = build_hive_inventory(runtime, node_id=node_id)
    prefixes = divergent_hive_buckets(sender_inventory, receiver_inventory)
    sender_manifest = build_hive_manifest(runtime, node_id=node_id, prefixes=prefixes)
    plan = plan_hive_delta(
        sender_inventory,
        receiver_inventory,
        sender_manifest,
        receiver_manifest,
    )
    return {
        "sender_inventory": sender_inventory,
        "sender_manifest": sender_manifest,
        "plan": plan,
        "delta": export_hive_delta(runtime, plan),
    }


@mcp.tool()
def gremlin_hive_sync_apply(
    delta: dict[str, Any],
    node_id: str = "GREMLIN-HIVE",
    priority: float = 0.82,
) -> dict[str, Any]:
    return apply_hive_delta(
        runtime,
        delta,
        receiver_node_id=node_id,
        priority=priority,
    )


@mcp.tool()
def gremlin_hive_consolidation_route(
    plan: dict[str, Any],
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate PhaseNav consolidation and return the admitted SEMANTIC->RELATIONAL route."""
    return build_consolidation_route(plan, receipt)


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
