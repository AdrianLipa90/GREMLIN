from __future__ import annotations

from copy import deepcopy
import json
import sqlite3

import pytest

from gremlin_mcp.adaptive_runtime import OperatorTier, ResourceBudget, ResourceCost
from gremlin_mcp.orchorbital_context import OrbitalContextStore
from gremlin_mcp.orchorbital_executor import (
    DISCOVERY_KEY,
    DISCOVERY_SCHEMA,
    REDUCTION_TASK_KEY,
    OrchorbitalExecutor,
)
from gremlin_mcp.orchorbital_fabric import OrchorbitalFabric
from gremlin_mcp.orchorbital_local import LocalAdapterRegistry
from gremlin_mcp.orchorbital_persistence import (
    DurableOrchorbitalRuntime,
    SQLiteOrchorbitalRuntimeStore,
    build_runtime_checkpoint,
    restore_runtime_checkpoint,
)
from gremlin_mcp.persistent_workers import PersistentWorkerBroker
from gremlin_mcp.workers import WorkerBroker


BUDGET = ResourceBudget(
    tokens=100.0,
    latency=100.0,
    calls=100.0,
    memory=100.0,
)


def operators():
    return (
        OperatorTier(
            "SPIDER",
            0,
            frozenset({"graph"}),
            ResourceCost(5, 5, 1, 2),
        ),
        OperatorTier(
            "OWL",
            0,
            frozenset({"audit"}),
            ResourceCost(4, 4, 1, 2),
        ),
    )


def _submit_one(broker, *, species: str, output: object) -> str:
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


def _runtime_with_persistent_worker(worker_path):
    broker = PersistentWorkerBroker(str(worker_path))
    broker.register_worker(
        "worker-1",
        ["SPIDER", "OWL"],
        vector_width=4,
        max_batch=8,
    )
    fabric = OrchorbitalFabric()
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root(
        {
            "shared_problem": "restart-safe-orbital-flow",
            "memory_projection": {"scope": "candidate"},
        }
    )
    executor = OrchorbitalExecutor(
        execution_id="restart-flow",
        fabric=fabric,
        broker=broker,
        operators=operators(),
        budget=BUDGET,
        context_store=contexts,
    )
    return broker, fabric, contexts, executor


