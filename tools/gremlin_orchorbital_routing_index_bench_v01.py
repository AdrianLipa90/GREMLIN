from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gremlin_mcp.workers import WorkerBroker

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
    target_tasks = _positive_int(target_tasks, "target_tasks")
    unrelated_tasks = _positive_int(unrelated_tasks, "unrelated_tasks")

    broker = WorkerBroker(max_pending=target_tasks + unrelated_tasks + 16)
    broker.register_worker(
        "routing-index-bench",
        ["SPIDER"],
        vector_width=8,
        max_batch=128,
    )

    for index in range(target_tasks):
        broker.enqueue(
            "SPIDER",
            {"class": "target", "index": index},
            task_id=f"target-{index:05d}",
        )
    for index in range(unrelated_tasks):
        broker.enqueue(
            "OWL",
            {"class": "unrelated", "index": index},
            task_id=f"unrelated-{index:05d}",
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
    )

    naive_global_scan_candidates = target_tasks + unrelated_tasks
    indexed_candidates = scheduler_views
    structural_scan_reduction_ratio = (
        naive_global_scan_candidates / indexed_candidates
        if indexed_candidates > 0
        else float("inf")
    )
    avoided_candidate_inspections = (
        naive_global_scan_candidates - indexed_candidates
    )
    reduction_fraction = (
        avoided_candidate_inspections / naive_global_scan_candidates
    )

    exact_target_only = indexed_candidates == target_tasks
    no_cross_species_claim = all(
        task["species"] == "SPIDER"
        for task in lease["tasks"]
    )
    verdict = (
        "PASS_INDEXED_ROUTING_SCAN_REDUCTION"
        if exact_target_only and no_cross_species_claim
        else "FAIL_INDEXED_ROUTING_SCAN_REDUCTION"
    )

    return {
        "schema": SCHEMA,
        "fixture": {
            "target_species": "SPIDER",
            "unrelated_species": "OWL",
            "target_tasks": target_tasks,
            "unrelated_tasks": unrelated_tasks,
            "total_queued_before_claim": naive_global_scan_candidates,
        },
        "summary": {
            "scheduler_task_views": scheduler_views,
            "naive_global_scan_candidates_proxy": naive_global_scan_candidates,
            "avoided_candidate_inspections": avoided_candidate_inspections,
            "candidate_inspection_reduction_fraction": reduction_fraction,
            "structural_scan_reduction_ratio": structural_scan_reduction_ratio,
            "claimed_batch_size": lease["batch_size"],
            "exact_target_species_only": exact_target_only,
            "no_cross_species_claim": no_cross_species_claim,
            "queue_indexed": True,
            "actual_wall_clock_speedup_claim": False,
            "end_to_end_speedup_claim": False,
            "two_hundred_x_end_to_end_claim": False,
        },
        "verdict": verdict,
        "claim_scope": (
            "STRUCTURAL_CANDIDATE_INSPECTION_REDUCTION_FOR_THIS_SYNTHETIC_"
            "SPECIES_SKEW_FIXTURE_ONLY; NOT WALL_CLOCK OR END_TO_END SPEEDUP"
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
