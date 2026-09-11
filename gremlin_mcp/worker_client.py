from __future__ import annotations

import asyncio
import inspect
import json
import math
from collections.abc import Iterable, Mapping
from typing import Any, Awaitable, Callable

from mcp import Client

BatchHandler = Callable[[dict[str, Any]], Iterable[Mapping[str, Any]] | Awaitable[Iterable[Mapping[str, Any]]]]


class GremlinWorkerClientError(RuntimeError):
    pass


def _strict_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field} must be non-empty")
    return text


def _strict_string_sequence(values: Iterable[str], field: str, *, allow_empty: bool) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, Mapping)) or not isinstance(values, Iterable):
        raise ValueError(f"{field} must be an iterable of strings")
    rows = tuple(_strict_text(value, f"{field}[{index}]") for index, value in enumerate(values))
    if not rows and not allow_empty:
        raise ValueError(f"{field} must be non-empty")
    return rows


def _strict_positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if value <= 0:
        raise ValueError(f"{field} must be positive")
    return value


def _strict_nonnegative_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise ValueError(f"{field} must be a non-negative finite number")
    return number


def _extract_mapping(result: Any) -> dict[str, Any]:
    """Extract a structured mapping from an MCP tool result."""
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


def _mapping_rows(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise GremlinWorkerClientError(f"{field} must be a list")
    if any(not isinstance(row, Mapping) for row in value):
        raise GremlinWorkerClientError(f"{field} must contain only objects")
    return [dict(row) for row in value]


class GremlinWorkerClient:
    """Small SDK for plugging an external backend into a GREMLIN animal role."""

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
        if not callable(handler):
            raise ValueError("handler must be callable")
        self.target = target
        self.worker_id = _strict_text(worker_id, "worker_id")
        self.species = tuple(value.upper() for value in _strict_string_sequence(species, "species", allow_empty=False))
        self.handler = handler
        self.capabilities = _strict_string_sequence(capabilities, "capabilities", allow_empty=True)
        self.vector_width = _strict_positive_int(vector_width, "vector_width")
        self.max_batch = _strict_positive_int(max_batch, "max_batch")

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
        requested_species = None if species is None else _strict_text(species, "species").upper()
        claim = await self._call(
            client,
            "gremlin_worker_claim",
            {"worker_id": self.worker_id, "species": requested_species, "limit": self.max_batch},
        )
        lease_id = claim.get("lease_id")
        raw_tasks = claim.get("tasks")
        if lease_id is None and raw_tasks in (None, []):
            return None
        if lease_id is None:
            raise GremlinWorkerClientError("worker claim supplied tasks without lease_id")
        if raw_tasks is None:
            raise GremlinWorkerClientError("worker claim supplied lease_id without tasks")
        if not isinstance(lease_id, str) or not lease_id.strip():
            raise GremlinWorkerClientError("worker claim lease_id must be a non-empty string")
        tasks = _mapping_rows(raw_tasks, "worker claim tasks")
        if not tasks:
            raise GremlinWorkerClientError("worker claim lease_id requires at least one task")

        expected: set[str] = set()
        for index, task in enumerate(tasks):
            task_id = task.get("task_id")
            if not isinstance(task_id, str) or not task_id.strip():
                raise GremlinWorkerClientError(f"worker claim task {index} requires a non-empty string task_id")
            if task_id in expected:
                raise GremlinWorkerClientError("worker claim contains duplicate task_id")
            expected.add(task_id)

        envelope = {
            "schema": "GREMLIN_MCP_WORKER_BATCH_V0_2",
            "worker_id": self.worker_id,
            "lease_id": lease_id,
            "species": claim.get("species"),
            "lane_width": claim.get("lane_width"),
            "omega": claim.get("omega"),
            "tasks": tasks,
        }
        produced = self.handler(envelope)
        if inspect.isawaitable(produced):
            produced = await produced
        if isinstance(produced, (str, bytes, Mapping)) or not isinstance(produced, Iterable):
            raise GremlinWorkerClientError("handler must return an iterable of result objects")
        rows: list[dict[str, Any]] = []
        for index, row in enumerate(produced):
            if not isinstance(row, Mapping):
                raise GremlinWorkerClientError(f"handler result {index} must be an object")
            rows.append(dict(row))

        supplied: set[str] = set()
        for index, row in enumerate(rows):
            task_id = row.get("task_id")
            if not isinstance(task_id, str) or not task_id.strip():
                raise GremlinWorkerClientError(f"handler result {index} requires a non-empty string task_id")
            if task_id in supplied:
                raise GremlinWorkerClientError("handler returned duplicate task_id")
            supplied.add(task_id)
            if "output" not in row:
                raise GremlinWorkerClientError("handler result requires output")
            row["status"] = "CANDIDATE"

        if supplied != expected or len(rows) != len(expected):
            raise GremlinWorkerClientError("handler must return exactly one result per claimed task")

        return await self._call(
            client,
            "gremlin_worker_submit",
            {"worker_id": self.worker_id, "lease_id": lease_id, "results": rows},
        )

    async def run_once(self, *, species: str | None = None) -> dict[str, Any] | None:
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
        delay = _strict_nonnegative_number(poll_interval, "poll_interval")
        idle_limit = None if idle_exit_after is None else _strict_positive_int(idle_exit_after, "idle_exit_after")
        requested_species = None if species is None else _strict_text(species, "species").upper()

        idle = 0
        async with Client(self.target) as client:
            await self._register(client)
            while True:
                receipt = await self._run_once(client, species=requested_species)
                if receipt is None:
                    idle += 1
                    if idle_limit is not None and idle >= idle_limit:
                        return
                    await asyncio.sleep(delay)
                    continue
                idle = 0
