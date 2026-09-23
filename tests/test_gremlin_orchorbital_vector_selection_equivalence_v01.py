from __future__ import annotations

import math

from tools.gremlin_geometry_phase_scheduler_v01 import (
    NUMPY_DISTANCE_KERNEL_CANDIDATE,
    SCALAR_DISTANCE_KERNEL,
    SCHEDULER_KEY,
    TAU,
    select_batch,
)


def _rows(seed: int, count: int):
    rows = []
    affinity = {}
    for index in range(count):
        phase = [
            (
                0.173 * index
                + 0.071 * axis
                + 0.013 * seed
                + 0.00017 * index * axis
                + 0.000003 * seed * index
            )
            % TAU
            for axis in range(36)
        ]
        task_id = f"s{seed:02d}-t{index:03d}"
        rows.append(
            {
                "task_id": task_id,
                "species": "SPIDER",
                "payload": {
                    "seed": seed,
                    "index": index,
                    SCHEDULER_KEY: {
                        "phase36": phase,
                        "ready": True,
                        "readiness": 0.25 + 0.7 * ((index * 7 + seed) % 19) / 18.0,
                        "temperature": ((index * 11 + seed) % 23) / 22.0,
                        "urgency": ((index * 5 + seed) % 13) / 12.0,
                        "noise": ((index * 3 + seed) % 17) / 20.0,
                    },
                },
                "task_commitment": f"commit-{seed:02d}-{index:03d}",
                "created_ns": seed * 10_000 + index + 1,
            }
        )
        affinity[task_id] = (
            "root",
            f"branch-{index % 4}",
            f"sub-{(index + seed) % 7}",
        )
    return rows, affinity


def _select(rows, affinity, *, kernel: str, seed: int, limit: int):
    return select_batch(
        rows,
        limit=limit,
        now_ns=1_000_000_000_000 + seed,
        affinity_by_task=affinity,
        receiver_known_affinity=("root", f"branch-{seed % 4}"),
        distance_kernel=kernel,
    )


def test_numpy_candidate_preserves_full_greedy_selection_across_deterministic_fixtures() -> None:
    for seed in range(24):
        count = 17 + (seed % 8) * 5
        rows, affinity = _rows(seed, count)
        limit = min(9, count)

        scalar_ids, scalar_receipt = _select(
            rows,
            affinity,
            kernel=SCALAR_DISTANCE_KERNEL,
            seed=seed,
            limit=limit,
        )
        vector_ids, vector_receipt = _select(
            rows,
            affinity,
            kernel=NUMPY_DISTANCE_KERNEL_CANDIDATE,
            seed=seed,
            limit=limit,
        )

        assert vector_ids == scalar_ids
        assert vector_receipt["selected_task_ids"] == scalar_receipt["selected_task_ids"]
        assert vector_receipt["fifo_task_ids_proxy"] == scalar_receipt["fifo_task_ids_proxy"]
        assert (
            vector_receipt["greedy_pairwise_state_distance_evaluations"]
            == scalar_receipt["greedy_pairwise_state_distance_evaluations"]
        )
        assert vector_receipt["mean_context_affinity"] == scalar_receipt[
            "mean_context_affinity"
        ]
        assert vector_receipt["mean_receiver_cache_affinity"] == scalar_receipt[
            "mean_receiver_cache_affinity"
        ]
        assert math.isclose(
            vector_receipt["transition_cost_selected"],
            scalar_receipt["transition_cost_selected"],
            rel_tol=0.0,
            abs_tol=0.0,
        )
        assert math.isclose(
            vector_receipt["noise_cost_selected"],
            scalar_receipt["noise_cost_selected"],
            rel_tol=0.0,
            abs_tol=0.0,
        )


def test_numpy_candidate_preserves_exact_tie_break_order() -> None:
    phase = [1.25] * 36
    rows = [
        {
            "task_id": task_id,
            "species": "SPIDER",
            "payload": {
                SCHEDULER_KEY: {
                    "phase36": phase,
                    "ready": True,
                    "readiness": 0.8,
                    "temperature": 0.4,
                    "urgency": 0.3,
                    "noise": 0.2,
                }
            },
            "task_commitment": commitment,
            "created_ns": index + 1,
        }
        for index, (task_id, commitment) in enumerate(
            (
                ("tie-a", "commit-a"),
                ("tie-b", "commit-b"),
                ("tie-c", "commit-c"),
                ("tie-d", "commit-d"),
            )
        )
    ]
    affinity = {row["task_id"]: ("root", "same") for row in rows}

    scalar, _ = select_batch(
        rows,
        limit=4,
        now_ns=99,
        affinity_by_task=affinity,
        receiver_known_affinity=("root",),
        distance_kernel=SCALAR_DISTANCE_KERNEL,
    )
    vector, _ = select_batch(
        rows,
        limit=4,
        now_ns=99,
        affinity_by_task=affinity,
        receiver_known_affinity=("root",),
        distance_kernel=NUMPY_DISTANCE_KERNEL_CANDIDATE,
    )

    assert vector == scalar


def test_numpy_candidate_preserves_near_tie_selection() -> None:
    rows = []
    for index, epsilon in enumerate((0.0, 1e-8, 2e-8, 5e-8, 1e-7, 2e-7)):
        phase = [(0.75 + epsilon + axis * 1e-9) % TAU for axis in range(36)]
        rows.append(
            {
                "task_id": f"near-{index}",
                "species": "SPIDER",
                "payload": {
                    SCHEDULER_KEY: {
                        "phase36": phase,
                        "ready": True,
                        "readiness": 0.7,
                        "temperature": 0.2,
                        "urgency": 0.1,
                        "noise": 0.05,
                    }
                },
                "task_commitment": f"near-commit-{index}",
                "created_ns": index + 1,
            }
        )

    scalar, _ = select_batch(
        rows,
        limit=len(rows),
        now_ns=1000,
        distance_kernel=SCALAR_DISTANCE_KERNEL,
    )
    vector, _ = select_batch(
        rows,
        limit=len(rows),
        now_ns=1000,
        distance_kernel=NUMPY_DISTANCE_KERNEL_CANDIDATE,
    )

    assert vector == scalar


def test_numpy_candidate_receipt_remains_explicitly_candidate_only() -> None:
    rows, affinity = _rows(3, 20)
    _, receipt = _select(
        rows,
        affinity,
        kernel=NUMPY_DISTANCE_KERNEL_CANDIDATE,
        seed=3,
        limit=6,
    )

    assert receipt["distance_kernel"] == NUMPY_DISTANCE_KERNEL_CANDIDATE
    assert receipt["distance_kernel_candidate_only"] is True
