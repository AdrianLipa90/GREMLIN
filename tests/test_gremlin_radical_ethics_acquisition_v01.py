import copy

import pytest

from tools.gremlin_kaku_radical_scalar_plane_v01 import build_kaku_scalar_packet, validate_radical_scalar_admission
from tools.gremlin_phasenav_compiler_v01 import CANDIDATE_SCHEMA
from tools.gremlin_radical_ethics_acquisition_v01 import (
    IMPLEMENTATION_DONORS,
    GremlinRadicalEthicsError,
    build_ethics_acquisition_bundle,
    build_gate_receipt,
    build_radical_admission_from_ethics_acquisition,
    build_scalar_producer_contract,
    build_scalar_receipt,
    validate_ethics_acquisition_bundle,
    validate_gate_receipt,
    validate_scalar_producer_contract,
    validate_scalar_receipt,
)
from tools.gremlin_scalar_admitted_phasenav_v02 import (
    GremlinScalarAdmissionCompileError,
    compile_scalar_admitted_phasenav_ir_v02,
)

HASH = "22" * 32
RELATIONS = ["rel-lock", "rel-torsion"]


def obs(value, name):
    return {
        "value": value,
        "scale_id": f"{name}/v1",
        "source_ref": f"evidence:{name}",
        "epistemic_status": "OBSERVED_CANDIDATE",
    }


def kaku(kid, operator):
    return build_kaku_scalar_packet(
        kaku_id=kid,
        operator_kind=operator,
        direction="FORWARD",
        polarity=1.0,
        role="RELATION",
        source_binding=f"source:{kid}",
        target_binding=f"target:{kid}",
        valuation=obs(0.4, "valuation"),
        affect=obs(0.1, "affect"),
        intention_alignment=obs(0.8, "intention"),
        epistemic_support=obs(0.9, "epistemic"),
    )


def candidate():
    return {
        "schema": CANDIDATE_SCHEMA,
        "candidate_id": "candidate-ethics-001",
        "status": "SURVIVED_AUDIT",
        "audit": {"belzebub_result": "SURVIVED"},
        "relations": [
            {"kind": "phase_lock", "a": 0, "b": 1, "gain": 1.0, "source_ref": "rel-lock"},
            {"kind": "torsion", "i": 2, "j": 3, "m": 3, "n": 2, "tau": 0.37, "gain": 1.25, "source_ref": "rel-torsion"},
        ],
    }


def producer(role, *, source="TEST_FIXTURE", live=False, scale=None):
    return build_scalar_producer_contract(
        producer_id=f"producer:{role}",
        producer_version="0.1",
        semantic_role=role,
        scale_id=scale or f"{role}/v1",
        formula_contract_ref=f"formula:{role}/v1",
        implementation_ref=f"implementation:{role}/v1",
        source_classification=source,
        producer_classification="TEST_PRODUCER" if source == "TEST_FIXTURE" else "SEMANTICALLY_BOUND_PRODUCER_CANDIDATE",
        live_required=live,
    )


def scalar_receipt(role, value, *, supports=(), source="TEST_FIXTURE", live=False, scale=None):
    return build_scalar_receipt(
        producer_contract=producer(role, source=source, live=live, scale=scale),
        value=value,
        source_ref=f"source:{role}",
        input_commitment=HASH,
        epistemic_status="OBSERVED_CANDIDATE",
        evidence_refs=[f"evidence:{role}"],
        support_receipt_ids=supports,
        live_surface_ref="/dev/shm/ciel_noema" if live else None,
    )


def gate(role, status, *, relation_ids=RELATIONS, source="TEST_FIXTURE", live=False):
    return build_gate_receipt(
        gate_role=role,
        status=status,
        relation_ids=relation_ids,
        source_ref=f"source:{role}",
        decision_context_commitment=HASH,
        epistemic_status="OBSERVED_CANDIDATE",
        evidence_refs=[f"evidence:{role}"],
        reason=f"{role}:{status}",
        subject_refs=["agent:affected"] if role == "consent" else [],
        source_classification=source,
        live_required=live,
        live_surface_ref="/dev/shm/ciel_noema" if live else None,
    )


