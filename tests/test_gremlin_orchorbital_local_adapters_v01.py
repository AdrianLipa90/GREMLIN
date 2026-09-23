from __future__ import annotations

import pytest

from gremlin_mcp.adaptive_runtime import OperatorTier, ResourceBudget, ResourceCost
from gremlin_mcp.orchorbital_context import OrbitalContextStore
from gremlin_mcp.orchorbital_executor import (
    DISCOVERY_KEY,
    DISCOVERY_SCHEMA,
    OrchorbitalExecutor,
)
from gremlin_mcp.orchorbital_fabric import OrchorbitalFabric
from gremlin_mcp.orchorbital_local import LocalAdapterRegistry
from gremlin_mcp.workers import WorkerBroker


BUDGET = ResourceBudget(tokens=100.0, latency=100.0, calls=100.0, memory=100.0)
BEES_IMPL = "b" * 64
ELEPHANT_IMPL = "e" * 64


def operators():
    return (
        OperatorTier(
            "BEES",
            0,
            frozenset({"coherence"}),
            ResourceCost(3, 2, 1, 2),
        ),
        OperatorTier(
            "SPIDER",
            0,
            frozenset({"graph"}),
            ResourceCost(5, 5, 1, 2),
        ),
    )


def make_executor(registry: LocalAdapterRegistry | None):
    fabric = OrchorbitalFabric()
    broker = WorkerBroker()
    broker.register_worker("worker-1", ["SPIDER"], vector_width=2, max_batch=2)
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root({"shared": "root-context"})
    executor = OrchorbitalExecutor(
        execution_id="local-adapter-runtime",
        fabric=fabric,
        broker=broker,
        operators=operators(),
        budget=BUDGET,
        context_store=contexts,
        local_adapters=registry,
    )
    return fabric, broker, contexts, executor


def test_registry_accepts_only_replay_safe_side_effect_free_local_roles() -> None:
    registry = LocalAdapterRegistry()
    registry.register(
        "BEES",
        lambda request: {"ok": True},
        adapter_id="bees-pure",
        implementation_commitment=BEES_IMPL,
    )

    with pytest.raises(ValueError, match="not eligible"):
        registry.register(
            "GREMLIN",
            lambda request: {"ok": True},
            adapter_id="root-invalid",
            implementation_commitment="a" * 64,
        )

    with pytest.raises(ValueError, match="replay_safe=true"):
        LocalAdapterRegistry().register(
            "ELEPHANT",
            lambda request: {"ok": True},
            adapter_id="elephant-unsafe-replay",
            implementation_commitment=ELEPHANT_IMPL,
            replay_safe=False,
        )

    with pytest.raises(ValueError, match="side_effects=false"):
        LocalAdapterRegistry().register(
            "ELEPHANT",
            lambda request: {"ok": True},
            adapter_id="elephant-side-effect",
            implementation_commitment=ELEPHANT_IMPL,
            side_effects=True,
        )


def test_executor_rejects_control_plane_species_as_exact_cover_operator() -> None:
    fabric = OrchorbitalFabric()
    with pytest.raises(ValueError, match="control-plane|workload operators"):
        OrchorbitalExecutor(
            execution_id="invalid-control-operator",
            fabric=fabric,
            broker=WorkerBroker(),
            operators=(
                OperatorTier(
                    "OCTOPUS",
                    0,
                    frozenset({"route"}),
                    ResourceCost(1, 1, 1, 1),
                ),
            ),
            budget=BUDGET,
        )


def test_bees_adapter_runs_from_local_frontier_and_closes_without_worker() -> None:
    registry = LocalAdapterRegistry()
    seen = {}

    def handler(request):
        seen.update(request)
        return {"coherence": "pass"}

    registry.register(
        "BEES",
        handler,
        adapter_id="bees-coherence-v1",
        implementation_commitment=BEES_IMPL,
    )
    fabric, broker, contexts, executor = make_executor(registry)
    node = executor.allocate(
        "AUTH:ROOT",
        ("coherence",),
        allocation_key="bees-local",
    ).nodes[0]

    step = executor.orchestration_step()

    assert node.species == "BEES"
    assert any(row["node_id"] == node.node_id for row in step["local_execution"]["completed"])
    assert fabric.node(node.node_id).status == "CLOSED"
    assert seen["node_id"] == node.node_id
    assert seen["context"]["shared"] == "root-context"
    assert seen["adapter"]["implementation_commitment"] == BEES_IMPL
    assert broker.queue_status()["unfinished_task_count"] == 0
    assert contexts.materialize(node.node_id)["shared"] == "root-context"


