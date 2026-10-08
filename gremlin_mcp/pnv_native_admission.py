from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.resources
import json
import os
from pathlib import Path
import shlex
from typing import Any, Mapping

from gremlin_mcp.tool_metadata import (
    CLASSIFIED_TOOLS,
    LOCAL_STATE_MUTATIONS,
    READ_ONLY_CLOSED,
    READ_ONLY_OPEN_WORLD,
)

SCHEMA = "GREMLIN_MCP_PNV_NATIVE_ADMISSION_V0_7"
RECEIPT_SCHEMA = "GREMLIN_MCP_PNV_NATIVE_ADMISSION_RECEIPT_V0_7"
SOURCE_SCHEMA = "GREMLIN_MCP_SOURCE_ADMISSION_V0_2"
SOURCE_RECEIPT_SCHEMA = "GREMLIN_MCP_SOURCE_ADMISSION_RECEIPT_V0_2"
DEFAULT_ROOT = Path("/dev/shm/ciel_noema")
LIVE_PNV_RESOURCE = "GREMLIN_MCP_NATIVE_ADMISSION_V0_6.pnv"
SOURCE_PNV_RESOURCE = "GREMLIN_MCP_SOURCE_ADMISSION_V0_1.pnv"
PNV_RESOURCE = LIVE_PNV_RESOURCE
SUPPORTED_OPCODES = frozenset({"SOURCE", "IDENTITY", "ORDER", "COMPOSITION", "RETURN"})


class PNVNativeAdmissionError(PermissionError):
    pass


@dataclass(frozen=True)
class _Op:
    name: str
    opcode: str
    args: tuple[str, ...]


