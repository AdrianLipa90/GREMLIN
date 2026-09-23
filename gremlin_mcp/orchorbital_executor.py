from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from typing import Any

from gremlin_mcp.adaptive_runtime import OperatorTier, ResourceBudget, ResourceCost
from gremlin_mcp.orchorbital_allocator import OctopusAllocation, allocate_invocation
from gremlin_mcp.orchorbital_context import OrbitalContextStore, PACKET_PAYLOAD_KEY
from gremlin_mcp.orchorbital_fabric import NodeInstance, OrchorbitalFabric
from gremlin_mcp.workers import WORKER_SPECIES
from tools.gremlin_geometry_phase_scheduler_v01 import SCHEDULER_KEY

SCHEMA = "GREMLIN_ORCHORBITAL_EXECUTOR_V0_2"
VERSION = "0.2.1"
CONTEXT_SCHEMA = "GREMLIN_ORCHORBITAL_WORKER_CONTEXT_V0_2"
DEFAULT_INPUT_SCHEMA = "GREMLIN_ORCHORBITAL_OBLIGATION_INPUT_V0_1"
DISCOVERY_SCHEMA = "GREMLIN_ORCHORBITAL_DISCOVERY_V0_1"
CONTEXT_KEY = "_gremlin_orchorbital_context"
DISCOVERY_KEY = "_gremlin_orchorbital_discovery"
ORBITAL_CONTEXT_PACKET_KEY = PACKET_PAYLOAD_KEY
TASK_DOMAIN = b"GREMLIN-ORCHORBITAL-WORKER-TASK/v0.2\x00"
LOCAL_RESULT_DOMAIN = b"GREMLIN-ORCHORBITAL-LOCAL-RESULT/v0.2\x00"
DISCOVERY_CONTEXT_DOMAIN = b"GREMLIN-ORCHORBITAL-DISCOVERY-CONTEXT/v0.2\x00"
REDUCTION_INPUT_DOMAIN = b"GREMLIN-ORCHORBITAL-REDUCTION-INPUT/v0.2\x00"
REDUCTION_OUTPUT_DOMAIN = b"GREMLIN-ORCHORBITAL-REDUCTION-OUTPUT/v0.2\x00"
REDUCTION_TASK_DOMAIN = b"GREMLIN-ORCHORBITAL-REDUCTION-TASK/v0.2\x00"
RECOVERY_EFFECTIVE_DOMAIN = b"GREMLIN-ORCHORBITAL-RECOVERY-EFFECTIVE/v0.2\x00"
REDUCTION_SCHEMA = "GREMLIN_ORCHORBITAL_REDUCTION_V0_1"
REDUCTION_TASK_KEY = "_gremlin_orchorbital_reduction"
EXECUTOR_CHECKPOINT_SCHEMA = "GREMLIN_ORCHORBITAL_EXECUTOR_CHECKPOINT_V0_1"
EXECUTOR_CHECKPOINT_DOMAIN = b"GREMLIN-ORCHORBITAL-EXECUTOR-CHECKPOINT/v0.1\x00"
MAX_DISCOVERED_OBLIGATIONS = 64
MAX_DISCOVERY_HANDOFF_KEYS = 128
MAX_DISCOVERY_HANDOFF_BYTES = 65_536
PARENT_RESULT_CONTEXT_KEY = "_gremlin_parent_result"
DISCOVERY_HANDOFF_CONTEXT_KEY = "_gremlin_handoff"
WORKER_DISPATCHABLE_SPECIES = frozenset(WORKER_SPECIES)


def _strict_text(value: Any, field: str, *, maximum: int = 256) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    out = value.strip()
    if not out or len(out) > maximum:
        raise ValueError(f"{field} must contain 1..{maximum} characters")
    return out


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("value must be finite JSON data") from exc


def _strict_obligations(
    values: Iterable[str],
    *,
    field: str,
    allow_empty: bool,
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, Mapping)) or not isinstance(values, Iterable):
        raise ValueError(f"{field} must be an iterable of strings")
    out: list[str] = []
    for index, raw in enumerate(values):
        item = _strict_text(raw, f"{field}[{index}]", maximum=512)
        if item not in out:
            out.append(item)
    if not allow_empty and not out:
        raise ValueError(f"{field} must be non-empty")
    if len(out) > MAX_DISCOVERED_OBLIGATIONS:
        raise ValueError(
            f"{field} exceeds {MAX_DISCOVERED_OBLIGATIONS} obligations"
        )
    return tuple(out)


def _task_id(execution_id: str, node: NodeInstance) -> str:
    raw = "\x00".join(
        (execution_id, node.authority_root_id, node.node_id)
    ).encode("utf-8")
    digest = hashlib.blake2b(TASK_DOMAIN + raw, digest_size=20).hexdigest()
    return f"orch-v02-{digest}"


def _discovery_context_frame_id(
    execution_id: str,
    caller_id: str,
    discovery_key: str,
) -> str:
    raw = "\x00".join((execution_id, caller_id, discovery_key)).encode("utf-8")
    digest = hashlib.blake2b(
        DISCOVERY_CONTEXT_DOMAIN + raw,
        digest_size=16,
    ).hexdigest()
    return f"CTX:DISC:{digest}"


def _reduction_task_id(
    execution_id: str,
    node_id: str,
    reduction_input_commitment: str,
) -> str:
    raw = "\x00".join(
        (execution_id, node_id, reduction_input_commitment)
    ).encode("utf-8")
    digest = hashlib.blake2b(
        REDUCTION_TASK_DOMAIN + raw,
        digest_size=20,
    ).hexdigest()
    return f"orch-red-v02-{digest}"


def _local_result_commitment(
    execution_id: str,
    node_id: str,
    output: Any,
) -> str:
    raw = {
        "execution_id": execution_id,
        "node_id": node_id,
        "output": output,
    }
    return hashlib.blake2b(
        LOCAL_RESULT_DOMAIN + _canonical(raw),
        digest_size=32,
    ).hexdigest()


def _discovery_directive(
    output: Any,
) -> tuple[tuple[str, ...], dict[str, Any] | None]:
    if not isinstance(output, Mapping):
        return (), None
    raw = output.get(DISCOVERY_KEY)
    if raw is None:
        return (), None
    if not isinstance(raw, Mapping):
        raise ValueError(f"{DISCOVERY_KEY} must be an object")
    if raw.get("schema") != DISCOVERY_SCHEMA:
        raise ValueError("invalid orchorbital discovery schema")
    obligations = raw.get("obligations")
    if obligations is None:
        raise ValueError("orchorbital discovery requires obligations")
    ordered = _strict_obligations(
        obligations,
        field="discovered obligations",
        allow_empty=True,
    )
    raw_handoff = raw.get("handoff")
    if raw_handoff is None:
        return ordered, None
    if not ordered:
        raise ValueError("orchorbital handoff requires at least one obligation")
    if not isinstance(raw_handoff, Mapping):
        raise ValueError("orchorbital discovery handoff must be an object")
    if len(raw_handoff) > MAX_DISCOVERY_HANDOFF_KEYS:
        raise ValueError(
            f"orchorbital discovery handoff exceeds {MAX_DISCOVERY_HANDOFF_KEYS} keys"
        )
    handoff: dict[str, Any] = {}
    for index, (raw_key, raw_value) in enumerate(raw_handoff.items()):
        key = _strict_text(raw_key, f"handoff key[{index}]", maximum=256)
        if key in handoff:
            raise ValueError("duplicate normalized discovery handoff key")
        handoff[key] = deepcopy(raw_value)
    encoded = _canonical(handoff)
    if len(encoded) > MAX_DISCOVERY_HANDOFF_BYTES:
        raise ValueError(
            f"orchorbital discovery handoff exceeds {MAX_DISCOVERY_HANDOFF_BYTES} bytes"
        )
    return ordered, handoff


