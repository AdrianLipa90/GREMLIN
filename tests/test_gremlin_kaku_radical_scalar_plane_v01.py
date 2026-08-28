import pytest

from tools.gremlin_kaku_radical_scalar_plane_v01 import (
    GremlinScalarPlaneError,
    build_kaku_scalar_packet,
    build_radical_scalar_admission,
    validate_kaku_scalar_packet,
    validate_radical_scalar_admission,
)


def obs(value, name):
    return {
        "value": value,
        "scale_id": f"{name}/v1",
        "source_ref": f"evidence:{name}",
        "epistemic_status": "OBSERVED_CANDIDATE",
    }


def packet(kaku_id="k0", operator_kind="SOURCE", polarity=1.0):
    return build_kaku_scalar_packet(
        kaku_id=kaku_id,
        operator_kind=operator_kind,
        direction="FORWARD",
        polarity=polarity,
        role="RELATION_SOURCE",
        source_binding=f"source:{kaku_id}",
        target_binding=f"target:{kaku_id}",
        valuation=obs(0.4, "valuation"),
        affect=obs(-0.2, "affect"),
        intention_alignment=obs(0.8, "intention"),
        epistemic_support=obs(0.9, "epistemic"),
        evidence_refs=["z", "a"],
    )


def admitted_radical(**overrides):
    data = dict(
        radical_id="radical-001",
        candidate_id="candidate-001",
        ordered_kaku_packets=[
            packet("k0", "SOURCE"),
            packet("k1", "TRANSFORM"),
            packet("k2", "IDENTITY"),
        ],
        relation_ids=["r0", "r1"],
        ethical_integrity=obs(0.75, "ethics"),
        consent_gate={"status": "GRANTED", "source_ref": "consent:receipt", "reason": "explicit"},
        reversibility_gate={"status": "SATISFIED", "source_ref": "reversibility:test", "reason": "bounded"},
        no_go_gate={"status": "CLEAR", "source_ref": "nogo:audit", "reason": "no protected hit"},
        contradiction_load=obs(0.1, "contradiction"),
        recursive_integrity=obs(0.85, "recursive-integrity"),
        evidence_refs=["receipt:b", "receipt:a"],
    )
    data.update(overrides)
    return build_radical_scalar_admission(**data)


def test_kaku_packet_is_pre_vector_and_deterministic():
    a = packet()
    b = packet()
    assert validate_kaku_scalar_packet(a)
    assert a["kaku_scalar_commitment"] == b["kaku_scalar_commitment"]
    assert a["operator_classification"] == "OBSERVED_REUSED_PNCS_LEAF"
    assert a["vector_bound"] is False
    assert a["t36_realization_present"] is False
    assert a["semantic_mass_present"] is False
    assert a["execution_admitted"] is False
    assert a["canon_allowed"] is False
    assert a["evidence_refs"] == ["a", "z"]


def test_operator_classes_preserve_current_pncs_status():
    assert packet("condition", "CONDITION")["operator_classification"] == "CONTROL_PLANE_KAKU_CANDIDATE"
    assert packet("negation", "NEGATION")["operator_classification"] == "RECOVERED_PNV_OPERATOR"


def test_unknown_kaku_opcode_is_fail_closed():
    with pytest.raises(GremlinScalarPlaneError, match="outside bounded PNCS/PNV KAKU set"):
        packet(operator_kind="MAGIC_NEW_OPCODE")


def test_tampered_operator_classification_is_rejected():
    p = packet("condition", "CONDITION")
    p["operator_classification"] = "OBSERVED_REUSED_PNCS_LEAF"
    with pytest.raises(GremlinScalarPlaneError, match="classification mismatch"):
        validate_kaku_scalar_packet(p)


def test_nonfinite_scalar_is_rejected():
    with pytest.raises(GremlinScalarPlaneError, match="affect must be finite"):
        build_kaku_scalar_packet(
            kaku_id="k0",
            operator_kind="SOURCE",
            direction="FORWARD",
            polarity=1.0,
            role="SOURCE",
            source_binding="s",
            target_binding="t",
            valuation=obs(0.1, "valuation"),
            affect=obs(float("nan"), "affect"),
            intention_alignment=obs(0.2, "intention"),
            epistemic_support=obs(0.3, "epistemic"),
        )


