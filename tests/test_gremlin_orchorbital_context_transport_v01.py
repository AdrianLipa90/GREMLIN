from __future__ import annotations

import asyncio
from copy import deepcopy

import pytest

from gremlin_mcp.adaptive_runtime import OperatorTier, ResourceBudget, ResourceCost
from gremlin_mcp.orchorbital_context import (
    BUNDLE_PAYLOAD_KEY,
    BUNDLE_REF_PAYLOAD_KEY,
    PACKET_PAYLOAD_KEY,
    OrbitalContextStore,
    apply_context_packet,
)
from gremlin_mcp.orchorbital_executor import OrchorbitalExecutor
from gremlin_mcp.orchorbital_fabric import OrchorbitalFabric
from gremlin_mcp.persistent_workers import PersistentWorkerBroker
from gremlin_mcp.worker_client import (
    ORBITAL_CONTEXT_MATERIALIZED_KEY,
    GremlinWorkerClient,
)
from gremlin_mcp.workers import WorkerBroker


BUDGET = ResourceBudget(tokens=100.0, latency=100.0, calls=100.0, memory=100.0)


def operators(species: str = "SPIDER"):
    return (
        OperatorTier(
            species,
            0,
            frozenset({"work"}),
            ResourceCost(5, 5, 1, 2),
        ),
    )


def build_two_siblings(*, species: str = "SPIDER"):
    fabric = OrchorbitalFabric()
    first = fabric.spawn(
        "AUTH:ROOT",
        species,
        obligations=("work",),
        node_id="NODE-A",
        join_to_caller=False,
    )
    second = fabric.spawn(
        "AUTH:ROOT",
        species,
        obligations=("work",),
        node_id="NODE-B",
        join_to_caller=False,
    )
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root(
        {
            "shared_problem": "R" * 4000,
            "shared_memory": "M" * 4000,
            "mode": "root",
        }
    )
    contexts.inherit_from_caller(
        first.node_id,
        set_values={"mode": "first", "local": "A"},
    )
    contexts.inherit_from_caller(
        second.node_id,
        set_values={"mode": "second", "local": "B"},
    )
    return fabric, contexts, first, second


def test_claim_reduces_sibling_context_against_receiver_cache_without_task_drift() -> None:
    fabric, contexts, first, second = build_two_siblings()
    broker = WorkerBroker()
    broker.register_worker("ctx-worker", ["SPIDER"], vector_width=1, max_batch=1)
    executor = OrchorbitalExecutor(
        execution_id="cache-negotiation",
        fabric=fabric,
        broker=broker,
        operators=operators(),
        budget=BUDGET,
        context_store=contexts,
    )

    first_dispatch = executor.ensure_dispatched(first.node_id, {"query": "first"})
    first_lease = broker.claim("ctx-worker", species="SPIDER", limit=1)
    first_packet = first_lease["tasks"][0]["payload"][PACKET_PAYLOAD_KEY]
    first_decoded = apply_context_packet(first_packet)
    known_frames = tuple(first_decoded["cache_updates"])
    assert contexts.frame("AUTH:ROOT").frame_commitment in known_frames

    broker.submit(
        "ctx-worker",
        first_lease["lease_id"],
        [{"task_id": first_dispatch.task_id, "output": {"ok": True}}],
    )

    second_dispatch = executor.ensure_dispatched(second.node_id, {"query": "second"})
    second_lease = broker.claim(
        "ctx-worker",
        species="SPIDER",
        limit=1,
        known_context_frames=known_frames,
    )
    second_packet = second_lease["tasks"][0]["payload"][PACKET_PAYLOAD_KEY]
    transport = second_lease["orchorbital_context_transport"]

    assert second_packet["required_base_frame_commitment"] == contexts.frame(
        "AUTH:ROOT"
    ).frame_commitment
    assert len(second_packet["frames"]) == 1
    assert transport["cache_hit_task_count"] == 1
    assert transport["transport_packet_bytes"] < transport["full_packet_bytes"]
    assert transport["canonical_task_commitment_unchanged"] is True
    assert transport["token_saving_claim"] is False

    replay = executor.ensure_dispatched(second.node_id, {"query": "second"})
    assert replay.task_id == second_dispatch.task_id
    assert replay.task_commitment == second_dispatch.task_commitment


