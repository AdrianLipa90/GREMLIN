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
    packets, orbit_of = {}, {}
    per_bucket = 30

    t0 = time.perf_counter()
    for orbit in range(36):
        for row in range(6):
            for j in range(per_bucket):
                mid = f"o{orbit:02d}-r{row}-{j:03d}"
                p = packet(
                    row,
                    phase=0.18 * row + 0.004 * orbit,
                    jitter=0.010,
                    seed=orbit * 100000 + row * 1000 + j,
                    sem=mid,
                )
                packets[mid] = p
                orbit_of[mid] = orbit
                idx.add(
                    memory_id=mid,
                    ledger_record_id="hive:" + mid,
                    packet=p,
                    orbit_index=orbit,
                    priority=1 - orbit / 36,
                )
    build = time.perf_counter() - t0

    targets = [
        "o00-r0-007",
        "o03-r2-011",
        "o07-r5-019",
        "o12-r1-003",
        "o18-r4-027",
        "o25-r3-014",
        "o31-r0-022",
        "o35-r5-008",
    ]

    t0 = time.perf_counter()
    full = []
    for target in targets:
        cue = packets[target]
        rows = [
            (score(cue, p), mid)
            for mid, p in packets.items()
        ]
        rows.sort(key=lambda x: (-x[0], x[1]))
        full.append(rows[0][1])
    full_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    hex_only = [
        idx.retrieve(
            packets[target],
            patch_radius=0,
            fallback_full=False,
        )
        for target in targets
    ]
    hex_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    orbital = [
        idx.retrieve(
            packets[target],
            patch_radius=0,
            orbit_radius=0,
            orbit_index=orbit_of[target],
            fallback_full=False,
        )
        for target in targets
    ]
    orb_s = time.perf_counter() - t0

    out = {
        "schema": "GREMLIN_HOLO_MEMORY_ORBITAL_BENCHMARK_V0_1",
        "dataset": "SYNTHETIC_36_ORBITS_X_6_HEX_PATCHES",
        "memories": len(packets),
        "queries": len(targets),
        "build_seconds": build,
        "full_scan_seconds": full_s,
        "hex_only_seconds": hex_s,
        "hex_orbital_seconds": orb_s,
        "hex_speedup": full_s / hex_s,
        "hex_orbital_speedup": full_s / orb_s,
        "hex_top1_agreement": sum(
            x["picked"] == y
            for x, y in zip(hex_only, full)
        )
        / len(full),
        "hex_orbital_top1_agreement": sum(
            x["picked"] == y
            for x, y in zip(orbital, full)
        )
        / len(full),
        "hex_mean_evaluated": sum(
            x["evaluated"] for x in hex_only
        )
        / len(hex_only),
        "hex_orbital_mean_evaluated": sum(
            x["evaluated"] for x in orbital
        )
        / len(orbital),
        "hex_orbital_fraction_evaluated": sum(
            x["fraction_evaluated"] for x in orbital
        )
        / len(orbital),
        "claim_scope": (
            "synthetic structural benchmark; orbit coordinate "
            "supplied by caller; no general semantic-recall claim"
        ),
    }
    Path(__file__).with_name(
        "GREMLIN_HOLO_MEMORY_ORBITAL_BENCHMARK_V0_1.json"
    ).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