def test_runtime_wal_restores_mid_orbit_and_finishes_parent_reduction(tmp_path) -> None:
    worker_path = tmp_path / "worker.sqlite3"
    runtime_path = tmp_path / "orchorbital.sqlite3"

    broker, fabric, contexts, executor = _runtime_with_persistent_worker(
        worker_path
    )
    parent = executor.allocate(
        "AUTH:ROOT",
        ("graph",),
        allocation_key="restart-root",
    ).nodes[0]
    executor.ensure_dispatched(parent.node_id, {"query": "graph"})

    _submit_one(
        broker,
        species="SPIDER",
        output={
            "graph": "candidate",
            DISCOVERY_KEY: {
                "schema": DISCOVERY_SCHEMA,
                "obligations": ["audit"],
            },
        },
    )
    step1 = executor.orchestration_step()
    child_id = step1["worker_dispatch"]["dispatched"][0]["node_id"]

    _submit_one(
        broker,
        species="OWL",
        output={"audit": "candidate-pass"},
    )
    step2 = executor.orchestration_step()
    assert fabric.node(child_id).status == "CLOSED"
    reduction_rows = step2["reduction_dispatch"]["dispatched"]
    assert len(reduction_rows) == 1
    reduction_task_id = reduction_rows[0]["task_id"]
    assert broker.task_result(reduction_task_id)["state"] == "QUEUED"

    topology_before = fabric.topology_commitment()
    parent_context_before = contexts.materialize(parent.node_id)
    child_context_before = contexts.materialize(child_id)
    runtime_store = SQLiteOrchorbitalRuntimeStore(runtime_path)
    save_receipt = runtime_store.save(executor)
    checkpoint = runtime_store.load_checkpoint("restart-flow")
    assert save_receipt["journal_mode"] == "WAL"
    assert checkpoint["fabric_topology_commitment"] == topology_before

    runtime_store.close()
    broker.close()

    broker2 = PersistentWorkerBroker(str(worker_path))
    runtime_store2 = SQLiteOrchorbitalRuntimeStore(runtime_path)
    restored = runtime_store2.restore("restart-flow", broker=broker2)

    assert restored.fabric.topology_commitment() == topology_before
    assert restored.context_store is not None
    assert restored.context_store.materialize(parent.node_id) == parent_context_before
    assert restored.context_store.materialize(child_id) == child_context_before
    assert restored.deterministic_reduction_task_id(parent.node_id) == reduction_task_id
    assert broker2.task_result(reduction_task_id)["state"] == "QUEUED"

    replay = restored.ensure_reduction_dispatched(parent.node_id)
    assert replay.task_id == reduction_task_id
    assert broker2.task_result(reduction_task_id)["state"] == "QUEUED"

    reduction_lease = broker2.claim(
        "worker-1",
        species="SPIDER",
        limit=1,
    )
    assert reduction_lease["tasks"][0]["task_id"] == reduction_task_id
    reduction_packet = reduction_lease["tasks"][0]["payload"]["input"][
        REDUCTION_TASK_KEY
    ]
    assert reduction_packet["join_results"][0]["resolved_node_id"] == child_id
    assert reduction_packet["join_results"][0]["output"] == {
        "audit": "candidate-pass"
    }

    broker2.submit(
        "worker-1",
        reduction_lease["lease_id"],
        [
            {
                "task_id": reduction_task_id,
                "status": "CANDIDATE",
                "output": {
                    "graph": "candidate",
                    "audit": "integrated-after-restart",
                },
            }
        ],
    )
    step3 = restored.orchestration_step()

    assert restored.fabric.node(parent.node_id).status == "CLOSED"
    assert parent.node_id in step3["settle_after_reductions"]["closed"]
    assert restored.fabric.node("AUTH:ROOT").status == "OPEN"
    assert step3["global_synthesis_barrier_required"] is False

    runtime_store2.close()
    broker2.close()


def test_runtime_checkpoint_round_trip_is_commitment_exact_without_context() -> None:
    fabric = OrchorbitalFabric()
    broker = WorkerBroker()
    executor = OrchorbitalExecutor(
        execution_id="no-context",
        fabric=fabric,
        broker=broker,
        operators=operators(),
        budget=BUDGET,
    )

    checkpoint = build_runtime_checkpoint(executor)
    restored = restore_runtime_checkpoint(checkpoint, broker=broker)
    replay = build_runtime_checkpoint(restored)

    assert restored.fabric.topology_commitment() == fabric.topology_commitment()
    assert restored.context_store is None
    assert replay["fabric_checkpoint_commitment"] == checkpoint[
        "fabric_checkpoint_commitment"
    ]
    assert replay["executor_checkpoint_commitment"] == checkpoint[
        "executor_checkpoint_commitment"
    ]
    assert replay["checkpoint_commitment"] == checkpoint["checkpoint_commitment"]


