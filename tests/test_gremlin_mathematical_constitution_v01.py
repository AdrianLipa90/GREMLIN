from __future__ import annotations

import copy
import hashlib
import json

import pytest

from gremlin_mcp.memory_capabilities import evaluate_access, issue_capability_token

from gremlin_mcp.mathematical_constitution import (
    BLOCK,
    ETHICS_GATES,
    PASS,
    UNRESOLVED,
    ConstitutionalError,
    admitted_action_ids,
    build_action_contract,
    build_gate_receipt,
    build_ledger_event,
    build_parameter_record,
    canonical_kappa_record,
    capability_status_from_memory_receipt,
    certify_transition,
    constitutional_manifest,
    evaluate_admission,
    intersect_flow_masks,
    intersect_jump_sets,
    lattice_meet,
    ledger_append,
    ledger_join,
    ledger_precedes,
    radical_gate_status,
    validate_action_contract,
    validate_admission_against_action,
    validate_admission_receipt,
    validate_constitutional_manifest,
    validate_gate_receipt,
    validate_parameter_record,
)


def _content_hash(value: dict) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _gate(gate: str, status: int = PASS) -> dict:
    return build_gate_receipt(
        gate=gate,
        status=status,
        relation_ids=("rel:1",),
        source_ref=f"test:{gate.lower()}",
        evidence_refs=(f"evidence:{gate.lower()}",),
        reason="test fixture",
    )


def _full_gates(*, override: dict[str, int] | None = None) -> list[dict]:
    state = dict(override or {})
    return [_gate(gate, state.get(gate, PASS)) for gate in ETHICS_GATES]


def _admission(
    action: dict,
    *,
    gates: list[dict] | None = None,
    capability: int = PASS,
    authority: int = PASS,
    evidence: int = PASS,
    parameters: tuple[dict, ...] = (),
) -> dict:
    if gates is None:
        gates = _full_gates()
    return evaluate_admission(
        action=action,
        gate_receipts=gates,
        capability_status=capability,
        authority_status=authority,
        evidence_status=evidence,
        parameter_records=parameters,
    )


def test_manifest_declares_non_bypass_and_no_weighted_ethics() -> None:
    manifest = constitutional_manifest()
    assert validate_constitutional_manifest(manifest) == manifest
    assert manifest["ethics_is_hard_admissibility_constraint"] is True
    assert manifest["ethics_weighting_allowed"] is False
    assert manifest["ethics_conflict_averaging_allowed"] is False
    assert manifest["utility_may_expand_admissible_domain"] is False
    assert manifest["raphael_subordinate_to_constitution"] is True
    assert manifest["unknown_high_consequence_admission"] is False
    assert manifest["ledger_delete_allowed"] is False


def test_exact_lattice_meet_is_non_compensating() -> None:
    assert lattice_meet((PASS, PASS, PASS)) == PASS
    assert lattice_meet((PASS, UNRESOLVED, PASS)) == UNRESOLVED
    assert lattice_meet((PASS, BLOCK, PASS)) == BLOCK
    assert lattice_meet((PASS,) * 100 + (BLOCK,)) == BLOCK


def test_high_consequence_action_requires_all_constitutional_gates() -> None:
    action = build_action_contract(action_id="mutate:test", consequence_class="MUTATION")
    assert action["required_ethics_gates"] == list(ETHICS_GATES)
    assert action["high_consequence"] is True

    tampered = copy.deepcopy(action)
    tampered["required_ethics_gates"].remove("LIFE_PROTECTION")
    with pytest.raises(ConstitutionalError, match="gate requirements"):
        validate_action_contract(tampered)


def test_missing_required_gate_can_only_defer_not_allow() -> None:
    action = build_action_contract(action_id="mutate:test", consequence_class="MUTATION")
    gates = [gate for gate in _full_gates() if gate["gate"] != "LIFE_PROTECTION"]
    receipt = _admission(action, gates=gates)
    assert receipt["ethical_scalar"] == UNRESOLVED
    assert receipt["global_admissibility_scalar"] == UNRESOLVED
    assert receipt["decision"] == "DEFER"
    validate_admission_receipt(receipt)


def test_blocked_gate_cannot_be_compensated_by_all_other_passes() -> None:
    action = build_action_contract(action_id="mutate:test", consequence_class="MUTATION")
    receipt = _admission(
        action,
        gates=_full_gates(override={"NO_GO": BLOCK}),
    )
    assert receipt["ethical_scalar"] == BLOCK
    assert receipt["decision"] == "DENY"


