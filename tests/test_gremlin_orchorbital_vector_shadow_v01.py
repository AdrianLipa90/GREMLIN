from __future__ import annotations

import pytest

import gremlin_mcp.workers as workers_module
from gremlin_mcp.workers import WorkerBroker
from tools.gremlin_geometry_phase_scheduler_v01 import (
    NUMPY_DISTANCE_KERNEL_CANDIDATE,
    SCHEDULER_KEY,
)


def payload(index: int) -> dict[str, object]:
    return {
        "index": index,
        SCHEDULER_KEY: {
            "phase36": [
                (0.03 * index + 0.002 * axis) % (2.0 * 3.141592653589793)
                for axis in range(36)
            ],
            "ready": True,
            "readiness": 1.0,
            "temperature": (index % 7) / 6.0,
            "urgency": (index % 5) / 4.0,
            "noise": (index % 3) / 10.0,
        },
    }


def test_worker_broker_vector_shadow_matches_scalar_without_changing_decision() -> None:
    broker = WorkerBroker(vector_distance_shadow=True)
    broker.register_worker(
        "shadow-worker",
        ["SPIDER"],
        vector_width=8,
        max_batch=16,
    )
    for index in range(24):
        broker.enqueue(
            "SPIDER",
            payload(index),
            task_id=f"shadow-{index:03d}",
        )

    lease = broker.claim(
        "shadow-worker",
        species="SPIDER",
        limit=8,
    )
    shadow = lease["scheduler"]["batch_selection"]["vector_distance_shadow"]

    assert shadow["enabled"] is True
    assert shadow["decision_kernel"] == "SCALAR_EXACT_V0_1"
    assert shadow["candidate_kernel"] == NUMPY_DISTANCE_KERNEL_CANDIDATE
    assert shadow["selection_equivalent"] is True
    assert shadow["candidate_selected_task_ids"] == [
        row["task_id"] for row in lease["tasks"]
    ]
    assert broker.queue_status()["vector_distance_shadow_enabled"] is True


def test_vector_shadow_mismatch_fails_before_any_lease_mutation(monkeypatch) -> None:
    broker = WorkerBroker(vector_distance_shadow=True)
    broker.register_worker(
        "shadow-worker",
        ["SPIDER"],
        vector_width=4,
        max_batch=4,
    )
    for index in range(6):
        broker.enqueue(
            "SPIDER",
            payload(index),
            task_id=f"mismatch-{index:03d}",
        )

    original = workers_module.select_batch

    def divergent(*args, **kwargs):
        selected, receipt = original(*args, **kwargs)
        if kwargs.get("distance_kernel") == NUMPY_DISTANCE_KERNEL_CANDIDATE:
            selected = list(reversed(selected))
        return selected, receipt

    monkeypatch.setattr(workers_module, "select_batch", divergent)

    with pytest.raises(
        RuntimeError,
        match="scalar/vector scheduler shadow selection mismatch",
    ):
        broker.claim(
            "shadow-worker",
            species="SPIDER",
            limit=3,
        )

    status = broker.queue_status()
    assert status["active_leases"] == 0
    assert status["unfinished_task_count"] == 6
    assert status["tasks"]["SPIDER"]["QUEUED"] == 6
    assert status["tasks"]["SPIDER"]["LEASED"] == 0


def test_vector_shadow_is_disabled_by_default() -> None:
    broker = WorkerBroker()
    broker.register_worker("default-worker", ["SPIDER"])
    broker.enqueue("SPIDER", payload(1), task_id="default-one")

    lease = broker.claim(
        "default-worker",
        species="SPIDER",
        limit=1,
    )
    shadow = lease["scheduler"]["batch_selection"]["vector_distance_shadow"]

    assert shadow["enabled"] is False
    assert shadow["selection_equivalent"] is None
    assert broker.queue_status()["vector_distance_shadow_enabled"] is False
