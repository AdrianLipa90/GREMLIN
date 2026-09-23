from __future__ import annotations

import pytest

from gremlin_mcp.adaptive_runtime import OperatorTier, ResourceBudget, ResourceCost
from gremlin_mcp.orchorbital_allocator import allocate_invocation
from gremlin_mcp.orchorbital_context import OrbitalContextStore, apply_context_packet
from gremlin_mcp.orchorbital_executor import (
    DEFAULT_INPUT_SCHEMA,
    DISCOVERY_HANDOFF_CONTEXT_KEY,
    DISCOVERY_KEY,
    DISCOVERY_SCHEMA,
    MAX_DISCOVERY_HANDOFF_BYTES,
    PARENT_RESULT_CONTEXT_KEY,
    ORBITAL_CONTEXT_PACKET_KEY,
    REDUCTION_TASK_KEY,
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
        "OCTOPUS",
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
        "OCTOPUS",
        node_id="OCTOPUS-LOCAL",
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
        "OCTOPUS",
        node_id="OCTOPUS-LOCAL",
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

    first_settle = executor.settle_local_joins()

    assert child_id in first_settle["closed"]
    assert parent.node_id not in first_settle["closed"]
    assert parent.node_id in first_settle["reduction_required"]
    assert fabric.node(child_id).status == "CLOSED"
    assert fabric.node(parent.node_id).status == "OPEN"

    packet = executor.build_reduction_packet(parent.node_id)
    assert packet["self_output"][DISCOVERY_KEY]["obligations"] == ["audit"]
    assert len(packet["join_results"]) == 1
    assert packet["join_results"][0]["resolved_node_id"] == child_id
    assert packet["join_results"][0]["output"] == {"audit": "candidate"}

    reduction = executor.complete_reduction(
        parent.node_id,
        {
            "graph": "candidate",
            "audit": packet["join_results"][0]["output"],
        },
    )
    assert reduction["state"] == "REDUCTION_COMPLETE"
    assert reduction["join_child_count"] == 1

    settled = executor.settle_local_joins()
    assert parent.node_id in settled["closed"]
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


def test_executor_allocate_binds_child_context_from_caller() -> None:
    fabric = OrchorbitalFabric()
    broker = WorkerBroker()
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root({"shared": "root-context", "mode": "root"})
    executor = OrchorbitalExecutor(
        execution_id="ctx-allocate",
        fabric=fabric,
        broker=broker,
        operators=operators(),
        budget=BUDGET,
        context_store=contexts,
    )

    allocation = executor.allocate(
        "AUTH:ROOT",
        ("graph",),
        allocation_key="initial-graph",
    )
    child = allocation.nodes[0]

    assert child.caller_id == "AUTH:ROOT"
    assert contexts.frame(child.node_id).base_node_id == "AUTH:ROOT"
    assert contexts.materialize(child.node_id) == contexts.materialize("AUTH:ROOT")


def test_recursive_discovery_binds_child_context_and_child_is_dispatchable() -> None:
    fabric = OrchorbitalFabric()
    broker = WorkerBroker()
    broker.register_worker(
        "worker-1",
        ["SPIDER", "OWL"],
        vector_width=2,
        max_batch=2,
    )
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root({"shared": "root", "request": "audit graph"})
    executor = OrchorbitalExecutor(
        execution_id="ctx-recursive",
        fabric=fabric,
        broker=broker,
        operators=operators(),
        budget=BUDGET,
        context_store=contexts,
    )
    parent = executor.allocate(
        "AUTH:ROOT",
        ("graph",),
        allocation_key="root-graph",
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
    receipt = executor.reconcile_node(parent.node_id)
    child_id = receipt["allocation"]["node_ids"][0]

    child_frame = contexts.frame(child_id)
    assert child_frame.base_node_id is not None
    assert child_frame.base_node_id.startswith("CTX:DISC:")
    shared_frame = contexts.frame(child_frame.base_node_id)
    assert shared_frame.base_node_id == parent.node_id
    child_context = contexts.materialize(child_id)
    parent_context = contexts.materialize(parent.node_id)
    assert child_context["shared"] == parent_context["shared"]
    assert child_context["request"] == parent_context["request"]
    assert child_context[PARENT_RESULT_CONTEXT_KEY] == {
        "node_id": parent.node_id,
        "result_commitment": receipt["result_commitment"],
    }
    assert DISCOVERY_HANDOFF_CONTEXT_KEY not in child_context

    dispatched = executor.ensure_dispatched(child_id, {"query": "audit"})
    assert dispatched.species == "OWL"
    assert broker.task_result(dispatched.task_id)["state"] == "QUEUED"


def test_context_binding_recovers_after_crash_without_duplicate_deterministic_nodes(
    monkeypatch,
) -> None:
    fabric = OrchorbitalFabric()
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root({"root": "context"})
    executor = OrchorbitalExecutor(
        execution_id="ctx-bind-recovery",
        fabric=fabric,
        broker=WorkerBroker(),
        operators=operators(),
        budget=BUDGET,
        context_store=contexts,
    )

    original = contexts.inherit_from_caller
    calls = 0

    def fail_once(node_id, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("simulated crash before context bind")
        return original(node_id, **kwargs)

    monkeypatch.setattr(contexts, "inherit_from_caller", fail_once)
    with pytest.raises(RuntimeError, match="simulated crash"):
        executor.allocate(
            "AUTH:ROOT",
            ("graph",),
            allocation_key="recoverable-allocation",
        )
    count_after_crash = fabric.receipt()["node_count"]

    monkeypatch.setattr(contexts, "bind_node", original)
    recovered = executor.allocate(
        "AUTH:ROOT",
        ("graph",),
        allocation_key="recoverable-allocation",
    )

    assert fabric.receipt()["node_count"] == count_after_crash
    assert len(recovered.nodes) == 1
    assert contexts.frame(recovered.nodes[0].node_id).base_node_id == "AUTH:ROOT"


def test_reduction_output_is_bound_to_exact_join_inputs() -> None:
    fabric, broker, executor = executor_with_worker()
    parent = fabric.spawn(
        "AUTH:ROOT",
        "OCTOPUS",
        node_id="LOCAL-REDUCE-PARENT",
        join_to_caller=False,
    )
    child = fabric.spawn(
        parent.node_id,
        "SPIDER",
        node_id="WORKER-REDUCE-CHILD",
    )
    executor.complete_local(parent.node_id, {"parent": "candidate"})
    executor.ensure_dispatched(child.node_id, {"query": "child"})
    _claim_and_submit(
        broker,
        species="SPIDER",
        output={"child": "candidate"},
    )
    executor.reconcile_node(child.node_id)
    executor.settle_local_joins()

    packet = executor.build_reduction_packet(parent.node_id)
    assert packet["self_output"] == {"parent": "candidate"}
    assert packet["join_results"][0]["output"] == {"child": "candidate"}

    first = executor.complete_reduction(
        parent.node_id,
        {"merged": ["parent", "child"]},
    )
    replay = executor.complete_reduction(
        parent.node_id,
        {"merged": ["parent", "child"]},
    )
    assert replay["reduction_commitment"] == first["reduction_commitment"]

    with pytest.raises(RuntimeError, match="reduction is already complete"):
        executor.complete_reduction(
            parent.node_id,
            {"merged": ["different"]},
        )


def test_join_results_are_not_silently_ignored_by_settle() -> None:
    fabric, broker, executor = executor_with_worker()
    parent = fabric.spawn(
        "AUTH:ROOT",
        "OCTOPUS",
        node_id="NO-SILENT-PARENT",
        join_to_caller=False,
    )
    child = fabric.spawn(parent.node_id, "SPIDER", node_id="NO-SILENT-CHILD")
    executor.complete_local(parent.node_id, {"parent": True})
    executor.ensure_dispatched(child.node_id, {"query": "child"})
    _claim_and_submit(broker, species="SPIDER", output={"child": True})
    executor.reconcile_node(child.node_id)

    settled = executor.settle_local_joins()

    assert child.node_id in settled["closed"]
    assert parent.node_id not in settled["closed"]
    assert parent.node_id in settled["reduction_required"]
    assert fabric.node(parent.node_id).reduction_complete is False


def test_recovery_effective_result_preserves_partial_replacement_and_stranded_children() -> None:
    fabric = OrchorbitalFabric()
    executor = OrchorbitalExecutor(
        execution_id="recovery-reduction",
        fabric=fabric,
        broker=WorkerBroker(),
        operators=operators(),
        budget=BUDGET,
    )

    source = fabric.spawn(
        "AUTH:ROOT",
        "OCTOPUS",
        obligations=("recover-me",),
        node_id="FAILED-SOURCE",
    )
    stranded = fabric.spawn(
        source.node_id,
        "HUMMINGBIRD",
        obligations=("stranded-evidence",),
        node_id="STRANDED-CHILD",
    )
    executor.complete_local(source.node_id, {"source": "partial"})
    fabric.fail(source.node_id, reason="simulated source failure")

    replacement = fabric.spawn(
        "AUTH:ROOT",
        "OCTOPUS",
        obligations=("recover-me",),
        node_id="RECOVERY-NODE",
        join_to_caller=False,
    )
    fabric.bind_replacement(source.node_id, replacement.node_id)

    executor.complete_local(stranded.node_id, {"stranded": "evidence"})
    executor.complete_local(replacement.node_id, {"replacement": "result"})
    settled = executor.settle_local_joins()
    assert stranded.node_id in settled["closed"]
    assert replacement.node_id in settled["closed"]
    assert fabric.is_resolved(source.node_id) is True

    executor.complete_local("AUTH:ROOT", {"root": "candidate"})
    assert "AUTH:ROOT" in fabric.reduction_candidates()

    packet = executor.build_reduction_packet("AUTH:ROOT")
    recovered = packet["join_results"][0]
    assert recovered["requested_node_id"] == source.node_id
    assert recovered["recovery"] is True
    recovery = recovered["output"]["recovery"]
    assert recovery["source_partial_result"]["output"] == {"source": "partial"}
    assert recovery["replacement"]["output"] == {"replacement": "result"}
    assert recovery["source_join_results"][0]["output"] == {
        "stranded": "evidence"
    }


def test_worker_parent_receives_deterministic_reduction_continuation_after_children_return() -> None:
    fabric, broker, executor = executor_with_worker(execution_id="reduction-continuation")
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
            "graph": "candidate",
            DISCOVERY_KEY: {
                "schema": DISCOVERY_SCHEMA,
                "obligations": ["audit"],
            },
        },
    )
    first = executor.reconcile_node(parent.node_id)
    child_id = first["allocation"]["node_ids"][0]

    executor.ensure_dispatched(child_id, {"query": "audit"})
    _claim_and_submit(
        broker,
        species="OWL",
        output={"audit": "child-candidate"},
    )
    executor.reconcile_node(child_id)

    first_settle = executor.settle_local_joins()
    assert child_id in first_settle["closed"]
    assert parent.node_id in first_settle["reduction_required"]

    first_dispatch = executor.ensure_reduction_dispatched(parent.node_id)
    replay_dispatch = executor.ensure_reduction_dispatched(parent.node_id)
    assert replay_dispatch.task_id == first_dispatch.task_id
    assert replay_dispatch.task_commitment == first_dispatch.task_commitment
    assert first_dispatch.species == "SPIDER"

    lease = broker.claim("worker-1", species="SPIDER", limit=1)
    assert len(lease["tasks"]) == 1
    reduction_task = lease["tasks"][0]
    assert reduction_task["task_id"] == first_dispatch.task_id

    reduction_input = reduction_task["payload"]["input"]
    assert reduction_input["kind"] == "ORCHORBITAL_LOCAL_REDUCTION"
    packet = reduction_input[REDUCTION_TASK_KEY]
    assert packet["node_id"] == parent.node_id
    assert packet["self_output"]["graph"] == "candidate"
    assert packet["join_results"][0]["resolved_node_id"] == child_id
    assert packet["join_results"][0]["output"] == {
        "audit": "child-candidate"
    }

    broker.submit(
        "worker-1",
        lease["lease_id"],
        [
            {
                "task_id": first_dispatch.task_id,
                "output": {
                    "graph": "candidate",
                    "audit": "integrated",
                },
            }
        ],
    )
    reduction = executor.reconcile_reduction(parent.node_id)

    assert reduction["state"] == "REDUCTION_COMPLETE"
    assert reduction["changed"] is True
    assert fabric.node(parent.node_id).reduction_complete is True

    final_settle = executor.settle_local_joins()
    assert parent.node_id in final_settle["closed"]
    assert fabric.node(parent.node_id).status == "CLOSED"


def test_reduction_continuation_cannot_spawn_new_children_after_join_seal() -> None:
    fabric, broker, executor = executor_with_worker(execution_id="reduction-seal")
    parent = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="REDUCE-PARENT",
        join_to_caller=False,
    )
    child = fabric.spawn(
        parent.node_id,
        "OWL",
        node_id="REDUCE-CHILD",
    )

    fabric.mark_started(parent.node_id)
    broker.enqueue(
        "SPIDER",
        {"seed": True},
        task_id=executor.deterministic_task_id(parent.node_id),
    )
    lease = broker.claim("worker-1", species="SPIDER", limit=1)
    broker.submit(
        "worker-1",
        lease["lease_id"],
        [{"task_id": lease["tasks"][0]["task_id"], "output": {"parent": True}}],
    )
    executor.reconcile_node(parent.node_id)

    fabric.mark_started(child.node_id)
    broker.enqueue(
        "OWL",
        {"child": True},
        task_id=executor.deterministic_task_id(child.node_id),
    )
    child_lease = broker.claim("worker-1", species="OWL", limit=1)
    broker.submit(
        "worker-1",
        child_lease["lease_id"],
        [{"task_id": child_lease["tasks"][0]["task_id"], "output": {"child": True}}],
    )
    executor.reconcile_node(child.node_id)
    executor.settle_local_joins()

    dispatch = executor.ensure_reduction_dispatched(parent.node_id)
    reduction_lease = broker.claim("worker-1", species="SPIDER", limit=1)
    broker.submit(
        "worker-1",
        reduction_lease["lease_id"],
        [
            {
                "task_id": dispatch.task_id,
                "output": {
                    DISCOVERY_KEY: {
                        "schema": DISCOVERY_SCHEMA,
                        "obligations": ["derive"],
                    }
                },
            }
        ],
    )

    receipt = executor.reconcile_reduction(parent.node_id)

    assert receipt["state"] == "QUARANTINED_REDUCTION_DISCOVERY_AFTER_SEAL"
    assert fabric.node(parent.node_id).status == "QUARANTINED"


