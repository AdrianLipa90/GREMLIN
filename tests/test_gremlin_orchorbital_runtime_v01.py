from __future__ import annotations

import math

import pytest

from gremlin_mcp.orchorbital_runtime import (
    OrbitSpec,
    compile_orchorbital_plan,
    plan_receipt,
    ready_events,
    work_steal_order,
)


def phase(value: float) -> tuple[float, ...]:
    return tuple((value + index * 0.01) % (2.0 * math.pi) for index in range(36))


def reference_plan():
    specs = (
        OrbitSpec("A", "GREMLIN", phase36=phase(0.0)),
        OrbitSpec("B", "SPIDER", parent_id="A", phase36=phase(0.1)),
        OrbitSpec("C", "OWL", parent_id="A", phase36=phase(2.0)),
        OrbitSpec("BA", "RAVEN", parent_id="B", phase36=phase(0.2)),
        OrbitSpec("BB", "HOUND", parent_id="B", phase36=phase(0.3)),
        OrbitSpec("CA", "MOLE", parent_id="C", phase36=phase(2.1)),
    )
    return compile_orchorbital_plan(
        specs,
        root_id="A",
        coordination_edges=(("BA", "C"),),
    )


def test_recursive_orbits_create_local_not_global_joins() -> None:
    plan = reference_plan()
    events = plan.event_map()

    assert events["CLOSE:B"].prerequisites == ("CLOSE:BA", "CLOSE:BB", "OPEN:B")
    assert events["CLOSE:C"].prerequisites == ("CLOSE:CA", "OPEN:C")
    assert "CLOSE:CA" not in events["CLOSE:B"].prerequisites
    assert "CLOSE:BA" not in events["CLOSE:C"].prerequisites

    assert events["CLOSE:A"].prerequisites == ("CLOSE:B", "CLOSE:C", "OPEN:A")
    assert plan.max_local_join_fan_in == 2
    assert plan.global_join_fan_in == 2
    assert plan.max_parallel_width >= 3


def test_tau_layers_preserve_parallel_siblings() -> None:
    plan = reference_plan()
    events = plan.event_map()

    assert events["OPEN:A"].tau == 0
    assert events["OPEN:B"].tau == events["OPEN:C"].tau == 1
    assert events["OPEN:BA"].tau == events["OPEN:BB"].tau == events["OPEN:CA"].tau == 2
    assert events["CLOSE:A"].tau > events["CLOSE:B"].tau
    assert events["CLOSE:A"].tau > events["CLOSE:C"].tau


def test_ready_frontier_does_not_wait_for_unrelated_subtree() -> None:
    plan = reference_plan()
    completed = {
        "OPEN:A",
        "OPEN:B",
        "OPEN:C",
        "OPEN:BA",
        "OPEN:BB",
        "OPEN:CA",
        "CLOSE:BA",
        "CLOSE:BB",
    }
    ready = set(ready_events(plan, completed))

    assert "CLOSE:B" in ready
    assert "CLOSE:C" not in ready
    assert "CLOSE:A" not in ready


def test_cross_orbit_dependency_cycle_fails_closed() -> None:
    specs = (
        OrbitSpec("A", "GREMLIN"),
        OrbitSpec("B", "SPIDER", parent_id="A", depends_on=("C",)),
        OrbitSpec("C", "OWL", parent_id="A", depends_on=("B",)),
    )
    with pytest.raises(ValueError, match="causal cycle"):
        compile_orchorbital_plan(specs, root_id="A")


def test_multiple_roots_fail_closed() -> None:
    specs = (
        OrbitSpec("A", "GREMLIN"),
        OrbitSpec("B", "SPIDER"),
    )
    with pytest.raises(ValueError, match="exactly one declared root"):
        compile_orchorbital_plan(specs, root_id="A")


def test_invalid_phase_fails_closed() -> None:
    with pytest.raises(ValueError, match="exactly 36"):
        OrbitSpec("A", "GREMLIN", phase36=(0.0,))


def test_coordination_edge_shortens_work_steal_locality() -> None:
    plan = reference_plan()
    order = work_steal_order(plan, "BA", ("BB", "C", "CA"))
    assert order[0] == "C"
    assert set(order) == {"BB", "C", "CA"}


def test_receipt_does_not_promote_authority_or_speedup_claim() -> None:
    receipt = plan_receipt(reference_plan())
    assert receipt["topology"] == "RECURSIVE_FORK_LOCAL_JOIN"
    assert receipt["global_specialist_barrier"] is False
    assert receipt["canon_allowed"] is False
    assert receipt["execution_admitted"] is False
    assert receipt["memory_mutation_allowed"] is False
    assert receipt["speedup_claim"] is False


def test_relational_memory_roles_are_admitted_without_requiring_phase36() -> None:
    specs = (
        OrbitSpec("A", "GREMLIN"),
        OrbitSpec("E", "ELEPHANT", parent_id="A"),
        OrbitSpec("B", "BEES", parent_id="A"),
    )
    plan = compile_orchorbital_plan(specs, root_id="A")
    assert {orbit.species for orbit in plan.orbits} == {"GREMLIN", "ELEPHANT", "BEES"}
