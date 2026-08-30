import copy

import pytest

from tools.gremlin_acquisition_bound_phasenav_v03 import (
    GremlinAcquisitionBoundCompileError,
    compile_acquisition_bound_phasenav_ir_v03,
    validate_acquisition_bound_phasenav_ir_v03,
)
from tools.gremlin_phasenav_compiler_v01 import CANDIDATE_SCHEMA
from tools.gremlin_scalar_acquisition_v02 import (
    ScalarAcquisitionError,
    _seal_receipt,
    build_acquired_kaku_scalar_packet,
    build_acquired_radical_scalar_admission,
)
from tools.gremlin_scalar_admitted_phasenav_v02 import GremlinScalarAdmissionCompileError


def receipt(name, value):
    return _seal_receipt(
        observation_name=name,
        value=value,
        scale_id=f"{name}/fixture-v1",
        source_ref=f"noema-live://fixture/{name}#INDEX:0",
        epistemic_status="TEST_FIXTURE_ONLY",
        semantic_adapter_id=f"TEST_FIXTURE/{name}/v0.2",
        semantic_adapter_status="TEST_FIXTURE_ONLY",
        producer={
            "producer_kind": "NOEMA_LIVE_F64",
            "source_path": f"fixture/{name}",
            "source_sha256": "11" * 32,
            "source_size": 8,
            "source_format": "little_endian_float64",
            "extraction": {"reducer": "INDEX", "sample_count": 1, "index": 0},
        },
        live_witness={
            "root": "/dev/shm/ciel_noema",
            "binding_status": "ACTIVE",
            "tether_status": "ACTIVE",
            "phi_sha256": "22" * 32,
            "tether_status_sha256": "33" * 32,
            "tick_sha256": "44" * 32,
            "live_surface_witness": True,
        },
    )


def acquired_kaku(kid, operator):
    return build_acquired_kaku_scalar_packet(
        kaku_id=kid,
        operator_kind=operator,
        direction="FORWARD",
        polarity=1.0,
        role="RELATION",
        source_binding=f"source:{kid}",
        target_binding=f"target:{kid}",
        observation_receipts={
            "valuation": receipt("valuation", 0.4),
            "affect": receipt("affect", 0.1),
            "intention_alignment": receipt("intention_alignment", 0.8),
            "epistemic_support": receipt("epistemic_support", 0.9),
        },
    )


def candidate():
    return {
        "schema": CANDIDATE_SCHEMA,
        "candidate_id": "candidate-acquisition-001",
        "status": "SURVIVED_AUDIT",
        "audit": {"belzebub_result": "SURVIVED"},
        "relations": [
            {
                "kind": "phase_lock",
                "a": 0,
                "b": 1,
                "gain": 1.0,
                "source_ref": "rel-lock",
            },
            {
                "kind": "torsion",
                "i": 2,
                "j": 3,
                "m": 3,
                "n": 2,
                "tau": 0.37,
                "gain": 1.25,
                "source_ref": "rel-torsion",
            },
        ],
    }


def acquired_radical(**overrides):
    data = dict(
        radical_id="radical-acquisition-001",
        candidate_id="candidate-acquisition-001",
        ordered_acquired_kaku_packets=[
            acquired_kaku("k0", "SOURCE"),
            acquired_kaku("k1", "TRANSFORM"),
        ],
        relation_ids=["rel-lock", "rel-torsion"],
        radical_observation_receipts={
            "ethical_integrity": receipt("ethical_integrity", 0.8),
            "contradiction_load": receipt("contradiction_load", 0.05),
            "recursive_integrity": receipt("recursive_integrity", 0.9),
        },
        consent_gate={"status": "GRANTED", "source_ref": "consent:receipt"},
        reversibility_gate={"status": "SATISFIED", "source_ref": "reversibility:receipt"},
        no_go_gate={"status": "CLEAR", "source_ref": "nogo:receipt"},
    )
    data.update(overrides)
    return build_acquired_radical_scalar_admission(**data)


