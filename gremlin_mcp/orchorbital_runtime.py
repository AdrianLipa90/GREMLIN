from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import math
from typing import Any

SCHEMA = "GREMLIN_ORCHORBITAL_RUNTIME_V0_1"
VERSION = "0.1.0"
AUTHORITY = "COGNITIVE_ROUTING_ONLY"
EPISTEMIC = "CHYBA"
TAU = 2.0 * math.pi
DIM = 36
MAX_IDENTIFIER_CHARS = 128

KNOWN_SPECIES = frozenset(
    {
        "HUMMINGBIRD",
        "OCTOPUS",
        "SPIDER",
        "RAVEN",
        "HOUND",
        "MOLE",
        "OWL",
        "ANT",
        "MANTIS",
        "FOX",
        "BEAVER",
        "BAT",
        "CANARY",
        "SERPENT",
        "CHAMELEON",
        "ELEPHANT",
        "BEES",
        "BELZEBUB",
        "FERRET",
        "GREMLIN",
    }
)


def _strict_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    out = value.strip()
    if not out or len(out) > MAX_IDENTIFIER_CHARS:
        raise ValueError(f"{field} must contain 1..{MAX_IDENTIFIER_CHARS} characters")
    return out


def _strict_species(value: Any) -> str:
    species = _strict_text(value, "species").upper()
    if species not in KNOWN_SPECIES:
        raise ValueError(f"unsupported species: {species}")
    return species


def _strict_ids(values: Iterable[str], field: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, Mapping)) or not isinstance(values, Iterable):
        raise ValueError(f"{field} must be an iterable of identifiers")
    out: list[str] = []
    for index, value in enumerate(values):
        item = _strict_text(value, f"{field}[{index}]")
        if item not in out:
            out.append(item)
    return tuple(out)


def _strict_phase36(value: Sequence[float] | None) -> tuple[float, ...] | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        raise ValueError("phase36 must be a sequence")
    if len(value) != DIM:
        raise ValueError(f"phase36 must contain exactly {DIM} values")
    out = tuple(float(item) for item in value)
    if not all(math.isfinite(item) and 0.0 <= item < TAU for item in out):
        raise ValueError("phase36 must contain finite values in [0,2pi)")
    return out


@dataclass(frozen=True)
class OrbitSpec:
    """One recursively composable orchestration orbit.

    parent_id defines the strict containment tree.
    depends_on defines extra causal dependencies between orbit closures.
    phase36 is an optional scheduling coordinate only.
    """

    orbit_id: str
    species: str
    parent_id: str | None = None
    depends_on: tuple[str, ...] = ()
    phase36: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        orbit_id = _strict_text(self.orbit_id, "orbit_id")
        species = _strict_species(self.species)
        parent = None if self.parent_id is None else _strict_text(self.parent_id, "parent_id")
        dependencies = _strict_ids(self.depends_on, "depends_on")
        phase = _strict_phase36(self.phase36)
        if parent == orbit_id:
            raise ValueError("orbit cannot parent itself")
        if orbit_id in dependencies:
            raise ValueError("orbit cannot causally depend on itself")
        object.__setattr__(self, "orbit_id", orbit_id)
        object.__setattr__(self, "species", species)
        object.__setattr__(self, "parent_id", parent)
        object.__setattr__(self, "depends_on", dependencies)
        object.__setattr__(self, "phase36", phase)


@dataclass(frozen=True)
class OrbitEvent:
    event_id: str
    orbit_id: str
    kind: str
    prerequisites: tuple[str, ...]
    tau: int


@dataclass(frozen=True)
class OrchorbitalPlan:
    root_id: str
    orbits: tuple[OrbitSpec, ...]
    coordination_edges: tuple[tuple[str, str], ...]
    events: tuple[OrbitEvent, ...]
    tau_layers: tuple[tuple[str, ...], ...]
    critical_path_depth: int
    max_parallel_width: int
    max_local_join_fan_in: int
    global_join_fan_in: int

    def event_map(self) -> dict[str, OrbitEvent]:
        return {event.event_id: event for event in self.events}

    def orbit_map(self) -> dict[str, OrbitSpec]:
        return {orbit.orbit_id: orbit for orbit in self.orbits}


