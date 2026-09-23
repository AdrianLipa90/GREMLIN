from __future__ import annotations

import pytest

from gremlin_mcp.orchestration_strategy_gate import (
    BOUNDED_DYNAMIC,
    DETERMINISTIC,
    HYBRID,
    StrategySignals,
    choose_orchestration_strategy,
)


def test_known_single_shot_uses_deterministic_minimal_cover() -> None:
    out = choose_orchestration_strategy(
        StrategySignals(True, False, False, 0.10)
    )
    assert out["mode"] == DETERMINISTIC
    assert out["delegation_cap"] == 0
    assert out["recursive_discovery_allowed"] is False


def test_open_multi_turn_discovery_is_bounded_dynamic() -> None:
    out = choose_orchestration_strategy(
        StrategySignals(False, True, True, 0.70)
    )
    assert out["mode"] == BOUNDED_DYNAMIC
    assert out["delegation_cap"] == 2
    assert out["recursive_discovery_allowed"] is True


def test_mixed_task_is_hybrid_not_forced_dynamic() -> None:
    out = choose_orchestration_strategy(
        StrategySignals(True, True, False, 0.35)
    )
    assert out["mode"] == HYBRID
    assert out["delegation_cap"] == 2


def test_high_uncertainty_known_path_falls_back_to_hybrid() -> None:
    out = choose_orchestration_strategy(
        StrategySignals(True, False, False, 0.26)
    )
    assert out["mode"] == HYBRID


def test_cap_and_uncertainty_validate_fail_closed() -> None:
    with pytest.raises(ValueError, match="delegation_cap"):
        choose_orchestration_strategy(
            StrategySignals(False, True, True, 0.5),
            delegation_cap=7,
        )
    with pytest.raises(ValueError, match="route_uncertainty"):
        StrategySignals(False, True, True, 1.1)