def test_orchestration_step_runs_recursive_worker_child_and_parent_reduction_flow() -> None:
    fabric, broker, executor = executor_with_worker(execution_id="auto-step")
    parent = allocate_invocation(
        fabric,
        "AUTH:ROOT",
        ("graph",),
        operators(),
        budget=BUDGET,
    ).nodes[0]
    executor.ensure_dispatched(parent.node_id, {"query": "initial graph"})

    _claim_and_submit(
        broker,
        species="SPIDER",
        output={
            "graph": "draft",
            DISCOVERY_KEY: {
                "schema": DISCOVERY_SCHEMA,
                "obligations": ["audit"],
            },
        },
    )

    step1 = executor.orchestration_step()
    parent_after = fabric.node(parent.node_id)
    assert parent_after.self_complete is True
    assert parent_after.status == "OPEN"
    assert len(step1["worker_dispatch"]["dispatched"]) == 1

    child_id = step1["worker_dispatch"]["dispatched"][0]["node_id"]
    child = fabric.node(child_id)
    assert child.species == "OWL"
    child_task_id = executor.deterministic_task_id(child_id)
    child_task = broker.task_result(child_task_id)
    assert child_task["state"] == "QUEUED"
    assert child_task["payload"]["input"]["schema"] == DEFAULT_INPUT_SCHEMA
    assert child_task["payload"]["input"]["obligations"] == ["audit"]

    child_lease = broker.claim("worker-1", species="OWL", limit=1)
    broker.submit(
        "worker-1",
        child_lease["lease_id"],
        [
            {
                "task_id": child_task_id,
                "output": {"audit": "pass-candidate"},
            }
        ],
    )

    step2 = executor.orchestration_step()
    assert fabric.node(child_id).status == "CLOSED"
    reduction_dispatches = step2["reduction_dispatch"]["dispatched"]
    assert len(reduction_dispatches) == 1
    assert reduction_dispatches[0]["node_id"] == parent.node_id
    reduction_task_id = reduction_dispatches[0]["task_id"]

    reduction_lease = broker.claim("worker-1", species="SPIDER", limit=1)
    assert reduction_lease["tasks"][0]["task_id"] == reduction_task_id
    reduction_packet = reduction_lease["tasks"][0]["payload"]["input"][
        REDUCTION_TASK_KEY
    ]
    assert reduction_packet["self_output"]["graph"] == "draft"
    assert reduction_packet["join_results"][0]["output"] == {
        "audit": "pass-candidate"
    }
    broker.submit(
        "worker-1",
        reduction_lease["lease_id"],
        [
            {
                "task_id": reduction_task_id,
                "output": {
                    "graph": "draft",
                    "audit": "integrated-pass",
                },
            }
        ],
    )

    step3 = executor.orchestration_step()

    assert fabric.node(parent.node_id).status == "CLOSED"
    assert step3["reduction_reconcile"]["failures"] == []
    assert parent.node_id in step3["settle_after_reductions"]["closed"]
    assert step3["global_synthesis_barrier_required"] is False


