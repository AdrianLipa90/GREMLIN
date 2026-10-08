from __future__ import annotations

import argparse
from dataclasses import asdict
import os
from typing import Any

from mcp.server import MCPServer

from gremlin_mcp import __version__
from gremlin_mcp.owl_runtime_audit import owl_runtime_boundary
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
from gremlin_mcp.orbital_hive_memory import HIVE_SCHEMA

runtime = HiveAuthorityRuntime(orbit_count=36)

mcp = MCPServer(
    "GREMLIN-HIVE",
    title="GREMLIN Orbital Hive Memory",
    description=(
        "Shared semantic/orbital/phase working memory for GREMLIN components. "
        "Importance determines orbit, meaning determines reference angle, supplied relation "
        "phase determines phase position, and complete closure gates trigger an append-only latch."
    ),
    instructions=(
        "This server is shared cognition only. It cannot grant repository-write, publication, "
        "production execution or canon authority. Place information with an explicit priority, "
        "semantic key, relation phase and provenance. Use gate updates only for independently "
        "verified closure conditions. Disputes preserve lineage and block latching until a new "
        "audited child is explicitly placed. Locked records are immutable."
    ),
    version=__version__,
)


def _record(record: Any) -> dict[str, Any]:
    return asdict(record)


def configure_state(state_path: str | None) -> None:
    """Replace process state with one fail-closed Hive authority runtime.

    A durable runtime owns the SQLite transaction boundary for hydration, mutation,
    head validation and append. The replacement runtime is constructed and validated
    before the currently active runtime is closed, so a bad state path never silently
    resets the server to empty process memory.
    """
    global runtime
    normalized = None if state_path is None or not str(state_path).strip() else str(state_path)
    candidate = HiveAuthorityRuntime(normalized, orbit_count=36)
    previous = runtime
    try:
        previous.close()
    except Exception:
        candidate.close()
        raise
    runtime = candidate


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_status() -> dict[str, Any]:
    """Return Hive authority, schema and current flat-ring head count."""
    status = runtime.status()
    return {
        "schema": HIVE_SCHEMA,
        "status": status["status"],
        "orbit_count": status["orbit_count"],
        "head_count": status["head_count"],
        "persistence": status["persistence"],
        "state_path": status["state_path"],
        "authority": status["authority"],
        "production_runtime_write": status["production_runtime_write"],
        "execution_admitted": status["execution_admitted"],
        "canon_allowed": status["canon_allowed"],
        "memory_information_exchange": {
            "status": "AVAILABLE",
            "tool": "gremlin_hive_exchange_ingest",
            "protocol_schema": "PHASENAV_MEMORY_INFORMATION_EXCHANGE_V0_1",
            "target_layer": "RELATIONAL",
            "automatic_latch": False,
        },
        "memory_anti_entropy": {
            "status": "AVAILABLE",
            "inventory_tool": "gremlin_hive_sync_inventory",
            "manifest_tool": "gremlin_hive_sync_manifest",
            "delta_tool": "gremlin_hive_sync_delta",
            "apply_tool": "gremlin_hive_sync_apply",
            "scope": "EXCHANGE_MEMORY_ONLY_APPEND_ONLY",
            "automatic_latch": False,
        },
        "memory_consolidation": {
            "status": "AVAILABLE_READ_ONLY",
            "route_tool": "gremlin_hive_consolidation_route",
            "source_layer": "EPISODIC",
            "derived_layer": "SEMANTIC",
            "direct_hive_ingest_allowed": False,
        },
    }


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_exchange_ingest(
    envelope: dict[str, Any],
    priority: float = 0.82,
    constitutional_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ingest a typed PhaseNav envelope into RELATIONAL Hive memory."""
    return ingest_exchange_envelope(
        runtime,
        envelope,
        priority=priority,
        consumer_id="GREMLIN-HIVE",
    )


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_exchange_bundle_ingest(
    bundle: dict[str, Any],
    priority: float = 0.82,
    constitutional_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify a portable lineage proof and ingest only its RELATIONAL target."""
    return ingest_exchange_bundle(
        runtime,
        bundle,
        priority=priority,
        consumer_id="GREMLIN-HIVE",
    )


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_sync_inventory(
    node_id: str = "GREMLIN-HIVE",
) -> dict[str, Any]:
    return build_hive_inventory(runtime, node_id=node_id)


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_sync_manifest(
    prefixes: list[str],
    node_id: str = "GREMLIN-HIVE",
) -> dict[str, Any]:
    return build_hive_manifest(runtime, node_id=node_id, prefixes=prefixes)


@mcp.tool()
@owl_runtime_boundary
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
@owl_runtime_boundary
def gremlin_hive_sync_apply(
    delta: dict[str, Any],
    node_id: str = "GREMLIN-HIVE",
    priority: float = 0.82,
    constitutional_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return apply_hive_delta(
        runtime,
        delta,
        receiver_node_id=node_id,
        priority=priority,
    )


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_consolidation_route(
    plan: dict[str, Any],
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate PhaseNav consolidation and return the admitted SEMANTIC->RELATIONAL route."""
    return build_consolidation_route(plan, receipt)


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_place(
    subject_id: str,
    payload: dict[str, Any],
    priority: float,
    semantic_key: str,
    relation_phase: float,
    provenance: list[str] | None = None,
    dependencies: list[str] | None = None,
    constitutional_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Place a new append-only information version on the 36-ring Hive surface."""
    record = runtime.place(
        subject_id=subject_id,
        payload=payload,
        priority=priority,
        semantic_key=semantic_key,
        relation_phase=relation_phase,
        provenance=provenance or (),
        dependencies=dependencies or (),
    )
    return _record(record)


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_gates(
    subject_id: str,
    evidence_ready: bool | None = None,
    dependencies_closed: bool | None = None,
    contradiction_audited: bool | None = None,
    provenance_complete: bool | None = None,
    phase_coherent: bool | None = None,
    constitutional_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a closure-gate update; unspecified gates retain their previous values."""
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
    record = runtime.update_gates(subject_id, **changes)
    return _record(record)


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_dispute(
    subject_id: str,
    contradiction_ref: str,
    constitutional_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a DISPUTED child while preserving its exact parent coordinate and lineage."""
    record = runtime.dispute(subject_id, contradiction_ref)
    return _record(record)


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_latch(
    subject_id: str,
    constitutional_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Latch only when all five closure gates pass and the head is not disputed/quarantined."""
    record = runtime.latch(subject_id)
    return _record(record)


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_head(subject_id: str) -> dict[str, Any]:
    """Return the current append-only head for one information subject."""
    return _record(runtime.head(subject_id))


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_table() -> dict[str, Any]:
    """Return the current flat concentric table, sorted inner-to-outer then angle and phase."""
    rows = [_record(record) for record in runtime.table()]
    return {
        "schema": HIVE_SCHEMA,
        "ordering": "INNER_TO_OUTER_THEN_SEMANTIC_ANGLE_THEN_RELATION_PHASE",
        "authority": "SHARED_COGNITION_ONLY",
        "records": rows,
    }


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_history(subject_id: str) -> dict[str, Any]:
    """Return the full append-only lineage for one subject."""
    return {
        "schema": HIVE_SCHEMA,
        "subject_id": subject_id,
        "records": [_record(record) for record in runtime.history(subject_id)],
    }


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_persisted(subject_id: str | None = None) -> dict[str, Any]:
    """Read durable WAL rows when a state path was configured."""
    if not runtime.persistent:
        return {
            "schema": HIVE_SCHEMA,
            "status": "NO_DURABLE_STORE_CONFIGURED",
            "records": [],
        }
    return {
        "schema": HIVE_SCHEMA,
        "status": "SQLITE_WAL_SINGLE_AUTHORITY",
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
        help="optional append-only SQLite WAL path; also read from GREMLIN_HIVE_STATE_PATH",
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