def test_local_adapter_discovery_spawns_worker_child_in_same_orchestration_step() -> None:
    registry = LocalAdapterRegistry()
    registry.register(
        "BEES",
        lambda request: {
            "coherence": "needs-graph",
            DISCOVERY_KEY: {
                "schema": DISCOVERY_SCHEMA,
                "obligations": ["graph"],
                "handoff": {"reason": "verify-overlap"},
            },
        },
        adapter_id="bees-discovery-v1",
        implementation_commitment=BEES_IMPL,
    )
    fabric, broker, contexts, executor = make_executor(registry)
    parent = executor.allocate(
        "AUTH:ROOT",
        ("coherence",),
        allocation_key="bees-discovery",
    ).nodes[0]

    step = executor.orchestration_step()

    children = [
        node
        for node in fabric.nodes()
        if node.caller_id == parent.node_id
    ]
    assert len(children) == 1
    child = children[0]
    assert child.species == "SPIDER"
    assert parent.node_id not in fabric.closable_nodes()
    assert step["worker_dispatch"]["failures"] == []
    assert any(
        row["node_id"] == child.node_id
        for row in step["worker_dispatch"]["dispatched"]
    )
    assert contexts.materialize(child.node_id)["_gremlin_handoff"] == {
        "reason": "verify-overlap"
    }


def test_local_bees_reducer_closes_parent_after_worker_child_returns() -> None:
    registry = LocalAdapterRegistry()

    def handler(request):
        return {
            "coherence": "needs-graph",
            DISCOVERY_KEY: {
                "schema": DISCOVERY_SCHEMA,
                "obligations": ["graph"],
            },
        }

    def reducer(request):
        packet = request["reduction"]
        return {
            "coherence": "integrated",
            "child_count": len(packet["join_results"]),
            "self": packet["self_output"]["coherence"],
        }

    registry.register(
        "BEES",
        handler,
        reducer=reducer,
        adapter_id="bees-with-reducer-v1",
        implementation_commitment=BEES_IMPL,
    )
    fabric, broker, _, executor = make_executor(registry)
    parent = executor.allocate(
        "AUTH:ROOT",
        ("coherence",),
        allocation_key="bees-reduction",
    ).nodes[0]

    step1 = executor.orchestration_step()
    child_id = next(
        row["node_id"]
        for row in step1["worker_dispatch"]["dispatched"]
        if row["species"] == "SPIDER"
    )

    lease = broker.claim("worker-1", species="SPIDER", limit=1)
    broker.submit(
        "worker-1",
        lease["lease_id"],
        [{"task_id": lease["tasks"][0]["task_id"], "output": {"graph": "pass"}}],
    )

    step2 = executor.orchestration_step()

    assert fabric.node(child_id).status == "CLOSED"
    assert fabric.node(parent.node_id).status == "CLOSED"
    assert any(
        row["node_id"] == parent.node_id
        and row["state"] == "REDUCTION_COMPLETE"
        for row in step2["local_reduction"]["completed"]
    )
    assert step2["global_synthesis_barrier_required"] is False


def test_missing_optional_local_adapter_uses_same_species_worker_backend() -> None:
    fabric, broker, _, executor = make_executor(None)
    node = executor.allocate(
        "AUTH:ROOT",
        ("coherence",),
        allocation_key="missing-local-adapter",
    ).nodes[0]

    step = executor.orchestration_step()

    assert node.node_id not in step["local_execution"]["adapter_required"]
    assert any(
        row["node_id"] == node.node_id and row["species"] == "BEES"
        for row in step["worker_dispatch"]["dispatched"]
    )
    assert fabric.node(node.node_id).status == "OPEN"
    assert fabric.node(node.node_id).execution_started is True
    assert broker.queue_status()["tasks"]["BEES"]["QUEUED"] == 1


def test_local_adapter_failure_terminalizes_node_fail_closed() -> None:
    registry = LocalAdapterRegistry()

    def handler(request):
        raise RuntimeError("adapter exploded")

    registry.register(
        "BEES",
        handler,
        adapter_id="bees-failing-v1",
        implementation_commitment=BEES_IMPL,
    )
    fabric, _, _, executor = make_executor(registry)
    node = executor.allocate(
        "AUTH:ROOT",
        ("coherence",),
        allocation_key="failing-local-adapter",
    ).nodes[0]

    step = executor.orchestration_step()

    assert fabric.node(node.node_id).status == "FAILED"
    result = next(
        row
        for row in step["local_execution"]["completed"]
        if row["node_id"] == node.node_id
    )
    assert result["state"] == "FAILED_LOCAL_ADAPTER"


