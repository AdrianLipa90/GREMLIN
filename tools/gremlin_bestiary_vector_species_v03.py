from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

from tools.gremlin_bestiary_orbital_scheduler_v02 import PROFILES, service_omega


@dataclass(frozen=True)
class SpeciesLanePlan:
    species: str
    route_count: int
    omega: float
    lane_width: int
    batch_count: int


def lane_width(species: str, *, vector_width: int = 8, lo: int = 1, hi: int = 128) -> int:
    """Map orbital cadence to a bounded same-operator lane width.

    Fast inner-orbit species keep small low-latency batches. Slower/heavier outer
    species accumulate larger batches so expensive synthesis/deep work amortizes
    dispatch and serialization overhead.
    """
    if species not in PROFILES:
        raise KeyError("unknown Bestiary species")
    vw = int(vector_width)
    if vw <= 0 or lo <= 0 or hi < lo:
        raise ValueError("invalid vector lane bounds")

    hummingbird = PROFILES["HUMMINGBIRD"]
    profile = PROFILES[species]
    omega_ratio = service_omega(hummingbird) / service_omega(profile)
    width = int(round(vw * math.sqrt(max(1.0, omega_ratio))))
    return max(int(lo), min(int(hi), width))


def build_species_plan(
    route_counts: Mapping[str, int],
    *,
    vector_width: int = 8,
) -> tuple[SpeciesLanePlan, ...]:
    plans = []
    for species, raw_count in route_counts.items():
        if species not in PROFILES:
            raise KeyError("unknown Bestiary species")
        count = int(raw_count)
        if count < 0:
            raise ValueError("route counts must be non-negative")
        width = lane_width(species, vector_width=vector_width)
        batches = 0 if count == 0 else math.ceil(count / width)
        plans.append(
            SpeciesLanePlan(
                species=species,
                route_count=count,
                omega=service_omega(PROFILES[species]),
                lane_width=width,
                batch_count=batches,
            )
        )
    return tuple(sorted(plans, key=lambda p: (-p.omega, p.species)))


def dispatch_compression(plan: tuple[SpeciesLanePlan, ...]) -> float:
    items = sum(p.route_count for p in plan)
    batches = sum(p.batch_count for p in plan)
    if items == 0:
        return 1.0
    return items / max(1, batches)


def validate_plan(plan: tuple[SpeciesLanePlan, ...]) -> None:
    for p in plan:
        if p.species not in PROFILES:
            raise ValueError("unknown species in plan")
        if p.route_count < 0 or p.lane_width <= 0 or p.batch_count < 0:
            raise ValueError("invalid species lane plan")
        expected = 0 if p.route_count == 0 else math.ceil(p.route_count / p.lane_width)
        if p.batch_count != expected:
            raise ValueError("batch lineage mismatch")
