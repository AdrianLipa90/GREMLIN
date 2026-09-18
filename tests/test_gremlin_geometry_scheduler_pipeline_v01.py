from gremlin_mcp.pipeline import fanout
from gremlin_mcp.router import route
from gremlin_mcp.workers import WorkerBroker
from tools.gremlin_geometry_phase_scheduler_v01 import SCHEDULER_KEY


def _meta() -> dict:
    return {
        "phase36": [0.25] * 36,
        "ready": True,
        "readiness": 1.0,
        "temperature": 0.3,
        "noise": 0.05,
    }


def test_pipeline_promotes_scheduler_metadata_to_worker_envelope_without_model_context_noise():
    broker = WorkerBroker()
    payload = {
        "problem": "relation graph dependency audit",
        "graph": {"A": ["B"]},
        SCHEDULER_KEY: _meta(),
    }
    queued = fanout(broker, payload, ["SPIDER"], request_id="phase-fanout")
    task_id = queued["tasks"][0]["task_id"]

    broker.register_worker("spider-phase", ["SPIDER"], vector_width=4, max_batch=4)
    lease = broker.claim("spider-phase", species="SPIDER", limit=1)
    assert lease["tasks"][0]["task_id"] == task_id
    task_payload = lease["tasks"][0]["payload"]
    assert task_payload[SCHEDULER_KEY] == _meta()
    assert SCHEDULER_KEY not in task_payload["payload"]
    assert lease["scheduler"]["batch_selection"]["phase_sources"] == {"EXPLICIT_T36": 1}
    assert SCHEDULER_KEY not in str(lease["context_pack"])


def test_octopus_semantic_scores_ignore_scheduler_numeric_phase_metadata():
    semantic = {
        "problem": "audit source citation evidence",
        "sources": ["paper-a"],
    }
    with_phase = {**semantic, SCHEDULER_KEY: _meta()}
    plain = route(semantic, max_species=4)
    phase = route(with_phase, max_species=4)

    plain_scores = {row["species"]: row["score"] for row in plain["scores"]}
    phase_scores = {row["species"]: row["score"] for row in phase["scores"]}
    assert phase_scores == plain_scores
    assert phase["route_mask"] == plain["route_mask"]
    # Commitment still binds the full request, including scheduling state.
    assert phase["route_commitment"] != plain["route_commitment"]
