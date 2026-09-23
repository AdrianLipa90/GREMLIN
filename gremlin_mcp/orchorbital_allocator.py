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
from gremlin_mcp.orchorbital_fabric import (
    NodeInstance,
    OrchorbitalFabric,
    SpawnRequest,
)

SCHEMA = "GREMLIN_OCTOPUS_ORCHORBITAL_ALLOCATOR_V0_2"
VERSION = "0.2.1"
ALLOCATION_DOMAIN = b"GREMLIN-ORCHORBITAL-ALLOCATION/v0.2\x00"


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


def _deterministic_node_id(caller_id: str, allocation_key: str, operator_id: str) -> str:
    raw = "\x00".join((caller_id, allocation_key, operator_id)).encode("utf-8")
    digest = hashlib.blake2b(ALLOCATION_DOMAIN + raw, digest_size=16).hexdigest()
    return f"ORCHD:{digest}"


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
    operator_to_center: tuple[tuple[str, str], ...]
    allocation_key: str | None = None

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
            "operator_to_center": dict(self.operator_to_center),
            "allocation_key": self.allocation_key,
            "deterministic_replay": self.allocation_key is not None,
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
    candidate_centers_by_operator: Mapping[str, Iterable[str]] | None = None,
    phase36_by_operator: Mapping[str, Sequence[float]] | None = None,
    join_to_caller: bool = True,
    allocation_key: str | None = None,
    max_states: int = 65_536,
) -> OctopusAllocation:
    """Allocate runtime nodes for obligations discovered by any open node.

    This is the OCTOPUS role in the orchorbital architecture. OCTOPUS is not a
    one-shot flat dispatcher: any Bestiary node may invoke this allocator when
    new obligations appear. The returned node instances may themselves invoke
    the allocator again, producing subnodes and sub-subnodes without assigning
    any fixed hierarchy to a species.

    allocation_key optionally makes node identities deterministic and replay-safe.
    caller_id is immutable provenance. center_by_operator fixes a non-causal
    center explicitly. candidate_centers_by_operator lets OCTOPUS choose among
    open candidates by fabric locality with optional T^36 tie-breaking.
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
    candidate_center_map = _validate_operator_map(
        candidate_centers_by_operator,
        field="candidate_centers_by_operator",
        route_ids=route_ids,
    )
    overlap = set(center_map) & set(candidate_center_map)
    if overlap:
        raise ValueError(
            "center_by_operator and candidate_centers_by_operator overlap: "
            f"{sorted(overlap)!r}"
        )
    phase_map = _validate_operator_map(
        phase36_by_operator,
        field="phase36_by_operator",
        route_ids=route_ids,
    )
    partition = _partition_obligations(ordered, route)
    ordered_operators = tuple(
        sorted(route.operators, key=lambda operator: operator.operator_id)
    )
    stable_key = None
    if allocation_key is not None:
        stable_key = _strict_text(allocation_key, "allocation_key")
        if len(stable_key) > 256:
            raise ValueError("allocation_key must contain at most 256 characters")

    deterministic_ids = {
        operator.operator_id: _deterministic_node_id(
            caller.node_id,
            stable_key,
            operator.operator_id,
        )
        for operator in ordered_operators
    } if stable_key is not None else {}

    if deterministic_ids:
        existing = {node.node_id: node for node in fabric.nodes()}
        expected_ids = tuple(deterministic_ids[operator.operator_id] for operator in ordered_operators)
        present = tuple(node_id for node_id in expected_ids if node_id in existing)
        if present and len(present) != len(expected_ids):
            raise RuntimeError("partial deterministic allocation exists")
        if len(present) == len(expected_ids):
            nodes = tuple(existing[node_id] for node_id in expected_ids)
            for operator, node in zip(ordered_operators, nodes):
                if node.species != operator.species:
                    raise RuntimeError("deterministic allocation species mismatch")
                if node.caller_id != caller.node_id:
                    raise RuntimeError("deterministic allocation caller mismatch")
                if node.authority_root_id != fabric.authority_root_id:
                    raise RuntimeError("deterministic allocation authority mismatch")
                if node.obligations != partition[operator.operator_id]:
                    raise RuntimeError("deterministic allocation obligation mismatch")
            operator_to_node = tuple(
                (operator.operator_id, node.node_id)
                for operator, node in zip(ordered_operators, nodes)
            )
            operator_node_map = dict(operator_to_node)
            obligation_to_node = tuple(
                (
                    obligation,
                    operator_node_map[_operator_for_obligation(route, obligation).operator_id],
                )
                for obligation in ordered
            )
            return OctopusAllocation(
                caller_id=caller.node_id,
                route_plan=route,
                nodes=nodes,
                obligation_to_node=obligation_to_node,
                operator_to_node=operator_to_node,
                operator_to_center=tuple(
                    (operator.operator_id, node.center_id or caller.node_id)
                    for operator, node in zip(ordered_operators, nodes)
                ),
                allocation_key=stable_key,
            )

    requests: list[SpawnRequest] = []
    selected_centers: list[tuple[str, str]] = []
    for operator in ordered_operators:
        operator_id = operator.operator_id
        phase = phase_map.get(operator_id)
        if operator_id in center_map:
            center_id = _strict_text(
                center_map[operator_id],
                f"center_by_operator[{operator_id}]",
            )
        elif operator_id in candidate_center_map:
            ranked = fabric.rank_centers(
                caller.node_id,
                candidate_center_map[operator_id],
                phase36=phase,
            )
            center_id = ranked[0]
        else:
            center_id = caller.node_id
        selected_centers.append((operator_id, center_id))
        requests.append(
            SpawnRequest(
                species=operator.species,
                obligations=partition[operator_id],
                center_id=center_id,
                causal_dependencies=(),
                join_to_caller=join_to_caller,
                phase36=None if phase is None else tuple(phase),
                node_id=deterministic_ids.get(operator_id),
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
        operator_to_center=tuple(selected_centers),
        allocation_key=stable_key,
    )


__all__ = [
    "OctopusAllocation",
    "SCHEMA",
    "VERSION",
    "allocate_invocation",
]
