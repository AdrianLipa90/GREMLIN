from __future__ import annotations

import asyncio
from copy import deepcopy
import inspect
import json
import math
from collections.abc import Iterable, Mapping
from typing import Any, Awaitable, Callable

from mcp import Client

from gremlin_mcp.orchorbital_context import (
    BUNDLE_PAYLOAD_KEY,
    BUNDLE_REF_PAYLOAD_KEY,
    BUNDLE_REF_SCHEMA,
    PACKET_PAYLOAD_KEY,
    apply_context_bundle,
    apply_context_packet,
)
from gremlin_mcp.workers import worker_transport_commitment

BatchHandler = Callable[[dict[str, Any]], Iterable[Mapping[str, Any]] | Awaitable[Iterable[Mapping[str, Any]]]]
ORBITAL_CONTEXT_MATERIALIZED_KEY = "orchorbital_context"


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
        max_context_frames: int = 4096,
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
        self.max_context_frames = _strict_positive_int(max_context_frames, "max_context_frames")
        if self.max_context_frames > 4096:
            raise ValueError("max_context_frames must be <= 4096")
        self._context_cache: dict[str, dict[str, Any]] = {}

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
            {
                "worker_id": self.worker_id,
                "species": requested_species,
                "limit": self.max_batch,
                "known_context_frames": list(self._context_cache),
            },
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
        context_packet_count = 0
        context_cache_hits = 0

        bundle = claim.get(BUNDLE_PAYLOAD_KEY)
        bundle_targets: Mapping[str, Any] = {}
        provisional_cache: dict[str, dict[str, Any]] | None = None
        active_bundle_commitment: str | None = None
        if bundle is not None:
            if not isinstance(bundle, Mapping):
                raise GremlinWorkerClientError("worker claim context bundle must be an object")
            try:
                decoded_bundle = apply_context_bundle(
                    bundle,
                    known_contexts=self._context_cache,
                )
            except ValueError as exc:
                raise GremlinWorkerClientError(
                    "worker claim context bundle verification failed"
                ) from exc
            active_bundle_commitment = bundle.get("bundle_commitment")
            if not isinstance(active_bundle_commitment, str):
                raise GremlinWorkerClientError(
                    "worker claim context bundle commitment is invalid"
                )
            raw_targets = decoded_bundle.get("task_targets")
            raw_updates = decoded_bundle.get("cache_updates")
            if not isinstance(raw_targets, Mapping) or not isinstance(raw_updates, Mapping):
                raise GremlinWorkerClientError("decoded context bundle is invalid")
            bundle_targets = raw_targets
            provisional_cache = deepcopy(self._context_cache)
            for commitment, materialized in raw_updates.items():
                if not isinstance(commitment, str) or not isinstance(materialized, Mapping):
                    raise GremlinWorkerClientError("context bundle cache update is invalid")
                provisional_cache[commitment] = deepcopy(dict(materialized))

        seen_bundle_targets: set[str] = set()
        for index, task in enumerate(tasks):
            task_id = task.get("task_id")
            if not isinstance(task_id, str) or not task_id.strip():
                raise GremlinWorkerClientError(f"worker claim task {index} requires a non-empty string task_id")
            if task_id in expected:
                raise GremlinWorkerClientError("worker claim contains duplicate task_id")
            expected.add(task_id)
            payload = task.get("payload")

            delivered_commitment = task.get("transport_commitment")
            requires_transport_commitment = (
                isinstance(payload, Mapping)
                and BUNDLE_REF_PAYLOAD_KEY in payload
            )
            if delivered_commitment is not None or requires_transport_commitment:
                if not isinstance(delivered_commitment, str):
                    raise GremlinWorkerClientError(
                        f"worker claim task {index} requires transport commitment"
                    )
                species_name = task.get("species")
                canonical_commitment = task.get("task_commitment")
                if (
                    not isinstance(species_name, str)
                    or not isinstance(canonical_commitment, str)
                    or not isinstance(payload, Mapping)
                ):
                    raise GremlinWorkerClientError(
                        f"worker claim task {index} transport metadata is invalid"
                    )
                try:
                    expected_transport = worker_transport_commitment(
                        task_id=task_id,
                        species=species_name,
                        task_commitment=canonical_commitment,
                        payload=payload,
                        bundle_commitment=active_bundle_commitment,
                    )
                except ValueError as exc:
                    raise GremlinWorkerClientError(
                        f"worker claim task {index} transport metadata is invalid"
                    ) from exc
                if delivered_commitment != expected_transport:
                    raise GremlinWorkerClientError(
                        f"worker claim task {index} transport commitment mismatch"
                    )
            if isinstance(payload, Mapping) and BUNDLE_REF_PAYLOAD_KEY in payload:
                if bundle is None or provisional_cache is None:
                    raise GremlinWorkerClientError(
                        f"worker claim task {index} has context reference without bundle"
                    )
                if PACKET_PAYLOAD_KEY in payload:
                    raise GremlinWorkerClientError(
                        f"worker claim task {index} mixes context packet and bundle reference"
                    )
                raw_ref = payload[BUNDLE_REF_PAYLOAD_KEY]
                if not isinstance(raw_ref, Mapping) or raw_ref.get("schema") != BUNDLE_REF_SCHEMA:
                    raise GremlinWorkerClientError(
                        f"worker claim task {index} has invalid context bundle reference"
                    )
                expected_target = bundle_targets.get(task_id)
                if not isinstance(expected_target, Mapping):
                    raise GremlinWorkerClientError(
                        f"worker claim task {index} is missing from context bundle targets"
                    )
                ref_core = {
                    "target_node_id": raw_ref.get("target_node_id"),
                    "target_frame_commitment": raw_ref.get("target_frame_commitment"),
                    "target_materialized_commitment": raw_ref.get(
                        "target_materialized_commitment"
                    ),
                }
                if ref_core != dict(expected_target):
                    raise GremlinWorkerClientError(
                        f"worker claim task {index} context reference mismatches bundle"
                    )
                target_commitment = raw_ref.get("target_frame_commitment")
                materialized = provisional_cache.get(target_commitment)
                if not isinstance(target_commitment, str) or not isinstance(
                    materialized, Mapping
                ):
                    raise GremlinWorkerClientError(
                        f"worker claim task {index} target context is unavailable"
                    )
                task[ORBITAL_CONTEXT_MATERIALIZED_KEY] = deepcopy(dict(materialized))
                context_packet_count += 1
                seen_bundle_targets.add(task_id)
                continue

            if isinstance(payload, Mapping) and PACKET_PAYLOAD_KEY in payload:
                raw_packet = payload[PACKET_PAYLOAD_KEY]
                if not isinstance(raw_packet, Mapping):
                    raise GremlinWorkerClientError(
                        f"worker claim task {index} has invalid orchorbital context packet"
                    )
                try:
                    decoded = apply_context_packet(
                        raw_packet,
                        known_contexts=self._context_cache,
                    )
                except ValueError as exc:
                    raise GremlinWorkerClientError(
                        f"worker claim task {index} context verification failed"
                    ) from exc
                context_packet_count += 1
                if raw_packet.get("required_base_frame_commitment") is not None:
                    context_cache_hits += 1
                updates = decoded.get("cache_updates")
                if not isinstance(updates, Mapping):
                    raise GremlinWorkerClientError("context cache updates are invalid")
                for commitment, materialized in updates.items():
                    if not isinstance(commitment, str) or not isinstance(materialized, Mapping):
                        raise GremlinWorkerClientError("context cache update is invalid")
                    if commitment in self._context_cache:
                        del self._context_cache[commitment]
                    self._context_cache[commitment] = deepcopy(dict(materialized))
                target_commitment = decoded.get("target_frame_commitment")
                materialized = decoded.get("materialized_context")
                if not isinstance(target_commitment, str) or not isinstance(materialized, Mapping):
                    raise GremlinWorkerClientError("decoded target context is invalid")
                if target_commitment in self._context_cache:
                    del self._context_cache[target_commitment]
                self._context_cache[target_commitment] = deepcopy(dict(materialized))
                while len(self._context_cache) > self.max_context_frames:
                    oldest = next(iter(self._context_cache))
                    del self._context_cache[oldest]
                task[ORBITAL_CONTEXT_MATERIALIZED_KEY] = deepcopy(dict(materialized))

        if bundle is not None:
            expected_bundle_targets = set(bundle_targets)
            if seen_bundle_targets != expected_bundle_targets:
                raise GremlinWorkerClientError(
                    "worker claim bundle targets must match task context references exactly"
                )
            if provisional_cache is None:
                raise GremlinWorkerClientError("context bundle cache staging is unavailable")
            self._context_cache = provisional_cache
            while len(self._context_cache) > self.max_context_frames:
                oldest = next(iter(self._context_cache))
                del self._context_cache[oldest]
            transport_receipt = claim.get("orchorbital_context_transport")
            if isinstance(transport_receipt, Mapping):
                reported_hits = transport_receipt.get("cache_hit_task_count", 0)
                if isinstance(reported_hits, bool) or not isinstance(reported_hits, int):
                    raise GremlinWorkerClientError(
                        "worker claim context cache-hit accounting is invalid"
                    )
                context_cache_hits += reported_hits

        envelope = {
            "schema": "GREMLIN_MCP_WORKER_BATCH_V0_2",
            "worker_id": self.worker_id,
            "lease_id": lease_id,
            "species": claim.get("species"),
            "lane_width": claim.get("lane_width"),
            "omega": claim.get("omega"),
            "scheduler": claim.get("scheduler"),
            "context_pack": claim.get("context_pack"),
            "orchorbital_context_transport": claim.get("orchorbital_context_transport"),
            BUNDLE_PAYLOAD_KEY: bundle,
            "orchorbital_context_cache": {
                "cached_frame_count": len(self._context_cache),
                "packet_task_count": context_packet_count,
                "cache_hit_task_count": context_cache_hits,
            },
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
