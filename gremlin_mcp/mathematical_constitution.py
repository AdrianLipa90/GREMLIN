from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "GREMLIN_MATHEMATICAL_CONSTITUTION_V0_1"
VERSION = "0.1.0"
EPISTEMIC = "CHYBA"
AUTHORITY = "NONE"
CANON_ALLOWED = False

BLOCK = -1
UNRESOLVED = 0
PASS = 1
LATTICE = (BLOCK, UNRESOLVED, PASS)

ETHICS_GATES = (
    "LIFE_PROTECTION",
    "AGENCY_PROTECTION",
    "CONSENT",
    "REVERSIBILITY",
    "NO_GO",
    "EPISTEMIC_INTEGRITY",
    "AUTHORITY_INTEGRITY",
    "PROVENANCE_INTEGRITY",
)

CONSEQUENCE_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "ANALYTIC_NON_ACTUATING": (
        "EPISTEMIC_INTEGRITY",
        "PROVENANCE_INTEGRITY",
    ),
    "READ_ONLY": (
        "AGENCY_PROTECTION",
        "EPISTEMIC_INTEGRITY",
        "AUTHORITY_INTEGRITY",
        "PROVENANCE_INTEGRITY",
    ),
    "APPEND_ONLY": ETHICS_GATES,
    "MUTATION": ETHICS_GATES,
    "GOVERNANCE": ETHICS_GATES,
}
HIGH_CONSEQUENCE_CLASSES = frozenset({"APPEND_ONLY", "MUTATION", "GOVERNANCE"})

PARAMETER_SOURCE_CLASSES = frozenset({"DERIVED", "MEASURED", "POLICY", "UNKNOWN"})
PARAMETER_BINDING_STATES = frozenset({"BOUND", "UNBOUND", "OPEN"})

GATE_SCHEMA = "GREMLIN_CONSTITUTIONAL_GATE_RECEIPT_V0_1"
PARAMETER_SCHEMA = "GREMLIN_CONSTITUTIONAL_PARAMETER_V0_1"
ACTION_SCHEMA = "GREMLIN_CONSTITUTIONAL_ACTION_CONTRACT_V0_1"
DECISION_SCHEMA = "GREMLIN_CONSTITUTIONAL_ADMISSION_RECEIPT_V0_1"
LEDGER_EVENT_SCHEMA = "GREMLIN_CONSTITUTIONAL_LEDGER_EVENT_V0_1"
TRANSITION_SCHEMA = "GREMLIN_CONSTITUTIONAL_TRANSITION_CERTIFICATE_V0_1"

MEMORY_ACCESS_RECEIPT_SCHEMA = "BESTIARY_MEMORY_ACCESS_RECEIPT_V0_1"

RADICAL_GATE_MAP = {
    ("consent", "GRANTED"): ("CONSENT", PASS),
    ("consent", "DENIED"): ("CONSENT", BLOCK),
    ("consent", "UNRESOLVED"): ("CONSENT", UNRESOLVED),
    ("reversibility", "SATISFIED"): ("REVERSIBILITY", PASS),
    ("reversibility", "FAILED"): ("REVERSIBILITY", BLOCK),
    ("reversibility", "UNRESOLVED"): ("REVERSIBILITY", UNRESOLVED),
    ("no_go", "CLEAR"): ("NO_GO", PASS),
    ("no_go", "HIT"): ("NO_GO", BLOCK),
    ("no_go", "UNRESOLVED"): ("NO_GO", UNRESOLVED),
}


class ConstitutionalError(ValueError):
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
        raise ConstitutionalError("constitutional values must be finite JSON data") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ConstitutionalError(f"{field} must be a string")
    out = value.strip()
    if not out:
        raise ConstitutionalError(f"{field} must be non-empty")
    return out


def _upper(value: Any, field: str) -> str:
    return _text(value, field).upper()


