from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import math
from typing import Any

import numpy as np

SCHEMA = "GREMLIN_ADAPTIVE_MINIMAL_COVER_RUNTIME_V0_1"
VERSION = "0.1.0"
AUTHORITY = "COGNITIVE_ROUTING_ONLY"
EPISTEMIC = "CHYBA"
DEFAULT_MAX_DP_STATES = 65_536
TIERS = {
    0: "PROBE",
    1: "LOCAL_CLOSURE",
    2: "RECURSIVE_CLOSURE",
    3: "CROSS_DOMAIN_CLOSURE",
}


def _strict_number(value: Any, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ):
        raise ValueError(f"{field} must be a real number")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{field} must be finite")
    if positive and out <= 0.0:
        raise ValueError(f"{field} must be positive")
    if not positive and out < 0.0:
        raise ValueError(f"{field} must be non-negative")
    return out


def _strict_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    out = value.strip()
    if not out:
        raise ValueError(f"{field} must be non-empty")
    return out


def _strict_text_set(
    values: Iterable[str],
    field: str,
    *,
    allow_empty: bool = False,
) -> frozenset[str]:
    if isinstance(values, (str, bytes, Mapping)) or not isinstance(values, Iterable):
        raise ValueError(f"{field} must be an iterable of strings")
    out = frozenset(_strict_text(value, field) for value in values)
    if not out and not allow_empty:
        raise ValueError(f"{field} must be non-empty")
    return out


@dataclass(frozen=True)
class ResourceBudget:
    tokens: float
    latency: float
    calls: float
    memory: float

    def __post_init__(self) -> None:
        for name in ("tokens", "latency", "calls", "memory"):
            object.__setattr__(
                self,
                name,
                _strict_number(getattr(self, name), f"{name} budget", positive=True),
            )


@dataclass(frozen=True)
class ResourceCost:
    tokens: float = 0.0
    latency: float = 0.0
    calls: float = 0.0
    memory: float = 0.0

    def __post_init__(self) -> None:
        for name in ("tokens", "latency", "calls", "memory"):
            object.__setattr__(
                self,
                name,
                _strict_number(getattr(self, name), f"{name} cost"),
            )

    def combine_parallel(self, other: "ResourceCost") -> "ResourceCost":
        if not isinstance(other, ResourceCost):
            raise ValueError("parallel cost must be a ResourceCost")
        return ResourceCost(
            tokens=self.tokens + other.tokens,
            latency=max(self.latency, other.latency),
            calls=self.calls + other.calls,
            memory=self.memory + other.memory,
        )

    def pressure(self, budget: ResourceBudget) -> float:
        if not isinstance(budget, ResourceBudget):
            raise ValueError("budget must be a ResourceBudget")
        return max(
            self.tokens / budget.tokens,
            self.latency / budget.latency,
            self.calls / budget.calls,
            self.memory / budget.memory,
        )


@dataclass(frozen=True)
class OperatorTier:
    species: str
    tier: int
    capabilities: frozenset[str]
    cost: ResourceCost = ResourceCost()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "species",
            _strict_text(self.species, "species").upper(),
        )
        if isinstance(self.tier, bool) or not isinstance(self.tier, int) or self.tier not in TIERS:
            raise ValueError("tier must be one of integer 0,1,2,3")
        object.__setattr__(
            self,
            "capabilities",
            _strict_text_set(self.capabilities, "capabilities"),
        )
        if not isinstance(self.cost, ResourceCost):
            raise ValueError("cost must be a ResourceCost")

    @property
    def operator_id(self) -> str:
        return f"{self.species}:T{self.tier}"


@dataclass(frozen=True)
class RoutePlan:
    obligations: frozenset[str]
    operators: tuple[OperatorTier, ...]
    covered: frozenset[str]
    total_cost: ResourceCost
    minimax_pressure: float

    @property
    def route_ids(self) -> tuple[str, ...]:
        return tuple(operator.operator_id for operator in self.operators)

    @property
    def complete(self) -> bool:
        return self.covered == self.obligations


