from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SCHEMA = "GREMLIN_TAU2_NATIVE_RECEIPT_V0_1"
VERSION = "0.1.1"
PINNED_TAU2_COMMIT = "b7ea9074c1cba482b30687fecdb5c8425fd6f619"
INFRASTRUCTURE_ERROR = "infrastructure_error"
SUCCESS_TOLERANCE = 1e-6


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top-level JSON object required")
    return value


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _discover(
    input_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[Path]]:
    path = input_path.resolve()
    if path.is_dir():
        metadata_path = path / "results.json"
        sims_dir = path / "simulations"
    else:
        metadata_path = path
        sims_dir = path.parent / "simulations"

    if not metadata_path.is_file():
        raise FileNotFoundError(metadata_path)
    metadata = _load_json(metadata_path)
    inline = metadata.get("simulations")

    files = [metadata_path]
    if isinstance(inline, list) and inline:
        simulations = inline
    elif sims_dir.is_dir():
        sim_files = sorted(sims_dir.glob("*.json"))
        if not sim_files:
            raise ValueError("directory-format results contain no simulation files")
        simulations = [_load_json(p) for p in sim_files]
        files.extend(sim_files)
    elif isinstance(inline, list):
        simulations = inline
    else:
        raise ValueError(
            "results JSON has no simulations list and no simulations directory"
        )

    if not simulations:
        raise ValueError("no simulations found")
    if not all(isinstance(row, dict) for row in simulations):
        raise ValueError("simulation entries must be JSON objects")
    return metadata, simulations, files


def _source_binding(files: list[Path], root: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(files):
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            rel = path.name
        rows.append({"path": rel, "sha256": _sha256_file(path)})
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "file_count": len(rows),
        "files": rows,
        "aggregate_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _reward(sim: dict[str, Any]) -> float:
    info = sim.get("reward_info")
    if not isinstance(info, dict):
        raise ValueError(f"simulation {sim.get('id')!r} missing reward_info")
    value = info.get("reward")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"simulation {sim.get('id')!r} reward must be numeric"
        )
    out = float(value)
    if not math.isfinite(out) or not 0.0 <= out <= 1.0:
        raise ValueError(
            f"simulation {sim.get('id')!r} reward must be finite in [0,1]"
        )
    return out


def _is_successful(reward: float) -> bool:
    # Mirrors tau2.metrics.agent_metrics.is_successful at the pinned commit.
    return (1.0 - SUCCESS_TOLERANCE) <= reward <= (1.0 + SUCCESS_TOLERANCE)


def _pass_hat_k(num_trials: int, success_count: int, k: int) -> float:
    # Mirrors tau2.metrics.agent_metrics.pass_hat_k at the pinned commit.
    if num_trials < k:
        raise ValueError(
            f"Number of trials {num_trials} is less than k {k}."
        )
    return math.comb(success_count, k) / math.comb(num_trials, k)


