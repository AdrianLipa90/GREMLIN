import json
import random
import time
from pathlib import Path

from gremlin_mcp.holo_memory import (
    HoloMemoryIndex,
    moire_cross_term,
    weighted_phase_coherence,
)


def packet(row, *, phase=0.0, jitter=0.0, seed=0, sem=None):
    rng = random.Random(seed)
    phases, amps = [], []
    for r in range(6):
        for _ in range(6):
            phases.append(
                phase
                + (
                    rng.uniform(-jitter, jitter)
                    if r == row
                    else 0.0
                )
            )
            amps.append(1.0 if r == row else 0.0)
    return {
        "phase36": phases,
        "amplitude36": amps,
        "semantic_commitment": sem or f"s:{row}:{seed}",
    }


def score(a, b):
    return (
        0.75 * weighted_phase_coherence(a, b)
        + 0.25 * ((moire_cross_term(a, b) + 1.0) / 2.0)
    )


def main():
    idx = HoloMemoryIndex(hex_scale=12.0)
    packets = {}
    per_patch = 1000

    t0 = time.perf_counter()
    for row in range(6):
        for j in range(per_patch):
            mid = f"r{row}-{j:04d}"
            p = packet(
                row,
                phase=0.25 * row,
                jitter=0.015,
                seed=row * 100000 + j,
                sem=mid,
            )
            packets[mid] = p
            idx.add(
                memory_id=mid,
                ledger_record_id="hive:" + mid,
                packet=p,
                orbit_index=row,
                priority=0.5,
            )
    build_s = time.perf_counter() - t0

    targets = [
        f"r{row}-{j:04d}"
        for row in range(6)
        for j in (7, 113, 251, 499, 777)
    ]

    t0 = time.perf_counter()
    full_picks = []
    for target in targets:
        cue = packets[target]
        ranked = [
            (score(cue, p), mid)
            for mid, p in packets.items()
        ]
        ranked.sort(key=lambda x: (-x[0], x[1]))
        full_picks.append(ranked[0][1])
    full_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    holo = [
        idx.retrieve(
            packets[target],
            patch_radius=0,
            fallback_full=False,
        )
        for target in targets
    ]
    holo_s = time.perf_counter() - t0

    out = {
        "schema": "GREMLIN_HOLO_MEMORY_BENCHMARK_V0_1",
        "dataset": "SYNTHETIC_6_PHASE_PATCHES_6000",
        "queries": len(targets),
        "memories": len(packets),
        "build_seconds": build_s,
        "full_scan_seconds": full_s,
        "holo_scan_seconds": holo_s,
        "wallclock_speedup": (
            full_s / holo_s if holo_s else None
        ),
        "top1_agreement": sum(
            a == b
            for a, b in zip(
                full_picks,
                [x["picked"] for x in holo],
            )
        )
        / len(targets),
        "mean_fraction_evaluated": sum(
            x["fraction_evaluated"] for x in holo
        )
        / len(holo),
        "mean_candidates_evaluated": sum(
            x["evaluated"] for x in holo
        )
        / len(holo),
        "full_candidates_per_query": len(packets),
        "claim_scope": (
            "synthetic structural benchmark only; "
            "not a general semantic-recall claim"
        ),
    }
    Path(__file__).with_name(
        "GREMLIN_HOLO_MEMORY_BENCHMARK_V0_1.json"
    ).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
