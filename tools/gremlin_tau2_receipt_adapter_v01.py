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
VERSION = "0.1.0"
PINNED_TAU2_COMMIT = "b7ea9074c1cba482b30687fecdb5c8425fd6f619"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top-level JSON object required")
    return value


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _discover(input_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[Path]]:
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
        raise ValueError("results JSON has no simulations list and no simulations directory")

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
        raise ValueError(f"simulation {sim.get('id')!r} reward must be numeric")
    out = float(value)
    if not math.isfinite(out) or not 0.0 <= out <= 1.0:
        raise ValueError(f"simulation {sim.get('id')!r} reward must be finite in [0,1]")
    return out


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
    if len(expected_tau2_commit) != 40 or any(c not in "0123456789abcdef" for c in expected_tau2_commit):
        raise ValueError("expected_tau2_commit must be lowercase 40-char SHA")
    if gremlin_commit_sha is not None and (
        len(gremlin_commit_sha) != 40
        or any(c not in "0123456789abcdef" for c in gremlin_commit_sha)
    ):
        raise ValueError("gremlin_commit_sha must be lowercase 40-char SHA or null")

    metadata, simulations, files = _discover(input_path)
    info = metadata.get("info")
    if not isinstance(info, dict):
        raise ValueError("results metadata missing info")

    tau2_commit = info.get("git_commit")
    if tau2_commit != expected_tau2_commit:
        raise RuntimeError(
            f"tau2 commit mismatch: expected={expected_tau2_commit} actual={tau2_commit}"
        )

    agent_info = info.get("agent_info")
    env_info = info.get("environment_info")
    user_info = info.get("user_info")
    if not isinstance(agent_info, dict) or not isinstance(env_info, dict):
        raise ValueError("results info missing agent_info/environment_info")
    if not isinstance(user_info, dict):
        raise ValueError("results info missing user_info")

    model = agent_info.get("llm")
    if not isinstance(model, str) or not model:
        raise ValueError("agent model identifier missing")
    if expected_model is not None and model != expected_model:
        raise RuntimeError(f"agent model mismatch: expected={expected_model} actual={model}")

    num_trials = info.get("num_trials")
    if isinstance(num_trials, bool) or not isinstance(num_trials, int) or num_trials < 1:
        raise ValueError("info.num_trials must be positive integer")
    if expected_num_trials is not None and num_trials != expected_num_trials:
        raise RuntimeError(
            f"num_trials mismatch: expected={expected_num_trials} actual={num_trials}"
        )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    reward_values: list[float] = []
    durations: list[float] = []
    agent_costs: list[float] = []
    user_costs: list[float] = []
    termination = Counter()

    for sim in simulations:
        task_id = sim.get("task_id")
        if task_id is None:
            raise ValueError("simulation missing task_id")
        trial = sim.get("trial")
        if isinstance(trial, bool) or not isinstance(trial, int):
            raise ValueError(f"simulation {sim.get('id')!r} trial must be integer")
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
        reward_values.append(reward)
        durations.append(duration)
        if agent_cost is not None:
            agent_costs.append(agent_cost)
        if user_cost is not None:
            user_costs.append(user_cost)
        termination[term] += 1

    task_rows = []
    for task_id, rows in sorted(grouped.items()):
        rows = sorted(rows, key=lambda x: x["trial"])
        trials = [r["trial"] for r in rows]
        if len(rows) != num_trials:
            raise RuntimeError(
                f"task {task_id} has {len(rows)} simulations; expected {num_trials}"
            )
        if len(set(trials)) != len(trials):
            raise RuntimeError(f"task {task_id} has duplicate trial identifiers")
        rewards = [r["reward"] for r in rows]
        task_rows.append(
            {
                "task_id": task_id,
                "trials": trials,
                "rewards": rewards,
                "pass1": rewards[0] == 1.0,
                "pass_k": all(value == 1.0 for value in rewards),
            }
        )

    pass_rates = {}
    for k in range(1, num_trials + 1):
        passing = 0
        for task in task_rows:
            if all(value == 1.0 for value in task["rewards"][:k]):
                passing += 1
        pass_rates[f"pass_{k}"] = passing / len(task_rows)

    root = input_path.resolve() if input_path.resolve().is_dir() else input_path.resolve().parent
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
            "native_reward_mean": statistics.fmean(reward_values),
            "pass_rates": pass_rates,
            "duration_s": {
                "median": statistics.median(durations),
                "p95": _p95(durations),
                "mean": statistics.fmean(durations),
            },
            "agent_cost": {
                "observed_count": len(agent_costs),
                "mean_when_reported": (
                    statistics.fmean(agent_costs) if agent_costs else None
                ),
                "total_when_reported": sum(agent_costs) if agent_costs else None,
            },
            "user_cost": {
                "observed_count": len(user_costs),
                "mean_when_reported": (
                    statistics.fmean(user_costs) if user_costs else None
                ),
                "total_when_reported": sum(user_costs) if user_costs else None,
            },
            "termination_reasons": dict(sorted(termination.items())),
        },
        "tasks": task_rows,
        "source_binding": _source_binding(files, root),
        "claim_boundary": (
            "GREMLIN does not re-grade tau2 trajectories. reward/pass metrics are "
            "aggregated directly from native tau2 reward_info.reward values produced "
            "by the pinned upstream evaluator."
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
    p.add_argument("--expected-tau2-commit", default=PINNED_TAU2_COMMIT)
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
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "domain": result["tau2"]["domain"],
                "model": result["tau2"]["agent_model"],
                "pass_rates": result["metrics"]["pass_rates"],
                "receipt_sha256": result["receipt_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
