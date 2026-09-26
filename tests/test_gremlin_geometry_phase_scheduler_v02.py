from __future__ import annotations

import pytest

from gremlin_mcp.workers import WorkerBroker
from tools.gremlin_bestiary_phasenav_phase_gates_v02 import role_phase_carrier
from tools.gremlin_geometry_phase_scheduler_v02 import (
    MODE,
    SCHEDULER_KEY,
    GeometryPhaseSchedulerError,
    derived_phase36,
    scheduler_manifest,
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
