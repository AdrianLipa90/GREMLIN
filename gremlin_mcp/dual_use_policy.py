from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum
import hashlib
import json
import math
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

RESTRICTED_ACTIONS = {
    Action.ANALYZE,
    Action.MITIGATE,
    Action.DETECT,
    Action.PATCH,
    Action.MONITOR,
}


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
        raise ValueError("dual-use policy data must be finite JSON") from exc


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _strict_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be boolean")
    return value


def _strict_text(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text and not allow_empty:
        raise ValueError(f"{field} must be non-empty")
    return text


def _strict_confidence(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("confidence must be a finite number in [0, 1]")
    out = float(value)
    if not math.isfinite(out) or not 0.0 <= out <= 1.0:
        raise ValueError("confidence must be a finite number in [0, 1]")
    return out


def _strict_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be a list")
    return list(value)


def _strict_string_list(value: Any, field: str) -> list[str]:
    rows = _strict_list(value, field)
    out: list[str] = []
    for item in rows:
        text = _strict_text(item, field)
        out.append(text)
    return out


def _reject_unknown_keys(payload: Mapping[str, Any], allowed: frozenset[str], field: str) -> None:
    unknown = sorted(repr(key) for key in payload if not isinstance(key, str) or key not in allowed)
    if unknown:
        raise ValueError(f"{field} contains unsupported keys: {unknown}")


def _parse_risk(value: RiskClass | str | int) -> RiskClass:
    if isinstance(value, RiskClass):
        return value
    if isinstance(value, bool):
        raise ValueError("risk class must not be boolean")
    if isinstance(value, int):
        try:
            return RiskClass(value)
        except ValueError as exc:
            raise ValueError(f"unknown risk class: {value!r}") from exc
    if not isinstance(value, str):
        raise ValueError("risk class must be a RiskClass, integer, or string")
    text = value.strip().upper()
    if not text:
        raise ValueError("risk class string must be non-empty")
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
    complete = _strict_bool(context_complete, "context_complete")
    if isinstance(parent_risks, (str, bytes, Mapping)) or not isinstance(parent_risks, Iterable):
        raise ValueError("parent_risks must be an iterable of risk classes")
    parsed_parents = [_parse_risk(value) for value in parent_risks]
    if declared_risk is None:
        declared = RiskClass.DUAL_USE_HIGH
    else:
        declared = _parse_risk(declared_risk)
    if not complete:
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
    if isinstance(requested_action, Action):
        action = requested_action
    elif isinstance(requested_action, str):
        action = Action(_strict_text(requested_action, "requested_action").upper())
    else:
        raise ValueError("requested_action must be an Action or string")
    human = _strict_bool(human_gate, "human_gate")
    tool = _strict_bool(tool_gate, "tool_gate")
    sandbox = _strict_bool(sandboxed, "sandboxed")

    reason = "ACTION_ALLOWED_BY_POLICY"
    admitted = action.value in allowed_actions_for(rc)

    if action is Action.EXECUTE:
        admitted = rc <= RiskClass.DUAL_USE_LOW and human and tool and sandbox
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
        "human_gate": human,
        "tool_gate": tool,
        "sandboxed": sandbox,
        "admitted": admitted,
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
    confidence_value = _strict_confidence(confidence)
    complete = _strict_bool(context_complete, "context_complete")
    object_kind_value = _strict_text(object_kind, "object_kind").upper()
    object_commitment_value = _strict_text(object_commitment, "object_commitment")
    parent_commitment_rows = _strict_string_list(list(parent_commitments), "parent_commitments")
    source_rows = _strict_string_list(list(source_refs), "source_refs")
    transformation_rows = _strict_string_list(list(transformations), "transformations")
    evidence_rows = _strict_string_list(list(evidence_refs), "evidence_refs")
    risk = inherit_risk(
        declared_risk,
        parent_risks,
        context_complete=complete,
    )
    core = {
        "object_kind": object_kind_value,
        "object_commitment": object_commitment_value,
        "source_refs": sorted(set(source_rows)),
        "transformations": transformation_rows,
        "evidence_refs": sorted(set(evidence_rows)),
        "confidence": confidence_value,
        "risk_class": risk.name,
        "parent_commitments": sorted(set(parent_commitment_rows)),
        "allowed_actions": allowed_actions_for(risk),
        "context_complete": complete,
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
    if not isinstance(candidate, Mapping):
        raise ValueError("candidate must be an object")
    candidate_copy = dict(candidate)
    existing = (
        candidate_copy.get("commitment")
        or candidate_copy.get("relation_commitment")
        or candidate_copy.get("semantic_frame_commitment")
    )
    if existing is None:
        object_commitment = _commit(b"GREMLIN-DUAL-USE-CANDIDATE/v0.1", candidate_copy)
    else:
        object_commitment = _strict_text(existing, "candidate commitment")
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
    if not isinstance(operation, str):
        raise ValueError("operation must be a string")
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be an object")
    op = operation.strip().lower()
    if op == "inherit":
        allowed = frozenset({"declared_risk", "parent_risks", "context_complete"})
        _reject_unknown_keys(payload, allowed, "inherit payload")
        parent_risks = _strict_list(payload.get("parent_risks", []), "parent_risks")
        complete = _strict_bool(payload.get("context_complete", True), "context_complete")
        risk = inherit_risk(
            payload.get("declared_risk"),
            parent_risks,
            context_complete=complete,
        )
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "risk_class": risk.name,
            "allowed_actions": allowed_actions_for(risk),
        }
    if op == "firewall":
        allowed = frozenset({"risk", "requested_action", "human_gate", "tool_gate", "sandboxed"})
        _reject_unknown_keys(payload, allowed, "firewall payload")
        risk_value = payload.get("risk", RiskClass.DUAL_USE_HIGH.name)
        action_value = payload.get("requested_action", Action.ANALYZE.value)
        return capability_firewall(
            risk=risk_value,
            requested_action=action_value,
            human_gate=_strict_bool(payload.get("human_gate", False), "human_gate"),
            tool_gate=_strict_bool(payload.get("tool_gate", False), "tool_gate"),
            sandboxed=_strict_bool(payload.get("sandboxed", True), "sandboxed"),
        )
    if op == "envelope":
        allowed = frozenset(
            {
                "object_kind", "object_commitment", "declared_risk", "parent_risks",
                "parent_commitments", "source_refs", "transformations", "evidence_refs",
                "confidence", "context_complete",
            }
        )
        _reject_unknown_keys(payload, allowed, "envelope payload")
        return make_policy_envelope(
            object_kind=_strict_text(payload.get("object_kind", "CANDIDATE"), "object_kind"),
            object_commitment=_strict_text(payload.get("object_commitment"), "object_commitment"),
            declared_risk=payload.get("declared_risk"),
            parent_risks=_strict_list(payload.get("parent_risks", []), "parent_risks"),
            parent_commitments=_strict_string_list(payload.get("parent_commitments", []), "parent_commitments"),
            source_refs=_strict_string_list(payload.get("source_refs", []), "source_refs"),
            transformations=_strict_string_list(payload.get("transformations", []), "transformations"),
            evidence_refs=_strict_string_list(payload.get("evidence_refs", []), "evidence_refs"),
            confidence=_strict_confidence(payload.get("confidence", 0.0)),
            context_complete=_strict_bool(payload.get("context_complete", True), "context_complete"),
        )
    raise ValueError("operation must be one of: inherit, firewall, envelope")
