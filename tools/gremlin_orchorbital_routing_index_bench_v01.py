from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gremlin_mcp.orchorbital_context import PACKET_PAYLOAD_KEY, OrbitalContextStore
from gremlin_mcp.orchorbital_fabric import OrchorbitalFabric
from gremlin_mcp.workers import WorkerBroker
from tools.gremlin_geometry_phase_scheduler_v01 import SCHEDULER_KEY

OUT = Path("provenance/GREMLIN_ORCHORBITAL_ROUTING_INDEX_BENCHMARK_V0_1.json")
SCHEMA = "GREMLIN_ORCHORBITAL_ROUTING_INDEX_BENCHMARK_V0_1"


def _positive_int(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def run_benchmark(
    *,
    target_tasks: int = 8,
    unrelated_tasks: int = 4096,
) -> dict[str, Any]:
    """Measure same-species candidate inspection reduction from warm ancestry.

    Every queued task is SPIDER. The only routing distinction is committed
    orbital context ancestry, so the result cannot be attributed to a trivial
    species index.
    """

    target_tasks = _positive_int(target_tasks, "target_tasks")
    unrelated_tasks = _positive_int(unrelated_tasks, "unrelated_tasks")
    total_tasks = target_tasks + unrelated_tasks

    fabric = OrchorbitalFabric(max_nodes=total_tasks + 3)
    contexts = OrbitalContextStore(fabric)
    contexts.bind_root(
        {
            "shared": "same-species-routing-index",
            "authority": "candidate-only",
        }
    )
    target_anchor = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="TARGET:ANCHOR",
        join_to_caller=False,
    )
    unrelated_anchor = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="UNRELATED:ANCHOR",
        join_to_caller=False,
    )
    contexts.inherit_from_caller(
        target_anchor.node_id,
        set_values={"orbital_branch": "target"},
    )
    contexts.inherit_from_caller(
        unrelated_anchor.node_id,
        set_values={"orbital_branch": "unrelated"},
    )

    broker = WorkerBroker(max_pending=total_tasks + 16)
    broker.register_worker(
        "routing-index-bench",
        ["SPIDER"],
        vector_width=8,
        max_batch=128,
    )
    scheduler = {
        "phase36": [0.75] * 36,
        "ready": True,
        "readiness": 1.0,
        "noise": 0.05,
        "urgency": 0.0,
    }

    target_ids: list[str] = []
    for index in range(target_tasks):
        node = fabric.spawn(
            target_anchor.node_id,
            "SPIDER",
            node_id=f"TARGET:{index:05d}",
            join_to_caller=False,
        )
        contexts.inherit_from_caller(
            node.node_id,
            set_values={"target_index": index},
        )
        task_id = f"target-{index:05d}"
        target_ids.append(task_id)
        broker.enqueue(
            "SPIDER",
            {
                "class": "target",
                "index": index,
                SCHEDULER_KEY: scheduler,
                PACKET_PAYLOAD_KEY: contexts.packet(node.node_id),
            },
            task_id=task_id,
        )

    for index in range(unrelated_tasks):
        node = fabric.spawn(
            unrelated_anchor.node_id,
            "SPIDER",
            node_id=f"UNRELATED:{index:05d}",
            join_to_caller=False,
        )
        contexts.inherit_from_caller(
            node.node_id,
            set_values={"unrelated_index": index},
        )
        broker.enqueue(
            "SPIDER",
            {
                "class": "unrelated",
                "index": index,
                SCHEDULER_KEY: scheduler,
                PACKET_PAYLOAD_KEY: contexts.packet(node.node_id),
            },
            task_id=f"unrelated-{index:05d}",
        )

    # The receiver has already worked in the target branch. Root is also warm,
    # but the broker should choose the smallest matching ancestry bucket.
    known_frames = (
        contexts.frame("AUTH:ROOT").frame_commitment,
        contexts.frame(target_anchor.node_id).frame_commitment,
    )

    scheduler_views = 0
    original = broker._scheduler_task_view

    def counted(record):
        nonlocal scheduler_views
        scheduler_views += 1
        return original(record)

    broker._scheduler_task_view = counted  # type: ignore[method-assign]
    lease = broker.claim(
        "routing-index-bench",
        species="SPIDER",
        limit=target_tasks,
        known_context_frames=known_frames,
    )

    scope = lease["scheduler"]["context_candidate_scope"]
    naive_same_species_scan_candidates = total_tasks
    indexed_candidates = scheduler_views
    structural_scan_reduction_ratio = (
        naive_same_species_scan_candidates / indexed_candidates
        if indexed_candidates > 0
        else float("inf")
    )
    avoided_candidate_inspections = (
        naive_same_species_scan_candidates - indexed_candidates
    )
    reduction_fraction = (
        avoided_candidate_inspections / naive_same_species_scan_candidates
    )

    claimed_ids = [task["task_id"] for task in lease["tasks"]]
    exact_target_only = set(claimed_ids) == set(target_ids[: len(claimed_ids)])
    no_cross_orbit_claim = all(
        task["payload"].get("class") == "target"
        for task in lease["tasks"]
    )
    ancestry_index_hit = bool(scope.get("active") and scope.get("hit"))
    selected_bucket_is_target = (
        scope.get("selected_context_frame_commitment")
        == contexts.frame(target_anchor.node_id).frame_commitment
    )

    verdict = (
        "PASS_SAME_SPECIES_ORCHORBITAL_INDEX_REDUCTION"
        if (
            exact_target_only
            and no_cross_orbit_claim
            and ancestry_index_hit
            and selected_bucket_is_target
            and indexed_candidates < naive_same_species_scan_candidates
        )
        else "FAIL_SAME_SPECIES_ORCHORBITAL_INDEX_REDUCTION"
    )

    return {
        "schema": SCHEMA,
        "fixture": {
            "species": "SPIDER",
            "target_orbit": target_anchor.node_id,
            "unrelated_orbit": unrelated_anchor.node_id,
            "target_tasks": target_tasks,
            "unrelated_tasks": unrelated_tasks,
            "total_same_species_queued_before_claim": total_tasks,
            "worker_known_frame_count": len(known_frames),
        },
        "summary": {
            "scheduler_task_views": scheduler_views,
            "naive_global_scan_candidates_proxy": naive_same_species_scan_candidates,
            "naive_same_species_scan_candidates_proxy": naive_same_species_scan_candidates,
            "indexed_candidate_count": scope.get("candidate_count"),
            "indexed_local_count": scope.get("indexed_local_count"),
            "fairness_candidate_count": scope.get("fairness_candidate_count"),
            "avoided_candidate_inspections": avoided_candidate_inspections,
            "candidate_inspection_reduction_fraction": reduction_fraction,
            "structural_scan_reduction_ratio": structural_scan_reduction_ratio,
            "claimed_batch_size": lease["batch_size"],
            "exact_target_orbit_only": exact_target_only,
            "no_cross_orbit_claim": no_cross_orbit_claim,
            "same_species_fixture": True,
            "context_ancestry_index_active": ancestry_index_hit,
            "selected_smallest_warm_bucket": selected_bucket_is_target,
            "queue_indexed": True,
            "actual_wall_clock_speedup_claim": False,
            "end_to_end_speedup_claim": False,
            "two_hundred_x_end_to_end_claim": False,
        },
        "verdict": verdict,
        "claim_scope": (
            "SAME_SPECIES_ORCHORBITAL_CANDIDATE_INSPECTION_REDUCTION_FOR_THIS_"
            "SYNTHETIC_WARM_CONTEXT_FIXTURE_ONLY; NOT WALL_CLOCK OR END_TO_END SPEEDUP"
        ),
        "authority": {
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        },
    }


def main() -> int:
    receipt = run_benchmark()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt["summary"], sort_keys=True))
    print(f"verdict={receipt['verdict']}")
    print(f"claim_scope={receipt['claim_scope']}")
    print(f"receipt={OUT}")
    return 0 if receipt["verdict"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
