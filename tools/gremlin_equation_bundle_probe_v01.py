from __future__ import annotations

import argparse
import json
from pathlib import Path

from gremlin_mcp.equation_bundle import run_equation_witness_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    bundle_path = Path(args.bundle)
    out_path = Path(args.out)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    result = run_equation_witness_bundle(bundle)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "bundle_id": result["bundle_id"],
        "classification": result["classification"],
        "witness_count": result["witness_count"],
        "pass_count": result["pass_count"],
        "fail_count": result["fail_count"],
        "unresolved_count": result["unresolved_count"],
        "detected_issue_ids": result["detected_issue_ids"],
        "bundle_commitment": result["bundle_commitment"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
