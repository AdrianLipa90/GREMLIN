from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT / "benchmarks" / "GREMLIN_EXTERNAL_SAME_MODEL_AB_TASK_SUITE_V0_3.json"
Adapter = Callable[[dict[str, Any]], dict[str, Any]]


def _sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def domain_tools(suite: dict[str, Any], domain: str) -> list[str]:
    tools = set()
    for task in suite["tasks"]:
        if task["domain"] == domain:
            tools.update(task.get("required_tools", []))
            tools.update(task.get("forbidden_tools", []))
    return sorted(tools)


def distractor_tools(domain: str, n: int) -> list[str]:
    return [f"{domain}_tool_{i:02d}" for i in range(1, n + 1)]


def build_request(suite: dict[str, Any], task: dict[str, Any], *, arm: str, total_domains: int, trial: int, model: str) -> dict[str, Any]:
    if arm not in suite["arms"]:
        raise ValueError(f"unknown arm {arm}")
    if total_domains not in suite["domain_counts"]:
        raise ValueError(f"unsupported total_domains {total_domains}")
    distractor_count = total_domains - 1
    active_distractors = list(suite["distractor_domains"][:distractor_count])
    relevant_domain = task["domain"]
    relevant_tools = domain_tools(suite, relevant_domain)
    relevant_policy = list(suite["policies"][relevant_domain])

    all_domains = [relevant_domain, *active_distractors]
    all_tools = list(relevant_tools)
    for d in active_distractors:
        all_tools.extend(distractor_tools(d, int(suite["distractor_tools_per_domain"])))

    if arm == "MONOLITHIC_ALL_CONTEXT":
        surface = {
            "router_context_domains": all_domains,
            "worker_context_domains": all_domains,
            "worker_tools": all_tools,
            "worker_policy": {relevant_domain: relevant_policy, **{d:[f"Synthetic distractor policy for {d}."] for d in active_distractors}},
            "routing_semantics": "MODEL_SEES_ALL_CONTEXT_AND_TOOLS",
        }
    elif arm == "SUPERVISOR_SAME_MODEL":
        surface = {
            "router_context_domains": all_domains,
            "worker_context_domains": [relevant_domain],
            "worker_tools": relevant_tools,
            "worker_policy": {relevant_domain: relevant_policy},
            "routing_semantics": "SAME_MODEL_ROUTER_THEN_RELEVANT_SUBAGENT",
        }
    else:
        surface = {
            "router_context_domains": [relevant_domain],
            "worker_context_domains": [relevant_domain],
            "worker_tools": relevant_tools,
            "worker_policy": {relevant_domain: relevant_policy},
            "routing_semantics": "GREMLIN_CONTROL_PLANE_SELECTIVE_CONE_THEN_MODEL",
        }

    request = {
        "schema": "GREMLIN_EXTERNAL_SAME_MODEL_AB_REQUEST_V0_3",
        "task_id": task["task_id"],
        "arm": arm,
        "total_domains": total_domains,
        "trial": trial,
        "model": model,
        **suite["common_config"],
        "prompt": task["prompt"],
        "initial_state": task["initial_state"],
        "surface": surface,
        "claim_boundary": "No expected_state, required_tools, or forbidden_tools are exposed to the model adapter.",
    }
    request["request_sha256"] = _sha(request)
    return request


def _validate_adapter_result(result: dict[str, Any]) -> None:
    required = {"status", "result_state", "tool_trace", "prompt_tokens", "completion_tokens", "model_calls", "tool_calls", "wall_ms"}
    missing = sorted(required - set(result))
    if missing:
        raise ValueError(f"adapter result missing {missing}")
    if result["status"] not in {"COMPLETED", "FAILED"}:
        raise ValueError("adapter status must be COMPLETED or FAILED")
    if not isinstance(result["tool_trace"], list):
        raise ValueError("tool_trace must be list")
    for key in ("prompt_tokens", "completion_tokens", "model_calls", "tool_calls", "wall_ms"):
        value = result[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{key} must be non-negative number")


def run_suite(suite: dict[str, Any], *, adapter: Adapter, model: str) -> list[dict[str, Any]]:
    if not model:
        raise ValueError("model is required")
    receipts: list[dict[str, Any]] = []
    for arm in suite["arms"]:
        for task in suite["tasks"]:
            for total_domains in suite["domain_counts"]:
                for trial in range(int(suite["trials_per_task"])):
                    request = build_request(suite, task, arm=arm, total_domains=int(total_domains), trial=trial, model=model)
                    result = dict(adapter(request))
                    _validate_adapter_result(result)
                    receipt = {
                        "schema": "GREMLIN_EXTERNAL_SAME_MODEL_AB_RUN_RECEIPT_V0_3",
                        "task_id": task["task_id"],
                        "arm": arm,
                        "total_domains": int(total_domains),
                        "trial": trial,
                        "model": model,
                        **suite["common_config"],
                        "request_sha256": request["request_sha256"],
                        **result,
                        "canon_allowed": False,
                    }
                    receipt["receipt_sha256"] = _sha(receipt)
                    receipts.append(receipt)
    return receipts


def load_adapter(spec: str) -> Adapter:
    root = str(ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    if ":" not in spec:
        raise ValueError("adapter must be module:function")
    module_name, function_name = spec.split(":", 1)
    fn = getattr(importlib.import_module(module_name), function_name)
    if not callable(fn):
        raise TypeError("adapter target is not callable")
    return fn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--adapter", required=True, help="Python adapter module:function")
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    suite = json.loads(args.suite.read_text(encoding="utf-8"))
    receipts = run_suite(suite, adapter=load_adapter(args.adapter), model=args.model)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in receipts), encoding="utf-8")
    print(json.dumps({"status":"PASS_RUNNER_COMPLETED","receipts":len(receipts),"model":args.model}, sort_keys=True))


if __name__ == "__main__":
    main()
