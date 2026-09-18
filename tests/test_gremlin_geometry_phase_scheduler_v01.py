from __future__ import annotations

import math

from gremlin_mcp.workers import WorkerBroker, WORKER_SPECIES
from tools.gremlin_geometry_phase_scheduler_v01 import (
    MODE,
    SCHEDULER_KEY,
    choose_species,
    derived_phase36,
    geometry_lane_width,
    phase_distance,
    queue_metrics,
    scheduler_manifest,
    select_batch,
)


def _phase(value: float) -> list[float]:
    return [value % (2.0 * math.pi)] * 36


def _payload(value: str, phase: float, *, ready: bool = True, noise: float = 0.05, urgency: float = 0.0):
    return {
        "text": value,
        SCHEDULER_KEY: {
            "phase36": _phase(phase),
            "ready": ready,
            "noise": noise,
            "urgency": urgency,
            "temperature": 0.4,
        },
    }


def _row(task_id: str, species: str, phase: float, created_ns: int, *, ready: bool = True):
    payload = _payload(task_id, phase, ready=ready)
    return {
        "task_id": task_id,
        "species": species,
        "payload": payload,
        "task_commitment": f"commit-{task_id}",
        "created_ns": created_ns,
    }


def test_scheduler_manifest_explicitly_disables_fifo_primary():
    manifest = scheduler_manifest()
    assert manifest["mode"] == MODE
    assert manifest["fifo_primary"] is False
    assert manifest["fifo_proxy_only"] is True
    assert manifest["space"] == "T^36"
    assert manifest["token_saving_claim"] is False


def test_new_bestiary_species_are_worker_schedulable():
    for name in ("FOX", "BEAVER", "BAT", "CANARY", "SERPENT", "CHAMELEON"):
        assert name in WORKER_SPECIES
    for name in ("HUMMINGBIRD", "OCTOPUS", "GREMLIN", "FERRET"):
        assert name not in WORKER_SPECIES


def test_explicit_phase_cluster_beats_fifo_outlier():
    broker = WorkerBroker()
    broker.register_worker("serpent-worker", ["SERPENT"], vector_width=8, max_batch=8)

    # The oldest task is intentionally a geometric outlier. FIFO would select it.
    broker.enqueue("SERPENT", _payload("old-outlier", 4.8), task_id="old-outlier")
    broker.enqueue("SERPENT", _payload("cluster-a", 1.00), task_id="cluster-a")
    broker.enqueue("SERPENT", _payload("cluster-b", 1.03), task_id="cluster-b")
    broker.enqueue("SERPENT", _payload("cluster-c", 1.06), task_id="cluster-c")

    lease = broker.claim("serpent-worker", species="SERPENT", limit=2)
    ids = [row["task_id"] for row in lease["tasks"]]
    assert "old-outlier" not in ids
    assert set(ids) <= {"cluster-a", "cluster-b", "cluster-c"}
    scheduler = lease["scheduler"]["batch_selection"]
    assert scheduler["fifo_used_for_selection"] is False
    assert scheduler["transition_cost_selected"] <= scheduler["transition_cost_fifo_proxy"]


def test_not_ready_state_is_not_scheduled_even_if_oldest():
    broker = WorkerBroker()
    broker.register_worker("canary-worker", ["CANARY"], vector_width=4, max_batch=4)
    broker.enqueue("CANARY", _payload("blocked-old", 0.0, ready=False), task_id="blocked-old")
    broker.enqueue("CANARY", _payload("ready-new", 0.1, ready=True), task_id="ready-new")
    lease = broker.claim("canary-worker", species="CANARY", limit=4)
    assert [row["task_id"] for row in lease["tasks"]] == ["ready-new"]


def test_species_selection_uses_queue_geometry_before_cadence():
    now = 10_000_000_000
    coherent = [
        _row("r1", "RAVEN", 1.00, 1),
        _row("r2", "RAVEN", 1.01, 2),
        _row("r3", "RAVEN", 1.02, 3),
    ]
    incoherent = [
        _row("s1", "SERPENT", 0.0, 1),
        _row("s2", "SERPENT", 2.1, 2),
        _row("s3", "SERPENT", 4.2, 3),
    ]
    selected, receipt = choose_species(
        {"RAVEN": coherent, "SERPENT": incoherent},
        now_ns=now,
        cadence_hint={"RAVEN": 1.0, "SERPENT": 9999.0},
    )
    assert selected == "RAVEN"
    assert receipt["selection_basis"] == "GEOMETRY_PHASE_STATE_THEN_CADENCE_TIEBREAK"


def test_geometry_lane_expands_for_coherent_queue_and_contracts_for_noisy_queue():
    coherent = geometry_lane_width(vector_width=8, max_batch=64, cluster_coherence=0.95, legacy_cap=64)
    noisy = geometry_lane_width(vector_width=8, max_batch=64, cluster_coherence=0.10, legacy_cap=64)
    assert coherent > noisy
    assert 1 <= noisy <= coherent <= 64


def test_scheduler_reduces_phase_transition_proxy_on_alternating_fifo():
    rows = [
        _row("a0", "FOX", 0.00, 1),
        _row("b0", "FOX", 2.00, 2),
        _row("a1", "FOX", 0.03, 3),
        _row("b1", "FOX", 2.03, 4),
        _row("a2", "FOX", 0.06, 5),
        _row("b2", "FOX", 2.06, 6),
    ]
    ids, receipt = select_batch(rows, limit=3, now_ns=10_000_000_000)
    assert len(ids) == 3
    assert receipt["transition_cost_selected"] < receipt["transition_cost_fifo_proxy"]
    assert receipt["transition_reduction_vs_fifo_proxy"] > 0.0
    assert receipt["noise_reduction_vs_fifo_proxy"] > 0.0


def test_derived_phase_is_deterministic_and_bounded():
    payload = {"topic": "phase geometry scheduler", "claim": "same input same state"}
    a = derived_phase36(payload)
    b = derived_phase36(payload)
    assert a == b
    assert len(a) == 36
    assert all(0.0 <= x < 2.0 * math.pi for x in a)


def test_related_payloads_share_closer_derived_geometry_than_exactly_unrelated_fixture():
    shared = {
        "topic": "riemann zeta phase geometry scheduler resonance memory",
        "context": "phase geometry scheduler resonance memory proof audit",
    }
    related = {
        "topic": "riemann zeta phase geometry scheduler resonance memory",
        "context": "phase geometry scheduler resonance memory derivation audit",
    }
    unrelated = {
        "topic": "culinary inventory refrigeration invoice payroll rota",
        "context": "warehouse forklift customs manifest barcode parcel",
    }
    d_related = phase_distance(derived_phase36(shared), derived_phase36(related))
    d_unrelated = phase_distance(derived_phase36(shared), derived_phase36(unrelated))
    assert d_related < d_unrelated


def test_queue_metrics_reports_explicit_phase_and_coherence():
    rows = [_row("x1", "BAT", 0.2, 1), _row("x2", "BAT", 0.21, 2)]
    metrics = queue_metrics(rows, now_ns=3)
    assert metrics["eligible"] is True
    assert metrics["eligible_count"] == 2
    assert metrics["explicit_phase_fraction"] == 1.0
    assert metrics["cluster_coherence"] > 0.99
