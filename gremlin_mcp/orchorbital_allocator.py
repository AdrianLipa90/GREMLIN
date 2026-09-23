from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from gremlin_mcp.adaptive_runtime import (
    OperatorTier,
    ResourceBudget,
    RoutePlan,
    minimal_capability_cover,
)
from gremlin_mcp.orchorbital_fabric import (
    NodeInstance,
    OrchorbitalFabric,
    SpawnRequest,
)

SCHEMA = "GREMLIN_OCTOPUS_ORCHORBITAL_ALLOCATOR_V0_2"
VERSION = "0.2.0"


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


def _validate_operator_map(
    value: Mapping[str, Any] | None,
    *,
    field: str,
    route_ids: set[str],
) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a mapping")
    unknown = set(value) - route_ids
    if unknown:
        raise ValueError(f"{field} contains operators outside selected route: {sorted(unknown)!r}")
    return dict(value)


def _operator_for_obligation(plan: RoutePlan, obligation: str) -> OperatorTier:
    candidates = [
        operator
        for operator in plan.operators
        if obligation in operator.capabilities
    ]
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


def _partition_obligations(
    ordered_obligations: Sequence[str],
    plan: RoutePlan,
) -> dict[str, tuple[str, ...]]:
    rows: dict[str, list[str]] = {
        operator.operator_id: [] for operator in plan.operators
    }
    for obligation in ordered_obligations:
        operator = _operator_for_obligation(plan, obligation)
        rows[operator.operator_id].append(obligation)

    empty = [
        operator_id
        for operator_id, assigned in rows.items()
        if not assigned
    ]
    if empty:
        raise RuntimeError(
            f"minimal cover contains operator with no assigned obligation: {empty!r}"
        )
    return {
        operator_id: tuple(assigned)
        for operator_id, assigned in rows.items()
    }


@dataclass(frozen=True)
class OctopusAllocation:
    caller_id: str
    route_plan: RoutePlan
    nodes: tuple[NodeInstance, ...]
    obligation_to_node: tuple[tuple[str, str], ...]
    operator_to_node: tuple[tuple[str, str], ...]

    def receipt(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "allocator": "OCTOPUS",
            "caller_id": self.caller_id,
            "selected_route": list(self.route_plan.route_ids),
            "minimax_pressure": self.route_plan.minimax_pressure,
            "node_ids": [node.node_id for node in self.nodes],
            "obligation_to_node": dict(self.obligation_to_node),
            "operator_to_node": dict(self.operator_to_node),
            "recursive_invocation_allowed": True,
            "species_position_fixed": False,
            "caller_is_provenance_not_center": True,
            "authority": "COGNITIVE_ROUTING_ONLY",
            "epistemic": "CHYBA",
            "canon_allowed": False,
            "execution_admitted": False,
            "memory_mutation_allowed": False,
            "speedup_claim": False,
        }


def allocate_invocation(
    fabric: OrchorbitalFabric,
    caller_id: str,
    obligations: Iterable[str],
    operators: Iterable[OperatorTier],
    *,
    budget: ResourceBudget,
    center_by_operator: Mapping[str, str] | None = None,
    phase36_by_operator: Mapping[str, Sequence[float]] | None = None,
    join_to_caller: bool = True,
    max_states: int = 65_536,
) -> OctopusAllocation:
    """Allocate runtime nodes for obligations discovered by any open node.

    This is the OCTOPUS role in the orchorbital architecture. OCTOPUS is not a
    one-shot flat dispatcher: any Bestiary node may invoke this allocator when
    new obligations appear. The returned node instances may themselves invoke
    the allocator again, producing subnodes and sub-subnodes without assigning
    any fixed hierarchy to a species.

    caller_id is immutable provenance. center_by_operator controls non-causal
    locality and may point to any currently open node in the same fabric.
    """

    if not isinstance(fabric, OrchorbitalFabric):
        raise ValueError("fabric must be an OrchorbitalFabric")
    if not isinstance(budget, ResourceBudget):
        raise ValueError("budget must be a ResourceBudget")
    if not isinstance(join_to_caller, bool):
        raise ValueError("join_to_caller must be boolean")

    caller = fabric.node(caller_id)
    if caller.status != "OPEN":
        raise RuntimeError("caller node must be open")

    ordered = _strict_obligations(obligations)
    route = minimal_capability_cover(
        ordered,
        operators,
        budget=budget,
        max_states=max_states,
    )
    route_ids = set(route.route_ids)
    center_map = _validate_operator_map(
        center_by_operator,
        field="center_by_operator",
        route_ids=route_ids,
    )
    phase_map = _validate_operator_map(
        phase36_by_operator,
        field="phase36_by_operator",
        route_ids=route_ids,
    )
    partition = _partition_obligations(ordered, route)

    requests: list[SpawnRequest] = []
    ordered_operators = tuple(
        sorted(route.operators, key=lambda operator: operator.operator_id)
    )
    for operator in ordered_operators:
        operator_id = operator.operator_id
        center_id = center_map.get(operator_id, caller.node_id)
        phase = phase_map.get(operator_id)
        requests.append(
            SpawnRequest(
                species=operator.species,
                obligations=partition[operator_id],
                center_id=center_id,
                causal_dependencies=(),
                join_to_caller=join_to_caller,
                phase36=None if phase is None else tuple(phase),
            )
        )

    nodes = fabric.spawn_batch(caller.node_id, requests)
    operator_to_node = tuple(
        (operator.operator_id, node.node_id)
        for operator, node in zip(ordered_operators, nodes)
    )
    operator_node_map = dict(operator_to_node)

    obligation_to_node: list[tuple[str, str]] = []
    for obligation in ordered:
        operator = _operator_for_obligation(route, obligation)
        obligation_to_node.append(
            (obligation, operator_node_map[operator.operator_id])
        )

    return OctopusAllocation(
        caller_id=caller.node_id,
        route_plan=route,
        nodes=nodes,
        obligation_to_node=tuple(obligation_to_node),
        operator_to_node=operator_to_node,
    )


__all__ = [
    "OctopusAllocation",
    "SCHEMA",
    "VERSION",
    "allocate_invocation",
]
