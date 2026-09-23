from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT / "benchmarks" / "GREMLIN_EXTERNAL_SAME_MODEL_AB_TASK_SUITE_V0_3.json"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"line {line_no}: object required")
        rows.append(row)
    return rows


def workload_keys(suite: dict[str, Any]) -> list[tuple[str, int]]:
    return [(task["task_id"], int(domains)) for task in suite["tasks"] for domains in suite["domain_counts"]]


def validate_common_config(suite: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("no receipts")
    model_values = {str(r.get("model")) for r in rows}
    if len(model_values) != 1 or "None" in model_values:
        raise ValueError("all receipts must use exactly one non-null model")
    expected = suite["common_config"]
    for r in rows:
        for key, value in expected.items():
            if r.get(key) != value:
                raise ValueError(f"config mismatch {key}: {r.get(key)!r} != {value!r}")
    return {"model": next(iter(model_values)), **expected}


def score_receipt(task: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    trace = [str(x) for x in receipt.get("tool_trace", [])]
    state_ok = receipt.get("result_state") == task["expected_state"]
    required_ok = all(tool in trace for tool in task.get("required_tools", []))
    forbidden_ok = all(tool not in trace for tool in task.get("forbidden_tools", []))
    runtime_ok = receipt.get("status") == "COMPLETED"
    passed = bool(state_ok and required_ok and forbidden_ok and runtime_ok)
    return {
        "pass": passed,
        "state_ok": state_ok,
        "required_tools_ok": required_ok,
        "forbidden_tools_ok": forbidden_ok,
        "runtime_ok": runtime_ok,
    }


def _pctile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    idx = min(len(xs)-1, max(0, math.ceil(q * len(xs)) - 1))
    return float(xs[idx])


def score(suite: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    config = validate_common_config(suite, rows)
    task_by_id = {t["task_id"]: t for t in suite["tasks"]}
    arms = list(suite["arms"])
    expected_trials = int(suite["trials_per_task"])
    expected_keys = set(workload_keys(suite))

    grouped: dict[str, dict[tuple[str, int], dict[int, dict[str, Any]]]] = {
        arm: defaultdict(dict) for arm in arms
    }
    unknown_arms = set()
    for r in rows:
        arm = r.get("arm")
        if arm not in grouped:
            unknown_arms.add(str(arm))
            continue
        key = (str(r.get("task_id")), int(r.get("total_domains")))
        if key not in expected_keys:
            raise ValueError(f"unexpected workload key {key}")
        trial = int(r.get("trial"))
        if trial in grouped[arm][key]:
            raise ValueError(f"duplicate receipt {arm} {key} trial={trial}")
        grouped[arm][key][trial] = r
    if unknown_arms:
        raise ValueError(f"unknown arms: {sorted(unknown_arms)}")

    results: dict[str, Any] = {}
    for arm in arms:
        flat_scored: list[tuple[dict[str, Any], dict[str, Any]]] = []
        per_workload = []
        for key in sorted(expected_keys):
            task_id, total_domains = key
            trials = grouped[arm].get(key, {})
            missing = [i for i in range(expected_trials) if i not in trials]
            if missing:
                raise ValueError(f"missing trials for {arm} {key}: {missing}")
            scores = []
            for trial in range(expected_trials):
                receipt = trials[trial]
                s = score_receipt(task_by_id[task_id], receipt)
                scores.append(s)
                flat_scored.append((receipt, s))
            per_workload.append({
                "task_id": task_id,
                "total_domains": total_domains,
                "pass1": bool(scores[0]["pass"]),
                "pass_k": bool(all(s["pass"] for s in scores)),
                "trial_pass_rate": sum(int(s["pass"]) for s in scores) / expected_trials,
            })

        receipts = [x[0] for x in flat_scored]
        pass1 = [x for x in per_workload if x["pass1"]]
        passk = [x for x in per_workload if x["pass_k"]]
        prompt_tokens = [float(r["prompt_tokens"]) for r in receipts]
        completion_tokens = [float(r["completion_tokens"]) for r in receipts]
        wall = [float(r["wall_ms"]) for r in receipts]
        model_calls = [float(r["model_calls"]) for r in receipts]
        tool_calls = [float(r["tool_calls"]) for r in receipts]
        results[arm] = {
            "workload_count": len(per_workload),
            "trial_count": len(receipts),
            "pass1": len(pass1) / len(per_workload),
            "pass_k": len(passk) / len(per_workload),
            "mean_trial_pass_rate": statistics.fmean(x["trial_pass_rate"] for x in per_workload),
            "tokens": {
                "mean_prompt": statistics.fmean(prompt_tokens),
                "mean_completion": statistics.fmean(completion_tokens),
                "mean_total": statistics.fmean(a+b for a,b in zip(prompt_tokens, completion_tokens)),
            },
            "calls": {
                "mean_model": statistics.fmean(model_calls),
                "mean_tool": statistics.fmean(tool_calls),
            },
            "wall_ms": {
                "median": statistics.median(wall),
                "p95": _pctile(wall, 0.95),
            },
            "per_workload": per_workload,
        }

    return {
        "schema": "GREMLIN_EXTERNAL_SAME_MODEL_AB_SCORE_V0_3",
        "status": "PASS_SCORED",
        "canon_allowed": False,
        "common_config": config,
        "suite_schema": suite["schema"],
        "trials_per_task": expected_trials,
        "arms": results,
        "claim_boundary": "Scoring only. The harness does not infer a winner and does not create receipts for models that were not actually executed.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    suite = json.loads(args.suite.read_text(encoding="utf-8"))
    result = score(suite, load_jsonl(args.receipts))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "model": result["common_config"]["model"]}, sort_keys=True))


if __name__ == "__main__":
    main()
