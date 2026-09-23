from __future__ import annotations

import pytest

from gremlin_mcp.adaptive_runtime import OperatorTier, ResourceBudget, ResourceCost
from gremlin_mcp.orchorbital_allocator import allocate_invocation
from gremlin_mcp.orchorbital_context import OrbitalContextStore, apply_context_packet
from gremlin_mcp.orchorbital_executor import (
    DISCOVERY_KEY,
    DISCOVERY_SCHEMA,
    ORBITAL_CONTEXT_PACKET_KEY,
    OrchorbitalExecutor,
)
from gremlin_mcp.orchorbital_fabric import OrchorbitalFabric
from gremlin_mcp.workers import WorkerBroker


BUDGET = ResourceBudget(tokens=100.0, latency=100.0, calls=100.0, memory=100.0)


def operators():
    return (
        OperatorTier("SPIDER", 0, frozenset({"graph"}), ResourceCost(5, 5, 1, 2)),
        OperatorTier("OWL", 0, frozenset({"audit"}), ResourceCost(4, 4, 1, 2)),
        OperatorTier("MOLE", 0, frozenset({"derive"}), ResourceCost(7, 7, 1, 3)),
    )


def executor_with_worker(*, execution_id: str = "exec-1"):
    fabric = OrchorbitalFabric()
    broker = WorkerBroker()
    broker.register_worker(
        "worker-1",
        ["SPIDER", "OWL", "MOLE"],
        vector_width=4,
        max_batch=8,
    )
    executor = OrchorbitalExecutor(
        execution_id=execution_id,
        fabric=fabric,
        broker=broker,
        operators=operators(),
        budget=BUDGET,
    )
    return fabric, broker, executor


def _claim_and_submit(
    broker: WorkerBroker,
    *,
    species: str,
    output: object,
) -> str:
    lease = broker.claim("worker-1", species=species, limit=1)
    assert lease["lease_id"]
    assert len(lease["tasks"]) == 1
    task_id = lease["tasks"][0]["task_id"]
    broker.submit(
        "worker-1",
        lease["lease_id"],
        [
            {
                "task_id": task_id,
                "status": "CANDIDATE",
                "output": output,
            }
        ],
    )
    return task_id


def test_worker_dispatch_is_deterministic_and_idempotent() -> None:
    fabric, broker, executor = executor_with_worker()
    node = allocate_invocation(
        fabric,
        "AUTH:ROOT",
        ("graph",),
        operators(),
        budget=BUDGET,
    ).nodes[0]

    first = executor.ensure_dispatched(node.node_id, {"query": "alpha"})
    second = executor.ensure_dispatched(node.node_id, {"query": "alpha"})

    assert first.task_id == second.task_id
    assert first.task_commitment == second.task_commitment
    assert fabric.node(node.node_id).execution_started is True
    status = broker.task_result(first.task_id)
    assert status["state"] == "QUEUED"


def test_started_but_not_enqueued_node_is_recoverable() -> None:
    fabric, broker, executor = executor_with_worker()
    node = allocate_invocation(
        fabric,
        "AUTH:ROOT",
        ("graph",),
        operators(),
        budget=BUDGET,
    ).nodes[0]
    fabric.mark_started(node.node_id)

    record = executor.ensure_dispatched(node.node_id, {"query": "recover"})
    assert broker.task_result(record.task_id)["state"] == "QUEUED"


def test_same_deterministic_task_id_rejects_payload_drift() -> None:
    fabric, _, executor = executor_with_worker()
    node = allocate_invocation(
        fabric,
        "AUTH:ROOT",
        ("graph",),
        operators(),
        budget=BUDGET,
    ).nodes[0]

    executor.ensure_dispatched(node.node_id, {"query": "alpha"})
    with pytest.raises(ValueError, match="different content"):
        executor.ensure_dispatched(node.node_id, {"query": "beta"})


def test_frontier_separates_worker_and_local_core_nodes() -> None:
    fabric, _, executor = executor_with_worker()
    worker = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="WORKER",
        join_to_caller=False,
    )
    local = fabric.spawn(
        "AUTH:ROOT",
        "BEES",
        node_id="LOCAL",
        join_to_caller=False,
    )

    frontier = executor.frontier()
    assert worker.node_id in frontier["worker_ready"]
    assert local.node_id in frontier["local_ready"]
    assert "AUTH:ROOT" in frontier["local_ready"]


