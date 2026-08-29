from __future__ import annotations

import asyncio

import pytest

from gremlin_mcp.pipeline import collect, enqueue_synthesis, fanout
from gremlin_mcp.workers import WorkerBroker


def _finish_one(broker: WorkerBroker, worker_id: str, species: str) -> None:
    broker.register_worker(worker_id, [species], max_batch=8)
    lease = broker.claim(worker_id, species=species, limit=8)
    assert lease["lease_id"]
    broker.submit(
        worker_id,
        lease["lease_id"],
        [
            {
                "task_id": task["task_id"],
                "output": {"species": species, "candidate": task["payload"]["payload"]},
            }
            for task in lease["tasks"]
        ],
    )


def test_explicit_fanout_collect_then_belzebub() -> None:
    broker = WorkerBroker()
    routed = fanout(
        broker,
        {"problem": "find relations and contradictions"},
        ["SPIDER", "HOUND", "OWL"],
        request_id="pipeline-test",
    )
    assert routed["status"] == "SPECIALISTS_QUEUED"
    assert routed["route_mask"] == ["SPIDER", "HOUND", "OWL"]
    task_ids = [row["task_id"] for row in routed["tasks"]]
    assert collect(broker, task_ids)["complete"] is False

    with pytest.raises(RuntimeError, match="not complete"):
        enqueue_synthesis(broker, task_ids, request_id="pipeline-test")

    _finish_one(broker, "worker-spider", "SPIDER")
    _finish_one(broker, "worker-hound", "HOUND")
    _finish_one(broker, "worker-owl", "OWL")

    collected = collect(broker, task_ids)
    assert collected["complete"] is True
    assert collected["done_count"] == 3
    synthesis = enqueue_synthesis(broker, task_ids, request_id="pipeline-test")
    assert synthesis["status"] == "BELZEBUB_QUEUED"
    assert synthesis["specialist_count"] == 3
    assert broker.task_result(synthesis["task_id"])["species"] == "BELZEBUB"


def test_fanout_rejects_non_specialist_route() -> None:
    broker = WorkerBroker()
    with pytest.raises(ValueError, match="must be a specialist"):
        fanout(broker, {"x": 1}, ["BELZEBUB"], request_id="bad-route")


def test_mcp_discovery_contains_pipeline_tools() -> None:
    from mcp import Client
    from gremlin_mcp.server import mcp

    async def exercise() -> None:
        async with Client(mcp) as client:
            listed = await client.list_tools()
            names = {tool.name for tool in listed.tools}
            assert {"gremlin_fanout", "gremlin_collect", "gremlin_synthesize"} <= names

    asyncio.run(exercise())
