from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
from typing import Any

from gremlin_mcp.adaptive_runtime import (
    OperatorTier,
    ResourceBudget,
    RoutePlan,
    minimal_capability_cover,
)
from gremlin_mcp.orchorbital_runtime import (
    OrbitSpec,
    OrchorbitalPlan,
    compile_orchorbital_plan,
    plan_receipt,
)

SCHEMA = "GREMLIN_ADAPTIVE_ORCHORBITAL_BRIDGE_V0_1"
VERSION = "0.1.0"
ROOT_ORBIT_ID = "ORCH:ROOT"


def _strict_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    out = value.strip()
    if not out:
        raise ValueError(f"{field} must be non-empty")
    return out


def _strict_obligations(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, Mapping)) or not isinstance(values, Iterable):
        raise ValueError("obligations must be an iterable of strings")
    out: list[str] = []
    for index, value in enumerate(values):
        item = _strict_text(value, f"obligations[{index}]")
        if item in out:
            raise ValueError(f"duplicate obligation: {item}")
        out.append(item)
    if not out:
        raise ValueError("obligations must be non-empty")
    return tuple(out)


def _normalize_parent_map(
    obligations: Sequence[str],
    parents: Mapping[str, str | None] | None,
) -> dict[str, str | None]:
    allowed = set(obligations)
    if parents is None:
        return {obligation: None for obligation in obligations}
    if not isinstance(parents, Mapping):
        raise ValueError("parent_by_obligation must be a mapping")
    unknown_keys = set(parents) - allowed
    if unknown_keys:
        raise ValueError(f"unknown parent mapping keys: {sorted(unknown_keys)!r}")

    out: dict[str, str | None] = {}
    for obligation in obligations:
        raw_parent = parents.get(obligation)
        if raw_parent is None:
            out[obligation] = None
            continue
        parent = _strict_text(raw_parent, f"parent_by_obligation[{obligation}]")
        if parent not in allowed:
            raise ValueError(f"unknown obligation parent: {parent}")
        if parent == obligation:
            raise ValueError("obligation cannot parent itself")
        out[obligation] = parent
    return out


def _normalize_dependency_map(
    obligations: Sequence[str],
    dependencies: Mapping[str, Iterable[str]] | None,
) -> dict[str, tuple[str, ...]]:
    allowed = set(obligations)
    if dependencies is None:
        return {obligation: () for obligation in obligations}
    if not isinstance(dependencies, Mapping):
        raise ValueError("depends_on_by_obligation must be a mapping")
    unknown_keys = set(dependencies) - allowed
    if unknown_keys:
        raise ValueError(f"unknown dependency mapping keys: {sorted(unknown_keys)!r}")

    out: dict[str, tuple[str, ...]] = {}
    for obligation in obligations:
        raw = dependencies.get(obligation, ())
        if isinstance(raw, (str, bytes, Mapping)) or not isinstance(raw, Iterable):
            raise ValueError(f"depends_on_by_obligation[{obligation}] must be an iterable")
        row: list[str] = []
        for value in raw:
            dependency = _strict_text(value, f"depends_on_by_obligation[{obligation}]")
            if dependency not in allowed:
                raise ValueError(f"unknown obligation dependency: {dependency}")
            if dependency == obligation:
                raise ValueError("obligation cannot causally depend on itself")
            if dependency not in row:
                row.append(dependency)
        out[obligation] = tuple(row)
    return out


def _normalize_phase_map(
    obligations: Sequence[str],
    phases: Mapping[str, Sequence[float]] | None,
) -> dict[str, tuple[float, ...]]:
    if phases is None:
        return {}
    if not isinstance(phases, Mapping):
        raise ValueError("phase36_by_obligation must be a mapping")
    allowed = set(obligations)
    unknown = set(phases) - allowed
    if unknown:
        raise ValueError(f"unknown phase mapping keys: {sorted(unknown)!r}")
    return {key: tuple(value) for key, value in phases.items()}


def _orbit_id(index: int, obligation: str) -> str:
    digest = hashlib.blake2b(
        b"GREMLIN-ORCHORBITAL-OBLIGATION/v0.1\x00" + obligation.encode("utf-8"),
        digest_size=6,
    ).hexdigest()
    return f"ORCH:O{index:04d}:{digest}"


def _operator_for_obligation(plan: RoutePlan, obligation: str) -> OperatorTier:
    candidates = [operator for operator in plan.operators if obligation in operator.capabilities]
    if not candidates:
        raise RuntimeError(f"selected route does not cover obligation: {obligation}")
    return min(
        candidates,
        key=lambda operator: (
            operator.tier,
            len(operator.capabilities),
            operator.species,
            operator.operator_id,
        ),
    )


