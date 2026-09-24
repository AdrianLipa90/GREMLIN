from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.gremlin_same_model_ab_score_v03 import score

ROOT = Path(__file__).resolve().parents[1]
SUITE = json.loads((ROOT / "benchmarks" / "GREMLIN_EXTERNAL_SAME_MODEL_AB_TASK_SUITE_V0_3.json").read_text(encoding="utf-8"))


def _receipts() -> list[dict]:
    rows = []
    for arm in SUITE["arms"]:
        for task in SUITE["tasks"]:
            for domains in SUITE["domain_counts"]:
                for trial in range(SUITE["trials_per_task"]):
                    trace = list(task["required_tools"])
                    rows.append({
                        "arm": arm,
                        "task_id": task["task_id"],
                        "total_domains": domains,
                        "trial": trial,
                        "model": "same-model-test",
                        **SUITE["common_config"],
                        "status": "COMPLETED",
                        "result_state": task["expected_state"],
                        "tool_trace": trace,
                        "prompt_tokens": 1000 + domains * 10,
                        "completion_tokens": 50,
                        "model_calls": 1 if arm != "SUPERVISOR_SAME_MODEL" else 2,
                        "tool_calls": len(trace),
                        "wall_ms": 100 + domains,
                    })
    return rows


def test_all_pass_receipts_score_one_for_pass1_and_passk() -> None:
    result = score(SUITE, _receipts())
    assert result["status"] == "PASS_SCORED"
    assert result["canon_allowed"] is False
    for arm in SUITE["arms"]:
        assert result["arms"][arm]["pass1"] == 1.0
        assert result["arms"][arm]["pass_k"] == 1.0


def test_late_trial_failure_preserves_pass1_but_reduces_passk() -> None:
    rows = _receipts()
    victim = next(r for r in rows if r["arm"] == "MONOLITHIC_ALL_CONTEXT" and r["task_id"] == "retail_cancel_processing" and r["total_domains"] == 7 and r["trial"] == 1)
    victim["result_state"] = {"wrong": True}
    result = score(SUITE, rows)
    mono = result["arms"]["MONOLITHIC_ALL_CONTEXT"]
    assert mono["pass1"] == 1.0
    assert mono["pass_k"] < 1.0
    assert mono["mean_trial_pass_rate"] < 1.0


def test_forbidden_tool_fails_even_with_correct_final_state() -> None:
    rows = _receipts()
    victim = next(r for r in rows if r["arm"] == "GREMLIN_SELECTIVE_CONE" and r["task_id"] == "retail_refuse_shipped_cancel" and r["total_domains"] == 3 and r["trial"] == 0)
    victim["tool_trace"].append("cancel_order")
    result = score(SUITE, rows)
    workload = next(x for x in result["arms"]["GREMLIN_SELECTIVE_CONE"]["per_workload"] if x["task_id"] == "retail_refuse_shipped_cancel" and x["total_domains"] == 3)
    assert workload["pass1"] is False


def test_config_mismatch_fails_closed() -> None:
    rows = _receipts()
    rows[0]["temperature"] = 0.2
    with pytest.raises(ValueError, match="config mismatch temperature"):
        score(SUITE, rows)
