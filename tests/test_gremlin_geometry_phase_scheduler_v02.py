from __future__ import annotations

import pytest

from gremlin_mcp.workers import WorkerBroker
from tools.gremlin_bestiary_phasenav_phase_gates_v02 import role_phase_carrier
from tools.gremlin_geometry_phase_scheduler_v02 import (
    MODE,
    SCHEDULER_KEY,
    GeometryPhaseSchedulerError,
    choose_species,
    derived_phase36,
    geometry_lane_width,
    queue_metrics,
    scheduler_manifest,
    select_batch,
    task_phase_state,
)


def _payload(species: str) -> dict:
    return {
        "text": f"{species} explicit ARPL carrier",
        SCHEDULER_KEY: {
            "phase36": list(role_phase_carrier(species)),
            "ready": True,
            "noise": 0.0,
            "urgency": 0.5,
            "temperature": 0.2,
        },
    }


def test_v02_manifest_arms_all_dynamic_roles() -> None:
    manifest = scheduler_manifest()
    assert manifest["mode"] == MODE == "GEOMETRY_PHASE_STATE_CLUSTERED_V0_2"
    assert manifest["anchor_neutral_dynamic_species"] == []
    assert {"ELEPHANT", "BEES"} <= set(
        manifest["validated_phasenav_carrier_species"]
    )


def test_elephant_and_bees_use_explicit_non_neutral_role_anchors() -> None:
    for species in ("ELEPHANT", "BEES"):
        broker = WorkerBroker()
        broker.register_worker(
            f"{species.lower()}-v02",
            [species],
            vector_width=4,
            max_batch=4,
        )
        broker.enqueue(
            species,
            _payload(species),
            task_id=f"{species.lower()}-v02-task",
        )
        lease = broker.claim(
            f"{species.lower()}-v02",
            species=species,
            limit=1,
        )
        queue = lease["scheduler"]["species_selection"]["queues"][species]
        assert lease["scheduler"]["mode"] == MODE
        assert queue["explicit_phase_fraction"] == 1.0
        assert queue["effective_queue_score"] > 0.0


def test_v02_scheduler_rejects_phase_numeric_coercion() -> None:
    row = {
        "task_id": "phase-string",
        "species": "SPIDER",
        "payload": {SCHEDULER_KEY: {"phase36": ["0.0"] * 36}},
        "task_commitment": "a" * 64,
        "created_ns": 1,
    }
    with pytest.raises(GeometryPhaseSchedulerError, match="phase36 values must be real numbers"):
        task_phase_state(row)

    row["payload"] = {SCHEDULER_KEY: {"phase36": [False] * 36}}
    with pytest.raises(GeometryPhaseSchedulerError, match="phase36 values must be real numbers"):
        task_phase_state(row)


def test_v02_scheduler_rejects_nonstring_payload_keys() -> None:
    with pytest.raises(GeometryPhaseSchedulerError, match="payload keys must be strings"):
        derived_phase36({1: "alpha", "1": "beta"})  # type: ignore[dict-item]


def test_v02_scheduler_rejects_noncanonical_task_commitment() -> None:
    row = {
        "task_id": "bad-commitment",
        "species": "SPIDER",
        "payload": {},
        "task_commitment": "not-a-commitment",
        "created_ns": 1,
    }
    with pytest.raises(
        GeometryPhaseSchedulerError,
        match="lowercase 64-hex task_commitment",
    ):
        task_phase_state(row)

    row["task_commitment"] = "A" * 64
    with pytest.raises(
        GeometryPhaseSchedulerError,
        match="lowercase 64-hex task_commitment",
    ):
        task_phase_state(row)


def _row(
    task_id: str = "task-v02",
    *,
    ready: bool = True,
    commitment: str = "a" * 64,
) -> dict:
    return {
        "task_id": task_id,
        "species": "SPIDER",
        "payload": {SCHEDULER_KEY: {"ready": ready}},
        "task_commitment": commitment,
        "created_ns": 1,
    }


def test_v02_scheduler_rejects_noncanonical_task_id() -> None:
    with pytest.raises(GeometryPhaseSchedulerError, match="canonical non-empty task_id"):
        task_phase_state(_row("   "))
    with pytest.raises(GeometryPhaseSchedulerError, match="canonical non-empty task_id"):
        task_phase_state(_row(" task-v02 "))


def test_v02_scheduler_rejects_invalid_clock_even_on_early_return() -> None:
    not_ready = _row(ready=False)
    with pytest.raises(GeometryPhaseSchedulerError, match="now_ns must be a non-negative integer"):
        queue_metrics([not_ready], now_ns=-1)
    with pytest.raises(GeometryPhaseSchedulerError, match="now_ns must be a non-negative integer"):
        choose_species({}, now_ns=True)
    with pytest.raises(GeometryPhaseSchedulerError, match="now_ns must be a non-negative integer"):
        select_batch([not_ready], limit=1, now_ns=-1)


def test_v02_scheduler_rejects_coerced_hints() -> None:
    row = _row()
    with pytest.raises(GeometryPhaseSchedulerError, match="cadence hints must contain real numbers"):
        choose_species(
            {"SPIDER": [row]},
            now_ns=2,
            cadence_hint={"SPIDER": "0.5"},  # type: ignore[dict-item]
        )
    with pytest.raises(GeometryPhaseSchedulerError, match="locality hints must contain real numbers"):
        choose_species(
            {"SPIDER": [row]},
            now_ns=2,
            locality_hint={"SPIDER": True},
        )


def test_v02_scheduler_rejects_lane_numeric_coercion() -> None:
    with pytest.raises(GeometryPhaseSchedulerError, match="vector_width must be a positive integer"):
        geometry_lane_width(
            vector_width=True,
            max_batch=4,
            cluster_coherence=0.5,
        )
    with pytest.raises(GeometryPhaseSchedulerError, match="max_batch must be a positive integer"):
        geometry_lane_width(
            vector_width=4,
            max_batch=4.5,  # type: ignore[arg-type]
            cluster_coherence=0.5,
        )
    with pytest.raises(GeometryPhaseSchedulerError, match="cluster_coherence must be a real number"):
        geometry_lane_width(
            vector_width=4,
            max_batch=4,
            cluster_coherence="0.5",  # type: ignore[arg-type]
        )
    with pytest.raises(GeometryPhaseSchedulerError, match="legacy_cap must be a positive integer"):
        geometry_lane_width(
            vector_width=4,
            max_batch=4,
            cluster_coherence=0.5,
            legacy_cap=True,
        )


def test_v02_scheduler_rejects_noncanonical_affinity_commitments() -> None:
    row = _row()
    with pytest.raises(GeometryPhaseSchedulerError, match="lowercase 64-hex commitments"):
        select_batch(
            [row],
            limit=1,
            now_ns=2,
            affinity_by_task={"task-v02": ["not-a-commitment"]},
        )
    with pytest.raises(GeometryPhaseSchedulerError, match="lowercase 64-hex commitments"):
        select_batch(
            [row],
            limit=1,
            now_ns=2,
            affinity_by_task={"task-v02": ["b" * 64]},
            receiver_known_affinity=[7],  # type: ignore[list-item]
        )