def ethics_receipts(*, consent="GRANTED", reversibility="SATISFIED", no_go="CLEAR", ethical_value=0.75):
    contradiction = scalar_receipt("contradiction_load", 0.1)
    recursive = scalar_receipt("recursive_integrity", 0.85, supports=[contradiction["receipt_id"]])
    consent_r = gate("consent", consent)
    reverse_r = gate("reversibility", reversibility)
    nogo_r = gate("no_go", no_go)
    ethical = scalar_receipt(
        "ethical_integrity",
        ethical_value,
        supports=[
            recursive["receipt_id"],
            consent_r["receipt_id"],
            reverse_r["receipt_id"],
            nogo_r["receipt_id"],
        ],
    )
    return [contradiction, recursive, ethical], [consent_r, reverse_r, nogo_r]


def bundle(**kwargs):
    scalars, gates = ethics_receipts(**kwargs)
    return build_ethics_acquisition_bundle(
        relation_ids=RELATIONS,
        scalar_receipts=scalars,
        gate_receipts=gates,
    )


def radical(ethics_bundle):
    return build_radical_admission_from_ethics_acquisition(
        ethics_bundle=ethics_bundle,
        radical_id="radical-ethics-001",
        candidate_id="candidate-ethics-001",
        ordered_kaku_packets=[kaku("k0", "SOURCE"), kaku("k1", "TRANSFORM")],
        relation_ids=RELATIONS,
        evidence_refs=["candidate:candidate-ethics-001"],
    )


def test_scalar_producers_are_deterministic_and_semantically_bound():
    a = producer("ethical_integrity")
    b = producer("ethical_integrity")
    assert validate_scalar_producer_contract(a)
    assert a == b
    assert a["canonical_term_id"] == "CLX2-DYN-011"
    assert a["support_term_ids"] == [
        "CLX2-DYN-010",
        "CLX2-DYN-012",
        "CLX2-DYN-013",
        "CLX2-DYN-014",
        "CLX2-SEM-019",
    ]
    assert a["realization_stage"] == "PRE_VECTOR_CONTEXTUAL_ASSESSMENT"


def test_recursive_integrity_declares_contradiction_dependency():
    p = producer("recursive_integrity")
    assert p["canonical_term_id"] == "CLX2-DYN-010"
    assert p["support_term_ids"] == ["CLX2-DYN-009", "CLX2-TIME-009"]


def test_gate_receipts_preserve_structural_status_and_relation_coverage():
    c = gate("consent", "GRANTED")
    r = gate("reversibility", "SATISFIED")
    n = gate("no_go", "CLEAR")
    assert validate_gate_receipt(c)
    assert validate_gate_receipt(r)
    assert validate_gate_receipt(n)
    assert c["canonical_term_id"] == "CLX2-DYN-012"
    assert c["subject_refs"] == ["agent:affected"]
    assert c["gate_is_structural"] is True
    assert c["gate_weighting_allowed"] is False
    assert c["relation_ids"] == sorted(RELATIONS)


@pytest.mark.parametrize(
    "role,status",
    [
        ("consent", "MAYBE"),
        ("reversibility", "PARTIAL"),
        ("no_go", "WARN"),
    ],
)
def test_unknown_gate_status_fails_closed(role, status):
    with pytest.raises(GremlinRadicalEthicsError, match="unsupported"):
        gate(role, status)


def test_consent_requires_affected_subject_lineage():
    with pytest.raises(GremlinRadicalEthicsError, match="affected subject"):
        build_gate_receipt(
            gate_role="consent",
            status="GRANTED",
            relation_ids=RELATIONS,
            source_ref="source:consent",
            decision_context_commitment=HASH,
            epistemic_status="OBSERVED_CANDIDATE",
            evidence_refs=[],
            subject_refs=[],
        )


def test_live_scalar_producer_requires_live_noema_witness():
    with pytest.raises(GremlinRadicalEthicsError, match="LIVE_NOEMA_WITNESS"):
        producer("recursive_integrity", source="STATIC_REFERENCE", live=True)


def test_live_scalar_receipt_requires_canonical_noema_surface():
    p = producer("recursive_integrity", source="LIVE_NOEMA_WITNESS", live=True)
    with pytest.raises(GremlinRadicalEthicsError, match="canonical NOEMA surface"):
        build_scalar_receipt(
            producer_contract=p,
            value=0.8,
            source_ref="source:recursive",
            input_commitment=HASH,
            epistemic_status="LIVE_OBSERVATION_CANDIDATE",
            evidence_refs=[],
            live_surface_ref="/tmp/fake-noema",
        )