def test_radical_with_all_hard_gates_passes_pre_vector_admission():
    record = admitted_radical()
    assert validate_radical_scalar_admission(record)
    assert record["status"] == "PRE_VECTOR_ADMITTED"
    assert record["vector_synthesis_allowed"] is True
    assert record["t36_realization_present"] is False
    assert record["semantic_mass_present"] is False
    assert record["execution_admitted"] is False
    assert record["canon_allowed"] is False


@pytest.mark.parametrize(
    "field,status",
    [
        ("consent_gate", "DENIED"),
        ("consent_gate", "UNRESOLVED"),
        ("reversibility_gate", "FAILED"),
        ("reversibility_gate", "UNRESOLVED"),
        ("no_go_gate", "HIT"),
        ("no_go_gate", "UNRESOLVED"),
    ],
)
def test_each_hard_gate_blocks_vector_synthesis(field, status):
    kwargs = {}
    if field == "consent_gate":
        kwargs[field] = {"status": status, "source_ref": "consent:test"}
    elif field == "reversibility_gate":
        kwargs[field] = {"status": status, "source_ref": "reversibility:test"}
    else:
        kwargs[field] = {"status": status, "source_ref": "nogo:test"}
    record = admitted_radical(**kwargs)
    assert validate_radical_scalar_admission(record)
    assert record["status"] == "PRE_VECTOR_BLOCKED"
    assert record["vector_synthesis_allowed"] is False


def test_high_ethics_scalar_cannot_override_denied_consent():
    record = admitted_radical(
        ethical_integrity=obs(1.0e9, "ethics"),
        consent_gate={"status": "DENIED", "source_ref": "consent:denied"},
    )
    assert record["status"] == "PRE_VECTOR_BLOCKED"
    assert record["vector_synthesis_allowed"] is False


def test_affect_and_valuation_do_not_grant_authority():
    p = build_kaku_scalar_packet(
        kaku_id="k-affect",
        operator_kind="TRANSFORM",
        direction="FORWARD",
        polarity=1.0,
        role="MODULATED",
        source_binding="s",
        target_binding="t",
        valuation=obs(1.0e12, "valuation"),
        affect=obs(1.0e12, "affect"),
        intention_alignment=obs(1.0e12, "intention"),
        epistemic_support=obs(1.0e12, "epistemic"),
    )
    assert p["execution_admitted"] is False
    assert p["canon_allowed"] is False
    assert p["vector_bound"] is False


def test_radical_commitment_changes_when_kaku_scalar_changes():
    a = admitted_radical()
    changed_packet = build_kaku_scalar_packet(
        kaku_id="k0",
        operator_kind="SOURCE",
        direction="FORWARD",
        polarity=1.0,
        role="RELATION_SOURCE",
        source_binding="source:k0",
        target_binding="target:k0",
        valuation=obs(0.41, "valuation"),
        affect=obs(-0.2, "affect"),
        intention_alignment=obs(0.8, "intention"),
        epistemic_support=obs(0.9, "epistemic"),
        evidence_refs=["z", "a"],
    )
    b = admitted_radical(
        ordered_kaku_packets=[
            changed_packet,
            packet("k1", "TRANSFORM"),
            packet("k2", "IDENTITY"),
        ]
    )
    assert a["radical_scalar_commitment"] != b["radical_scalar_commitment"]


def test_tampered_radical_status_is_rejected():
    record = admitted_radical()
    record["status"] = "PRE_VECTOR_BLOCKED"
    with pytest.raises(GremlinScalarPlaneError, match="inconsistent with hard gates"):
        validate_radical_scalar_admission(record)


def test_tampered_commitment_is_rejected():
    record = admitted_radical()
    record["radical_scalar_commitment"] = "00" * 32
    with pytest.raises(GremlinScalarPlaneError, match="commitment mismatch"):
        validate_radical_scalar_admission(record)


def test_ordered_kaku_lineage_is_order_sensitive():
    a = admitted_radical()
    b = admitted_radical(
        ordered_kaku_packets=[
            packet("k1", "TRANSFORM"),
            packet("k0", "SOURCE"),
            packet("k2", "IDENTITY"),
        ]
    )
    assert a["radical_scalar_commitment"] != b["radical_scalar_commitment"]
