import copy

import pytest

from tools.gremlin_kaku_radical_scalar_plane_v01 import (
    build_kaku_scalar_packet,
    build_radical_scalar_admission,
)
from tools.gremlin_phasenav_compiler_v01 import CANDIDATE_SCHEMA
from tools.gremlin_scalar_admitted_phasenav_v02 import (
    GremlinScalarAdmissionCompileError,
    compile_scalar_admitted_phasenav_ir_v02,
    validate_scalar_admitted_phasenav_ir_v02,
)


def obs(value, name):
    return {
        "value": value,
        "scale_id": f"{name}/v1",
        "source_ref": f"evidence:{name}",
        "epistemic_status": "OBSERVED_CANDIDATE",
    }


def kaku(kid, op):
    return build_kaku_scalar_packet(
        kaku_id=kid,
        operator_kind=op,
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
        "candidate_id": "candidate-scalar-001",
        "status": "SURVIVED_AUDIT",
        "audit": {"belzebub_result": "SURVIVED"},
        "relations": [
            {"kind": "phase_lock", "a": 0, "b": 1, "gain": 1.0, "source_ref": "rel-lock"},
            {"kind": "torsion", "i": 2, "j": 3, "m": 3, "n": 2, "tau": 0.37, "gain": 1.25, "source_ref": "rel-torsion"},
        ],
    }


def admission(**overrides):
    data = dict(
        radical_id="radical-scalar-001",
        candidate_id="candidate-scalar-001",
        ordered_kaku_packets=[kaku("k0", "SOURCE"), kaku("k1", "TRANSFORM")],
        relation_ids=["rel-lock", "rel-torsion"],
        ethical_integrity=obs(0.8, "ethics"),
        consent_gate={"status": "GRANTED", "source_ref": "consent:1"},
        reversibility_gate={"status": "SATISFIED", "source_ref": "reversibility:1"},
        no_go_gate={"status": "CLEAR", "source_ref": "nogo:1"},
        contradiction_load=obs(0.05, "contradiction"),
        recursive_integrity=obs(0.9, "recursive"),
    )
    data.update(overrides)
    return build_radical_scalar_admission(**data)


def test_admitted_radical_allows_phasenav_ir_creation():
    record = compile_scalar_admitted_phasenav_ir_v02(candidate(), admission())
    assert validate_scalar_admitted_phasenav_ir_v02(record)
    assert record["pre_vector_admission"]["status"] == "PRE_VECTOR_ADMITTED"
    assert record["phasenav_ir"]["schema"] == "GREMLIN_PHASENAV_IR_V0_1"
    assert record["post_realization_complete"] is False
    assert record["post_realization_scalars_required"] == [
        "PHASE_COHERENCE_R_K",
        "SEMANTIC_MASS",
        "MASS_AWARE_GRAPH_COST",
        "OPERATOR_STABILITY_BOUND",
    ]
    assert record["execution_admitted"] is False
    assert record["canon_allowed"] is False


@pytest.mark.parametrize(
    "gate,value",
    [
        ("consent_gate", {"status": "DENIED", "source_ref": "consent:deny"}),
        ("reversibility_gate", {"status": "FAILED", "source_ref": "reverse:fail"}),
        ("no_go_gate", {"status": "HIT", "source_ref": "nogo:hit"}),
    ],
)
def test_blocked_radical_cannot_reach_phasenav_compiler(gate, value):
    blocked = admission(**{gate: value})
    with pytest.raises(GremlinScalarAdmissionCompileError, match="not admitted"):
        compile_scalar_admitted_phasenav_ir_v02(candidate(), blocked)


def test_candidate_identity_mismatch_is_rejected():
    a = admission(candidate_id="other-candidate")
    with pytest.raises(GremlinScalarAdmissionCompileError, match="identity mismatch"):
        compile_scalar_admitted_phasenav_ir_v02(candidate(), a)


def test_relation_lineage_mismatch_is_rejected():
    a = admission(relation_ids=["rel-lock", "different-relation"])
    with pytest.raises(GremlinScalarAdmissionCompileError, match="lineage differs"):
        compile_scalar_admitted_phasenav_ir_v02(candidate(), a)


def test_candidate_requires_unique_explicit_relation_refs():
    c = candidate()
    c["relations"][1]["source_ref"] = "rel-lock"
    a = admission(relation_ids=["rel-lock"])
    with pytest.raises(GremlinScalarAdmissionCompileError, match="must be unique"):
        compile_scalar_admitted_phasenav_ir_v02(c, a)


def test_scalar_admitted_ir_is_deterministic():
    a = compile_scalar_admitted_phasenav_ir_v02(candidate(), admission())
    b = compile_scalar_admitted_phasenav_ir_v02(candidate(), admission())
    assert a["scalar_admitted_ir_commitment"] == b["scalar_admitted_ir_commitment"]


def test_tampered_admission_binding_is_rejected():
    record = compile_scalar_admitted_phasenav_ir_v02(candidate(), admission())
    record["pre_vector_admission"]["hard_gates"]["consent"]["status"] = "DENIED"
    with pytest.raises(GremlinScalarAdmissionCompileError, match="consent gate is not admitted"):
        validate_scalar_admitted_phasenav_ir_v02(record)


def test_post_realization_cannot_be_claimed_complete_at_pre_vector_stage():
    record = compile_scalar_admitted_phasenav_ir_v02(candidate(), admission())
    record["post_realization_complete"] = True
    with pytest.raises(GremlinScalarAdmissionCompileError, match="cannot be predeclared complete"):
        validate_scalar_admitted_phasenav_ir_v02(record)