def _obligation_set(values: Iterable[str], field: str) -> frozenset[str]:
    return _strict_text_set(values, field)


def _plan_key(
    operators: Sequence[OperatorTier],
    total_cost: ResourceCost,
    budget: ResourceBudget,
) -> tuple[float, int, int, tuple[str, ...]]:
    return (
        total_cost.pressure(budget),
        len(operators),
        sum(operator.tier for operator in operators),
        tuple(sorted(operator.operator_id for operator in operators)),
    )


def minimal_capability_cover(
    obligations: Iterable[str],
    operators: Iterable[OperatorTier],
    *,
    budget: ResourceBudget,
    max_states: int = DEFAULT_MAX_DP_STATES,
) -> RoutePlan:
    """Return an exact, deterministic, budget-admissible capability cover.

    Optimization among admissible complete routes is lexicographic:
      1. minimax budget pressure,
      2. fewer operators,
      3. lower aggregate tier,
      4. stable operator-id order.

    At most one tier of any species may occur in one route step. The exact
    dynamic program fails closed if its explicit state budget would be exceeded.
    """
    if not isinstance(budget, ResourceBudget):
        raise ValueError("budget must be a ResourceBudget")
    if isinstance(max_states, bool) or not isinstance(max_states, int) or max_states <= 0:
        raise ValueError("max_states must be a positive integer")

    required = _obligation_set(obligations, "obligations")
    if isinstance(operators, (str, bytes, Mapping)) or not isinstance(operators, Iterable):
        raise ValueError("operators must be an iterable of OperatorTier values")
    available = tuple(operators)
    if not available:
        raise ValueError("operators must be non-empty")
    if not all(isinstance(operator, OperatorTier) for operator in available):
        raise ValueError("operators must contain only OperatorTier values")

    useful: list[OperatorTier] = []
    universe: set[str] = set()
    by_species: dict[str, list[OperatorTier]] = {}
    seen_operator_ids: set[str] = set()
    for operator in available:
        if operator.operator_id in seen_operator_ids:
            raise ValueError(f"duplicate operator tier: {operator.operator_id}")
        seen_operator_ids.add(operator.operator_id)
        by_species.setdefault(operator.species, []).append(operator)
        hit = operator.capabilities & required
        if hit:
            useful.append(operator)
            universe.update(hit)

    missing = required - universe
    if missing:
        raise ValueError(f"uncovered obligations: {sorted(missing)!r}")

    for species, family in by_species.items():
        ordered_family = sorted(family, key=lambda item: item.tier)
        prior_caps: frozenset[str] | None = None
        for operator in ordered_family:
            if prior_caps is not None and not prior_caps <= operator.capabilities:
                raise ValueError(
                    f"{species} tier capabilities must be monotone by closure scope"
                )
            prior_caps = operator.capabilities

    useful_by_species: dict[str, list[OperatorTier]] = {}
    for operator in useful:
        useful_by_species.setdefault(operator.species, []).append(operator)

    states: dict[frozenset[str], tuple[tuple[OperatorTier, ...], ResourceCost]] = {
        frozenset(): ((), ResourceCost())
    }
    for species in sorted(useful_by_species):
        options = tuple(sorted(useful_by_species[species], key=lambda item: item.tier))
        prior_states = list(states.items())
        next_states = dict(states)
        for covered, (chosen, cost) in prior_states:
            for operator in options:
                next_covered = covered | (operator.capabilities & required)
                if next_covered == covered:
                    continue
                next_chosen = chosen + (operator,)
                next_cost = cost.combine_parallel(operator.cost)
                if next_cost.pressure(budget) > 1.0:
                    continue
                current = next_states.get(next_covered)
                if current is None:
                    if len(next_states) >= max_states:
                        raise ValueError("exact planner state budget exceeded")
                    next_states[next_covered] = (next_chosen, next_cost)
                elif _plan_key(next_chosen, next_cost, budget) < _plan_key(
                    current[0], current[1], budget
                ):
                    next_states[next_covered] = (next_chosen, next_cost)
        states = next_states

    if required not in states:
        raise ValueError("no complete route fits resource budget")

    chosen, total_cost = states[required]
    ordered = tuple(sorted(chosen, key=lambda item: (item.species, item.tier)))
    pressure = total_cost.pressure(budget)
    return RoutePlan(
        obligations=required,
        operators=ordered,
        covered=required,
        total_cost=total_cost,
        minimax_pressure=pressure,
    )


