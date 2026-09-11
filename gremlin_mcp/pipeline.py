from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any
import uuid

from gremlin_mcp.workers import WorkerBroker

PIPELINE_SCHEMA = "GREMLIN_MCP_BESTIARY_PIPELINE_V0_4"
SPECIALISTS = ("SPIDER", "RAVEN", "HOUND", "MOLE", "OWL", "ANT", "MANTIS")


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("pipeline data must be finite JSON") from exc


def _authority() -> dict[str, bool]:
    return {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False}


def _strict_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field} must be non-empty")
    return text


def _string_sequence(values: Iterable[str], field: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, Mapping)) or not isinstance(values, Iterable):
        raise ValueError(f"{field} must be an iterable of strings")
    rows: list[str] = []
    for index, raw in enumerate(values):
        rows.append(_strict_text(raw, f"{field}[{index}]"))
    if not rows:
        raise ValueError(f"{field} must be non-empty")
    return tuple(rows)


def _normalize_species(values: Iterable[str]) -> tuple[str, ...]:
    out: list[str] = []
    for raw in _string_sequence(values, "species"):
        name = raw.upper()
        if name not in SPECIALISTS:
            raise ValueError(f"fanout species must be a specialist: {raw!r}")
        if name not in out:
            out.append(name)
    return tuple(out)


def _request_id(value: str | None) -> str:
    if value is None:
        return uuid.uuid4().hex
    rid = _strict_text(value, "request_id")
    if len(rid) > 64:
        raise ValueError("request_id must contain 1..64 characters")
    return rid


def fanout(
    broker: WorkerBroker,
    payload: Mapping[str, Any],
    species: Iterable[str],
    *,
    request_id: str | None = None,
    route_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Fan one payload out to selected specialist animals."""
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be a mapping")
    body = dict(payload)
    _canonical(body)
    roles = _normalize_species(species)
    rid = _request_id(request_id)

    route_meta: dict[str, Any] | None = None
    if route_context is not None:
        if not isinstance(route_context, Mapping):
            raise ValueError("route_context must be a mapping")
        route_meta = dict(route_context)
        _canonical(route_meta)

    digest_input: dict[str, Any] = {"request_id": rid, "payload": body, "species": roles}
    if route_meta is not None:
        digest_input["route_context"] = route_meta
    digest = hashlib.blake2b(b"GREMLIN-MCP-FANOUT/v0.4\x00" + _canonical(digest_input), digest_size=16).hexdigest()

    rows: list[dict[str, Any]] = []
    for name in roles:
        task_id = f"{rid[:48]}-{name.lower()}-{digest[:12]}"
        task_payload: dict[str, Any] = {"schema": PIPELINE_SCHEMA, "request_id": rid, "route_species": name, "payload": body}
        if route_meta is not None:
            task_payload["route_context"] = route_meta
        task = broker.enqueue(name, task_payload, task_id=task_id)
        rows.append({"species": name, "task_id": task_id, "task_commitment": task["task_commitment"]})

    result = {
        "schema": PIPELINE_SCHEMA, "request_id": rid, "route_mask": list(roles), "tasks": rows,
        "status": "SPECIALISTS_QUEUED", "authority": _authority(),
    }
    if route_meta is not None:
        result["route_context"] = route_meta
    return result


def collect(broker: WorkerBroker, task_ids: Iterable[str]) -> dict[str, Any]:
    ids = _string_sequence(task_ids, "task_ids")
    rows = [broker.task_result(task_id) for task_id in ids]
    done = [row for row in rows if row["state"] == "DONE"]
    return {
        "schema": PIPELINE_SCHEMA, "task_count": len(rows), "done_count": len(done),
        "complete": len(done) == len(rows), "tasks": rows, "authority": _authority(),
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

    candidates = [
        {
            "species": task["species"], "task_id": task["task_id"],
            "task_commitment": task["task_commitment"], "result_commitment": task["result_commitment"],
            "candidate": task["result"],
        }
        for task in collected["tasks"]
    ]

    rid = _request_id(request_id)
    bundle = {
        "schema": PIPELINE_SCHEMA, "request_id": rid, "stage": "BELZEBUB_SYNTHESIS",
        "specialist_candidates": candidates,
    }
    digest = hashlib.blake2b(b"GREMLIN-MCP-SYNTHESIS/v0.4\x00" + _canonical(bundle), digest_size=16).hexdigest()
    task_id = f"{rid[:48]}-belzebub-{digest[:12]}"
    task = broker.enqueue("BELZEBUB", bundle, task_id=task_id)
    return {
        "schema": PIPELINE_SCHEMA, "request_id": rid, "status": "BELZEBUB_QUEUED", "task_id": task_id,
        "task_commitment": task["task_commitment"], "specialist_count": len(candidates), "authority": _authority(),
    }
