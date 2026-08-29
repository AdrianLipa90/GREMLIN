from __future__ import annotations

import hashlib
import json
from typing import Any

from gremlin_mcp.router import route

SCHEMA = "GREMLIN_RESEARCH_PLAN_V0_2"
VERSION = "0.2.0"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _contains(text: str, *needles: str) -> bool:
    lowered = text.casefold()
    return any(needle.casefold() in lowered for needle in needles)


def _stage(stage_id: str, species: str, task: str, query_commitment: str) -> dict[str, Any]:
    # Stage routing intentionally receives the typed task and query commitment,
    # not the full free-text query. This prevents unrelated query vocabulary from
    # drowning the specialist signal while preserving a cryptographic link to it.
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


def build_research_plan_v02(query: str) -> dict[str, Any]:
    text = str(query).strip()
    if not text:
        raise ValueError("query must be non-empty")

    query_commitment = _commit(b"GREMLIN-RESEARCH-QUERY/v0.2", {"query": text})
    specs: list[tuple[str, str, str]] = [
        (
            "ACQUIRE_EVIDENCE",
            "OWL",
            "evidence source citation literature review provenance methodology",
        )
    ]

    if _contains(text, "relation", "dependenc", "graph", "connect", "bridge", "isomorph", "mapping", "topology"):
        specs.append(
            (
                "MAP_RELATIONS",
                "SPIDER",
                "relation dependency graph mapping topology isomorphism connect",
            )
        )
    if _contains(text, "derive", "deriv", "proof", "equation", "formula", "solve", "mechanism"):
        specs.append(
            (
                "DERIVE_CANDIDATE",
                "MOLE",
                "derive proof equation formula solve mechanism",
            )
        )
    if _contains(text, "audit", "contradict", "falsif", "validate", "verify", "error", "mismatch", "regression", "test"):
        specs.append(
            (
                "ADVERSARIAL_CHECK",
                "HOUND",
                "contradict contradiction falsify test regression error mismatch verify validate",
            )
        )
    if _contains(text, "memory", "history", "previous", "prior", "archive", "archived"):
        specs.append(
            (
                "MEMORY_CONTEXT",
                "RAVEN",
                "memory history previous prior archive archived",
            )
        )
    if _contains(text, "enumerate", "combination", "permutation", "sweep", "exhaustive", "variant"):
        specs.append(
            (
                "ENUMERATE_VARIANTS",
                "ANT",
                "enumerate combination permutation sweep exhaustive variant",
            )
        )
    if _contains(text, "duplicate", "redundant", "obsolete", "overlap", "prune", "merge"):
        specs.append(
            (
                "PRUNE_REDUNDANCY",
                "MANTIS",
                "duplicate redundant obsolete overlap prune merge",
            )
        )

    stages = [_stage(stage_id, species, task, query_commitment) for stage_id, species, task in specs]
    species_union: list[str] = []
    for stage in stages:
        for species in stage["route_mask"]:
            if species not in species_union:
                species_union.append(species)

    core = {
        "query_commitment": query_commitment,
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
        "query": text,
        "query_commitment": query_commitment,
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
