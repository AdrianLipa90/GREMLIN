from __future__ import annotations

import json
import math
import random
from statistics import mean

from gremlin_mcp.holographic_orbital_memory import (
    DIM,
    HolographicOrbitalIndex,
    moire_overlap,
    phase_rms_distance,
)


def _run_profile(records, labels, bases, *, hex_scale, min_candidates, seed, queries_per_cluster):
    rng = random.Random(seed + 1000)
    index = HolographicOrbitalIndex.remap(records, hex_scale=hex_scale)
    cluster_hits = []
    exact_hits = []
    candidate_counts = []
    reductions = []
    for c, base in enumerate(bases):
        for _ in range(queries_per_cluster):
            query = tuple((x + rng.gauss(0.0, 0.22)) % (2 * math.pi) for x in base)
            result = index.retrieve(query, min_candidates=min_candidates, max_hex_ring=3, orbit_radius=1)
            baseline = min(
                records,
                key=lambda rid: (-moire_overlap(query, records[rid]), phase_rms_distance(query, records[rid]), rid),
            )
            cluster_hits.append(labels[result.record_id] == c)
            exact_hits.append(result.record_id == baseline)
            candidate_counts.append(result.candidate_count)
            reductions.append(result.comparison_reduction)
    return {
        "hex_scale": hex_scale,
        "min_candidates": min_candidates,
        "cluster_recall_at_1": sum(cluster_hits) / len(cluster_hits),
        "exact_full_scan_top1_match": sum(exact_hits) / len(exact_hits),
        "average_candidate_count": mean(candidate_counts),
        "average_comparison_reduction": mean(reductions),
        "mapping_commitment": index.mapping_commitment(),
    }


def run(seed: int = 17, clusters: int = 12, per_cluster: int = 64, queries_per_cluster: int = 8) -> dict:
    rng = random.Random(seed)
    bases = [tuple(rng.random() * 2 * math.pi for _ in range(DIM)) for _ in range(clusters)]
    records = {}
    labels = {}
    for c, base in enumerate(bases):
        for j in range(per_cluster):
            rid = f"c{c}:{j}"
            records[rid] = tuple((x + rng.gauss(0.0, 0.18)) % (2 * math.pi) for x in base)
            labels[rid] = c

    return {
        "schema": "GREMLIN_HOLOGRAPHIC_ORBITAL_MEMORY_BENCHMARK_V0_1",
        "scope": "DETERMINISTIC_SYNTHETIC_REFERENCE_ONLY",
        "seed": seed,
        "records": len(records),
        "queries_per_profile": clusters * queries_per_cluster,
        "profiles": {
            "BALANCED": _run_profile(
                records, labels, bases,
                hex_scale=12.0, min_candidates=16,
                seed=seed, queries_per_cluster=queries_per_cluster,
            ),
            "AGGRESSIVE": _run_profile(
                records, labels, bases,
                hex_scale=16.0, min_candidates=12,
                seed=seed, queries_per_cluster=queries_per_cluster,
            ),
        },
        "authority": {
            "production_claim": False,
            "universal_speedup_claim": False,
            "ledger_mutated": False,
        },
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
