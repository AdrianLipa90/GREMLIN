from __future__ import annotations

from dataclasses import asdict
import json
import os
from typing import Any

from .hive_authority import HiveAuthorityRuntime
from .hive_ingest import ingest_research_execution
from .holographic_orbital_memory import (
    AUTHORITY as HOLOGRAPHIC_MEMORY_AUTHORITY,
    HolographicOrbitalIndex,
    apply_phase_carrier,
    holographic_address,
    project_hologram,
)
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
from .semantic_graph_transformer import SemanticGraphTransformer
from .semantic_graph_bestiary import build_bestiary_handoff, build_hive_exchange_candidate
from .memory_capabilities import authorize_memory_requests
from .owl_runtime_audit import owl_runtime_boundary
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
@owl_runtime_boundary
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
    result["holographic_orbital_memory"] = {
        "status": "AVAILABLE_READ_ONLY_DERIVED",
        "schema": "GREMLIN_HOLOGRAPHIC_ORBITAL_MEMORY_V0_1",
        "project_tool": "gremlin_hive_holographic_project",
        "remap_tool": "gremlin_hive_holographic_remap",
        "retrieve_tool": "gremlin_hive_holographic_retrieve",
        "phase_transport_tool": "gremlin_hive_holographic_phase_transport",
        "ledger_mutation": False,
        "rebuildable_from_ledger": True,
    }
    result["integrated_research_ingest"] = {
        "status": "AVAILABLE",
        "tool": "gremlin_hive_research_execute",
        "automatic_latch": False,
        "phase_basis": "COMMITMENT_REFERENCE_PHASE_NOT_PHYSICAL",
    }
    return result


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_holographic_project(
    cells: list[list[float]],
    weights: list[float] | None = None,
    relation_phases: list[float] | None = None,
) -> dict[str, Any]:
    """Build a non-authoritative 36D holographic projection from explicit memory cells."""
    return asdict(
        project_hologram(
            cells,
            weights=weights,
            relation_phases=relation_phases,
        )
    )


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_holographic_remap(
    records: dict[str, list[float]],
    orbit_count: int = 9,
    hex_scale: float = 16.0,
) -> dict[str, Any]:
    """Rebuild the derived orbital/BEES-hex index from explicit 36D attachments."""
    index = HolographicOrbitalIndex.remap(
        records,
        orbit_count=orbit_count,
        hex_scale=hex_scale,
    )
    return {
        "schema": "GREMLIN_HOLOGRAPHIC_ORBITAL_MEMORY_REMAP_V0_1",
        "status": "DERIVED_REBUILD_ONLY",
        "record_count": index.size,
        "mapping_commitment": index.mapping_commitment(),
        "addresses": {
            record_id: asdict(
                holographic_address(
                    cell,
                    orbit_count=orbit_count,
                    hex_scale=hex_scale,
                )
            )
            for record_id, cell in sorted(records.items())
        },
        "authority": dict(HOLOGRAPHIC_MEMORY_AUTHORITY),
    }


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_holographic_retrieve(
    query: list[float],
    records: dict[str, list[float]],
    orbit_count: int = 9,
    hex_scale: float = 16.0,
    min_candidates: int = 12,
    max_hex_ring: int = 3,
    orbit_radius: int = 1,
) -> dict[str, Any]:
    """Prefilter by orbital/hex address and rerank by exact memory-moire overlap."""
    index = HolographicOrbitalIndex.remap(
        records,
        orbit_count=orbit_count,
        hex_scale=hex_scale,
    )
    return asdict(
        index.retrieve(
            query,
            min_candidates=min_candidates,
            max_hex_ring=max_hex_ring,
            orbit_radius=orbit_radius,
        )
    )


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_holographic_phase_transport(
    cell: list[float],
    carrier_36d: list[float],
    gain: float = 1.0,
) -> dict[str, Any]:
    """Apply explicit reversible 36D phase transport to a derived working-memory cell."""
    transported = apply_phase_carrier(cell, carrier_36d, gain=gain)
    return {
        "schema": "GREMLIN_HOLOGRAPHIC_ORBITAL_MEMORY_PHASE_TRANSPORT_V0_1",
        "phase_36d": list(transported),
        "gain": float(gain),
        "authority": dict(HOLOGRAPHIC_MEMORY_AUTHORITY),
        "physical_qhtri_claim": False,
    }


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
@owl_runtime_boundary
def gremlin_hive_dispute(
    subject_id: str,
    contradiction_ref: str,
    constitutional_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a DISPUTED child and preserve exact lineage/provenance."""
    return asdict(hive_runtime.dispute(subject_id, contradiction_ref))


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_latch(
    subject_id: str,
    constitutional_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Latch only after all closure gates pass and no dispute/quarantine blocks the head."""
    return asdict(hive_runtime.latch(subject_id))


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_head(subject_id: str) -> dict[str, Any]:
    """Return the current authoritative head for one information subject."""
    return asdict(hive_runtime.head(subject_id))


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_table() -> dict[str, Any]:
    """Return current heads sorted inner-to-outer, then semantic angle and relation phase."""
    return {
        "schema": hive_runtime.status()["hive_schema"],
        "ordering": "INNER_TO_OUTER_THEN_SEMANTIC_ANGLE_THEN_RELATION_PHASE",
        "authority": "SHARED_COGNITION_ONLY",
        "records": [asdict(record) for record in hive_runtime.table()],
    }


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_history(subject_id: str) -> dict[str, Any]:
    """Return the full append-only lineage for one Hive subject."""
    return {
        "subject_id": subject_id,
        "authority": "SHARED_COGNITION_ONLY",
        "records": [asdict(record) for record in hive_runtime.history(subject_id)],
    }


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_persisted(subject_id: str | None = None) -> dict[str, Any]:
    """Read the append-only durable history when persistence is configured."""
    return {
        "authority": "SHARED_COGNITION_ONLY",
        "persistence": hive_runtime.status()["persistence"],
        "records": list(hive_runtime.persisted(subject_id)),
    }


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_exchange_ingest(
    envelope: dict[str, Any],
    priority: float = 0.82,
    constitutional_packet: dict[str, Any] | None = None,
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
@owl_runtime_boundary
def gremlin_hive_exchange_bundle_ingest(
    bundle: dict[str, Any],
    priority: float = 0.82,
    constitutional_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify a portable lineage proof and ingest only its RELATIONAL target."""
    return ingest_exchange_bundle(
        hive_runtime,
        bundle,
        priority=priority,
        consumer_id="GREMLIN-HIVE",
    )


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_sync_inventory(
    node_id: str = "GREMLIN-HIVE",
) -> dict[str, Any]:
    """Return the compact exchange-memory anti-entropy inventory."""
    return build_hive_inventory(hive_runtime, node_id=node_id)


@mcp.tool()
@owl_runtime_boundary
def gremlin_hive_sync_manifest(
    prefixes: list[str],
    node_id: str = "GREMLIN-HIVE",
) -> dict[str, Any]:
    """Return metadata-only manifests for selected divergent buckets."""
    return build_hive_manifest(hive_runtime, node_id=node_id, prefixes=prefixes)


@mcp.tool()
@owl_runtime_boundary
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
@owl_runtime_boundary
def gremlin_hive_sync_apply(
    delta: dict[str, Any],
    node_id: str = "GREMLIN-HIVE",
    priority: float = 0.82,
    constitutional_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply one prevalidated append-only exchange-memory delta."""
    return apply_hive_delta(
        hive_runtime,
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
def gremlin_hive_research_execute(
    query: str,
    providers: list[str] | None = None,
    limit_per_provider: int = 6,
    max_species: int = 4,
    max_sources: int = 12,
    constitutional_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute GREMLIN research and atomically project candidate outputs into Hive.

    This path never sets closure gates and never latches automatically. Commitment-derived
    phases are deterministic reference addresses only and carry no physical interpretation.
    """
    effective_providers = providers or ["crossref", "arxiv", "duckduckgo"]
    result = execute_research(
        query,
        providers=effective_providers,
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



@mcp.tool()
@owl_runtime_boundary
def gremlin_semantic_graph_compile(
    documents: list[str],
    max_neighbors: int = 8,
    min_confidence: float = 0.52,
) -> dict[str, Any]:
    """Compile unstructured text into compact typed relation tokens without mutating Hive."""
    return SemanticGraphTransformer(
        max_neighbors=max_neighbors,
        min_confidence=min_confidence,
    ).compile(documents)


@mcp.tool()
@owl_runtime_boundary
def gremlin_semantic_graph_causal_cone(
    compiled: dict[str, Any],
    seeds: list[str],
    depth: int = 2,
) -> dict[str, Any]:
    """Return the bounded active semantic subgraph around the query seeds."""
    return SemanticGraphTransformer.causal_cone(compiled, seeds, depth=depth)


@mcp.tool()
@owl_runtime_boundary
def gremlin_semantic_graph_bestiary_handoff(
    compiled: dict[str, Any],
    subject_id: str,
    generation_id: str,
    task_id: str,
) -> dict[str, Any]:
    """Build exact capability-scoped SPIDER -> ELEPHANT -> BEES handoff receipts."""
    return build_bestiary_handoff(
        compiled,
        subject_id=subject_id,
        generation_id=generation_id,
        task_id=task_id,
        authorize=lambda role, requests: authorize_memory_requests(
            role,
            requests,
            task_id=task_id,
        ),
    )


@mcp.tool()
@owl_runtime_boundary
def gremlin_semantic_graph_hive_exchange_candidate(
    compiled: dict[str, Any],
    subject_id: str,
    generation_id: str,
) -> dict[str, Any]:
    """Build a read-only content-addressed candidate packet for existing Hive ingest."""
    return build_hive_exchange_candidate(
        compiled,
        subject_id=subject_id,
        generation_id=generation_id,
    )


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