def test_dispatch_ready_does_not_reenqueue_existing_custom_running_task() -> None:
    fabric, broker, executor = executor_with_worker(execution_id="custom-pending")
    node = allocate_invocation(
        fabric,
        "AUTH:ROOT",
        ("graph",),
        operators(),
        budget=BUDGET,
    ).nodes[0]
    custom = executor.ensure_dispatched(
        node.node_id,
        {"custom": "payload-that-must-not-drift"},
    )
    before = broker.task_result(custom.task_id)

    dispatched = executor.dispatch_ready()

    assert dispatched["failures"] == []
    assert dispatched["dispatched"] == []
    after = broker.task_result(custom.task_id)
    assert after["task_commitment"] == before["task_commitment"]
    assert after["payload"] == before["payload"]


def test_worker_discovery_handoff_becomes_child_local_context_delta() -> None:
    fabric = OrchorbitalFabric()
    broker = WorkerBroker()
    broker.register_worker(
        "worker-1",
        ["SPIDER", "OWL"],
        vector_width=2,
        max_batch=2,
    )
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root(
        {
            "shared": "root-state",
            "protected": "must-not-be-overwritten",
        }
    )
    executor = OrchorbitalExecutor(
        execution_id="handoff-worker",
        fabric=fabric,
        broker=broker,
        operators=operators(),
        budget=BUDGET,
        context_store=contexts,
    )
    parent = executor.allocate(
        "AUTH:ROOT",
        ("graph",),
        allocation_key="handoff-parent",
    ).nodes[0]
    executor.ensure_dispatched(parent.node_id, {"query": "derive graph"})

    _claim_and_submit(
        broker,
        species="SPIDER",
        output={
            "answer": "candidate",
            DISCOVERY_KEY: {
                "schema": DISCOVERY_SCHEMA,
                "obligations": ["audit"],
                "handoff": {
                    "graph_summary": {"edges": 7, "components": 2},
                    "protected": "child-local-only",
                },
            },
        },
    )
    receipt = executor.reconcile_node(parent.node_id)
    child_id = receipt["allocation"]["node_ids"][0]
    child_context = contexts.materialize(child_id)

    assert receipt["handoff_present"] is True
    assert child_context["protected"] == "must-not-be-overwritten"
    assert child_context[DISCOVERY_HANDOFF_CONTEXT_KEY]["protected"] == (
        "child-local-only"
    )
    assert child_context[DISCOVERY_HANDOFF_CONTEXT_KEY]["graph_summary"] == {
        "edges": 7,
        "components": 2,
    }
    assert child_context[PARENT_RESULT_CONTEXT_KEY] == {
        "node_id": parent.node_id,
        "result_commitment": receipt["result_commitment"],
    }


