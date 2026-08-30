from __future__ import annotations

import hashlib
import json
from typing import Any

from gremlin_mcp.pipeline import SPECIALISTS
from gremlin_mcp.router import route

SCHEMA = "GREMLIN_RESEARCH_PLAN_V0_2"
VERSION = "0.2.1"
SEMANTIC_PROFILE = "OCTOPUS_QUERY_EVIDENCE_V0_6"

_STAGE_ORDER = (
    ("SPIDER", "MAP_RELATIONS", "relation dependency graph mapping topology isomorphism connect"),
    ("MOLE", "DERIVE_CANDIDATE", "derive proof equation formula solve mechanism"),
    ("HOUND", "ADVERSARIAL_CHECK", "contradict contradiction falsify test regression error mismatch verify validate"),
    ("RAVEN", "MEMORY_CONTEXT", "memory history previous prior archive archived retrieve context"),
    ("ANT", "ENUMERATE_VARIANTS", "enumerate combination permutation sweep exhaustive variant alternatives"),
    ("MANTIS", "PRUNE_REDUNDANCY", "duplicate redundant obsolete overlap prune deduplicate cleanup"),
)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _stage(stage_id: str, species: str, task: str, query_commitment: str) -> dict[str, Any]:
    # Stage routing receives typed task semantics plus expected specialist. The
    # free-text query is routed separately and only decides which stages exist.
    payload = {
        "stage_id": stage_id,
        "task": task,
        "query_commitment": query_commitment,
        "expected_species": species,
    }
    decision = route(payload, max_species=1, min_score=2.0, relative_cutoff=0.45)
    selected = list(decision.get("route_mask") or [])
    return {
        "stage_id": stage_id,
        "target_species": species,
        "route_mask": selected,
        "route_commitment": decision["route_commitment"],
        "task": task,
        "routing_status": "MATCH" if selected == [species] else "MISMATCH",
    }


def _query_route(text: str) -> dict[str, Any]:
    # Low relative cutoff makes the absolute evidence floor authoritative. This
    # avoids a strong cue for one specialist suppressing a second independently
    # evidenced specialist while still requiring >=2.0 evidence per species.
    return route(
        {"query": text, "intent": "research_stage_discovery"},
        max_species=len(SPECIALISTS),
        min_score=2.0,
        relative_cutoff=0.05,
    )


def build_research_plan_v02(query: str) -> dict[str, Any]:
    text = str(query).strip()
    if not text:
        raise ValueError("query must be non-empty")

    query_commitment = _commit(b"GREMLIN-RESEARCH-QUERY/v0.2", {"query": text})
    query_decision = _query_route(text)
    detected = set(query_decision.get("route_mask") or [])

    # Evidence acquisition remains the baseline research stage. Every optional
    # stage is now activated from the same auditable OCTOPUS semantic evidence
    # used by direct routing, removing the old raw-substring planner path.
    specs: list[tuple[str, str, str]] = [
        (
            "ACQUIRE_EVIDENCE",
            "OWL",
            "evidence source citation literature review provenance methodology",
        )
    ]
    for species, stage_id, task in _STAGE_ORDER:
        if species in detected:
            specs.append((stage_id, species, task))

    stages = [_stage(stage_id, species, task, query_commitment) for stage_id, species, task in specs]
    species_union: list[str] = []
    for stage in stages:
        for species in stage["route_mask"]:
            if species not in species_union:
                species_union.append(species)

    query_scores = [
        {
            "species": row["species"],
            "score": row["score"],
            "evidence": row["evidence"],
        }
        for row in query_decision["scores"]
        if row["score"] > 0
    ]

    core = {
        "semantic_profile": SEMANTIC_PROFILE,
        "query_commitment": query_commitment,
        "query_route_commitment": query_decision["route_commitment"],
        "query_detected_species": list(query_decision["route_mask"]),
        "stages": [
            {
                "stage_id": row["stage_id"],
                "target_species": row["target_species"],
                "route_mask": row["route_mask"],
                "route_commitment": row["route_commitment"],
            }
            for row in stages
        ],
        "species_union": species_union,
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "semantic_profile": SEMANTIC_PROFILE,
        "query": text,
        "query_commitment": query_commitment,
        "query_router_status": query_decision["status"],
        "query_route_commitment": query_decision["route_commitment"],
        "query_detected_species": list(query_decision["route_mask"]),
        "query_router_scores": query_scores,
        "stages": stages,
        "stage_count": len(stages),
        "species_union": species_union,
        "all_stage_routes_match_targets": all(row["routing_status"] == "MATCH" for row in stages),
        "plan_commitment": _commit(b"GREMLIN-RESEARCH-PLAN/v0.2", core),
        "epistemic_status": "DETERMINISTIC_STAGED_RESEARCH_PLAN_CANDIDATE",
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
