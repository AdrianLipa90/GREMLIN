from __future__ import annotations

from dataclasses import asdict

import pytest

from gremlin_mcp.orbital_hive_memory import ClosureGates, OrbitalHiveMemory


def test_closure_gates_reject_truthy_non_boolean_values() -> None:
    with pytest.raises((TypeError, ValueError), match="boolean"):
        ClosureGates(evidence_ready="false")  # type: ignore[arg-type]


def test_gate_update_rejects_truthy_non_boolean_values() -> None:
    hive = OrbitalHiveMemory()
    hive.place(
        subject_id="strict-gates",
        payload={"claim": "A"},
        priority=0.5,
        semantic_key="strict/gates",
        relation_phase=0.0,
    )
    before = hive.head("strict-gates")

    with pytest.raises((TypeError, ValueError), match="boolean"):
        hive.update_gates("strict-gates", evidence_ready="false")  # type: ignore[arg-type]

    assert hive.head("strict-gates").record_id == before.record_id
    assert hive.head("strict-gates").gates.evidence_ready is False


def test_hydration_rejects_string_encoded_boolean_gate_without_mutating_state() -> None:
    source = OrbitalHiveMemory()
    record = source.place(
        subject_id="persisted-strict-gates",
        payload={"claim": "B"},
        priority=0.5,
        semantic_key="persisted/strict/gates",
        relation_phase=0.0,
    )
    row = asdict(record)
    row["gates"]["evidence_ready"] = "false"

    recovered = OrbitalHiveMemory()
    with pytest.raises((TypeError, ValueError), match="boolean"):
        recovered.import_record(row)
    with pytest.raises(KeyError):
        recovered.head("persisted-strict-gates")