def test_worker_handoff_without_context_store_is_quarantined_fail_closed() -> None:
    fabric, broker, executor = executor_with_worker(
        execution_id="handoff-no-context"
    )
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
                "handoff": {"summary": "cannot-be-delivered"},
            }
        },
    )

    receipt = executor.reconcile_node(parent.node_id)

    assert receipt["state"] == "QUARANTINED_DISCOVERY_HANDOFF_WITHOUT_CONTEXT"
    assert fabric.node(parent.node_id).status == "QUARANTINED"


def test_oversized_worker_handoff_is_quarantined_before_child_allocation() -> None:
    fabric = OrchorbitalFabric()
    broker = WorkerBroker()
    broker.register_worker("worker-1", ["SPIDER", "OWL"])
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root({"root": True})
    executor = OrchorbitalExecutor(
        execution_id="handoff-oversized",
        fabric=fabric,
        broker=broker,
        operators=operators(),
        budget=BUDGET,
        context_store=contexts,
    )
    parent = executor.allocate(
        "AUTH:ROOT",
        ("graph",),
        allocation_key="oversized-parent",
    ).nodes[0]
    before_nodes = fabric.receipt()["node_count"]
    executor.ensure_dispatched(parent.node_id, {"query": "graph"})
    _claim_and_submit(
        broker,
        species="SPIDER",
        output={
            DISCOVERY_KEY: {
                "schema": DISCOVERY_SCHEMA,
                "obligations": ["audit"],
                "handoff": {"blob": "X" * (MAX_DISCOVERY_HANDOFF_BYTES + 1)},
            }
        },
    )

    receipt = executor.reconcile_node(parent.node_id)

    assert receipt["state"] == "QUARANTINED_INVALID_DISCOVERY"
    assert fabric.node(parent.node_id).status == "QUARANTINED"
    assert fabric.receipt()["node_count"] == before_nodes


