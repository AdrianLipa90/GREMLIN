from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from tools.gremlin_bestiary_orbital_scheduler_v02 import PROFILES, service_omega, service_period
from tools.gremlin_bestiary_vector_species_v03 import (
    build_species_plan,
    dispatch_compression,
    validate_plan,
)

SCHEMA = "GREMLIN_MCP_V0_2"
VERSION = "0.2.0"

BESTIARY_ROLES: dict[str, dict[str, str]] = {
    "HUMMINGBIRD": {
        "stage": "capture",
        "role": "fast append-only capture",
    },
    "OCTOPUS": {
        "stage": "routing",
        "role": "route mask and bounded semantic fanout",
    },
    "SPIDER": {
        "stage": "specialist",
        "role": "relation, dependency and isomorphism scan",
    },
    "RAVEN": {
        "stage": "specialist",
        "role": "memory and similarity scan",
    },
    "HOUND": {
        "stage": "specialist",
        "role": "contradiction, anomaly and test-target scan",
    },
    "MOLE": {
        "stage": "specialist",
        "role": "deep local derivation",
    },
    "OWL": {
        "stage": "specialist",
        "role": "epistemic audit",
    },
    "ANT": {
        "stage": "specialist",
        "role": "bounded combinatorial scan",
    },
    "MANTIS": {
        "stage": "specialist",
        "role": "duplicate and dead-branch pruning",
    },
    "BELZEBUB": {
        "stage": "synthesis",
        "role": "defensive candidate synthesis",
    },
    "GREMLIN": {
        "stage": "aggregate",
        "role": "aggregate verified heads and emit research candidates",
    },
}

TOPOLOGY = (
    "RAW",
    "HUMMINGBIRD",
    "OCTOPUS",
    "SPECIALISTS",
    "BELZEBUB",
    "GREMLIN",
)

MCP_TOOLS = [
    "gremlin_status",
    "gremlin_bestiary",
    "gremlin_species",
    "gremlin_plan",
    "gremlin_prototype",
    "gremlin_worker_register",
    "gremlin_worker_heartbeat",
    "gremlin_worker_list",
    "gremlin_worker_enqueue",
    "gremlin_worker_claim",
    "gremlin_worker_submit",
    "gremlin_worker_result",
    "gremlin_worker_queue",
]


def authority_state() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def status() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "mode": "STANDALONE_REFERENCE_MCP",
        "standalone": True,
        "noema_required": False,
        "phasenav_native_authority_required": False,
        "transport_capabilities": ["stdio", "streamable-http"],
        "worker_abi": {
            "version": "0.2.0",
            "model": "PULL_LEASE_SUBMIT",
            "callback_networking": False,
            "same_species_batches": True,
            "orbit_lane_bounded": True,
            "state_persistence": "PROCESS_MEMORY_V0_2",
        },
        "tools": list(MCP_TOOLS),
        "topology": list(TOPOLOGY),
        "authority": authority_state(),
    }


def bestiary_manifest() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for name, meta in BESTIARY_ROLES.items():
        entry: dict[str, Any] = {
            "name": name,
            **meta,
            "scheduler_profile": None,
        }
        if name in PROFILES:
            profile = PROFILES[name]
            entry["scheduler_profile"] = {
                "mass": profile.mass,
                "radius": profile.radius,
                "omega": service_omega(profile),
                "period": service_period(profile),
            }
        entries.append(entry)
    return {
        "schema": SCHEMA,
        "topology": list(TOPOLOGY),
        "species": entries,
        "authority": authority_state(),
    }


def species_profile(species: str) -> dict[str, Any]:
    name = str(species).strip().upper()
    if name not in BESTIARY_ROLES:
        raise ValueError(f"unknown GREMLIN species: {species!r}")
    meta = BESTIARY_ROLES[name]
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "name": name,
        **meta,
        "scheduler_profile": None,
        "authority": authority_state(),
    }
    if name in PROFILES:
        profile = PROFILES[name]
        result["scheduler_profile"] = {
            "mass": profile.mass,
            "radius": profile.radius,
            "omega": service_omega(profile),
            "period": service_period(profile),
        }
    return result


def plan_bestiary(route_counts: Mapping[str, int], *, vector_width: int = 8) -> dict[str, Any]:
    if not isinstance(route_counts, Mapping) or not route_counts:
        raise ValueError("route_counts must be a non-empty mapping")
    normalized: dict[str, int] = {}
    for raw_name, raw_count in route_counts.items():
        name = str(raw_name).strip().upper()
        if name not in PROFILES:
            raise ValueError(f"species has no scheduler profile: {raw_name!r}")
        count = int(raw_count)
        if count < 0:
            raise ValueError("route counts must be non-negative")
        normalized[name] = normalized.get(name, 0) + count

    width = int(vector_width)
    if width <= 0:
        raise ValueError("vector_width must be positive")

    plan = build_species_plan(normalized, vector_width=width)
    validate_plan(plan)
    return {
        "schema": SCHEMA,
        "route_counts": normalized,
        "vector_width": width,
        "dispatch_compression": dispatch_compression(plan),
        "plan": [asdict(item) for item in plan],
        "authority": authority_state(),
    }


def run_prototype(request: Mapping[str, Any]) -> dict[str, Any]:
    """Run the existing fail-closed GREMLIN reference prototype pipeline.

    Import is intentionally lazy so status/planning stay lightweight and do not
    require the PhaseNav reference pipeline until this MCP tool is invoked.
    """
    if not isinstance(request, Mapping):
        raise ValueError("request must be a mapping")
    from tools.gremlin_client_protocol_v01 import run_client_request

    return run_client_request(request)
