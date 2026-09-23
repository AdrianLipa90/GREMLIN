from __future__ import annotations

import asyncio

import pytest

from gremlin_mcp.workers import WORKER_ABI_VERSION, WORKER_SCHEMA, WorkerBroker
from tools.gremlin_bestiary_vector_species_v03 import lane_width


def test_worker_register_claim_submit_roundtrip_is_candidate_only() -> None:
    broker = WorkerBroker()
    worker = broker.register_worker(
        "spider-test",
        ["SPIDER"],
        capabilities=["relations", "isomorphisms"],
        vector_width=8,
        max_batch=16,
    )
    assert worker["schema"] == WORKER_SCHEMA
    assert worker["species"] == ("SPIDER",)
    assert worker["authority"]["canon_allowed"] is False

    first = broker.enqueue("SPIDER", {"text": "alpha"}, task_id="task-a")
    second = broker.enqueue("SPIDER", {"text": "beta"}, task_id="task-b")
    assert first["state"] == "QUEUED"
    assert second["state"] == "QUEUED"

    lease = broker.claim("spider-test", species="SPIDER", limit=16)
    assert lease["species"] == "SPIDER"
    assert lease["batch_size"] == 2
    assert lease["batch_size"] <= lane_width("SPIDER", vector_width=8)
    claimed_ids = [task["task_id"] for task in lease["tasks"]]
    assert set(claimed_ids) == {"task-a", "task-b"}
    assert lease["scheduler"]["mode"] == "GEOMETRY_PHASE_STATE_CLUSTERED_V0_1"
    assert lease["scheduler"]["fifo_primary"] is False

    receipt = broker.submit(
        "spider-test",
        lease["lease_id"],
        [
            {"task_id": "task-a", "status": "CANDIDATE", "output": {"edges": [["a", "b"]]}},
            {"task_id": "task-b", "output": {"edges": [["b", "c"]]}},
        ],
    )
    assert receipt["status"] == "CANDIDATE"
    assert receipt["authority"] == {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
    result = broker.task_result("task-a")
    assert result["state"] == "DONE"
    assert result["status"] == "CANDIDATE"
    assert result["result"] == {"edges": [["a", "b"]]}
    assert result["result_commitment"]


def test_worker_claim_is_lane_bounded() -> None:
    broker = WorkerBroker()
    broker.register_worker("mole-test", ["MOLE"], vector_width=8, max_batch=128)
    for i in range(100):
        broker.enqueue("MOLE", {"n": i}, task_id=f"mole-{i:03d}")
    lease = broker.claim("mole-test", limit=128)
    assert 1 <= lease["batch_size"] <= lane_width("MOLE", vector_width=8)
    assert len(lease["tasks"]) == lease["batch_size"]
    assert lease["scheduler"]["mode"] == "GEOMETRY_PHASE_STATE_CLUSTERED_V0_1"


def test_worker_submission_fails_closed_on_wrong_worker_or_partial_batch() -> None:
    broker = WorkerBroker()
    broker.register_worker("owl-a", ["OWL"])
    broker.register_worker("owl-b", ["OWL"])
    broker.enqueue("OWL", {"claim": 1}, task_id="owl-1")
    broker.enqueue("OWL", {"claim": 2}, task_id="owl-2")
    lease = broker.claim("owl-a", species="OWL", limit=2)

    with pytest.raises(ValueError, match="another worker"):
        broker.submit(
            "owl-b",
            lease["lease_id"],
            [
                {"task_id": "owl-1", "output": {}},
                {"task_id": "owl-2", "output": {}},
            ],
        )

    with pytest.raises(ValueError, match="exact claimed task set"):
        broker.submit(
            "owl-a",
            lease["lease_id"],
            [{"task_id": "owl-1", "output": {}}],
        )

    with pytest.raises(ValueError, match="must remain CANDIDATE"):
        broker.submit(
            "owl-a",
            lease["lease_id"],
            [
                {"task_id": "owl-1", "status": "CANON", "output": {}},
                {"task_id": "owl-2", "output": {}},
            ],
        )


def test_task_id_is_idempotent_only_for_identical_content() -> None:
    broker = WorkerBroker()
    a = broker.enqueue("HOUND", {"x": 1}, task_id="same")
    b = broker.enqueue("HOUND", {"x": 1}, task_id="same")
    assert a["task_commitment"] == b["task_commitment"]
    with pytest.raises(ValueError, match="different content"):
        broker.enqueue("HOUND", {"x": 2}, task_id="same")


def test_worker_abi_rejects_type_coercions() -> None:
    with pytest.raises(ValueError, match="lease_seconds must be an integer"):
        WorkerBroker(lease_seconds="30")  # type: ignore[arg-type]

    broker = WorkerBroker()
    with pytest.raises(ValueError, match="worker_id must be a string"):
        broker.register_worker(123, ["OWL"])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="species must be an iterable"):
        broker.register_worker("worker", "OWL")
    with pytest.raises(ValueError, match="vector_width must be an integer"):
        broker.register_worker("worker", ["OWL"], vector_width=8.0)  # type: ignore[arg-type]

    broker.register_worker("worker", ["OWL"])
    broker.enqueue("OWL", {"x": 1}, task_id="strict-task")
    with pytest.raises(ValueError, match="limit must be an integer"):
        broker.claim("worker", limit=1.9)  # type: ignore[arg-type]