def next_obligations(
    current: Iterable[str],
    *,
    closed: Iterable[str] = (),
    discovered: Iterable[str] = (),
) -> frozenset[str]:
    current_set = _strict_text_set(current, "current")
    closed_set = _strict_text_set(closed, "closed", allow_empty=True)
    discovered_set = _strict_text_set(discovered, "discovered", allow_empty=True)
    if not closed_set <= current_set:
        raise ValueError("closed obligations must be present in the current frontier")
    return (current_set - closed_set) | discovered_set


def continuation_required(unmet_obligations: Iterable[str]) -> bool:
    unmet = _strict_text_set(unmet_obligations, "unmet_obligations", allow_empty=True)
    return bool(unmet)


def escalation_required(
    unmet_obligations: Iterable[str],
    current_capabilities: Iterable[str] = (),
) -> bool:
    """Escalate only when an unmet obligation lies outside current capability."""
    unmet = _strict_text_set(unmet_obligations, "unmet_obligations", allow_empty=True)
    if not unmet:
        return False
    current = _strict_text_set(
        current_capabilities,
        "current_capabilities",
        allow_empty=True,
    )
    return not unmet <= current


def causal_tau(dependencies: Mapping[str, Iterable[str]]) -> dict[str, object]:
    """Assign causal depth tau on a finite directed acyclic dependency graph."""
    if not isinstance(dependencies, Mapping) or not dependencies:
        raise ValueError("dependencies must be a non-empty mapping")

    graph: dict[str, tuple[str, ...]] = {}
    nodes: set[str] = set()
    for raw_node, raw_parents in dependencies.items():
        node = _strict_text(raw_node, "dependency node")
        if isinstance(raw_parents, (str, bytes, Mapping)) or not isinstance(raw_parents, Iterable):
            raise ValueError("dependency parents must be an iterable of strings")
        parents = tuple(
            dict.fromkeys(_strict_text(parent, "dependency parent") for parent in raw_parents)
        )
        if node in parents:
            raise ValueError("self-dependency is a cycle")
        graph[node] = parents
        nodes.add(node)
        nodes.update(parents)

    for node in nodes:
        graph.setdefault(node, ())

    visiting: set[str] = set()
    memo: dict[str, int] = {}

    def depth(node: str) -> int:
        if node in memo:
            return memo[node]
        if node in visiting:
            raise ValueError("dependency graph contains a cycle")
        visiting.add(node)
        parents = graph[node]
        value = 0 if not parents else 1 + max(depth(parent) for parent in parents)
        visiting.remove(node)
        memo[node] = value
        return value

    for node in sorted(nodes):
        depth(node)

    critical = max(memo.values(), default=0)
    layers: dict[int, list[str]] = {}
    for node, value in sorted(memo.items()):
        layers.setdefault(value, []).append(node)
    return {
        "tau": dict(sorted(memo.items())),
        "critical_path_depth": critical,
        "layers": {key: tuple(value) for key, value in sorted(layers.items())},
    }


