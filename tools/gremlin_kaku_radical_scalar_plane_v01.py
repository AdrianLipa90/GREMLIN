from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

KAKU_PACKET_SCHEMA = "GREMLIN_KAKU_SCALAR_PACKET_V0_1"
RADICAL_ADMISSION_SCHEMA = "GREMLIN_RADICAL_SCALAR_ADMISSION_V0_1"
KAKU_DOMAIN = b"GREMLIN-KAKU-SCALAR-PACKET/v0.1\x00"
RADICAL_DOMAIN = b"GREMLIN-RADICAL-SCALAR-ADMISSION/v0.1\x00"

PNCS_MINIMAL_KAKU = {
    "SOURCE",
    "ORDER",
    "TRANSFORM",
    "COMPOSITION",
    "DIFFERENCE",
    "IDENTITY",
    "CONDITION",
    "NEGATION",
}

HARD_GATE_PASS = {
    "consent": "GRANTED",
    "reversibility": "SATISFIED",
    "no_go": "CLEAR",
}


class GremlinScalarPlaneError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _nonempty(value: Any, name: str) -> str:
    text = str(value)
    if not text:
        raise GremlinScalarPlaneError(f"{name} must be non-empty")
    return text


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise GremlinScalarPlaneError(f"{name} must be finite")
    return x


