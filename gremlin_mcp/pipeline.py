from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping
import uuid

from gremlin_mcp.workers import WorkerBroker

PIPELINE_SCHEMA = "GREMLIN_MCP_BESTIARY_PIPELINE_V0_4"
SPECIALISTS = ("SPIDER", "RAVEN", "HOUND", "MOLE", "OWL", "ANT", "MANTIS")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _normalize_species(values: Iterable[str]) -> tuple[str, ...]:
    out: list[str] = []
    for raw in values:
        name = str(raw).strip().upper()
        if name not in SPECIALISTS:
            raise ValueError(f"fanout species must be a specialist: {raw!r}")
        if name not in out:
            out.append(name)
    if not out:
        raise ValueError("at least one specialist is required")
    return tuple(out)


def fanout(
    broker: WorkerBroker,
    payload: Mapping[str, Any],
    species: Iterable[str],
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Explicitly fan one payload out to selected specialist animals.

    This is intentionally not an implicit OCTOPUS semantic router. The caller
    supplies the route mask, while GREMLIN owns task identity, lineage and the
    worker queue.
    """
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be a mapping")
    body = dict(payload)
    _canonical(body)
    roles = _normalize_species(species)
    rid = str(request_id or uuid.uuid4().hex).strip()
    if not rid or len(rid) > 64:
        raise ValueError("request_id must contain 1..64 characters")

    digest = hashlib.blake2b(
        b"GREMLIN-MCP-FANOUT/v0.4\x00" + _canonical({"request_id": rid, "payload": body, "species": roles}),
        digest_size=16,
    ).hexdigest()
    rows: list[dict[str, Any]] = []
    for name in roles:
        task_id = f"{rid[:48]}-{name.lower()}-{digest[:12]}"
        task = broker.enqueue(
            name,
            {
                "schema": PIPELINE_SCHEMA,
                "request_id": rid,
                "route_species": name,
                "payload": body,
            },
            task_id=task_id,
        )
        rows.append({"species": name, "task_id": task_id, "task_commitment": task["task_commitment"]})

    return {
        "schema": PIPELINE_SCHEMA,
        "request_id": rid,
        "route_mask": list(roles),
        "tasks": rows,
        "status": "SPECIALISTS_QUEUED",
        "authority": _authority(),
    }


def collect(broker: WorkerBroker, task_ids: Iterable[str]) -> dict[str, Any]:
    ids = tuple(str(value).strip() for value in task_ids)
    if not ids or any(not value for value in ids):
        raise ValueError("task_ids must be non-empty")
    rows = [broker.task_result(task_id) for task_id in ids]
    done = [row for row in rows if row["state"] == "DONE"]
    return {
        "schema": PIPELINE_SCHEMA,
        "task_count": len(rows),
        "done_count": len(done),
        "complete": len(done) == len(rows),
        "tasks": rows,
        "authority": _authority(),
    }


def enqueue_synthesis(
    broker: WorkerBroker,
    specialist_task_ids: Iterable[str],
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Queue BELZEBUB only after every supplied specialist task is DONE."""
    collected = collect(broker, specialist_task_ids)
    if not collected["complete"]:
        raise RuntimeError("specialist fanout is not complete")

    candidates = []
    for task in collected["tasks"]:
        candidates.append(
            {
                "species": task["species"],
                "task_id": task["task_id"],
                "task_commitment": task["task_commitment"],
                "result_commitment": task["result_commitment"],
                "candidate": task["result"],
            }
        )

    rid = str(request_id or uuid.uuid4().hex).strip()
    if not rid or len(rid) > 64:
        raise ValueError("request_id must contain 1..64 characters")
    bundle = {
        "schema": PIPELINE_SCHEMA,
        "request_id": rid,
        "stage": "BELZEBUB_SYNTHESIS",
        "specialist_candidates": candidates,
    }
    digest = hashlib.blake2b(
        b"GREMLIN-MCP-SYNTHESIS/v0.4\x00" + _canonical(bundle),
        digest_size=16,
    ).hexdigest()
    task_id = f"{rid[:48]}-belzebub-{digest[:12]}"
    task = broker.enqueue("BELZEBUB", bundle, task_id=task_id)
    return {
        "schema": PIPELINE_SCHEMA,
        "request_id": rid,
        "status": "BELZEBUB_QUEUED",
        "task_id": task_id,
        "task_commitment": task["task_commitment"],
        "specialist_count": len(candidates),
        "authority": _authority(),
    }
