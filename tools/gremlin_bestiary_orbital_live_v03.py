#!/usr/bin/env python3
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import time

from tools.gremlin_bestiary_live_bench_v02 import (
    SURFACE,
    _bestiary_task,
    _generalist_task,
    baseline_serial,
    canon,
    integrity,
    metrics,
    ru,
    synth,
    burn,
    workload,
)
from tools.gremlin_bestiary_orbital_scheduler_v02 import PROFILES, bounded_batch_size, service_omega

SCHEMA = "GREMLIN_BESTIARY_ORBITAL_LIVE_V0_3"


def _orbital_batch(batch):
    out = []
    for item in batch:
        routed = {role: burn(role, item)[1] for role in item["routed_roles"]}
        out.append((item["object_id"], {"roles": routed, "synth": synth(item, routed)}))
    return out


def parallel_individual(items, workers, fn):
    r0 = ru()
    t0 = time.perf_counter()
    outputs = {}
    finished = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(fn, item) for item in items]
        qdepth = len(futures)
        for fut in as_completed(futures):
            result = fut.result()
            if isinstance(result, dict):
                oid = result["object_id"]
                outputs[oid] = {"roles": result["roles"], "synth": result["synth"]}
            else:
                oid, value = result
                outputs[oid] = value
            finished.append(time.perf_counter())
    return outputs, metrics(t0, finished, r0, ru(), len(items), qdepth, workers)


def orbital_parallel(items, workers):
    counts = {role: 0 for role in PROFILES if role not in {"HUMMINGBIRD", "BELZEBUB"}}
    for item in items:
        for role in item["routed_roles"]:
            counts[role] += 1
    chunk = bounded_batch_size(counts, len(items), workers)
    batches = [items[i:i + chunk] for i in range(0, len(items), chunk)]
    r0 = ru()
    t0 = time.perf_counter()
    outputs = {}
    finished = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_orbital_batch, batch) for batch in batches]
        qdepth = len(futures)
        for fut in as_completed(futures):
            now = time.perf_counter()
            for oid, value in fut.result():
                outputs[oid] = value
                finished.append(now)
    extra = {
        "orbital_chunk_size": chunk,
        "orbital_batches": len(batches),
        "hummingbird_omega": service_omega(PROFILES["HUMMINGBIRD"]),
        "belzebub_omega": service_omega(PROFILES["BELZEBUB"]),
        "orbit_model": "omega0*tau/sqrt(mass*radius^3)",
    }
    return outputs, metrics(t0, finished, r0, ru(), len(items), qdepth, workers, extra)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=616)
    ap.add_argument("--workers", type=int, default=max(1, min(5, os.cpu_count() or 1)))
    args = ap.parse_args()

    if not SURFACE.is_dir():
        raise SystemExit("live benchmark requires /dev/shm/ciel_noema")
    status = SURFACE / "ciel_binding_status"
    if not status.is_file() or status.read_text().strip() != "ACTIVE":
        raise SystemExit("NOEMA surface binding not ACTIVE")

    items = workload(args.items, args.seed)
    raw = b"\n".join(canon(x) for x in items) + b"\n"
    raw_hash = hashlib.sha256(raw).hexdigest()
    outdir = SURFACE / "gremlin" / "bestiary_orbital_v02"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "frozen_raw.jsonl").write_bytes(raw)

    serial, sm = baseline_serial(items)
    general, gm = parallel_individual(items, args.workers, _generalist_task)
    old, om = parallel_individual(items, args.workers, _bestiary_task)
    orbital, xm = orbital_parallel(items, args.workers)
    integ = integrity(items, serial, general, old, orbital)

    receipt = {
        "schema": SCHEMA,
        "validation_scope": "LIVE_SAME_RUNTIME_GENERATION_CPU_REPLAY",
        "surface": str(SURFACE),
        "items": args.items,
        "seed": args.seed,
        "workers": args.workers,
        "frozen_raw_sha256": raw_hash,
        "legacy_serial": sm,
        "resource_matched_generalist": gm,
        "bestiary_individual": om,
        "bestiary_orbital_batched": xm,
        "speedup_orbital_vs_legacy": xm["items_per_s"] / sm["items_per_s"],
        "speedup_orbital_vs_generalist": xm["items_per_s"] / gm["items_per_s"],
        "speedup_orbital_vs_old_bestiary": xm["items_per_s"] / om["items_per_s"],
        "candidate_threshold": 10.0,
        "candidate": bool(
            xm["items_per_s"] / sm["items_per_s"] >= 10.0
            and integ["lineage_integrity"] == "PASS"
            and integ["output_equivalence"] == "PASS"
        ),
        "integrity": integ,
        "cpu_count_visible": os.cpu_count(),
    }
    receipt["receipt_sha256"] = hashlib.sha256(canon(receipt)).hexdigest()
    (outdir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