def test_worker_submit_rejects_numeric_task_id_instead_of_stringifying() -> None:
    broker = WorkerBroker()
    broker.register_worker("owl", ["OWL"])
    broker.enqueue("OWL", {"x": 1}, task_id="1")
    lease = broker.claim("owl", limit=1)
    with pytest.raises(ValueError, match="task_id must be a string"):
        broker.submit("owl", lease["lease_id"], [{"task_id": 1, "output": {}}])


def test_expired_lease_lineage_corruption_is_not_silently_skipped() -> None:
    broker = WorkerBroker()
    broker.register_worker("owl", ["OWL"])
    broker.enqueue("OWL", {"x": 1}, task_id="lease-task")
    lease = broker.claim("owl", limit=1, lease_seconds=1)
    broker._tasks["lease-task"].lease_id = "wrong-lineage"
    with pytest.raises(RuntimeError, match="lineage is inconsistent"):
        broker._reap_expired(lease["expires_ns"] + 1)
    assert lease["lease_id"] in broker._leases


def test_mcp_discovery_contains_worker_abi_tools() -> None:
    from mcp import Client
    from gremlin_mcp.server import mcp

    async def exercise() -> None:
        async with Client(mcp) as client:
            listed = await client.list_tools()
            names = {tool.name for tool in listed.tools}
            assert {
                "gremlin_worker_register",
                "gremlin_worker_heartbeat",
                "gremlin_worker_list",
                "gremlin_worker_enqueue",
                "gremlin_worker_claim",
                "gremlin_worker_submit",
                "gremlin_worker_result",
                "gremlin_worker_queue",
            } <= names

            reg = await client.call_tool(
                "gremlin_worker_register",
                {
                    "worker_id": "mcp-raven",
                    "species": ["RAVEN"],
                    "capabilities": ["memory"],
                    "vector_width": 8,
                    "max_batch": 8,
                },
            )
            assert reg.is_error is False
            queued = await client.call_tool(
                "gremlin_worker_enqueue",
                {"species": "RAVEN", "payload": {"query": "prior structure"}, "task_id": "mcp-task"},
            )
            assert queued.is_error is False
            claimed = await client.call_tool(
                "gremlin_worker_claim",
                {"worker_id": "mcp-raven", "species": "RAVEN", "limit": 8},
            )
            assert claimed.is_error is False

    asyncio.run(exercise())


def test_claim_uses_species_queue_index_instead_of_global_task_scan(monkeypatch) -> None:
    broker = WorkerBroker()
    broker.register_worker(
        "indexed-spider",
        ["SPIDER"],
        vector_width=8,
        max_batch=8,
    )
    for index in range(3):
        broker.enqueue(
            "SPIDER",
            {"kind": "target", "index": index},
            task_id=f"indexed-spider-{index}",
        )
    for index in range(200):
        broker.enqueue(
            "OWL",
            {"kind": "unrelated", "index": index},
            task_id=f"indexed-owl-{index:03d}",
        )

    seen_species: list[str] = []
    original = broker._scheduler_task_view

    def counted(record):
        seen_species.append(record.species)
        return original(record)

    monkeypatch.setattr(broker, "_scheduler_task_view", counted)
    lease = broker.claim("indexed-spider", species="SPIDER", limit=3)

    assert lease["batch_size"] == 3
    assert seen_species == ["SPIDER", "SPIDER", "SPIDER"]
    status = broker.queue_status()
    assert status["queue_indexed"] is True
    assert status["queued_index_counts"]["OWL"] == 200
    assert status["queued_index_counts"]["SPIDER"] == 0
    assert status["unfinished_task_count"] == 203


def test_queue_index_and_unfinished_counter_follow_lease_submit_and_reap() -> None:
    broker = WorkerBroker()
    broker.register_worker("indexed-owl", ["OWL"], vector_width=1, max_batch=1)
    broker.enqueue("OWL", {"x": 1}, task_id="idx-a")
    broker.enqueue("OWL", {"x": 2}, task_id="idx-b")

    initial = broker.queue_status()
    assert initial["queued_index_counts"]["OWL"] == 2
    assert initial["unfinished_task_count"] == 2

    first = broker.claim(
        "indexed-owl",
        species="OWL",
        limit=1,
        lease_seconds=60,
    )
    leased = broker.queue_status()
    assert leased["queued_index_counts"]["OWL"] == 1
    assert leased["unfinished_task_count"] == 2

    broker.submit(
        "indexed-owl",
        first["lease_id"],
        [{"task_id": first["tasks"][0]["task_id"], "output": {"ok": 1}}],
    )
    after_submit = broker.queue_status()
    assert after_submit["queued_index_counts"]["OWL"] == 1
    assert after_submit["unfinished_task_count"] == 1

    second = broker.claim(
        "indexed-owl",
        species="OWL",
        limit=1,
        lease_seconds=1,
    )
    assert broker.queue_status()["queued_index_counts"]["OWL"] == 0

    broker._reap_expired(second["expires_ns"] + 1)
    after_reap = broker.queue_status()
    assert after_reap["queued_index_counts"]["OWL"] == 1
    assert after_reap["unfinished_task_count"] == 1


