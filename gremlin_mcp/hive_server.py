from __future__ import annotations

import argparse
from dataclasses import asdict
import os
from typing import Any

from mcp.server import MCPServer

from gremlin_mcp import __version__
from gremlin_mcp.orbital_hive_memory import HIVE_SCHEMA, OrbitalHiveMemory, SQLiteHiveStore

hive = OrbitalHiveMemory(orbit_count=36)
store: SQLiteHiveStore | None = None

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


def _persist(record: Any) -> None:
    if store is not None:
        store.append(record)


def configure_state(state_path: str | None) -> None:
    """Reset process state and fail-closed hydrate an optional durable WAL lineage."""
    global hive, store
    if store is not None:
        store.close()
    hive = OrbitalHiveMemory(orbit_count=36)
    store = None
    if state_path is None or not str(state_path).strip():
        return
    candidate = SQLiteHiveStore(str(state_path))
    try:
        for row in candidate.rows():
            hive.import_record(row)
    except Exception:
        candidate.close()
        hive = OrbitalHiveMemory(orbit_count=36)
        raise
    store = candidate


@mcp.tool()
def gremlin_hive_status() -> dict[str, Any]:
    """Return Hive authority, schema and current flat-ring head count."""
    table = hive.flat_ring_table()
    return {
        "schema": HIVE_SCHEMA,
        "status": "AVAILABLE",
        "orbit_count": hive.orbit_count,
        "head_count": len(table),
        "persistence": "SQLITE_WAL_HYDRATED_APPEND_ONLY" if store is not None else "PROCESS_RESIDENT",
        "authority": "SHARED_COGNITION_ONLY",
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


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
    """Place a new append-only information version on the 36-ring Hive surface."""
    record = hive.place(
        subject_id=subject_id,
        payload=payload,
        priority=priority,
        semantic_key=semantic_key,
        relation_phase=relation_phase,
        provenance=provenance or (),
        dependencies=dependencies or (),
    )
    _persist(record)
    return _record(record)


@mcp.tool()
def gremlin_hive_gates(
    subject_id: str,
    evidence_ready: bool | None = None,
    dependencies_closed: bool | None = None,
    contradiction_audited: bool | None = None,
    provenance_complete: bool | None = None,
    phase_coherent: bool | None = None,
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
    record = hive.update_gates(subject_id, **changes)
    _persist(record)
    return _record(record)


@mcp.tool()
def gremlin_hive_dispute(subject_id: str, contradiction_ref: str) -> dict[str, Any]:
    """Append a DISPUTED child while preserving its exact parent coordinate and lineage."""
    record = hive.dispute(subject_id, contradiction_ref)
    _persist(record)
    return _record(record)


@mcp.tool()
def gremlin_hive_latch(subject_id: str) -> dict[str, Any]:
    """Latch only when all five closure gates pass and the head is not disputed/quarantined."""
    record = hive.latch(subject_id)
    _persist(record)
    return _record(record)


@mcp.tool()
def gremlin_hive_head(subject_id: str) -> dict[str, Any]:
    """Return the current append-only head for one information subject."""
    return _record(hive.head(subject_id))


@mcp.tool()
def gremlin_hive_table() -> dict[str, Any]:
    """Return the current flat concentric table, sorted inner-to-outer then angle and phase."""
    rows = [_record(record) for record in hive.flat_ring_table()]
    return {
        "schema": HIVE_SCHEMA,
        "ordering": "INNER_TO_OUTER_THEN_SEMANTIC_ANGLE_THEN_RELATION_PHASE",
        "authority": "SHARED_COGNITION_ONLY",
        "records": rows,
    }


@mcp.tool()
def gremlin_hive_history(subject_id: str) -> dict[str, Any]:
    """Return the full append-only lineage for one subject."""
    return {
        "schema": HIVE_SCHEMA,
        "subject_id": subject_id,
        "records": [_record(record) for record in hive.history(subject_id)],
    }


@mcp.tool()
def gremlin_hive_persisted(subject_id: str | None = None) -> dict[str, Any]:
    """Read durable WAL rows when a state path was configured."""
    if store is None:
        return {
            "schema": HIVE_SCHEMA,
            "status": "NO_DURABLE_STORE_CONFIGURED",
            "records": [],
        }
    return {
        "schema": HIVE_SCHEMA,
        "status": "SQLITE_WAL_HYDRATED_APPEND_ONLY",
        "records": list(store.rows(subject_id)),
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
