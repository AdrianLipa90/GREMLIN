from __future__ import annotations

from dataclasses import asdict
import json
import sqlite3

import pytest

from gremlin_mcp.hive_authority import HiveAuthorityRuntime
from gremlin_mcp.orbital_hive_memory import OrbitalHiveMemory


def test_failed_head_repair_preserves_previous_head_table(tmp_path) -> None:
    path = tmp_path / "hive.sqlite3"
    memory = OrbitalHiveMemory()
    record = memory.place(
        subject_id="atomic-repair",
        payload={"claim": "stable"},
        priority=0.7,
        semantic_key="atomic/repair",
        relation_phase=0.0,
    )

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
            CREATE INDEX hive_subject_idx ON hive_records(subject_id, ordinal);
            CREATE TABLE hive_heads (
                subject_id TEXT PRIMARY KEY,
                record_id TEXT UNIQUE NOT NULL
            );
            """
        )
        db.execute(
            "INSERT INTO hive_records(record_id, subject_id, data_json) VALUES(?,?,?)",
            (
                record.record_id,
                record.subject_id,
                json.dumps(asdict(record), sort_keys=True, separators=(",", ":")),
            ),
        )
        db.execute(
            "INSERT INTO hive_heads(subject_id, record_id) VALUES(?, ?)",
            (record.subject_id, record.record_id),
        )
        db.execute(
            """
            CREATE TRIGGER fail_head_repair
            BEFORE INSERT ON hive_heads
            BEGIN
                SELECT RAISE(ABORT, 'forced head repair failure');
            END;
            """
        )
        db.commit()
    finally:
        db.close()

    with pytest.raises(sqlite3.DatabaseError, match="forced head repair failure"):
        HiveAuthorityRuntime(path)

    verify = sqlite3.connect(path)
    try:
        heads = verify.execute(
            "SELECT subject_id, record_id FROM hive_heads ORDER BY subject_id"
        ).fetchall()
    finally:
        verify.close()

    assert heads == [(record.subject_id, record.record_id)]
