from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum
import hashlib
import json
from typing import Any, Iterable, Mapping

SCHEMA = "GREMLIN_DUAL_USE_CAPABILITY_LAYER_V0_1"
VERSION = "0.1.0"


class RiskClass(IntEnum):
    BENIGN = 0
    DUAL_USE_LOW = 1
    DUAL_USE_HIGH = 2
    RESTRICTED = 3


class Stage(StrEnum):
    DISCOVER = "DISCOVER"
    VALIDATE = "VALIDATE"
    SIMULATE = "SIMULATE"
    RED_TEAM = "RED_TEAM"
    DEFENSIVE_ENGINEERING = "DEFENSIVE_ENGINEERING"
    EXECUTE = "EXECUTE"


class Action(StrEnum):
    ANALYZE = "ANALYZE"
    SEARCH = "SEARCH"
    BENCHMARK = "BENCHMARK"
    SIMULATE = "SIMULATE"
    RED_TEAM = "RED_TEAM"
    MITIGATE = "MITIGATE"
    DETECT = "DETECT"
    PATCH = "PATCH"
    MONITOR = "MONITOR"
    EXPORT_CANDIDATE = "EXPORT_CANDIDATE"
    REQUEST_EXECUTION = "REQUEST_EXECUTION"
    EXECUTE = "EXECUTE"


SAFE_ANALYTIC_ACTIONS = {
    Action.ANALYZE,
    Action.SEARCH,
    Action.BENCHMARK,
    Action.SIMULATE,
    Action.RED_TEAM,
    Action.MITIGATE,
    Action.DETECT,
    Action.PATCH,
    Action.MONITOR,
    Action.EXPORT_CANDIDATE,
}

# RESTRICTED candidates are deliberately narrowed to defensive abstraction.
RESTRICTED_ACTIONS = {
    Action.ANALYZE,
    Action.MITIGATE,
    Action.DETECT,
    Action.PATCH,
    Action.MONITOR,
}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _parse_risk(value: RiskClass | str | int) -> RiskClass:
    if isinstance(value, RiskClass):
        return value
    if isinstance(value, int):
        return RiskClass(value)
    text = str(value).strip().upper()
    try:
        return RiskClass[text]
    except KeyError as exc:
        raise ValueError(f"unknown risk class: {value!r}") from exc


def inherit_risk(
    declared_risk: RiskClass | str | int | None,
    parent_risks: Iterable[RiskClass | str | int] = (),
    *,
    context_complete: bool = True,
) -> RiskClass:
    """Return monotonic risk: transformations may preserve or raise risk, never lower it."""
    parsed_parents = [_parse_risk(value) for value in parent_risks]
    if declared_risk is None:
        # Unknown classification is fail-closed rather than silently BENIGN.
        declared = RiskClass.DUAL_USE_HIGH
    else:
        declared = _parse_risk(declared_risk)
    if not context_complete:
        declared = max(declared, RiskClass.DUAL_USE_HIGH)
    return max([declared, *parsed_parents], default=declared)


def allowed_actions_for(risk: RiskClass | str | int) -> list[str]:
    rc = _parse_risk(risk)
    if rc is RiskClass.RESTRICTED:
        allowed = RESTRICTED_ACTIONS
    elif rc is RiskClass.DUAL_USE_HIGH:
        allowed = SAFE_ANALYTIC_ACTIONS
    else:
        allowed = SAFE_ANALYTIC_ACTIONS | {Action.REQUEST_EXECUTION}
    return sorted(action.value for action in allowed)


def capability_firewall(
    *,
    risk: RiskClass | str | int,
    requested_action: Action | str,
    human_gate: bool = False,
    tool_gate: bool = False,
    sandboxed: bool = True,
) -> dict[str, Any]:
    rc = _parse_risk(risk)
    action = requested_action if isinstance(requested_action, Action) else Action(str(requested_action).strip().upper())

    reason = "ACTION_ALLOWED_BY_POLICY"
    admitted = action.value in allowed_actions_for(rc)

    if action is Action.EXECUTE:
        # No DISCOVER -> EXECUTE shortcut. Execution is a separate admission domain.
        admitted = (
            rc <= RiskClass.DUAL_USE_LOW
            and human_gate
            and tool_gate
            and sandboxed
        )
        if not admitted:
            reason = "EXECUTION_REQUIRES_LOW_RISK_PLUS_HUMAN_AND_TOOL_GATES_IN_SANDBOX"
    elif action is Action.REQUEST_EXECUTION:
        admitted = rc <= RiskClass.DUAL_USE_LOW
        if not admitted:
            reason = "HIGH_OR_RESTRICTED_RISK_CANNOT_REQUEST_EXECUTION"
    elif not admitted:
        reason = "ACTION_BLOCKED_FOR_RISK_CLASS"

    decision_core = {
        "risk_class": rc.name,
        "requested_action": action.value,
        "human_gate": bool(human_gate),
        "tool_gate": bool(tool_gate),
        "sandboxed": bool(sandboxed),
        "admitted": bool(admitted),
        "reason": reason,
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **decision_core,
        "decision_commitment": _commit(b"GREMLIN-DUAL-USE-POLICY-DECISION/v0.1", decision_core),
        "production_runtime_write": False,
        "canon_allowed": False,
    }


