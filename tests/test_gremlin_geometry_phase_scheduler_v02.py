from __future__ import annotations

from gremlin_mcp.workers import WorkerBroker
from tools.gremlin_bestiary_phasenav_phase_gates_v02 import role_phase_carrier
from tools.gremlin_geometry_phase_scheduler_v02 import (
    MODE,
    SCHEDULER_KEY,
    scheduler_manifest,
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
