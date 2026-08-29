#!/usr/bin/env python3
"""Minimal external GREMLIN MCP animal worker.

Start GREMLIN first:

    gremlin-mcp --transport streamable-http --host 127.0.0.1 --port 8766

Then run this file. Replace ``spider_handler`` with a model, graph engine, search
backend, local toolchain, or any other batch-aware implementation.
"""
from __future__ import annotations

import asyncio
from typing import Any

from gremlin_mcp.worker_client import GremlinWorkerClient


async def spider_handler(batch: dict[str, Any]) -> list[dict[str, Any]]:
    # Demonstration only: preserve the external worker contract without
    # pretending this echo is SPIDER's real relation/isomorphism analysis.
    return [
        {
            "task_id": task["task_id"],
            "output": {
                "demo": True,
                "received_payload": task["payload"],
            },
        }
        for task in batch["tasks"]
    ]


async def main() -> None:
    worker = GremlinWorkerClient(
        "http://127.0.0.1:8766/mcp",
        worker_id="example-spider",
        species=["SPIDER"],
        handler=spider_handler,
        capabilities=["relations", "isomorphisms"],
        vector_width=8,
        max_batch=32,
    )
    await worker.serve(poll_interval=0.25)


if __name__ == "__main__":
    asyncio.run(main())
