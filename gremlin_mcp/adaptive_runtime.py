from __future__ import annotations

from dataclasses import dataclass
from itertools import count
import math
from typing import Iterable, Mapping, Sequence

import numpy as np

SCHEMA = "GREMLIN_ADAPTIVE_MINIMAL_COVER_RUNTIME_V0_1"
VERSION = "0.1.0"
AUTHORITY = "COGNITIVE_ROUTING_ONLY"
EPISTEMIC = "CHYBA"
TIERS = {
    0: "PROBE",
    1: "LOCAL_CLOSURE",
    2: "RECURSIVE_CLOSURE",
    3: "CROSS_DOMAIN_CLOSURE",
}


@dataclass(frozen=True)
class ResourceBudget:
    tokens: float
    latency: float
    calls: float
    memory: float

    def __post_init__(self) -> None:
        for name, value in (
            ("tokens", self.tokens),
            ("latency", self.latency),
            ("calls", self.calls),
            ("memory", self.memory),
        ):
            if not math.isfinite(float(value)) or float(value) <= 0.0:
                raise ValueError(f"{name} budget must be finite and positive")


@dataclass(frozen=True)
class ResourceCost:
    tokens: float = 0.0
    latency: float = 0.0
    calls: float = 0.0
    memory: float = 0.0

    def __post_init__(self) -> None:
        for name, value in (
            ("tokens", self.tokens),
            ("latency", self.latency),
            ("calls", self.calls),
            ("memory", self.memory),
        ):
            if not math.isfinite(float(value)) or float(value) < 0.0:
                raise ValueError(f"{name} cost must be finite and non-negative")

    def combine_parallel(self, other: "ResourceCost") -> "ResourceCost":
        """Compose independent operators: additive work, max critical latency."""
        return ResourceCost(
            tokens=self.tokens + other.tokens,
            latency=max(self.latency, other.latency),
            calls=self.calls + other.calls,
            memory=self.memory + other.memory,
        )

    def pressure(self, budget: ResourceBudget) -> float:
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
        name = str(self.species).strip().upper()
        if not name:
            raise ValueError("species must be non-empty")
        object.__setattr__(self, "species", name)
        if self.tier not in TIERS:
            raise ValueError("tier must be one of 0,1,2,3")
        caps = frozenset(str(cap).strip() for cap in self.capabilities if str(cap).strip())
        if not caps:
            raise ValueError("capabilities must be non-empty")
        object.__setattr__(self, "capabilities", caps)

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
    out = frozenset(str(value).strip() for value in values if str(value).strip())
    if not out:
        raise ValueError(f"{field} must be non-empty")
    if len(out) > 32:
        raise ValueError(f"{field} is capped at 32 items for exact minimal-cover planning")
    return out


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
) -> RoutePlan:
    """Find an exact deterministic minimum cover over required obligations.

    Optimization is lexicographic:
      1. minimax budget pressure,
      2. fewer operators,
      3. lower aggregate tier,
      4. stable operator-id order.

    No weighted sum of heterogeneous resources is used.
    """
    required = _obligation_set(obligations, "obligations")
    available = tuple(operators)
    if not available:
        raise ValueError("operators must be non-empty")

    useful: list[OperatorTier] = []
    universe: set[str] = set()
    for operator in available:
        hit = operator.capabilities & required
        if hit:
            useful.append(operator)
            universe.update(hit)
    missing = required - universe
    if missing:
        raise ValueError(f"uncovered obligations: {sorted(missing)!r}")

    # Exact dynamic programming on obligation subsets. State stores the best
    # route for each covered subset. With <=32 obligations this remains bounded
    # for normal GREMLIN routing surfaces and fails closed above that bound.
    states: dict[frozenset[str], tuple[tuple[OperatorTier, ...], ResourceCost]] = {
        frozenset(): ((), ResourceCost())
    }
    for operator in sorted(useful, key=lambda item: item.operator_id):
        prior = list(states.items())
        for covered, (chosen, cost) in prior:
            next_covered = covered | (operator.capabilities & required)
            if next_covered == covered:
                continue
            next_chosen = chosen + (operator,)
            next_cost = cost.combine_parallel(operator.cost)
            current = states.get(next_covered)
            if current is None or _plan_key(next_chosen, next_cost, budget) < _plan_key(
                current[0], current[1], budget
            ):
                states[next_covered] = (next_chosen, next_cost)

    chosen, total_cost = states[required]
    ordered = tuple(sorted(chosen, key=lambda item: (item.species, item.tier)))
    return RoutePlan(
        obligations=required,
        operators=ordered,
        covered=required,
        total_cost=total_cost,
        minimax_pressure=total_cost.pressure(budget),
    )