def _scalar_observation(value: Mapping[str, Any], name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise GremlinScalarPlaneError(f"{name} observation must be a mapping")
    return {
        "value_f64_hex": _finite(value.get("value"), name).hex(),
        "scale_id": _nonempty(value.get("scale_id"), f"{name}.scale_id"),
        "source_ref": _nonempty(value.get("source_ref"), f"{name}.source_ref"),
        "epistemic_status": _nonempty(value.get("epistemic_status"), f"{name}.epistemic_status"),
    }


def build_kaku_scalar_packet(
    *,
    kaku_id: str,
    operator_kind: str,
    direction: str,
    polarity: Any,
    role: str,
    source_binding: str,
    target_binding: str,
    valuation: Mapping[str, Any],
    affect: Mapping[str, Any],
    intention_alignment: Mapping[str, Any],
    epistemic_support: Mapping[str, Any],
    evidence_refs: Sequence[str] = (),
) -> dict[str, Any]:
    operator = _nonempty(operator_kind, "operator_kind").upper()
    if operator not in PNCS_MINIMAL_KAKU:
        raise GremlinScalarPlaneError(f"operator_kind outside bounded PNCS KAKU set: {operator}")

    core = {
        "schema": KAKU_PACKET_SCHEMA,
        "kaku_id": _nonempty(kaku_id, "kaku_id"),
        "operator_kind": operator,
        "direction": _nonempty(direction, "direction"),
        "polarity_f64_hex": _finite(polarity, "polarity").hex(),
        "role": _nonempty(role, "role"),
        "source_binding": _nonempty(source_binding, "source_binding"),
        "target_binding": _nonempty(target_binding, "target_binding"),
        "scalars": {
            "valuation": _scalar_observation(valuation, "valuation"),
            "affect": _scalar_observation(affect, "affect"),
            "intention_alignment": _scalar_observation(intention_alignment, "intention_alignment"),
            "epistemic_support": _scalar_observation(epistemic_support, "epistemic_support"),
        },
        "evidence_refs": sorted(_nonempty(v, "evidence_ref") for v in evidence_refs),
        "vector_bound": False,
        "t36_realization_present": False,
        "semantic_mass_present": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "KAKU_SCALARS_COMPLETE",
    }
    commitment = hashlib.blake2b(KAKU_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    return {**core, "kaku_scalar_commitment": commitment}


def validate_kaku_scalar_packet(packet: Mapping[str, Any]) -> bool:
    if packet.get("schema") != KAKU_PACKET_SCHEMA:
        raise GremlinScalarPlaneError("unsupported KAKU scalar packet schema")
    operator = str(packet.get("operator_kind", ""))
    if operator not in PNCS_MINIMAL_KAKU:
        raise GremlinScalarPlaneError("invalid PNCS KAKU operator kind")
    for key in ("kaku_id", "direction", "role", "source_binding", "target_binding"):
        _nonempty(packet.get(key), key)
    _finite(float.fromhex(str(packet.get("polarity_f64_hex"))), "polarity")

    scalars = packet.get("scalars")
    if not isinstance(scalars, Mapping) or set(scalars) != {
        "valuation",
        "affect",
        "intention_alignment",
        "epistemic_support",
    }:
        raise GremlinScalarPlaneError("exact required KAKU scalar set missing")
    for name, observation in scalars.items():
        if not isinstance(observation, Mapping):
            raise GremlinScalarPlaneError(f"{name} observation must be a mapping")
        _finite(float.fromhex(str(observation.get("value_f64_hex"))), name)
        for key in ("scale_id", "source_ref", "epistemic_status"):
            _nonempty(observation.get(key), f"{name}.{key}")

    if packet.get("vector_bound") is not False or packet.get("t36_realization_present") is not False:
        raise GremlinScalarPlaneError("pre-vector KAKU packet cannot contain realized vector authority")
    if packet.get("semantic_mass_present") is not False:
        raise GremlinScalarPlaneError("semantic mass is post-realization")
    if packet.get("execution_admitted") is not False or packet.get("canon_allowed") is not False:
        raise GremlinScalarPlaneError("KAKU scalar authority boundary violated")
    if packet.get("status") != "KAKU_SCALARS_COMPLETE":
        raise GremlinScalarPlaneError("wrong KAKU scalar status")

    supplied = str(packet.get("kaku_scalar_commitment", ""))
    core = dict(packet)
    core.pop("kaku_scalar_commitment", None)
    expected = hashlib.blake2b(KAKU_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    if supplied != expected:
        raise GremlinScalarPlaneError("KAKU scalar commitment mismatch")
    return True


def _gate_record(value: Mapping[str, Any], name: str, allowed: set[str]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise GremlinScalarPlaneError(f"{name} gate must be a mapping")
    status = _nonempty(value.get("status"), f"{name}.status").upper()
    if status not in allowed:
        raise GremlinScalarPlaneError(f"unsupported {name} gate status: {status}")
    return {
        "status": status,
        "source_ref": _nonempty(value.get("source_ref"), f"{name}.source_ref"),
        "reason": str(value.get("reason", "")),
    }


def build_radical_scalar_admission(
    *,
    radical_id: str,
    candidate_id: str,
    ordered_kaku_packets: Sequence[Mapping[str, Any]],
    relation_ids: Sequence[str],
    ethical_integrity: Mapping[str, Any],
    consent_gate: Mapping[str, Any],
    reversibility_gate: Mapping[str, Any],
    no_go_gate: Mapping[str, Any],
    contradiction_load: Mapping[str, Any],
    recursive_integrity: Mapping[str, Any],
    evidence_refs: Sequence[str] = (),
) -> dict[str, Any]:
    if not ordered_kaku_packets:
        raise GremlinScalarPlaneError("Radical requires at least one KAKU scalar packet")
    packets = []
    seen = set()
    for packet in ordered_kaku_packets:
        validate_kaku_scalar_packet(packet)
        kid = str(packet["kaku_id"])
        if kid in seen:
            raise GremlinScalarPlaneError(f"duplicate KAKU in Radical: {kid}")
        seen.add(kid)
        packets.append({
            "kaku_id": kid,
            "kaku_scalar_commitment": str(packet["kaku_scalar_commitment"]),
            "operator_kind": str(packet["operator_kind"]),
        })

    gates = {
        "consent": _gate_record(consent_gate, "consent", {"GRANTED", "DENIED", "UNRESOLVED"}),
        "reversibility": _gate_record(reversibility_gate, "reversibility", {"SATISFIED", "FAILED", "UNRESOLVED"}),
        "no_go": _gate_record(no_go_gate, "no_go", {"CLEAR", "HIT", "UNRESOLVED"}),
    }
    hard_pass = all(gates[name]["status"] == required for name, required in HARD_GATE_PASS.items())

    core = {
        "schema": RADICAL_ADMISSION_SCHEMA,
        "radical_id": _nonempty(radical_id, "radical_id"),
        "candidate_id": _nonempty(candidate_id, "candidate_id"),
        "ordered_kaku": packets,
        "relation_ids": [_nonempty(v, "relation_id") for v in relation_ids],
        "radical_scalars": {
            "ethical_integrity": _scalar_observation(ethical_integrity, "ethical_integrity"),
            "contradiction_load": _scalar_observation(contradiction_load, "contradiction_load"),
            "recursive_integrity": _scalar_observation(recursive_integrity, "recursive_integrity"),
        },
        "hard_gates": gates,
        "evidence_refs": sorted(_nonempty(v, "evidence_ref") for v in evidence_refs),
        "vector_synthesis_allowed": hard_pass,
        "t36_realization_present": False,
        "semantic_mass_present": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "PRE_VECTOR_ADMITTED" if hard_pass else "PRE_VECTOR_BLOCKED",
    }
    commitment = hashlib.blake2b(RADICAL_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    return {**core, "radical_scalar_commitment": commitment}


def validate_radical_scalar_admission(record: Mapping[str, Any]) -> bool:
    if record.get("schema") != RADICAL_ADMISSION_SCHEMA:
        raise GremlinScalarPlaneError("unsupported Radical scalar admission schema")
    _nonempty(record.get("radical_id"), "radical_id")
    _nonempty(record.get("candidate_id"), "candidate_id")
    ordered = record.get("ordered_kaku")
    if not isinstance(ordered, list) or not ordered:
        raise GremlinScalarPlaneError("ordered KAKU lineage required")
    if len({str(v.get("kaku_id")) for v in ordered}) != len(ordered):
        raise GremlinScalarPlaneError("duplicate KAKU lineage entry")
    for item in ordered:
        _nonempty(item.get("kaku_id"), "ordered_kaku.kaku_id")
        commitment = str(item.get("kaku_scalar_commitment", ""))
        if len(commitment) != 64:
            raise GremlinScalarPlaneError("invalid KAKU scalar commitment")
        bytes.fromhex(commitment)
        if str(item.get("operator_kind", "")) not in PNCS_MINIMAL_KAKU:
            raise GremlinScalarPlaneError("invalid KAKU lineage operator")

    scalars = record.get("radical_scalars")
    if not isinstance(scalars, Mapping) or set(scalars) != {
        "ethical_integrity",
        "contradiction_load",
        "recursive_integrity",
    }:
        raise GremlinScalarPlaneError("exact required Radical scalar set missing")
    for name, observation in scalars.items():
        _finite(float.fromhex(str(observation.get("value_f64_hex"))), name)
        for key in ("scale_id", "source_ref", "epistemic_status"):
            _nonempty(observation.get(key), f"{name}.{key}")

    gates = record.get("hard_gates")
    if not isinstance(gates, Mapping) or set(gates) != set(HARD_GATE_PASS):
        raise GremlinScalarPlaneError("exact hard-gate set required")
    hard_pass = True
    gate_allowed = {
        "consent": {"GRANTED", "DENIED", "UNRESOLVED"},
        "reversibility": {"SATISFIED", "FAILED", "UNRESOLVED"},
        "no_go": {"CLEAR", "HIT", "UNRESOLVED"},
    }
    for name, required in HARD_GATE_PASS.items():
        gate = gates[name]
        if str(gate.get("status", "")) not in gate_allowed[name]:
            raise GremlinScalarPlaneError(f"invalid {name} gate")
        _nonempty(gate.get("source_ref"), f"{name}.source_ref")
        hard_pass = hard_pass and gate["status"] == required

    expected_status = "PRE_VECTOR_ADMITTED" if hard_pass else "PRE_VECTOR_BLOCKED"
    if record.get("status") != expected_status:
        raise GremlinScalarPlaneError("Radical admission status inconsistent with hard gates")
    if record.get("vector_synthesis_allowed") is not hard_pass:
        raise GremlinScalarPlaneError("vector synthesis flag inconsistent with hard gates")
    if record.get("t36_realization_present") is not False or record.get("semantic_mass_present") is not False:
        raise GremlinScalarPlaneError("pre-vector Radical cannot contain post-realization authority")
    if record.get("execution_admitted") is not False or record.get("canon_allowed") is not False:
        raise GremlinScalarPlaneError("Radical scalar authority boundary violated")

    supplied = str(record.get("radical_scalar_commitment", ""))
    core = dict(record)
    core.pop("radical_scalar_commitment", None)
    expected = hashlib.blake2b(RADICAL_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    if supplied != expected:
        raise GremlinScalarPlaneError("Radical scalar commitment mismatch")
    return True