@dataclass(frozen=True)
class AdaptiveOrchorbitalPlan:
    route_plan: RoutePlan
    execution_plan: OrchorbitalPlan
    obligation_to_orbit: tuple[tuple[str, str], ...]
    obligation_to_operator: tuple[tuple[str, str], ...]

    def receipt(self) -> dict[str, object]:
        topology = plan_receipt(self.execution_plan)
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "obligations": sorted(self.route_plan.obligations),
            "minimal_cover_route": list(self.route_plan.route_ids),
            "minimax_pressure": self.route_plan.minimax_pressure,
            "obligation_to_orbit": dict(self.obligation_to_orbit),
            "obligation_to_operator": dict(self.obligation_to_operator),
            "orchorbital": topology,
            "authority": "COGNITIVE_ROUTING_ONLY",
            "epistemic": "CHYBA",
            "canon_allowed": False,
            "execution_admitted": False,
            "memory_mutation_allowed": False,
            "speedup_claim": False,
        }


def compile_adaptive_orchorbital_plan(
    obligations: Iterable[str],
    operators: Iterable[OperatorTier],
    *,
    budget: ResourceBudget,
    parent_by_obligation: Mapping[str, str | None] | None = None,
    depends_on_by_obligation: Mapping[str, Iterable[str]] | None = None,
    phase36_by_obligation: Mapping[str, Sequence[float]] | None = None,
    coordination_obligation_edges: Iterable[tuple[str, str]] = (),
    max_states: int = 65_536,
) -> AdaptiveOrchorbitalPlan:
    """Bind exact minimal capability cover to recursive orchorbital execution.

    The adaptive runtime decides which operator tiers are necessary.
    This bridge decides how the selected work is composed causally.
    It never grants execution or mutation authority.
    """

    ordered = _strict_obligations(obligations)
    route = minimal_capability_cover(
        ordered,
        operators,
        budget=budget,
        max_states=max_states,
    )
    parents = _normalize_parent_map(ordered, parent_by_obligation)
    dependencies = _normalize_dependency_map(ordered, depends_on_by_obligation)
    phases = _normalize_phase_map(ordered, phase36_by_obligation)

    ids = {obligation: _orbit_id(index, obligation) for index, obligation in enumerate(ordered)}
    assigned = {
        obligation: _operator_for_obligation(route, obligation)
        for obligation in ordered
    }

    specs: list[OrbitSpec] = [OrbitSpec(ROOT_ORBIT_ID, "GREMLIN")]
    for obligation in ordered:
        parent_obligation = parents[obligation]
        specs.append(
            OrbitSpec(
                orbit_id=ids[obligation],
                species=assigned[obligation].species,
                parent_id=ROOT_ORBIT_ID if parent_obligation is None else ids[parent_obligation],
                depends_on=tuple(ids[item] for item in dependencies[obligation]),
                phase36=phases.get(obligation),
            )
        )

    raw_edges: list[tuple[str, str]] = []
    if isinstance(coordination_obligation_edges, (str, bytes, Mapping)) or not isinstance(
        coordination_obligation_edges, Iterable
    ):
        raise ValueError("coordination_obligation_edges must be an iterable")
    for index, raw in enumerate(coordination_obligation_edges):
        if (
            isinstance(raw, (str, bytes, Mapping))
            or not isinstance(raw, Sequence)
            or len(raw) != 2
        ):
            raise ValueError(f"coordination_obligation_edges[{index}] must be a pair")
        left = _strict_text(raw[0], f"coordination_obligation_edges[{index}][0]")
        right = _strict_text(raw[1], f"coordination_obligation_edges[{index}][1]")
        if left not in ids or right not in ids:
            raise ValueError("coordination obligation edge references unknown obligation")
        raw_edges.append((ids[left], ids[right]))

    execution = compile_orchorbital_plan(
        specs,
        root_id=ROOT_ORBIT_ID,
        coordination_edges=raw_edges,
    )
    return AdaptiveOrchorbitalPlan(
        route_plan=route,
        execution_plan=execution,
        obligation_to_orbit=tuple((obligation, ids[obligation]) for obligation in ordered),
        obligation_to_operator=tuple(
            (obligation, assigned[obligation].operator_id) for obligation in ordered
        ),
    )


__all__ = [
    "AdaptiveOrchorbitalPlan",
    "ROOT_ORBIT_ID",
    "SCHEMA",
    "VERSION",
    "compile_adaptive_orchorbital_plan",
]