def test_runtime_store_tamper_fails_closed_before_restore(tmp_path) -> None:
    runtime_path = tmp_path / "tamper.sqlite3"
    fabric = OrchorbitalFabric()
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root({"secret": "candidate"})
    executor = OrchorbitalExecutor(
        execution_id="tamper-flow",
        fabric=fabric,
        broker=WorkerBroker(),
        operators=operators(),
        budget=BUDGET,
        context_store=contexts,
    )

    store = SQLiteOrchorbitalRuntimeStore(runtime_path)
    store.save(executor)
    store.close()

    connection = sqlite3.connect(str(runtime_path))
    row = connection.execute(
        """
        SELECT data_json
        FROM runtime_checkpoints
        WHERE execution_id = ?
        """,
        ("tamper-flow",),
    ).fetchone()
    assert row is not None
    payload = json.loads(row[0])
    payload["fabric_topology_commitment"] = "0" * 64
    connection.execute(
        """
        UPDATE runtime_checkpoints
        SET data_json = ?
        WHERE execution_id = ?
        """,
        (
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ),
            "tamper-flow",
        ),
    )
    connection.commit()
    connection.close()

    reopened = SQLiteOrchorbitalRuntimeStore(runtime_path)
    with pytest.raises(RuntimeError, match="checkpoint commitment mismatch"):
        reopened.load_checkpoint("tamper-flow")
    reopened.close()


def test_restore_fails_closed_when_completed_worker_result_is_missing() -> None:
    broker = WorkerBroker()
    broker.register_worker("worker-1", ["SPIDER"])
    fabric = OrchorbitalFabric()
    executor = OrchorbitalExecutor(
        execution_id="broker-binding",
        fabric=fabric,
        broker=broker,
        operators=operators(),
        budget=BUDGET,
    )
    node = executor.allocate(
        "AUTH:ROOT",
        ("graph",),
        allocation_key="broker-binding-root",
    ).nodes[0]
    executor.ensure_dispatched(node.node_id, {"query": "graph"})
    _submit_one(
        broker,
        species="SPIDER",
        output={"graph": "done"},
    )
    executor.reconcile_node(node.node_id)
    checkpoint = build_runtime_checkpoint(executor)

    empty_broker = WorkerBroker()
    empty_broker.register_worker("worker-1", ["SPIDER"])
    with pytest.raises(ValueError, match="unknown task_id"):
        restore_runtime_checkpoint(
            deepcopy(checkpoint),
            broker=empty_broker,
        )


def test_durable_runtime_checkpoints_after_each_orchestration_step(tmp_path) -> None:
    worker_path = tmp_path / "worker-step.sqlite3"
    runtime_path = tmp_path / "runtime-step.sqlite3"

    broker, fabric, _, executor = _runtime_with_persistent_worker(worker_path)
    parent = executor.allocate(
        "AUTH:ROOT",
        ("graph",),
        allocation_key="durable-step-root",
    ).nodes[0]
    executor.ensure_dispatched(parent.node_id, {"query": "graph"})
    _submit_one(
        broker,
        species="SPIDER",
        output={
            "graph": "candidate",
            DISCOVERY_KEY: {
                "schema": DISCOVERY_SCHEMA,
                "obligations": ["audit"],
            },
        },
    )

    store = SQLiteOrchorbitalRuntimeStore(runtime_path)
    durable = DurableOrchorbitalRuntime(executor, store)
    receipt = durable.orchestration_step()

    assert receipt["checkpoint_after_step"] is True
    assert receipt["checkpoint"]["fabric_topology_commitment"] == (
        executor.fabric.topology_commitment()
    )
    persisted = store.load_checkpoint("restart-flow")
    assert persisted["fabric_topology_commitment"] == (
        executor.fabric.topology_commitment()
    )

    child_id = receipt["step"]["worker_dispatch"]["dispatched"][0]["node_id"]
    broker.close()
    store.close()

    broker2 = PersistentWorkerBroker(str(worker_path))
    store2 = SQLiteOrchorbitalRuntimeStore(runtime_path)
    restored = DurableOrchorbitalRuntime.restore(
        store2,
        "restart-flow",
        broker=broker2,
    )

    assert restored.execution_id == "restart-flow"
    assert restored.executor.fabric.node(parent.node_id).self_complete is True
    assert restored.executor.fabric.node(child_id).status == "OPEN"
    assert restored.executor.fabric.topology_commitment() == persisted[
        "fabric_topology_commitment"
    ]

    store2.close()
    broker2.close()