def _discovered_obligations(output: Any) -> tuple[str, ...]:
    return _discovery_directive(output)[0]


@dataclass(frozen=True)
class DispatchRecord:
    node_id: str
    task_id: str
    species: str
    task_commitment: str
    state: str
    topology_commitment: str


class OrchorbitalExecutor:
    """Bind dynamic fabric nodes to the existing pull-based WorkerBroker.

    The bridge is intentionally stateless with respect to node/task identity:
    task IDs derive only from execution_id + immutable node identity, so a
    restarted orchestrator can replay enqueue safely. WorkerBroker itself
    remains the lease/result transport and rejects content drift for an
    existing deterministic task ID.
    """

    def __init__(
        self,
        *,
        execution_id: str,
        fabric: OrchorbitalFabric,
        broker: Any,
        operators: Iterable[OperatorTier],
        budget: ResourceBudget,
        context_store: OrbitalContextStore | None = None,
        max_states: int = 65_536,
    ) -> None:
        self.execution_id = _strict_text(
            execution_id,
            "execution_id",
            maximum=128,
        )
        if not isinstance(fabric, OrchorbitalFabric):
            raise ValueError("fabric must be an OrchorbitalFabric")
        if not isinstance(budget, ResourceBudget):
            raise ValueError("budget must be a ResourceBudget")
        rows = tuple(operators)
        if not rows or not all(isinstance(row, OperatorTier) for row in rows):
            raise ValueError("operators must contain OperatorTier values")
        if isinstance(max_states, bool) or not isinstance(max_states, int) or max_states < 1:
            raise ValueError("max_states must be a positive integer")
        if not hasattr(broker, "enqueue") or not hasattr(broker, "task_result"):
            raise ValueError("broker must provide enqueue and task_result")
        if context_store is not None:
            if not isinstance(context_store, OrbitalContextStore):
                raise ValueError("context_store must be an OrbitalContextStore")
            if context_store.fabric is not fabric:
                raise ValueError("context_store must belong to the same fabric")
        self.fabric = fabric
        self.broker = broker
        self.context_store = context_store
        self.operators = rows
        self.budget = budget
        self.max_states = max_states
        self._local_results: dict[str, Any] = {}
        self._reduction_results: dict[str, Any] = {}
        self._reduction_input_commitments: dict[str, str] = {}

    def deterministic_task_id(self, node_id: str) -> str:
        return _task_id(self.execution_id, self.fabric.node(node_id))

    def frontier(self) -> dict[str, object]:
        ready = tuple(self.fabric.ready_nodes())
        running = tuple(self.fabric.running_nodes())
        worker_ready = tuple(
            node_id
            for node_id in ready
            if self.fabric.node(node_id).species in WORKER_DISPATCHABLE_SPECIES
        )
        local_ready = tuple(
            node_id
            for node_id in ready
            if self.fabric.node(node_id).species not in WORKER_DISPATCHABLE_SPECIES
        )
        worker_running = tuple(
            node_id
            for node_id in running
            if self.fabric.node(node_id).species in WORKER_DISPATCHABLE_SPECIES
        )
        local_running = tuple(
            node_id
            for node_id in running
            if self.fabric.node(node_id).species not in WORKER_DISPATCHABLE_SPECIES
        )
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "execution_id": self.execution_id,
            "worker_ready": worker_ready,
            "worker_running": worker_running,
            "local_ready": local_ready,
            "local_running": local_running,
            "authority_root_id": self.fabric.authority_root_id,
            "topology_commitment": self.fabric.topology_commitment(),
            "execution_admitted": False,
            "canon_allowed": False,
        }

    def _worker_payload(
        self,
        node: NodeInstance,
        input_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(input_payload, Mapping):
            raise ValueError("input_payload must be a mapping")
        payload: dict[str, Any] = {
            CONTEXT_KEY: {
                "schema": CONTEXT_SCHEMA,
                "execution_id": self.execution_id,
                "node_id": node.node_id,
                "species": node.species,
                "authority_root_id": node.authority_root_id,
                "caller_id": node.caller_id,
                "obligations": list(node.obligations),
                "phase36": None if node.phase36 is None else list(node.phase36),
                "invocation_depth": node.invocation_depth,
            },
            "input": dict(input_payload),
        }
        if self.context_store is not None:
            payload[ORBITAL_CONTEXT_PACKET_KEY] = self.context_store.packet(node.node_id)
        if node.phase36 is not None:
            payload[SCHEDULER_KEY] = {
                "phase36": list(node.phase36),
                "ready": True,
                "readiness": 1.0,
            }
        _canonical(payload)
        return payload

    def ensure_dispatched(
        self,
        node_id: str,
        input_payload: Mapping[str, Any],
    ) -> DispatchRecord:
        node = self.fabric.node(node_id)
        if node.status != "OPEN":
            raise RuntimeError("only open nodes may be dispatched")
        if node.self_complete:
            raise RuntimeError("self-complete node cannot be dispatched")
        if node.species not in WORKER_DISPATCHABLE_SPECIES:
            raise RuntimeError(
                f"species requires local/core execution adapter: {node.species}"
            )

        task_id = _task_id(self.execution_id, node)
        worker_payload = self._worker_payload(node, input_payload)
        if not node.execution_started:
            node = self.fabric.mark_started(node.node_id)
        task = self.broker.enqueue(
            node.species,
            worker_payload,
            task_id=task_id,
        )
        state = task.get("state")
        commitment = task.get("task_commitment")
        if not isinstance(state, str):
            raise RuntimeError("worker broker returned invalid task state")
        if not isinstance(commitment, str) or not commitment:
            raise RuntimeError("worker broker returned invalid task commitment")
        return DispatchRecord(
            node_id=node.node_id,
            task_id=task_id,
            species=node.species,
            task_commitment=commitment,
            state=state,
            topology_commitment=self.fabric.topology_commitment(),
        )

    def default_input_payload(self, node_id: str) -> dict[str, object]:
        """Build the canonical automatic payload for a dynamically allocated node."""

        node = self.fabric.node(node_id)
        return {
            "schema": DEFAULT_INPUT_SCHEMA,
            "execution_id": self.execution_id,
            "node_id": node.node_id,
            "species": node.species,
            "obligations": list(node.obligations),
            "caller_id": node.caller_id,
            "center_id": node.center_id,
            "invocation_depth": node.invocation_depth,
            "authority_root_id": node.authority_root_id,
        }

    def dispatch_ready(
        self,
        payload_overrides: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> dict[str, object]:
        """Dispatch the current worker frontier using overrides or obligation envelopes."""

        overrides: Mapping[str, Mapping[str, Any]] = (
            {} if payload_overrides is None else payload_overrides
        )
        if not isinstance(overrides, Mapping):
            raise ValueError("payload_overrides must be a mapping")
        frontier = self.frontier()
        retry_missing: list[str] = []
        for node_id in frontier["worker_running"]:
            task_id = self.deterministic_task_id(node_id)
            try:
                self.broker.task_result(task_id)
            except ValueError as exc:
                if "unknown task_id" not in str(exc):
                    raise
                retry_missing.append(node_id)
        candidate_ids = tuple(
            dict.fromkeys(
                tuple(frontier["worker_ready"]) + tuple(retry_missing)
            )
        )
        payloads: dict[str, Mapping[str, Any]] = {}
        for node_id in candidate_ids:
            override = overrides.get(node_id)
            payloads[node_id] = (
                self.default_input_payload(node_id)
                if override is None
                else override
            )
        return self.dispatch_frontier(payloads)

    def dispatch_frontier(
        self,
        payload_by_node: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, object]:
        if not isinstance(payload_by_node, Mapping):
            raise ValueError("payload_by_node must be a mapping")
        frontier = self.frontier()
        candidate_ids = tuple(
            dict.fromkeys(
                tuple(frontier["worker_ready"]) + tuple(frontier["worker_running"])
            )
        )
        dispatched: list[dict[str, object]] = []
        failures: list[dict[str, str]] = []
        for node_id in candidate_ids:
            payload = payload_by_node.get(node_id)
            if payload is None:
                failures.append(
                    {
                        "node_id": node_id,
                        "error": "missing input payload",
                    }
                )
                continue
            try:
                record = self.ensure_dispatched(node_id, payload)
            except Exception as exc:
                failures.append(
                    {
                        "node_id": node_id,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                continue
            dispatched.append(
                {
                    "node_id": record.node_id,
                    "task_id": record.task_id,
                    "species": record.species,
                    "task_commitment": record.task_commitment,
                    "state": record.state,
                    "topology_commitment": record.topology_commitment,
                }
            )
        return {
            "schema": SCHEMA,
            "execution_id": self.execution_id,
            "dispatched": dispatched,
            "failures": failures,
            "local_ready": list(self.frontier()["local_ready"]),
            "execution_admitted": False,
            "canon_allowed": False,
        }

    def allocate(
        self,
        caller_id: str,
        obligations: Iterable[str],
        *,
        center_by_operator: Mapping[str, str] | None = None,
        candidate_centers_by_operator: Mapping[str, Iterable[str]] | None = None,
        phase36_by_operator: Mapping[str, Sequence[float]] | None = None,
        join_to_caller: bool = True,
        allocation_key: str | None = None,
        child_context_set_values: Mapping[str, Any] | None = None,
    ) -> OctopusAllocation:
        """Allocate through OCTOPUS and bind inherited context as one flow.

        Topology allocation remains owned by the allocator. When an orbital
        context store is configured, the caller context must already exist and
        every returned child receives an immutable empty-delta frame based on
        that caller. Replays are idempotent for deterministic allocations.
        """

        caller = self.fabric.node(caller_id)
        if caller.status != "OPEN":
            raise RuntimeError("caller node must be open")
        context_delta: dict[str, Any] = {}
        if child_context_set_values is not None:
            if not isinstance(child_context_set_values, Mapping):
                raise ValueError("child_context_set_values must be a mapping")
            context_delta = deepcopy(dict(child_context_set_values))
            _canonical(context_delta)
            if self.context_store is None:
                raise RuntimeError(
                    "child context delta requires an OrbitalContextStore"
                )
        if self.context_store is not None:
            # Precondition before topology mutation.
            self.context_store.frame(caller.node_id)

        allocation = allocate_invocation(
            self.fabric,
            caller.node_id,
            obligations,
            self.operators,
            budget=self.budget,
            center_by_operator=center_by_operator,
            candidate_centers_by_operator=candidate_centers_by_operator,
            phase36_by_operator=phase36_by_operator,
            join_to_caller=join_to_caller,
            allocation_key=allocation_key,
            max_states=self.max_states,
        )

        if self.context_store is not None:
            for node in allocation.nodes:
                if node.caller_id != caller.node_id:
                    raise RuntimeError("allocation caller/context lineage mismatch")
                self.context_store.inherit_from_caller(
                    node.node_id,
                    set_values=context_delta,
                )
        return allocation

    def apply_discovery(
        self,
        caller_id: str,
        obligations: Iterable[str],
        *,
        discovery_key: str,
        parent_result_commitment: str | None = None,
        handoff: Mapping[str, Any] | None = None,
    ) -> OctopusAllocation:
        ordered = _strict_obligations(
            obligations,
            field="discovered obligations",
            allow_empty=False,
        )
        key = _strict_text(discovery_key, "discovery_key", maximum=256)

        context_delta: dict[str, Any] | None = None
        if self.context_store is not None:
            if parent_result_commitment is None:
                raise ValueError(
                    "context-backed discovery requires parent_result_commitment"
                )
            result_commitment = _strict_text(
                parent_result_commitment,
                "parent_result_commitment",
                maximum=64,
            )
            if len(result_commitment) != 64:
                raise ValueError(
                    "parent_result_commitment must be a 64-character commitment"
                )
            try:
                int(result_commitment, 16)
            except ValueError as exc:
                raise ValueError(
                    "parent_result_commitment must be hexadecimal"
                ) from exc
            context_delta = {
                PARENT_RESULT_CONTEXT_KEY: {
                    "node_id": _strict_text(caller_id, "caller_id"),
                    "result_commitment": result_commitment,
                }
            }
            if handoff is not None:
                if not isinstance(handoff, Mapping):
                    raise ValueError("handoff must be a mapping")
                context_delta[DISCOVERY_HANDOFF_CONTEXT_KEY] = deepcopy(dict(handoff))
                _canonical(context_delta)
        elif handoff is not None:
            raise RuntimeError(
                "orchorbital discovery handoff requires an OrbitalContextStore"
            )

        caller = self.fabric.node(caller_id)
        if caller.status != "OPEN":
            raise RuntimeError("caller node must be open")
        if self.context_store is not None:
            self.context_store.frame(caller.node_id)

        allocation = allocate_invocation(
            self.fabric,
            caller.node_id,
            ordered,
            self.operators,
            budget=self.budget,
            join_to_caller=True,
            allocation_key=f"{self.execution_id}:{key}",
            max_states=self.max_states,
        )

        if self.context_store is not None:
            shared_frame_id = _discovery_context_frame_id(
                self.execution_id,
                caller.node_id,
                key,
            )
            self.context_store.bind_shared_frame(
                shared_frame_id,
                base_frame_id=caller.node_id,
                set_values={} if context_delta is None else context_delta,
            )
            for node in allocation.nodes:
                if node.caller_id != caller.node_id:
                    raise RuntimeError(
                        "discovery allocation caller/context lineage mismatch"
                    )
                self.context_store.bind_node(
                    node.node_id,
                    base_node_id=shared_frame_id,
                )
        return allocation

    def reconcile_node(self, node_id: str) -> dict[str, object]:
        node = self.fabric.node(node_id)
        if node.species not in WORKER_DISPATCHABLE_SPECIES:
            raise RuntimeError("node is not WorkerBroker-dispatchable")
        if node.status != "OPEN":
            return {
                "node_id": node.node_id,
                "state": node.status,
                "changed": False,
            }
        if not node.execution_started:
            raise RuntimeError("node execution has not started")
        if node.self_complete:
            return {
                "node_id": node.node_id,
                "state": "SELF_COMPLETE",
                "changed": False,
            }

        task_id = _task_id(self.execution_id, node)
        try:
            task = self.broker.task_result(task_id)
        except ValueError as exc:
            if "unknown task_id" in str(exc):
                return {
                    "node_id": node.node_id,
                    "task_id": task_id,
                    "state": "MISSING_TASK_RETRY_REQUIRED",
                    "changed": False,
                }
            raise

        state = task.get("state")
        if state in {"QUEUED", "LEASED"}:
            return {
                "node_id": node.node_id,
                "task_id": task_id,
                "state": state,
                "changed": False,
            }
        if state != "DONE":
            raise RuntimeError(f"unsupported worker task state: {state!r}")

        result_commitment = task.get("result_commitment")
        if not isinstance(result_commitment, str) or not result_commitment:
            raise RuntimeError("DONE worker task is missing result commitment")
        if "result" not in task:
            raise RuntimeError("DONE worker task is missing result")
        output = task["result"]

        try:
            discovered, handoff = _discovery_directive(output)
        except ValueError as exc:
            self.fabric.quarantine(
                node.node_id,
                reason=f"invalid worker discovery envelope: {exc}",
            )
            return {
                "node_id": node.node_id,
                "task_id": task_id,
                "state": "QUARANTINED_INVALID_DISCOVERY",
                "changed": True,
            }

        if handoff is not None and self.context_store is None:
            self.fabric.quarantine(
                node.node_id,
                reason="worker discovery handoff requires context store",
            )
            return {
                "node_id": node.node_id,
                "task_id": task_id,
                "state": "QUARANTINED_DISCOVERY_HANDOFF_WITHOUT_CONTEXT",
                "changed": True,
            }

        allocation_receipt: dict[str, object] | None = None
        if discovered:
            allocation = self.apply_discovery(
                node.node_id,
                discovered,
                discovery_key=result_commitment,
                parent_result_commitment=result_commitment,
                handoff=handoff,
            )
            allocation_receipt = allocation.receipt()

        self.fabric.mark_self_complete(
            node.node_id,
            result_commitment=result_commitment,
        )
        return {
            "node_id": node.node_id,
            "task_id": task_id,
            "state": "SELF_COMPLETE",
            "changed": True,
            "result_commitment": result_commitment,
            "discovered_obligations": list(discovered),
            "handoff_present": handoff is not None,
            "allocation": allocation_receipt,
        }

    def reconcile_frontier(self) -> dict[str, object]:
        rows: list[dict[str, object]] = []
        failures: list[dict[str, str]] = []
        for node_id in tuple(self.fabric.running_nodes()):
            node = self.fabric.node(node_id)
            if node.species not in WORKER_DISPATCHABLE_SPECIES:
                continue
            try:
                rows.append(self.reconcile_node(node_id))
            except Exception as exc:
                failures.append(
                    {
                        "node_id": node_id,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
        return {
            "schema": SCHEMA,
            "execution_id": self.execution_id,
            "nodes": rows,
            "failures": failures,
            "topology_commitment": self.fabric.topology_commitment(),
            "execution_admitted": False,
            "canon_allowed": False,
        }

    def start_local(self, node_id: str) -> NodeInstance:
        node = self.fabric.node(node_id)
        if node.species in WORKER_DISPATCHABLE_SPECIES:
            raise RuntimeError("worker-dispatchable node must use WorkerBroker")
        return self.fabric.mark_started(node.node_id)

    def complete_local(
        self,
        node_id: str,
        output: Any,
    ) -> dict[str, object]:
        node = self.fabric.node(node_id)
        if node.species in WORKER_DISPATCHABLE_SPECIES:
            raise RuntimeError("worker-dispatchable node must use WorkerBroker")
        if not node.execution_started:
            node = self.fabric.mark_started(node.node_id)
        commitment = _local_result_commitment(
            self.execution_id,
            node.node_id,
            output,
        )
        discovered, handoff = _discovery_directive(output)
        if handoff is not None and self.context_store is None:
            raise RuntimeError(
                "local discovery handoff requires an OrbitalContextStore"
            )
        allocation_receipt: dict[str, object] | None = None
        if discovered:
            allocation = self.apply_discovery(
                node.node_id,
                discovered,
                discovery_key=commitment,
                parent_result_commitment=commitment,
                handoff=handoff,
            )
            allocation_receipt = allocation.receipt()
        self.fabric.mark_self_complete(
            node.node_id,
            result_commitment=commitment,
        )
        prior = self._local_results.get(node.node_id)
        if prior is not None and _canonical(prior) != _canonical(output):
            raise RuntimeError("local result payload drift detected")
        self._local_results[node.node_id] = deepcopy(output)
        return {
            "node_id": node.node_id,
            "state": "SELF_COMPLETE",
            "result_commitment": commitment,
            "discovered_obligations": list(discovered),
            "handoff_present": handoff is not None,
            "allocation": allocation_receipt,
        }

    def _resolved_success_node_id(self, node_id: str) -> str:
        current = self.fabric.node(node_id)
        seen: set[str] = set()
        while current.status in {"FAILED", "QUARANTINED"}:
            if current.node_id in seen:
                raise RuntimeError("replacement chain contains a cycle")
            seen.add(current.node_id)
            replacement_id = self.fabric.replacement_for(current.node_id)
            if replacement_id is None:
                raise RuntimeError(
                    f"node has no successful replacement: {current.node_id}"
                )
            current = self.fabric.node(replacement_id)
        if current.status != "CLOSED":
            raise RuntimeError(
                f"resolved result node is not closed: {current.node_id}"
            )
        return current.node_id

    def _self_result(self, node_id: str) -> tuple[str, Any]:
        node = self.fabric.node(node_id)
        commitment = node.result_commitment
        if not isinstance(commitment, str) or not commitment:
            raise RuntimeError(f"node result commitment is unavailable: {node.node_id}")

        if node.species in WORKER_DISPATCHABLE_SPECIES:
            task = self.broker.task_result(_task_id(self.execution_id, node))
            if task.get("state") != "DONE" or "result" not in task:
                raise RuntimeError(f"worker result is unavailable: {node.node_id}")
            task_commitment = task.get("result_commitment")
            if task_commitment != commitment:
                raise RuntimeError(
                    f"worker/fabric result commitment mismatch: {node.node_id}"
                )
            return commitment, deepcopy(task["result"])

        if node.node_id not in self._local_results:
            raise RuntimeError(
                f"local result payload is unavailable: {node.node_id}"
            )
        output = deepcopy(self._local_results[node.node_id])
        expected = _local_result_commitment(
            self.execution_id,
            node.node_id,
            output,
        )
        if expected != commitment:
            raise RuntimeError(
                f"local result commitment mismatch: {node.node_id}"
            )
        return commitment, output

    def _closed_effective_result(self, node_id: str) -> dict[str, object]:
        node = self.fabric.node(node_id)
        if node.status != "CLOSED":
            raise RuntimeError(f"effective result node is not closed: {node.node_id}")
        if node.reduction_complete:
            commitment = node.reduction_commitment
            if not isinstance(commitment, str) or not commitment:
                raise RuntimeError(
                    f"reduction commitment is unavailable: {node.node_id}"
                )
            if node.node_id not in self._reduction_results:
                raise RuntimeError(
                    f"reduction payload is unavailable: {node.node_id}"
                )
            output = deepcopy(self._reduction_results[node.node_id])
        else:
            commitment, output = self._self_result(node.node_id)
        return {
            "requested_node_id": node.node_id,
            "resolved_node_id": node.node_id,
            "source_status": "CLOSED",
            "source_species": node.species,
            "resolved_species": node.species,
            "recovery": False,
            "effective_result_commitment": commitment,
            "output": output,
        }

    def _effective_result(
        self,
        node_id: str,
        *,
        path: frozenset[str] = frozenset(),
    ) -> dict[str, object]:
        if node_id in path:
            raise RuntimeError("effective-result recovery contains a cycle")
        node = self.fabric.node(node_id)
        if node.status == "CLOSED":
            return self._closed_effective_result(node.node_id)
        if node.status == "OPEN":
            raise RuntimeError(f"effective result node is unresolved: {node.node_id}")
        if node.status not in {"FAILED", "QUARANTINED"}:
            raise RuntimeError(f"unsupported effective result state: {node.status}")

        replacement_id = self.fabric.replacement_for(node.node_id)
        if replacement_id is None:
            raise RuntimeError(
                f"node has no successful replacement: {node.node_id}"
            )
        next_path = path | {node.node_id}
        replacement = self._effective_result(
            replacement_id,
            path=next_path,
        )
        stranded_children = [
            self._effective_result(child_id, path=next_path)
            for child_id in self.fabric.join_dependencies(node.node_id)
        ]

        partial_result: dict[str, object] | None = None
        if node.self_complete and node.result_commitment is not None:
            partial_commitment, partial_output = self._self_result(node.node_id)
            partial_result = {
                "result_commitment": partial_commitment,
                "output": partial_output,
            }

        prior_reduction: dict[str, object] | None = None
        if node.reduction_complete:
            if (
                not isinstance(node.reduction_commitment, str)
                or node.node_id not in self._reduction_results
            ):
                raise RuntimeError(
                    f"failed node reduction payload is unavailable: {node.node_id}"
                )
            prior_reduction = {
                "reduction_input_commitment": self._reduction_input_commitments.get(
                    node.node_id
                ),
                "reduction_commitment": node.reduction_commitment,
                "output": deepcopy(self._reduction_results[node.node_id]),
            }

        recovery_core = {
            "source_node_id": node.node_id,
            "source_status": node.status,
            "source_species": node.species,
            "source_partial_result": partial_result,
            "source_prior_reduction": prior_reduction,
            "replacement": replacement,
            "source_join_results": stranded_children,
        }
        recovery_commitment = hashlib.blake2b(
            RECOVERY_EFFECTIVE_DOMAIN + _canonical(recovery_core),
            digest_size=32,
        ).hexdigest()
        return {
            "requested_node_id": node.node_id,
            "resolved_node_id": replacement["resolved_node_id"],
            "source_status": node.status,
            "source_species": node.species,
            "resolved_species": replacement["resolved_species"],
            "recovery": True,
            "effective_result_commitment": recovery_commitment,
            "output": {
                "recovery": recovery_core,
            },
        }

    def build_reduction_packet(self, node_id: str) -> dict[str, object]:
        """Build explicit semantic inputs for one completed local join."""

        node = self.fabric.node(node_id)
        if node.status != "OPEN":
            raise RuntimeError("reduction target must remain open")
        if not node.self_complete:
            raise RuntimeError("reduction target local work is not complete")
        child_ids = self.fabric.join_dependencies(node.node_id)
        if not child_ids:
            raise RuntimeError("reduction target has no join children")
        unresolved = [
            child_id
            for child_id in child_ids
            if not self.fabric.is_resolved(child_id)
        ]
        if unresolved:
            raise RuntimeError(
                f"join dependencies are not closed: {sorted(unresolved)!r}"
            )

        own_commitment, own_output = self._self_result(node.node_id)
        children = [
            self._effective_result(child_id)
            for child_id in child_ids
        ]
        core = {
            "schema": REDUCTION_SCHEMA,
            "execution_id": self.execution_id,
            "node_id": node.node_id,
            "species": node.species,
            "self_result_commitment": own_commitment,
            "self_output": own_output,
            "join_results": children,
        }
        input_commitment = hashlib.blake2b(
            REDUCTION_INPUT_DOMAIN + _canonical(core),
            digest_size=32,
        ).hexdigest()
        return {
            **core,
            "reduction_input_commitment": input_commitment,
            "authority": "COGNITIVE_ROUTING_ONLY",
            "canon_allowed": False,
        }

    def complete_reduction(
        self,
        node_id: str,
        output: Any,
    ) -> dict[str, object]:
        """Bind a semantic local reduction to the exact joined result set."""

        packet = self.build_reduction_packet(node_id)
        _canonical(output)
        core = {
            "reduction_input_commitment": packet[
                "reduction_input_commitment"
            ],
            "output": output,
        }
        commitment = hashlib.blake2b(
            REDUCTION_OUTPUT_DOMAIN + _canonical(core),
            digest_size=32,
        ).hexdigest()

        node = self.fabric.node(node_id)
        if node.reduction_complete:
            if node.reduction_commitment != commitment:
                raise RuntimeError("node reduction is already complete")
            prior = self._reduction_results.get(node.node_id)
            if prior is not None and _canonical(prior) != _canonical(output):
                raise RuntimeError("reduction payload drift detected")
        else:
            self.fabric.mark_reduction_complete(
                node.node_id,
                reduction_commitment=commitment,
            )

        self._reduction_results[node.node_id] = deepcopy(output)
        self._reduction_input_commitments[node.node_id] = str(
            packet["reduction_input_commitment"]
        )
        return {
            "schema": REDUCTION_SCHEMA,
            "node_id": node.node_id,
            "state": "REDUCTION_COMPLETE",
            "join_child_count": len(packet["join_results"]),
            "reduction_input_commitment": packet[
                "reduction_input_commitment"
            ],
            "reduction_commitment": commitment,
            "canon_allowed": False,
            "execution_admitted": False,
        }

    def deterministic_reduction_task_id(self, node_id: str) -> str:
        packet = self.build_reduction_packet(node_id)
        return _reduction_task_id(
            self.execution_id,
            node_id,
            str(packet["reduction_input_commitment"]),
        )

    def ensure_reduction_dispatched(self, node_id: str) -> DispatchRecord:
        """Dispatch one local join reduction back to the owning Bestiary species."""

        node = self.fabric.node(node_id)
        if node.status != "OPEN":
            raise RuntimeError("reduction target must remain open")
        if node.species not in WORKER_DISPATCHABLE_SPECIES:
            raise RuntimeError(
                f"reduction requires local/core adapter for species: {node.species}"
            )
        if node.reduction_complete:
            raise RuntimeError("node reduction is already complete")

        packet = self.build_reduction_packet(node.node_id)
        input_commitment = str(packet["reduction_input_commitment"])
        task_id = _reduction_task_id(
            self.execution_id,
            node.node_id,
            input_commitment,
        )
        payload = self._worker_payload(
            node,
            {
                "kind": "ORCHORBITAL_LOCAL_REDUCTION",
                REDUCTION_TASK_KEY: packet,
            },
        )
        task = self.broker.enqueue(
            node.species,
            payload,
            task_id=task_id,
        )
        state = task.get("state")
        commitment = task.get("task_commitment")
        if not isinstance(state, str):
            raise RuntimeError("worker broker returned invalid reduction task state")
        if not isinstance(commitment, str) or not commitment:
            raise RuntimeError(
                "worker broker returned invalid reduction task commitment"
            )
        return DispatchRecord(
            node_id=node.node_id,
            task_id=task_id,
            species=node.species,
            task_commitment=commitment,
            state=state,
            topology_commitment=self.fabric.topology_commitment(),
        )

    def dispatch_reduction_frontier(self) -> dict[str, object]:
        dispatched: list[dict[str, object]] = []
        failures: list[dict[str, str]] = []
        local_required: list[str] = []
        for node_id in self.fabric.reduction_candidates():
            node = self.fabric.node(node_id)
            if node.species not in WORKER_DISPATCHABLE_SPECIES:
                local_required.append(node.node_id)
                continue
            try:
                record = self.ensure_reduction_dispatched(node.node_id)
            except Exception as exc:
                failures.append(
                    {
                        "node_id": node.node_id,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                continue
            dispatched.append(
                {
                    "node_id": record.node_id,
                    "task_id": record.task_id,
                    "species": record.species,
                    "task_commitment": record.task_commitment,
                    "state": record.state,
                }
            )
        return {
            "schema": REDUCTION_SCHEMA,
            "execution_id": self.execution_id,
            "dispatched": dispatched,
            "local_reduction_required": local_required,
            "failures": failures,
            "global_synthesis_barrier_required": False,
            "canon_allowed": False,
            "execution_admitted": False,
        }

    def reconcile_reduction(self, node_id: str) -> dict[str, object]:
        node = self.fabric.node(node_id)
        if node.status != "OPEN":
            return {
                "node_id": node.node_id,
                "state": node.status,
                "changed": False,
            }
        if node.reduction_complete:
            return {
                "node_id": node.node_id,
                "state": "REDUCTION_COMPLETE",
                "changed": False,
                "reduction_commitment": node.reduction_commitment,
            }
        if node.species not in WORKER_DISPATCHABLE_SPECIES:
            raise RuntimeError("node requires local/core reduction adapter")

        packet = self.build_reduction_packet(node.node_id)
        task_id = _reduction_task_id(
            self.execution_id,
            node.node_id,
            str(packet["reduction_input_commitment"]),
        )
        try:
            task = self.broker.task_result(task_id)
        except ValueError as exc:
            if "unknown task_id" in str(exc):
                return {
                    "node_id": node.node_id,
                    "task_id": task_id,
                    "state": "MISSING_REDUCTION_TASK_RETRY_REQUIRED",
                    "changed": False,
                }
            raise

        state = task.get("state")
        if state in {"QUEUED", "LEASED"}:
            return {
                "node_id": node.node_id,
                "task_id": task_id,
                "state": state,
                "changed": False,
            }
        if state != "DONE":
            raise RuntimeError(f"unsupported reduction task state: {state!r}")
        if "result" not in task:
            raise RuntimeError("DONE reduction task is missing result")

        output = task["result"]
        try:
            discovered = _discovered_obligations(output)
        except ValueError as exc:
            self.fabric.quarantine(
                node.node_id,
                reason=f"invalid reduction discovery envelope: {exc}",
            )
            return {
                "node_id": node.node_id,
                "task_id": task_id,
                "state": "QUARANTINED_INVALID_REDUCTION",
                "changed": True,
            }
        if discovered:
            self.fabric.quarantine(
                node.node_id,
                reason=(
                    "reduction attempted recursive discovery after local join seal"
                ),
            )
            return {
                "node_id": node.node_id,
                "task_id": task_id,
                "state": "QUARANTINED_REDUCTION_DISCOVERY_AFTER_SEAL",
                "changed": True,
                "discovered_obligations": list(discovered),
            }

        receipt = self.complete_reduction(node.node_id, output)
        return {
            **receipt,
            "task_id": task_id,
            "worker_result_commitment": task.get("result_commitment"),
            "changed": True,
        }

    def reconcile_reduction_frontier(self) -> dict[str, object]:
        rows: list[dict[str, object]] = []
        failures: list[dict[str, str]] = []
        for node_id in self.fabric.reduction_candidates():
            node = self.fabric.node(node_id)
            if node.species not in WORKER_DISPATCHABLE_SPECIES:
                continue
            try:
                rows.append(self.reconcile_reduction(node.node_id))
            except Exception as exc:
                failures.append(
                    {
                        "node_id": node.node_id,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
        return {
            "schema": REDUCTION_SCHEMA,
            "execution_id": self.execution_id,
            "nodes": rows,
            "failures": failures,
            "canon_allowed": False,
            "execution_admitted": False,
        }

    def _fallback_center(self, node: NodeInstance) -> str:
        for candidate in (
            node.caller_id,
            self.fabric.authority_root_id,
        ):
            if candidate is None or candidate == node.node_id:
                continue
            target = self.fabric.node(candidate)
            if target.status == "OPEN":
                return target.node_id
        raise RuntimeError("no open fallback center is available")

    def settle_local_joins(self) -> dict[str, object]:
        """Close completed non-root subtrees deepest-first.

        Open satellites are explicitly recentered to a live caller/root fallback
        before their center closes. Computational barycenter migration is also
        explicit and therefore appears in the fabric event log.
        """

        closed: list[str] = []
        blocked: dict[str, str] = {}
        while True:
            progress = False
            candidates = sorted(
                (
                    self.fabric.node(node_id)
                    for node_id in self.fabric.closable_nodes()
                    if node_id != self.fabric.authority_root_id
                ),
                key=lambda node: (-node.invocation_depth, node.node_id),
            )
            if not candidates:
                break
            for node in candidates:
                current = self.fabric.node(node.node_id)
                if current.status != "OPEN":
                    continue
                try:
                    satellites = [
                        other
                        for other in self.fabric.nodes()
                        if other.status == "OPEN"
                        and other.center_id == current.node_id
                    ]
                    if satellites:
                        fallback = self._fallback_center(current)
                        for satellite in sorted(
                            satellites,
                            key=lambda item: item.node_id,
                        ):
                            target = fallback
                            if target == satellite.node_id:
                                target = self.fabric.authority_root_id
                            self.fabric.recenter(
                                satellite.node_id,
                                target,
                                reason="executor_center_drain",
                            )
                    if self.fabric.computational_barycenter_id == current.node_id:
                        self.fabric.move_barycenter(
                            self._fallback_center(current),
                            reason="executor_subtree_close",
                        )
                    self.fabric.close(current.node_id)
                except Exception as exc:
                    blocked[current.node_id] = f"{type(exc).__name__}: {exc}"
                    continue
                closed.append(current.node_id)
                blocked.pop(current.node_id, None)
                progress = True
            if not progress:
                break
        return {
            "schema": SCHEMA,
            "execution_id": self.execution_id,
            "closed": closed,
            "blocked": dict(sorted(blocked.items())),
            "reduction_required": list(self.fabric.reduction_candidates()),
            "authority_root_closed": (
                self.fabric.node(self.fabric.authority_root_id).status == "CLOSED"
            ),
            "topology_commitment": self.fabric.topology_commitment(),
            "execution_admitted": False,
            "canon_allowed": False,
        }

    def orchestration_step(
        self,
        payload_overrides: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> dict[str, object]:
        """Advance one deterministic non-blocking orchorbital runtime iteration.

        This method never waits for external workers. It reconciles results
        already present in WorkerBroker, closes locally resolvable subtrees,
        dispatches newly eligible reductions, and dispatches the current worker
        frontier. Repeated calls therefore advance the same fabric without a
        central global barrier.
        """

        before = self.fabric.topology_commitment()
        worker_reconcile = self.reconcile_frontier()
        settle_after_workers = self.settle_local_joins()
        reduction_reconcile = self.reconcile_reduction_frontier()
        settle_after_reductions = self.settle_local_joins()
        reduction_dispatch = self.dispatch_reduction_frontier()
        worker_dispatch = self.dispatch_ready(payload_overrides)
        after = self.fabric.topology_commitment()
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "execution_id": self.execution_id,
            "worker_reconcile": worker_reconcile,
            "settle_after_workers": settle_after_workers,
            "reduction_reconcile": reduction_reconcile,
            "settle_after_reductions": settle_after_reductions,
            "reduction_dispatch": reduction_dispatch,
            "worker_dispatch": worker_dispatch,
            "frontier": self.frontier(),
            "topology_commitment_before": before,
            "topology_commitment_after": after,
            "non_blocking": True,
            "global_synthesis_barrier_required": False,
            "canon_allowed": False,
            "execution_admitted": False,
        }

    def checkpoint_state(self) -> dict[str, object]:
        """Sensitive executor restart state excluding WorkerBroker persistence."""

        context_commitment: str | None = None
        if self.context_store is not None:
            context_checkpoint = self.context_store.checkpoint_state()
            raw_context_commitment = context_checkpoint.get("checkpoint_commitment")
            if not isinstance(raw_context_commitment, str):
                raise RuntimeError("context checkpoint commitment is unavailable")
            context_commitment = raw_context_commitment

        core: dict[str, object] = {
            "schema": EXECUTOR_CHECKPOINT_SCHEMA,
            "executor_version": VERSION,
            "execution_id": self.execution_id,
            "max_states": self.max_states,
            "fabric_topology_commitment": self.fabric.topology_commitment(),
            "context_checkpoint_commitment": context_commitment,
            "operators": [
                {
                    "species": operator.species,
                    "tier": operator.tier,
                    "capabilities": sorted(operator.capabilities),
                    "cost": {
                        "tokens": operator.cost.tokens,
                        "latency": operator.cost.latency,
                        "calls": operator.cost.calls,
                        "memory": operator.cost.memory,
                    },
                }
                for operator in sorted(
                    self.operators,
                    key=lambda item: item.operator_id,
                )
            ],
            "budget": {
                "tokens": self.budget.tokens,
                "latency": self.budget.latency,
                "calls": self.budget.calls,
                "memory": self.budget.memory,
            },
            "local_results": {
                node_id: deepcopy(self._local_results[node_id])
                for node_id in sorted(self._local_results)
            },
            "reduction_results": {
                node_id: deepcopy(self._reduction_results[node_id])
                for node_id in sorted(self._reduction_results)
            },
            "reduction_input_commitments": dict(
                sorted(self._reduction_input_commitments.items())
            ),
            "worker_broker_state_included": False,
            "worker_broker_state_required_external": True,
            "sensitive_result_payloads": True,
            "canon_allowed": False,
        }
        return {
            **core,
            "checkpoint_commitment": hashlib.blake2b(
                EXECUTOR_CHECKPOINT_DOMAIN + _canonical(core),
                digest_size=32,
            ).hexdigest(),
        }

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint: Mapping[str, Any],
        *,
        fabric: OrchorbitalFabric,
        broker: Any,
        context_store: OrbitalContextStore | None = None,
    ) -> "OrchorbitalExecutor":
        """Restore executor-only state and verify it against fabric + broker."""

        if not isinstance(checkpoint, Mapping):
            raise ValueError("executor checkpoint must be a mapping")
        if checkpoint.get("schema") != EXECUTOR_CHECKPOINT_SCHEMA:
            raise ValueError("invalid executor checkpoint schema")
        supplied = checkpoint.get("checkpoint_commitment")
        if not isinstance(supplied, str) or len(supplied) != 64:
            raise ValueError("executor checkpoint commitment is invalid")
        try:
            int(supplied, 16)
        except ValueError as exc:
            raise ValueError("executor checkpoint commitment must be hexadecimal") from exc
        core = {
            key: deepcopy(value)
            for key, value in checkpoint.items()
            if key != "checkpoint_commitment"
        }
        expected = hashlib.blake2b(
            EXECUTOR_CHECKPOINT_DOMAIN + _canonical(core),
            digest_size=32,
        ).hexdigest()
        if supplied != expected:
            raise ValueError("executor checkpoint commitment mismatch")

        if not isinstance(fabric, OrchorbitalFabric):
            raise ValueError("fabric must be an OrchorbitalFabric")
        claimed_topology = core.get("fabric_topology_commitment")
        if (
            not isinstance(claimed_topology, str)
            or fabric.topology_commitment() != claimed_topology
        ):
            raise ValueError("executor checkpoint fabric topology mismatch")

        claimed_context = core.get("context_checkpoint_commitment")
        if claimed_context is None:
            if context_store is not None:
                raise ValueError(
                    "executor checkpoint has no context store but one was supplied"
                )
        else:
            if not isinstance(claimed_context, str) or len(claimed_context) != 64:
                raise ValueError("executor checkpoint context commitment is invalid")
            if context_store is None:
                raise ValueError("executor checkpoint requires context store")
            actual_context = context_store.checkpoint_state().get(
                "checkpoint_commitment"
            )
            if actual_context != claimed_context:
                raise ValueError("executor checkpoint context store mismatch")

        execution_id = _strict_text(
            core.get("execution_id"),
            "execution_id",
            maximum=128,
        )
        max_states = core.get("max_states")
        if isinstance(max_states, bool) or not isinstance(max_states, int) or max_states < 1:
            raise ValueError("executor checkpoint max_states must be positive")

        raw_budget = core.get("budget")
        if not isinstance(raw_budget, Mapping):
            raise ValueError("executor checkpoint budget must be an object")
        budget = ResourceBudget(
            tokens=raw_budget.get("tokens"),  # type: ignore[arg-type]
            latency=raw_budget.get("latency"),  # type: ignore[arg-type]
            calls=raw_budget.get("calls"),  # type: ignore[arg-type]
            memory=raw_budget.get("memory"),  # type: ignore[arg-type]
        )

        raw_operators = core.get("operators")
        if not isinstance(raw_operators, list) or not raw_operators:
            raise ValueError("executor checkpoint operators must be a non-empty list")
        operators: list[OperatorTier] = []
        seen_operator_ids: set[str] = set()
        for index, raw in enumerate(raw_operators):
            if not isinstance(raw, Mapping):
                raise ValueError("executor checkpoint operator must be an object")
            raw_cost = raw.get("cost")
            if not isinstance(raw_cost, Mapping):
                raise ValueError("executor checkpoint operator cost must be an object")
            capabilities = raw.get("capabilities")
            if not isinstance(capabilities, list):
                raise ValueError("executor checkpoint capabilities must be a list")
            operator = OperatorTier(
                str(raw.get("species")),
                raw.get("tier"),  # type: ignore[arg-type]
                frozenset(str(value) for value in capabilities),
                ResourceCost(
                    tokens=raw_cost.get("tokens", 0.0),  # type: ignore[arg-type]
                    latency=raw_cost.get("latency", 0.0),  # type: ignore[arg-type]
                    calls=raw_cost.get("calls", 0.0),  # type: ignore[arg-type]
                    memory=raw_cost.get("memory", 0.0),  # type: ignore[arg-type]
                ),
            )
            if operator.operator_id in seen_operator_ids:
                raise ValueError("duplicate operator in executor checkpoint")
            seen_operator_ids.add(operator.operator_id)
            operators.append(operator)

        restored = cls(
            execution_id=execution_id,
            fabric=fabric,
            broker=broker,
            operators=operators,
            budget=budget,
            context_store=context_store,
            max_states=max_states,
        )

        raw_local = core.get("local_results")
        raw_reductions = core.get("reduction_results")
        raw_inputs = core.get("reduction_input_commitments")
        if not isinstance(raw_local, Mapping):
            raise ValueError("executor checkpoint local_results must be a mapping")
        if not isinstance(raw_reductions, Mapping):
            raise ValueError("executor checkpoint reduction_results must be a mapping")
        if not isinstance(raw_inputs, Mapping):
            raise ValueError(
                "executor checkpoint reduction_input_commitments must be a mapping"
            )

        local_results: dict[str, Any] = {}
        for raw_node_id, output in raw_local.items():
            node_id = _strict_text(raw_node_id, "local result node_id")
            node = fabric.node(node_id)
            if node.species in WORKER_DISPATCHABLE_SPECIES:
                raise ValueError("worker node cannot own executor-local result payload")
            if not node.self_complete or not isinstance(node.result_commitment, str):
                raise ValueError("local result node is not self-complete")
            _canonical(output)
            expected_local = _local_result_commitment(
                execution_id,
                node_id,
                output,
            )
            if expected_local != node.result_commitment:
                raise ValueError("local result commitment mismatch during restore")
            local_results[node_id] = deepcopy(output)

        reduction_results: dict[str, Any] = {}
        reduction_inputs: dict[str, str] = {}
        if set(raw_reductions) != set(raw_inputs):
            raise ValueError("executor reduction checkpoint key sets do not match")
        for raw_node_id, output in raw_reductions.items():
            node_id = _strict_text(raw_node_id, "reduction result node_id")
            node = fabric.node(node_id)
            if not node.reduction_complete or not isinstance(
                node.reduction_commitment, str
            ):
                raise ValueError("reduction result node is not reduction-complete")
            input_commitment = raw_inputs.get(raw_node_id)
            if not isinstance(input_commitment, str) or not input_commitment:
                raise ValueError("reduction input commitment is invalid")
            _canonical(output)
            reduction_core = {
                "reduction_input_commitment": input_commitment,
                "output": output,
            }
            expected_reduction = hashlib.blake2b(
                REDUCTION_OUTPUT_DOMAIN + _canonical(reduction_core),
                digest_size=32,
            ).hexdigest()
            if expected_reduction != node.reduction_commitment:
                raise ValueError("reduction result commitment mismatch during restore")
            reduction_results[node_id] = deepcopy(output)
            reduction_inputs[node_id] = input_commitment

        for node in fabric.nodes():
            if (
                node.species not in WORKER_DISPATCHABLE_SPECIES
                and node.self_complete
                and node.result_commitment is not None
                and node.node_id not in local_results
            ):
                raise ValueError(
                    f"executor checkpoint is missing local result: {node.node_id}"
                )
            if node.reduction_complete and node.node_id not in reduction_results:
                raise ValueError(
                    f"executor checkpoint is missing reduction result: {node.node_id}"
                )
            if (
                node.species in WORKER_DISPATCHABLE_SPECIES
                and node.self_complete
                and node.result_commitment is not None
            ):
                task = broker.task_result(_task_id(execution_id, node))
                if (
                    task.get("state") != "DONE"
                    or task.get("result_commitment") != node.result_commitment
                ):
                    raise ValueError(
                        f"broker/fabric worker result mismatch: {node.node_id}"
                    )

        restored._local_results = local_results
        restored._reduction_results = reduction_results
        restored._reduction_input_commitments = reduction_inputs
        return restored

    def receipt(self) -> dict[str, object]:
        frontier = self.frontier()
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "execution_id": self.execution_id,
            "worker_dispatchable_species": sorted(WORKER_DISPATCHABLE_SPECIES),
            "local_core_species": sorted(
                {
                    node.species
                    for node in self.fabric.nodes()
                    if node.species not in WORKER_DISPATCHABLE_SPECIES
                }
            ),
            "worker_ready_count": len(frontier["worker_ready"]),
            "worker_running_count": len(frontier["worker_running"]),
            "local_ready_count": len(frontier["local_ready"]),
            "local_running_count": len(frontier["local_running"]),
            "topology_commitment": self.fabric.topology_commitment(),
            "recursive_worker_discovery": True,
            "worker_local_reduction_continuations": True,
            "automatic_obligation_payloads": True,
            "non_blocking_orchestration_step": True,
            "orbital_context_packets": self.context_store is not None,
            "worker_context_cache_negotiation": self.context_store is not None,
            "worker_context_lease_bundle": self.context_store is not None,
            "worker_transport_projection_commitment": True,
            "deterministic_task_ids": True,
            "deterministic_discovery_allocations": True,
            "global_synthesis_barrier_required": False,
            "explicit_local_reduction_required": True,
            "automatic_semantic_reduction": False,
            "reduction_result_persistence": "CHECKPOINTABLE_EXECUTOR_STATE_V0_1",
            "reduction_candidate_count": len(self.fabric.reduction_candidates()),
            "authority": "COGNITIVE_ROUTING_ONLY",
            "epistemic": "CHYBA",
            "canon_allowed": False,
            "execution_admitted": False,
            "memory_mutation_allowed": False,
            "speedup_claim": False,
        }


__all__ = [
    "CONTEXT_KEY",
    "DEFAULT_INPUT_SCHEMA",
    "CONTEXT_SCHEMA",
    "DISCOVERY_HANDOFF_CONTEXT_KEY",
    "DISCOVERY_KEY",
    "DISCOVERY_SCHEMA",
    "DispatchRecord",
    "EXECUTOR_CHECKPOINT_SCHEMA",
    "MAX_DISCOVERED_OBLIGATIONS",
    "MAX_DISCOVERY_HANDOFF_BYTES",
    "MAX_DISCOVERY_HANDOFF_KEYS",
    "PARENT_RESULT_CONTEXT_KEY",
    "REDUCTION_TASK_KEY",
    "ORBITAL_CONTEXT_PACKET_KEY",
    "REDUCTION_SCHEMA",
    "OrchorbitalExecutor",
    "SCHEMA",
    "VERSION",
    "WORKER_DISPATCHABLE_SPECIES",
]
