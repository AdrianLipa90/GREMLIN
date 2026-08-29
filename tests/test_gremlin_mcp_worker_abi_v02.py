from __future__ import annotations

import asyncio

import pytest

from gremlin_mcp.workers import WORKER_SCHEMA, WorkerBroker
from tools.gremlin_bestiary_vector_species_v03 import lane_width


def test_worker_register_claim_submit_roundtrip_is_candidate_only() -> None:
    broker = WorkerBroker()
    worker = broker.register_worker(
        "spider-test",
        ["SPIDER"],
        capabilities=["relations", "isomorphisms"],
        vector_width=8,
        max_batch=16,
    )
    assert worker["schema"] == WORKER_SCHEMA
    assert worker["species"] == ("SPIDER",)
    assert worker["authority"]["canon_allowed"] is False

    first = broker.enqueue("SPIDER", {"text": "alpha"}, task_id="task-a")
    second = broker.enqueue("SPIDER", {"text": "beta"}, task_id="task-b")
    assert first["state"] == "QUEUED"
    assert second["state"] == "QUEUED"

    lease = broker.claim("spider-test", species="SPIDER", limit=16)
    assert lease["species"] == "SPIDER"
    assert lease["batch_size"] == 2
    assert lease["batch_size"] <= lane_width("SPIDER", vector_width=8)
    claimed_ids = [task["task_id"] for task in lease["tasks"]]
    assert claimed_ids == ["task-a", "task-b"]

    receipt = broker.submit(
        "spider-test",
        lease["lease_id"],
        [
            {"task_id": "task-a", "status": "CANDIDATE", "output": {"edges": [["a", "b"]]}},
            {"task_id": "task-b", "output": {"edges": [["b", "c"]]}},
        ],
    )
    assert receipt["status"] == "CANDIDATE"
    assert receipt["authority"] == {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
    result = broker.task_result("task-a")
    assert result["state"] == "DONE"
    assert result["status"] == "CANDIDATE"
    assert result["result"] == {"edges": [["a", "b"]]}
    assert result["result_commitment"]


def test_worker_claim_is_lane_bounded() -> None:
    broker = WorkerBroker()
    broker.register_worker("mole-test", ["MOLE"], vector_width=8, max_batch=128)
    for i in range(100):
        broker.enqueue("MOLE", {"n": i}, task_id=f"mole-{i:03d}")
    lease = broker.claim("mole-test", limit=128)
    assert lease["batch_size"] == lane_width("MOLE", vector_width=8)
    assert len(lease["tasks"]) == lease["batch_size"]


def test_worker_submission_fails_closed_on_wrong_worker_or_partial_batch() -> None:
    broker = WorkerBroker()
    broker.register_worker("owl-a", ["OWL"])
    broker.register_worker("owl-b", ["OWL"])
    broker.enqueue("OWL", {"claim": 1}, task_id="owl-1")
    broker.enqueue("OWL", {"claim": 2}, task_id="owl-2")
    lease = broker.claim("owl-a", species="OWL", limit=2)

    with pytest.raises(ValueError, match="another worker"):
        broker.submit(
            "owl-b",
            lease["lease_id"],
            [
                {"task_id": "owl-1", "output": {}},
                {"task_id": "owl-2", "output": {}},
            ],
        )

    with pytest.raises(ValueError, match="exact claimed task set"):
        broker.submit(
            "owl-a",
            lease["lease_id"],
            [{"task_id": "owl-1", "output": {}}],
        )

    with pytest.raises(ValueError, match="must remain CANDIDATE"):
        broker.submit(
            "owl-a",
            lease["lease_id"],
            [
                {"task_id": "owl-1", "status": "CANON", "output": {}},
                {"task_id": "owl-2", "output": {}},
            ],
        )


def test_task_id_is_idempotent_only_for_identical_content() -> None:
    broker = WorkerBroker()
    a = broker.enqueue("HOUND", {"x": 1}, task_id="same")
    b = broker.enqueue("HOUND", {"x": 1}, task_id="same")
    assert a["task_commitment"] == b["task_commitment"]
    with pytest.raises(ValueError, match="different content"):
        broker.enqueue("HOUND", {"x": 2}, task_id="same")


def test_mcp_discovery_contains_worker_abi_tools() -> None:
    from mcp import Client
    from gremlin_mcp.server import mcp

    async def exercise() -> None:
        async with Client(mcp) as client:
            listed = await client.list_tools()
            names = {tool.name for tool in listed.tools}
            assert {
                "gremlin_worker_register",
                "gremlin_worker_heartbeat",
                "gremlin_worker_list",
                "gremlin_worker_enqueue",
                "gremlin_worker_claim",
                "gremlin_worker_submit",
                "gremlin_worker_result",
                "gremlin_worker_queue",
            } <= names

            reg = await client.call_tool(
                "gremlin_worker_register",
                {
                    "worker_id": "mcp-raven",
                    "species": ["RAVEN"],
                    "capabilities": ["memory"],
                    "vector_width": 8,
                    "max_batch": 8,
                },
            )
            assert reg.is_error is False
            queued = await client.call_tool(
                "gremlin_worker_enqueue",
                {"species": "RAVEN", "payload": {"query": "prior structure"}, "task_id": "mcp-task"},
            )
            assert queued.is_error is False
            claimed = await client.call_tool(
                "gremlin_worker_claim",
                {"worker_id": "mcp-raven", "species": "RAVEN", "limit": 8},
            )
            assert claimed.is_error is False

    asyncio.run(exercise())
