from __future__ import annotations

import math

import pytest

from gremlin_mcp.adaptive_runtime import (
    OperatorTier,
    ResourceBudget,
    ResourceCost,
    causal_tau,
    effective_resistance,
    escalation_required,
    minimal_capability_cover,
    next_obligations,
    phase_modulated_edges,
    relational_gravity,
    runtime_receipt,
)


BUDGET = ResourceBudget(tokens=1000, latency=10, calls=10, memory=100)


def test_exact_minimal_cover_prefers_lower_tier_when_it_closes_same_obligation() -> None:
    operators = [
        OperatorTier("HOUND", 0, frozenset({"contradiction_probe"}), ResourceCost(10, 1, 1, 1)),
        OperatorTier("HOUND", 1, frozenset({"contradiction_probe", "local_contradiction"}), ResourceCost(40, 2, 1, 2)),
    ]
    plan = minimal_capability_cover({"contradiction_probe"}, operators, budget=BUDGET)
    assert plan.complete is True
    assert plan.route_ids == ("HOUND:T0",)


def test_minimal_cover_uses_multiple_species_only_when_obligations_require_them() -> None:
    operators = [
        OperatorTier("SPIDER", 1, frozenset({"dependency_graph"}), ResourceCost(20, 2, 1, 3)),
        OperatorTier("OWL", 1, frozenset({"provenance"}), ResourceCost(20, 2, 1, 3)),
        OperatorTier("HOUND", 3, frozenset({"dependency_graph", "provenance"}), ResourceCost(500, 8, 4, 30)),
    ]
    plan = minimal_capability_cover({"dependency_graph", "provenance"}, operators, budget=BUDGET)
    assert set(plan.route_ids) == {"OWL:T1", "SPIDER:T1"}
    assert plan.minimax_pressure < 1.0



def test_same_species_tiers_are_mutually_exclusive_and_monotone() -> None:
    operators = [
        OperatorTier("HOUND", 0, frozenset({"probe"}), ResourceCost(10, 1, 1, 1)),
        OperatorTier("HOUND", 1, frozenset({"probe", "local"}), ResourceCost(20, 2, 1, 2)),
        OperatorTier("OWL", 0, frozenset({"audit"}), ResourceCost(10, 1, 1, 1)),
    ]
    plan = minimal_capability_cover({"probe", "local", "audit"}, operators, budget=BUDGET)
    assert set(plan.route_ids) == {"HOUND:T1", "OWL:T0"}
    assert sum(route.startswith("HOUND:") for route in plan.route_ids) == 1


def test_nonmonotone_species_tier_family_fails_closed() -> None:
    operators = [
        OperatorTier("HOUND", 0, frozenset({"probe"}), ResourceCost(10, 1, 1, 1)),
        OperatorTier("HOUND", 1, frozenset({"local"}), ResourceCost(20, 2, 1, 2)),
    ]
    with pytest.raises(ValueError, match="tier capabilities must be monotone"):
        minimal_capability_cover({"probe", "local"}, operators, budget=BUDGET)


def test_duplicate_species_tier_fails_closed() -> None:
    operators = [
        OperatorTier("OWL", 0, frozenset({"audit"}), ResourceCost(10, 1, 1, 1)),
        OperatorTier("OWL", 0, frozenset({"audit", "source"}), ResourceCost(20, 1, 1, 1)),
    ]
    with pytest.raises(ValueError, match="duplicate operator tier"):
        minimal_capability_cover({"audit"}, operators, budget=BUDGET)


def test_uncovered_obligation_fails_closed() -> None:
    operators = [
        OperatorTier("MOLE", 1, frozenset({"derive"}), ResourceCost(20, 1, 1, 1)),
    ]
    with pytest.raises(ValueError, match="uncovered obligations"):
        minimal_capability_cover({"derive", "external_actuation"}, operators, budget=BUDGET)


