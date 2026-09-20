from __future__ import annotations

from dataclasses import asdict
import json
import os
from typing import Any

from .hive_authority import HiveAuthorityRuntime
from .hive_ingest import ingest_research_execution
from .memory_exchange import ingest_exchange_bundle, ingest_exchange_envelope
from .memory_consolidation import build_consolidation_route
from .memory_anti_entropy import (
    apply_hive_delta,
    build_hive_inventory,
    build_hive_manifest,
    divergent_hive_buckets,
    export_hive_delta,
    plan_hive_delta,
)
from .research_executor import execute_research
from .server import build_parser as build_base_parser
from .server import configure_state, mcp, standalone_phasenav_self_test

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
    result["principal_boundary"] = {
        "mode": "SYSTEM_OPERATOR_CONTROL_PLANE",
        "bestiary_species_authority": False,
        "bestiary_gateway_schema": "GREMLIN_BESTIARY_MEMORY_GATEWAY_V0_1",
        "bestiary_policy_schema": "BESTIARY_MEMORY_CAPABILITY_V0_1",
        "direct_hive_tools_are_species_capabilities": False,
        "identity_authentication_provided": False,
    }
    result["memory_information_exchange"] = {
        "status": "AVAILABLE",
        "tool": "gremlin_hive_exchange_ingest",
        "bundle_tool": "gremlin_hive_exchange_bundle_ingest",
        "protocol_schema": "PHASENAV_MEMORY_INFORMATION_EXCHANGE_V0_1",
        "bundle_schema": "PHASENAV_MEMORY_INFORMATION_EXCHANGE_BUNDLE_V0_1",
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
def gremlin_hive_exchange_ingest(
    envelope: dict[str, Any],
    priority: float = 0.82,
) -> dict[str, Any]:
    """Ingest one typed PhaseNav memory envelope into RELATIONAL Hive memory.

    The operation is idempotent, parent-first and shared-cognition only. It never
    sets closure gates or latches automatically.
    """
    return ingest_exchange_envelope(
        hive_runtime,
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
        hive_runtime,
        bundle,
        priority=priority,
        consumer_id="GREMLIN-HIVE",
    )


@mcp.tool()
def gremlin_hive_sync_inventory(
    node_id: str = "GREMLIN-HIVE",
) -> dict[str, Any]:
    """Return the compact exchange-memory anti-entropy inventory."""
    return build_hive_inventory(hive_runtime, node_id=node_id)


@mcp.tool()
def gremlin_hive_sync_manifest(
    prefixes: list[str],
    node_id: str = "GREMLIN-HIVE",
) -> dict[str, Any]:
    """Return metadata-only manifests for selected divergent buckets."""
    return build_hive_manifest(hive_runtime, node_id=node_id, prefixes=prefixes)


@mcp.tool()
def gremlin_hive_sync_delta(
    receiver_inventory: dict[str, Any],
    receiver_manifest: dict[str, Any],
    node_id: str = "GREMLIN-HIVE",
) -> dict[str, Any]:
    """Build one append-only delta from this Hive to a receiver inventory."""
    sender_inventory = build_hive_inventory(hive_runtime, node_id=node_id)
    prefixes = divergent_hive_buckets(sender_inventory, receiver_inventory)
    sender_manifest = build_hive_manifest(
        hive_runtime,
        node_id=node_id,
        prefixes=prefixes,
    )
    plan = plan_hive_delta(
        sender_inventory,
        receiver_inventory,
        sender_manifest,
        receiver_manifest,
    )
    delta = export_hive_delta(hive_runtime, plan)
    return {
        "sender_inventory": sender_inventory,
        "sender_manifest": sender_manifest,
        "plan": plan,
        "delta": delta,
    }


@mcp.tool()
def gremlin_hive_sync_apply(
    delta: dict[str, Any],
    node_id: str = "GREMLIN-HIVE",
    priority: float = 0.82,
) -> dict[str, Any]:
    """Apply one prevalidated append-only exchange-memory delta."""
    return apply_hive_delta(
        hive_runtime,
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
    if args.self_test_phasenav:
        print(json.dumps(standalone_phasenav_self_test(), sort_keys=True))
        return
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
