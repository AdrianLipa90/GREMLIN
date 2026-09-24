from __future__ import annotations

import json
from pathlib import Path

from tools.gremlin_same_model_ab_runner_v03 import build_request, run_suite

ROOT = Path(__file__).resolve().parents[1]
SUITE = json.loads((ROOT / "benchmarks" / "GREMLIN_EXTERNAL_SAME_MODEL_AB_TASK_SUITE_V0_3.json").read_text(encoding="utf-8"))
TASKS = {t["task_id"]: t for t in SUITE["tasks"]}


def perfect_mock_adapter(request: dict) -> dict:
    task = TASKS[request["task_id"]]
    calls = 2 if request["arm"] == "SUPERVISOR_SAME_MODEL" else 1
    return {
        "status": "COMPLETED",
        "result_state": task["expected_state"],
        "tool_trace": list(task["required_tools"]),
        "prompt_tokens": 1000 + 10 * request["total_domains"],
        "completion_tokens": 50,
        "model_calls": calls,
        "tool_calls": len(task["required_tools"]),
        "wall_ms": 100 + request["total_domains"],
    }


def _contains_exact_object(node, target) -> bool:
    if node == target:
        return True
    if isinstance(node, dict):
        return any(_contains_exact_object(v, target) for v in node.values())
    if isinstance(node, list):
        return any(_contains_exact_object(v, target) for v in node)
    return False


def test_request_never_leaks_scoring_oracle() -> None:
    task = SUITE["tasks"][0]
    req = build_request(SUITE, task, arm="MONOLITHIC_ALL_CONTEXT", total_domains=7, trial=0, model="same-model-test")
    assert "expected_state" not in req
    assert "required_tools" not in req
    assert "forbidden_tools" not in req
    assert not _contains_exact_object(req, task["expected_state"])


def test_monolithic_surface_exposes_distractors_but_selective_cone_does_not() -> None:
    task = SUITE["tasks"][0]
    mono = build_request(SUITE, task, arm="MONOLITHIC_ALL_CONTEXT", total_domains=7, trial=0, model="same-model-test")
    gremlin = build_request(SUITE, task, arm="GREMLIN_SELECTIVE_CONE", total_domains=7, trial=0, model="same-model-test")
    assert len(mono["surface"]["router_context_domains"]) == 7
    assert len(gremlin["surface"]["router_context_domains"]) == 1
    assert len(mono["surface"]["worker_tools"]) > len(gremlin["surface"]["worker_tools"])
    assert len(mono["surface"]["worker_tools"]) - len(gremlin["surface"]["worker_tools"]) == 6 * 19


def test_runner_generates_complete_432_receipts() -> None:
    receipts = run_suite(SUITE, adapter=perfect_mock_adapter, model="same-model-test")
    assert len(receipts) == 432
    assert {r["arm"] for r in receipts} == set(SUITE["arms"])
    assert all(r["canon_allowed"] is False for r in receipts)
    assert len({r["receipt_sha256"] for r in receipts}) == 432


def test_runner_keeps_exact_model_identifier_across_arms() -> None:
    receipts = run_suite(SUITE, adapter=perfect_mock_adapter, model="same-model-test")
    assert {r["model"] for r in receipts} == {"same-model-test"}