def test_recursive_handoff_context_binding_recovers_after_crash_without_duplicate_child(
    monkeypatch,
) -> None:
    fabric = OrchorbitalFabric()
    broker = WorkerBroker()
    broker.register_worker("worker-1", ["SPIDER", "OWL"])
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root({"root": "context"})
    executor = OrchorbitalExecutor(
        execution_id="handoff-crash-recovery",
        fabric=fabric,
        broker=broker,
        operators=operators(),
        budget=BUDGET,
        context_store=contexts,
    )
    parent = executor.allocate(
        "AUTH:ROOT",
        ("graph",),
        allocation_key="handoff-crash-parent",
    ).nodes[0]
    executor.ensure_dispatched(parent.node_id, {"query": "graph"})
    _claim_and_submit(
        broker,
        species="SPIDER",
        output={
            DISCOVERY_KEY: {
                "schema": DISCOVERY_SCHEMA,
                "obligations": ["audit"],
                "handoff": {"summary": "stable"},
            }
        },
    )

    original = contexts.bind_node
    failed_once = False

    def fail_first_child_bind(node_id, **kwargs):
        nonlocal failed_once
        if node_id != parent.node_id and not failed_once:
            failed_once = True
            raise RuntimeError("simulated crash before handoff context bind")
        return original(node_id, **kwargs)

    monkeypatch.setattr(contexts, "bind_node", fail_first_child_bind)
    with pytest.raises(RuntimeError, match="simulated crash"):
        executor.reconcile_node(parent.node_id)
    count_after_crash = fabric.receipt()["node_count"]

    monkeypatch.setattr(contexts, "inherit_from_caller", original)
    receipt = executor.reconcile_node(parent.node_id)
    child_id = receipt["allocation"]["node_ids"][0]

    assert fabric.receipt()["node_count"] == count_after_crash
    assert contexts.materialize(child_id)[DISCOVERY_HANDOFF_CONTEXT_KEY] == {
        "summary": "stable"
    }
    assert contexts.materialize(child_id)[PARENT_RESULT_CONTEXT_KEY][
        "result_commitment"
    ] == receipt["result_commitment"]


