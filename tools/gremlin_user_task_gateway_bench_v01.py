from __future__ import annotations

import json
import statistics
import time

from gremlin_mcp.user_task_gateway import build_user_task_plan

CASES = [
    "What is the conceptual difference between a graph and a tree?",
    "Audit the dependency graph, benchmark the router, and find contradictions.",
    "Update the repository, run tests, commit the change and merge the branch.",
    "Research the latest evidence, compare sources and identify provenance conflicts.",
]


def main() -> None:
    rows = []
    for task in CASES:
        samples = []
        result = None
        for _ in range(20):
            t0 = time.perf_counter_ns()
            result = build_user_task_plan(task, surface_root="/definitely/missing/noema")
            samples.append((time.perf_counter_ns() - t0) / 1_000_000.0)
        rows.append({
            "task": task,
            "mode": result["mode"],
            "species": result["execution"]["route_species"],
            "median_ms": statistics.median(samples),
            "p95_ms": sorted(samples)[18],
            "graph_nodes": result["semantic_graph"]["active_nodes"],
            "graph_relations": result["semantic_graph"]["active_relations"],
        })
    print(json.dumps({
        "schema": "GREMLIN_USER_TASK_GATEWAY_BENCHMARK_V0_1",
        "status": "PASS",
        "rows": rows,
        "claim_boundary": "Routing/compilation overhead only; not answer-quality measurement.",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
