from __future__ import annotations

import argparse
import json
from pathlib import Path

from gremlin_mcp.external_eval import (
    aggregate_browsecomp_plus,
    build_browsecomp_plus_run,
    score_browsecomp_plus_run,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    fixtures = [
        (
            build_browsecomp_plus_run(
                query_id="fixture-1",
                output_text="Candidate answer [101, 102].",
                retrieved_docids=[101, 102, 103],
                tool_call_counts={"search": 2, "fetch": 3},
                metadata={"fixture": True},
            ),
            ["101", "102", "104"],
        ),
        (
            build_browsecomp_plus_run(
                query_id="fixture-2",
                output_text="Candidate answer 【201】.",
                retrieved_docids=[201, 202],
                tool_call_counts={"search": 1, "fetch": 2},
                metadata={"fixture": True},
            ),
            ["201", "203"],
        ),
    ]
    scores = [score_browsecomp_plus_run(run, relevant_docids=qrels) for run, qrels in fixtures]
    aggregate = aggregate_browsecomp_plus(scores)
    checks = {
        "two_fixture_queries": aggregate["query_count"] == 2,
        "completion_rate_one": aggregate["completion_rate"] == 1.0,
        "retrieval_metric_present": aggregate["mean_retrieval_recall"] > 0.0,
        "citation_precision_present": aggregate["mean_citation_precision"] > 0.0,
        "external_answer_judge_preserved": aggregate["answer_accuracy"] is None,
        "external_answer_judge_status": aggregate["answer_accuracy_status"] == "EXTERNAL_SEMANTIC_JUDGE_REQUIRED",
    }
    receipt = {
        "schema": "GREMLIN_EXTERNAL_RESEARCH_EVAL_PROBE_V0_1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "mode": "SYNTHETIC_CONTRACT_FIXTURES_ONLY",
        "checks": checks,
        "aggregate": aggregate,
        "scores": scores,
        "external_dataset_executed": False,
        "external_answer_judge_executed": False,
    }
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    if receipt["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