def test_idempotent_enqueue_does_not_double_count_queue_index() -> None:
    broker = WorkerBroker()
    first = broker.enqueue("HOUND", {"x": 1}, task_id="index-idempotent")
    replay = broker.enqueue("HOUND", {"x": 1}, task_id="index-idempotent")

    assert replay["task_commitment"] == first["task_commitment"]
    status = broker.queue_status()
    assert status["queued_index_counts"]["HOUND"] == 1
    assert status["unfinished_task_count"] == 1


def test_lease_expiry_heap_reaps_only_due_lease_and_preserves_later_lease() -> None:
    broker = WorkerBroker()
    broker.register_worker("heap-owl", ["OWL"], vector_width=1, max_batch=1)
    broker.enqueue("OWL", {"x": 1}, task_id="heap-a")
    broker.enqueue("OWL", {"x": 2}, task_id="heap-b")

    first = broker.claim(
        "heap-owl",
        species="OWL",
        limit=1,
        lease_seconds=1,
    )
    second = broker.claim(
        "heap-owl",
        species="OWL",
        limit=1,
        lease_seconds=60,
    )

    assert broker.queue_status()["active_leases"] == 2
    assert broker.queue_status()["lease_expiry_heap_indexed"] is True

    broker._reap_expired(first["expires_ns"] + 1)

    assert first["lease_id"] not in broker._leases
    assert second["lease_id"] in broker._leases
    assert broker._tasks[first["tasks"][0]["task_id"]].state == "QUEUED"
    assert broker._tasks[second["tasks"][0]["task_id"]].state == "LEASED"


def test_submitted_lease_heap_entry_is_safe_stale_and_does_not_requeue_done_task() -> None:
    broker = WorkerBroker()
    broker.register_worker("heap-submit", ["OWL"], vector_width=1, max_batch=1)
    broker.enqueue("OWL", {"x": 1}, task_id="heap-submit-task")
    lease = broker.claim(
        "heap-submit",
        species="OWL",
        limit=1,
        lease_seconds=1,
    )
    task_id = lease["tasks"][0]["task_id"]

    broker.submit(
        "heap-submit",
        lease["lease_id"],
        [{"task_id": task_id, "output": {"done": True}}],
    )
    broker._reap_expired(lease["expires_ns"] + 1)

    assert broker._tasks[task_id].state == "DONE"
    assert task_id not in broker._queued_by_species["OWL"]
    assert broker.queue_status()["unfinished_task_count"] == 0


def test_lease_expiry_heap_compacts_stale_entries_under_repeated_short_leases() -> None:
    broker = WorkerBroker()
    broker.register_worker("heap-compact", ["OWL"], vector_width=1, max_batch=1)

    for index in range(100):
        task_id = f"heap-cycle-{index:03d}"
        broker.enqueue("OWL", {"index": index}, task_id=task_id)
        lease = broker.claim(
            "heap-compact",
            species="OWL",
            limit=1,
            lease_seconds=60,
        )
        broker.submit(
            "heap-compact",
            lease["lease_id"],
            [{"task_id": task_id, "output": {"ok": index}}],
        )

    status = broker.queue_status()

    assert status["active_leases"] == 0
    assert status["unfinished_task_count"] == 0
    assert status["lease_expiry_heap_entries"] <= 64


def test_worker_claim_reuses_precomputed_phase_state_after_enqueue_and_reap(
    monkeypatch,
) -> None:
    import tools.gremlin_geometry_phase_scheduler_v01 as scheduler

    broker = WorkerBroker()
    broker.register_worker(
        "phase-cache-worker",
        ["OWL"],
        vector_width=1,
        max_batch=1,
    )
    broker.enqueue(
        "OWL",
        {
            "text": "cached-phase",
            "_gremlin_scheduler": {
                "phase36": [0.25] * 36,
                "ready": True,
                "urgency": 0.5,
            },
        },
        task_id="phase-cache-task",
    )
    assert broker.queue_status()["precomputed_phase_state_count"] == 1

    def forbidden_reparse(row):
        raise AssertionError("claim must not reparse immutable task phase state")

    monkeypatch.setattr(scheduler, "_task_state", forbidden_reparse)

    first = broker.claim(
        "phase-cache-worker",
        species="OWL",
        limit=1,
        lease_seconds=1,
    )
    assert first["scheduler"]["batch_selection"][
        "precomputed_state_cache_used"
    ] is True

    broker._reap_expired(first["expires_ns"] + 1)

    second = broker.claim(
        "phase-cache-worker",
        species="OWL",
        limit=1,
        lease_seconds=60,
    )
    assert second["tasks"][0]["task_id"] == "phase-cache-task"
    assert second["scheduler"]["batch_selection"][
        "precomputed_state_cache_used"
    ] is True


def test_worker_abi_version_includes_indexed_routing_contract() -> None:
    assert WORKER_ABI_VERSION == "0.2.5"
