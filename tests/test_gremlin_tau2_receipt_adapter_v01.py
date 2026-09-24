from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.gremlin_tau2_receipt_adapter_v01 import (
    PINNED_TAU2_COMMIT,
    import_tau2_results,
)


def _metadata(simulations, *, num_trials=2):
    return {
        "info": {
            "git_commit": PINNED_TAU2_COMMIT,
            "num_trials": num_trials,
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


def _sim(
    sim_id,
    task_id,
    trial,
    reward,
    *,
    termination_reason="agent_stop",
    include_reward_info=True,
):
    row = {
        "id": sim_id,
        "task_id": task_id,
        "trial": trial,
        "duration": 1.0 + trial,
        "termination_reason": termination_reason,
        "agent_cost": 0.1,
        "user_cost": 0.05,
        "messages": [],
    }
    if include_reward_info:
        row["reward_info"] = {"reward": reward}
    return row


def test_native_rewards_generate_upstream_compatible_pass_hat_k(tmp_path: Path) -> None:
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
    tau = out["metrics"]["tau2_compatible"]
    assert out["status"] == "PASS_IMPORTED_NATIVE_TAU2"
    assert tau["avg_reward"] == 0.75
    assert tau["pass_hat_k"]["pass_hat_1"] == 0.75
    assert tau["pass_hat_k"]["pass_hat_2"] == 0.5
    assert out["comparison_ready"] is True
    assert out["canon_allowed"] is False


def test_success_tolerance_matches_upstream_rule(tmp_path: Path) -> None:
    sims = [
        _sim("a0", "A", 0, 0.9999995),
        _sim("a1", "A", 1, 1.0),
    ]
    path = tmp_path / "results.json"
    path.write_text(json.dumps(_metadata(sims)), encoding="utf-8")
    out = import_tau2_results(path)
    tau = out["metrics"]["tau2_compatible"]
    assert tau["pass_hat_k"]["pass_hat_1"] == 1.0
    assert tau["pass_hat_k"]["pass_hat_2"] == 1.0


def test_infrastructure_errors_are_excluded_and_block_comparison_ready(
    tmp_path: Path,
) -> None:
    sims = [
        _sim("a0", "A", 0, 1.0),
        _sim(
            "a1",
            "A",
            1,
            0.0,
            termination_reason="infrastructure_error",
            include_reward_info=False,
        ),
        _sim("b0", "B", 0, 1.0),
        _sim("b1", "B", 1, 1.0),
    ]
    path = tmp_path / "results.json"
    path.write_text(json.dumps(_metadata(sims)), encoding="utf-8")
    out = import_tau2_results(path)
    tau = out["metrics"]["tau2_compatible"]
    assert tau["infra_error_count"] == 1
    assert tau["infrastructure_errors_excluded"] is True
    assert tau["max_k"] == 1
    assert tau["pass_hat_k"]["pass_hat_1"] == 1.0
    assert out["comparison_ready"] is False


def test_noncontiguous_trials_fail_closed(tmp_path: Path) -> None:
    sims = [
        _sim("a0", "A", 0, 1.0),
        _sim("a2", "A", 2, 1.0),
    ]
    path = tmp_path / "results.json"
    path.write_text(json.dumps(_metadata(sims)), encoding="utf-8")
    with pytest.raises(RuntimeError, match="trial identifiers"):
        import_tau2_results(path)


def test_upstream_commit_mismatch_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "results.json"
    data = _metadata(
        [_sim("a0", "A", 0, 1.0), _sim("a1", "A", 1, 1.0)]
    )
    data["info"]["git_commit"] = "0" * 40
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RuntimeError, match="tau2 commit mismatch"):
        import_tau2_results(path)


def test_model_mismatch_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "results.json"
    path.write_text(
        json.dumps(
            _metadata(
                [
                    _sim("a0", "A", 0, 1.0),
                    _sim("a1", "A", 1, 1.0),
                ]
            )
        ),
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
    (root / "results.json").write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )
    (sims_dir / "a0.json").write_text(
        json.dumps(_sim("a0", "A", 0, 1.0)),
        encoding="utf-8",
    )
    (sims_dir / "a1.json").write_text(
        json.dumps(_sim("a1", "A", 1, 1.0)),
        encoding="utf-8",
    )
    out = import_tau2_results(root, expected_model="same-model-test")
    assert out["metrics"]["tau2_compatible"]["pass_hat_k"][
        "pass_hat_2"
    ] == 1.0
    assert out["source_binding"]["file_count"] == 3


def test_missing_trial_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "results.json"
    path.write_text(
        json.dumps(_metadata([_sim("a0", "A", 0, 1.0)])),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="expected 2"):
        import_tau2_results(path)


def test_non_infrastructure_missing_reward_still_fails_closed(tmp_path: Path) -> None:
    sims = [
        _sim(
            "a0",
            "A",
            0,
            0.0,
            include_reward_info=False,
        ),
        _sim("a1", "A", 1, 1.0),
    ]
    path = tmp_path / "results.json"
    path.write_text(json.dumps(_metadata(sims)), encoding="utf-8")
    with pytest.raises(ValueError, match="missing reward_info"):
        import_tau2_results(path)