def test_invalid_context_cache_hint_fails_before_any_task_is_leased() -> None:
    broker = WorkerBroker()
    broker.register_worker("worker", ["SPIDER"])
    broker.enqueue("SPIDER", {"x": 1}, task_id="cache-strict")

    with pytest.raises(ValueError, match="hexadecimal"):
        broker.claim(
            "worker",
            species="SPIDER",
            known_context_frames=("z" * 64,),
        )

    assert broker.task_result("cache-strict")["state"] == "QUEUED"


def test_unknown_but_well_formed_cache_hint_does_not_truncate_packet() -> None:
    fabric, contexts, first, _ = build_two_siblings()
    broker = WorkerBroker()
    broker.register_worker("worker", ["SPIDER"], vector_width=1, max_batch=1)
    executor = OrchorbitalExecutor(
        execution_id="unknown-cache",
        fabric=fabric,
        broker=broker,
        operators=operators(),
        budget=BUDGET,
        context_store=contexts,
    )
    executor.ensure_dispatched(first.node_id, {"query": "x"})

    lease = broker.claim(
        "worker",
        species="SPIDER",
        limit=1,
        known_context_frames=("0" * 64,),
    )
    packet = lease["tasks"][0]["payload"][PACKET_PAYLOAD_KEY]

    assert packet["required_base_frame_commitment"] is None
    assert len(packet["frames"]) == 2
    assert lease["orchorbital_context_transport"]["cache_hit_task_count"] == 0


def test_persistent_broker_accepts_ephemeral_cache_hints_without_persisting_them(tmp_path) -> None:
    state = tmp_path / "workers.sqlite"
    broker = PersistentWorkerBroker(str(state))
    try:
        broker.register_worker("worker", ["SPIDER"])
        broker.enqueue("SPIDER", {"x": 1}, task_id="plain-task")
        lease = broker.claim(
            "worker",
            species="SPIDER",
            known_context_frames=("0" * 64,),
        )
        assert lease["lease_id"] is not None
        assert lease["orchorbital_context_transport"]["known_frame_count"] == 1
    finally:
        broker.close()

    reopened = PersistentWorkerBroker(str(state))
    try:
        workers = reopened.list_workers()["workers"]
        assert len(workers) == 1
        assert "known_context_frames" not in workers[0]
    finally:
        reopened.close()


def test_worker_sdk_caches_verified_frames_and_advertises_them_on_next_claim(monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []
    root_context = {"shared": "S" * 1000}

    fabric = OrchorbitalFabric()
    node = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        obligations=("work",),
        node_id="SDK-NODE",
        join_to_caller=False,
    )
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root(root_context)
    contexts.inherit_from_caller(node.node_id, set_values={"local": "delta"})
    full_packet = contexts.packet(node.node_id)

    task = {
        "task_id": "sdk-task",
        "payload": {PACKET_PAYLOAD_KEY: full_packet},
    }

    worker = GremlinWorkerClient(
        object(),
        worker_id="sdk-cache",
        species=["SPIDER"],
        handler=lambda batch: [
            {"task_id": row["task_id"], "output": {"ok": True}}
            for row in batch["tasks"]
        ],
        max_batch=1,
        max_context_frames=8,
    )

    responses = [
        {
            "lease_id": "lease-1",
            "species": "SPIDER",
            "lane_width": 1,
            "tasks": [task],
            "scheduler": {},
            "context_pack": {},
            "orchorbital_context_transport": {},
        },
        {
            "status": "CANDIDATE",
            "authority": {"canon_allowed": False},
        },
        {
            "lease_id": None,
            "species": None,
            "tasks": [],
            "scheduler": {},
        },
    ]

    async def fake_call(client, tool, arguments):
        calls.append((tool, dict(arguments)))
        return responses.pop(0)

    monkeypatch.setattr(worker, "_call", fake_call)

    async def exercise() -> None:
        receipt = await worker._run_once(object(), species="SPIDER")
        assert receipt is not None
        assert worker._context_cache
        idle = await worker._run_once(object(), species="SPIDER")
        assert idle is None

    asyncio.run(exercise())

    claim_calls = [args for tool, args in calls if tool == "gremlin_worker_claim"]
    assert claim_calls[0]["known_context_frames"] == []
    assert set(claim_calls[1]["known_context_frames"]) == set(worker._context_cache)


