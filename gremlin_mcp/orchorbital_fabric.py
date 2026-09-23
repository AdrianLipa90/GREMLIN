from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, replace
import math
from threading import RLock
from typing import Any

from gremlin_mcp.role_registry import BESTIARY_ROLE_NAMES

SCHEMA = "GREMLIN_ORCHORBITAL_FABRIC_V0_2"
VERSION = "0.2.0"
TAU = 2.0 * math.pi
DIM = 36
OPEN = "OPEN"
TERMINAL_STATES = frozenset({"CLOSED", "FAILED", "QUARANTINED"})
MAX_IDENTIFIER_CHARS = 128


def _strict_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    out = value.strip()
    if not out or len(out) > MAX_IDENTIFIER_CHARS:
        raise ValueError(f"{field} must contain 1..{MAX_IDENTIFIER_CHARS} characters")
    return out


def _strict_species(value: Any) -> str:
    species = _strict_text(value, "species").upper()
    if species not in BESTIARY_ROLE_NAMES:
        raise ValueError(f"unsupported species: {species}")
    return species


def _strict_ids(values: Iterable[str], field: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, Mapping)) or not isinstance(values, Iterable):
        raise ValueError(f"{field} must be an iterable")
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


def _has_cycle(graph: Mapping[str, set[str]]) -> bool:
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in done:
            return False
        if node_id in visiting:
            return True
        visiting.add(node_id)
        for dependency in graph.get(node_id, set()):
            if visit(dependency):
                return True
        visiting.remove(node_id)
        done.add(node_id)
        return False

    return any(visit(node_id) for node_id in graph)


@dataclass(frozen=True)
class NodeInstance:
    """Runtime node identity.

    caller_id is immutable invocation provenance.
    center_id is mutable non-causal orbital locality.
    authority_root_id is stable for the lifetime of the fabric.
    """

    node_id: str
    species: str
    authority_root_id: str
    caller_id: str | None
    center_id: str | None
    obligations: tuple[str, ...]
    phase36: tuple[float, ...] | None
    status: str
    spawned_seq: int


@dataclass(frozen=True)
class SpawnRequest:
    species: str
    obligations: tuple[str, ...] = ()
    center_id: str | None = None
    causal_dependencies: tuple[str, ...] = ()
    join_to_caller: bool = True
    phase36: tuple[float, ...] | None = None
    node_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "species", _strict_species(self.species))
        object.__setattr__(
            self,
            "obligations",
            _strict_ids(self.obligations, "obligations"),
        )
        if self.center_id is not None:
            object.__setattr__(
                self,
                "center_id",
                _strict_text(self.center_id, "center_id"),
            )
        object.__setattr__(
            self,
            "causal_dependencies",
            _strict_ids(self.causal_dependencies, "causal_dependencies"),
        )
        if not isinstance(self.join_to_caller, bool):
            raise ValueError("join_to_caller must be boolean")
        object.__setattr__(self, "phase36", _strict_phase36(self.phase36))
        if self.node_id is not None:
            object.__setattr__(
                self,
                "node_id",
                _strict_text(self.node_id, "node_id"),
            )