def _validated_nodes(nodes: Sequence[str]) -> tuple[str, ...]:
    if isinstance(nodes, (str, bytes, Mapping)) or not isinstance(nodes, Sequence):
        raise ValueError("nodes must be a sequence of strings")
    names = tuple(_strict_text(node, "node") for node in nodes)
    if not names or len(set(names)) != len(names):
        raise ValueError("nodes must be unique non-empty strings")
    return names


def _normalize_edges(
    nodes: Sequence[str],
    edges: Iterable[tuple[str, str, float]],
) -> tuple[tuple[str, str, float], ...]:
    allowed = set(nodes)
    if isinstance(edges, (str, bytes, Mapping)) or not isinstance(edges, Iterable):
        raise ValueError("edges must be an iterable of (u,v,conductance) triples")

    out: list[tuple[str, str, float]] = []
    for index, raw_edge in enumerate(edges):
        if isinstance(raw_edge, (str, bytes, Mapping)) or not isinstance(raw_edge, Sequence) or len(raw_edge) != 3:
            raise ValueError(f"edge[{index}] must be a three-item sequence")
        raw_u, raw_v, raw_w = raw_edge
        u = _strict_text(raw_u, f"edge[{index}].u")
        v = _strict_text(raw_v, f"edge[{index}].v")
        w = _strict_number(raw_w, f"edge[{index}].conductance", positive=True)
        if u not in allowed or v not in allowed:
            raise ValueError("edge endpoint is outside declared nodes")
        if u == v:
            raise ValueError("self-loop conductance is not admitted in v0.1")
        out.append((u, v, w))

    if not out:
        raise ValueError("edges must be non-empty")
    return tuple(out)


def _laplacian_from_normalized(
    names: Sequence[str],
    edges: Sequence[tuple[str, str, float]],
) -> tuple[np.ndarray, dict[str, int]]:
    index = {name: pos for pos, name in enumerate(names)}
    matrix = np.zeros((len(names), len(names)), dtype=float)
    for u, v, conductance in edges:
        i, j = index[u], index[v]
        matrix[i, i] += conductance
        matrix[j, j] += conductance
        matrix[i, j] -= conductance
        matrix[j, i] -= conductance
    return matrix, index


def laplacian(
    nodes: Sequence[str],
    edges: Iterable[tuple[str, str, float]],
) -> tuple[np.ndarray, dict[str, int]]:
    names = _validated_nodes(nodes)
    normalized = _normalize_edges(names, edges)
    return _laplacian_from_normalized(names, normalized)


def _reachable(
    nodes: Sequence[str],
    edges: Sequence[tuple[str, str, float]],
    source: str,
) -> set[str]:
    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    for u, v, _ in edges:
        adjacency[u].add(v)
        adjacency[v].add(u)
    seen = {source}
    frontier = [source]
    while frontier:
        current = frontier.pop()
        for neighbor in adjacency[current]:
            if neighbor not in seen:
                seen.add(neighbor)
                frontier.append(neighbor)
    return seen


def _resistance_from_pinv(
    pinv: np.ndarray,
    index: Mapping[str, int],
    source: str,
    target: str,
) -> float:
    b = np.zeros(len(index), dtype=float)
    b[index[source]] = 1.0
    b[index[target]] = -1.0
    resistance = float(b @ pinv @ b)
    if resistance < 0.0 and abs(resistance) < 1e-12:
        resistance = 0.0
    if resistance <= 0.0 or not math.isfinite(resistance):
        raise RuntimeError("effective resistance is numerically invalid")
    return resistance


def effective_resistance(
    nodes: Sequence[str],
    edges: Iterable[tuple[str, str, float]],
    source: str,
    target: str,
) -> float:
    """Return pairwise effective resistance for balanced injection e_s-e_t."""
    names = _validated_nodes(nodes)
    normalized = _normalize_edges(names, edges)
    src = _strict_text(source, "source")
    dst = _strict_text(target, "target")
    if src not in names or dst not in names:
        raise ValueError("source and target must be declared nodes")
    if src == dst:
        return 0.0
    if dst not in _reachable(names, normalized, src):
        return math.inf

    matrix, index = _laplacian_from_normalized(names, normalized)
    pinv = np.linalg.pinv(matrix, hermitian=True)
    return _resistance_from_pinv(pinv, index, src, dst)