def test_worker_sdk_rejects_unverifiable_context_before_handler(monkeypatch) -> None:
    called = False

    def handler(batch):
        nonlocal called
        called = True
        return []

    worker = GremlinWorkerClient(
        object(),
        worker_id="sdk-invalid",
        species=["SPIDER"],
        handler=handler,
        max_batch=1,
    )

    invalid_packet = {
        "schema": "GREMLIN_ORCHORBITAL_CONTEXT_PACKET_V0_1",
        "target_node_id": "X",
        "target_frame_commitment": "0" * 64,
        "target_materialized_commitment": "0" * 64,
        "required_base_frame_commitment": None,
        "frames": [],
        "packet_commitment": "0" * 64,
    }

    async def fake_call(client, tool, arguments):
        if tool == "gremlin_worker_claim":
            return {
                "lease_id": "lease",
                "species": "SPIDER",
                "tasks": [
                    {
                        "task_id": "bad",
                        "payload": {PACKET_PAYLOAD_KEY: invalid_packet},
                    }
                ],
            }
        raise AssertionError("submit must not be reached")

    monkeypatch.setattr(worker, "_call", fake_call)

    async def exercise() -> None:
        with pytest.raises(Exception, match="context verification failed"):
            await worker._run_once(object(), species="SPIDER")

    asyncio.run(exercise())
    assert called is False


def _bundle_claim_for_sdk():
    fabric, contexts, first, second = build_two_siblings()
    broker = WorkerBroker()
    broker.register_worker("sdk-bundle-source", ["SPIDER"], vector_width=64, max_batch=8)
    scheduler = {"phase36": [0.2] * 36}
    for node, task_id in ((first, "sdk-bundle-a"), (second, "sdk-bundle-b")):
        broker.enqueue(
            "SPIDER",
            {
                "input": {"query": "shared"},
                "_gremlin_scheduler": scheduler,
                PACKET_PAYLOAD_KEY: contexts.packet(node.node_id),
            },
            task_id=task_id,
        )
    lease = broker.claim("sdk-bundle-source", species="SPIDER", limit=2)
    assert lease["batch_size"] == 2
    assert lease[BUNDLE_PAYLOAD_KEY] is not None
    return contexts, first, second, lease


def test_worker_sdk_verifies_bundle_once_and_materializes_each_task(monkeypatch) -> None:
    contexts, first, second, lease = _bundle_claim_for_sdk()
    seen: dict[str, dict] = {}

    def handler(batch):
        for task in batch["tasks"]:
            materialized = task[ORBITAL_CONTEXT_MATERIALIZED_KEY]
            seen[task["task_id"]] = deepcopy(materialized)
            materialized["shared_problem"] = "HANDLER-MUTATION"
        return [
            {"task_id": task["task_id"], "output": {"ok": True}}
            for task in batch["tasks"]
        ]

    worker = GremlinWorkerClient(
        object(),
        worker_id="sdk-bundle-worker",
        species=["SPIDER"],
        handler=handler,
        max_batch=8,
        max_context_frames=16,
    )
    responses = [
        deepcopy(lease),
        {"status": "CANDIDATE", "authority": {"canon_allowed": False}},
    ]

    async def fake_call(client, tool, arguments):
        return responses.pop(0)

    monkeypatch.setattr(worker, "_call", fake_call)

    asyncio.run(worker._run_once(object(), species="SPIDER"))

    assert seen["sdk-bundle-a"] == contexts.materialize(first.node_id)
    assert seen["sdk-bundle-b"] == contexts.materialize(second.node_id)
    root_frame = contexts.frame("AUTH:ROOT").frame_commitment
    assert worker._context_cache[root_frame]["shared_problem"] != "HANDLER-MUTATION"
    assert len(worker._context_cache) >= 3


