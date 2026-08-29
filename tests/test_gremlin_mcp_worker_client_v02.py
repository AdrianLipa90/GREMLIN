from __future__ import annotations

import asyncio

from gremlin_mcp.worker_client import GremlinWorkerClient
from gremlin_mcp.workers import broker


def test_worker_client_processes_same_species_batch_in_process() -> None:
    from gremlin_mcp.server import mcp

    task_ids = ["worker-client-spider-a", "worker-client-spider-b"]
    broker.enqueue("SPIDER", {"text": "alpha"}, task_id=task_ids[0])
    broker.enqueue("SPIDER", {"text": "beta"}, task_id=task_ids[1])

    seen: dict[str, object] = {}

    async def handler(batch: dict) -> list[dict]:
        seen["species"] = batch["species"]
        seen["count"] = len(batch["tasks"])
        return [
            {
                "task_id": task["task_id"],
                "output": {
                    "worker": "spider-sdk-test",
                    "echo": task["payload"]["text"],
                },
            }
            for task in batch["tasks"]
        ]

    async def exercise() -> None:
        worker = GremlinWorkerClient(
            mcp,
            worker_id="spider-sdk-test",
            species=["SPIDER"],
            handler=handler,
            capabilities=["relations"],
            vector_width=8,
            max_batch=8,
        )
        receipt = await worker.run_once(species="SPIDER")
        assert receipt is not None
        assert receipt["status"] == "CANDIDATE"
        assert receipt["authority"]["canon_allowed"] is False

    asyncio.run(exercise())

    assert seen == {"species": "SPIDER", "count": 2}
    for task_id, expected in zip(task_ids, ("alpha", "beta")):
        result = broker.task_result(task_id)
        assert result["state"] == "DONE"
        assert result["status"] == "CANDIDATE"
        assert result["result"]["echo"] == expected


def test_worker_client_resident_loop_can_exit_after_idle() -> None:
    from gremlin_mcp.server import mcp

    broker.enqueue("HOUND", {"claim": "x"}, task_id="worker-client-hound-a")
    calls = 0

    def handler(batch: dict) -> list[dict]:
        nonlocal calls
        calls += 1
        return [
            {"task_id": task["task_id"], "output": {"checked": True}}
            for task in batch["tasks"]
        ]

    async def exercise() -> None:
        worker = GremlinWorkerClient(
            mcp,
            worker_id="hound-sdk-test",
            species=["HOUND"],
            handler=handler,
            max_batch=4,
        )
        await worker.serve(
            species="HOUND",
            poll_interval=0.0,
            idle_exit_after=1,
        )

    asyncio.run(exercise())
    assert calls == 1
    assert broker.task_result("worker-client-hound-a")["state"] == "DONE"