def relational_gravity(
    nodes: Sequence[str],
    edges: Iterable[tuple[str, str, float]],
    query_node: str,
) -> dict[str, float]:
    """Rank nodes by g_rel=1/R_eff using one pseudoinverse per graph."""
    names = _validated_nodes(nodes)
    normalized = _normalize_edges(names, edges)
    query = _strict_text(query_node, "query_node")
    if query not in names:
        raise ValueError("query_node must be a declared node")

    reachable = _reachable(names, normalized, query)
    matrix, index = _laplacian_from_normalized(names, normalized)
    pinv = np.linalg.pinv(matrix, hermitian=True)

    out: dict[str, float] = {}
    for target in names:
        if target == query:
            continue
        if target not in reachable:
            out[target] = 0.0
            continue
        resistance = _resistance_from_pinv(pinv, index, query, target)
        out[target] = 1.0 / resistance
    return dict(sorted(out.items(), key=lambda item: (-item[1], item[0])))


def phase_modulated_edges(
    edges: Iterable[tuple[str, str, float]],
    activation: Mapping[tuple[str, str], float],
) -> tuple[tuple[str, str, float], ...]:
    if isinstance(edges, (str, bytes, Mapping)) or not isinstance(edges, Iterable):
        raise ValueError("edges must be an iterable of triples")
    if not isinstance(activation, Mapping):
        raise ValueError("activation must be a mapping")

    out: list[tuple[str, str, float]] = []
    for index, raw_edge in enumerate(edges):
        if isinstance(raw_edge, (str, bytes, Mapping)) or not isinstance(raw_edge, Sequence) or len(raw_edge) != 3:
            raise ValueError(f"edge[{index}] must be a three-item sequence")
        raw_u, raw_v, raw_w = raw_edge
        u = _strict_text(raw_u, f"edge[{index}].u")
        v = _strict_text(raw_v, f"edge[{index}].v")
        w = _strict_number(raw_w, f"edge[{index}].conductance", positive=True)
        factor_raw = activation.get((u, v), activation.get((v, u), 1.0))
        factor = _strict_number(factor_raw, f"activation[{u},{v}]")
        modulated = w * factor
        if modulated > 0.0:
            out.append((u, v, modulated))
    return tuple(out)


def runtime_receipt(plan: RoutePlan, tau_result: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(plan, RoutePlan):
        raise ValueError("plan must be a RoutePlan")
    if not isinstance(tau_result, Mapping):
        raise ValueError("tau_result must be a mapping")
    depth = tau_result.get("critical_path_depth")
    if isinstance(depth, bool) or not isinstance(depth, int) or depth < 0:
        raise ValueError("critical_path_depth must be a non-negative integer")
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "obligations": sorted(plan.obligations),
        "route": list(plan.route_ids),
        "minimax_pressure": plan.minimax_pressure,
        "critical_path_depth": depth,
        "authority": AUTHORITY,
        "epistemic": EPISTEMIC,
        "canon_allowed": False,
        "execution_admitted": False,
        "memory_mutation_allowed": False,
        "physical_gravity_claim": False,
    }


__all__ = [
    "AUTHORITY",
    "DEFAULT_MAX_DP_STATES",
    "EPISTEMIC",
    "OperatorTier",
    "ResourceBudget",
    "ResourceCost",
    "RoutePlan",
    "SCHEMA",
    "TIERS",
    "VERSION",
    "causal_tau",
    "continuation_required",
    "effective_resistance",
    "escalation_required",
    "laplacian",
    "minimal_capability_cover",
    "next_obligations",
    "phase_modulated_edges",
    "relational_gravity",
    "runtime_receipt",
]