def test_worker_sdk_bundle_validation_is_transactional(monkeypatch) -> None:
    _, _, _, lease = _bundle_claim_for_sdk()
    tampered = deepcopy(lease)
    first_task = tampered["tasks"][0]
    first_task["payload"][BUNDLE_REF_PAYLOAD_KEY][
        "target_frame_commitment"
    ] = "0" * 64

    called = False

    def handler(batch):
        nonlocal called
        called = True
        return []

    worker = GremlinWorkerClient(
        object(),
        worker_id="sdk-bundle-invalid",
        species=["SPIDER"],
        handler=handler,
        max_batch=8,
        max_context_frames=16,
    )

    async def fake_call(client, tool, arguments):
        if tool == "gremlin_worker_claim":
            return tampered
        raise AssertionError("submit must not be reached")

    monkeypatch.setattr(worker, "_call", fake_call)

    async def exercise():
        with pytest.raises(Exception, match="transport commitment mismatch"):
            await worker._run_once(object(), species="SPIDER")

    asyncio.run(exercise())
    assert worker._context_cache == {}
    assert called is False


def test_worker_sdk_rejects_any_projected_payload_tamper_before_handler(monkeypatch) -> None:
    _, _, _, lease = _bundle_claim_for_sdk()
    tampered = deepcopy(lease)
    tampered["tasks"][0]["payload"]["input"]["query"] = "TAMPERED-AFTER-CLAIM"

    called = False

    def handler(batch):
        nonlocal called
        called = True
        return []

    worker = GremlinWorkerClient(
        object(),
        worker_id="sdk-transport-tamper",
        species=["SPIDER"],
        handler=handler,
        max_batch=8,
        max_context_frames=16,
    )

    async def fake_call(client, tool, arguments):
        if tool == "gremlin_worker_claim":
            return tampered
        raise AssertionError("submit must not be reached")

    monkeypatch.setattr(worker, "_call", fake_call)

    async def exercise():
        with pytest.raises(Exception, match="transport commitment mismatch"):
            await worker._run_once(object(), species="SPIDER")

    asyncio.run(exercise())
    assert worker._context_cache == {}
    assert called is False


def test_worker_sdk_per_task_context_cache_is_claim_transactional(monkeypatch) -> None:
    fabric, contexts, first, second = build_two_siblings()
    first_packet = contexts.packet(first.node_id)
    second_packet = contexts.packet(second.node_id)
    broken = deepcopy(second_packet)
    broken["frames"][-1]["set_values"]["local"] = "tampered"

    tasks = [
        {
            "task_id": "tx-a",
            "species": "SPIDER",
            "task_commitment": "1" * 64,
            "payload": {PACKET_PAYLOAD_KEY: first_packet},
        },
        {
            "task_id": "tx-b",
            "species": "SPIDER",
            "task_commitment": "2" * 64,
            "payload": {PACKET_PAYLOAD_KEY: broken},
        },
    ]

    called = False

    def handler(batch):
        nonlocal called
        called = True
        return []

    worker = GremlinWorkerClient(
        object(),
        worker_id="sdk-tx",
        species=["SPIDER"],
        handler=handler,
        max_batch=2,
        max_context_frames=16,
    )

    async def fake_call(client, tool, arguments):
        if tool == "gremlin_worker_claim":
            return {
                "lease_id": "lease-tx",
                "species": "SPIDER",
                "tasks": tasks,
            }
        raise AssertionError("submit must not be reached")

    monkeypatch.setattr(worker, "_call", fake_call)

    async def exercise():
        with pytest.raises(Exception, match="context verification failed"):
            await worker._run_once(object(), species="SPIDER")

    asyncio.run(exercise())
    assert worker._context_cache == {}
    assert called is False