def make_policy_envelope(
    *,
    object_kind: str,
    object_commitment: str,
    declared_risk: RiskClass | str | int | None,
    parent_risks: Iterable[RiskClass | str | int] = (),
    parent_commitments: Iterable[str] = (),
    source_refs: Iterable[str] = (),
    transformations: Iterable[str] = (),
    evidence_refs: Iterable[str] = (),
    confidence: float = 0.0,
    context_complete: bool = True,
) -> dict[str, Any]:
    if not 0.0 <= float(confidence) <= 1.0:
        raise ValueError("confidence must be in [0, 1]")
    risk = inherit_risk(
        declared_risk,
        parent_risks,
        context_complete=context_complete,
    )
    core = {
        "object_kind": str(object_kind).strip().upper(),
        "object_commitment": str(object_commitment).strip(),
        "source_refs": sorted({str(x) for x in source_refs if str(x).strip()}),
        "transformations": [str(x) for x in transformations],
        "evidence_refs": sorted({str(x) for x in evidence_refs if str(x).strip()}),
        "confidence": float(confidence),
        "risk_class": risk.name,
        "parent_commitments": sorted({str(x) for x in parent_commitments if str(x).strip()}),
        "allowed_actions": allowed_actions_for(risk),
        "context_complete": bool(context_complete),
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "kind": "DUAL_USE_POLICY_ENVELOPE",
        **core,
        "policy_commitment": _commit(b"GREMLIN-DUAL-USE-POLICY-ENVELOPE/v0.1", core),
        "execution_admitted": False,
        "production_runtime_write": False,
        "canon_allowed": False,
    }


def attach_policy(
    candidate: Mapping[str, Any],
    *,
    object_kind: str,
    declared_risk: RiskClass | str | int | None,
    parent_risks: Iterable[RiskClass | str | int] = (),
    parent_commitments: Iterable[str] = (),
    source_refs: Iterable[str] = (),
    transformations: Iterable[str] = (),
    evidence_refs: Iterable[str] = (),
    confidence: float = 0.0,
    context_complete: bool = True,
) -> dict[str, Any]:
    candidate_copy = dict(candidate)
    object_commitment = str(
        candidate_copy.get("commitment")
        or candidate_copy.get("relation_commitment")
        or candidate_copy.get("semantic_frame_commitment")
        or _commit(b"GREMLIN-DUAL-USE-CANDIDATE/v0.1", candidate_copy)
    )
    candidate_copy["dual_use_policy"] = make_policy_envelope(
        object_kind=object_kind,
        object_commitment=object_commitment,
        declared_risk=declared_risk,
        parent_risks=parent_risks,
        parent_commitments=parent_commitments,
        source_refs=source_refs,
        transformations=transformations,
        evidence_refs=evidence_refs,
        confidence=confidence,
        context_complete=context_complete,
    )
    return candidate_copy


def policy_api(
    operation: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Small deterministic API suitable for MCP exposure."""
    op = str(operation).strip().lower()
    if op == "inherit":
        risk = inherit_risk(
            payload.get("declared_risk"),
            payload.get("parent_risks") or [],
            context_complete=bool(payload.get("context_complete", True)),
        )
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "risk_class": risk.name,
            "allowed_actions": allowed_actions_for(risk),
        }
    if op == "firewall":
        return capability_firewall(
            risk=payload.get("risk") or RiskClass.DUAL_USE_HIGH.name,
            requested_action=payload.get("requested_action") or Action.ANALYZE.value,
            human_gate=bool(payload.get("human_gate", False)),
            tool_gate=bool(payload.get("tool_gate", False)),
            sandboxed=bool(payload.get("sandboxed", True)),
        )
    if op == "envelope":
        return make_policy_envelope(
            object_kind=str(payload.get("object_kind") or "CANDIDATE"),
            object_commitment=str(payload.get("object_commitment") or ""),
            declared_risk=payload.get("declared_risk"),
            parent_risks=payload.get("parent_risks") or [],
            parent_commitments=payload.get("parent_commitments") or [],
            source_refs=payload.get("source_refs") or [],
            transformations=payload.get("transformations") or [],
            evidence_refs=payload.get("evidence_refs") or [],
            confidence=float(payload.get("confidence", 0.0)),
            context_complete=bool(payload.get("context_complete", True)),
        )
    raise ValueError("operation must be one of: inherit, firewall, envelope")
