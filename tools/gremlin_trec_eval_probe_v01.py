from __future__ import annotations

import argparse
import json
from pathlib import Path

from gremlin_mcp.trec_eval import build_trec_run, evaluate_trec


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    qrels = "\n".join(
        [
            "q1 0 d1 1",
            "q1 0 d2 1",
            "q2 0 d3 2",
            "q2 0 d4 1",
        ]
    ) + "\n"
    run = build_trec_run(
        {
            "q1": [("d1", 2.0), ("x", 1.0), ("d2", 0.5)],
            "q2": [("d3", 3.0), ("d4", 2.0)],
        },
        tag="GREMLIN_PROBE",
    )
    scored = evaluate_trec(run, qrels, cutoffs=(1, 3), ndcg_k=2)
    checks = {
        "query_count_two": scored["query_count"] == 2,
        "recall_at_1_expected": abs(scored["metrics"]["recall@1"] - 0.5) < 1e-12,
        "recall_at_3_expected": abs(scored["metrics"]["recall@3"] - 1.0) < 1e-12,
        "ndcg_bounded": 0.0 <= scored["metrics"]["ndcg@2"] <= 1.0,
        "scope_not_leaderboard_authority": "VALIDATE_AGAINST_PYSERINI" in scored["scope"],
    }
    receipt = {
        "schema": "GREMLIN_TREC_EVAL_PROBE_V0_1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "metrics": scored["metrics"],
        "reference_run": run,
        "external_dataset_executed": False,
        "leaderboard_score_claimed": False,
    }
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    if receipt["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
