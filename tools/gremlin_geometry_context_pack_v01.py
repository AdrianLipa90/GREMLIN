from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from tools.gremlin_geometry_phase_scheduler_v01 import SCHEDULER_KEY

SCHEMA = "GREMLIN_GEOMETRY_CONTEXT_PACK_V0_1"
DOMAIN = b"GREMLIN-GEOMETRY-CONTEXT-PACK/v0.1\x00"


class ContextPackError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ContextPackError("context pack values must be finite JSON") from exc


def _core(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {str(k): v for k, v in payload.items() if str(k) != SCHEDULER_KEY}


def _lcp(values: Sequence[str]) -> str:
    if not values:
        return ""
    prefix = values[0]
    for value in values[1:]:
        n = min(len(prefix), len(value))
        i = 0
        while i < n and prefix[i] == value[i]:
            i += 1
        prefix = prefix[:i]
        if not prefix:
            break
    return prefix


def _lcs(values: Sequence[str], *, prefix_len: int) -> str:
    if not values:
        return ""
    # Prevent shared prefix and suffix from overlapping on the shortest value.
    max_suffix = max(0, min(len(v) for v in values) - prefix_len)
    suffix = values[0][-max_suffix:] if max_suffix else ""
    for value in values[1:]:
        candidate = value[-max_suffix:] if max_suffix else ""
        n = min(len(suffix), len(candidate))
        i = 0
        while i < n and suffix[-(i + 1)] == candidate[-(i + 1)]:
            i += 1
        suffix = suffix[len(suffix) - i :] if i else ""
        if not suffix:
            break
    return suffix


def pack_context(
    tasks: Sequence[Mapping[str, Any]],
    *,
    min_shared_string_chars: int = 12,
) -> dict[str, Any]:
    """Losslessly factor repeated semantic payload context across one batch.

    Scheduler metadata is intentionally excluded from the model-facing context
    pack but remains in the committed worker task payload and lineage.
    """
    if not tasks:
        raise ContextPackError("context pack requires at least one task")
    if isinstance(min_shared_string_chars, bool) or not isinstance(min_shared_string_chars, int) or min_shared_string_chars < 1:
        raise ContextPackError("min_shared_string_chars must be a positive integer")

    ids: list[str] = []
    payloads: dict[str, dict[str, Any]] = {}
    for index, task in enumerate(tasks):
        if not isinstance(task, Mapping):
            raise ContextPackError(f"task {index} must be an object")
        task_id = task.get("task_id")
        payload = task.get("payload")
        if not isinstance(task_id, str) or not task_id:
            raise ContextPackError(f"task {index} requires task_id")
        if task_id in payloads:
            raise ContextPackError("context pack task IDs must be unique")
        if not isinstance(payload, Mapping):
            raise ContextPackError(f"task {index} requires payload")
        ids.append(task_id)
        payloads[task_id] = _core(payload)

    common_keys = set(payloads[ids[0]])
    for task_id in ids[1:]:
        common_keys &= set(payloads[task_id])

    shared_values: dict[str, Any] = {}
    string_factors: dict[str, dict[str, Any]] = {}
    factored_keys: set[str] = set()

    for key in sorted(common_keys):
        values = [payloads[task_id][key] for task_id in ids]
        first = values[0]
        if all(value == first for value in values[1:]):
            shared_values[key] = first
            factored_keys.add(key)
            continue
        if all(isinstance(value, str) for value in values):
            strings = [str(value) for value in values]
            prefix = _lcp(strings)
            suffix = _lcs(strings, prefix_len=len(prefix))
            if len(prefix) + len(suffix) >= min_shared_string_chars:
                middles = {
                    task_id: value[
                        len(prefix) : len(value) - len(suffix) if suffix else None
                    ]
                    for task_id, value in zip(ids, strings)
                }
                string_factors[key] = {
                    "prefix": prefix,
                    "suffix": suffix,
                    "middle_by_task": middles,
                }
                factored_keys.add(key)

    residual_by_task: dict[str, dict[str, Any]] = {}
    for task_id in ids:
        residual_by_task[task_id] = {
            key: value
            for key, value in payloads[task_id].items()
            if key not in factored_keys
        }

    pack_core = {
        "schema": SCHEMA,
        "task_ids": ids,
        "shared_values": shared_values,
        "string_factors": string_factors,
        "residual_by_task": residual_by_task,
    }
    raw_bytes = sum(len(_canonical(payloads[task_id])) for task_id in ids)
    packed_bytes = len(_canonical(pack_core))
    digest = hashlib.blake2b(DOMAIN + _canonical(pack_core), digest_size=32).hexdigest()

    return {
        **pack_core,
        "context_commitment": digest,
        "raw_semantic_bytes": raw_bytes,
        "packed_context_bytes": packed_bytes,
        "byte_saving_fraction": (
            0.0 if raw_bytes <= 0 else 1.0 - packed_bytes / raw_bytes
        ),
        "scheduler_metadata_included": False,
        "lossless_semantic_payload_core": True,
        "actual_model_token_accounting": False,
        "token_saving_claim": False,
    }


def unpack_context(pack: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(pack, Mapping) or pack.get("schema") != SCHEMA:
        raise ContextPackError("invalid context pack schema")
    task_ids = pack.get("task_ids")
    shared = pack.get("shared_values")
    factors = pack.get("string_factors")
    residual = pack.get("residual_by_task")
    if not isinstance(task_ids, list) or any(not isinstance(x, str) or not x for x in task_ids):
        raise ContextPackError("context pack task_ids are invalid")
    if not isinstance(shared, Mapping) or not isinstance(factors, Mapping) or not isinstance(residual, Mapping):
        raise ContextPackError("context pack mappings are invalid")

    out: dict[str, dict[str, Any]] = {}
    for task_id in task_ids:
        row = dict(shared)
        raw_residual = residual.get(task_id)
        if not isinstance(raw_residual, Mapping):
            raise ContextPackError("context pack residual is missing")
        row.update(dict(raw_residual))
        for key, raw_factor in factors.items():
            if not isinstance(key, str) or not isinstance(raw_factor, Mapping):
                raise ContextPackError("invalid string factor")
            prefix = raw_factor.get("prefix")
            suffix = raw_factor.get("suffix")
            middles = raw_factor.get("middle_by_task")
            if not isinstance(prefix, str) or not isinstance(suffix, str) or not isinstance(middles, Mapping):
                raise ContextPackError("invalid string factor fields")
            middle = middles.get(task_id)
            if not isinstance(middle, str):
                raise ContextPackError("missing string factor middle")
            row[key] = prefix + middle + suffix
        out[task_id] = row
    return out


def context_pack_prompt(pack: Mapping[str, Any]) -> str:
    """Canonical model-facing representation for tokenizer benchmarks/workers."""
    core = {
        "schema": pack.get("schema"),
        "task_ids": pack.get("task_ids"),
        "shared_values": pack.get("shared_values"),
        "string_factors": pack.get("string_factors"),
        "residual_by_task": pack.get("residual_by_task"),
    }
    return _canonical(core).decode("utf-8")


def naive_batch_prompt(tasks: Sequence[Mapping[str, Any]]) -> str:
    rows = []
    for task in tasks:
        task_id = task.get("task_id")
        payload = task.get("payload")
        if not isinstance(task_id, str) or not isinstance(payload, Mapping):
            raise ContextPackError("invalid task for naive prompt")
        rows.append({"task_id": task_id, "payload": _core(payload)})
    return _canonical({"schema": "GREMLIN_NAIVE_BATCH_PROMPT_V0_1", "tasks": rows}).decode("utf-8")