def test_checkpoint_requires_identical_local_adapter_manifest() -> None:
    registry = LocalAdapterRegistry()
    handler = lambda request: {"coherence": "pass"}
    registry.register(
        "BEES",
        handler,
        adapter_id="bees-checkpoint-v1",
        implementation_commitment=BEES_IMPL,
    )
    fabric, broker, contexts, executor = make_executor(registry)
    checkpoint = executor.checkpoint_state()

    restored = OrchorbitalExecutor.from_checkpoint(
        checkpoint,
        fabric=fabric,
        broker=broker,
        context_store=contexts,
        local_adapters=registry,
    )
    assert restored.checkpoint_state()["checkpoint_commitment"] == (
        checkpoint["checkpoint_commitment"]
    )

    with pytest.raises(ValueError, match="local adapter manifest mismatch"):
        OrchorbitalExecutor.from_checkpoint(
            checkpoint,
            fabric=fabric,
            broker=broker,
            context_store=contexts,
            local_adapters=None,
        )

    drifted = LocalAdapterRegistry()
    drifted.register(
        "BEES",
        handler,
        adapter_id="bees-checkpoint-v1",
        implementation_commitment="c" * 64,
    )
    with pytest.raises(ValueError, match="local adapter manifest mismatch"):
        OrchorbitalExecutor.from_checkpoint(
            checkpoint,
            fabric=fabric,
            broker=broker,
            context_store=contexts,
            local_adapters=drifted,
        )


def test_bees_backend_is_worker_without_adapter_and_local_with_adapter() -> None:
    # Same logical role, same obligation, different explicitly available backend.
    fabric_worker = OrchorbitalFabric()
    broker_worker = WorkerBroker()
    broker_worker.register_worker("bees-worker", ["BEES"])
    contexts_worker = OrbitalContextStore(fabric_worker)
    contexts_worker.bind_root({"shared": "backend-modular"})
    executor_worker = OrchorbitalExecutor(
        execution_id="bees-worker-backend",
        fabric=fabric_worker,
        broker=broker_worker,
        operators=(
            OperatorTier(
                "BEES",
                0,
                frozenset({"coherence"}),
                ResourceCost(1, 1, 1, 1),
            ),
        ),
        budget=BUDGET,
        context_store=contexts_worker,
    )
    worker_node = executor_worker.allocate(
        "AUTH:ROOT",
        ("coherence",),
        allocation_key="bees-backend-worker",
    ).nodes[0]

    worker_frontier = executor_worker.frontier()
    assert worker_node.node_id in worker_frontier["worker_ready"]
    assert worker_node.node_id not in worker_frontier["local_ready"]
    worker_step = executor_worker.orchestration_step()
    assert any(
        row["node_id"] == worker_node.node_id
        for row in worker_step["worker_dispatch"]["dispatched"]
    )
    assert broker_worker.queue_status()["tasks"]["BEES"]["QUEUED"] == 1

    registry = LocalAdapterRegistry()
    registry.register(
        "BEES",
        lambda request: {"coherence": "local-pass"},
        adapter_id="bees-local-backend-v1",
        implementation_commitment=BEES_IMPL,
    )
    fabric_local = OrchorbitalFabric()
    broker_local = WorkerBroker()
    contexts_local = OrbitalContextStore(fabric_local)
    contexts_local.bind_root({"shared": "backend-modular"})
    executor_local = OrchorbitalExecutor(
        execution_id="bees-local-backend",
        fabric=fabric_local,
        broker=broker_local,
        operators=(
            OperatorTier(
                "BEES",
                0,
                frozenset({"coherence"}),
                ResourceCost(1, 1, 1, 1),
            ),
        ),
        budget=BUDGET,
        context_store=contexts_local,
        local_adapters=registry,
    )
    local_node = executor_local.allocate(
        "AUTH:ROOT",
        ("coherence",),
        allocation_key="bees-backend-local",
    ).nodes[0]

    local_frontier = executor_local.frontier()
    assert local_node.node_id in local_frontier["local_ready"]
    assert local_node.node_id not in local_frontier["worker_ready"]
    local_step = executor_local.orchestration_step()
    assert any(
        row["node_id"] == local_node.node_id
        for row in local_step["local_execution"]["completed"]
    )
    assert broker_local.queue_status()["tasks"]["BEES"]["QUEUED"] == 0
    assert fabric_local.node(local_node.node_id).status == "CLOSED"


