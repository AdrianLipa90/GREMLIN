from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any, Awaitable, Callable, Iterable, Mapping

from mcp import Client

BatchHandler = Callable[[dict[str, Any]], Iterable[Mapping[str, Any]] | Awaitable[Iterable[Mapping[str, Any]]]]


class GremlinWorkerClientError(RuntimeError):
    pass


def _extract_mapping(result: Any) -> dict[str, Any]:
    """Extract a structured mapping from an MCP tool result.

    MCP v2 exposes ``structured_content`` for structured tool responses. The
    text fallback keeps the worker helper tolerant of clients/servers that only
    surface the JSON payload as a text content block.
    """
    if getattr(result, "is_error", False):
        raise GremlinWorkerClientError("GREMLIN MCP tool call returned an error")

    structured = getattr(result, "structured_content", None)
    if isinstance(structured, Mapping):
        return dict(structured)

    for block in getattr(result, "content", ()):
        text = getattr(block, "text", None)
        if not isinstance(text, str):
            continue
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(value, Mapping):
            return dict(value)

    raise GremlinWorkerClientError("GREMLIN MCP tool result did not contain a structured mapping")


class GremlinWorkerClient:
    """Small SDK for plugging an external backend into a GREMLIN animal role.

    ``target`` may be a Streamable HTTP URL (for a separate worker process) or
    an in-process MCP server object (useful for embedding/tests). The handler is
    batch-oriented on purpose: it receives the entire same-species lease so a
    backend can vectorize or otherwise fuse work before returning CANDIDATE
    outputs.
    """

    def __init__(
        self,
        target: Any,
        *,
        worker_id: str,
        species: Iterable[str],
        handler: BatchHandler,
        capabilities: Iterable[str] = (),
        vector_width: int = 8,
        max_batch: int = 128,
    ) -> None:
        self.target = target
        self.worker_id = str(worker_id)
        self.species = tuple(str(name).upper() for name in species)
        self.handler = handler
        self.capabilities = tuple(str(value) for value in capabilities)
        self.vector_width = int(vector_width)
        self.max_batch = int(max_batch)
        if not self.worker_id.strip():
            raise ValueError("worker_id is required")
        if not self.species:
            raise ValueError("at least one species is required")
        if self.vector_width <= 0:
            raise ValueError("vector_width must be positive")
        if self.max_batch <= 0:
            raise ValueError("max_batch must be positive")

    async def _call(self, client: Client, tool: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        result = await client.call_tool(tool, dict(arguments))
        return _extract_mapping(result)

    async def _register(self, client: Client) -> dict[str, Any]:
        return await self._call(
            client,
            "gremlin_worker_register",
            {
                "worker_id": self.worker_id,
                "species": list(self.species),
                "capabilities": list(self.capabilities),
                "vector_width": self.vector_width,
                "max_batch": self.max_batch,
            },
        )

    async def _run_once(self, client: Client, *, species: str | None = None) -> dict[str, Any] | None:
        claim = await self._call(
            client,
            "gremlin_worker_claim",
            {
                "worker_id": self.worker_id,
                "species": species,
                "limit": self.max_batch,
            },
        )
        lease_id = claim.get("lease_id")
        tasks = claim.get("tasks", [])
        if not lease_id or not tasks:
            return None

        envelope = {
            "schema": "GREMLIN_MCP_WORKER_BATCH_V0_2",
            "worker_id": self.worker_id,
            "lease_id": str(lease_id),
            "species": claim.get("species"),
            "lane_width": claim.get("lane_width"),
            "omega": claim.get("omega"),
            "tasks": tasks,
        }
        produced = self.handler(envelope)
        if inspect.isawaitable(produced):
            produced = await produced
        rows = [dict(row) for row in produced]

        expected = {str(task["task_id"]) for task in tasks}
        supplied = {str(row.get("task_id", "")) for row in rows}
        if supplied != expected or len(rows) != len(expected):
            raise GremlinWorkerClientError("handler must return exactly one result per claimed task")
        for row in rows:
            if "output" not in row:
                raise GremlinWorkerClientError("handler result requires output")
            row["status"] = "CANDIDATE"

        return await self._call(
            client,
            "gremlin_worker_submit",
            {
                "worker_id": self.worker_id,
                "lease_id": str(lease_id),
                "results": rows,
            },
        )

    async def run_once(self, *, species: str | None = None) -> dict[str, Any] | None:
        """Connect, register, process at most one lease, then disconnect."""
        async with Client(self.target) as client:
            await self._register(client)
            return await self._run_once(client, species=species)

    async def serve(
        self,
        *,
        poll_interval: float = 0.25,
        species: str | None = None,
        idle_exit_after: int | None = None,
    ) -> None:
        """Keep one MCP session open and continuously consume leased batches.

        ``idle_exit_after`` is mainly useful for deterministic jobs/tests. Leave
        it ``None`` for a resident worker.
        """
        delay = float(poll_interval)
        if delay < 0.0:
            raise ValueError("poll_interval must be non-negative")
        if idle_exit_after is not None and int(idle_exit_after) <= 0:
            raise ValueError("idle_exit_after must be positive when supplied")

        idle = 0
        async with Client(self.target) as client:
            await self._register(client)
            while True:
                receipt = await self._run_once(client, species=species)
                if receipt is None:
                    idle += 1
                    if idle_exit_after is not None and idle >= int(idle_exit_after):
                        return
                    await asyncio.sleep(delay)
                    continue
                idle = 0