def test_runtime_store_restore_requires_matching_local_adapter_manifest(tmp_path) -> None:
    runtime_path = tmp_path / "orchorbital-local-adapter.sqlite3"
    fabric = OrchorbitalFabric()
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root({"shared": "local-adapter-runtime"})
    registry = LocalAdapterRegistry()
    handler = lambda request: {"coherence": "pass"}
    registry.register(
        "BEES",
        handler,
        adapter_id="bees-runtime-store-v1",
        implementation_commitment="b" * 64,
    )
    executor = OrchorbitalExecutor(
        execution_id="adapter-store-flow",
        fabric=fabric,
        broker=WorkerBroker(),
        operators=(
            OperatorTier(
                "BEES",
                0,
                frozenset({"coherence"}),
                ResourceCost(1, 1, 1, 1),
            ),
        ),
        budget=BUDGET,
        context_store=contexts,
        local_adapters=registry,
    )
    node = executor.allocate(
        "AUTH:ROOT",
        ("coherence",),
        allocation_key="adapter-store-node",
    ).nodes[0]
    executor.orchestration_step()
    assert fabric.node(node.node_id).status == "CLOSED"

    store = SQLiteOrchorbitalRuntimeStore(runtime_path)
    try:
        store.save(executor)

        restored = store.restore(
            "adapter-store-flow",
            broker=WorkerBroker(),
            local_adapters=registry,
        )
        assert restored.local_adapters is registry
        assert restored.checkpoint_state()["local_adapter_manifest"] == (
            executor.checkpoint_state()["local_adapter_manifest"]
        )

        with pytest.raises(ValueError, match="local adapter manifest mismatch"):
            store.restore(
                "adapter-store-flow",
                broker=WorkerBroker(),
                local_adapters=None,
            )

        drifted = LocalAdapterRegistry()
        drifted.register(
            "BEES",
            handler,
            adapter_id="bees-runtime-store-v1",
            implementation_commitment="c" * 64,
        )
        with pytest.raises(ValueError, match="local adapter manifest mismatch"):
            store.restore(
                "adapter-store-flow",
                broker=WorkerBroker(),
                local_adapters=drifted,
            )
    finally:
        store.close()


def test_durable_runtime_restore_forwards_local_adapter_registry(tmp_path) -> None:
    runtime_path = tmp_path / "durable-local-adapter.sqlite3"
    fabric = OrchorbitalFabric()
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root({"shared": "durable-local"})

    registry = LocalAdapterRegistry()
    registry.register(
        "BEES",
        lambda request: {"coherence": "pass"},
        adapter_id="bees-durable-v1",
        implementation_commitment="d" * 64,
    )
    executor = OrchorbitalExecutor(
        execution_id="durable-local-flow",
        fabric=fabric,
        broker=WorkerBroker(),
        operators=(
            OperatorTier(
                "BEES",
                0,
                frozenset({"coherence"}),
                ResourceCost(1, 1, 1, 1),
            ),
        ),
        budget=BUDGET,
        context_store=contexts,
        local_adapters=registry,
    )
    node = executor.allocate(
        "AUTH:ROOT",
        ("coherence",),
        allocation_key="durable-local-node",
    ).nodes[0]
    executor.orchestration_step()
    assert fabric.node(node.node_id).status == "CLOSED"

    store = SQLiteOrchorbitalRuntimeStore(runtime_path)
    try:
        store.save(executor)
        restored = DurableOrchorbitalRuntime.restore(
            store,
            "durable-local-flow",
            broker=WorkerBroker(),
            local_adapters=registry,
        )
        assert restored.executor.local_adapters is registry

        with pytest.raises(ValueError, match="local adapter manifest mismatch"):
            DurableOrchorbitalRuntime.restore(
                store,
                "durable-local-flow",
                broker=WorkerBroker(),
                local_adapters=None,
            )
    finally:
        store.close()
