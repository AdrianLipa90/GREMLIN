import copy
import json
import math
import struct
from pathlib import Path

import pytest

from tools.gremlin_scalar_acquisition_v02 import (
    ScalarAcquisitionError,
    _seal_receipt,
    acquire_noema_f64_observation,
    build_acquired_kaku_scalar_packet,
    build_acquired_radical_scalar_admission,
    reduce_f64_le,
    scalar_mapping_from_receipt,
    select_jsonl_f64,
    validate_acquired_kaku_scalar_packet,
    validate_acquired_radical_scalar_admission,
    validate_scalar_observation_receipt,
)


def fixture_receipt(name, value):
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


def kaku_receipts(offset=0.0):
    return {
        "valuation": fixture_receipt("valuation", 0.4 + offset),
        "affect": fixture_receipt("affect", -0.2),
        "intention_alignment": fixture_receipt("intention_alignment", 0.8),
        "epistemic_support": fixture_receipt("epistemic_support", 0.9),
    }


def radical_receipts():
    return {
        "ethical_integrity": fixture_receipt("ethical_integrity", 0.75),
        "contradiction_load": fixture_receipt("contradiction_load", 0.1),
        "recursive_integrity": fixture_receipt("recursive_integrity", 0.85),
    }


def acquired_kaku(kaku_id="k0", operator_kind="SOURCE", offset=0.0):
    return build_acquired_kaku_scalar_packet(
        kaku_id=kaku_id,
        operator_kind=operator_kind,
        direction="FORWARD",
        polarity=1.0,
        role="RELATION_SOURCE",
        source_binding=f"source:{kaku_id}",
        target_binding=f"target:{kaku_id}",
        observation_receipts=kaku_receipts(offset),
        evidence_refs=["candidate:evidence"],
    )


def test_f64_reducers_are_deterministic():
    data = struct.pack("<4d", 0.0, 1.0, 2.0, 3.0)
    value, meta = reduce_f64_le(data, "MEAN")
    assert value == 1.5
    assert meta == {"reducer": "MEAN", "sample_count": 4}

    rms, _ = reduce_f64_le(data, "RMS")
    assert rms == pytest.approx(math.sqrt(3.5))

    indexed, index_meta = reduce_f64_le(data, "INDEX", index=2)
    assert indexed == 2.0
    assert index_meta["index"] == 2


def test_circular_coherence_reducer_preserves_phase_geometry():
    coherent = struct.pack("<4d", 0.0, 0.0, 0.0, 0.0)
    opposed = struct.pack("<4d", 0.0, math.pi, 0.0, math.pi)
    r1, _ = reduce_f64_le(coherent, "CIRCULAR_COHERENCE")
    r2, _ = reduce_f64_le(opposed, "CIRCULAR_COHERENCE")
    assert r1 == pytest.approx(1.0)
    assert r2 == pytest.approx(0.0, abs=1e-15)


def test_jsonl_selector_requires_exactly_one_record():
    data = b'{"name":"A","coherence_R":0.25}\n{"name":"B","coherence_R":0.75}\n'
    value, meta = select_jsonl_f64(
        data,
        selector_key="name",
        selector_value="B",
        field="coherence_R",
    )
    assert value == 0.75
    assert meta["line_number"] == 2
    assert len(meta["record_sha256"]) == 64

    with pytest.raises(ScalarAcquisitionError, match="exactly one"):
        select_jsonl_f64(data, selector_key="name", selector_value="missing", field="coherence_R")


def test_acquisition_cannot_redirect_to_static_or_temp_root(tmp_path):
    with pytest.raises(ScalarAcquisitionError, match="fixed to /dev/shm/ciel_noema"):
        acquire_noema_f64_observation(
            observation_name="x",
            relative_path="phi",
            reducer="MEAN",
            scale_id="x/v1",
            epistemic_status="TEST",
            semantic_adapter_id="TEST/v1",
            root=tmp_path,
        )