class OrchorbitalFabric:
    """Dynamic execution topology with stable authority and mutable locality.

    Relations are intentionally separate:
      caller      - immutable invocation provenance;
      center      - mutable non-causal orbital locality;
      causal      - execution prerequisite DAG;
      join        - local reduction/return dependency DAG;
      coordination- non-causal peer locality.

    Center edges may contain cycles. Causal and join edges may not.
    """

    def __init__(
        self,
        *,
        root_species: str = "GREMLIN",
        root_id: str = "AUTH:ROOT",
    ) -> None:
        rid = _strict_text(root_id, "root_id")
        species = _strict_species(root_species)
        self._lock = RLock()
        self._seq = 0
        self._node_counter = 0
        self._nodes: dict[str, NodeInstance] = {}
        self._causal: dict[str, set[str]] = {}
        self._joins: dict[str, set[str]] = {}
        self._coordination: set[tuple[str, str]] = set()
        self._events: list[dict[str, Any]] = []

        root = NodeInstance(
            node_id=rid,
            species=species,
            authority_root_id=rid,
            caller_id=None,
            center_id=None,
            obligations=(),
            phase36=None,
            status=OPEN,
            spawned_seq=0,
        )
        self._nodes[rid] = root
        self._causal[rid] = set()
        self._joins[rid] = set()
        self._authority_root_id = rid
        self._barycenter_id = rid
        self._record("FABRIC_INIT", rid, root_species=species)

    @property
    def authority_root_id(self) -> str:
        return self._authority_root_id

    @property
    def computational_barycenter_id(self) -> str:
        return self._barycenter_id

    def _record(self, kind: str, node_id: str, **details: Any) -> None:
        self._seq += 1
        self._events.append(
            {
                "seq": self._seq,
                "kind": _strict_text(kind, "event kind"),
                "node_id": _strict_text(node_id, "event node_id"),
                "details": deepcopy(details),
            }
        )

    def _require(self, node_id: str) -> NodeInstance:
        nid = _strict_text(node_id, "node_id")
        node = self._nodes.get(nid)
        if node is None:
            raise ValueError(f"unknown node_id: {nid}")
        return node

    def _require_open(self, node_id: str) -> NodeInstance:
        node = self._require(node_id)
        if node.status != OPEN:
            raise RuntimeError(f"node is not open: {node.node_id}")
        return node

    def _new_node_id(self, species: str) -> str:
        self._node_counter += 1
        return f"N{self._node_counter:06d}:{species}"

    def _assert_invariants(self) -> None:
        if set(self._nodes) != set(self._causal) or set(self._nodes) != set(self._joins):
            raise RuntimeError("node/edge registry drift detected")

        root = self._nodes.get(self._authority_root_id)
        if root is None:
            raise RuntimeError("authority root is missing")
        if root.caller_id is not None or root.center_id is not None:
            raise RuntimeError("authority root boundary invariant violated")

        for node_id, node in self._nodes.items():
            if node.authority_root_id != self._authority_root_id:
                raise RuntimeError("authority root drift detected")
            if node.status != OPEN and node.status not in TERMINAL_STATES:
                raise RuntimeError("unknown node lifecycle state")
            if node.caller_id is not None:
                if node.caller_id not in self._nodes:
                    raise RuntimeError("caller edge points outside fabric")
                if node.caller_id == node_id:
                    raise RuntimeError("self caller edge is invalid")
            if node.center_id is not None:
                if node.center_id not in self._nodes:
                    raise RuntimeError("center edge points outside fabric")
                if node.center_id == node_id:
                    raise RuntimeError("self center edge is invalid")
            if node_id in self._causal[node_id]:
                raise RuntimeError("self causal dependency")
            if node_id in self._joins[node_id]:
                raise RuntimeError("self join dependency")
            if not self._causal[node_id] <= self._nodes.keys():
                raise RuntimeError("causal edge points outside fabric")
            if not self._joins[node_id] <= self._nodes.keys():
                raise RuntimeError("join edge points outside fabric")

        if _has_cycle(self._causal):
            raise RuntimeError("causal graph contains a cycle")
        if _has_cycle(self._joins):
            raise RuntimeError("join graph contains a cycle")

        for edge in self._coordination:
            if len(edge) != 2 or not set(edge) <= self._nodes.keys():
                raise RuntimeError("coordination edge invariant violated")

        if self._barycenter_id not in self._nodes:
            raise RuntimeError("computational barycenter is missing")

    def node(self, node_id: str) -> NodeInstance:
        with self._lock:
            return self._require(node_id)

    def nodes(self) -> tuple[NodeInstance, ...]:
        with self._lock:
            return tuple(self._nodes[node_id] for node_id in sorted(self._nodes))

    def events(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(deepcopy(self._events))

    def spawn(
        self,
        caller_id: str,
        species: str,
        *,
        obligations: Iterable[str] = (),
        center_id: str | None = None,
        causal_dependencies: Iterable[str] = (),
        join_to_caller: bool = True,
        phase36: Sequence[float] | None = None,
        node_id: str | None = None,
    ) -> NodeInstance:
        request = SpawnRequest(
            species=species,
            obligations=tuple(obligations),
            center_id=center_id,
            causal_dependencies=tuple(causal_dependencies),
            join_to_caller=join_to_caller,
            phase36=None if phase36 is None else tuple(phase36),
            node_id=node_id,
        )
        return self.spawn_batch(caller_id, (request,))[0]

    def spawn_batch(
        self,
        caller_id: str,
        requests: Iterable[SpawnRequest],
    ) -> tuple[NodeInstance, ...]:
        """Atomically create one local invocation fanout.

        A failed request rolls the full batch back, including event sequence and
        generated identifiers.
        """

        if isinstance(requests, (str, bytes, Mapping)) or not isinstance(requests, Iterable):
            raise ValueError("requests must be an iterable")
        rows = tuple(requests)
        if not rows or not all(isinstance(row, SpawnRequest) for row in rows):
            raise ValueError("requests must contain SpawnRequest values")

        with self._lock:
            caller = self._require_open(caller_id)
            explicit_ids = [row.node_id for row in rows if row.node_id is not None]
            if len(explicit_ids) != len(set(explicit_ids)):
                raise ValueError("duplicate explicit node_id in batch")
            if set(explicit_ids) & self._nodes.keys():
                raise ValueError("node_id already exists")

            for row in rows:
                center = row.center_id or caller.node_id
                self._require_open(center)
                for dependency in row.causal_dependencies:
                    self._require(dependency)

            checkpoint = (
                dict(self._nodes),
                {key: set(value) for key, value in self._causal.items()},
                {key: set(value) for key, value in self._joins.items()},
                set(self._coordination),
                deepcopy(self._events),
                self._seq,
                self._node_counter,
                self._barycenter_id,
            )
            created: list[NodeInstance] = []
            try:
                for row in rows:
                    node_id = row.node_id or self._new_node_id(row.species)
                    if node_id in self._nodes:
                        raise ValueError("node_id already exists")
                    center = row.center_id or caller.node_id
                    node = NodeInstance(
                        node_id=node_id,
                        species=row.species,
                        authority_root_id=self._authority_root_id,
                        caller_id=caller.node_id,
                        center_id=center,
                        obligations=row.obligations,
                        phase36=row.phase36,
                        status=OPEN,
                        spawned_seq=self._seq + 1,
                    )
                    self._nodes[node_id] = node
                    self._causal[node_id] = set(row.causal_dependencies)
                    self._joins[node_id] = set()
                    if row.join_to_caller:
                        self._joins[caller.node_id].add(node_id)
                    self._record(
                        "NODE_SPAWN",
                        node_id,
                        caller_id=caller.node_id,
                        center_id=center,
                        join_to_caller=row.join_to_caller,
                        species=row.species,
                    )
                    created.append(node)

                self._assert_invariants()
                self._record(
                    "SPAWN_BATCH_COMMIT",
                    caller.node_id,
                    count=len(created),
                    node_ids=[node.node_id for node in created],
                )
                return tuple(created)
            except Exception:
                (
                    self._nodes,
                    self._causal,
                    self._joins,
                    self._coordination,
                    self._events,
                    self._seq,
                    self._node_counter,
                    self._barycenter_id,
                ) = checkpoint
                raise

    def add_causal_dependency(self, node_id: str, dependency_id: str) -> None:
        with self._lock:
            self._require_open(node_id)
            self._require(dependency_id)
            if node_id == dependency_id:
                raise ValueError("self causal dependency")
            old = set(self._causal[node_id])
            self._causal[node_id].add(dependency_id)
            if _has_cycle(self._causal):
                self._causal[node_id] = old
                raise ValueError("causal dependency would create a cycle")
            self._record(
                "CAUSAL_EDGE_ADD",
                node_id,
                dependency_id=dependency_id,
            )
            self._assert_invariants()

    def add_join_dependency(self, consumer_id: str, child_id: str) -> None:
        with self._lock:
            self._require_open(consumer_id)
            self._require(child_id)
            if consumer_id == child_id:
                raise ValueError("self join dependency")
            old = set(self._joins[consumer_id])
            self._joins[consumer_id].add(child_id)
            if _has_cycle(self._joins):
                self._joins[consumer_id] = old
                raise ValueError("join dependency would create a cycle")
            self._record(
                "JOIN_EDGE_ADD",
                consumer_id,
                child_id=child_id,
            )
            self._assert_invariants()

    def add_coordination_edge(self, left_id: str, right_id: str) -> None:
        with self._lock:
            self._require(left_id)
            self._require(right_id)
            if left_id == right_id:
                raise ValueError("coordination self-loop is not allowed")
            edge = tuple(sorted((left_id, right_id)))
            self._coordination.add(edge)
            self._record(
                "COORDINATION_EDGE_ADD",
                left_id,
                peer_id=right_id,
            )
            self._assert_invariants()

    def recenter(
        self,
        node_id: str,
        new_center_id: str,
        *,
        reason: str = "runtime_locality",
    ) -> NodeInstance:
        """Move local orbital attachment without changing provenance or authority.

        Center cycles are deliberately allowed. A<->B is legal here because
        center edges do not gate execution.
        """

        with self._lock:
            node = self._require_open(node_id)
            center = self._require_open(new_center_id)
            if node.node_id == self._authority_root_id:
                raise ValueError("authority root does not receive a local orbital center")
            if node.node_id == center.node_id:
                raise ValueError("node cannot orbit itself")
            old_center = node.center_id
            self._nodes[node.node_id] = replace(node, center_id=center.node_id)
            self._record(
                "NODE_RECENTER",
                node.node_id,
                old_center_id=old_center,
                new_center_id=center.node_id,
                reason=_strict_text(reason, "reason"),
            )
            self._assert_invariants()
            return self._nodes[node.node_id]

    def move_barycenter(
        self,
        node_id: str,
        *,
        reason: str = "runtime_activity",
    ) -> str:
        """Move computational focus without changing the authority root."""

        with self._lock:
            node = self._require_open(node_id)
            old_barycenter = self._barycenter_id
            self._barycenter_id = node.node_id
            self._record(
                "BARYCENTER_MOVE",
                node.node_id,
                old_barycenter_id=old_barycenter,
                reason=_strict_text(reason, "reason"),
            )
            self._assert_invariants()
            return node.node_id

    def ready_nodes(self) -> tuple[str, ...]:
        """Open nodes whose explicit causal prerequisites are CLOSED."""

        with self._lock:
            return tuple(
                sorted(
                    node_id
                    for node_id, node in self._nodes.items()
                    if node.status == OPEN
                    and all(
                        self._nodes[dependency].status == "CLOSED"
                        for dependency in self._causal[node_id]
                    )
                )
            )

    def closable_nodes(self) -> tuple[str, ...]:
        """Ready nodes whose local join dependencies are also CLOSED."""

        with self._lock:
            ready = set(self.ready_nodes())
            return tuple(
                sorted(
                    node_id
                    for node_id in ready
                    if all(
                        self._nodes[child].status == "CLOSED"
                        for child in self._joins[node_id]
                    )
                )
            )

    def close(self, node_id: str) -> NodeInstance:
        with self._lock:
            node = self._require_open(node_id)
            unresolved_causal = sorted(
                dependency
                for dependency in self._causal[node.node_id]
                if self._nodes[dependency].status != "CLOSED"
            )
            if unresolved_causal:
                raise RuntimeError(
                    f"causal dependencies are not closed: {unresolved_causal!r}"
                )
            unresolved_join = sorted(
                child
                for child in self._joins[node.node_id]
                if self._nodes[child].status != "CLOSED"
            )
            if unresolved_join:
                raise RuntimeError(
                    f"join dependencies are not closed: {unresolved_join!r}"
                )
            if (
                node.node_id == self._barycenter_id
                and node.node_id != self._authority_root_id
            ):
                raise RuntimeError(
                    "move computational barycenter before closing its node"
                )
            if node.node_id == self._authority_root_id:
                open_others = [
                    other_id
                    for other_id, other in self._nodes.items()
                    if other_id != node.node_id and other.status == OPEN
                ]
                if open_others:
                    raise RuntimeError(
                        "authority root cannot close while other nodes are open"
                    )

            self._nodes[node.node_id] = replace(node, status="CLOSED")
            self._record("NODE_CLOSE", node.node_id)
            self._assert_invariants()
            return self._nodes[node.node_id]

    def receipt(self) -> dict[str, object]:
        with self._lock:
            self._assert_invariants()
            return {
                "schema": SCHEMA,
                "version": VERSION,
                "authority_root_id": self._authority_root_id,
                "computational_barycenter_id": self._barycenter_id,
                "node_count": len(self._nodes),
                "open_node_count": sum(
                    node.status == OPEN for node in self._nodes.values()
                ),
                "causal_edge_count": sum(
                    len(value) for value in self._causal.values()
                ),
                "join_edge_count": sum(
                    len(value) for value in self._joins.values()
                ),
                "coordination_edge_count": len(self._coordination),
                "caller_is_provenance_not_center": True,
                "center_cycles_allowed": True,
                "causal_cycles_allowed": False,
                "join_cycles_allowed": False,
                "authority_root_stable": True,
                "species_position_fixed": False,
                "canon_allowed": False,
                "execution_admitted": False,
                "memory_mutation_allowed": False,
                "speedup_claim": False,
            }


__all__ = [
    "DIM",
    "NodeInstance",
    "OPEN",
    "OrchorbitalFabric",
    "SCHEMA",
    "SpawnRequest",
    "TAU",
    "TERMINAL_STATES",
    "VERSION",
]
