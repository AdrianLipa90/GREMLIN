import copy

import pytest

from tools.gremlin_kaku_radical_scalar_plane_v01 import build_kaku_scalar_packet, build_radical_scalar_admission
from tools.gremlin_kaku_radical_writer_v01 import build_kaku_record, build_radical_record
from tools.gremlin_operator_record_v01 import (
    GremlinOperatorRecordError,
    build_operator_record,
    render_operator_json,
    validate_operator_record,
    write_immutable_operator_json,
)
from tools.gremlin_phasenav_compiler_v01 import CANDIDATE_SCHEMA
from tools.gremlin_scalar_admitted_phasenav_v02 import compile_scalar_admitted_phasenav_ir_v02


def obs(value, name):
    return {
        "value": value,
        "scale_id": f"{name}/v1",
        "source_ref": f"evidence:{name}",
        "epistemic_status": "OBSERVED_CANDIDATE",
    }


def packet(kid, op):
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
        "candidate_id": "candidate-operator-001",
        "status": "SURVIVED_AUDIT",
        "audit": {"belzebub_result": "SURVIVED"},
        "relations": [
            {"kind": "phase_lock", "a": 0, "b": 1, "gain": 1.0, "source_ref": "rel-lock"},
            {"kind": "torsion", "i": 2, "j": 3, "m": 3, "n": 2, "tau": 0.37, "gain": 1.25, "source_ref": "rel-torsion"},
        ],
    }


def chain(*, consent="GRANTED"):
    packets = [packet("k0", "SOURCE"), packet("k1", "TRANSFORM")]
    radical = build_radical_scalar_admission(
        radical_id="radical-operator-001",
        candidate_id="candidate-operator-001",
        ordered_kaku_packets=packets,
        relation_ids=["rel-lock", "rel-torsion"],
        ethical_integrity=obs(0.8, "ethics"),
        consent_gate={"status": consent, "source_ref": "receipt:consent"},
        reversibility_gate={"status": "SATISFIED", "source_ref": "receipt:reversibility"},
        no_go_gate={"status": "CLEAR", "source_ref": "receipt:nogo"},
        contradiction_load=obs(0.1, "contradiction"),
        recursive_integrity=obs(0.9, "recursive"),
    )
    kaku_records = [build_kaku_record(x) for x in packets]
    radical_record = build_radical_record(radical, kaku_records)
    ir = compile_scalar_admitted_phasenav_ir_v02(candidate(), radical)
    return packets, kaku_records, radical, radical_record, ir


def operator_record():
    _, _, _, radical_record, ir = chain()
    return build_operator_record(radical_record=radical_record, scalar_admitted_ir=ir), radical_record


def test_operator_record_is_deterministic_and_binds_all_parent_commitments():
    a, radical_record = operator_record()
    b, _ = operator_record()
    assert validate_operator_record(a, radical_record)
    assert a == b
    assert a["record_type"] == "OPERATOR"
    assert a["radical_record_id"] == radical_record["record_id"]
    assert a["radical_scalar_commitment"] == radical_record["radical_scalar_commitment"]
    assert a["ordered_kaku_record_ids"] == radical_record["ordered_kaku_record_ids"]
    assert a["operator_kind"] == "KCHI_TORUS_CHARACTER_FIELD"
    assert a["geometry"]["space"] == "T^36"
    assert a["geometry"]["dual_lattice"] == "Z^36"
    assert a["term_count"] == 2


def test_operator_stage_keeps_second_scalar_plane_open():
    record, _ = operator_record()
    assert record["stage"] == "OPERATOR_CANDIDATE_AFTER_PRE_VECTOR_ADMISSION"
    assert record["post_realization_scalars_required"] == [
        "PHASE_COHERENCE_R_K",
        "SEMANTIC_MASS",
        "MASS_AWARE_GRAPH_COST",
        "OPERATOR_STABILITY_BOUND",
    ]
    assert record["post_realization_complete"] is False
    assert record["realization_receipt_bound"] is False
    assert record["production_runtime_write"] is False
    assert record["execution_admitted"] is False
    assert record["canon_allowed"] is False


