from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping

SCHEMA = "GREMLIN_BIO_OS_CONTINUOUS_RELATIONAL_MEDIUM_V0_1"
VERSION = "0.1.0"


REQUIRED_SEMANTIC_INVARIANTS = {
    "persistent_state_required": True,
    "time_is_state_coordinate": True,
    "global_semantic_tick_required": False,
    "global_poll_loop_required": False,
    "full_graph_rescan_required": False,
    "stable_relation_recompute_required": False,
    "local_perturbation_propagation_required": True,
    "bounded_active_support_required": True,
    "orbital_activation_semantics": True,
}


FORBIDDEN_POSITIVE_CLAIMS = (
    "physical_material_fluid_claim",
    "einstein_equals_navier_stokes_claim",
    "bio_os_validates_tir_physics",
    "measured_energy_advantage_without_telemetry",
    "perfect_continuity_across_host_loss",
)


@dataclass(frozen=True)
class BioOSLocalityMetrics:
    total_nodes: int
    active_nodes: int
    eligible_stable_relations: int
    recomputed_stable_relations: int
    reused_relations: int
    recomputed_relations: int

    def __post_init__(self) -> None:
        for name in (
            "total_nodes",
            "active_nodes",
            "eligible_stable_relations",
            "recomputed_stable_relations",
            "reused_relations",
            "recomputed_relations",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.total_nodes < 1:
            raise ValueError("total_nodes must be >= 1")
        if self.active_nodes > self.total_nodes:
            raise ValueError("active_nodes cannot exceed total_nodes")
        if self.recomputed_stable_relations > self.eligible_stable_relations:
            raise ValueError(
                "recomputed_stable_relations cannot exceed eligible_stable_relations"
            )

    def receipt(self) -> dict[str, float | int | None]:
        reuse_den = self.reused_relations + self.recomputed_relations
        active_fraction = self.active_nodes / self.total_nodes
        reuse_ratio = (
            None if reuse_den == 0 else self.reused_relations / reuse_den
        )
        recompute_avoidance = (
            None
            if self.eligible_stable_relations == 0
            else 1.0
            - self.recomputed_stable_relations / self.eligible_stable_relations
        )
        return {
            "total_nodes": self.total_nodes,
            "active_nodes": self.active_nodes,
            "active_fraction": active_fraction,
            "reuse_ratio": reuse_ratio,
            "recompute_avoidance": recompute_avoidance,
        }


def validate_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    semantics = contract.get("semantics")
    forbidden = contract.get("forbidden_claims")
    authority = contract.get("authority")
    if not isinstance(semantics, Mapping):
        raise ValueError("contract semantics mapping required")
    if not isinstance(forbidden, Mapping):
        raise ValueError("contract forbidden_claims mapping required")
    if not isinstance(authority, Mapping):
        raise ValueError("contract authority mapping required")

    for key, expected in REQUIRED_SEMANTIC_INVARIANTS.items():
        if semantics.get(key) is not expected:
            raise ValueError(
                f"Bio-OS invariant violated: {key} must be {expected!r}"
            )

    for key in FORBIDDEN_POSITIVE_CLAIMS:
        if forbidden.get(key) is not False:
            raise ValueError(
                f"Bio-OS firewall violated: {key} must remain false"
            )

    if authority.get("canon_allowed") is not False:
        raise ValueError("candidate contract must remain canon_allowed=false")
    if authority.get("external_effects_authorized") is not False:
        raise ValueError(
            "candidate contract must not authorize external effects"
        )

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "PASS_CONTRACT",
        "global_semantic_tick_required": False,
        "full_graph_rescan_required": False,
        "physical_fluid_claim": False,
        "canon_allowed": False,
    }


def verified_delta_per_joule(
    accepted_verified_delta_units: float,
    measured_energy_joules: float,
) -> float:
    delta = float(accepted_verified_delta_units)
    joules = float(measured_energy_joules)
    if not math.isfinite(delta) or delta < 0.0:
        raise ValueError(
            "accepted_verified_delta_units must be finite and non-negative"
        )
    if not math.isfinite(joules) or joules <= 0.0:
        raise ValueError("measured_energy_joules must be finite and > 0")
    return delta / joules


__all__ = [
    "SCHEMA",
    "VERSION",
    "REQUIRED_SEMANTIC_INVARIANTS",
    "FORBIDDEN_POSITIVE_CLAIMS",
    "BioOSLocalityMetrics",
    "validate_contract",
    "verified_delta_per_joule",
]