def test_capability_deny_cannot_be_overridden_by_ethics_or_evidence() -> None:
    action = build_action_contract(action_id="append:test", consequence_class="APPEND_ONLY")
    receipt = _admission(
        action,
        capability=BLOCK,
        authority=PASS,
        evidence=PASS,
    )
    assert receipt["ethical_scalar"] == PASS
    assert receipt["capability_scalar"] == BLOCK
    assert receipt["global_admissibility_scalar"] == BLOCK
    assert receipt["decision"] == "DENY"


def test_unknown_authority_or_evidence_fails_closed_to_defer() -> None:
    action = build_action_contract(action_id="govern:test", consequence_class="GOVERNANCE")
    authority_unknown = _admission(action, authority=UNRESOLVED)
    evidence_unknown = _admission(action, evidence=UNRESOLVED)
    assert authority_unknown["decision"] == "DEFER"
    assert evidence_unknown["decision"] == "DEFER"


def test_admission_receipt_cannot_hide_a_required_gate() -> None:
    action = build_action_contract(action_id="mutate:test", consequence_class="MUTATION")
    receipt = _admission(action)
    validate_admission_receipt(receipt)

    tampered = copy.deepcopy(receipt)
    tampered["required_ethics_gates"].remove("NO_GO")
    tampered["required_gate_state"].pop("NO_GO")
    core = dict(tampered)
    core.pop("receipt_id")
    tampered["receipt_id"] = "car:" + _content_hash(core)
    with pytest.raises(ConstitutionalError, match="consequence class"):
        validate_admission_receipt(tampered)


def test_radical_gate_adapter_is_exact_and_unweighted() -> None:
    assert radical_gate_status("consent", "GRANTED") == ("CONSENT", PASS)
    assert radical_gate_status("consent", "UNRESOLVED") == ("CONSENT", UNRESOLVED)
    assert radical_gate_status("consent", "DENIED") == ("CONSENT", BLOCK)

    assert radical_gate_status("reversibility", "SATISFIED") == ("REVERSIBILITY", PASS)
    assert radical_gate_status("reversibility", "FAILED") == ("REVERSIBILITY", BLOCK)

    assert radical_gate_status("no_go", "CLEAR") == ("NO_GO", PASS)
    assert radical_gate_status("no_go", "HIT") == ("NO_GO", BLOCK)


def test_memory_capability_receipt_adapter_validates_full_receipt() -> None:
    token = issue_capability_token(
        beast="SPIDER",
        layer="RELATIONAL",
        operation="GRAPH_APPEND",
        artifact_type="RELATION_EDGE",
        subject_scope="subject:1",
        generation_scope="generation:1",
        task_scope="task:1",
    )
    allow = evaluate_access(
        beast="SPIDER",
        layer="RELATIONAL",
        operation="GRAPH_APPEND",
        artifact_type="RELATION_EDGE",
        subject_id="subject:1",
        generation_id="generation:1",
        task_id="task:1",
        token=token,
    )
    deny = evaluate_access(
        beast="SPIDER",
        layer="RELATIONAL",
        operation="DELETE",
        artifact_type="RELATION_EDGE",
        subject_id="subject:1",
        generation_id="generation:1",
        task_id="task:1",
        token=None,
    )
    assert capability_status_from_memory_receipt(allow) == PASS
    assert capability_status_from_memory_receipt(deny) == BLOCK

    forged = copy.deepcopy(deny)
    forged["decision"] = "ALLOW"
    with pytest.raises(ConstitutionalError, match="invalid Bestiary"):
        capability_status_from_memory_receipt(forged)


def test_parameter_provenance_classes_are_explicit() -> None:
    derived = build_parameter_record(
        name="derived-x",
        value_expression="2*pi",
        units="dimensionless",
        source_classification="DERIVED",
        source_ref="proof:x",
        binding_status="BOUND",
        derivation_ref="proof:x",
    )
    measured = build_parameter_record(
        name="measured-x",
        value_expression="1.25",
        units="s",
        source_classification="MEASURED",
        source_ref="measurement:x",
        binding_status="BOUND",
        measurement_ref="measurement:x",
        uncertainty_ref="uncertainty:x",
    )
    policy = build_parameter_record(
        name="policy-x",
        value_expression="3",
        units="count",
        source_classification="POLICY",
        source_ref="policy:x",
        binding_status="BOUND",
        policy_ref="policy:x",
    )
    for record in (derived, measured, policy):
        validate_parameter_record(record, high_consequence=True)


def test_unknown_or_unbound_parameter_cannot_control_high_consequence_action() -> None:
    unknown = build_parameter_record(
        name="unknown-x",
        value_expression="UNKNOWN",
        units="dimensionless",
        source_classification="UNKNOWN",
        source_ref="open:x",
        binding_status="OPEN",
    )
    with pytest.raises(ConstitutionalError, match="high-consequence"):
        validate_parameter_record(unknown, high_consequence=True)

    action = build_action_contract(
        action_id="mutate:param",
        consequence_class="MUTATION",
        parameter_ids=(unknown["parameter_sha256"],),
    )
    receipt = _admission(action, parameters=(unknown,))
    assert receipt["parameter_scalar"] == UNRESOLVED
    assert receipt["decision"] == "DEFER"