def test_relation_lineage_mismatch_is_rejected():
    _, _, radical, radical_record, ir = chain()
    changed = copy.deepcopy(ir)
    changed["relation_lineage"] = list(reversed(changed["relation_lineage"]))
    with pytest.raises(Exception):
        build_operator_record(radical_record=radical_record, scalar_admitted_ir=changed)


def test_foreign_radical_record_is_rejected():
    _, _, _, radical_record, ir = chain()
    foreign = copy.deepcopy(radical_record)
    foreign["record_id"] = "00" * 32
    with pytest.raises(Exception):
        build_operator_record(radical_record=foreign, scalar_admitted_ir=ir)


def test_tampered_terms_commitment_is_rejected():
    record, radical_record = operator_record()
    record["terms_commitment"] = "00" * 32
    with pytest.raises(GremlinOperatorRecordError, match="terms commitment mismatch"):
        validate_operator_record(record, radical_record)


def test_tampered_kaku_parent_lineage_is_rejected():
    record, radical_record = operator_record()
    record["ordered_kaku_record_ids"] = list(reversed(record["ordered_kaku_record_ids"]))
    with pytest.raises(GremlinOperatorRecordError, match="KAKU parent lineage mismatch"):
        validate_operator_record(record, radical_record)


def test_operator_json_is_deterministic():
    a, _ = operator_record()
    b, _ = operator_record()
    assert render_operator_json(a) == render_operator_json(b)
    assert render_operator_json(a).endswith(b"\n")


def test_operator_immutable_store_roundtrip_and_idempotence(tmp_path):
    record, _ = operator_record()
    path = tmp_path / "operator.json"
    first = write_immutable_operator_json(path, record)
    second = write_immutable_operator_json(path, record)
    assert first["write_mode"] == "NEW_IMMUTABLE_OBJECT"
    assert second["write_mode"] == "IDEMPOTENT_EXISTING_BYTES"
    assert first["sha256"] == second["sha256"]


def test_operator_immutable_store_rejects_different_bytes(tmp_path):
    record, _ = operator_record()
    path = tmp_path / "operator.json"
    write_immutable_operator_json(path, record)

    _, _, radical, radical_record, _ = chain()
    changed_candidate = candidate()
    changed_candidate["relations"][0]["gain"] = 0.5
    changed_ir = compile_scalar_admitted_phasenav_ir_v02(changed_candidate, radical)
    changed_record = build_operator_record(radical_record=radical_record, scalar_admitted_ir=changed_ir)
    assert changed_record["operator_record_commitment"] != record["operator_record_commitment"]
    with pytest.raises(GremlinOperatorRecordError, match="immutable OPERATOR persistence path collision"):
        write_immutable_operator_json(path, changed_record)


def test_changed_kaku_changes_operator_identity_transitively():
    record_a, _ = operator_record()

    packets = [
        build_kaku_scalar_packet(
            kaku_id="k0",
            operator_kind="SOURCE",
            direction="FORWARD",
            polarity=1.0,
            role="RELATION",
            source_binding="source:k0",
            target_binding="target:k0",
            valuation=obs(0.41, "valuation"),
            affect=obs(0.1, "affect"),
            intention_alignment=obs(0.8, "intention"),
            epistemic_support=obs(0.9, "epistemic"),
        ),
        packet("k1", "TRANSFORM"),
    ]
    radical = build_radical_scalar_admission(
        radical_id="radical-operator-001",
        candidate_id="candidate-operator-001",
        ordered_kaku_packets=packets,
        relation_ids=["rel-lock", "rel-torsion"],
        ethical_integrity=obs(0.8, "ethics"),
        consent_gate={"status": "GRANTED", "source_ref": "receipt:consent"},
        reversibility_gate={"status": "SATISFIED", "source_ref": "receipt:reversibility"},
        no_go_gate={"status": "CLEAR", "source_ref": "receipt:nogo"},
        contradiction_load=obs(0.1, "contradiction"),
        recursive_integrity=obs(0.9, "recursive"),
    )
    kaku_records = [build_kaku_record(x) for x in packets]
    radical_record = build_radical_record(radical, kaku_records)
    ir = compile_scalar_admitted_phasenav_ir_v02(candidate(), radical)
    record_b = build_operator_record(radical_record=radical_record, scalar_admitted_ir=ir)
    assert record_a["operator_record_commitment"] != record_b["operator_record_commitment"]