def next_obligations(
    current: Iterable[str],
    *,
    closed: Iterable[str] = (),
    discovered: Iterable[str] = (),
) -> frozenset[str]:
    """Apply one PROBE/CLOSE/CHECK transition to the obligation frontier."""
    current_set = _obligation_set(current, "current")
    closed_set = frozenset(str(value).strip() for value in closed if str(value).strip())
    discovered_set = frozenset(str(value).strip() for value in discovered if str(value).strip())
    if not closed_set <= current_set:
        raise ValueError("closed obligations must be present in the current frontier")
    return (current_set - closed_set) | discovered_set


def escalation_required(unmet_obligations: Iterable[str]) -> bool:
    """The only generic escalation trigger: at least one obligation remains."""
    return any(str(value).strip() for value in unmet_obligations)


def causal_tau(dependencies: Mapping[str, Iterable[str]]) -> dict[str, object]:
    """Assign causal depth tau on a finite directed acyclic dependency graph.

    tau(root)=0
    tau(node)=1+max(tau(parent))

    Independent nodes therefore share tau and may execute concurrently.
    Cycles fail closed.
    """
    if not isinstance(dependencies, Mapping) or not dependencies:
        raise ValueError("dependencies must be a non-empty mapping")

    graph: dict[str, tuple[str, ...]] = {}
    nodes: set[str] = set()
    for raw_node, raw_parents in dependencies.items():
        node = str(raw_node).strip()
        if not node:
            raise ValueError("dependency node names must be non-empty")
        if isinstance(raw_parents, (str, bytes)):
            raise ValueError("dependency parents must be an iterable, not a string")
        parents = tuple(dict.fromkeys(str(parent).strip() for parent in raw_parents if str(parent).strip()))
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


def _normalize_edges(
    nodes: Sequence[str],
    edges: Iterable[tuple[str, str, float]],
) -> tuple[tuple[str, str, float], ...]:
    allowed = set(nodes)
    out: list[tuple[str, str, float]] = []
    for raw_u, raw_v, raw_w in edges:
        u = str(raw_u).strip()
        v = str(raw_v).strip()
        w = float(raw_w)
        if u not in allowed or v not in allowed:
            raise ValueError("edge endpoint is outside declared nodes")
        if u == v:
            raise ValueError("self-loop conductance is not admitted in v0.1")
        if not math.isfinite(w) or w <= 0.0:
            raise ValueError("edge conductance must be finite and positive")
        out.append((u, v, w))
    if not out:
        raise ValueError("edges must be non-empty")
    return tuple(out)


def laplacian(
    nodes: Sequence[str],
    edges: Iterable[tuple[str, str, float]],
) -> tuple[np.ndarray, dict[str, int]]:
    """Build the undirected weighted graph Laplacian L=BWB^T."""
    names = tuple(str(node).strip() for node in nodes)
    if not names or any(not name for name in names) or len(set(names)) != len(names):
        raise ValueError("nodes must be unique non-empty strings")
    normalized = _normalize_edges(names, edges)
    index = {name: pos for pos, name in enumerate(names)}
    matrix = np.zeros((len(names), len(names)), dtype=float)
    for u, v, conductance in normalized:
        i, j = index[u], index[v]
        matrix[i, i] += conductance
        matrix[j, j] += conductance
        matrix[i, j] -= conductance
        matrix[j, i] -= conductance
    return matrix, index


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


