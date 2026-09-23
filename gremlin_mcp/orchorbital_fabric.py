from __future__ import annotations

from collections import deque
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
DEFAULT_MAX_NODES = 10_000


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


def _phase_distance(
    left: tuple[float, ...] | None,
    right: tuple[float, ...] | None,
) -> float:
    if left is None or right is None:
        return 1.0
    rms = math.sqrt(
        sum(
            ((((a - b + math.pi) % TAU) - math.pi) ** 2)
            for a, b in zip(left, right)
        )
        / DIM
    )
    return min(1.0, rms / math.pi)


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
    execution_started: bool
    self_complete: bool
    result_commitment: str | None
    spawned_seq: int
    invocation_depth: int


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


@dataclass(frozen=True)
class CoordinationPoint:
    """Non-causal n-node rendezvous used only for execution locality."""

    point_id: str
    member_ids: tuple[str, ...]
    weight: float
    created_seq: int
    physical_claim: bool = False


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
        max_nodes: int = DEFAULT_MAX_NODES,
    ) -> None:
        rid = _strict_text(root_id, "root_id")
        species = _strict_species(root_species)
        if isinstance(max_nodes, bool) or not isinstance(max_nodes, int) or max_nodes < 1:
            raise ValueError("max_nodes must be a positive integer")
        self._max_nodes = max_nodes
        self._lock = RLock()
        self._seq = 0
        self._node_counter = 0
        self._nodes: dict[str, NodeInstance] = {}
        self._causal: dict[str, set[str]] = {}
        self._joins: dict[str, set[str]] = {}
        self._coordination: set[tuple[str, str]] = set()
        self._coordination_points: dict[str, CoordinationPoint] = {}
        self._replacements: dict[str, str] = {}
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
            execution_started=False,
            self_complete=False,
            result_commitment=None,
            spawned_seq=0,
            invocation_depth=0,
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

    def _blocking_graph(self) -> dict[str, set[str]]:
        """Union of every relation that can block successful subtree closure."""

        graph = {
            node_id: set(self._causal[node_id]) | set(self._joins[node_id])
            for node_id in self._nodes
        }
        for source_id, replacement_id in self._replacements.items():
            graph[source_id].add(replacement_id)
        return graph

    def _closure_satisfied(
        self,
        node_id: str,
        *,
        path: frozenset[str] = frozenset(),
    ) -> bool:
        """True only when a node resolves to successful CLOSED work.

        FAILED/QUARANTINED nodes never satisfy a dependency by themselves.
        They may resolve through one explicit replacement, and their historical
        local join children must also resolve successfully.
        """

        if node_id in path:
            raise RuntimeError("closure resolution contains a cycle")
        node = self._nodes[node_id]
        if node.status == "CLOSED":
            return True
        if node.status == OPEN:
            return False
        if node.status not in {"FAILED", "QUARANTINED"}:
            return False

        replacement_id = self._replacements.get(node_id)
        if replacement_id is None:
            return False
        next_path = path | {node_id}
        if not self._closure_satisfied(replacement_id, path=next_path):
            return False
        return all(
            self._closure_satisfied(child_id, path=next_path)
            for child_id in self._joins[node_id]
        )

    def _assert_invariants(self) -> None:
        if set(self._nodes) != set(self._causal) or set(self._nodes) != set(self._joins):
            raise RuntimeError("node/edge registry drift detected")

        root = self._nodes.get(self._authority_root_id)
        if root is None:
            raise RuntimeError("authority root is missing")
        if root.caller_id is not None or root.center_id is not None:
            raise RuntimeError("authority root boundary invariant violated")

        caller_graph: dict[str, set[str]] = {}
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
            if node_id == self._authority_root_id:
                caller_graph[node_id] = set()
            else:
                if node.caller_id is None:
                    raise RuntimeError("non-root node is missing caller provenance")
                caller_graph[node_id] = {node.caller_id}

        if _has_cycle(caller_graph):
            raise RuntimeError("caller provenance graph contains a cycle")
        for node_id in self._nodes:
            current = node_id
            seen: set[str] = set()
            while current != self._authority_root_id:
                if current in seen:
                    raise RuntimeError("caller provenance graph contains a cycle")
                seen.add(current)
                caller = self._nodes[current].caller_id
                if caller is None:
                    raise RuntimeError("caller provenance does not reach authority root")
                current = caller

        if _has_cycle(self._causal):
            raise RuntimeError("causal graph contains a cycle")
        if _has_cycle(self._joins):
            raise RuntimeError("join graph contains a cycle")

        replacement_targets: set[str] = set()
        for source_id, replacement_id in self._replacements.items():
            if source_id not in self._nodes or replacement_id not in self._nodes:
                raise RuntimeError("replacement edge points outside fabric")
            source = self._nodes[source_id]
            if source_id == self._authority_root_id:
                raise RuntimeError("authority root cannot be replaced")
            if source.status not in {"FAILED", "QUARANTINED"}:
                raise RuntimeError("only failed or quarantined nodes may be replaced")
            if source_id == replacement_id:
                raise RuntimeError("node cannot replace itself")
            if replacement_id in replacement_targets:
                raise RuntimeError("replacement target must be unique")
            replacement_targets.add(replacement_id)
            replacement = self._nodes[replacement_id]
            if not set(source.obligations) <= set(replacement.obligations):
                raise RuntimeError("replacement does not cover source obligations")

        if _has_cycle(self._blocking_graph()):
            raise RuntimeError("blocking graph contains a cross-relation cycle")

        for edge in self._coordination:
            if len(edge) != 2 or not set(edge) <= self._nodes.keys():
                raise RuntimeError("coordination edge invariant violated")

        for point_id, point in self._coordination_points.items():
            if point.point_id != point_id:
                raise RuntimeError("coordination point registry drift detected")
            if len(point.member_ids) < 2 or len(set(point.member_ids)) != len(point.member_ids):
                raise RuntimeError("coordination point membership invariant violated")
            if not set(point.member_ids) <= self._nodes.keys():
                raise RuntimeError("coordination point points outside fabric")
            if not math.isfinite(point.weight) or point.weight <= 0.0:
                raise RuntimeError("coordination point weight invariant violated")
            if point.physical_claim:
                raise RuntimeError("coordination point cannot assert a physical claim")

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
            if caller.self_complete:
                raise RuntimeError("self-complete node cannot spawn new work")
            if len(self._nodes) + len(rows) > self._max_nodes:
                raise RuntimeError("orchorbital node budget exceeded")

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
                        execution_started=False,
                        self_complete=False,
                        result_commitment=None,
                        spawned_seq=self._seq + 1,
                        invocation_depth=caller.invocation_depth + 1,
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
            node = self._require_open(node_id)
            self._require(dependency_id)
            if node.execution_started:
                raise RuntimeError("causal dependencies are sealed after execution starts")
            if node_id == dependency_id:
                raise ValueError("self causal dependency")
            old = set(self._causal[node_id])
            self._causal[node_id].add(dependency_id)
            if _has_cycle(self._causal):
                self._causal[node_id] = old
                raise ValueError("causal dependency would create a cycle")
            if _has_cycle(self._blocking_graph()):
                self._causal[node_id] = old
                raise ValueError("blocking dependency would create a cross-relation cycle")
            self._record(
                "CAUSAL_EDGE_ADD",
                node_id,
                dependency_id=dependency_id,
            )
            self._assert_invariants()

    def add_join_dependency(self, consumer_id: str, child_id: str) -> None:
        with self._lock:
            consumer = self._require_open(consumer_id)
            self._require(child_id)
            if consumer.self_complete:
                raise RuntimeError("join dependencies are sealed after self completion")
            if consumer_id == child_id:
                raise ValueError("self join dependency")
            old = set(self._joins[consumer_id])
            self._joins[consumer_id].add(child_id)
            if _has_cycle(self._joins):
                self._joins[consumer_id] = old
                raise ValueError("join dependency would create a cycle")
            if _has_cycle(self._blocking_graph()):
                self._joins[consumer_id] = old
                raise ValueError("blocking dependency would create a cross-relation cycle")
            self._record(
                "JOIN_EDGE_ADD",
                consumer_id,
                child_id=child_id,
            )
            self._assert_invariants()

    def add_coordination_edge(self, left_id: str, right_id: str) -> None:
        with self._lock:
            self._require_open(left_id)
            self._require_open(right_id)
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

    def create_coordination_point(
        self,
        member_ids: Iterable[str],
        *,
        point_id: str | None = None,
        weight: float = 1.0,
    ) -> CoordinationPoint:
        """Create a non-causal n-node rendezvous / Lagrange-style software point."""

        if isinstance(member_ids, (str, bytes, Mapping)) or not isinstance(
            member_ids, Iterable
        ):
            raise ValueError("member_ids must be an iterable")
        raw_members = tuple(member_ids)
        members = tuple(
            _strict_text(value, f"member_ids[{index}]")
            for index, value in enumerate(raw_members)
        )
        if len(members) < 2:
            raise ValueError("coordination point requires at least two members")
        if len(set(members)) != len(members):
            raise ValueError("coordination point members must be unique")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise ValueError("coordination point weight must be numeric")
        normalized_weight = float(weight)
        if not math.isfinite(normalized_weight) or normalized_weight <= 0.0:
            raise ValueError("coordination point weight must be finite and positive")

        with self._lock:
            for member_id in members:
                self._require_open(member_id)
            if point_id is None:
                pid = f"LAGRANGE:{len(self._coordination_points) + 1:06d}"
            else:
                pid = _strict_text(point_id, "point_id")
            if pid in self._coordination_points:
                raise ValueError("coordination point_id already exists")
            point = CoordinationPoint(
                point_id=pid,
                member_ids=members,
                weight=normalized_weight,
                created_seq=self._seq + 1,
                physical_claim=False,
            )
            self._coordination_points[pid] = point
            self._record(
                "COORDINATION_POINT_CREATE",
                self._authority_root_id,
                point_id=pid,
                member_ids=list(members),
                weight=normalized_weight,
                physical_claim=False,
            )
            self._assert_invariants()
            return point

    def coordination_points(self) -> tuple[CoordinationPoint, ...]:
        with self._lock:
            return tuple(
                self._coordination_points[point_id]
                for point_id in sorted(self._coordination_points)
            )

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

    def _locality_adjacency(self) -> dict[str, set[str]]:
        open_ids = {
            node_id
            for node_id, node in self._nodes.items()
            if node.status == OPEN
        }
        adjacency: dict[str, set[str]] = {
            node_id: set() for node_id in open_ids
        }

        for node_id in sorted(open_ids):
            node = self._nodes[node_id]
            for peer in (node.caller_id, node.center_id):
                if peer is not None and peer in open_ids and peer != node_id:
                    adjacency[node_id].add(peer)
                    adjacency[peer].add(node_id)

        for left, right in self._coordination:
            if left in open_ids and right in open_ids:
                adjacency[left].add(right)
                adjacency[right].add(left)

        for point in self._coordination_points.values():
            members = [
                member_id
                for member_id in point.member_ids
                if member_id in open_ids
            ]
            for index, left in enumerate(members):
                for right in members[index + 1 :]:
                    adjacency[left].add(right)
                    adjacency[right].add(left)

        return adjacency

    def locality_distance(self, source_id: str, target_id: str) -> float:
        """Shortest open-node locality distance across caller/center/coordination links."""

        with self._lock:
            source = self._require_open(source_id).node_id
            target = self._require_open(target_id).node_id
            if source == target:
                return 0.0
            adjacency = self._locality_adjacency()
            distance = {source: 0}
            queue: deque[str] = deque([source])
            while queue:
                current = queue.popleft()
                for neighbor in sorted(adjacency[current]):
                    if neighbor in distance:
                        continue
                    distance[neighbor] = distance[current] + 1
                    if neighbor == target:
                        return float(distance[neighbor])
                    queue.append(neighbor)
            return math.inf

    def rank_centers(
        self,
        caller_id: str,
        candidate_ids: Iterable[str],
        *,
        phase36: Sequence[float] | None = None,
    ) -> tuple[str, ...]:
        """Rank open candidate centers by graph locality then T^36 distance."""

        if isinstance(candidate_ids, (str, bytes, Mapping)) or not isinstance(
            candidate_ids, Iterable
        ):
            raise ValueError("candidate_ids must be an iterable")
        candidates = _strict_ids(candidate_ids, "candidate_ids")
        if not candidates:
            raise ValueError("candidate_ids must be non-empty")
        target_phase = _strict_phase36(phase36)

        with self._lock:
            caller = self._require_open(caller_id)
            for candidate_id in candidates:
                self._require_open(candidate_id)
            return tuple(
                sorted(
                    candidates,
                    key=lambda candidate_id: (
                        self.locality_distance(caller.node_id, candidate_id),
                        _phase_distance(
                            target_phase,
                            self._nodes[candidate_id].phase36,
                        ),
                        0 if candidate_id == self._barycenter_id else 1,
                        candidate_id,
                    ),
                )
            )

    def ready_nodes(self) -> tuple[str, ...]:
        """Open nodes whose explicit causal prerequisites are CLOSED."""

        with self._lock:
            return tuple(
                sorted(
                    node_id
                    for node_id, node in self._nodes.items()
                    if node.status == OPEN
                    and not node.execution_started
                    and not node.self_complete
                    and all(
                        self._closure_satisfied(dependency)
                        for dependency in self._causal[node_id]
                    )
                )
            )

    def running_nodes(self) -> tuple[str, ...]:
        """Open nodes with local execution started but no local result yet."""

        with self._lock:
            return tuple(
                sorted(
                    node_id
                    for node_id, node in self._nodes.items()
                    if node.status == OPEN
                    and node.execution_started
                    and not node.self_complete
                )
            )

    def mark_started(self, node_id: str) -> NodeInstance:
        """Seal causal prerequisites and mark local execution as started."""

        with self._lock:
            node = self._require_open(node_id)
            unresolved_causal = sorted(
                dependency
                for dependency in self._causal[node.node_id]
                if not self._closure_satisfied(dependency)
            )
            if unresolved_causal:
                raise RuntimeError(
                    f"causal dependencies are not closed: {unresolved_causal!r}"
                )
            if node.self_complete:
                raise RuntimeError("node local work is already complete")
            if node.execution_started:
                return node
            self._nodes[node.node_id] = replace(node, execution_started=True)
            self._record("NODE_EXECUTION_START", node.node_id)
            self._assert_invariants()
            return self._nodes[node.node_id]

    def closable_nodes(self) -> tuple[str, ...]:
        """Ready nodes whose local join dependencies are also CLOSED."""

        with self._lock:
            return tuple(
                sorted(
                    node_id
                    for node_id, node in self._nodes.items()
                    if node.status == OPEN
                    and node.self_complete
                    and all(
                        self._closure_satisfied(dependency)
                        for dependency in self._causal[node_id]
                    )
                    and all(
                        self._closure_satisfied(child)
                        for child in self._joins[node_id]
                    )
                )
            )

    def mark_self_complete(
        self,
        node_id: str,
        *,
        result_commitment: str | None = None,
    ) -> NodeInstance:
        """Record completion of local work without closing the local subtree."""

        with self._lock:
            node = self._require_open(node_id)
            if not node.execution_started:
                raise RuntimeError("node local execution has not started")
            unresolved_causal = sorted(
                dependency
                for dependency in self._causal[node.node_id]
                if not self._closure_satisfied(dependency)
            )
            if unresolved_causal:
                raise RuntimeError(
                    f"causal dependencies are not closed: {unresolved_causal!r}"
                )
            commitment = (
                None
                if result_commitment is None
                else _strict_text(result_commitment, "result_commitment")
            )
            if node.self_complete:
                if commitment == node.result_commitment:
                    return node
                raise RuntimeError("node local work is already complete")
            self._nodes[node.node_id] = replace(
                node,
                self_complete=True,
                result_commitment=commitment,
            )
            self._record(
                "NODE_SELF_COMPLETE",
                node.node_id,
                result_commitment=commitment,
            )
            self._assert_invariants()
            return self._nodes[node.node_id]

    def _terminalize_unsuccessful(
        self,
        node_id: str,
        *,
        status: str,
        reason: str,
    ) -> NodeInstance:
        if status not in {"FAILED", "QUARANTINED"}:
            raise ValueError("unsuccessful terminal status must be FAILED or QUARANTINED")
        why = _strict_text(reason, "reason")

        with self._lock:
            node = self._require_open(node_id)
            if node.node_id == self._authority_root_id:
                raise RuntimeError("authority root failure requires external governance")

            fallback_id = node.caller_id or self._authority_root_id
            fallback = self._require_open(fallback_id)

            # A crash/quarantine cannot require cooperation from the failed node.
            # Re-home every live satellite explicitly and audibly.
            satellites = sorted(
                other_id
                for other_id, other in self._nodes.items()
                if other.status == OPEN and other.center_id == node.node_id
            )
            for satellite_id in satellites:
                satellite = self._nodes[satellite_id]
                target_id = fallback.node_id
                if target_id == satellite_id:
                    target_id = self._authority_root_id
                target = self._require_open(target_id)
                self._nodes[satellite_id] = replace(
                    satellite,
                    center_id=target.node_id,
                )
                self._record(
                    "NODE_RECENTER_FAILOVER",
                    satellite_id,
                    failed_center_id=node.node_id,
                    new_center_id=target.node_id,
                    reason=why,
                )

            self._nodes[node.node_id] = replace(node, status=status)
            self._record(
                f"NODE_{status}",
                node.node_id,
                reason=why,
            )

            if self._barycenter_id == node.node_id:
                old_barycenter = self._barycenter_id
                self._barycenter_id = fallback.node_id
                self._record(
                    "BARYCENTER_FAILOVER",
                    fallback.node_id,
                    old_barycenter_id=old_barycenter,
                    reason=why,
                )

            self._assert_invariants()
            return self._nodes[node.node_id]

    def fail(self, node_id: str, *, reason: str) -> NodeInstance:
        """Terminal fail-closed state; never counts as successful closure."""

        return self._terminalize_unsuccessful(
            node_id,
            status="FAILED",
            reason=reason,
        )

    def quarantine(self, node_id: str, *, reason: str) -> NodeInstance:
        """Terminal quarantine; never counts as successful closure."""

        return self._terminalize_unsuccessful(
            node_id,
            status="QUARANTINED",
            reason=reason,
        )

    def bind_replacement(
        self,
        source_id: str,
        replacement_id: str,
    ) -> None:
        """Append an explicit recovery edge for FAILED/QUARANTINED work.

        Existing causal/join edges are not rewritten. Any consumer waiting on
        source_id resolves only after the replacement and the source's already
        spawned join children resolve successfully.
        """

        with self._lock:
            source = self._require(source_id)
            replacement = self._require(replacement_id)
            if source.node_id == self._authority_root_id:
                raise RuntimeError("authority root cannot be replaced")
            if source.status not in {"FAILED", "QUARANTINED"}:
                raise RuntimeError("replacement source must be failed or quarantined")
            if source.node_id == replacement.node_id:
                raise ValueError("node cannot replace itself")
            if not set(source.obligations) <= set(replacement.obligations):
                raise ValueError("replacement does not cover source obligations")

            prior = self._replacements.get(source.node_id)
            if prior is not None:
                if prior == replacement.node_id:
                    return
                raise RuntimeError("replacement is already bound")
            if replacement.node_id in self._replacements.values():
                raise RuntimeError("replacement target is already bound to another source")

            self._replacements[source.node_id] = replacement.node_id
            if _has_cycle(self._blocking_graph()):
                del self._replacements[source.node_id]
                raise ValueError("replacement would create a blocking cycle")

            self._record(
                "NODE_REPLACEMENT_BIND",
                source.node_id,
                replacement_id=replacement.node_id,
            )
            self._assert_invariants()

    def replacement_for(self, source_id: str) -> str | None:
        with self._lock:
            source = self._require(source_id)
            return self._replacements.get(source.node_id)

    def close(self, node_id: str) -> NodeInstance:
        with self._lock:
            node = self._require_open(node_id)
            if not node.self_complete:
                raise RuntimeError("node local work is not complete")
            unresolved_causal = sorted(
                dependency
                for dependency in self._causal[node.node_id]
                if not self._closure_satisfied(dependency)
            )
            if unresolved_causal:
                raise RuntimeError(
                    f"causal dependencies are not closed: {unresolved_causal!r}"
                )
            unresolved_join = sorted(
                child
                for child in self._joins[node.node_id]
                if not self._closure_satisfied(child)
            )
            if unresolved_join:
                raise RuntimeError(
                    f"join dependencies are not closed: {unresolved_join!r}"
                )
            open_satellites = sorted(
                other_id
                for other_id, other in self._nodes.items()
                if other.status == OPEN and other.center_id == node.node_id
            )
            if open_satellites:
                raise RuntimeError(
                    f"recenter open satellites before closing center: {open_satellites!r}"
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
                "started_node_count": sum(
                    node.execution_started for node in self._nodes.values()
                ),
                "self_complete_node_count": sum(
                    node.self_complete for node in self._nodes.values()
                ),
                "max_nodes": self._max_nodes,
                "max_invocation_depth": max(
                    node.invocation_depth for node in self._nodes.values()
                ),
                "causal_edge_count": sum(
                    len(value) for value in self._causal.values()
                ),
                "join_edge_count": sum(
                    len(value) for value in self._joins.values()
                ),
                "coordination_edge_count": len(self._coordination),
                "coordination_point_count": len(self._coordination_points),
                "replacement_edge_count": len(self._replacements),
                "caller_is_provenance_not_center": True,
                "caller_cycles_allowed": False,
                "caller_chain_reaches_authority_root": True,
                "causal_edges_sealed_after_start": True,
                "center_cycles_allowed": True,
                "causal_cycles_allowed": False,
                "join_cycles_allowed": False,
                "cross_relation_blocking_cycles_allowed": False,
                "failed_or_quarantined_counts_as_closed": False,
                "authority_root_stable": True,
                "species_position_fixed": False,
                "canon_allowed": False,
                "execution_admitted": False,
                "memory_mutation_allowed": False,
                "speedup_claim": False,
            }


__all__ = [
    "DEFAULT_MAX_NODES",
    "DIM",
    "CoordinationPoint",
    "NodeInstance",
    "OPEN",
    "OrchorbitalFabric",
    "SCHEMA",
    "SpawnRequest",
    "TAU",
    "TERMINAL_STATES",
    "VERSION",
]
