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
    assert broker.queue_status()["queued"] == 0
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


def test_missing_local_adapter_is_reported_without_silent_fallback() -> None:
    fabric, broker, _, executor = make_executor(None)
    node = executor.allocate(
        "AUTH:ROOT",
        ("coherence",),
        allocation_key="missing-local-adapter",
    ).nodes[0]

    step = executor.orchestration_step()

    assert node.node_id in step["local_execution"]["adapter_required"]
    assert fabric.node(node.node_id).status == "OPEN"
    assert fabric.node(node.node_id).execution_started is False
    assert broker.queue_status()["queued"] == 0


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