def _finite_optional(value: Any, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric or null")
    out = float(value)
    if not math.isfinite(out) or out < 0:
        raise ValueError(f"{field} must be finite and non-negative")
    return out


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    index = min(len(xs) - 1, max(0, math.ceil(0.95 * len(xs)) - 1))
    return xs[index]


def import_tau2_results(
    input_path: Path,
    *,
    expected_tau2_commit: str = PINNED_TAU2_COMMIT,
    expected_model: str | None = None,
    expected_num_trials: int | None = None,
    gremlin_commit_sha: str | None = None,
) -> dict[str, Any]:
    if len(expected_tau2_commit) != 40 or any(
        c not in "0123456789abcdef" for c in expected_tau2_commit
    ):
        raise ValueError("expected_tau2_commit must be lowercase 40-char SHA")
    if gremlin_commit_sha is not None and (
        len(gremlin_commit_sha) != 40
        or any(c not in "0123456789abcdef" for c in gremlin_commit_sha)
    ):
        raise ValueError(
            "gremlin_commit_sha must be lowercase 40-char SHA or null"
        )

    metadata, simulations, files = _discover(input_path)
    info = metadata.get("info")
    if not isinstance(info, dict):
        raise ValueError("results metadata missing info")

    tau2_commit = info.get("git_commit")
    if tau2_commit != expected_tau2_commit:
        raise RuntimeError(
            f"tau2 commit mismatch: expected={expected_tau2_commit} "
            f"actual={tau2_commit}"
        )

    agent_info = info.get("agent_info")
    env_info = info.get("environment_info")
    user_info = info.get("user_info")
    if not isinstance(agent_info, dict) or not isinstance(env_info, dict):
        raise ValueError(
            "results info missing agent_info/environment_info"
        )
    if not isinstance(user_info, dict):
        raise ValueError("results info missing user_info")

    model = agent_info.get("llm")
    if not isinstance(model, str) or not model:
        raise ValueError("agent model identifier missing")
    if expected_model is not None and model != expected_model:
        raise RuntimeError(
            f"agent model mismatch: expected={expected_model} actual={model}"
        )

    num_trials = info.get("num_trials")
    if (
        isinstance(num_trials, bool)
        or not isinstance(num_trials, int)
        or num_trials < 1
    ):
        raise ValueError("info.num_trials must be positive integer")
    if expected_num_trials is not None and num_trials != expected_num_trials:
        raise RuntimeError(
            f"num_trials mismatch: expected={expected_num_trials} "
            f"actual={num_trials}"
        )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    raw_reward_values: list[float] = []
    raw_durations: list[float] = []
    termination = Counter()

    for sim in simulations:
        task_id = sim.get("task_id")
        if task_id is None:
            raise ValueError("simulation missing task_id")
        trial = sim.get("trial")
        if isinstance(trial, bool) or not isinstance(trial, int):
            raise ValueError(
                f"simulation {sim.get('id')!r} trial must be integer"
            )
        reward = _reward(sim)
        duration = _finite_optional(sim.get("duration"), "duration")
        if duration is None:
            raise ValueError("duration cannot be null")
        agent_cost = _finite_optional(sim.get("agent_cost"), "agent_cost")
        user_cost = _finite_optional(sim.get("user_cost"), "user_cost")
        term = sim.get("termination_reason")
        if not isinstance(term, str) or not term:
            raise ValueError("termination_reason must be non-empty string")

        row = {
            "simulation_id": sim.get("id"),
            "task_id": str(task_id),
            "trial": trial,
            "reward": reward,
            "termination_reason": term,
            "duration_s": duration,
            "agent_cost": agent_cost,
            "user_cost": user_cost,
        }
        grouped[str(task_id)].append(row)
        raw_reward_values.append(reward)
        raw_durations.append(duration)
        termination[term] += 1

    task_rows = []
    expected_trials = list(range(num_trials))
    evaluated_flat: list[dict[str, Any]] = []
    for task_id, rows in sorted(grouped.items()):
        rows = sorted(rows, key=lambda x: x["trial"])
        trials = [r["trial"] for r in rows]
        if len(rows) != num_trials:
            raise RuntimeError(
                f"task {task_id} has {len(rows)} simulations; "
                f"expected {num_trials}"
            )
        if trials != expected_trials:
            raise RuntimeError(
                f"task {task_id} trial identifiers must equal "
                f"{expected_trials}; actual={trials}"
            )

        rewards = [r["reward"] for r in rows]
        ordered_prefix = {
            f"first_{k}_all_success": all(
                _is_successful(value) for value in rewards[:k]
            )
            for k in range(1, num_trials + 1)
        }
        evaluated = [
            r for r in rows
            if r["termination_reason"] != INFRASTRUCTURE_ERROR
        ]
        evaluated_flat.extend(evaluated)
        success_count = sum(
            int(_is_successful(r["reward"])) for r in evaluated
        )
        task_rows.append(
            {
                "task_id": task_id,
                "trials": trials,
                "rewards": rewards,
                "evaluated_trial_count": len(evaluated),
                "success_count": success_count,
                "ordered_prefix_all_success_diagnostic": ordered_prefix,
            }
        )

    eligible_tasks = [
        row for row in task_rows if row["evaluated_trial_count"] > 0
    ]
    if eligible_tasks:
        max_k = min(
            num_trials,
            min(row["evaluated_trial_count"] for row in eligible_tasks),
        )
    else:
        max_k = 0

    pass_hat_ks: dict[str, float] = {}
    for k in range(1, max_k + 1):
        per_task = [
            _pass_hat_k(
                row["evaluated_trial_count"],
                row["success_count"],
                k,
            )
            for row in eligible_tasks
        ]
        pass_hat_ks[f"pass_hat_{k}"] = statistics.fmean(per_task)

    for row in task_rows:
        n = row["evaluated_trial_count"]
        c = row["success_count"]
        row["tau2_compatible_pass_hat_k"] = {
            f"pass_hat_{k}": _pass_hat_k(n, c, k)
            for k in range(1, min(n, max_k) + 1)
        }

    evaluated_rewards = [r["reward"] for r in evaluated_flat]
    evaluated_durations = [r["duration_s"] for r in evaluated_flat]
    evaluated_agent_costs = [
        r["agent_cost"]
        for r in evaluated_flat
        if r["agent_cost"] is not None
    ]
    evaluated_user_costs = [
        r["user_cost"]
        for r in evaluated_flat
        if r["user_cost"] is not None
    ]
    infra_error_count = termination.get(INFRASTRUCTURE_ERROR, 0)

    root = (
        input_path.resolve()
        if input_path.resolve().is_dir()
        else input_path.resolve().parent
    )
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "PASS_IMPORTED_NATIVE_TAU2",
        "canon_allowed": False,
        "tau2": {
            "expected_commit": expected_tau2_commit,
            "observed_commit": tau2_commit,
            "commit_verified": True,
            "domain": env_info.get("domain_name"),
            "agent_implementation": agent_info.get("implementation"),
            "agent_model": model,
            "agent_llm_args": agent_info.get("llm_args"),
            "user_implementation": user_info.get("implementation"),
            "user_model": user_info.get("llm"),
            "user_llm_args": user_info.get("llm_args"),
            "num_trials": num_trials,
            "task_count": len(task_rows),
            "simulation_count": len(simulations),
        },
        "gremlin_commit_sha": gremlin_commit_sha,
        "metrics": {
            "tau2_compatible": {
                "avg_reward": (
                    statistics.fmean(evaluated_rewards)
                    if evaluated_rewards else 0.0
                ),
                "pass_hat_k": pass_hat_ks,
                "max_k": max_k,
                "evaluated_simulation_count": len(evaluated_flat),
                "evaluated_task_count": len(eligible_tasks),
                "infra_error_count": infra_error_count,
                "infrastructure_errors_excluded": True,
                "success_tolerance": SUCCESS_TOLERANCE,
                "method": (
                    "Mirrors pinned tau2 agent_metrics: infrastructure errors "
                    "excluded, success within 1e-6 of reward=1, "
                    "pass_hat_k=comb(success_count,k)/comb(num_trials,k)."
                ),
            },
            "raw_diagnostics": {
                "native_reward_mean_all_simulations": (
                    statistics.fmean(raw_reward_values)
                    if raw_reward_values else 0.0
                ),
                "duration_s_all_simulations": {
                    "median": statistics.median(raw_durations),
                    "p95": _p95(raw_durations),
                    "mean": statistics.fmean(raw_durations),
                },
                "ordered_prefix_all_success_is_not_tau2_pass_hat_k": True,
            },
            "evaluated_duration_s": {
                "median": (
                    statistics.median(evaluated_durations)
                    if evaluated_durations else None
                ),
                "p95": _p95(evaluated_durations),
                "mean": (
                    statistics.fmean(evaluated_durations)
                    if evaluated_durations else None
                ),
            },
            "agent_cost": {
                "observed_count": len(evaluated_agent_costs),
                "mean_when_reported": (
                    statistics.fmean(evaluated_agent_costs)
                    if evaluated_agent_costs else None
                ),
                "total_when_reported": (
                    sum(evaluated_agent_costs)
                    if evaluated_agent_costs else None
                ),
            },
            "user_cost": {
                "observed_count": len(evaluated_user_costs),
                "mean_when_reported": (
                    statistics.fmean(evaluated_user_costs)
                    if evaluated_user_costs else None
                ),
                "total_when_reported": (
                    sum(evaluated_user_costs)
                    if evaluated_user_costs else None
                ),
            },
            "termination_reasons_all_simulations": dict(
                sorted(termination.items())
            ),
        },
        "comparison_ready": (
            infra_error_count == 0
            and max_k == num_trials
            and len(eligible_tasks) == len(task_rows)
        ),
        "tasks": task_rows,
        "source_binding": _source_binding(files, root),
        "claim_boundary": (
            "GREMLIN does not re-grade tau2 trajectories. Reward values are "
            "read from native tau2 reward_info.reward. pass_hat_k aggregation "
            "mirrors the pinned upstream metric definition; ordered-prefix "
            "diagnostics are explicitly not called pass^k."
        ),
    }
    raw = json.dumps(
        core,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    core["receipt_sha256"] = hashlib.sha256(raw).hexdigest()
    return core


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    p.add_argument(
        "--expected-tau2-commit",
        default=PINNED_TAU2_COMMIT,
    )
    p.add_argument("--expected-model")
    p.add_argument("--expected-num-trials", type=int)
    p.add_argument("--gremlin-commit-sha")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()

    result = import_tau2_results(
        a.input,
        expected_tau2_commit=a.expected_tau2_commit,
        expected_model=a.expected_model,
        expected_num_trials=a.expected_num_trials,
        gremlin_commit_sha=a.gremlin_commit_sha,
    )
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "domain": result["tau2"]["domain"],
                "model": result["tau2"]["agent_model"],
                "pass_hat_k": result["metrics"]["tau2_compatible"][
                    "pass_hat_k"
                ],
                "comparison_ready": result["comparison_ready"],
                "receipt_sha256": result["receipt_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
