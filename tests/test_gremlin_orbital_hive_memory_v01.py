from __future__ import annotations

import math

import pytest

from gremlin_mcp.orbital_hive_memory import (
    ClosureGates,
    LOCK_GATES,
    OrbitalHiveMemory,
    SQLiteHiveStore,
    priority_orbit,
    semantic_angle,
)


def test_higher_priority_occupies_inner_orbit() -> None:
    high = priority_orbit(0.95)
    low = priority_orbit(0.10)
    assert high[0] < low[0]
    assert high[1] < low[1]


def test_semantic_address_is_deterministic_and_bounded() -> None:
    a = semantic_angle("tir/einstein/source")
    b = semantic_angle("tir/einstein/source")
    assert a == b
    assert 0.0 <= a < 2.0 * math.pi


def test_latch_fails_closed_until_all_gates_pass() -> None:
    hive = OrbitalHiveMemory()
    hive.place(
        subject_id="claim-A",
        payload={"claim": "A"},
        priority=0.9,
        semantic_key="claim/A",
        relation_phase=7.0,
        provenance=("source:1",),
    )

    with pytest.raises(RuntimeError, match="closure gates incomplete"):
        hive.latch("claim-A")

    for gate in LOCK_GATES:
        hive.update_gates("claim-A", **{gate: True})

    locked = hive.latch("claim-A")
    assert locked.state == "LOCKED"
    assert locked.gates.closed is True
    assert locked.authority == "SHARED_COGNITION_ONLY"
    assert locked.seal_receipt is not None
    assert locked.seal_receipt.startswith("latch:")


def test_dispute_preserves_lineage_and_blocks_latch_and_gate_bypass() -> None:
    hive = OrbitalHiveMemory()
    first = hive.place(
        subject_id="claim-B",
        payload={"claim": "B"},
        priority=0.5,
        semantic_key="claim/B",
        relation_phase=0.25,
        gates=ClosureGates(True, True, True, True, True),
    )
    disputed = hive.dispute("claim-B", "hound:counterexample:1")

    assert disputed.parent_record_id == first.record_id
    assert disputed.state == "DISPUTED"
    assert disputed.gates.contradiction_audited is False
    assert disputed.contradictions == ("hound:counterexample:1",)
    with pytest.raises(RuntimeError, match="cannot latch"):
        hive.latch("claim-B")
    with pytest.raises(RuntimeError, match="cannot be gate-mutated"):
        hive.update_gates("claim-B", contradiction_audited=True)


def test_flat_ring_table_sorts_inner_to_outer() -> None:
    hive = OrbitalHiveMemory()
    hive.place(
        subject_id="outer",
        payload={"v": 1},
        priority=0.1,
        semantic_key="outer",
        relation_phase=0.0,
    )
    hive.place(
        subject_id="inner",
        payload={"v": 2},
        priority=0.95,
        semantic_key="inner",
        relation_phase=0.0,
    )
    table = hive.flat_ring_table()
    assert [record.subject_id for record in table] == ["inner", "outer"]


def test_locked_record_rejects_in_place_gate_mutation() -> None:
    hive = OrbitalHiveMemory()
    hive.place(
        subject_id="sealed",
        payload={"v": "stable"},
        priority=1.0,
        semantic_key="sealed",
        relation_phase=0.0,
        gates=ClosureGates(True, True, True, True, True),
    )
    hive.latch("sealed")
    with pytest.raises(RuntimeError, match="cannot be gate-mutated"):
        hive.update_gates("sealed", evidence_ready=False)


def test_sqlite_store_is_wal_append_only_and_rehydratable(tmp_path) -> None:
    hive = OrbitalHiveMemory()
    first = hive.place(
        subject_id="persisted",
        payload={"v": 1},
        priority=0.75,
        semantic_key="persisted",
        relation_phase=1.5,
    )
    second = hive.update_gates("persisted", evidence_ready=True)

    store = SQLiteHiveStore(tmp_path / "hive.sqlite3")
    try:
        assert str(store._db.execute("PRAGMA journal_mode").fetchone()[0]).lower() == "wal"
        store.append(first)
        store.append(second)
        rows = store.rows("persisted")
        assert len(rows) == 2
        assert rows[0]["record_id"] == first.record_id
        assert rows[1]["parent_record_id"] == first.record_id
        with pytest.raises(Exception):
            store.append(first)

        recovered = OrbitalHiveMemory()
        for row in store.rows():
            recovered.import_record(row)
        assert recovered.head("persisted").record_id == second.record_id
        assert [r.record_id for r in recovered.history("persisted")] == [
            first.record_id,
            second.record_id,
        ]
    finally:
        store.close()


def test_hydration_fails_closed_on_orphan_lineage() -> None:
    hive = OrbitalHiveMemory()
    child = hive.place(
        subject_id="orphan",
        payload={"v": 1},
        priority=0.4,
        semantic_key="orphan",
        relation_phase=0.0,
    )
    row = {
        "record_id": "hive:fake-child",
        "subject_id": child.subject_id,
        "version": 2,
        "payload_hash": child.payload_hash,
        "payload": dict(child.payload),
        "priority": child.priority,
        "coordinate": {
            "orbit_index": child.coordinate.orbit_index,
            "radius": child.coordinate.radius,
            "semantic_angle": child.coordinate.semantic_angle,
            "relation_phase": child.coordinate.relation_phase,
        },
        "semantic_key": child.semantic_key,
        "state": "ALIGNING",
        "gates": {
            "evidence_ready": True,
            "dependencies_closed": False,
            "contradiction_audited": False,
            "provenance_complete": False,
            "phase_coherent": False,
        },
        "provenance": [],
        "dependencies": [],
        "contradictions": [],
        "parent_record_id": "hive:missing-parent",
        "seal_receipt": None,
        "authority": "SHARED_COGNITION_ONLY",
    }
    recovered = OrbitalHiveMemory()
    with pytest.raises(RuntimeError, match="orphan"):
        recovered.import_record(row)
