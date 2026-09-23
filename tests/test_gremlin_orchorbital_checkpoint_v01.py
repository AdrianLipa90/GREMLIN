from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import pytest

from gremlin_mcp.adaptive_runtime import OperatorTier, ResourceBudget, ResourceCost
from gremlin_mcp.orchorbital_context import OrbitalContextStore
from gremlin_mcp.orchorbital_executor import (
    DISCOVERY_KEY,
    DISCOVERY_SCHEMA,
    EXECUTOR_CHECKPOINT_DOMAIN,
    OrchorbitalExecutor,
)
from gremlin_mcp.orchorbital_fabric import OrchorbitalFabric
from gremlin_mcp.persistent_workers import PersistentWorkerBroker
from gremlin_mcp.workers import WorkerBroker


BUDGET = ResourceBudget(tokens=100.0, latency=100.0, calls=100.0, memory=100.0)


def operators():
    return (
        OperatorTier("SPIDER", 0, frozenset({"graph"}), ResourceCost(5, 5, 1, 2)),
        OperatorTier("OWL", 0, frozenset({"audit"}), ResourceCost(4, 4, 1, 2)),
        OperatorTier("MOLE", 0, frozenset({"derive"}), ResourceCost(7, 7, 1, 3)),
    )


def _claim_submit(
    broker,
    worker_id: str,
    species: str,
    output: object,
) -> str:
    lease = broker.claim(worker_id, species=species, limit=1)
    assert lease["lease_id"] is not None
    assert len(lease["tasks"]) == 1
    task_id = lease["tasks"][0]["task_id"]
    broker.submit(
        worker_id,
        lease["lease_id"],
        [{"task_id": task_id, "output": output}],
    )
    return task_id


def _build_checkpointed_runtime(tmp_path):
    state_path = tmp_path / "orch-workers.sqlite"
    broker = PersistentWorkerBroker(str(state_path))
    broker.register_worker(
        "checkpoint-worker",
        ["SPIDER", "OWL"],
        vector_width=4,
        max_batch=4,
    )

    fabric = OrchorbitalFabric()
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root(
        {
            "shared": "restart-stable",
            "request": "graph then audit",
        }
    )
    executor = OrchorbitalExecutor(
        execution_id="checkpoint-runtime",
        fabric=fabric,
        broker=broker,
        operators=operators(),
        budget=BUDGET,
        context_store=contexts,
    )

    parent = executor.allocate(
        "AUTH:ROOT",
        ("graph",),
        allocation_key="checkpoint-parent",
    ).nodes[0]
    executor.ensure_dispatched(parent.node_id, {"query": "graph"})
    _claim_submit(
        broker,
        "checkpoint-worker",
        "SPIDER",
        {
            "graph": "candidate",
            DISCOVERY_KEY: {
                "schema": DISCOVERY_SCHEMA,
                "obligations": ["audit"],
                "handoff": {"graph_summary": "stable"},
            },
        },
    )
    parent_receipt = executor.reconcile_node(parent.node_id)
    child_id = parent_receipt["allocation"]["node_ids"][0]

    executor.ensure_dispatched(child_id, {"query": "audit"})
    _claim_submit(
        broker,
        "checkpoint-worker",
        "OWL",
        {"audit": "pass"},
    )
    executor.reconcile_node(child_id)
    first_settle = executor.settle_local_joins()
    assert child_id in first_settle["closed"]
    assert parent.node_id in first_settle["reduction_required"]

    reduction = executor.ensure_reduction_dispatched(parent.node_id)
    lease = broker.claim("checkpoint-worker", species="SPIDER", limit=1)
    assert lease["tasks"][0]["task_id"] == reduction.task_id
    broker.submit(
        "checkpoint-worker",
        lease["lease_id"],
        [
            {
                "task_id": reduction.task_id,
                "output": {
                    "graph": "candidate",
                    "audit": "pass",
                    "integrated": True,
                },
            }
        ],
    )
    executor.reconcile_reduction(parent.node_id)
    second_settle = executor.settle_local_joins()
    assert parent.node_id in second_settle["closed"]

    local = fabric.spawn(
        "AUTH:ROOT",
        "BEES",
        node_id="LOCAL-CHECKPOINT",
        join_to_caller=False,
    )
    contexts.inherit_from_caller(
        local.node_id,
        set_values={"local_role": "coherence"},
    )
    executor.complete_local(local.node_id, {"coherence": "stable"})
    executor.settle_local_joins()
    assert fabric.node(local.node_id).status == "CLOSED"

    checkpoints = {
        "fabric": fabric.checkpoint_state(),
        "context": contexts.checkpoint_state(),
        "executor": executor.checkpoint_state(),
    }
    ids = {
        "parent": parent.node_id,
        "child": child_id,
        "local": local.node_id,
    }
    broker.close()
    return state_path, checkpoints, ids


