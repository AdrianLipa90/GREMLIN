from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .mathematical_constitution import (
    ConstitutionalError,
    build_action_contract,
    validate_action_contract,
    validate_admission_against_action,
)

SCHEMA = "GREMLIN_RUNTIME_CONSTITUTIONAL_ADMISSION_V0_1"
VERSION = "0.1.0"
ACTION_SCHEMA = "GREMLIN_RUNTIME_ACTION_BINDING_V0_1"
PACKET_SCHEMA = "GREMLIN_RUNTIME_CONSTITUTIONAL_PACKET_V0_1"


class RuntimeConstitutionalError(PermissionError):
    pass


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RuntimeConstitutionalError(
            "runtime constitutional request must be finite JSON data"
        ) from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise RuntimeConstitutionalError(f"{field} must be a string")
    out = value.strip()
    if not out:
        raise RuntimeConstitutionalError(f"{field} must be non-empty")
    return out


def _parameter_ids(values: Sequence[str] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        raise RuntimeConstitutionalError("parameter_ids must be a sequence")
    return tuple(sorted({_text(value, "parameter_id") for value in values}))


def build_runtime_action_binding(
    *,
    endpoint: str,
    consequence_class: str,
    request_payload: Mapping[str, Any],
    parameter_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(request_payload, Mapping):
        raise RuntimeConstitutionalError("request_payload must be a mapping")

    endpoint_name = _text(endpoint, "endpoint")
    consequence = _text(consequence_class, "consequence_class").upper()
    request = dict(request_payload)
    request_sha = _sha256(request)
    params = _parameter_ids(parameter_ids)

    action_id = f"runtime:{endpoint_name}:{request_sha}"
    action_contract = build_action_contract(
        action_id=action_id,
        consequence_class=consequence,
        parameter_ids=params,
    )
    core = {
        "schema": ACTION_SCHEMA,
        "version": VERSION,
        "endpoint": endpoint_name,
        "consequence_class": consequence,
        "request_sha256": request_sha,
        "parameter_ids": list(params),
        "action_contract": action_contract,
    }
    return {
        **core,
        "binding_sha256": _sha256(core),
    }


def validate_runtime_action_binding(
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(packet, Mapping):
        raise RuntimeConstitutionalError("runtime action binding must be a mapping")
    row = dict(packet)
    if row.get("schema") != ACTION_SCHEMA or row.get("version") != VERSION:
        raise RuntimeConstitutionalError("unsupported runtime action binding")

    core = dict(row)
    supplied = _text(core.pop("binding_sha256", None), "binding_sha256")
    endpoint = _text(core.get("endpoint"), "endpoint")
    consequence = _text(
        core.get("consequence_class"), "consequence_class"
    ).upper()
    request_sha = _text(core.get("request_sha256"), "request_sha256")
    if len(request_sha) != 64:
        raise RuntimeConstitutionalError("request_sha256 must be 64 hex")
    try:
        int(request_sha, 16)
    except ValueError as exc:
        raise RuntimeConstitutionalError("request_sha256 must be hexadecimal") from exc

    params_raw = core.get("parameter_ids")
    if not isinstance(params_raw, list):
        raise RuntimeConstitutionalError("parameter_ids must be a list")
    params = _parameter_ids(params_raw)
    if list(params) != params_raw:
        raise RuntimeConstitutionalError(
            "runtime action parameter_ids must be canonical and unique"
        )

    action_raw = core.get("action_contract")
    if not isinstance(action_raw, Mapping):
        raise RuntimeConstitutionalError("runtime action requires action_contract")
    try:
        action = validate_action_contract(action_raw)
    except ConstitutionalError as exc:
        raise RuntimeConstitutionalError(
            "invalid constitutional action contract"
        ) from exc

    expected_action_id = f"runtime:{endpoint}:{request_sha}"
    if action["action_id"] != expected_action_id:
        raise RuntimeConstitutionalError("runtime action_id/request binding mismatch")
    if action["consequence_class"] != consequence:
        raise RuntimeConstitutionalError(
            "runtime consequence class/action contract mismatch"
        )
    if action["parameter_ids"] != list(params):
        raise RuntimeConstitutionalError(
            "runtime parameter/action contract mismatch"
        )
    if supplied != _sha256(core):
        raise RuntimeConstitutionalError(
            "runtime action binding commitment mismatch"
        )
    return {
        **core,
        "binding_sha256": supplied,
    }


def build_runtime_constitutional_packet(
    *,
    action_binding: Mapping[str, Any],
    admission_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    binding = validate_runtime_action_binding(action_binding)
    try:
        admission = validate_admission_against_action(
            admission_receipt,
            binding["action_contract"],
        )
    except ConstitutionalError as exc:
        raise RuntimeConstitutionalError(
            "admission receipt does not match runtime action"
        ) from exc

    core = {
        "schema": PACKET_SCHEMA,
        "version": VERSION,
        "action_binding": binding,
        "admission_receipt": admission,
    }
    return {
        **core,
        "packet_sha256": _sha256(core),
    }


def validate_runtime_constitutional_packet(
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(packet, Mapping):
        raise RuntimeConstitutionalError(
            "constitutional_packet must be a mapping"
        )
    row = dict(packet)
    if row.get("schema") != PACKET_SCHEMA or row.get("version") != VERSION:
        raise RuntimeConstitutionalError(
            "unsupported runtime constitutional packet"
        )

    core = dict(row)
    supplied = _text(core.pop("packet_sha256", None), "packet_sha256")
    binding_raw = core.get("action_binding")
    admission_raw = core.get("admission_receipt")
    if not isinstance(binding_raw, Mapping) or not isinstance(
        admission_raw, Mapping
    ):
        raise RuntimeConstitutionalError(
            "runtime packet requires action_binding and admission_receipt"
        )
    binding = validate_runtime_action_binding(binding_raw)
    try:
        admission = validate_admission_against_action(
            admission_raw,
            binding["action_contract"],
        )
    except ConstitutionalError as exc:
        raise RuntimeConstitutionalError(
            "runtime admission/action mismatch"
        ) from exc

    normalized = {
        "schema": PACKET_SCHEMA,
        "version": VERSION,
        "action_binding": binding,
        "admission_receipt": admission,
    }
    if supplied != _sha256(normalized):
        raise RuntimeConstitutionalError(
            "runtime constitutional packet commitment mismatch"
        )
    return {
        **normalized,
        "packet_sha256": supplied,
    }


def require_constitutional_admission(
    *,
    endpoint: str,
    consequence_class: str,
    request_payload: Mapping[str, Any],
    constitutional_packet: Mapping[str, Any],
    parameter_ids: Sequence[str] | None = None,
    expected_capability_status: int | None = None,
    expected_authority_status: int | None = None,
    expected_evidence_status: int | None = None,
) -> dict[str, Any]:
    expected = build_runtime_action_binding(
        endpoint=endpoint,
        consequence_class=consequence_class,
        request_payload=request_payload,
        parameter_ids=parameter_ids,
    )
    packet = validate_runtime_constitutional_packet(constitutional_packet)
    binding = packet["action_binding"]

    if binding != expected:
        raise RuntimeConstitutionalError(
            "constitutional packet is not bound to this exact runtime request"
        )

    admission = packet["admission_receipt"]
    for field, expected in (
        ("capability_scalar", expected_capability_status),
        ("authority_scalar", expected_authority_status),
        ("evidence_scalar", expected_evidence_status),
    ):
        if expected is None:
            continue
        if isinstance(expected, bool) or expected not in {-1, 0, 1}:
            raise RuntimeConstitutionalError(
                f"expected {field} must be one of -1, 0, +1"
            )
        if admission[field] != expected:
            raise RuntimeConstitutionalError(
                f"runtime admission {field} does not match validated upstream state"
            )

    if admission["decision"] != "ALLOW":
        raise RuntimeConstitutionalError(
            f"runtime action is not constitutionally admitted: "
            f"{admission['decision']}"
        )

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ADMITTED",
        "endpoint": expected["endpoint"],
        "request_sha256": expected["request_sha256"],
        "action_sha256": expected["action_contract"]["action_sha256"],
        "admission_receipt_id": admission["receipt_id"],
        "packet_sha256": packet["packet_sha256"],
        "canon_allowed": False,
    }


__all__ = [
    "ACTION_SCHEMA",
    "PACKET_SCHEMA",
    "RuntimeConstitutionalError",
    "SCHEMA",
    "VERSION",
    "build_runtime_action_binding",
    "build_runtime_constitutional_packet",
    "require_constitutional_admission",
    "validate_runtime_action_binding",
    "validate_runtime_constitutional_packet",
]
