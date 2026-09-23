from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib, json, math
from typing import Any, Callable, Mapping

from .semantic_graph_transformer import SemanticGraphTransformer

SCHEMA = "GREMLIN_SEMANTIC_GRAPH_BESTIARY_HANDOFF_V0_1"
VERSION = "0.1.0"
PHASENAV_EXCHANGE_SCHEMA = "PHASENAV_MEMORY_INFORMATION_EXCHANGE_V0_1"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class MemoryRequest:
    layer: str
    operation: str
    artifact_type: str
    subject_id: str
    generation_id: str


ROLE_REQUESTS = {
    "SPIDER": (
        ("RELATIONAL", "GRAPH_APPEND", "GRAPH_SNAPSHOT"),
        ("RELATIONAL", "EDGE_APPEND", "RELATION_EDGE"),
        ("RELATIONAL", "NODE_LINK", "DEPENDENCY_LINK"),
    ),
    "ELEPHANT": (
        ("SEMANTIC", "CONSOLIDATE", "MEMORY_ORBIT"),
        ("SEMANTIC", "DERIVE", "CONSOLIDATION_RECEIPT"),
        ("RELATIONAL", "DERIVE", "REPLAY_PLAN"),
    ),
    "BEES": (
        ("RELATIONAL", "DERIVE", "COHERENCE_FINDING"),
        ("RELATIONAL", "DERIVE", "ANTI_ENTROPY_DELTA"),
        ("RELATIONAL", "DERIVE", "RECONCILE_PROPOSAL"),
    ),
}


def _requests(role: str, subject_id: str, generation_id: str) -> list[dict[str, str]]:
    return [
        asdict(MemoryRequest(layer, operation, artifact, subject_id, generation_id))
        for layer, operation, artifact in ROLE_REQUESTS[role]
    ]