def test_multi_child_discovery_uses_one_shared_handoff_frame_without_copying_delta() -> None:
    fabric = OrchorbitalFabric()
    broker = WorkerBroker()
    broker.register_worker(
        "worker-1",
        ["SPIDER", "OWL", "MOLE"],
        vector_width=4,
        max_batch=4,
    )
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root({"shared": "root"})
    executor = OrchorbitalExecutor(
        execution_id="shared-handoff-fanout",
        fabric=fabric,
        broker=broker,
        operators=operators(),
        budget=BUDGET,
        context_store=contexts,
    )
    parent = executor.allocate(
        "AUTH:ROOT",
        ("graph",),
        allocation_key="fanout-parent",
    ).nodes[0]
    executor.ensure_dispatched(parent.node_id, {"query": "fanout"})
    _claim_and_submit(
        broker,
        species="SPIDER",
        output={
            DISCOVERY_KEY: {
                "schema": DISCOVERY_SCHEMA,
                "obligations": ["audit", "derive"],
                "handoff": {
                    "summary": "shared-once",
                    "evidence": [1, 2, 3],
                },
            }
        },
    )

    receipt = executor.reconcile_node(parent.node_id)
    child_ids = receipt["allocation"]["node_ids"]
    assert len(child_ids) == 2

    child_frames = [contexts.frame(node_id) for node_id in child_ids]
    shared_ids = {frame.base_node_id for frame in child_frames}
    assert len(shared_ids) == 1
    shared_id = next(iter(shared_ids))
    assert shared_id is not None and shared_id.startswith("CTX:DISC:")

    shared = contexts.frame(shared_id)
    assert shared.base_node_id == parent.node_id
    assert shared.set_values[DISCOVERY_HANDOFF_CONTEXT_KEY] == {
        "summary": "shared-once",
        "evidence": [1, 2, 3],
    }
    assert shared.set_values[PARENT_RESULT_CONTEXT_KEY]["result_commitment"] == (
        receipt["result_commitment"]
    )
    assert all(frame.set_values == {} for frame in child_frames)

    materialized = [contexts.materialize(node_id) for node_id in child_ids]
    assert all(
        row[DISCOVERY_HANDOFF_CONTEXT_KEY]["summary"] == "shared-once"
        for row in materialized
    )
