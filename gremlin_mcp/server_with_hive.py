from __future__ import annotations

from dataclasses import asdict
import os
from typing import Any

from .hive_authority import HiveAuthorityRuntime
from .hive_ingest import ingest_research_execution
from .research_executor import execute_research
from .server import build_parser as build_base_parser
from .server import configure_state, mcp

hive_runtime = HiveAuthorityRuntime()


def configure_hive_state(state_path: str | None) -> HiveAuthorityRuntime:
    """Select the one Hive authority runtime used by the main GREMLIN MCP process."""
    global hive_runtime
    hive_runtime.close()
    hive_runtime = HiveAuthorityRuntime(state_path, orbit_count=36)
    return hive_runtime


@mcp.tool()
def gremlin_hive_status() -> dict[str, Any]:
    """Return the authoritative shared-cognition Hive surface status."""
    result = hive_runtime.status()
    result["integrated_research_ingest"] = {
        "status": "AVAILABLE",
        "tool": "gremlin_hive_research_execute",
        "automatic_latch": False,
        "phase_basis": "COMMITMENT_REFERENCE_PHASE_NOT_PHYSICAL",
    }
    return result


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
    return asdict(
        hive_runtime.place(
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
    """Append a fail-closed closure-gate update to the current subject head."""
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
    return asdict(hive_runtime.update_gates(subject_id, **changes))


@mcp.tool()
def gremlin_hive_dispute(subject_id: str, contradiction_ref: str) -> dict[str, Any]:
    """Append a DISPUTED child and preserve exact lineage/provenance."""
    return asdict(hive_runtime.dispute(subject_id, contradiction_ref))


@mcp.tool()
def gremlin_hive_latch(subject_id: str) -> dict[str, Any]:
    """Latch only after all closure gates pass and no dispute/quarantine blocks the head."""
    return asdict(hive_runtime.latch(subject_id))


@mcp.tool()
def gremlin_hive_head(subject_id: str) -> dict[str, Any]:
    """Return the current authoritative head for one information subject."""
    return asdict(hive_runtime.head(subject_id))


@mcp.tool()
def gremlin_hive_table() -> dict[str, Any]:
    """Return current heads sorted inner-to-outer, then semantic angle and relation phase."""
    return {
        "schema": hive_runtime.status()["hive_schema"],
        "ordering": "INNER_TO_OUTER_THEN_SEMANTIC_ANGLE_THEN_RELATION_PHASE",
        "authority": "SHARED_COGNITION_ONLY",
        "records": [asdict(record) for record in hive_runtime.table()],
    }


@mcp.tool()
def gremlin_hive_history(subject_id: str) -> dict[str, Any]:
    """Return the full append-only lineage for one Hive subject."""
    return {
        "subject_id": subject_id,
        "authority": "SHARED_COGNITION_ONLY",
        "records": [asdict(record) for record in hive_runtime.history(subject_id)],
    }


@mcp.tool()
def gremlin_hive_persisted(subject_id: str | None = None) -> dict[str, Any]:
    """Read the append-only durable history when persistence is configured."""
    return {
        "authority": "SHARED_COGNITION_ONLY",
        "persistence": hive_runtime.status()["persistence"],
        "records": list(hive_runtime.persisted(subject_id)),
    }


@mcp.tool()
def gremlin_hive_research_execute(
    query: str,
    providers: list[str] | None = None,
    limit_per_provider: int = 6,
    max_species: int = 4,
    max_sources: int = 12,
) -> dict[str, Any]:
    """Execute GREMLIN research and atomically project candidate outputs into Hive.

    This path never sets closure gates and never latches automatically. Commitment-derived
    phases are deterministic reference addresses only and carry no physical interpretation.
    """
    result = execute_research(
        query,
        providers=providers or ["crossref", "arxiv", "duckduckgo"],
        limit_per_provider=limit_per_provider,
        max_species=max_species,
        max_sources=max_sources,
    )
    ingest = ingest_research_execution(hive_runtime, result)
    return {
        "research": result,
        "hive_ingest": ingest,
        "authority": "SHARED_COGNITION_ONLY",
    }


def build_parser():
    parser = build_base_parser()
    parser.add_argument(
        "--hive-state-path",
        default=os.environ.get("GREMLIN_HIVE_STATE_PATH"),
        help=(
            "optional authoritative Hive SQLite/WAL path; also read from "
            "GREMLIN_HIVE_STATE_PATH"
        ),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    configure_state(args.state_path)
    configure_hive_state(args.hive_state_path)
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
