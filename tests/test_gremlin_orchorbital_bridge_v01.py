from __future__ import annotations

import math

import pytest

from gremlin_mcp.adaptive_runtime import OperatorTier, ResourceBudget, ResourceCost
from gremlin_mcp.orchorbital_bridge import compile_adaptive_orchorbital_plan


BUDGET = ResourceBudget(tokens=100.0, latency=100.0, calls=100.0, memory=100.0)


def operators():
    return (
        OperatorTier("SPIDER", 0, frozenset({"graph"}), ResourceCost(5, 5, 1, 2)),
        OperatorTier("SPIDER", 1, frozenset({"graph", "relations"}), ResourceCost(8, 7, 1, 3)),
        OperatorTier("OWL", 0, frozenset({"audit"}), ResourceCost(4, 4, 1, 2)),
        OperatorTier("MOLE", 0, frozenset({"derive"}), ResourceCost(7, 7, 1, 3)),
    )


def phase(x: float):
    return tuple((x + 0.01 * index) % (2 * math.pi) for index in range(36))


def test_exact_cover_compiles_to_recursive_execution_tree() -> None:
    result = compile_adaptive_orchorbital_plan(
        ("graph", "audit", "derive"),
        operators(),
        budget=BUDGET,
        parent_by_obligation={
            "graph": None,
            "audit": "graph",
            "derive": "graph",
        },
        phase36_by_obligation={"graph": phase(0.0), "audit": phase(0.2)},
        coordination_obligation_edges=(("audit", "derive"),),
    )

    receipt = result.receipt()
    assert set(receipt["minimal_cover_route"]) == {"SPIDER:T0", "OWL:T0", "MOLE:T0"}
    assert receipt["orchorbital"]["global_specialist_barrier"] is False
    assert receipt["orchorbital"]["root_join_fan_in"] == 1
    assert receipt["speedup_claim"] is False


def test_same_selected_species_can_own_multiple_nested_obligations() -> None:
    result = compile_adaptive_orchorbital_plan(
        ("graph", "relations"),
        operators(),
        budget=BUDGET,
        parent_by_obligation={"graph": None, "relations": "graph"},
    )
    mapping = dict(result.obligation_to_operator)
    assert mapping == {"graph": "SPIDER:T1", "relations": "SPIDER:T1"}
    species = [orbit.species for orbit in result.execution_plan.orbits]
    assert species.count("SPIDER") == 2


def test_uncovered_obligation_fails_closed_in_minimal_cover() -> None:
    with pytest.raises(ValueError, match="uncovered obligations"):
        compile_adaptive_orchorbital_plan(
            ("graph", "missing"),
            operators(),
            budget=BUDGET,
        )


def test_unknown_parent_fails_closed_before_execution() -> None:
    with pytest.raises(ValueError, match="unknown obligation parent"):
        compile_adaptive_orchorbital_plan(
            ("graph", "audit"),
            operators(),
            budget=BUDGET,
            parent_by_obligation={"audit": "not-declared"},
        )


def test_cross_obligation_cycle_is_rejected_by_orchorbital_compiler() -> None:
    with pytest.raises(ValueError, match="causal cycle"):
        compile_adaptive_orchorbital_plan(
            ("graph", "audit"),
            operators(),
            budget=BUDGET,
            depends_on_by_obligation={
                "graph": ("audit",),
                "audit": ("graph",),
            },
        )


def test_authority_is_not_promoted_by_bridge() -> None:
    receipt = compile_adaptive_orchorbital_plan(
        ("graph",),
        operators(),
        budget=BUDGET,
    ).receipt()
    assert receipt["canon_allowed"] is False
    assert receipt["execution_admitted"] is False
    assert receipt["memory_mutation_allowed"] is False
