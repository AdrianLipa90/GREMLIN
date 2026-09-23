from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gremlin_mcp.orchorbital_fabric import OrchorbitalFabric

SCHEMA = "GREMLIN_ORCHORBITAL_SYSTEMS_OVERHEAD_V0_1"
VERSION = "0.1.0"
TOPOLOGIES = ("chain", "wide", "diamond", "layered")
SIZES = (10, 50, 200)
DEFAULT_WARMUPS = 2
DEFAULT_SAMPLES = 9
_SHA40 = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class TopologyPlan:
    topology: str
    node_ids: tuple[str, ...]
    causal_edges: tuple[tuple[str, str], ...]
    close_order: tuple[str, ...]


def _node_ids(n: int) -> tuple[str, ...]:
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be integer >= 2")
    return tuple(f"N{i:04d}" for i in range(n))


def topology_plan(topology: str, n: int) -> TopologyPlan:
    if topology not in TOPOLOGIES:
        raise ValueError(f"unsupported topology: {topology}")
    ids = _node_ids(n)
    edges: list[tuple[str, str]] = []

    if topology == "chain":
        for i in range(1, n):
            edges.append((ids[i], ids[i - 1]))
        order = ids
    elif topology == "wide":
        hub = ids[0]
        for node_id in ids[1:]:
            edges.append((node_id, hub))
        order = ids
    elif topology == "diamond":
        source, sink = ids[0], ids[-1]
        middles = ids[1:-1]
        for node_id in middles:
            edges.append((node_id, source))
            edges.append((sink, node_id))
        order = (source, *middles, sink)
    else:
        width = max(2, int(math.sqrt(n)))
        layers: list[tuple[str, ...]] = []
        cursor = 0
        while cursor < n:
            layers.append(ids[cursor : min(n, cursor + width)])
            cursor += width
        for prev, cur in zip(layers, layers[1:]):
            for index, node_id in enumerate(cur):
                edges.append((node_id, prev[index % len(prev)]))
        order = tuple(node for layer in layers for node in layer)

    return TopologyPlan(topology, ids, tuple(edges), tuple(order))


def _build(plan: TopologyPlan) -> OrchorbitalFabric:
    fabric = OrchorbitalFabric(max_nodes=len(plan.node_ids) + 1)
    species = ("SPIDER", "OWL", "MOLE", "HOUND", "ANT", "MANTIS")
    for i, node_id in enumerate(plan.node_ids):
        fabric.spawn(
            "AUTH:ROOT",
            species[i % len(species)],
            node_id=node_id,
            obligations=(f"noop:{i}",),
            join_to_caller=False,
        )
    for consumer, dependency in plan.causal_edges:
        fabric.add_causal_dependency(consumer, dependency)
    return fabric


def _state_transition_run(fabric: OrchorbitalFabric, plan: TopologyPlan) -> None:
    for index, node_id in enumerate(plan.close_order):
        fabric.mark_started(node_id)
        fabric.mark_self_complete(node_id, result_commitment=f"noop-result-{index}")
        fabric.close(node_id)
    if fabric.receipt()["open_node_count"] != 1:
        raise RuntimeError("all workload nodes must be closed after state-transition run")


def _measure_ns(fn) -> tuple[int, Any]:
    t0 = time.perf_counter_ns()
    value = fn()
    return time.perf_counter_ns() - t0, value


def _summary(samples_ns: list[int]) -> dict[str, float]:
    if not samples_ns:
        raise ValueError("samples required")
    ordered = sorted(samples_ns)
    p95_index = min(len(ordered) - 1, max(0, math.ceil(0.95 * len(ordered)) - 1))
    return {
        "median_ms": statistics.median(samples_ns) / 1_000_000.0,
        "mean_ms": statistics.fmean(samples_ns) / 1_000_000.0,
        "stdev_ms": (statistics.stdev(samples_ns) if len(samples_ns) > 1 else 0.0) / 1_000_000.0,
        "p95_ms": ordered[p95_index] / 1_000_000.0,
        "min_ms": ordered[0] / 1_000_000.0,
        "max_ms": ordered[-1] / 1_000_000.0,
    }