def test_worker_discovery_recursively_allocates_subnode_before_parent_completion() -> None:
    fabric, broker, executor = executor_with_worker()
    parent = allocate_invocation(
        fabric,
        "AUTH:ROOT",
        ("graph",),
        operators(),
        budget=BUDGET,
    ).nodes[0]
    executor.ensure_dispatched(parent.node_id, {"query": "find graph"})

    _claim_and_submit(
        broker,
        species="SPIDER",
        output={
            "answer": "graph candidate",
            DISCOVERY_KEY: {
                "schema": DISCOVERY_SCHEMA,
                "obligations": ["audit"],
            },
        },
    )
    receipt = executor.reconcile_node(parent.node_id)

    assert receipt["state"] == "SELF_COMPLETE"
    assert receipt["discovered_obligations"] == ["audit"]
    allocation = receipt["allocation"]
    assert allocation is not None
    child_id = allocation["node_ids"][0]
    child = fabric.node(child_id)
    assert child.species == "OWL"
    assert child.caller_id == parent.node_id
    assert parent.node_id not in fabric.closable_nodes()


def test_discovery_replay_after_crash_does_not_duplicate_children(monkeypatch) -> None:
    fabric, broker, executor = executor_with_worker()
    parent = allocate_invocation(
        fabric,
        "AUTH:ROOT",
        ("graph",),
        operators(),
        budget=BUDGET,
    ).nodes[0]
    executor.ensure_dispatched(parent.node_id, {"query": "find graph"})
    _claim_and_submit(
        broker,
        species="SPIDER",
        output={
            DISCOVERY_KEY: {
                "schema": DISCOVERY_SCHEMA,
                "obligations": ["audit"],
            }
        },
    )

    original = fabric.mark_self_complete

    def crash_after_allocation(*args, **kwargs):
        raise RuntimeError("simulated crash after child allocation")

    monkeypatch.setattr(fabric, "mark_self_complete", crash_after_allocation)
    with pytest.raises(RuntimeError, match="simulated crash"):
        executor.reconcile_node(parent.node_id)
    count_after_crash = fabric.receipt()["node_count"]

    monkeypatch.setattr(fabric, "mark_self_complete", original)
    receipt = executor.reconcile_node(parent.node_id)

    assert receipt["state"] == "SELF_COMPLETE"
    assert fabric.receipt()["node_count"] == count_after_crash


def test_malformed_worker_discovery_quarantines_source_fail_closed() -> None:
    fabric, broker, executor = executor_with_worker()
    node = allocate_invocation(
        fabric,
        "AUTH:ROOT",
        ("graph",),
        operators(),
        budget=BUDGET,
    ).nodes[0]
    executor.ensure_dispatched(node.node_id, {"query": "x"})
    _claim_and_submit(
        broker,
        species="SPIDER",
        output={
            DISCOVERY_KEY: {
                "schema": "WRONG",
                "obligations": ["audit"],
            }
        },
    )

    receipt = executor.reconcile_node(node.node_id)
    assert receipt["state"] == "QUARANTINED_INVALID_DISCOVERY"
    assert fabric.node(node.node_id).status == "QUARANTINED"


def test_local_role_uses_same_completion_contract_without_worker_queue() -> None:
    fabric, _, executor = executor_with_worker()
    node = fabric.spawn(
        "AUTH:ROOT",
        "BEES",
        node_id="BEES-LOCAL",
        join_to_caller=False,
    )

    result = executor.complete_local(node.node_id, {"coherence": "candidate"})

    assert result["state"] == "SELF_COMPLETE"
    assert fabric.node(node.node_id).self_complete is True
    assert fabric.node(node.node_id).result_commitment == result["result_commitment"]


def test_local_result_can_discover_recursive_worker_obligation() -> None:
    fabric, _, executor = executor_with_worker()
    local = fabric.spawn(
        "AUTH:ROOT",
        "BEES",
        node_id="BEES-LOCAL",
        join_to_caller=False,
    )

    result = executor.complete_local(
        local.node_id,
        {
            DISCOVERY_KEY: {
                "schema": DISCOVERY_SCHEMA,
                "obligations": ["graph"],
            }
        },
    )

    assert result["allocation"] is not None
    child_id = result["allocation"]["node_ids"][0]
    child = fabric.node(child_id)
    assert child.species == "SPIDER"
    assert child.caller_id == local.node_id