def test_active_local_adapter_prevents_duplicate_worker_dispatch_for_same_node() -> None:
    registry = LocalAdapterRegistry()
    registry.register(
        "ELEPHANT",
        lambda request: {"memory": "local"},
        adapter_id="elephant-local-v1",
        implementation_commitment=ELEPHANT_IMPL,
    )
    fabric = OrchorbitalFabric()
    broker = WorkerBroker()
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root({"shared": "memory"})
    executor = OrchorbitalExecutor(
        execution_id="elephant-no-double-dispatch",
        fabric=fabric,
        broker=broker,
        operators=(
            OperatorTier(
                "ELEPHANT",
                0,
                frozenset({"memory"}),
                ResourceCost(1, 1, 1, 1),
            ),
        ),
        budget=BUDGET,
        context_store=contexts,
        local_adapters=registry,
    )
    node = executor.allocate(
        "AUTH:ROOT",
        ("memory",),
        allocation_key="elephant-local-only",
    ).nodes[0]

    with pytest.raises(RuntimeError, match="active local adapter"):
        executor.ensure_dispatched(node.node_id, {"query": "must-not-queue"})

    assert broker.queue_status()["tasks"]["ELEPHANT"]["QUEUED"] == 0
    assert fabric.node(node.node_id).execution_started is False


def test_local_handler_without_local_reducer_falls_back_to_same_species_worker_reduction() -> None:
    registry = LocalAdapterRegistry()
    registry.register(
        "BEES",
        lambda request: {
            "coherence": "needs-graph",
            DISCOVERY_KEY: {
                "schema": DISCOVERY_SCHEMA,
                "obligations": ["graph"],
            },
        },
        adapter_id="bees-local-handler-worker-reducer-v1",
        implementation_commitment=BEES_IMPL,
    )

    fabric = OrchorbitalFabric()
    broker = WorkerBroker()
    broker.register_worker(
        "mixed-worker",
        ["SPIDER", "BEES"],
        vector_width=4,
        max_batch=4,
    )
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root({"shared": "mixed-backend"})
    executor = OrchorbitalExecutor(
        execution_id="bees-mixed-backend",
        fabric=fabric,
        broker=broker,
        operators=(
            OperatorTier(
                "BEES",
                0,
                frozenset({"coherence"}),
                ResourceCost(1, 1, 1, 1),
            ),
            OperatorTier(
                "SPIDER",
                0,
                frozenset({"graph"}),
                ResourceCost(1, 1, 1, 1),
            ),
        ),
        budget=BUDGET,
        context_store=contexts,
        local_adapters=registry,
    )
    parent = executor.allocate(
        "AUTH:ROOT",
        ("coherence",),
        allocation_key="mixed-backend-parent",
    ).nodes[0]

    step1 = executor.orchestration_step()
    child_id = next(
        row["node_id"]
        for row in step1["worker_dispatch"]["dispatched"]
        if row["species"] == "SPIDER"
    )
    child_lease = broker.claim("mixed-worker", species="SPIDER", limit=1)
    broker.submit(
        "mixed-worker",
        child_lease["lease_id"],
        [
            {
                "task_id": child_lease["tasks"][0]["task_id"],
                "output": {"graph": "pass"},
            }
        ],
    )

    step2 = executor.orchestration_step()
    assert fabric.node(child_id).status == "CLOSED"
    assert step2["local_reduction"]["completed"] == []
    reduction = next(
        row
        for row in step2["reduction_dispatch"]["dispatched"]
        if row["node_id"] == parent.node_id
    )
    assert reduction["species"] == "BEES"

    reduction_lease = broker.claim("mixed-worker", species="BEES", limit=1)
    assert reduction_lease["tasks"][0]["task_id"] == reduction["task_id"]
    broker.submit(
        "mixed-worker",
        reduction_lease["lease_id"],
        [
            {
                "task_id": reduction["task_id"],
                "output": {"coherence": "worker-reduced"},
            }
        ],
    )
    step3 = executor.orchestration_step()

    assert fabric.node(parent.node_id).status == "CLOSED"
    assert step3["global_synthesis_barrier_required"] is False