def test_live_gate_receipt_requires_canonical_noema_surface():
    with pytest.raises(GremlinRadicalEthicsError, match="canonical NOEMA surface"):
        build_gate_receipt(
            gate_role="no_go",
            status="CLEAR",
            relation_ids=RELATIONS,
            source_ref="source:nogo",
            decision_context_commitment=HASH,
            epistemic_status="LIVE_OBSERVATION_CANDIDATE",
            evidence_refs=[],
            source_classification="LIVE_NOEMA_WITNESS",
            live_required=True,
            live_surface_ref="/tmp/fake-noema",
        )


def test_scale_mismatch_fails_without_conversion():
    p = producer("contradiction_load", scale="contradiction/unit-a")
    with pytest.raises(GremlinRadicalEthicsError, match="observed scale differs"):
        build_scalar_receipt(
            producer_contract=p,
            value=0.1,
            source_ref="source:contradiction",
            input_commitment=HASH,
            epistemic_status="OBSERVED_CANDIDATE",
            evidence_refs=[],
            observed_scale_id="contradiction/unit-b",
        )


def test_nonfinite_ethics_scalar_fails_closed():
    p = producer("ethical_integrity")
    with pytest.raises(GremlinRadicalEthicsError, match="value must be finite"):
        build_scalar_receipt(
            producer_contract=p,
            value=float("nan"),
            source_ref="source:ethics",
            input_commitment=HASH,
            epistemic_status="OBSERVED_CANDIDATE",
            evidence_refs=[],
        )


def test_recursive_integrity_must_bind_contradiction_receipt():
    contradiction = scalar_receipt("contradiction_load", 0.1)
    recursive = scalar_receipt("recursive_integrity", 0.85)
    c, r, n = gate("consent", "GRANTED"), gate("reversibility", "SATISFIED"), gate("no_go", "CLEAR")
    ethical = scalar_receipt("ethical_integrity", 0.75, supports=[recursive["receipt_id"], c["receipt_id"], r["receipt_id"], n["receipt_id"]])
    with pytest.raises(GremlinRadicalEthicsError, match="bind contradiction lineage"):
        build_ethics_acquisition_bundle(
            relation_ids=RELATIONS,
            scalar_receipts=[contradiction, recursive, ethical],
            gate_receipts=[c, r, n],
        )


def test_ethical_integrity_must_bind_recursive_integrity_and_all_hard_gates():
    contradiction = scalar_receipt("contradiction_load", 0.1)
    recursive = scalar_receipt("recursive_integrity", 0.85, supports=[contradiction["receipt_id"]])
    c, r, n = gate("consent", "GRANTED"), gate("reversibility", "SATISFIED"), gate("no_go", "CLEAR")
    ethical = scalar_receipt("ethical_integrity", 0.75, supports=[recursive["receipt_id"], c["receipt_id"], r["receipt_id"]])
    with pytest.raises(GremlinRadicalEthicsError, match="all structural gate receipts"):
        build_ethics_acquisition_bundle(
            relation_ids=RELATIONS,
            scalar_receipts=[contradiction, recursive, ethical],
            gate_receipts=[c, r, n],
        )


def test_duplicate_gate_role_fails_instead_of_averaging():
    scalars, gates = ethics_receipts()
    gates.append(gate("consent", "DENIED"))
    with pytest.raises(GremlinRadicalEthicsError, match="conflicting duplicate structural gate role"):
        build_ethics_acquisition_bundle(relation_ids=RELATIONS, scalar_receipts=scalars, gate_receipts=gates)


def test_gate_relation_coverage_must_match_radical_lineage():
    scalars, gates = ethics_receipts()
    gates[2] = gate("no_go", "CLEAR", relation_ids=["rel-lock"])
    ethical = scalar_receipt(
        "ethical_integrity",
        0.75,
        supports=[scalars[1]["receipt_id"], gates[0]["receipt_id"], gates[1]["receipt_id"], gates[2]["receipt_id"]],
    )
    scalars[2] = ethical
    with pytest.raises(GremlinRadicalEthicsError, match="relation coverage differs"):
        build_ethics_acquisition_bundle(relation_ids=RELATIONS, scalar_receipts=scalars, gate_receipts=gates)