def test_full_orchorbital_restart_restores_identical_committed_state(tmp_path) -> None:
    state_path, checkpoints, ids = _build_checkpointed_runtime(tmp_path)

    fabric = OrchorbitalFabric.from_checkpoint(checkpoints["fabric"])
    contexts = OrbitalContextStore.from_checkpoint(fabric, checkpoints["context"])
    broker = PersistentWorkerBroker(str(state_path))
    try:
        executor = OrchorbitalExecutor.from_checkpoint(
            checkpoints["executor"],
            fabric=fabric,
            broker=broker,
            context_store=contexts,
        )

        assert fabric.checkpoint_state()["checkpoint_commitment"] == (
            checkpoints["fabric"]["checkpoint_commitment"]
        )
        assert contexts.checkpoint_state()["checkpoint_commitment"] == (
            checkpoints["context"]["checkpoint_commitment"]
        )
        assert executor.checkpoint_state()["checkpoint_commitment"] == (
            checkpoints["executor"]["checkpoint_commitment"]
        )

        assert fabric.node(ids["parent"]).status == "CLOSED"
        assert fabric.node(ids["child"]).status == "CLOSED"
        assert fabric.node(ids["local"]).status == "CLOSED"
        assert contexts.materialize(ids["child"])["shared"] == "restart-stable"
        assert contexts.materialize(ids["local"])["local_role"] == "coherence"

        step = executor.orchestration_step()
        assert step["worker_reconcile"]["failures"] == []
        assert step["reduction_reconcile"]["failures"] == []
        assert step["worker_dispatch"]["failures"] == []
        assert step["worker_dispatch"]["dispatched"] == []
        assert step["global_synthesis_barrier_required"] is False
    finally:
        broker.close()


def test_fabric_checkpoint_tamper_fails_closed(tmp_path) -> None:
    _, checkpoints, _ = _build_checkpointed_runtime(tmp_path)
    tampered = deepcopy(checkpoints["fabric"])
    tampered["nodes"][0]["obligations"] = ["tampered"]

    with pytest.raises(ValueError, match="checkpoint commitment mismatch"):
        OrchorbitalFabric.from_checkpoint(tampered)


def test_context_checkpoint_tamper_fails_closed(tmp_path) -> None:
    _, checkpoints, _ = _build_checkpointed_runtime(tmp_path)
    fabric = OrchorbitalFabric.from_checkpoint(checkpoints["fabric"])
    tampered = deepcopy(checkpoints["context"])
    tampered["frames"][0]["set_values"]["shared"] = "tampered"

    with pytest.raises(ValueError, match="checkpoint commitment mismatch"):
        OrbitalContextStore.from_checkpoint(fabric, tampered)


