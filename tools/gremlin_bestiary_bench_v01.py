#!/usr/bin/env python3
"""Deterministic virtual-service benchmark for GREMLIN Bestiary v0.1.

This benchmark measures scheduler/service topology only. It does not claim a
live wall-clock runtime speedup. The baseline is a monolithic generalist that
runs every specialist transform for every input. The Bestiary performs fast
capture, routing, bounded specialist fanout, then defensive synthesis.
"""
from __future__ import annotations

from dataclasses import dataclass
import argparse
import heapq
import json
import random
from typing import Iterable

SEED = 616
CAPTURE_COST = 0.05
ROUTER_COST = 0.08
ROLE_COST = {
    "SPIDER": 1.2,
    "RAVEN": 0.9,
    "HOUND": 1.0,
    "MOLE": 1.6,
    "OWL": 1.1,
    "ANT": 0.8,
    "MANTIS": 0.7,
    "BELZEBUB": 1.3,
}
SPECIALISTS = tuple(k for k in ROLE_COST if k != "BELZEBUB")
DEFAULT_WORKERS = {
    "HUMMINGBIRD": 1,
    "OCTOPUS": 1,
    "SPIDER": 1,
    "RAVEN": 1,
    "HOUND": 1,
    "MOLE": 2,
    "OWL": 1,
    "ANT": 1,
    "MANTIS": 1,
    "BELZEBUB": 2,
}


@dataclass(frozen=True)
class Item:
    all_costs: dict[str, float]
    merge_cost: float
    routed_roles: tuple[str, ...]


def make_workload(count: int, seed: int = SEED) -> tuple[Item, ...]:
    if count <= 0:
        raise ValueError("count must be positive")
    rng = random.Random(int(seed))
    out = []
    for _ in range(int(count)):
        all_costs = {
            role: ROLE_COST[role] * (0.75 + 0.50 * rng.random())
            for role in SPECIALISTS
        }
        merge_cost = ROLE_COST["BELZEBUB"] * (0.75 + 0.50 * rng.random())
        k = rng.choice((3, 3, 4, 4, 4, 5))
        routed = tuple(sorted(rng.sample(SPECIALISTS, k)))
        out.append(Item(all_costs, merge_cost, routed))
    return tuple(out)


def baseline_serial_cost(items: Iterable[Item]) -> float:
    """Generalist cost: every item traverses every specialist transform."""
    total = 0.0
    for item in items:
        total += CAPTURE_COST + ROUTER_COST
        total += sum(item.all_costs.values())
        total += item.merge_cost
    return total


def _schedule_pool(jobs: list[tuple[float, float, int]], workers: int) -> tuple[dict[int, float], float]:
    n = int(workers)
    if n <= 0:
        raise ValueError("worker count must be positive")
    available = [0.0] * n
    heapq.heapify(available)
    finish: dict[int, float] = {}
    for ready, duration, item_id in sorted(jobs, key=lambda x: (x[0], x[2])):
        free = heapq.heappop(available)
        done = max(float(ready), free) + float(duration)
        heapq.heappush(available, done)
        finish[int(item_id)] = done
    return finish, max(available, default=0.0)


def bestiary_makespan(items: tuple[Item, ...], workers: dict[str, int] | None = None) -> float:
    cfg = dict(DEFAULT_WORKERS if workers is None else workers)
    for role in ("HUMMINGBIRD", "OCTOPUS", *SPECIALISTS, "BELZEBUB"):
        if int(cfg.get(role, 0)) <= 0:
            raise ValueError(f"missing positive worker count for {role}")

    capture_jobs = [(0.0, CAPTURE_COST, i) for i in range(len(items))]
    capture_done, _ = _schedule_pool(capture_jobs, cfg["HUMMINGBIRD"])

    route_jobs = [(capture_done[i], ROUTER_COST, i) for i in range(len(items))]
    route_done, _ = _schedule_pool(route_jobs, cfg["OCTOPUS"])

    specialist_done: dict[str, dict[int, float]] = {}
    for role in SPECIALISTS:
        jobs = [
            (route_done[i], item.all_costs[role], i)
            for i, item in enumerate(items)
            if role in item.routed_roles
        ]
        specialist_done[role], _ = _schedule_pool(jobs, cfg[role])

    merge_jobs = []
    for i, item in enumerate(items):
        ready = max(
            [route_done[i]] + [specialist_done[role][i] for role in item.routed_roles]
        )
        merge_jobs.append((ready, item.merge_cost, i))
    _, makespan = _schedule_pool(merge_jobs, cfg["BELZEBUB"])
    return makespan


def run(count: int = 10_000, seed: int = SEED, workers: dict[str, int] | None = None) -> dict:
    items = make_workload(count, seed)
    baseline = baseline_serial_cost(items)
    makespan = bestiary_makespan(items, workers)
    speedup = baseline / makespan
    return {
        "schema": "GREMLIN_BESTIARY_THROUGHPUT_BENCH_V0_1",
        "validation_scope": "DETERMINISTIC_VIRTUAL_SERVICE_TOPOLOGY_ONLY",
        "items": int(count),
        "seed": int(seed),
        "baseline_serial_service_units": baseline,
        "bestiary_makespan_service_units": makespan,
        "throughput_speedup": speedup,
        "candidate_threshold": 10.0,
        "candidate": speedup >= 10.0,
        "workers": dict(DEFAULT_WORKERS if workers is None else workers),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    print(json.dumps(run(args.items, args.seed), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