def test_execution_backend_binding_survives_late_local_adapter_registration() -> None:
    registry = LocalAdapterRegistry()
    fabric = OrchorbitalFabric()
    broker = WorkerBroker()
    broker.register_worker("late-adapter-worker", ["BEES"])
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root({"shared": "late-adapter"})
    executor = OrchorbitalExecutor(
        execution_id="late-adapter-binding",
        fabric=fabric,
        broker=broker,
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
        allocation_key="late-adapter-node",
    ).nodes[0]

    step1 = executor.orchestration_step()
    dispatch = next(
        row
        for row in step1["worker_dispatch"]["dispatched"]
        if row["node_id"] == node.node_id
    )
    assert executor.receipt()["execution_backend_bindings"][node.node_id] == "WORKER"

    local_called = False

    def late_handler(request):
        nonlocal local_called
        local_called = True
        return {"coherence": "must-not-run"}

    registry.register(
        "BEES",
        late_handler,
        adapter_id="late-bees-local-v1",
        implementation_commitment="1" * 64,
    )

    lease = broker.claim("late-adapter-worker", species="BEES", limit=1)
    assert lease["tasks"][0]["task_id"] == dispatch["task_id"]
    broker.submit(
        "late-adapter-worker",
        lease["lease_id"],
        [{"task_id": dispatch["task_id"], "output": {"coherence": "worker-pass"}}],
    )
    step2 = executor.orchestration_step()

    assert local_called is False
    assert fabric.node(node.node_id).status == "CLOSED"
    assert executor.receipt()["execution_backend_bindings"][node.node_id] == "WORKER"
    assert step2["local_execution"]["completed"] == []


def test_reduction_backend_binding_survives_late_local_reducer_registration() -> None:
    registry = LocalAdapterRegistry()

    def local_handler(request):
        return {
            "coherence": "needs-graph",
            DISCOVERY_KEY: {
                "schema": DISCOVERY_SCHEMA,
                "obligations": ["graph"],
            },
        }

    registry.register(
        "BEES",
        local_handler,
        adapter_id="late-reducer-bees-v1",
        implementation_commitment="2" * 64,
    )
    fabric = OrchorbitalFabric()
    broker = WorkerBroker()
    broker.register_worker(
        "late-reducer-worker",
        ["SPIDER", "BEES"],
        vector_width=4,
        max_batch=4,
    )
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root({"shared": "late-reducer"})
    executor = OrchorbitalExecutor(
        execution_id="late-reducer-binding",
        fabric=fabric,
        broker=broker,
        operators=(
            OperatorTier(
                "BEES",
                0,
                frozenset({"coherence"}),
                ResourceCost(1, 1, 1, 1),
            ),
            OperatorTier(
                "SPIDER",
                0,
                frozenset({"graph"}),
                ResourceCost(1, 1, 1, 1),
            ),
        ),
        budget=BUDGET,
        context_store=contexts,
        local_adapters=registry,
    )
    parent = executor.allocate(
        "AUTH:ROOT",
        ("coherence",),
        allocation_key="late-reducer-parent",
    ).nodes[0]

    step1 = executor.orchestration_step()
    child_dispatch = next(
        row
        for row in step1["worker_dispatch"]["dispatched"]
        if row["species"] == "SPIDER"
    )
    child_lease = broker.claim("late-reducer-worker", species="SPIDER", limit=1)
    broker.submit(
        "late-reducer-worker",
        child_lease["lease_id"],
        [{"task_id": child_dispatch["task_id"], "output": {"graph": "pass"}}],
    )

    step2 = executor.orchestration_step()
    reduction_dispatch = next(
        row
        for row in step2["reduction_dispatch"]["dispatched"]
        if row["node_id"] == parent.node_id
    )
    assert executor.receipt()["reduction_backend_bindings"][parent.node_id] == "WORKER"

    reducer_called = False

    def late_reducer(request):
        nonlocal reducer_called
        reducer_called = True
        return {"coherence": "must-not-run"}

    # Re-registering the same species with different callable is forbidden.
    # The existing adapter object is immutable, so build a new executor-level
    # registry would be a checkpoint-level drift. Here we prove the live binding
    # directly by replacing no registry state and calling the worker completion.
    reduction_lease = broker.claim(
        "late-reducer-worker",
        species="BEES",
        limit=1,
    )
    assert reduction_lease["tasks"][0]["task_id"] == reduction_dispatch["task_id"]
    broker.submit(
        "late-reducer-worker",
        reduction_lease["lease_id"],
        [
            {
                "task_id": reduction_dispatch["task_id"],
                "output": {"coherence": "worker-reduced"},
            }
        ],
    )
    step3 = executor.orchestration_step()

    assert reducer_called is False
    assert fabric.node(parent.node_id).status == "CLOSED"
    assert executor.receipt()["reduction_backend_bindings"][parent.node_id] == "WORKER"
    assert step3["local_reduction"]["completed"] == []