def test_settle_closes_completed_subtree_deepest_first_without_root_close() -> None:
    fabric, broker, executor = executor_with_worker()
    parent = allocate_invocation(
        fabric,
        "AUTH:ROOT",
        ("graph",),
        operators(),
        budget=BUDGET,
    ).nodes[0]
    executor.ensure_dispatched(parent.node_id, {"query": "graph"})
    _claim_and_submit(
        broker,
        species="SPIDER",
        output={
            DISCOVERY_KEY: {
                "schema": DISCOVERY_SCHEMA,
                "obligations": ["audit"],
            }
        },
    )
    first = executor.reconcile_node(parent.node_id)
    child_id = first["allocation"]["node_ids"][0]

    executor.ensure_dispatched(child_id, {"query": "audit"})
    _claim_and_submit(broker, species="OWL", output={"audit": "candidate"})
    executor.reconcile_node(child_id)

    settled = executor.settle_local_joins()

    assert child_id in settled["closed"]
    assert parent.node_id in settled["closed"]
    assert fabric.node(child_id).status == "CLOSED"
    assert fabric.node(parent.node_id).status == "CLOSED"
    assert fabric.node("AUTH:ROOT").status == "OPEN"
    assert settled["authority_root_closed"] is False


def test_execution_id_namespaces_deterministic_worker_tasks() -> None:
    fabric = OrchorbitalFabric()
    node = allocate_invocation(
        fabric,
        "AUTH:ROOT",
        ("graph",),
        operators(),
        budget=BUDGET,
    ).nodes[0]
    broker = WorkerBroker()

    first = OrchorbitalExecutor(
        execution_id="execution-A",
        fabric=fabric,
        broker=broker,
        operators=operators(),
        budget=BUDGET,
    )
    second = OrchorbitalExecutor(
        execution_id="execution-B",
        fabric=fabric,
        broker=broker,
        operators=operators(),
        budget=BUDGET,
    )

    assert first.deterministic_task_id(node.node_id) != second.deterministic_task_id(node.node_id)


def test_context_packet_is_committed_into_worker_task_and_reconstructs_losslessly() -> None:
    fabric = OrchorbitalFabric()
    broker = WorkerBroker()
    broker.register_worker("worker-1", ["SPIDER"], vector_width=2, max_batch=4)
    node = allocate_invocation(
        fabric,
        "AUTH:ROOT",
        ("graph",),
        operators(),
        budget=BUDGET,
    ).nodes[0]

    contexts = OrbitalContextStore(fabric)
    contexts.bind_root({"shared": "R" * 1000, "mode": "root"})
    contexts.inherit_from_caller(
        node.node_id,
        set_values={"mode": "spider", "local": "delta"},
    )
    executor = OrchorbitalExecutor(
        execution_id="ctx-exec",
        fabric=fabric,
        broker=broker,
        operators=operators(),
        budget=BUDGET,
        context_store=contexts,
    )

    record = executor.ensure_dispatched(node.node_id, {"query": "local-only"})
    lease = broker.claim("worker-1", species="SPIDER", limit=1)
    payload = lease["tasks"][0]["payload"]
    packet = payload[ORBITAL_CONTEXT_PACKET_KEY]
    decoded = apply_context_packet(packet)

    assert record.task_id == lease["tasks"][0]["task_id"]
    assert decoded["materialized_context"] == contexts.materialize(node.node_id)
    assert payload["input"] == {"query": "local-only"}


def test_missing_context_binding_fails_before_execution_start() -> None:
    fabric = OrchorbitalFabric()
    broker = WorkerBroker()
    node = allocate_invocation(
        fabric,
        "AUTH:ROOT",
        ("graph",),
        operators(),
        budget=BUDGET,
    ).nodes[0]
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root({"root": True})
    executor = OrchorbitalExecutor(
        execution_id="ctx-missing",
        fabric=fabric,
        broker=broker,
        operators=operators(),
        budget=BUDGET,
        context_store=contexts,
    )

    with pytest.raises(ValueError, match="node context is not bound"):
        executor.ensure_dispatched(node.node_id, {"query": "x"})

    assert fabric.node(node.node_id).execution_started is False


def test_context_store_from_different_fabric_is_rejected() -> None:
    fabric = OrchorbitalFabric()
    other = OrchorbitalFabric(root_id="OTHER:ROOT")
    contexts = OrbitalContextStore(other)

    with pytest.raises(ValueError, match="same fabric"):
        OrchorbitalExecutor(
            execution_id="bad-context-store",
            fabric=fabric,
            broker=WorkerBroker(),
            operators=operators(),
            budget=BUDGET,
            context_store=contexts,
        )