def build_bestiary_handoff(
    compiled: Mapping[str, Any],
    *,
    subject_id: str,
    generation_id: str,
    task_id: str,
    authorize: Callable[[str, list[dict[str, str]]], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a fail-closed SGT -> SPIDER -> ELEPHANT -> BEES handoff plan.

    If authorize is provided it is called once per role with the exact request
    set. In GREMLIN this callback is authorize_memory_requests. No Hive mutation
    happens here.
    """
    graph = compiled.get("graph")
    if not isinstance(graph, Mapping):
        raise ValueError("compiled graph missing")
    nodes = graph.get("nodes")
    relations = graph.get("relations")
    if not isinstance(nodes, list) or not isinstance(relations, list):
        raise ValueError("compiled graph invalid")
    if not subject_id or not generation_id or not task_id:
        raise ValueError("subject_id, generation_id and task_id are required")

    role_order = ["SPIDER", "ELEPHANT", "BEES"]
    stages: list[dict[str, Any]] = []
    for role in role_order:
        requests = _requests(role, subject_id, generation_id)
        authorization = None
        if authorize is not None:
            authorization = dict(authorize(role, requests))
            if authorization.get("beast") != role:
                raise PermissionError(f"authorization beast mismatch for {role}")
            if authorization.get("task_id") != task_id:
                raise PermissionError(f"authorization task mismatch for {role}")
            if authorization.get("canon_allowed") is not False:
                raise PermissionError("authorization must remain canon_allowed=false")
        stages.append({"role": role, "requests": requests, "authorization": authorization})

    payload = {
        "schema": SCHEMA,
        "version": VERSION,
        "subject_id": subject_id,
        "generation_id": generation_id,
        "task_id": task_id,
        "graph_sha256": compiled.get("graph_sha256"),
        "graph_metrics": {
            "nodes": len(nodes),
            "relations": len(relations),
            "bytecode_bytes": int((compiled.get("metrics") or {}).get("bytecode_bytes") or 0),
        },
        "stage_order": role_order,
        "stages": stages,
        "execution_semantics": {
            "SPIDER": "append typed graph snapshot/edges/dependency links",
            "ELEPHANT": "derive bounded memory-orbit consolidation/replay candidate",
            "BEES": "derive coherence/anti-entropy/reconciliation findings",
            "automatic_hive_mutation": False,
            "requires_existing_capability_gateway": True,
        },
        "authority": "CANDIDATE_ONLY",
        "canon_allowed": False,
    }
    payload["handoff_sha256"] = _sha(payload)
    return payload


def compile_causal_handoff(
    documents: list[str],
    seeds: list[str],
    *,
    subject_id: str,
    generation_id: str,
    task_id: str,
    depth: int = 2,
    max_neighbors: int = 8,
) -> dict[str, Any]:
    compiler = SemanticGraphTransformer(max_neighbors=max_neighbors)
    compiled = compiler.compile(documents)
    cone = compiler.causal_cone(compiled, seeds, depth=depth)
    return {
        "compiled": compiled,
        "causal_cone": cone,
        "handoff": build_bestiary_handoff(compiled, subject_id=subject_id, generation_id=generation_id, task_id=task_id),
    }


def build_hive_exchange_candidate(
    compiled: Mapping[str, Any],
    *,
    subject_id: str,
    generation_id: str,
    sequence: int = 0,
    producer_id: str = "GREMLIN-SGT",
    provenance: list[str] | None = None,
    dependencies: list[str] | None = None,
    route_edge_potentials: list[float] | None = None,
    hop_limit: int = 8,
) -> dict[str, Any]:
    """Build a content-addressed RELATIONAL exchange envelope for existing Hive ingest."""
    graph = compiled.get("graph")
    if not isinstance(graph, Mapping):
        raise ValueError("compiled graph missing")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
        raise ValueError("sequence must be a non-negative integer")
    if not isinstance(hop_limit, int) or isinstance(hop_limit, bool) or hop_limit < 1:
        raise ValueError("hop_limit must be >=1")
    edges = [float(x) for x in (route_edge_potentials if route_edge_potentials is not None else [0.0])]
    if not all(math.isfinite(x) for x in edges):
        raise ValueError("route_edge_potentials must be finite")
    theta = math.fsum(edges)
    payload = {
        "kind": "GREMLIN_SEMANTIC_RELATION_GRAPH",
        "graph_schema": compiled.get("schema"),
        "graph_sha256": compiled.get("graph_sha256"),
        "graph": dict(graph),
        "metrics": dict(compiled.get("metrics") or {}),
        "relation_bytecode_hex": compiled.get("bytecode_hex"),
        "authority": "CANDIDATE_ONLY",
        "canon_allowed": False,
    }
    payload_sha = _sha(payload)
    core = {
        "schema": PHASENAV_EXCHANGE_SCHEMA,
        "version": "0.1.0",
        "subject_id": subject_id,
        "producer_id": producer_id,
        "generation_id": generation_id,
        "sequence": sequence,
        "source_layer": "SEMANTIC",
        "target_layer": "RELATIONAL",
        "payload_sha256": payload_sha,
        "parent_envelope_ids": [],
        "provenance": sorted(set(provenance or [f"sgt:{compiled.get('graph_sha256')}"])),
        "dependencies": sorted(set(dependencies or [])),
        "route_edge_potentials": edges,
        "hop_count": 0,
        "hop_limit": hop_limit,
        "epistemic": "CHYBA",
        "authority": "SHARED_COGNITION_ONLY",
        "canon_allowed": False,
    }
    envelope_id = "px:" + _sha(core)
    return {
        **core,
        "envelope_id": envelope_id,
        "payload": payload,
        "transport": {
            "real": math.cos(theta),
            "imag": math.sin(theta),
            "phase": math.atan2(math.sin(theta), math.cos(theta)),
            "modulus": 1.0,
        },
        "claims": {
            "content_addressed_payload": True,
            "causal_lineage": True,
            "computational_u1_route_phase": True,
            "producer_identity_authenticated": False,
            "physical_nonlocal_signalling": False,
            "physical_channel_identified": False,
            "canon_promoted": False,
        },
    }


__all__ = [
    "SCHEMA", "VERSION", "PHASENAV_EXCHANGE_SCHEMA", "ROLE_REQUESTS", "MemoryRequest",
    "build_bestiary_handoff", "compile_causal_handoff", "build_hive_exchange_candidate",
]