def test_kappa_is_canonical_but_constitutionally_unbound() -> None:
    kappa = canonical_kappa_record()
    validated = validate_parameter_record(kappa)
    assert validated["value_expression"] == "ln(2)/(24*pi)"
    assert validated["source_classification"] == "POLICY"
    assert validated["binding_status"] == "UNBOUND"
    assert validated["high_consequence_eligible"] is False
    with pytest.raises(ConstitutionalError):
        validate_parameter_record(kappa, high_consequence=True)


def test_flow_mask_intersection_is_exact_commutative_and_idempotent() -> None:
    a = (True, True, False, True)
    b = (True, False, True, True)
    expected = (True, False, False, True)
    assert intersect_flow_masks(a, b) == expected
    assert intersect_flow_masks(b, a) == expected
    assert intersect_flow_masks(a, a) == a


def test_jump_admission_is_exact_set_intersection() -> None:
    capability = {"GRAPH_APPEND", "EDGE_APPEND", "DELETE"}
    authority = {"GRAPH_APPEND", "EDGE_APPEND"}
    ethics = {"GRAPH_APPEND", "EDGE_APPEND", "NODE_LINK"}
    governance = {"GRAPH_APPEND"}
    assert intersect_jump_sets(capability, authority, ethics, governance) == ("GRAPH_APPEND",)


def test_ledger_join_is_semilattice_and_append_only() -> None:
    a = build_ledger_event(event_type="OBSERVATION", payload={"x": 1})
    b = build_ledger_event(event_type="RECEIPT", payload={"x": 2})
    c = build_ledger_event(event_type="GRAPH_APPEND", payload={"x": 3})

    la = (a,)
    lb = (b,)
    lc = (c,)

    assert ledger_join(la, la) == la
    assert ledger_join(la, lb) == ledger_join(lb, la)
    assert ledger_join(ledger_join(la, lb), lc) == ledger_join(la, ledger_join(lb, lc))

    appended = ledger_append(la, b)
    assert ledger_precedes(la, appended) is True
    assert ledger_precedes(appended, la) is False


def test_state_change_requires_allow_and_new_mutation_receipt() -> None:
    action = build_action_contract(action_id="mutate:state", consequence_class="MUTATION")
    allow = _admission(action)
    event = build_ledger_event(
        event_type="MUTATION_RECEIPT",
        payload={
            "action_id": action["action_id"],
            "action_sha256": action["action_sha256"],
            "admission_receipt_id": allow["receipt_id"],
            "pre_state_commitment": "state:before",
            "post_state_commitment": "state:after",
        },
    )
    after = ledger_append((), event)

    cert = certify_transition(
        action_contract=action,
        pre_state_commitment="state:before",
        post_state_commitment="state:after",
        admission_receipt=allow,
        ledger_before=(),
        ledger_after=after,
        mutation_receipt_event_id=event["event_id"],
    )
    assert cert["state_changed"] is True
    assert cert["ledger_monotone"] is True
    assert cert["silent_state_change"] is False


def test_deny_or_defer_cannot_certify_state_change() -> None:
    action = build_action_contract(action_id="mutate:state", consequence_class="MUTATION")
    deny = _admission(action, capability=BLOCK)
    deny_event = build_ledger_event(
        event_type="MUTATION_RECEIPT",
        payload={
            "action_id": action["action_id"],
            "action_sha256": action["action_sha256"],
            "admission_receipt_id": deny["receipt_id"],
            "pre_state_commitment": "before",
            "post_state_commitment": "after",
        },
    )
    with pytest.raises(ConstitutionalError, match="ALLOW"):
        certify_transition(
            action_contract=action,
            pre_state_commitment="before",
            post_state_commitment="after",
            admission_receipt=deny,
            ledger_before=(),
            ledger_after=(deny_event,),
            mutation_receipt_event_id=deny_event["event_id"],
        )

    defer = _admission(action, authority=UNRESOLVED)
    defer_event = build_ledger_event(
        event_type="MUTATION_RECEIPT",
        payload={
            "action_id": action["action_id"],
            "action_sha256": action["action_sha256"],
            "admission_receipt_id": defer["receipt_id"],
            "pre_state_commitment": "before",
            "post_state_commitment": "after",
        },
    )
    with pytest.raises(ConstitutionalError, match="ALLOW"):
        certify_transition(
            action_contract=action,
            pre_state_commitment="before",
            post_state_commitment="after",
            admission_receipt=defer,
            ledger_before=(),
            ledger_after=(defer_event,),
            mutation_receipt_event_id=defer_event["event_id"],
        )


