from __future__ import annotations

import json
from pathlib import Path

from tools.gremlin_bestiary_phasenav_threeway_v01 import run_threeway_suite

OUT = Path("provenance/GREMLIN_BESTIARY_PHASENAV_THREEWAY_BENCHMARK_V0_1.json")


def main() -> int:
    receipt = run_threeway_suite(
        batch_size=48,
        horizon=1.6,
        coarse_steps=8,
        fine_steps=64,
        rk4_substeps=512,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt["summary"], sort_keys=True))
    print(f"receipt={OUT}")
    if not receipt["summary"]["all_species_pass"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