def test_executor_checkpoint_tamper_fails_closed(tmp_path) -> None:
    state_path, checkpoints, _ = _build_checkpointed_runtime(tmp_path)
    fabric = OrchorbitalFabric.from_checkpoint(checkpoints["fabric"])
    contexts = OrbitalContextStore.from_checkpoint(fabric, checkpoints["context"])
    broker = PersistentWorkerBroker(str(state_path))
    try:
        tampered = deepcopy(checkpoints["executor"])
        tampered["local_results"]["LOCAL-CHECKPOINT"]["coherence"] = "tampered"

        with pytest.raises(ValueError, match="checkpoint commitment mismatch"):
            OrchorbitalExecutor.from_checkpoint(
                tampered,
                fabric=fabric,
                broker=broker,
                context_store=contexts,
            )
    finally:
        broker.close()


def test_executor_restore_rejects_missing_external_worker_state(tmp_path) -> None:
    _, checkpoints, _ = _build_checkpointed_runtime(tmp_path)
    fabric = OrchorbitalFabric.from_checkpoint(checkpoints["fabric"])
    contexts = OrbitalContextStore.from_checkpoint(fabric, checkpoints["context"])

    with pytest.raises(ValueError, match="broker/fabric worker result mismatch|unknown task_id"):
        OrchorbitalExecutor.from_checkpoint(
            checkpoints["executor"],
            fabric=fabric,
            broker=WorkerBroker(),
            context_store=contexts,
        )


def test_context_restore_rejects_wrong_fabric_even_with_valid_context_checkpoint(
    tmp_path,
) -> None:
    _, checkpoints, _ = _build_checkpointed_runtime(tmp_path)
    wrong = OrchorbitalFabric(root_id="OTHER:ROOT")

    with pytest.raises(ValueError, match="fabric topology mismatch"):
        OrbitalContextStore.from_checkpoint(wrong, checkpoints["context"])


def _recommit_executor_checkpoint(checkpoint: dict) -> None:
    core = {
        key: deepcopy(value)
        for key, value in checkpoint.items()
        if key != "checkpoint_commitment"
    }
    encoded = json.dumps(
        core,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    checkpoint["checkpoint_commitment"] = hashlib.blake2b(
        EXECUTOR_CHECKPOINT_DOMAIN + encoded,
        digest_size=32,
    ).hexdigest()


def test_restore_rejects_semantically_forged_worker_to_local_backend_binding(
    tmp_path,
) -> None:
    state_path, checkpoints, ids = _build_checkpointed_runtime(tmp_path)
    fabric = OrchorbitalFabric.from_checkpoint(checkpoints["fabric"])
    contexts = OrbitalContextStore.from_checkpoint(fabric, checkpoints["context"])
    broker = PersistentWorkerBroker(str(state_path))
    try:
        forged = deepcopy(checkpoints["executor"])
        forged["execution_backend_bindings"][ids["parent"]] = "LOCAL"
        _recommit_executor_checkpoint(forged)

        with pytest.raises(
            ValueError,
            match="LOCAL backend without matching adapter",
        ):
            OrchorbitalExecutor.from_checkpoint(
                forged,
                fabric=fabric,
                broker=broker,
                context_store=contexts,
            )
    finally:
        broker.close()


def test_restore_rejects_recommitted_started_node_without_backend_binding(
    tmp_path,
) -> None:
    state_path, checkpoints, ids = _build_checkpointed_runtime(tmp_path)
    fabric = OrchorbitalFabric.from_checkpoint(checkpoints["fabric"])
    contexts = OrbitalContextStore.from_checkpoint(fabric, checkpoints["context"])
    broker = PersistentWorkerBroker(str(state_path))
    try:
        forged = deepcopy(checkpoints["executor"])
        del forged["execution_backend_bindings"][ids["parent"]]
        _recommit_executor_checkpoint(forged)

        with pytest.raises(
            ValueError,
            match="started node is missing execution backend binding",
        ):
            OrchorbitalExecutor.from_checkpoint(
                forged,
                fabric=fabric,
                broker=broker,
                context_store=contexts,
            )
    finally:
        broker.close()