@dataclass(frozen=True)
class _Program:
    ops: tuple[_Op, ...]
    assertions: tuple[str, ...]
    emits: tuple[str, ...]
    source: str

    @property
    def source_sha256(self) -> str:
        return hashlib.sha256(self.source.encode("utf-8")).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _load_json(path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PNVNativeAdmissionError(f"PNV_NATIVE_{label.upper()}_UNAVAILABLE") from exc
    if not isinstance(value, dict):
        raise PNVNativeAdmissionError(f"PNV_NATIVE_{label.upper()}_INVALID")
    return value


def _program_text(resource: str = LIVE_PNV_RESOURCE) -> str:
    try:
        return importlib.resources.files("gremlin_mcp").joinpath(resource).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise PNVNativeAdmissionError(f"PNV_NATIVE_POLICY_BYTES_UNAVAILABLE:{resource}") from exc


def _parse(source: str) -> _Program:
    version = None
    epistemic = None
    mode = None
    ops: list[_Op] = []
    assertions: list[str] = []
    emits: list[str] = []
    names: set[str] = set()
    for line_no, raw in enumerate(source.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            parts = shlex.split(line, comments=False, posix=True)
        except ValueError as exc:
            raise PNVNativeAdmissionError(f"PNV_NATIVE_PARSE_LINE_{line_no}") from exc
        head = parts[0]
        if head == "PNV":
            if len(parts) != 2 or version is not None:
                raise PNVNativeAdmissionError("PNV_NATIVE_HEADER_INVALID")
            version = parts[1]
            continue
        if head == "EPISTEMIC":
            if len(parts) != 2 or epistemic is not None:
                raise PNVNativeAdmissionError("PNV_NATIVE_EPISTEMIC_INVALID")
            epistemic = parts[1]
            continue
        if head == "MODE":
            if len(parts) != 2 or mode is not None:
                raise PNVNativeAdmissionError("PNV_NATIVE_MODE_INVALID")
            mode = parts[1]
            continue
        if head == "OP":
            if len(parts) < 4:
                raise PNVNativeAdmissionError(f"PNV_NATIVE_OP_INVALID_LINE_{line_no}")
            name, opcode = parts[1], parts[2]
            if name in names or opcode not in SUPPORTED_OPCODES:
                raise PNVNativeAdmissionError(f"PNV_NATIVE_OP_REJECTED_LINE_{line_no}")
            names.add(name)
            ops.append(_Op(name, opcode, tuple(parts[3:])))
            continue
        if head == "ASSERT":
            if len(parts) != 2:
                raise PNVNativeAdmissionError(f"PNV_NATIVE_ASSERT_INVALID_LINE_{line_no}")
            assertions.append(parts[1])
            continue
        if head == "EMIT":
            if len(parts) != 2:
                raise PNVNativeAdmissionError(f"PNV_NATIVE_EMIT_INVALID_LINE_{line_no}")
            emits.append(parts[1])
            continue
        raise PNVNativeAdmissionError(f"PNV_NATIVE_UNKNOWN_STATEMENT_{line_no}")
    if version != "1" or epistemic != "CHYBA" or mode != "INTERNAL_EXECUTION" or not ops:
        raise PNVNativeAdmissionError("PNV_NATIVE_HEADER_CONTRACT_MISMATCH")
    if any(name not in names for name in assertions + emits):
        raise PNVNativeAdmissionError("PNV_NATIVE_UNKNOWN_ASSERT_OR_EMIT")
    return _Program(tuple(ops), tuple(assertions), tuple(emits), source)


def _resolve(token: str, values: Mapping[str, Any], sources: Mapping[str, Any]) -> Any:
    if token in values:
        return values[token]
    if token in sources:
        return sources[token]
    if token == "TRUE":
        return True
    if token == "FALSE":
        return False
    if token == "NONE":
        return None
    try:
        return int(token)
    except ValueError:
        return token


def _execute(program: _Program, sources: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    values: dict[str, Any] = {}
    trace: list[dict[str, Any]] = []
    for op in program.ops:
        if op.opcode == "SOURCE":
            if len(op.args) != 1 or op.args[0] not in sources:
                raise PNVNativeAdmissionError(f"PNV_NATIVE_SOURCE_UNRESOLVED:{op.name}")
            value = sources[op.args[0]]
        elif op.opcode == "IDENTITY":
            if len(op.args) != 2:
                raise PNVNativeAdmissionError(f"PNV_NATIVE_IDENTITY_ARITY:{op.name}")
            value = _resolve(op.args[0], values, sources) == _resolve(op.args[1], values, sources)
        elif op.opcode in {"ORDER", "COMPOSITION"}:
            value = [_resolve(arg, values, sources) for arg in op.args]
        elif op.opcode == "RETURN":
            if len(op.args) != 1:
                raise PNVNativeAdmissionError(f"PNV_NATIVE_RETURN_ARITY:{op.name}")
            value = _resolve(op.args[0], values, sources)
        else:
            raise PNVNativeAdmissionError(f"PNV_NATIVE_OPCODE_UNSUPPORTED:{op.opcode}")
        values[op.name] = value
        trace.append({"op": op.name, "opcode": op.opcode, "result_sha256": _sha(value)})
    for name in program.assertions:
        if values.get(name) is not True:
            raise PNVNativeAdmissionError(f"PNV_NATIVE_ASSERT_FAILED:{name}")
    return values, {"trace": trace, "emitted": {name: values[name] for name in program.emits}}


def native_mode_enabled() -> bool:
    return os.environ.get("GREMLIN_PNV_NATIVE", "").strip().lower() in {"1", "true", "yes", "on"}


def _root() -> Path:
    raw = os.environ.get("GREMLIN_NOEMA_RUNTIME_ROOT", "").strip()
    return Path(raw) if raw else DEFAULT_ROOT


def _tool_tier(tool: str) -> str:
    if tool in READ_ONLY_CLOSED or tool in READ_ONLY_OPEN_WORLD:
        return "READ_ONLY"
    if tool in LOCAL_STATE_MUTATIONS:
        return "LOW_RISK_AUTO"
    return "UNCLASSIFIED"


def _live_sources(root: Path) -> dict[str, Any]:
    guard = _load_json(root / "session/tether_guard_latest.json", "tether_guard")
    pulse = _load_json(root / "gremlin/triple_pulse_attestation.json", "triple_pulse")
    sync = _load_json(root / "system_sync/CURRENT.json", "system_sync")
    identity = pulse.get("identity_receipt")
    domain = pulse.get("domain_receipt")
    authority = pulse.get("authority_receipt")
    if not all(isinstance(x, dict) for x in (identity, domain, authority)):
        raise PNVNativeAdmissionError("PNV_NATIVE_TRIPLE_PULSE_RECEIPTS_INVALID")
    return {
        "current.identity_status": identity.get("status"),
        "current.domain_status": domain.get("status"),
        "current.authority_status": authority.get("status"),
        "current.tether_status": guard.get("tether_status"),
        "current.guard_status": guard.get("status"),
        "current.guard_failures_count": len(guard.get("failures", []))
        if isinstance(guard.get("failures", []), list)
        else -1,
        "current.generation": pulse.get("generation"),
        "current.identity_generation": identity.get("generation"),
        "current.domain_generation": domain.get("generation"),
        "current.authority_generation": authority.get("generation"),
        "current.system_sync_status": sync.get("status"),
        "current.system_sync_generation": sync.get("generation"),
        "current.system_sync_sha256": sync.get("sync_sha256"),
    }


def admission_facts(tool: str) -> dict[str, Any]:
    tier = _tool_tier(tool)
    return {
        "tool": tool,
        "tier": tier,
        "known_tool": tool in CLASSIFIED_TOOLS,
        "policy_admitted": True,
        "key_mutation": False,
        "canon_mutation": False,
        "production_effect": False,
        "scope_exact": True,
    }


def _request_sources(facts: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "request.key_mutation": facts["key_mutation"],
        "request.production_effect": facts["production_effect"],
    }


def _source_work_receipt(tool: str, facts: Mapping[str, Any]) -> dict[str, Any]:
    program = _parse(_program_text(SOURCE_PNV_RESOURCE))
    _, execution = _execute(program, _request_sources(facts))
    payload = {
        "schema": SOURCE_RECEIPT_SCHEMA,
        "policy_schema": SOURCE_SCHEMA,
        "status": "PASS",
        "tool": tool,
        "authority_lane": "SOURCE_WORK",
        "source_work_authority": "ACTIVE",
        "live_production_authority": "NOT_REQUIRED_FOR_SOURCE_WORK",
        "mutation_tier": facts["tier"],
        "pnv_sha256": program.source_sha256,
        "generation": None,
        "tether_required": False,
        "tether_status": "NOT_REQUIRED",
        "system_sync_sha256": None,
        "triple_pulse_same_generation": None,
        "trace_sha256": _sha(execution["trace"]),
        "canon_promotion_gate": "NOT_APPLIED_HERE",
        "local_state_write": facts["tier"] == "LOW_RISK_AUTO",
        "production_effect_admitted_by_request": False,
        "key_mutation_auto": False,
        "global_action_denial": False,
    }
    return {**payload, "receipt_sha256": _sha(payload)}


def _live_production_receipt(tool: str, facts: Mapping[str, Any]) -> dict[str, Any]:
    sources = _live_sources(_root())
    sources.update(_request_sources(facts))
    program = _parse(_program_text(LIVE_PNV_RESOURCE))
    _, execution = _execute(program, sources)
    payload = {
        "schema": RECEIPT_SCHEMA,
        "policy_schema": SCHEMA,
        "status": "PASS",
        "tool": tool,
        "authority_lane": "LIVE_PRODUCTION",
        "source_work_authority": "UNCHANGED",
        "live_production_authority": "ADMITTED_BY_LIVE_GUARD",
        "mutation_tier": facts["tier"],
        "pnv_sha256": program.source_sha256,
        "generation": sources["current.generation"],
        "tether_required": True,
        "tether_status": sources["current.tether_status"],
        "system_sync_sha256": sources.get("current.system_sync_sha256"),
        "triple_pulse_same_generation": (
            sources["current.generation"]
            == sources["current.identity_generation"]
            == sources["current.domain_generation"]
            == sources["current.authority_generation"]
        ),
        "trace_sha256": _sha(execution["trace"]),
        "canon_promotion_gate": "NOT_APPLIED_HERE",
        "local_state_write": facts["tier"] == "LOW_RISK_AUTO",
        "production_effect_admitted_by_request": False,
        "key_mutation_auto": False,
        "global_action_denial": False,
    }
    return {**payload, "receipt_sha256": _sha(payload)}


def admit_tool_call(tool: str, args: tuple[Any, ...], kwargs: Mapping[str, Any]) -> dict[str, Any]:
    del args, kwargs
    facts = admission_facts(tool)
    if facts["tier"] in {"READ_ONLY", "LOW_RISK_AUTO"}:
        return _source_work_receipt(tool, facts)
    return _live_production_receipt(tool, facts)


def native_admission_manifest() -> dict[str, Any]:
    live_source = _program_text(LIVE_PNV_RESOURCE)
    source_work = _program_text(SOURCE_PNV_RESOURCE)
    return {
        "schema": SCHEMA,
        "mode": "PNV_NATIVE_SPLIT_AUTHORITY_PYTHON_TRANSPORT_ONLY",
        "enabled": native_mode_enabled(),
        "authority_model": "SOURCE_WORK_VS_LIVE_PRODUCTION",
        "pnv_sha256": hashlib.sha256(live_source.encode("utf-8")).hexdigest(),
        "live_pnv_sha256": hashlib.sha256(live_source.encode("utf-8")).hexdigest(),
        "source_work_pnv_sha256": hashlib.sha256(source_work.encode("utf-8")).hexdigest(),
        "source_work": {
            "read_only": "AUTO",
            "low_risk_local_state_mutations": "AUTO",
            "live_tether_required": False,
            "tool_whitelist": False,
            "canon_promotion_gate": "NOT_APPLIED_HERE",
            "production_effect": False,
            "global_action_denial": False,
        },
        "live_production": {
            "unclassified_tools": "LIVE_TETHER_PATH",
            "live_tether_required": True,
            "same_generation_required": True,
            "main_mutation_requires_explicit_admission": True,
            "canon_promotion_requires_explicit_admission": False,
            "production_effect_requires_explicit_admission": True,
        },
        "read_only": "AUTO",
        "low_risk_local_state_mutations": "AUTO",
        "key_mutations": "EXACT_EFFECT_PATH",
        "main_mutation_requires_explicit_admission": True,
        "canon_promotion_requires_explicit_admission": False,
        "delete_move_rename_auto": False,
        "force_push_auto": False,
        "secrets_auto": False,
        "production_effect_requires_explicit_admission": True,
        "fail_closed": True,
    }