def test_admitted_acquired_radical_reaches_acquisition_bound_phasenav_ir():
    acquired = acquired_radical()
    record = compile_acquisition_bound_phasenav_ir_v03(candidate(), acquired)

    assert validate_acquisition_bound_phasenav_ir_v03(record)
    assert record["acquired_radical_v02"] == acquired
    assert record["acquisition_lineage"]["acquired_radical_commitment"] == acquired["acquired_radical_commitment"]
    assert record["scalar_admitted_phasenav_ir_v02"]["phasenav_ir"]["schema"] == "GREMLIN_PHASENAV_IR_V0_1"
    assert record["post_realization_complete"] is False
    assert record["production_runtime_write"] is False
    assert record["execution_admitted"] is False
    assert record["canon_allowed"] is False


def test_all_kaku_and_radical_observation_receipts_survive_into_lineage():
    acquired = acquired_radical()
    record = compile_acquisition_bound_phasenav_ir_v03(candidate(), acquired)
    lineage = record["acquisition_lineage"]

    expected_radical = {
        name: value["observation_receipt_commitment"]
        for name, value in acquired["radical_observation_receipts"].items()
    }
    assert lineage["radical_observations"] == dict(sorted(expected_radical.items()))

    assert [item["kaku_id"] for item in lineage["ordered_kaku"]] == ["k0", "k1"]
    for source, bound in zip(acquired["ordered_acquired_kaku"], lineage["ordered_kaku"]):
        assert bound["acquired_kaku_commitment"] == source["acquired_kaku_commitment"]
        assert bound["observations"] == {
            name: value["observation_receipt_commitment"]
            for name, value in sorted(source["observation_receipts"].items())
        }


def test_v03_is_deterministic():
    a = compile_acquisition_bound_phasenav_ir_v03(candidate(), acquired_radical())
    b = compile_acquisition_bound_phasenav_ir_v03(candidate(), acquired_radical())
    assert a["acquisition_bound_ir_commitment"] == b["acquisition_bound_ir_commitment"]


def test_tampered_nested_observation_receipt_is_rejected():
    record = compile_acquisition_bound_phasenav_ir_v03(candidate(), acquired_radical())
    record["acquired_radical_v02"]["radical_observation_receipts"]["ethical_integrity"]["value_f64_hex"] = float(0.2).hex()

    with pytest.raises(ScalarAcquisitionError, match="commitment mismatch"):
        validate_acquisition_bound_phasenav_ir_v03(record)


def test_copied_lineage_cannot_diverge_from_full_acquired_envelope():
    record = compile_acquisition_bound_phasenav_ir_v03(candidate(), acquired_radical())
    record["acquisition_lineage"]["ordered_kaku"][0]["observations"]["valuation"] = "aa" * 32

    with pytest.raises(GremlinAcquisitionBoundCompileError, match="lineage differs"):
        validate_acquisition_bound_phasenav_ir_v03(record)


def test_blocked_consent_cannot_reach_v03():
    acquired = acquired_radical(
        consent_gate={"status": "DENIED", "source_ref": "consent:denied"}
    )
    assert acquired["status"] == "ACQUIRED_PRE_VECTOR_BLOCKED"

    with pytest.raises(GremlinAcquisitionBoundCompileError, match="not admitted"):
        compile_acquisition_bound_phasenav_ir_v03(candidate(), acquired)


def test_relation_lineage_mismatch_still_fails_closed():
    acquired = acquired_radical(relation_ids=["rel-lock", "other-relation"])
    with pytest.raises(GremlinScalarAdmissionCompileError, match="lineage differs"):
        compile_acquisition_bound_phasenav_ir_v03(candidate(), acquired)


def test_post_realization_cannot_be_predeclared_complete():
    record = compile_acquisition_bound_phasenav_ir_v03(candidate(), acquired_radical())
    record["post_realization_complete"] = True

    with pytest.raises(GremlinAcquisitionBoundCompileError, match="cannot be predeclared complete"):
        validate_acquisition_bound_phasenav_ir_v03(record)


def test_tampered_outer_commitment_is_rejected():
    record = compile_acquisition_bound_phasenav_ir_v03(candidate(), acquired_radical())
    record["acquisition_bound_ir_commitment"] = "00" * 32

    with pytest.raises(GremlinAcquisitionBoundCompileError, match="commitment mismatch"):
        validate_acquisition_bound_phasenav_ir_v03(record)
