import copy

import pytest

from tools.gremlin_kaku_radical_scalar_plane_v01 import (
    build_kaku_scalar_packet,
    build_radical_scalar_admission,
)
from tools.gremlin_kaku_radical_store_v01 import write_immutable_bundle_jsonl
from tools.gremlin_kaku_radical_writer_v01 import (
    GremlinKakuRadicalWriterError,
    build_kaku_record,
    build_persistence_bundle,
    build_radical_record,
    read_bundle_jsonl,
    render_bundle_jsonl,
    validate_kaku_record,
    validate_persistence_bundle,
    validate_radical_record,
)


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


def radical_payload(packets=None, *, consent="GRANTED"):
    packets = packets or [packet("k0", "SOURCE"), packet("k1", "TRANSFORM"), packet("k2", "IDENTITY")]
    return build_radical_scalar_admission(
        radical_id="radical-write-001",
        candidate_id="candidate-write-001",
        ordered_kaku_packets=packets,
        relation_ids=["r0", "r1"],
        ethical_integrity=obs(0.8, "ethics"),
        consent_gate={"status": consent, "source_ref": "receipt:consent"},
        reversibility_gate={"status": "SATISFIED", "source_ref": "receipt:reversibility"},
        no_go_gate={"status": "CLEAR", "source_ref": "receipt:nogo"},
        contradiction_load=obs(0.1, "contradiction"),
        recursive_integrity=obs(0.9, "recursive"),
    )


def records(*, consent="GRANTED"):
    packets = [packet("k0", "SOURCE"), packet("k1", "TRANSFORM"), packet("k2", "IDENTITY")]
    kaku_records = [build_kaku_record(x) for x in packets]
    radical = build_radical_record(radical_payload(packets, consent=consent), kaku_records)
    return kaku_records, radical


def persistence_bundle(*, consent="GRANTED"):
    kaku_records, radical = records(consent=consent)
    return build_persistence_bundle(kaku_records, radical)


def test_kaku_records_are_deterministic_content_addressed_objects():
    a = build_kaku_record(packet("k0", "SOURCE"))
    b = build_kaku_record(packet("k0", "SOURCE"))
    assert validate_kaku_record(a)
    assert a == b
    assert a["record_type"] == "KAKU"
    assert a["storage_role"] == "CONTENT_ADDRESSED_PERSISTENCE_OBJECT"
    assert a["execution_admitted"] is False
    assert a["canon_allowed"] is False


def test_changed_kaku_scalar_changes_record_id():
    a = build_kaku_record(packet("k0", "SOURCE"))
    changed = build_kaku_scalar_packet(
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
    )
    b = build_kaku_record(changed)
    assert a["record_id"] != b["record_id"]


def test_radical_record_binds_exact_ordered_kaku_records():
    kaku_records, radical = records()
    assert validate_radical_record(radical, kaku_records)
    assert radical["ordered_kaku_record_ids"] == [x["record_id"] for x in kaku_records]
    assert radical["ordered_kaku_ids"] == ["k0", "k1", "k2"]


def test_reordered_kaku_records_fail_radical_writer():
    packets = [packet("k0", "SOURCE"), packet("k1", "TRANSFORM"), packet("k2", "IDENTITY")]
    radical = radical_payload(packets)
    recs = [build_kaku_record(x) for x in packets]
    with pytest.raises(GremlinKakuRadicalWriterError, match="ordered KAKU persistence lineage differs"):
        build_radical_record(radical, [recs[1], recs[0], recs[2]])


def test_missing_or_foreign_kaku_record_fails_radical_writer():
    packets = [packet("k0", "SOURCE"), packet("k1", "TRANSFORM")]
    radical = radical_payload(packets)
    recs = [build_kaku_record(x) for x in packets]
    foreign = build_kaku_record(packet("foreign", "IDENTITY"))
    with pytest.raises(GremlinKakuRadicalWriterError, match="lineage differs"):
        build_radical_record(radical, [recs[0], foreign])


def test_radical_record_preserves_blocked_pre_vector_status():
    kaku_records, radical = records(consent="DENIED")
    assert validate_radical_record(radical, kaku_records)
    assert radical["pre_vector_status"] == "PRE_VECTOR_BLOCKED"
    assert radical["vector_synthesis_allowed"] is False


def test_persistence_bundle_is_deterministic_and_ordered():
    a = persistence_bundle()
    b = persistence_bundle()
    assert validate_persistence_bundle(a)
    assert a == b
    assert a["record_order"] == "ORDERED_KAKU_THEN_RADICAL"
    assert a["kaku_count"] == 3
    assert a["radical_count"] == 1
    assert [x["record_type"] for x in a["records"]] == ["KAKU", "KAKU", "KAKU", "RADICAL"]


def test_jsonl_bytes_are_deterministic_and_newline_terminated():
    a = render_bundle_jsonl(persistence_bundle())
    b = render_bundle_jsonl(persistence_bundle())
    assert a == b
    assert a.endswith(b"\n")
    assert len(a.splitlines()) == 5


def test_immutable_store_roundtrip(tmp_path):
    bundle = persistence_bundle()
    path = tmp_path / "radical.pnv.jsonl"
    receipt = write_immutable_bundle_jsonl(path, bundle)
    assert receipt["status"] == "IMMUTABLE_STORE_CONFIRMED"
    assert receipt["write_mode"] == "NEW_IMMUTABLE_OBJECT"
    restored = read_bundle_jsonl(path)
    assert restored == bundle


def test_second_identical_write_is_idempotent(tmp_path):
    bundle = persistence_bundle()
    path = tmp_path / "radical.pnv.jsonl"
    first = write_immutable_bundle_jsonl(path, bundle)
    second = write_immutable_bundle_jsonl(path, bundle)
    assert first["sha256"] == second["sha256"]
    assert second["write_mode"] == "IDEMPOTENT_EXISTING_BYTES"


def test_immutable_store_rejects_path_collision(tmp_path):
    path = tmp_path / "radical.pnv.jsonl"
    write_immutable_bundle_jsonl(path, persistence_bundle(consent="GRANTED"))
    with pytest.raises(GremlinKakuRadicalWriterError, match="immutable persistence path collision"):
        write_immutable_bundle_jsonl(path, persistence_bundle(consent="DENIED"))


def test_tampered_kaku_payload_is_detected():
    record = build_kaku_record(packet("k0", "SOURCE"))
    record["payload"]["direction"] = "BACKWARD"
    with pytest.raises(Exception):
        validate_kaku_record(record)


def test_tampered_radical_payload_is_detected():
    kaku_records, radical = records()
    radical["payload"]["status"] = "PRE_VECTOR_BLOCKED"
    with pytest.raises(Exception):
        validate_radical_record(radical, kaku_records)


def test_tampered_bundle_record_order_is_detected():
    bundle = persistence_bundle()
    bundle["record_ids"][0], bundle["record_ids"][1] = bundle["record_ids"][1], bundle["record_ids"][0]
    with pytest.raises(GremlinKakuRadicalWriterError, match="record order mismatch"):
        validate_persistence_bundle(bundle)
