from __future__ import annotations

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