def test_silent_mutation_without_new_ledger_event_is_rejected() -> None:
    action = build_action_contract(action_id="mutate:state", consequence_class="MUTATION")
    allow = _admission(action)
    with pytest.raises(ConstitutionalError, match="appended ledger event"):
        certify_transition(
            action_contract=action,
            pre_state_commitment="before",
            post_state_commitment="after",
            admission_receipt=allow,
            ledger_before=(),
            ledger_after=(),
            mutation_receipt_event_id="gce:" + "0" * 64,
        )


def test_utility_has_no_surface_to_promote_denied_action() -> None:
    allow_action = build_action_contract(
        action_id="action:allow",
        consequence_class="ANALYTIC_NON_ACTUATING",
    )
    deny_action = build_action_contract(
        action_id="action:deny",
        consequence_class="ANALYTIC_NON_ACTUATING",
    )

    allow_receipt = _admission(
        allow_action,
        gates=[
            _gate("EPISTEMIC_INTEGRITY"),
            _gate("PROVENANCE_INTEGRITY"),
        ],
    )
    deny_receipt = _admission(
        deny_action,
        gates=[
            _gate("EPISTEMIC_INTEGRITY", BLOCK),
            _gate("PROVENANCE_INTEGRITY"),
        ],
    )

    utility = {"action:allow": -1_000_000, "action:deny": 1_000_000_000}
    assert utility["action:deny"] > utility["action:allow"]
    assert admitted_action_ids(
        (allow_receipt, deny_receipt),
        (allow_action, deny_action),
    ) == ("action:allow",)


def test_gate_receipt_tamper_fails_commitment_validation() -> None:
    receipt = _gate("NO_GO")
    validate_gate_receipt(receipt)
    tampered = copy.deepcopy(receipt)
    tampered["status"] = BLOCK
    with pytest.raises(ConstitutionalError, match="commitment"):
        validate_gate_receipt(tampered)


def test_transition_cannot_reuse_allow_receipt_for_different_action() -> None:
    admitted_action = build_action_contract(
        action_id="mutate:admitted",
        consequence_class="MUTATION",
    )
    executed_action = build_action_contract(
        action_id="mutate:different",
        consequence_class="MUTATION",
    )
    allow = _admission(admitted_action)
    event = build_ledger_event(
        event_type="MUTATION_RECEIPT",
        payload={
            "action_id": executed_action["action_id"],
            "action_sha256": executed_action["action_sha256"],
            "admission_receipt_id": allow["receipt_id"],
            "pre_state_commitment": "before",
            "post_state_commitment": "after",
        },
    )
    with pytest.raises(ConstitutionalError, match="does not match"):
        certify_transition(
            action_contract=executed_action,
            pre_state_commitment="before",
            post_state_commitment="after",
            admission_receipt=allow,
            ledger_before=(),
            ledger_after=(event,),
            mutation_receipt_event_id=event["event_id"],
        )


def test_mutation_receipt_must_bind_exact_pre_and_post_state() -> None:
    action = build_action_contract(action_id="mutate:bound", consequence_class="MUTATION")
    allow = _admission(action)
    event = build_ledger_event(
        event_type="MUTATION_RECEIPT",
        payload={
            "action_id": action["action_id"],
            "action_sha256": action["action_sha256"],
            "admission_receipt_id": allow["receipt_id"],
            "pre_state_commitment": "wrong-before",
            "post_state_commitment": "after",
        },
    )
    with pytest.raises(ConstitutionalError, match="state/action binding"):
        certify_transition(
            action_contract=action,
            pre_state_commitment="before",
            post_state_commitment="after",
            admission_receipt=allow,
            ledger_before=(),
            ledger_after=(event,),
            mutation_receipt_event_id=event["event_id"],
        )


def test_admission_receipt_is_bound_to_full_action_contract() -> None:
    action = build_action_contract(
        action_id="analytic:bound",
        consequence_class="ANALYTIC_NON_ACTUATING",
    )
    receipt = _admission(
        action,
        gates=[
            _gate("EPISTEMIC_INTEGRITY"),
            _gate("PROVENANCE_INTEGRITY"),
        ],
    )
    assert validate_admission_against_action(receipt, action)["decision"] == "ALLOW"

    other = build_action_contract(
        action_id="analytic:other",
        consequence_class="ANALYTIC_NON_ACTUATING",
    )
    with pytest.raises(ConstitutionalError, match="action_id"):
        validate_admission_against_action(receipt, other)
