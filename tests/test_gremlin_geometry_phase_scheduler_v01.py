from __future__ import annotations

import math

import pytest

from gremlin_mcp.role_registry import (
    BESTIARY_ROLE_NAMES,
    CONTROL_PLANE_SPECIES,
    DYNAMIC_WORKLOAD_SPECIES,
)
from gremlin_mcp.workers import WorkerBroker, WORKER_SPECIES
from tools.gremlin_geometry_phase_scheduler_v01 import (
    GeometryPhaseSchedulerError,
    MODE,
    SCHEDULER_KEY,
    choose_species,
    derived_phase36,
    geometry_lane_width,
    phase_distance,
    queue_metrics,
    scheduler_manifest,
    select_batch,
    task_phase_state,
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
    for name in ("FOX", "BEAVER", "BAT", "CANARY", "SERPENT", "CHAMELEON", "ELEPHANT", "BEES"):
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


def test_optional_context_affinity_prefers_shared_orbital_ancestry() -> None:
    rows = [
        {
            "task_id": "seed",
            "species": "FOX",
            "payload": _payload("seed", 1.0, urgency=1.0),
            "task_commitment": "commit-seed",
            "created_ns": 1,
        },
        {
            "task_id": "sibling",
            "species": "FOX",
            "payload": _payload("sibling", 1.0),
            "task_commitment": "commit-a-sibling",
            "created_ns": 2,
        },
        {
            "task_id": "other",
            "species": "FOX",
            "payload": _payload("other", 1.0),
            "task_commitment": "commit-z-other",
            "created_ns": 3,
        },
    ]

    without_affinity, plain = select_batch(
        rows,
        limit=2,
        now_ns=10_000_000_000,
    )
    with_affinity, receipt = select_batch(
        rows,
        limit=2,
        now_ns=10_000_000_000,
        affinity_by_task={
            "seed": ("root", "branch-a"),
            "sibling": ("root", "branch-a"),
            "other": ("root", "branch-b"),
        },
    )

    assert without_affinity[0] == "seed"
    assert with_affinity == ["seed", "sibling"]
    assert plain["context_affinity_active"] is False
    assert receipt["context_affinity_active"] is True
    assert receipt["context_affinity_weight"] > 0.0
    assert receipt["mean_context_affinity"] == 1.0
    assert receipt["context_affinity_bitset_used"] is True
    assert receipt["context_affinity_commitment_count"] == 3


def test_receiver_cache_affinity_can_break_equal_geometry_seed_tie() -> None:
    rows = [
        {
            "task_id": "cached",
            "species": "FOX",
            "payload": _payload("cached", 1.0),
            "task_commitment": "commit-a-cached",
            "created_ns": 1,
        },
        {
            "task_id": "uncached",
            "species": "FOX",
            "payload": _payload("uncached", 1.0),
            "task_commitment": "commit-z-uncached",
            "created_ns": 2,
        },
    ]

    plain, _ = select_batch(rows, limit=1, now_ns=10_000_000_000)
    localized, receipt = select_batch(
        rows,
        limit=1,
        now_ns=10_000_000_000,
        affinity_by_task={
            "cached": ("root", "branch-a"),
            "uncached": ("root", "branch-b"),
        },
        receiver_known_affinity=("branch-a",),
    )

    assert plain == ["uncached"]
    assert localized == ["cached"]
    assert receipt["receiver_cache_affinity_active"] is True
    assert receipt["receiver_cache_affinity_weight"] > 0.0
    assert receipt["mean_receiver_cache_affinity"] == 0.5
    assert receipt["receiver_cache_affinity_precomputed"] is True
    assert receipt["context_affinity_bitset_used"] is True


def test_species_selection_accepts_small_receiver_locality_bias() -> None:
    now = 10_000_000_000
    raven = [_row("r1", "RAVEN", 1.0, 1)]
    serpent = [_row("s1", "SERPENT", 1.0, 1)]

    plain, _ = choose_species(
        {"RAVEN": raven, "SERPENT": serpent},
        now_ns=now,
        cadence_hint={"RAVEN": 0.0, "SERPENT": 0.0},
    )
    localized, receipt = choose_species(
        {"RAVEN": raven, "SERPENT": serpent},
        now_ns=now,
        cadence_hint={"RAVEN": 0.0, "SERPENT": 0.0},
        locality_hint={"RAVEN": 1.0, "SERPENT": 0.0},
    )

    assert localized == "RAVEN"
    assert receipt["selection_basis"] == (
        "GEOMETRY_PHASE_STATE_PLUS_RECEIVER_LOCALITY_THEN_CADENCE"
    )
    assert receipt["queues"]["RAVEN"]["receiver_locality_hint"] == 1.0
    assert receipt["receiver_species_affinity_weight"] > 0.0
    assert plain in {"RAVEN", "SERPENT"}


def test_context_affinity_prefers_deeper_shared_ancestry_over_root_only() -> None:
    rows = [
        {
            "task_id": "seed-deep",
            "species": "FOX",
            "payload": _payload("seed-deep", 1.0, urgency=1.0),
            "task_commitment": "commit-seed-deep",
            "created_ns": 1,
        },
        {
            "task_id": "same-branch",
            "species": "FOX",
            "payload": _payload("same-branch", 1.0),
            "task_commitment": "commit-a-same-branch",
            "created_ns": 2,
        },
        {
            "task_id": "root-only",
            "species": "FOX",
            "payload": _payload("root-only", 1.0),
            "task_commitment": "commit-z-root-only",
            "created_ns": 3,
        },
    ]

    selected, receipt = select_batch(
        rows,
        limit=2,
        now_ns=10_000_000_000,
        affinity_by_task={
            "seed-deep": ("root", "branch-a", "parent-a1"),
            "same-branch": ("root", "branch-a", "parent-a1", "child-a2"),
            "root-only": ("root", "branch-b", "parent-b1"),
        },
    )

    assert selected == ["seed-deep", "same-branch"]
    assert receipt["context_affinity_active"] is True
    assert receipt["mean_context_affinity"] > 0.5


def test_context_affinity_does_not_change_selection_when_absent() -> None:
    rows = [
        {
            "task_id": "a",
            "species": "FOX",
            "payload": _payload("a", 0.5),
            "task_commitment": "commit-a",
            "created_ns": 1,
        },
        {
            "task_id": "b",
            "species": "FOX",
            "payload": _payload("b", 0.5),
            "task_commitment": "commit-b",
            "created_ns": 2,
        },
    ]

    baseline, baseline_receipt = select_batch(
        rows,
        limit=2,
        now_ns=10_000_000_000,
    )
    explicit_empty, empty_receipt = select_batch(
        rows,
        limit=2,
        now_ns=10_000_000_000,
        affinity_by_task={},
        receiver_known_affinity=(),
    )

    assert explicit_empty == baseline
    assert empty_receipt["context_affinity_active"] is False
    assert empty_receipt["receiver_cache_affinity_active"] is False
    assert baseline_receipt["selected_task_ids"] == empty_receipt["selected_task_ids"]


def test_context_affinity_cannot_override_large_phase_state_distance() -> None:
    rows = [
        {
            "task_id": "seed",
            "species": "FOX",
            "payload": _payload("seed", 0.00, urgency=1.0),
            "task_commitment": "commit-seed",
            "created_ns": 1,
        },
        {
            "task_id": "phase-near",
            "species": "FOX",
            "payload": _payload("phase-near", 0.03),
            "task_commitment": "commit-phase-near",
            "created_ns": 2,
        },
        {
            "task_id": "context-near-phase-far",
            "species": "FOX",
            "payload": _payload("context-near-phase-far", 2.80),
            "task_commitment": "commit-context-far",
            "created_ns": 3,
        },
    ]

    selected, receipt = select_batch(
        rows,
        limit=2,
        now_ns=10_000_000_000,
        affinity_by_task={
            "seed": ("root", "branch-a"),
            "phase-near": ("root", "branch-b"),
            "context-near-phase-far": ("root", "branch-a"),
        },
    )

    assert selected == ["seed", "phase-near"]
    assert receipt["context_affinity_active"] is True
    assert 0.0 < receipt["context_affinity_weight"] < 0.10


def test_receiver_species_locality_cannot_override_large_geometry_gap() -> None:
    now = 10_000_000_000
    coherent = [
        _row("r1", "RAVEN", 1.00, 1),
        _row("r2", "RAVEN", 1.01, 2),
        _row("r3", "RAVEN", 1.02, 3),
        _row("r4", "RAVEN", 1.03, 4),
    ]
    incoherent = [
        _row("s1", "SERPENT", 0.0, 1),
        _row("s2", "SERPENT", 1.57, 2),
        _row("s3", "SERPENT", 3.14, 3),
        _row("s4", "SERPENT", 4.71, 4),
    ]

    selected, receipt = choose_species(
        {"RAVEN": coherent, "SERPENT": incoherent},
        now_ns=now,
        cadence_hint={"RAVEN": 0.0, "SERPENT": 0.0},
        locality_hint={"RAVEN": 0.0, "SERPENT": 1.0},
    )

    assert selected == "RAVEN"
    assert receipt["receiver_species_affinity_weight"] < 0.10
    assert (
        receipt["queues"]["RAVEN"]["effective_queue_score"]
        > receipt["queues"]["SERPENT"]["effective_queue_score"]
    )


def test_unknown_affinity_task_ids_are_neutral() -> None:
    rows = [
        _row("a", "FOX", 0.10, 1),
        _row("b", "FOX", 0.12, 2),
        _row("c", "FOX", 0.14, 3),
    ]

    baseline, _ = select_batch(
        rows,
        limit=2,
        now_ns=10_000_000_000,
    )
    selected, receipt = select_batch(
        rows,
        limit=2,
        now_ns=10_000_000_000,
        affinity_by_task={
            "not-in-queue": ("root", "branch-x"),
        },
    )

    assert selected == baseline
    assert receipt["context_affinity_active"] is False


def test_malformed_affinity_input_fails_closed() -> None:
    rows = [_row("a", "FOX", 0.10, 1)]

    try:
        select_batch(
            rows,
            limit=1,
            now_ns=10_000_000_000,
            affinity_by_task={"a": "not-an-iterable-of-commitments"},
        )
    except ValueError as exc:
        assert "task affinity must be an iterable" in str(exc)
    else:
        raise AssertionError("malformed context affinity must fail closed")


def test_scheduler_exposes_exact_dynamic_and_control_plane_role_split() -> None:
    manifest = scheduler_manifest()

    assert len(WORKER_SPECIES) == 16
    assert set(manifest["dynamic_workload_species"]) == set(WORKER_SPECIES)
    assert set(manifest["anchor_neutral_dynamic_species"]) == {
        "BEES",
        "ELEPHANT",
    }
    assert "BEES" not in manifest["validated_phasenav_carrier_species"]
    assert "ELEPHANT" not in manifest["validated_phasenav_carrier_species"]


def test_bees_and_elephant_accept_explicit_t36_without_invented_species_anchor() -> None:
    for species in ("BEES", "ELEPHANT"):
        broker = WorkerBroker()
        broker.register_worker(
            f"{species.lower()}-worker",
            [species],
            vector_width=4,
            max_batch=4,
        )
        broker.enqueue(
            species,
            _payload(
                f"{species.lower()} explicit phase",
                1.25,
                ready=True,
            ),
            task_id=f"{species.lower()}-task",
        )

        lease = broker.claim(
            f"{species.lower()}-worker",
            species=species,
            limit=1,
        )

        assert lease["species"] == species
        assert lease["tasks"][0]["task_id"] == f"{species.lower()}-task"
        queue = lease["scheduler"]["species_selection"]["queues"][species]
        assert queue["explicit_phase_fraction"] == 1.0


def test_precomputed_states_preserve_exact_batch_selection() -> None:
    rows = [
        {
            "task_id": f"cached-{index}",
            "species": "FOX",
            "payload": _payload(
                f"cached-{index}",
                0.2 + 0.01 * index,
                urgency=(index % 3) / 2.0,
            ),
            "task_commitment": f"commit-{index:03d}",
            "created_ns": index + 1,
        }
        for index in range(12)
    ]
    states = {
        row["task_id"]: task_phase_state(row)
        for row in rows
    }

    baseline_ids, baseline = select_batch(
        rows,
        limit=6,
        now_ns=10_000_000_000,
        affinity_by_task={
            row["task_id"]: ("root", f"branch-{int(index / 4)}")
            for index, row in enumerate(rows)
        },
        receiver_known_affinity=("root",),
    )
    metrics = queue_metrics(
        rows,
        now_ns=10_000_000_000,
        precomputed_states=states,
    )
    cached_ids, cached = select_batch(
        rows,
        limit=6,
        now_ns=10_000_000_000,
        affinity_by_task={
            row["task_id"]: ("root", f"branch-{int(index / 4)}")
            for index, row in enumerate(rows)
        },
        receiver_known_affinity=("root",),
        precomputed_states=states,
        precomputed_centroid=metrics["centroid"],
    )

    assert cached_ids == baseline_ids
    assert cached["transition_cost_selected"] == baseline["transition_cost_selected"]
    assert cached["noise_cost_selected"] == baseline["noise_cost_selected"]
    assert cached["mean_priority"] == baseline["mean_priority"]
    assert baseline["precomputed_state_cache_used"] is False
    assert cached["precomputed_state_cache_used"] is True
    assert cached["precomputed_centroid_used"] is True


def test_precomputed_state_lineage_mismatch_fails_closed() -> None:
    row = {
        "task_id": "cached-one",
        "species": "FOX",
        "payload": _payload("cached-one", 0.5),
        "task_commitment": "commit-cached-one",
        "created_ns": 1,
    }
    state = task_phase_state(row)
    drifted = dict(row)
    drifted["task_commitment"] = "commit-drift"

    with pytest.raises(GeometryPhaseSchedulerError, match="lineage mismatch"):
        select_batch(
            [drifted],
            limit=1,
            now_ns=10,
            precomputed_states={"cached-one": state},
        )


def test_bestiary_registry_partitions_exactly_into_dynamic_and_control_plane() -> None:
    assert len(BESTIARY_ROLE_NAMES) == 20
    assert len(DYNAMIC_WORKLOAD_SPECIES) == 16
    assert len(CONTROL_PLANE_SPECIES) == 4
    assert DYNAMIC_WORKLOAD_SPECIES.isdisjoint(CONTROL_PLANE_SPECIES)
    assert DYNAMIC_WORKLOAD_SPECIES | CONTROL_PLANE_SPECIES == BESTIARY_ROLE_NAMES
    assert set(WORKER_SPECIES) == set(DYNAMIC_WORKLOAD_SPECIES)


def test_bitset_affinity_selection_matches_legacy_set_overlap_ordering() -> None:
    rows = [
        {
            "task_id": "seed-bits",
            "species": "FOX",
            "payload": _payload("seed-bits", 1.2, urgency=1.0),
            "task_commitment": "commit-seed-bits",
            "created_ns": 1,
        },
        {
            "task_id": "deep-bits",
            "species": "FOX",
            "payload": _payload("deep-bits", 1.2),
            "task_commitment": "commit-a-deep",
            "created_ns": 2,
        },
        {
            "task_id": "shallow-bits",
            "species": "FOX",
            "payload": _payload("shallow-bits", 1.2),
            "task_commitment": "commit-b-shallow",
            "created_ns": 3,
        },
        {
            "task_id": "other-bits",
            "species": "FOX",
            "payload": _payload("other-bits", 1.2),
            "task_commitment": "commit-c-other",
            "created_ns": 4,
        },
    ]
    affinity = {
        "seed-bits": ("root", "a", "a1", "a2"),
        "deep-bits": ("root", "a", "a1", "a2", "a3"),
        "shallow-bits": ("root", "a"),
        "other-bits": ("root", "b", "b1", "b2"),
    }

    selected, receipt = select_batch(
        rows,
        limit=3,
        now_ns=10_000_000_000,
        affinity_by_task=affinity,
        receiver_known_affinity=("root", "a", "a1"),
    )

    assert selected[0] == "seed-bits"
    assert selected[1] == "deep-bits"
    assert receipt["context_affinity_bitset_used"] is True
    assert receipt["context_affinity_commitment_count"] == 8
    assert receipt["receiver_cache_affinity_precomputed"] is True
