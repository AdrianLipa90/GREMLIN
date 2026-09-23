from __future__ import annotations

import hashlib
import json
from typing import Any

from gremlin_mcp.user_task_gateway import build_user_task_plan

SCHEMA = "GREMLIN_USER_TASK_ADMISSION_V0_1"
VERSION = "0.1.0"
AUTHORITY = "HOST_ADMISSION_CANDIDATE_ONLY"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def build_user_turn_admission(
    prompt: str,
    *,
    current_task: str | None = None,
    active_path: str | None = None,
    recent_summary: str | None = None,
    request_id: str | None = None,
    surface_root: str = "/dev/shm/ciel_noema",
) -> dict[str, Any]:
    """Build a deterministic host preflight for one user turn.

    Host context is supplied as bounded context to the gateway. The gateway
    decides whether that context may affect semantic specialist membership:
    continuation/deictic prompts may use it; explicit new tasks remain task-only.
    """
    context: list[str] = []
    context_labels: list[str] = []
    for label, value in (
        ("current_task", current_task),
        ("active_path", active_path),
        ("recent_summary", recent_summary),
    ):
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        context.append(text)
        context_labels.append(label)

    plan = build_user_task_plan(
        prompt,
        context=context or None,
        request_id=request_id,
        surface_root=surface_root,
    )
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "request_id": request_id,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "context_labels": context_labels,
        "context_commitments": [
            hashlib.sha256(item.encode("utf-8")).hexdigest()
            for item in context
        ],
        "context_routing": plan["context_routing"],
        "plan_sha256": plan["plan_sha256"],
        "route_species": plan["execution"]["route_species"],
        "phasenav_state_id": plan["phasenav"]["state_id"],
        "host_tool_hints": plan["execution"]["host_tool_hints"],
        "external_effects_authorized": False,
        "canon_allowed": False,
        "authority": AUTHORITY,
    }
    core["admission_sha256"] = _sha(core)
    return {
        **core,
        "status": "READY",
        "plan": plan,
    }


__all__ = ["SCHEMA", "VERSION", "build_user_turn_admission"]
