from __future__ import annotations

import json
import sqlite3

import pytest

from gremlin_mcp.persistent_workers import PersistentWorkerBroker


def test_sqlite_wal_survives_restart_and_preserves_candidate_result(tmp_path) -> None:
    state = tmp_path / "gremlin-worker.sqlite3"

    first = PersistentWorkerBroker(str(state))
    first.register_worker("spider-durable", ["SPIDER"], max_batch=8)
    first.enqueue("SPIDER", {"text": "durable"}, task_id="durable-task")
    lease = first.claim("spider-durable", species="SPIDER", limit=8, lease_seconds=60)
    assert lease["lease_id"]
    first.close()

    second = PersistentWorkerBroker(str(state))
    status = second.queue_status()
    assert status["state_persistence"] == "SQLITE_WAL_V0_3"
    assert status["store"]["journal_mode"] == "WAL"
    assert status["active_leases"] == 1

    receipt = second.submit(
        "spider-durable",
        lease["lease_id"],
        [{"task_id": "durable-task", "output": {"edge": ["a", "b"]}}],
    )
    assert receipt["status"] == "CANDIDATE"
    second.close()

    third = PersistentWorkerBroker(str(state))
    result = third.task_result("durable-task")
    assert result["state"] == "DONE"
    assert result["status"] == "CANDIDATE"
    assert result["result"] == {"edge": ["a", "b"]}
    assert result["result_commitment"]
    assert third.queue_status()["active_leases"] == 0
    third.close()


def test_sqlite_store_fails_closed_when_task_payload_breaks_commitment(tmp_path) -> None:
    state = tmp_path / "gremlin-corrupt.sqlite3"
    broker = PersistentWorkerBroker(str(state))
    broker.enqueue("HOUND", {"claim": 1}, task_id="corrupt-me")
    broker.close()

    connection = sqlite3.connect(str(state))
    connection.execute(
        "UPDATE tasks SET data_json = replace(data_json, '\"claim\":1', '\"claim\":2') "
        "WHERE task_id = 'corrupt-me'"
    )
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeError, match="failed closed"):
        PersistentWorkerBroker(str(state))


def test_sqlite_store_refuses_incompatible_schema_instead_of_overwriting_it(tmp_path) -> None:
    state = tmp_path / "gremlin-old-schema.sqlite3"
    broker = PersistentWorkerBroker(str(state))
    broker.close()

    connection = sqlite3.connect(str(state))
    connection.execute("UPDATE meta SET value = 'GREMLIN_MCP_SQLITE_WAL_V0_2' WHERE key = 'schema'")
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeError, match="incompatible GREMLIN worker store schema"):
        PersistentWorkerBroker(str(state))

    connection = sqlite3.connect(str(state))
    schema = connection.execute("SELECT value FROM meta WHERE key = 'schema'").fetchone()[0]
    connection.close()
    assert schema == "GREMLIN_MCP_SQLITE_WAL_V0_2"


def test_sqlite_store_refuses_persisted_rows_without_schema_metadata(tmp_path) -> None:
    state = tmp_path / "gremlin-missing-schema.sqlite3"
    broker = PersistentWorkerBroker(str(state))
    broker.enqueue("OWL", {"claim": 1}, task_id="orphaned")
    broker.close()

    connection = sqlite3.connect(str(state))
    connection.execute("DELETE FROM meta WHERE key = 'schema'")
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeError, match="without schema metadata"):
        PersistentWorkerBroker(str(state))


def test_persisted_numeric_strings_are_rejected_instead_of_coerced(tmp_path) -> None:
    state = tmp_path / "gremlin-string-int.sqlite3"
    broker = PersistentWorkerBroker(str(state))
    broker.register_worker("strict-worker", ["OWL"], vector_width=8)
    broker.close()

    connection = sqlite3.connect(str(state))
    raw = connection.execute(
        "SELECT data_json FROM workers WHERE worker_id = 'strict-worker'"
    ).fetchone()[0]
    payload = json.loads(raw)
    payload["vector_width"] = "8"
    connection.execute(
        "UPDATE workers SET data_json = ? WHERE worker_id = 'strict-worker'",
        (json.dumps(payload),),
    )
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeError, match="failed closed"):
        PersistentWorkerBroker(str(state))