def test_obligation_frontier_closes_and_discovers_without_implicit_escalation() -> None:
    current = {"derive", "provenance"}
    nxt = next_obligations(current, closed={"derive"}, discovered={"contradiction_check"})
    assert nxt == frozenset({"provenance", "contradiction_check"})
    assert escalation_required(nxt) is True
    assert escalation_required(()) is False


def test_causal_tau_parallel_specialists_then_synthesis() -> None:
    result = causal_tau({
        "SPIDER": (),
        "HOUND": (),
        "OWL": (),
        "BELZEBUB": ("SPIDER", "HOUND", "OWL"),
    })
    assert result["tau"]["SPIDER"] == 0
    assert result["tau"]["HOUND"] == 0
    assert result["tau"]["OWL"] == 0
    assert result["tau"]["BELZEBUB"] == 1
    assert result["critical_path_depth"] == 1
    assert set(result["layers"][0]) == {"SPIDER", "HOUND", "OWL"}
    assert result["layers"][1] == ("BELZEBUB",)


def test_causal_tau_rejects_cycle() -> None:
    with pytest.raises(ValueError, match="cycle"):
        causal_tau({"A": ("B",), "B": ("A",)})


def test_independent_parallel_path_lowers_effective_resistance() -> None:
    nodes = ("q", "a", "b", "x")
    single = (
        ("q", "a", 1.0),
        ("a", "x", 1.0),
        ("b", "x", 1.0),
    )
    parallel = single + (("q", "b", 1.0),)
    r_single = effective_resistance(nodes, single, "q", "x")
    r_parallel = effective_resistance(nodes, parallel, "q", "x")
    assert r_single == pytest.approx(2.0)
    assert r_parallel == pytest.approx(1.0)
    assert r_parallel < r_single


def test_relational_gravity_zero_for_disconnected_node() -> None:
    nodes = ("q", "a", "x", "isolated")
    edges = (("q", "a", 1.0), ("a", "x", 1.0))
    gravity = relational_gravity(nodes, edges, "q")
    assert gravity["a"] > gravity["x"] > 0.0
    assert gravity["isolated"] == 0.0


def test_phase_modulation_changes_edges_without_mutating_input() -> None:
    edges = (("q", "a", 2.0), ("a", "x", 3.0))
    activation = {("q", "a"): 0.5, ("a", "x"): 2.0}
    modulated = phase_modulated_edges(edges, activation)
    assert edges == (("q", "a", 2.0), ("a", "x", 3.0))
    assert modulated == (("q", "a", 1.0), ("a", "x", 6.0))


def test_runtime_receipt_never_promotes_authority() -> None:
    plan = minimal_capability_cover(
        {"derive"},
        [OperatorTier("MOLE", 1, frozenset({"derive"}), ResourceCost(20, 1, 1, 1))],
        budget=BUDGET,
    )
    tau = causal_tau({"MOLE": ()})
    receipt = runtime_receipt(plan, tau)
    assert receipt["authority"] == "COGNITIVE_ROUTING_ONLY"
    assert receipt["epistemic"] == "CHYBA"
    assert receipt["canon_allowed"] is False
    assert receipt["execution_admitted"] is False
    assert receipt["memory_mutation_allowed"] is False
    assert receipt["physical_gravity_claim"] is False


def test_over_budget_complete_route_fails_closed() -> None:
    with pytest.raises(ValueError, match="no complete route fits resource budget"):
        minimal_capability_cover(
            {"audit"},
            [OperatorTier("OWL", 0, frozenset({"audit"}), ResourceCost(
                tokens=1500,
                latency=5,
                calls=1,
                memory=10,
            ))],
            budget=BUDGET,
        )


def test_minimax_pressure_uses_tightest_resource_not_weighted_sum() -> None:
    plan = minimal_capability_cover(
        {"audit"},
        [
            OperatorTier("OWL", 0, frozenset({"audit"}), ResourceCost(
                tokens=100,
                latency=5,
                calls=1,
                memory=10,
            )),
        ],
        budget=BUDGET,
    )
    assert plan.minimax_pressure == pytest.approx(0.5)
    assert math.isfinite(plan.minimax_pressure)