def _lattice(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value not in LATTICE:
        raise ConstitutionalError(f"{field} must be one of -1, 0, +1")
    return int(value)


def _unique_text(values: Sequence[str] | Iterable[str], field: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ConstitutionalError(f"{field} must be a sequence")
    out = sorted({_text(value, field) for value in values})
    return tuple(out)


def lattice_meet(values: Sequence[int] | Iterable[int]) -> int:
    rows = tuple(_lattice(value, "lattice value") for value in values)
    if not rows:
        raise ConstitutionalError("lattice meet requires at least one value")
    return min(rows)


def decision_from_scalar(value: int) -> str:
    code = _lattice(value, "admissibility scalar")
    if code == PASS:
        return "ALLOW"
    if code == BLOCK:
        return "DENY"
    return "DEFER"


def constitutional_manifest() -> dict[str, Any]:
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": CANON_ALLOWED,
        "normative_axioms_are_explicit_policy_not_theorems": True,
        "ethics_is_hard_admissibility_constraint": True,
        "ethics_weighting_allowed": False,
        "ethics_conflict_averaging_allowed": False,
        "utility_may_expand_admissible_domain": False,
        "raphael_subordinate_to_constitution": True,
        "unknown_high_consequence_admission": False,
        "silent_state_change_allowed": False,
        "ledger_delete_allowed": False,
        "parameter_source_classes": sorted(PARAMETER_SOURCE_CLASSES),
        "ethics_gates": list(ETHICS_GATES),
        "consequence_requirements": {
            key: list(value) for key, value in sorted(CONSEQUENCE_REQUIREMENTS.items())
        },
        "lattice": {
            "BLOCK": BLOCK,
            "UNRESOLVED": UNRESOLVED,
            "PASS": PASS,
            "meet": "MIN",
            "allow_iff": PASS,
        },
    }
    return {**core, "constitution_sha256": _sha256(core)}


def validate_constitutional_manifest(packet: Mapping[str, Any]) -> dict[str, Any]:
    expected = constitutional_manifest()
    if dict(packet) != expected:
        raise ConstitutionalError("mathematical constitution manifest mismatch")
    return expected


def build_parameter_record(
    *,
    name: str,
    value_expression: str,
    units: str,
    source_classification: str,
    source_ref: str,
    binding_status: str,
    derivation_ref: str | None = None,
    measurement_ref: str | None = None,
    uncertainty_ref: str | None = None,
    policy_ref: str | None = None,
    validity_ref: str | None = None,
) -> dict[str, Any]:
    source = _upper(source_classification, "source_classification")
    if source not in PARAMETER_SOURCE_CLASSES:
        raise ConstitutionalError("unsupported parameter source classification")
    binding = _upper(binding_status, "binding_status")
    if binding not in PARAMETER_BINDING_STATES:
        raise ConstitutionalError("unsupported parameter binding status")
    name_text = _text(name, "name")
    value_text = _text(value_expression, "value_expression")
    units_text = _text(units, "units")
    source_text = _text(source_ref, "source_ref")

    refs = {
        "derivation_ref": None if derivation_ref is None else _text(derivation_ref, "derivation_ref"),
        "measurement_ref": None if measurement_ref is None else _text(measurement_ref, "measurement_ref"),
        "uncertainty_ref": None if uncertainty_ref is None else _text(uncertainty_ref, "uncertainty_ref"),
        "policy_ref": None if policy_ref is None else _text(policy_ref, "policy_ref"),
        "validity_ref": None if validity_ref is None else _text(validity_ref, "validity_ref"),
    }
    if source == "DERIVED" and refs["derivation_ref"] is None:
        raise ConstitutionalError("derived parameter requires derivation_ref")
    if source == "MEASURED" and (
        refs["measurement_ref"] is None or refs["uncertainty_ref"] is None
    ):
        raise ConstitutionalError("measured parameter requires measurement_ref and uncertainty_ref")
    if source == "POLICY" and refs["policy_ref"] is None:
        raise ConstitutionalError("policy parameter requires policy_ref")

    core = {
        "schema": PARAMETER_SCHEMA,
        "version": VERSION,
        "name": name_text,
        "value_expression": value_text,
        "units": units_text,
        "source_classification": source,
        "source_ref": source_text,
        "binding_status": binding,
        **refs,
        "high_consequence_eligible": source != "UNKNOWN" and binding == "BOUND",
        "epistemic": EPISTEMIC,
        "canon_allowed": False,
    }
    return {**core, "parameter_sha256": _sha256(core)}


def validate_parameter_record(
    packet: Mapping[str, Any],
    *,
    high_consequence: bool = False,
) -> dict[str, Any]:
    if packet.get("schema") != PARAMETER_SCHEMA or packet.get("version") != VERSION:
        raise ConstitutionalError("unsupported constitutional parameter record")
    core = dict(packet)
    supplied = _text(core.pop("parameter_sha256", None), "parameter_sha256")
    source = _upper(core.get("source_classification"), "source_classification")
    binding = _upper(core.get("binding_status"), "binding_status")
    if source not in PARAMETER_SOURCE_CLASSES:
        raise ConstitutionalError("unsupported parameter source classification")
    if binding not in PARAMETER_BINDING_STATES:
        raise ConstitutionalError("unsupported parameter binding status")
    for key in ("name", "value_expression", "units", "source_ref"):
        _text(core.get(key), key)
    if source == "DERIVED" and core.get("derivation_ref") is None:
        raise ConstitutionalError("derived parameter requires derivation_ref")
    if source == "MEASURED" and (
        core.get("measurement_ref") is None or core.get("uncertainty_ref") is None
    ):
        raise ConstitutionalError("measured parameter requires measurement and uncertainty provenance")
    if source == "POLICY" and core.get("policy_ref") is None:
        raise ConstitutionalError("policy parameter requires policy_ref")
    eligible = source != "UNKNOWN" and binding == "BOUND"
    if core.get("high_consequence_eligible") is not eligible:
        raise ConstitutionalError("parameter eligibility claim mismatch")
    if core.get("epistemic") != EPISTEMIC or core.get("canon_allowed") is not False:
        raise ConstitutionalError("parameter authority boundary mismatch")
    if supplied != _sha256(core):
        raise ConstitutionalError("parameter commitment mismatch")
    if high_consequence and not eligible:
        raise ConstitutionalError("unbound or unknown parameter cannot control high-consequence admission")
    return {**core, "parameter_sha256": supplied}


def canonical_kappa_record() -> dict[str, Any]:
    return build_parameter_record(
        name="kappa",
        value_expression="ln(2)/(24*pi)",
        units="dimensionless",
        source_classification="POLICY",
        source_ref="NOEMA_CANONICAL_KAPPA",
        binding_status="UNBOUND",
        policy_ref="NOEMA_CANONICAL_KAPPA",
        validity_ref="CONSTITUTION_RECORD_ONLY_NO_OPERATOR_BINDING",
    )


def build_gate_receipt(
    *,
    gate: str,
    status: int,
    relation_ids: Sequence[str],
    source_ref: str,
    evidence_refs: Sequence[str],
    reason: str,
) -> dict[str, Any]:
    gate_name = _upper(gate, "gate")
    if gate_name not in ETHICS_GATES:
        raise ConstitutionalError(f"unknown ethics gate: {gate_name}")
    code = _lattice(status, "status")
    relations = _unique_text(relation_ids, "relation_id")
    evidence = _unique_text(evidence_refs, "evidence_ref")
    core = {
        "schema": GATE_SCHEMA,
        "version": VERSION,
        "gate": gate_name,
        "status": code,
        "relation_ids": list(relations),
        "source_ref": _text(source_ref, "source_ref"),
        "evidence_refs": list(evidence),
        "reason": _text(reason, "reason"),
        "hard_gate": True,
        "weighting_allowed": False,
        "conflict_averaging_allowed": False,
        "epistemic": EPISTEMIC,
        "canon_allowed": False,
    }
    return {**core, "receipt_id": "gcr:" + _sha256(core)}


def validate_gate_receipt(packet: Mapping[str, Any]) -> dict[str, Any]:
    if packet.get("schema") != GATE_SCHEMA or packet.get("version") != VERSION:
        raise ConstitutionalError("unsupported constitutional gate receipt")
    core = dict(packet)
    supplied = _text(core.pop("receipt_id", None), "receipt_id")
    gate = _upper(core.get("gate"), "gate")
    if gate not in ETHICS_GATES:
        raise ConstitutionalError("unknown constitutional gate")
    _lattice(core.get("status"), "status")
    relations = core.get("relation_ids")
    evidence = core.get("evidence_refs")
    if not isinstance(relations, list) or tuple(relations) != _unique_text(relations, "relation_id"):
        raise ConstitutionalError("gate relation_ids must be canonical and unique")
    if not isinstance(evidence, list) or tuple(evidence) != _unique_text(evidence, "evidence_ref"):
        raise ConstitutionalError("gate evidence_refs must be canonical and unique")
    for key in ("source_ref", "reason"):
        _text(core.get(key), key)
    if core.get("hard_gate") is not True:
        raise ConstitutionalError("constitutional ethics gate must remain hard")
    if core.get("weighting_allowed") is not False:
        raise ConstitutionalError("constitutional ethics gate cannot be weighted")
    if core.get("conflict_averaging_allowed") is not False:
        raise ConstitutionalError("constitutional ethics gate cannot be averaged")
    if core.get("epistemic") != EPISTEMIC or core.get("canon_allowed") is not False:
        raise ConstitutionalError("gate authority boundary mismatch")
    expected = "gcr:" + _sha256(core)
    if supplied != expected:
        raise ConstitutionalError("gate receipt commitment mismatch")
    return {**core, "receipt_id": supplied}


def radical_gate_status(role: str, status: str) -> tuple[str, int]:
    key = (_text(role, "role").lower(), _upper(status, "status"))
    try:
        return RADICAL_GATE_MAP[key]
    except KeyError as exc:
        raise ConstitutionalError("unsupported Radical ethics gate status") from exc


def capability_status_from_memory_receipt(packet: Mapping[str, Any]) -> int:
    if packet.get("schema") != MEMORY_ACCESS_RECEIPT_SCHEMA:
        raise ConstitutionalError("unsupported memory capability receipt")
    decision = _upper(packet.get("decision"), "decision")
    claims = packet.get("claims")
    if not isinstance(claims, Mapping):
        raise ConstitutionalError("memory capability receipt claims must be a mapping")
    if claims.get("deny_by_default") is not True or claims.get("decision_is_auditable") is not True:
        raise ConstitutionalError("memory capability receipt loses deny-by-default/audit boundary")
    if decision == "ALLOW":
        return PASS
    if decision == "DENY":
        return BLOCK
    raise ConstitutionalError("unsupported memory capability decision")


def build_action_contract(
    *,
    action_id: str,
    consequence_class: str,
    parameter_ids: Sequence[str] = (),
) -> dict[str, Any]:
    action = _text(action_id, "action_id")
    consequence = _upper(consequence_class, "consequence_class")
    if consequence not in CONSEQUENCE_REQUIREMENTS:
        raise ConstitutionalError("unsupported consequence class")
    params = _unique_text(parameter_ids, "parameter_id")
    core = {
        "schema": ACTION_SCHEMA,
        "version": VERSION,
        "action_id": action,
        "consequence_class": consequence,
        "required_ethics_gates": list(CONSEQUENCE_REQUIREMENTS[consequence]),
        "high_consequence": consequence in HIGH_CONSEQUENCE_CLASSES,
        "parameter_ids": list(params),
        "utility_can_override_admission": False,
        "epistemic": EPISTEMIC,
        "canon_allowed": False,
    }
    return {**core, "action_sha256": _sha256(core)}


def validate_action_contract(packet: Mapping[str, Any]) -> dict[str, Any]:
    if packet.get("schema") != ACTION_SCHEMA or packet.get("version") != VERSION:
        raise ConstitutionalError("unsupported constitutional action contract")
    core = dict(packet)
    supplied = _text(core.pop("action_sha256", None), "action_sha256")
    consequence = _upper(core.get("consequence_class"), "consequence_class")
    if consequence not in CONSEQUENCE_REQUIREMENTS:
        raise ConstitutionalError("unsupported consequence class")
    _text(core.get("action_id"), "action_id")
    expected_gates = list(CONSEQUENCE_REQUIREMENTS[consequence])
    if core.get("required_ethics_gates") != expected_gates:
        raise ConstitutionalError("action contract attempts to alter constitutional gate requirements")
    if core.get("high_consequence") is not (consequence in HIGH_CONSEQUENCE_CLASSES):
        raise ConstitutionalError("action consequence classification mismatch")
    params = core.get("parameter_ids")
    if not isinstance(params, list) or tuple(params) != _unique_text(params, "parameter_id"):
        raise ConstitutionalError("action parameter_ids must be canonical and unique")
    if core.get("utility_can_override_admission") is not False:
        raise ConstitutionalError("utility cannot widen constitutional admissibility")
    if core.get("epistemic") != EPISTEMIC or core.get("canon_allowed") is not False:
        raise ConstitutionalError("action authority boundary mismatch")
    if supplied != _sha256(core):
        raise ConstitutionalError("action contract commitment mismatch")
    return {**core, "action_sha256": supplied}


def _ethical_scalar(
    action: Mapping[str, Any],
    gate_receipts: Sequence[Mapping[str, Any]],
) -> tuple[int, dict[str, int]]:
    validated_action = validate_action_contract(action)
    by_gate: dict[str, int] = {}
    for packet in gate_receipts:
        receipt = validate_gate_receipt(packet)
        gate = receipt["gate"]
        if gate in by_gate:
            raise ConstitutionalError(f"duplicate constitutional gate receipt: {gate}")
        by_gate[gate] = int(receipt["status"])
    required = tuple(validated_action["required_ethics_gates"])
    gate_state = {gate: by_gate.get(gate, UNRESOLVED) for gate in required}
    return lattice_meet(tuple(gate_state.values())), gate_state


def _parameter_scalar(
    action: Mapping[str, Any],
    parameter_records: Sequence[Mapping[str, Any]],
) -> int:
    validated_action = validate_action_contract(action)
    required_ids = tuple(validated_action["parameter_ids"])
    by_id: dict[str, Mapping[str, Any]] = {}
    for packet in parameter_records:
        validated = validate_parameter_record(packet)
        pid = validated["parameter_sha256"]
        if pid in by_id:
            raise ConstitutionalError("duplicate constitutional parameter record")
        by_id[pid] = validated
    if not required_ids:
        return PASS
    states = []
    for pid in required_ids:
        packet = by_id.get(pid)
        if packet is None:
            states.append(UNRESOLVED)
            continue
        eligible = bool(packet["high_consequence_eligible"])
        if validated_action["high_consequence"] and not eligible:
            states.append(UNRESOLVED)
        else:
            states.append(PASS)
    return lattice_meet(states)


def evaluate_admission(
    *,
    action: Mapping[str, Any],
    gate_receipts: Sequence[Mapping[str, Any]],
    capability_status: int,
    authority_status: int,
    evidence_status: int,
    parameter_records: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    validated_action = validate_action_contract(action)
    ethical_scalar, gate_state = _ethical_scalar(validated_action, gate_receipts)
    parameter_scalar = _parameter_scalar(validated_action, parameter_records)
    capability = _lattice(capability_status, "capability_status")
    authority = _lattice(authority_status, "authority_status")
    evidence = _lattice(evidence_status, "evidence_status")
    global_scalar = lattice_meet(
        (ethical_scalar, capability, authority, evidence, parameter_scalar)
    )
    core = {
        "schema": DECISION_SCHEMA,
        "version": VERSION,
        "action_id": validated_action["action_id"],
        "action_sha256": validated_action["action_sha256"],
        "consequence_class": validated_action["consequence_class"],
        "decision": decision_from_scalar(global_scalar),
        "global_admissibility_scalar": global_scalar,
        "ethical_scalar": ethical_scalar,
        "capability_scalar": capability,
        "authority_scalar": authority,
        "evidence_scalar": evidence,
        "parameter_scalar": parameter_scalar,
        "required_gate_state": gate_state,
        "utility_participated_in_admission": False,
        "fail_closed_unknown": True,
        "epistemic": EPISTEMIC,
        "canon_allowed": False,
    }
    return {**core, "receipt_id": "car:" + _sha256(core)}


def validate_admission_receipt(packet: Mapping[str, Any]) -> dict[str, Any]:
    if packet.get("schema") != DECISION_SCHEMA or packet.get("version") != VERSION:
        raise ConstitutionalError("unsupported constitutional admission receipt")
    core = dict(packet)
    supplied = _text(core.pop("receipt_id", None), "receipt_id")
    for key in (
        "global_admissibility_scalar",
        "ethical_scalar",
        "capability_scalar",
        "authority_scalar",
        "evidence_scalar",
        "parameter_scalar",
    ):
        _lattice(core.get(key), key)
    expected_global = lattice_meet(
        (
            core["ethical_scalar"],
            core["capability_scalar"],
            core["authority_scalar"],
            core["evidence_scalar"],
            core["parameter_scalar"],
        )
    )
    if core.get("global_admissibility_scalar") != expected_global:
        raise ConstitutionalError("admission scalar composition mismatch")
    if core.get("decision") != decision_from_scalar(expected_global):
        raise ConstitutionalError("admission decision/scalar mismatch")
    gate_state = core.get("required_gate_state")
    if not isinstance(gate_state, Mapping) or not gate_state:
        raise ConstitutionalError("admission receipt requires gate state")
    for key, value in gate_state.items():
        if _upper(key, "gate") not in ETHICS_GATES:
            raise ConstitutionalError("unknown gate in admission receipt")
        _lattice(value, "gate status")
    for key in ("action_id", "action_sha256", "consequence_class"):
        _text(core.get(key), key)
    if core.get("utility_participated_in_admission") is not False:
        raise ConstitutionalError("utility cannot participate in constitutional admission")
    if core.get("fail_closed_unknown") is not True:
        raise ConstitutionalError("constitutional admission must fail closed on unknown")
    if core.get("epistemic") != EPISTEMIC or core.get("canon_allowed") is not False:
        raise ConstitutionalError("admission authority boundary mismatch")
    expected = "car:" + _sha256(core)
    if supplied != expected:
        raise ConstitutionalError("admission receipt commitment mismatch")
    return {**core, "receipt_id": supplied}


def admitted_action_ids(receipts: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    allowed = []
    for packet in receipts:
        receipt = validate_admission_receipt(packet)
        if receipt["decision"] == "ALLOW":
            allowed.append(receipt["action_id"])
    return tuple(sorted(set(allowed)))


def intersect_flow_masks(*masks: Sequence[bool]) -> tuple[bool, ...]:
    if not masks:
        raise ConstitutionalError("at least one flow mask is required")
    normalized = []
    dimension = None
    for index, mask in enumerate(masks):
        values = tuple(mask)
        if not values:
            raise ConstitutionalError("flow mask must be non-empty")
        if any(type(value) is not bool for value in values):
            raise ConstitutionalError(f"flow mask {index} must contain booleans only")
        if dimension is None:
            dimension = len(values)
        elif len(values) != dimension:
            raise ConstitutionalError("flow masks must have identical dimension")
        normalized.append(values)
    return tuple(all(mask[i] for mask in normalized) for i in range(dimension or 0))


def intersect_jump_sets(*families: Iterable[str]) -> tuple[str, ...]:
    if not families:
        raise ConstitutionalError("at least one jump family is required")
    sets = []
    for family in families:
        if isinstance(family, (str, bytes)):
            raise ConstitutionalError("jump family must be an iterable of event names")
        sets.append({_upper(value, "jump event") for value in family})
    return tuple(sorted(set.intersection(*sets)))


def build_ledger_event(*, event_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ConstitutionalError("ledger event payload must be a mapping")
    core = {
        "schema": LEDGER_EVENT_SCHEMA,
        "version": VERSION,
        "event_type": _upper(event_type, "event_type"),
        "payload": dict(payload),
    }
    return {**core, "event_id": "gce:" + _sha256(core)}


def validate_ledger_event(packet: Mapping[str, Any]) -> dict[str, Any]:
    if packet.get("schema") != LEDGER_EVENT_SCHEMA or packet.get("version") != VERSION:
        raise ConstitutionalError("unsupported constitutional ledger event")
    core = dict(packet)
    supplied = _text(core.pop("event_id", None), "event_id")
    _upper(core.get("event_type"), "event_type")
    if not isinstance(core.get("payload"), Mapping):
        raise ConstitutionalError("ledger event payload must be a mapping")
    expected = "gce:" + _sha256(core)
    if supplied != expected:
        raise ConstitutionalError("ledger event commitment mismatch")
    return {**core, "event_id": supplied}


def _ledger_index(ledger: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    if isinstance(ledger, (str, bytes)):
        raise ConstitutionalError("ledger must be a sequence")
    out: dict[str, dict[str, Any]] = {}
    for packet in ledger:
        event = validate_ledger_event(packet)
        event_id = event["event_id"]
        previous = out.get(event_id)
        if previous is not None and previous != event:
            raise ConstitutionalError("ledger event id collision")
        out[event_id] = event
    return out


def ledger_join(
    left: Sequence[Mapping[str, Any]],
    right: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    merged = _ledger_index(left)
    for event_id, event in _ledger_index(right).items():
        previous = merged.get(event_id)
        if previous is not None and previous != event:
            raise ConstitutionalError("ledger join content collision")
        merged[event_id] = event
    return tuple(merged[key] for key in sorted(merged))


def ledger_append(
    ledger: Sequence[Mapping[str, Any]],
    event: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    return ledger_join(ledger, (event,))


def ledger_precedes(
    older: Sequence[Mapping[str, Any]],
    newer: Sequence[Mapping[str, Any]],
) -> bool:
    left = _ledger_index(older)
    right = _ledger_index(newer)
    return all(event_id in right and right[event_id] == event for event_id, event in left.items())


def certify_transition(
    *,
    pre_state_commitment: str,
    post_state_commitment: str,
    admission_receipt: Mapping[str, Any],
    ledger_before: Sequence[Mapping[str, Any]],
    ledger_after: Sequence[Mapping[str, Any]],
    mutation_receipt_event_id: str | None = None,
) -> dict[str, Any]:
    admission = validate_admission_receipt(admission_receipt)
    pre = _text(pre_state_commitment, "pre_state_commitment")
    post = _text(post_state_commitment, "post_state_commitment")
    if not ledger_precedes(ledger_before, ledger_after):
        raise ConstitutionalError("transition would violate append-only ledger monotonicity")
    before = _ledger_index(ledger_before)
    after = _ledger_index(ledger_after)
    changed = pre != post
    if changed:
        if admission["decision"] != "ALLOW":
            raise ConstitutionalError("state change requires ALLOW constitutional admission")
        if set(after) == set(before):
            raise ConstitutionalError("state change requires an appended ledger event")
        receipt_id = _text(mutation_receipt_event_id, "mutation_receipt_event_id")
        if receipt_id in before or receipt_id not in after:
            raise ConstitutionalError("mutation receipt must be newly appended")
    elif mutation_receipt_event_id is not None:
        _text(mutation_receipt_event_id, "mutation_receipt_event_id")

    core = {
        "schema": TRANSITION_SCHEMA,
        "version": VERSION,
        "pre_state_commitment": pre,
        "post_state_commitment": post,
        "state_changed": changed,
        "admission_receipt_id": admission["receipt_id"],
        "decision": admission["decision"],
        "ledger_before_ids": sorted(before),
        "ledger_after_ids": sorted(after),
        "ledger_monotone": True,
        "mutation_receipt_event_id": mutation_receipt_event_id,
        "silent_state_change": False,
        "epistemic": EPISTEMIC,
        "canon_allowed": False,
    }
    return {**core, "certificate_id": "gct:" + _sha256(core)}


__all__ = [
    "ACTION_SCHEMA",
    "AUTHORITY",
    "BLOCK",
    "CANON_ALLOWED",
    "CONSEQUENCE_REQUIREMENTS",
    "ConstitutionalError",
    "DECISION_SCHEMA",
    "EPISTEMIC",
    "ETHICS_GATES",
    "GATE_SCHEMA",
    "HIGH_CONSEQUENCE_CLASSES",
    "LEDGER_EVENT_SCHEMA",
    "LATTICE",
    "PARAMETER_SCHEMA",
    "PASS",
    "SCHEMA",
    "TRANSITION_SCHEMA",
    "UNRESOLVED",
    "VERSION",
    "admitted_action_ids",
    "build_action_contract",
    "build_gate_receipt",
    "build_ledger_event",
    "build_parameter_record",
    "canonical_kappa_record",
    "capability_status_from_memory_receipt",
    "certify_transition",
    "constitutional_manifest",
    "decision_from_scalar",
    "evaluate_admission",
    "intersect_flow_masks",
    "intersect_jump_sets",
    "lattice_meet",
    "ledger_append",
    "ledger_join",
    "ledger_precedes",
    "radical_gate_status",
    "validate_action_contract",
    "validate_admission_receipt",
    "validate_constitutional_manifest",
    "validate_gate_receipt",
    "validate_ledger_event",
    "validate_parameter_record",
]
