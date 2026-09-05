from __future__ import annotations

from dataclasses import asdict
import json
import sqlite3

import pytest

from gremlin_mcp.hive_authority import HiveAuthorityRuntime
from gremlin_mcp.orbital_hive_memory import OrbitalHiveMemory


def test_two_runtimes_share_one_durable_head(tmp_path) -> None:
    path = tmp_path / "hive.sqlite3"
    first = HiveAuthorityRuntime(path)
    second = HiveAuthorityRuntime(path)
    try:
        placed = first.place(
            subject_id="shared",
            payload={"claim": "A"},
            priority=0.9,
            semantic_key="claim/A",
            relation_phase=0.25,
            provenance=("source:1",),
        )
        updated = second.update_gates("shared", evidence_ready=True)
        observed = first.head("shared")
        assert updated.parent_record_id == placed.record_id
        assert observed.record_id == updated.record_id
        assert observed.gates.evidence_ready is True
        assert observed.authority == "SHARED_COGNITION_ONLY"
    finally:
        first.close()
        second.close()


def test_cross_runtime_dispute_blocks_latch(tmp_path) -> None:
    path = tmp_path / "hive.sqlite3"
    first = HiveAuthorityRuntime(path)
    second = HiveAuthorityRuntime(path)
    try:
        first.place(
            subject_id="disputed",
            payload={"claim": "B"},
            priority=0.8,
            semantic_key="claim/B",
            relation_phase=1.0,
        )
        for gate in (
            "evidence_ready",
            "dependencies_closed",
            "contradiction_audited",
            "provenance_complete",
            "phase_coherent",
        ):
            first.update_gates("disputed", **{gate: True})
        second.dispute("disputed", "hound:counterexample")
        with pytest.raises(RuntimeError, match="disputed/quarantined"):
            first.latch("disputed")
    finally:
        first.close()
        second.close()


def test_runtime_repairs_heads_for_v01_append_only_store(tmp_path) -> None:
    path = tmp_path / "legacy.sqlite3"
    hive = OrbitalHiveMemory()
    one = hive.place(
        subject_id="legacy",
        payload={"v": 1},
        priority=0.5,
        semantic_key="legacy",
        relation_phase=0.0,
    )
    two = hive.update_gates("legacy", evidence_ready=True)
    db = sqlite3.connect(path)
    try:
        db.executescript(
            """
            CREATE TABLE hive_records (
                ordinal INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT UNIQUE NOT NULL,
                subject_id TEXT NOT NULL,
                data_json TEXT NOT NULL
            );
            """
        )
        for record in (one, two):
            db.execute(
                "INSERT INTO hive_records(record_id, subject_id, data_json) VALUES(?,?,?)",
                (
                    record.record_id,
                    record.subject_id,
                    json.dumps(asdict(record), sort_keys=True, separators=(",", ":")),
                ),
            )
        db.commit()
    finally:
        db.close()

    runtime = HiveAuthorityRuntime(path)
    try:
        assert runtime.head("legacy").record_id == two.record_id
        assert runtime.status()["persistence"] == "SQLITE_WAL_SINGLE_AUTHORITY"
    finally:
        runtime.close()


def test_persisted_fork_is_rejected_fail_closed(tmp_path) -> None:
    path = tmp_path / "fork.sqlite3"
    base = OrbitalHiveMemory()
    parent = base.place(
        subject_id="forked",
        payload={"v": 1},
        priority=0.5,
        semantic_key="forked",
        relation_phase=0.0,
    )

    left_hive = OrbitalHiveMemory()
    left_hive.import_record(asdict(parent))
    left = left_hive.update_gates("forked", evidence_ready=True)

    right_hive = OrbitalHiveMemory()
    right_hive.import_record(asdict(parent))
    right = right_hive.update_gates("forked", provenance_complete=True)

    db = sqlite3.connect(path)
    try:
        db.executescript(
            """
            CREATE TABLE hive_records (
                ordinal INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT UNIQUE NOT NULL,
                subject_id TEXT NOT NULL,
                data_json TEXT NOT NULL
            );
            """
        )
        for record in (parent, left, right):
            db.execute(
                "INSERT INTO hive_records(record_id, subject_id, data_json) VALUES(?,?,?)",
                (
                    record.record_id,
                    record.subject_id,
                    json.dumps(asdict(record), sort_keys=True, separators=(",", ":")),
                ),
            )
        db.commit()
    finally:
        db.close()

    with pytest.raises(RuntimeError, match="forked persisted hive lineage"):
        HiveAuthorityRuntime(path)


def test_process_resident_runtime_retains_authority_firewall() -> None:
    runtime = HiveAuthorityRuntime()
    record = runtime.place(
        subject_id="local",
        payload={"v": 1},
        priority=1.0,
        semantic_key="local",
        relation_phase=0.0,
    )
    assert record.authority == "SHARED_COGNITION_ONLY"
    status = runtime.status()
    assert status["production_runtime_write"] is False
    assert status["execution_admitted"] is False
    assert status["canon_allowed"] is False