def _open_id(orbit_id: str) -> str:
    return f"OPEN:{orbit_id}"


def _close_id(orbit_id: str) -> str:
    return f"CLOSE:{orbit_id}"


def _children(orbits: Mapping[str, OrbitSpec]) -> dict[str, tuple[str, ...]]:
    out: dict[str, list[str]] = {orbit_id: [] for orbit_id in orbits}
    for orbit in orbits.values():
        if orbit.parent_id is not None:
            out[orbit.parent_id].append(orbit.orbit_id)
    return {key: tuple(sorted(value)) for key, value in out.items()}


def _validate_tree(orbits: Mapping[str, OrbitSpec], root_id: str) -> None:
    roots = sorted(orbit.orbit_id for orbit in orbits.values() if orbit.parent_id is None)
    if roots != [root_id]:
        raise ValueError(f"orchorbital plan requires exactly one declared root: {root_id!r}")
    for orbit in orbits.values():
        if orbit.parent_id is not None and orbit.parent_id not in orbits:
            raise ValueError(f"missing parent for {orbit.orbit_id}: {orbit.parent_id}")
        for dependency in orbit.depends_on:
            if dependency not in orbits:
                raise ValueError(f"missing dependency for {orbit.orbit_id}: {dependency}")

    for start in orbits:
        seen: set[str] = set()
        current: str | None = start
        while current is not None:
            if current in seen:
                raise ValueError(f"parent cycle detected at orbit {current}")
            seen.add(current)
            current = orbits[current].parent_id
        if root_id not in seen:
            raise ValueError(f"orbit {start} is disconnected from root {root_id}")


def _normalize_coordination_edges(
    raw_edges: Iterable[tuple[str, str]],
    orbits: Mapping[str, OrbitSpec],
) -> tuple[tuple[str, str], ...]:
    if isinstance(raw_edges, (str, bytes, Mapping)) or not isinstance(raw_edges, Iterable):
        raise ValueError("coordination_edges must be an iterable")
    edges: set[tuple[str, str]] = set()
    for index, raw in enumerate(raw_edges):
        if (
            isinstance(raw, (str, bytes, Mapping))
            or not isinstance(raw, Sequence)
            or len(raw) != 2
        ):
            raise ValueError(f"coordination_edges[{index}] must be a pair")
        left = _strict_text(raw[0], f"coordination_edges[{index}][0]")
        right = _strict_text(raw[1], f"coordination_edges[{index}][1]")
        if left == right:
            raise ValueError("coordination edge cannot be a self-loop")
        if left not in orbits or right not in orbits:
            raise ValueError("coordination edge endpoint is outside the orbit tree")
        edges.add(tuple(sorted((left, right))))
    return tuple(sorted(edges))


def _event_prerequisites(
    orbits: Mapping[str, OrbitSpec],
    child_map: Mapping[str, tuple[str, ...]],
) -> dict[str, tuple[str, ...]]:
    deps: dict[str, tuple[str, ...]] = {}
    for orbit_id, orbit in orbits.items():
        open_deps: list[str] = []
        if orbit.parent_id is not None:
            open_deps.append(_open_id(orbit.parent_id))
        open_deps.extend(_close_id(dep) for dep in orbit.depends_on)
        deps[_open_id(orbit_id)] = tuple(sorted(set(open_deps)))

        close_deps = [_open_id(orbit_id)]
        close_deps.extend(_close_id(child) for child in child_map[orbit_id])
        deps[_close_id(orbit_id)] = tuple(sorted(set(close_deps)))
    return deps


