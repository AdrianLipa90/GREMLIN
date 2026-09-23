from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any

SCHEMA = "GREMLIN_ORCHESTRATION_STRATEGY_GATE_V0_1"
VERSION = "0.1.0"
DETERMINISTIC = "DETERMINISTIC_MINIMAL_COVER"
BOUNDED_DYNAMIC = "BOUNDED_DYNAMIC_ORCHORBITAL"
HYBRID = "HYBRID_GUARDED"
MODES = frozenset({DETERMINISTIC, BOUNDED_DYNAMIC, HYBRID})


@dataclass(frozen=True)
class StrategySignals:
    known_path: bool
    multi_turn: bool
    dynamic_discovery_required: bool
    route_uncertainty: float = 0.0

    def __post_init__(self) -> None:
        for name in ("known_path", "multi_turn", "dynamic_discovery_required"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be bool")
        value = float(self.route_uncertainty)
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("route_uncertainty must be finite in [0,1]")
        object.__setattr__(self, "route_uncertainty", value)


def _sha(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def choose_orchestration_strategy(
    signals: StrategySignals,
    *,
    uncertainty_threshold: float = 0.25,
    delegation_cap: int = 2,
) -> dict[str, Any]:
    if not isinstance(signals, StrategySignals):
        raise ValueError("signals must be StrategySignals")
    threshold = float(uncertainty_threshold)
    if not math.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError("uncertainty_threshold must be finite in [0,1]")
    if (
        isinstance(delegation_cap, bool)
        or not isinstance(delegation_cap, int)
        or not 1 <= delegation_cap <= 6
    ):
        raise ValueError("delegation_cap must be integer in 1..6")

    if (
        signals.known_path
        and not signals.multi_turn
        and not signals.dynamic_discovery_required
        and signals.route_uncertainty <= threshold
    ):
        mode = DETERMINISTIC
        cap = 0
        reason = "KNOWN_SINGLE_SHOT_LOW_UNCERTAINTY"
    elif signals.multi_turn and signals.dynamic_discovery_required:
        mode = BOUNDED_DYNAMIC
        cap = delegation_cap
        reason = "OPEN_MULTI_TURN_REQUIRES_RUNTIME_DISCOVERY"
    else:
        mode = HYBRID
        cap = delegation_cap
        reason = "MIXED_OR_UNCERTAIN_TASK_SHAPE"

    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "mode": mode,
        "reason": reason,
        "signals": asdict(signals),
        "uncertainty_threshold": threshold,
        "delegation_cap": cap,
        "recursive_discovery_allowed": mode != DETERMINISTIC,
        "minimal_capability_cover_required": True,
        "fail_closed_on_budget_or_authority_violation": True,
        "evidence_status": "CANDIDATE_POLICY_CALIBRATED_BY_EXTERNAL_ORCHESTRATION_BENCHMARK",
        "calibration": {
            "source": "https://github.com/Himanshu-Sangshetti/orchestra-bench",
            "observation": "Known single-shot tasks favored explicit deterministic orchestration in the reported local pilot; open multi-turn tau2 tasks sometimes favored runtime self-orchestration; unguarded delegation cascaded to a cap of 6 in an open-ended AWS task while a guardrail held it to 2.",
            "delegation_cap_is_universal_optimum": False,
        },
        "authority": "CANDIDATE_ONLY",
        "canon_allowed": False,
    }
    core["strategy_commitment"] = _sha(core)
    return core


__all__ = [
    "SCHEMA",
    "VERSION",
    "DETERMINISTIC",
    "BOUNDED_DYNAMIC",
    "HYBRID",
    "MODES",
    "StrategySignals",
    "choose_orchestration_strategy",
]