def test_committed_live_witness_receipts_validate():
    witness = json.loads(
        Path("provenance/SCALAR_ACQUISITION_LIVE_NOEMA_WITNESS_V0_2.json").read_text()
    )
    assert witness["live_noema_surface_witness"] is True
    assert witness["live_gremlin_producer_claim"] is False
    assert len(witness["observations"]) == 2
    for receipt in witness["observations"]:
        assert validate_scalar_observation_receipt(receipt)
        assert receipt["execution_admitted"] is False
        assert receipt["canon_allowed"] is False


def test_receipt_tamper_is_rejected():
    receipt = fixture_receipt("valuation", 0.4)
    tampered = copy.deepcopy(receipt)
    tampered["value_f64_hex"] = float(0.5).hex()
    with pytest.raises(ScalarAcquisitionError, match="commitment mismatch"):
        validate_scalar_observation_receipt(tampered)


def test_scalar_mapping_preserves_receipt_identity():
    receipt = fixture_receipt("valuation", 0.4)
    mapping = scalar_mapping_from_receipt(receipt)
    assert mapping["value"] == 0.4
    assert mapping["source_ref"] == receipt["source_ref"]
    assert mapping["observation_receipt_commitment"] == receipt["observation_receipt_commitment"]


def test_acquired_kaku_binds_all_four_observation_receipts():
    record = acquired_kaku()
    assert validate_acquired_kaku_scalar_packet(record)
    legacy_refs = set(record["kaku_packet_v01"]["evidence_refs"])
    for receipt in record["observation_receipts"].values():
        assert f"scalar-observation:{receipt['observation_receipt_commitment']}" in legacy_refs
    assert record["kaku_packet_v01"]["vector_bound"] is False
    assert record["execution_admitted"] is False
    assert record["canon_allowed"] is False


def test_acquired_kaku_commitment_changes_with_source_receipt():
    a = acquired_kaku(offset=0.0)
    b = acquired_kaku(offset=0.01)
    assert a["acquired_kaku_commitment"] != b["acquired_kaku_commitment"]
    assert a["kaku_packet_v01"]["kaku_scalar_commitment"] != b["kaku_packet_v01"]["kaku_scalar_commitment"]


def test_acquired_radical_binds_kaku_and_radical_observation_lineage():
    record = build_acquired_radical_scalar_admission(
        radical_id="radical-001",
        candidate_id="candidate-001",
        ordered_acquired_kaku_packets=[
            acquired_kaku("k0", "SOURCE"),
            acquired_kaku("k1", "TRANSFORM"),
        ],
        relation_ids=["r0", "r1"],
        radical_observation_receipts=radical_receipts(),
        consent_gate={"status": "GRANTED", "source_ref": "consent:receipt"},
        reversibility_gate={"status": "SATISFIED", "source_ref": "reversibility:receipt"},
        no_go_gate={"status": "CLEAR", "source_ref": "nogo:receipt"},
    )
    assert validate_acquired_radical_scalar_admission(record)
    assert record["status"] == "ACQUIRED_PRE_VECTOR_ADMITTED"
    assert record["radical_admission_v01"]["status"] == "PRE_VECTOR_ADMITTED"
    refs = set(record["radical_admission_v01"]["evidence_refs"])
    for item in record["ordered_acquired_kaku"]:
        assert f"acquired-kaku:{item['acquired_kaku_commitment']}" in refs
    for receipt in record["radical_observation_receipts"].values():
        assert f"scalar-observation:{receipt['observation_receipt_commitment']}" in refs


def test_denied_consent_stays_blocked_after_acquisition():
    record = build_acquired_radical_scalar_admission(
        radical_id="radical-denied",
        candidate_id="candidate-denied",
        ordered_acquired_kaku_packets=[acquired_kaku()],
        relation_ids=["r0"],
        radical_observation_receipts=radical_receipts(),
        consent_gate={"status": "DENIED", "source_ref": "consent:denied"},
        reversibility_gate={"status": "SATISFIED", "source_ref": "reversibility:receipt"},
        no_go_gate={"status": "CLEAR", "source_ref": "nogo:receipt"},
    )
    assert validate_acquired_radical_scalar_admission(record)
    assert record["status"] == "ACQUIRED_PRE_VECTOR_BLOCKED"
    assert record["radical_admission_v01"]["vector_synthesis_allowed"] is False
