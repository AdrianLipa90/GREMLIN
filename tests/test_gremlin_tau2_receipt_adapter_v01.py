from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.gremlin_tau2_receipt_adapter_v01 import (
    PINNED_TAU2_COMMIT,
    import_tau2_results,
)


def _metadata(simulations):
    return {
        "info": {
            "git_commit": PINNED_TAU2_COMMIT,
            "num_trials": 2,
            "max_steps": 200,
            "max_errors": 10,
            "agent_info": {
                "implementation": "gremlin_candidate",
                "llm": "same-model-test",
                "llm_args": {"temperature": 0},
            },
            "user_info": {
                "implementation": "user_simulator",
                "llm": "same-user-test",
                "llm_args": {"temperature": 0},
            },
            "environment_info": {"domain_name": "retail"},
        },
        "tasks": [],
        "simulations": simulations,
    }


def _sim(sim_id, task_id, trial, reward):
    return {
        "id": sim_id,
        "task_id": task_id,
        "trial": trial,
        "duration": 1.0 + trial,
        "termination_reason": "agent_stop",
        "agent_cost": 0.1,
        "user_cost": 0.05,
        "reward_info": {"reward": reward},
        "messages": [],
    }


def test_native_rewards_generate_pass1_and_passk_without_regrading(tmp_path: Path) -> None:
    sims = [
        _sim("a0", "A", 0, 1.0),
        _sim("a1", "A", 1, 1.0),
        _sim("b0", "B", 0, 1.0),
        _sim("b1", "B", 1, 0.0),
    ]
    path = tmp_path / "results.json"
    path.write_text(json.dumps(_metadata(sims)), encoding="utf-8")
    out = import_tau2_results(
        path,
        expected_model="same-model-test",
        expected_num_trials=2,
    )
    assert out["status"] == "PASS_IMPORTED_NATIVE_TAU2"
    assert out["metrics"]["pass_rates"]["pass_1"] == 1.0
    assert out["metrics"]["pass_rates"]["pass_2"] == 0.5
    assert out["metrics"]["native_reward_mean"] == 0.75
    assert out["canon_allowed"] is False


def test_upstream_commit_mismatch_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "results.json"
    data = _metadata([_sim("a0", "A", 0, 1.0), _sim("a1", "A", 1, 1.0)])
    data["info"]["git_commit"] = "0" * 40
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RuntimeError, match="tau2 commit mismatch"):
        import_tau2_results(path)


def test_model_mismatch_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "results.json"
    path.write_text(
        json.dumps(_metadata([_sim("a0", "A", 0, 1.0), _sim("a1", "A", 1, 1.0)])),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="agent model mismatch"):
        import_tau2_results(path, expected_model="different-model")


def test_directory_format_is_loaded_and_hashed(tmp_path: Path) -> None:
    root = tmp_path / "run"
    sims_dir = root / "simulations"
    sims_dir.mkdir(parents=True)
    metadata = _metadata([])
    metadata["simulation_index"] = [
        {"id": "a0", "task_id": "A", "trial": 0},
        {"id": "a1", "task_id": "A", "trial": 1},
    ]
    (root / "results.json").write_text(json.dumps(metadata), encoding="utf-8")
    (sims_dir / "a0.json").write_text(json.dumps(_sim("a0", "A", 0, 1.0)), encoding="utf-8")
    (sims_dir / "a1.json").write_text(json.dumps(_sim("a1", "A", 1, 1.0)), encoding="utf-8")
    out = import_tau2_results(root, expected_model="same-model-test")
    assert out["metrics"]["pass_rates"]["pass_2"] == 1.0
    assert out["source_binding"]["file_count"] == 3


def test_missing_trial_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "results.json"
    path.write_text(json.dumps(_metadata([_sim("a0", "A", 0, 1.0)])), encoding="utf-8")
    with pytest.raises(RuntimeError, match="expected 2"):
        import_tau2_results(path)