def _layer_events(prerequisites: Mapping[str, tuple[str, ...]]) -> tuple[dict[str, int], tuple[tuple[str, ...], ...]]:
    unknown = {
        parent
        for parents in prerequisites.values()
        for parent in parents
        if parent not in prerequisites
    }
    if unknown:
        raise ValueError(f"event prerequisites reference unknown events: {sorted(unknown)!r}")

    children: dict[str, list[str]] = {event_id: [] for event_id in prerequisites}
    indegree = {event_id: len(parents) for event_id, parents in prerequisites.items()}
    for event_id, parents in prerequisites.items():
        for parent in parents:
            children[parent].append(event_id)

    tau: dict[str, int] = {}
    ready = sorted(event_id for event_id, degree in indegree.items() if degree == 0)
    processed = 0
    while ready:
        event_id = ready.pop(0)
        parents = prerequisites[event_id]
        tau[event_id] = 0 if not parents else 1 + max(tau[parent] for parent in parents)
        processed += 1
        for child in sorted(children[event_id]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()

    if processed != len(prerequisites):
        cyclic = sorted(event_id for event_id, degree in indegree.items() if degree > 0)
        raise ValueError(f"causal cycle detected: {cyclic!r}")

    depth = max(tau.values(), default=0)
    layers = tuple(
        tuple(sorted(event_id for event_id, layer in tau.items() if layer == level))
        for level in range(depth + 1)
    )
    return tau, layers


def compile_orchorbital_plan(
    specs: Iterable[OrbitSpec],
    *,
    root_id: str,
    coordination_edges: Iterable[tuple[str, str]] = (),
) -> OrchorbitalPlan:
    """Compile a recursive fork/local-join execution graph.

    Each orbit opens after its parent has opened. An internal orbit closes only
    after its own immediate children have closed. This creates local recursive
    barriers instead of one global specialist barrier. Explicit depends_on
    edges bind an orbit OPEN event to the CLOSE event of the dependency.
    """

    root = _strict_text(root_id, "root_id")
    if isinstance(specs, (str, bytes, Mapping)) or not isinstance(specs, Iterable):
        raise ValueError("specs must be an iterable of OrbitSpec values")
    rows = tuple(specs)
    if not rows or not all(isinstance(row, OrbitSpec) for row in rows):
        raise ValueError("specs must contain OrbitSpec values")

    orbit_map: dict[str, OrbitSpec] = {}
    for orbit in rows:
        if orbit.orbit_id in orbit_map:
            raise ValueError(f"duplicate orbit_id: {orbit.orbit_id}")
        orbit_map[orbit.orbit_id] = orbit
    if root not in orbit_map:
        raise ValueError("root_id must name a declared orbit")

    _validate_tree(orbit_map, root)
    child_map = _children(orbit_map)
    edges = _normalize_coordination_edges(coordination_edges, orbit_map)
    prerequisites = _event_prerequisites(orbit_map, child_map)
    tau, layers = _layer_events(prerequisites)

    events = tuple(
        OrbitEvent(
            event_id=event_id,
            orbit_id=event_id.split(":", 1)[1],
            kind=event_id.split(":", 1)[0],
            prerequisites=prerequisites[event_id],
            tau=tau[event_id],
        )
        for event_id in sorted(prerequisites, key=lambda event_id: (tau[event_id], event_id))
    )
    max_local = max((len(children) for children in child_map.values()), default=0)
    return OrchorbitalPlan(
        root_id=root,
        orbits=tuple(sorted(rows, key=lambda orbit: orbit.orbit_id)),
        coordination_edges=edges,
        events=events,
        tau_layers=layers,
        critical_path_depth=max(tau.values(), default=0),
        max_parallel_width=max((len(layer) for layer in layers), default=0),
        max_local_join_fan_in=max_local,
        global_join_fan_in=len(child_map[root]),
    )


def ready_events(plan: OrchorbitalPlan, completed_event_ids: Iterable[str]) -> tuple[str, ...]:
    if not isinstance(plan, OrchorbitalPlan):
        raise ValueError("plan must be an OrchorbitalPlan")
    completed = set(_strict_ids(completed_event_ids, "completed_event_ids"))
    events = plan.event_map()
    unknown = completed - events.keys()
    if unknown:
        raise ValueError(f"unknown completed events: {sorted(unknown)!r}")
    return tuple(
        event.event_id
        for event in plan.events
        if event.event_id not in completed and set(event.prerequisites) <= completed
    )


def _phase_distance(left: tuple[float, ...] | None, right: tuple[float, ...] | None) -> float:
    if left is None or right is None:
        return 1.0
    rms = math.sqrt(
        sum((((a - b + math.pi) % TAU) - math.pi) ** 2 for a, b in zip(left, right)) / DIM
    )
    return min(1.0, rms / math.pi)


def _coordination_adjacency(plan: OrchorbitalPlan) -> dict[str, set[str]]:
    orbit_map = plan.orbit_map()
    adjacency: dict[str, set[str]] = {orbit_id: set() for orbit_id in orbit_map}
    for orbit in orbit_map.values():
        if orbit.parent_id is not None:
            adjacency[orbit.orbit_id].add(orbit.parent_id)
            adjacency[orbit.parent_id].add(orbit.orbit_id)
    for left, right in plan.coordination_edges:
        adjacency[left].add(right)
        adjacency[right].add(left)
    return adjacency


def _distances(plan: OrchorbitalPlan, source: str) -> dict[str, int]:
    adjacency = _coordination_adjacency(plan)
    out = {source: 0}
    queue: deque[str] = deque([source])
    while queue:
        current = queue.popleft()
        for neighbor in sorted(adjacency[current]):
            if neighbor not in out:
                out[neighbor] = out[current] + 1
                queue.append(neighbor)
    return out


def work_steal_order(
    plan: OrchorbitalPlan,
    worker_orbit_id: str,
    pending_orbit_ids: Iterable[str],
) -> tuple[str, ...]:
    """Return deterministic locality-first work-stealing preference.

    The hierarchy edges and explicit coordination/Lagrange edges form the
    locality graph. Graph distance is primary; T^36 distance is a secondary
    tie-break only when both orbits carry explicit phase coordinates.
    """

    if not isinstance(plan, OrchorbitalPlan):
        raise ValueError("plan must be an OrchorbitalPlan")
    orbit_map = plan.orbit_map()
    source = _strict_text(worker_orbit_id, "worker_orbit_id")
    if source not in orbit_map:
        raise ValueError("worker_orbit_id is outside the plan")
    pending = _strict_ids(pending_orbit_ids, "pending_orbit_ids")
    unknown = set(pending) - orbit_map.keys()
    if unknown:
        raise ValueError(f"unknown pending orbits: {sorted(unknown)!r}")
    distances = _distances(plan, source)
    return tuple(
        sorted(
            pending,
            key=lambda orbit_id: (
                distances[orbit_id],
                _phase_distance(orbit_map[source].phase36, orbit_map[orbit_id].phase36),
                orbit_id,
            ),
        )
    )


def plan_receipt(plan: OrchorbitalPlan) -> dict[str, object]:
    if not isinstance(plan, OrchorbitalPlan):
        raise ValueError("plan must be an OrchorbitalPlan")
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "root_id": plan.root_id,
        "orbit_count": len(plan.orbits),
        "event_count": len(plan.events),
        "critical_path_depth": plan.critical_path_depth,
        "max_parallel_width": plan.max_parallel_width,
        "max_local_join_fan_in": plan.max_local_join_fan_in,
        "root_join_fan_in": plan.global_join_fan_in,
        "coordination_edge_count": len(plan.coordination_edges),
        "topology": "RECURSIVE_FORK_LOCAL_JOIN",
        "global_specialist_barrier": False,
        "authority": AUTHORITY,
        "epistemic": EPISTEMIC,
        "canon_allowed": False,
        "execution_admitted": False,
        "memory_mutation_allowed": False,
        "physical_orbital_claim": False,
        "speedup_claim": False,
    }


__all__ = [
    "AUTHORITY",
    "DIM",
    "EPISTEMIC",
    "KNOWN_SPECIES",
    "OrbitEvent",
    "OrbitSpec",
    "OrchorbitalPlan",
    "SCHEMA",
    "TAU",
    "VERSION",
    "compile_orchorbital_plan",
    "plan_receipt",
    "ready_events",
    "work_steal_order",
]