def test_bundle_is_deterministic_self_contained_and_pre_vector():
    a = bundle()
    b = bundle()
    assert validate_ethics_acquisition_bundle(a)
    assert a == b
    ethical = next(x for x in a["scalar_receipts"] if x["semantic_role"] == "ethical_integrity")
    assert len(ethical["support_receipt_ids"]) == 4
    assert a["pre_vector_stage"] == "PRE_VECTOR_CONTEXTUAL_ASSESSMENT"
    assert a["relational_ethics_realization_stage"] == "POST_REALIZATION_RELATIONAL_ETHICS"
    assert a["relational_ethics_realization_pending"] is True
    assert a["gate_weighting_used"] is False
    assert a["gate_conflict_averaging_used"] is False


def test_serialized_bundle_lineage_tamper_is_detected_before_commitment_check():
    record = bundle()
    ethical = next(x for x in record["scalar_receipts"] if x["semantic_role"] == "ethical_integrity")
    ethical["support_receipt_ids"] = ethical["support_receipt_ids"][:-1]
    with pytest.raises(GremlinRadicalEthicsError, match="all structural gate receipts"):
        validate_ethics_acquisition_bundle(record)


def test_acquired_ethics_builds_valid_admitted_radical():
    record = radical(bundle())
    assert validate_radical_scalar_admission(record)
    assert record["status"] == "PRE_VECTOR_ADMITTED"
    assert record["vector_synthesis_allowed"] is True
    assert any(ref.startswith("ethics-acquisition:") for ref in record["evidence_refs"])


@pytest.mark.parametrize(
    "kwargs",
    [
        {"consent": "DENIED"},
        {"reversibility": "FAILED"},
        {"no_go": "HIT"},
    ],
)
def test_each_acquired_structural_gate_blocks_radical(kwargs):
    record = radical(bundle(**kwargs))
    assert validate_radical_scalar_admission(record)
    assert record["status"] == "PRE_VECTOR_BLOCKED"
    assert record["vector_synthesis_allowed"] is False


def test_large_contextual_ethics_value_cannot_override_denied_consent():
    record = radical(bundle(consent="DENIED", ethical_value=1.0e12))
    assert record["status"] == "PRE_VECTOR_BLOCKED"
    assert record["vector_synthesis_allowed"] is False


def test_gate_receipt_change_changes_radical_commitment():
    admitted = radical(bundle(consent="GRANTED"))
    denied = radical(bundle(consent="DENIED"))
    assert admitted["radical_scalar_commitment"] != denied["radical_scalar_commitment"]


def test_admitted_ethics_chain_reaches_scalar_admitted_phasenav_ir():
    record = radical(bundle())
    ir = compile_scalar_admitted_phasenav_ir_v02(candidate(), record)
    assert ir["pre_vector_admission"]["status"] == "PRE_VECTOR_ADMITTED"
    assert ir["execution_admitted"] is False
    assert ir["canon_allowed"] is False


def test_blocked_ethics_chain_cannot_reach_phasenav_ir():
    record = radical(bundle(no_go="HIT"))
    with pytest.raises(GremlinScalarAdmissionCompileError, match="not admitted"):
        compile_scalar_admitted_phasenav_ir_v02(candidate(), record)


def test_implementation_donors_preserve_stage_and_scope():
    legacy = IMPLEMENTATION_DONORS["ciel_ethical_engine"]
    noema = IMPLEMENTATION_DONORS["noema_relational_ethics_field_v2_1"]
    assert legacy["binding_status"] == "PARTIAL_FEATURE_DONOR_CANDIDATE"
    assert legacy["realization_stage"] == "POST_REALIZATION_RELATIONAL_ETHICS"
    assert noema["binding_status"] == "HARDPATH_VALIDATED_DONOR"
    assert noema["realization_stage"] == "POST_REALIZATION_RELATIONAL_ETHICS"
    assert noema["operating_mode"] == "LIVE_COMPUTE_ON_EXCHANGE_NO_STATIC_ETHICS_STATE"