def effective_resistance(
    nodes: Sequence[str],
    edges: Iterable[tuple[str, str, float]],
    source: str,
    target: str,
) -> float:
    """Return pairwise effective resistance using the Moore-Penrose inverse.

    The valid injection is b=e_source-e_target, so 1^T b = 0. This corrects
    the ill-posed single-source equation L phi = e_source for a free Laplacian.
    """
    names = tuple(str(node).strip() for node in nodes)
    normalized = _normalize_edges(names, edges)
    src = str(source).strip()
    dst = str(target).strip()
    if src not in names or dst not in names:
        raise ValueError("source and target must be declared nodes")
    if src == dst:
        return 0.0
    if dst not in _reachable(names, normalized, src):
        return math.inf

    matrix, index = laplacian(names, normalized)
    b = np.zeros(len(names), dtype=float)
    b[index[src]] = 1.0
    b[index[dst]] = -1.0
    pinv = np.linalg.pinv(matrix, hermitian=True)
    resistance = float(b @ pinv @ b)
    if resistance < 0.0 and abs(resistance) < 1e-12:
        resistance = 0.0
    if resistance <= 0.0 or not math.isfinite(resistance):
        raise RuntimeError("effective resistance is numerically invalid")
    return resistance


def relational_gravity(
    nodes: Sequence[str],
    edges: Iterable[tuple[str, str, float]],
    query_node: str,
) -> dict[str, float]:
    """Rank memory nodes by graph conductance g_rel=1/R_eff from a query node.

    This is a software graph metric only. It is not a claim of physical gravity.
    Unreachable nodes receive zero gravity; the query node itself is omitted.
    """
    names = tuple(str(node).strip() for node in nodes)
    normalized = _normalize_edges(names, edges)
    query = str(query_node).strip()
    if query not in names:
        raise ValueError("query_node must be a declared node")

    out: dict[str, float] = {}
    for target in names:
        if target == query:
            continue
        resistance = effective_resistance(names, normalized, query, target)
        out[target] = 0.0 if math.isinf(resistance) else 1.0 / resistance
    return dict(sorted(out.items(), key=lambda item: (-item[1], item[0])))


def phase_modulated_edges(
    edges: Iterable[tuple[str, str, float]],
    activation: Mapping[tuple[str, str], float],
) -> tuple[tuple[str, str, float], ...]:
    """Apply read-only hypercrystal/expression factors to graph conductances.

    W_tau = W_0 odot E(Phi_tau). The caller owns the activation model.
    v0.1 only validates and applies finite non-negative factors.
    """
    out: list[tuple[str, str, float]] = []
    for raw_u, raw_v, raw_w in edges:
        u = str(raw_u).strip()
        v = str(raw_v).strip()
        w = float(raw_w)
        if not math.isfinite(w) or w <= 0.0:
            raise ValueError("base edge conductance must be finite and positive")
        factor = activation.get((u, v), activation.get((v, u), 1.0))
        factor = float(factor)
        if not math.isfinite(factor) or factor < 0.0:
            raise ValueError("activation factor must be finite and non-negative")
        modulated = w * factor
        if modulated > 0.0:
            out.append((u, v, modulated))
    return tuple(out)


def runtime_receipt(plan: RoutePlan, tau_result: Mapping[str, object]) -> dict[str, object]:
    """Serialize a non-actuating candidate planning receipt."""
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "obligations": sorted(plan.obligations),
        "route": list(plan.route_ids),
        "minimax_pressure": plan.minimax_pressure,
        "critical_path_depth": int(tau_result["critical_path_depth"]),
        "authority": AUTHORITY,
        "epistemic": EPISTEMIC,
        "canon_allowed": False,
        "execution_admitted": False,
        "memory_mutation_allowed": False,
        "physical_gravity_claim": False,
    }


__all__ = [
    "AUTHORITY",
    "EPISTEMIC",
    "OperatorTier",
    "ResourceBudget",
    "ResourceCost",
    "RoutePlan",
    "SCHEMA",
    "TIERS",
    "VERSION",
    "causal_tau",
    "effective_resistance",
    "escalation_required",
    "laplacian",
    "minimal_capability_cover",
    "next_obligations",
    "phase_modulated_edges",
    "relational_gravity",
    "runtime_receipt",
]