def test_leased_task_without_matching_lease_is_rejected_on_hydration(tmp_path) -> None:
    state = tmp_path / "gremlin-orphaned-lease.sqlite3"
    broker = PersistentWorkerBroker(str(state))
    broker.register_worker("lease-worker", ["OWL"])
    broker.enqueue("OWL", {"claim": 1}, task_id="leased-task")
    broker.claim("lease-worker", limit=1, lease_seconds=60)
    broker.close()

    connection = sqlite3.connect(str(state))
    connection.execute("DELETE FROM leases")
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeError, match="failed closed"):
        PersistentWorkerBroker(str(state))


def test_server_can_switch_to_durable_state(tmp_path) -> None:
    import gremlin_mcp.server as server

    state = tmp_path / "server-worker.sqlite3"
    persistent = server.configure_state(str(state))
    try:
        queued = persistent.enqueue("OWL", {"assertion": "x"}, task_id="server-durable")
        assert queued["state"] == "QUEUED"
        queue = server.gremlin_worker_queue()
        assert queue["state_persistence"] == "SQLITE_WAL_V0_3"
    finally:
        persistent.close()
        server.configure_state(None)


def test_sqlite_hydration_rebuilds_ephemeral_queue_indexes_and_counters(tmp_path) -> None:
    state = tmp_path / "gremlin-index-rebuild.sqlite3"

    first = PersistentWorkerBroker(str(state))
    first.register_worker("owl-indexed", ["OWL"], max_batch=1)
    first.enqueue("SPIDER", {"x": "queued"}, task_id="persist-spider")
    first.enqueue("OWL", {"x": "leased"}, task_id="persist-owl")
    lease = first.claim(
        "owl-indexed",
        species="OWL",
        limit=1,
        lease_seconds=60,
    )
    before = first.queue_status()
    assert before["unfinished_task_count"] == 2
    assert before["queued_index_counts"]["SPIDER"] == 1
    assert before["queued_index_counts"]["OWL"] == 0
    first.close()

    second = PersistentWorkerBroker(str(state))
    try:
        restored = second.queue_status()
        assert restored["active_leases"] == 1
        assert restored["lease_expiry_heap_indexed"] is True
        assert restored["lease_expiry_heap_entries"] == 1
        assert restored["unfinished_task_count"] == 2
        assert restored["queued_index_counts"]["SPIDER"] == 1
        assert restored["queued_index_counts"]["OWL"] == 0
        assert restored["queue_indexed"] is True

        second.submit(
            "owl-indexed",
            lease["lease_id"],
            [{"task_id": "persist-owl", "output": {"ok": True}}],
        )
        after = second.queue_status()
        assert after["unfinished_task_count"] == 1
        assert after["queued_index_counts"]["SPIDER"] == 1
        assert after["queued_index_counts"]["OWL"] == 0
    finally:
        second.close()


def test_sqlite_hydration_rejects_canonical_context_that_is_structurally_invalid(
    tmp_path,
) -> None:
    from gremlin_mcp.workers import WORKER_SCHEMA, _commit

    state = tmp_path / "gremlin-invalid-context.sqlite3"
    broker = PersistentWorkerBroker(str(state))
    broker.enqueue("SPIDER", {"x": 1}, task_id="context-corrupt")
    broker.close()

    connection = sqlite3.connect(str(state))
    raw = connection.execute(
        "SELECT data_json FROM tasks WHERE task_id = 'context-corrupt'"
    ).fetchone()[0]
    row = json.loads(raw)
    row["payload"]["_gremlin_orchorbital_context_packet"] = {
        "schema": "GREMLIN_ORCHORBITAL_CONTEXT_PACKET_V0_1",
        "target_node_id": "BROKEN",
        "target_frame_commitment": "0" * 64,
        "target_materialized_commitment": "0" * 64,
        "required_base_frame_commitment": None,
        "frames": [],
        "packet_commitment": "0" * 64,
        "materialized_context_bytes": 1,
        "packet_bytes": 1,
    }
    row["task_commitment"] = _commit(
        {
            "schema": WORKER_SCHEMA,
            "task_id": row["task_id"],
            "species": row["species"],
            "payload": row["payload"],
        }
    )
    connection.execute(
        "UPDATE tasks SET data_json = ? WHERE task_id = 'context-corrupt'",
        (json.dumps(row),),
    )
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeError, match="failed closed"):
        PersistentWorkerBroker(str(state))