def _one_sample(plan: TopologyPlan) -> dict[str, Any]:
    build_ns, fabric = _measure_ns(lambda: _build(plan))
    build_receipt = fabric.receipt()
    if build_receipt["node_count"] != len(plan.node_ids) + 1:
        raise RuntimeError("node count mismatch after build")
    if build_receipt["causal_edge_count"] != len(plan.causal_edges):
        raise RuntimeError("causal edge count mismatch after build")

    snapshot_ns, snapshot = _measure_ns(lambda: fabric.topology_snapshot(include_obligations=False))
    commitment_ns, commitment = _measure_ns(fabric.topology_commitment)
    checkpoint_ns, checkpoint = _measure_ns(fabric.checkpoint_state)
    restore_ns, restored = _measure_ns(lambda: OrchorbitalFabric.from_checkpoint(checkpoint))
    if restored.topology_commitment() != commitment:
        raise RuntimeError("restore topology commitment mismatch")
    run_ns, _ = _measure_ns(lambda: _state_transition_run(fabric, plan))

    return {
        "build_ns": build_ns,
        "snapshot_ns": snapshot_ns,
        "commitment_ns": commitment_ns,
        "checkpoint_ns": checkpoint_ns,
        "restore_ns": restore_ns,
        "state_transition_run_ns": run_ns,
        "topology_commitment": commitment,
        "snapshot_node_count": len(snapshot["nodes"]),
    }


def benchmark_cell(topology: str, n: int, *, warmups: int, samples: int) -> dict[str, Any]:
    if warmups < 0 or samples < 1:
        raise ValueError("warmups must be >=0 and samples >=1")
    plan = topology_plan(topology, n)
    for _ in range(warmups):
        _one_sample(plan)
    raw = [_one_sample(plan) for _ in range(samples)]

    commitments = {row["topology_commitment"] for row in raw}
    if len(commitments) != 1:
        raise RuntimeError("topology commitment changed between deterministic samples")

    phases = {}
    for key in (
        "build_ns",
        "snapshot_ns",
        "commitment_ns",
        "checkpoint_ns",
        "restore_ns",
        "state_transition_run_ns",
    ):
        phase = key.removesuffix("_ns")
        values = [int(row[key]) for row in raw]
        phases[phase] = {**_summary(values), "raw_ns": values}

    return {
        "topology": topology,
        "workload_nodes": n,
        "authority_root_excluded_from_workload_node_count": True,
        "causal_edges": len(plan.causal_edges),
        "warmups": warmups,
        "samples": samples,
        "topology_commitment": next(iter(commitments)),
        "phases": phases,
        "model_calls": 0,
        "network_calls": 0,
        "tool_io_calls": 0,
        "invariant_checks_enabled": True,
        "status": "PASS",
    }


def run_benchmark(
    *,
    commit_sha: str,
    warmups: int = DEFAULT_WARMUPS,
    samples: int = DEFAULT_SAMPLES,
) -> dict[str, Any]:
    if not _SHA40.fullmatch(commit_sha):
        raise ValueError("commit_sha must be lowercase 40-char SHA")

    cells = [
        benchmark_cell(topology, n, warmups=warmups, samples=samples)
        for topology in TOPOLOGIES
        for n in SIZES
    ]
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "PASS_EXECUTED",
        "commit_sha": commit_sha,
        "environment": {
            "python": sys.version,
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "matrix": {"topologies": list(TOPOLOGIES), "sizes": list(SIZES)},
        "cells": cells,
        "claim_boundary": "Pure OrchorbitalFabric systems overhead with no LLM, network, or external tool I/O. External comparisons require phase/topology/size alignment.",
        "canon_allowed": False,
    }
    encoded = json.dumps(
        core,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    core["receipt_sha256"] = hashlib.sha256(encoded).hexdigest()
    return core


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--commit-sha", required=True)
    p.add_argument("--warmups", type=int, default=DEFAULT_WARMUPS)
    p.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = run_benchmark(
        commit_sha=a.commit_sha,
        warmups=a.warmups,
        samples=a.samples,
    )
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "cells": len(result["cells"]),
                "receipt_sha256": result["receipt_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
