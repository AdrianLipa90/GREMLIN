from __future__ import annotations

import math
from dataclasses import replace

import pytest

from gremlin_mcp.adaptive_runtime import OperatorTier, ResourceBudget, ResourceCost
from gremlin_mcp.orchorbital_allocator import allocate_invocation
from gremlin_mcp.orchorbital_fabric import (
    OrchorbitalFabric,
    SpawnRequest,
)


BUDGET = ResourceBudget(tokens=100.0, latency=100.0, calls=100.0, memory=100.0)


def operators():
    return (
        OperatorTier("SPIDER", 0, frozenset({"graph"}), ResourceCost(5, 5, 1, 2)),
        OperatorTier(
            "SPIDER",
            1,
            frozenset({"graph", "relations"}),
            ResourceCost(8, 7, 1, 3),
        ),
        OperatorTier("OWL", 0, frozenset({"audit"}), ResourceCost(4, 4, 1, 2)),
        OperatorTier("MOLE", 0, frozenset({"derive"}), ResourceCost(7, 7, 1, 3)),
    )


def phase(value: float) -> tuple[float, ...]:
    return tuple((value + index * 0.01) % (2.0 * math.pi) for index in range(36))


def finish_local(fabric: OrchorbitalFabric, node_id: str, commitment: str) -> None:
    fabric.mark_started(node_id)
    fabric.mark_self_complete(node_id, result_commitment=commitment)


def test_species_has_no_fixed_hierarchical_position() -> None:
    fabric = OrchorbitalFabric()

    first = allocate_invocation(
        fabric,
        "AUTH:ROOT",
        ("derive",),
        operators(),
        budget=BUDGET,
    )
    mole_1 = first.nodes[0]

    second = allocate_invocation(
        fabric,
        mole_1.node_id,
        ("graph", "relations"),
        operators(),
        budget=BUDGET,
    )
    spider = second.nodes[0]

    third = allocate_invocation(
        fabric,
        spider.node_id,
        ("derive",),
        operators(),
        budget=BUDGET,
    )
    mole_2 = third.nodes[0]

    assert mole_1.species == "MOLE"
    assert spider.species == "SPIDER"
    assert mole_2.species == "MOLE"
    assert spider.caller_id == mole_1.node_id
    assert mole_2.caller_id == spider.node_id
    assert mole_1.node_id != mole_2.node_id


def test_caller_and_orbital_center_are_independent_relations() -> None:
    fabric = OrchorbitalFabric()
    caller = fabric.spawn(
        "AUTH:ROOT",
        "MOLE",
        node_id="CALLER",
        join_to_caller=False,
    )
    anchor = fabric.spawn(
        "AUTH:ROOT",
        "BEES",
        node_id="ANCHOR",
        join_to_caller=False,
    )

    allocation = allocate_invocation(
        fabric,
        caller.node_id,
        ("graph",),
        operators(),
        budget=BUDGET,
        center_by_operator={"SPIDER:T0": anchor.node_id},
    )
    node = allocation.nodes[0]

    assert node.caller_id == caller.node_id
    assert node.center_id == anchor.node_id


def test_reciprocal_orbital_centers_are_legal_but_noncausal() -> None:
    fabric = OrchorbitalFabric()
    a = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="A",
        join_to_caller=False,
    )
    b = fabric.spawn(
        "AUTH:ROOT",
        "MOLE",
        node_id="B",
        join_to_caller=False,
    )

    fabric.recenter(a.node_id, b.node_id)
    fabric.recenter(b.node_id, a.node_id)

    assert fabric.node("A").center_id == "B"
    assert fabric.node("B").center_id == "A"
    receipt = fabric.receipt()
    assert receipt["center_cycles_allowed"] is True
    assert receipt["causal_cycles_allowed"] is False


def test_causal_cycle_fails_closed_even_when_center_cycle_is_valid() -> None:
    fabric = OrchorbitalFabric()
    fabric.spawn("AUTH:ROOT", "SPIDER", node_id="A", join_to_caller=False)
    fabric.spawn("AUTH:ROOT", "MOLE", node_id="B", join_to_caller=False)

    fabric.recenter("A", "B")
    fabric.recenter("B", "A")
    fabric.add_causal_dependency("A", "B")

    with pytest.raises(ValueError, match="causal dependency would create a cycle"):
        fabric.add_causal_dependency("B", "A")


def test_join_cycle_fails_closed() -> None:
    fabric = OrchorbitalFabric()
    fabric.spawn("AUTH:ROOT", "SPIDER", node_id="A", join_to_caller=False)
    fabric.spawn("AUTH:ROOT", "MOLE", node_id="B", join_to_caller=False)

    fabric.add_join_dependency("A", "B")
    with pytest.raises(ValueError, match="join dependency would create a cycle"):
        fabric.add_join_dependency("B", "A")


def test_local_child_join_blocks_only_its_consumer() -> None:
    fabric = OrchorbitalFabric()
    a = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="A",
        join_to_caller=False,
    )
    b = fabric.spawn(
        "AUTH:ROOT",
        "MOLE",
        node_id="B",
        join_to_caller=False,
    )
    child = fabric.spawn(a.node_id, "OWL", node_id="A1")
    finish_local(fabric, a.node_id, "a-local")
    finish_local(fabric, b.node_id, "b-local")
    finish_local(fabric, child.node_id, "a1-local")

    assert b.node_id in fabric.closable_nodes()
    assert a.node_id not in fabric.closable_nodes()

    fabric.close(child.node_id)
    assert a.node_id in fabric.closable_nodes()


def test_authority_root_and_computational_barycenter_are_separate() -> None:
    fabric = OrchorbitalFabric()
    node = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="HOT",
        join_to_caller=False,
    )

    root = fabric.authority_root_id
    fabric.move_barycenter(node.node_id, reason="subtree became dominant")

    assert fabric.authority_root_id == root
    assert fabric.computational_barycenter_id == node.node_id
    assert fabric.node(node.node_id).authority_root_id == root


def test_recenter_does_not_mutate_caller_or_authority() -> None:
    fabric = OrchorbitalFabric()
    caller = fabric.spawn(
        "AUTH:ROOT",
        "MOLE",
        node_id="CALLER",
        join_to_caller=False,
    )
    a = fabric.spawn(caller.node_id, "SPIDER", node_id="A")
    b = fabric.spawn(
        "AUTH:ROOT",
        "BEES",
        node_id="B",
        join_to_caller=False,
    )

    before = fabric.node(a.node_id)
    after = fabric.recenter(a.node_id, b.node_id)

    assert after.caller_id == before.caller_id == caller.node_id
    assert after.authority_root_id == before.authority_root_id
    assert after.center_id == b.node_id


def test_barycenter_must_move_before_hot_node_closes() -> None:
    fabric = OrchorbitalFabric()
    node = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="HOT",
        join_to_caller=False,
    )
    fabric.move_barycenter(node.node_id)
    finish_local(fabric, node.node_id, "hot-local")

    with pytest.raises(RuntimeError, match="move computational barycenter"):
        fabric.close(node.node_id)

    fabric.move_barycenter("AUTH:ROOT")
    fabric.close(node.node_id)


def test_spawn_batch_is_atomic_on_invariant_failure(monkeypatch) -> None:
    fabric = OrchorbitalFabric()
    before_nodes = fabric.nodes()
    before_events = fabric.events()

    original = fabric._assert_invariants

    def forced_failure():
        raise RuntimeError("forced invariant failure")

    monkeypatch.setattr(fabric, "_assert_invariants", forced_failure)
    with pytest.raises(RuntimeError, match="forced invariant failure"):
        fabric.spawn_batch(
            "AUTH:ROOT",
            (
                SpawnRequest("SPIDER"),
                SpawnRequest("OWL"),
            ),
        )
    monkeypatch.setattr(fabric, "_assert_invariants", original)

    assert fabric.nodes() == before_nodes
    assert fabric.events() == before_events
    assert fabric.receipt()["node_count"] == 1


def test_event_log_is_returned_by_copy() -> None:
    fabric = OrchorbitalFabric()
    fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="A",
        join_to_caller=False,
    )

    events = list(fabric.events())
    events[-1]["details"]["node_ids"] = ["CORRUPTED"]

    fresh = fabric.events()
    assert fresh[-1]["details"]["node_ids"] == ["A"]


def test_phase36_boundary_is_fail_closed() -> None:
    fabric = OrchorbitalFabric()

    with pytest.raises(ValueError, match="exactly 36"):
        fabric.spawn(
            "AUTH:ROOT",
            "SPIDER",
            phase36=(0.0,),
        )

    node = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        phase36=phase(0.5),
        join_to_caller=False,
    )
    assert len(node.phase36 or ()) == 36


def test_allocator_receipt_preserves_non_authoritative_boundary() -> None:
    fabric = OrchorbitalFabric()
    allocation = allocate_invocation(
        fabric,
        "AUTH:ROOT",
        ("graph", "audit"),
        operators(),
        budget=BUDGET,
    )
    receipt = allocation.receipt()

    assert receipt["allocator"] == "OCTOPUS"
    assert receipt["recursive_invocation_allowed"] is True
    assert receipt["species_position_fixed"] is False
    assert receipt["canon_allowed"] is False
    assert receipt["execution_admitted"] is False
    assert receipt["memory_mutation_allowed"] is False
    assert receipt["speedup_claim"] is False


def test_allocator_rejects_center_for_operator_not_in_selected_route() -> None:
    fabric = OrchorbitalFabric()
    with pytest.raises(ValueError, match="outside selected route"):
        allocate_invocation(
            fabric,
            "AUTH:ROOT",
            ("graph",),
            operators(),
            budget=BUDGET,
            center_by_operator={"OWL:T0": "AUTH:ROOT"},
        )


def test_static_v01_paths_are_explicitly_compatibility_only() -> None:
    from gremlin_mcp.orchorbital_bridge import (
        COMPATIBILITY_ONLY as BRIDGE_COMPATIBILITY_ONLY,
        SUPERSEDED_BY as BRIDGE_SUPERSEDED_BY,
    )
    from gremlin_mcp.orchorbital_runtime import (
        COMPATIBILITY_ONLY as RUNTIME_COMPATIBILITY_ONLY,
        SUPERSEDED_BY as RUNTIME_SUPERSEDED_BY,
    )

    assert RUNTIME_COMPATIBILITY_ONLY is True
    assert RUNTIME_SUPERSEDED_BY == "GREMLIN_ORCHORBITAL_FABRIC_V0_2"
    assert BRIDGE_COMPATIBILITY_ONLY is True
    assert BRIDGE_SUPERSEDED_BY == "GREMLIN_OCTOPUS_ORCHORBITAL_ALLOCATOR_V0_2"


def test_invocation_depth_tracks_runtime_lineage_not_species() -> None:
    fabric = OrchorbitalFabric()
    a = fabric.spawn("AUTH:ROOT", "MOLE", node_id="A", join_to_caller=False)
    b = fabric.spawn(a.node_id, "SPIDER", node_id="B", join_to_caller=False)
    c = fabric.spawn(b.node_id, "MOLE", node_id="C", join_to_caller=False)

    assert a.invocation_depth == 1
    assert b.invocation_depth == 2
    assert c.invocation_depth == 3
    assert fabric.receipt()["max_invocation_depth"] == 3


def test_recursive_growth_is_bounded_by_node_budget_not_species_depth() -> None:
    fabric = OrchorbitalFabric(max_nodes=3)
    a = fabric.spawn("AUTH:ROOT", "MOLE", node_id="A", join_to_caller=False)
    fabric.spawn(a.node_id, "SPIDER", node_id="B", join_to_caller=False)

    with pytest.raises(RuntimeError, match="node budget exceeded"):
        fabric.spawn("B", "OWL", node_id="C", join_to_caller=False)

    assert fabric.receipt()["node_count"] == 3


def test_open_satellites_must_be_recentered_before_center_closes() -> None:
    fabric = OrchorbitalFabric()
    center = fabric.spawn(
        "AUTH:ROOT",
        "BEES",
        node_id="CENTER",
        join_to_caller=False,
    )
    satellite = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="SAT",
        center_id=center.node_id,
        join_to_caller=False,
    )

    finish_local(fabric, center.node_id, "center-local")
    with pytest.raises(RuntimeError, match="recenter open satellites"):
        fabric.close(center.node_id)

    fabric.recenter(satellite.node_id, "AUTH:ROOT")
    fabric.close(center.node_id)


def test_node_cannot_close_before_local_work_is_complete() -> None:
    fabric = OrchorbitalFabric()
    node = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="A",
        join_to_caller=False,
    )

    assert node.node_id in fabric.ready_nodes()
    assert node.node_id not in fabric.closable_nodes()

    with pytest.raises(RuntimeError, match="local work is not complete"):
        fabric.close(node.node_id)

    fabric.mark_started(node.node_id)
    completed = fabric.mark_self_complete(
        node.node_id,
        result_commitment="result-a",
    )
    assert completed.self_complete is True
    assert completed.result_commitment == "result-a"
    assert node.node_id not in fabric.ready_nodes()
    assert node.node_id in fabric.closable_nodes()

    fabric.close(node.node_id)


def test_self_completion_is_idempotent_only_for_same_commitment() -> None:
    fabric = OrchorbitalFabric()
    node = fabric.spawn(
        "AUTH:ROOT",
        "OWL",
        node_id="A",
        join_to_caller=False,
    )

    fabric.mark_started(node.node_id)
    first = fabric.mark_self_complete(
        node.node_id,
        result_commitment="same",
    )
    second = fabric.mark_self_complete(
        node.node_id,
        result_commitment="same",
    )
    assert first == second

    with pytest.raises(RuntimeError, match="already complete"):
        fabric.mark_self_complete(
            node.node_id,
            result_commitment="different",
        )


def test_local_execution_must_start_before_result_is_accepted() -> None:
    fabric = OrchorbitalFabric()
    node = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="A",
        join_to_caller=False,
    )

    with pytest.raises(RuntimeError, match="execution has not started"):
        fabric.mark_self_complete(
            node.node_id,
            result_commitment="premature",
        )

    started = fabric.mark_started(node.node_id)
    assert started.execution_started is True
    assert node.node_id in fabric.running_nodes()

    fabric.mark_self_complete(
        node.node_id,
        result_commitment="valid",
    )
    assert node.node_id not in fabric.running_nodes()


def test_causal_dependencies_are_sealed_after_execution_starts() -> None:
    fabric = OrchorbitalFabric()
    dependency = fabric.spawn(
        "AUTH:ROOT",
        "OWL",
        node_id="DEP",
        join_to_caller=False,
    )
    finish_local(fabric, dependency.node_id, "dep")
    fabric.close(dependency.node_id)

    node = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="A",
        join_to_caller=False,
    )
    fabric.mark_started(node.node_id)

    with pytest.raises(RuntimeError, match="causal dependencies are sealed"):
        fabric.add_causal_dependency(node.node_id, dependency.node_id)


def test_corrupted_caller_cycle_is_detected_fail_loud() -> None:
    fabric = OrchorbitalFabric()
    fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="A",
        join_to_caller=False,
    )
    fabric.spawn(
        "AUTH:ROOT",
        "MOLE",
        node_id="B",
        join_to_caller=False,
    )

    fabric._nodes["A"] = replace(fabric._nodes["A"], caller_id="B")
    fabric._nodes["B"] = replace(fabric._nodes["B"], caller_id="A")

    with pytest.raises(RuntimeError, match="caller provenance graph contains a cycle"):
        fabric.receipt()


def test_new_coordination_edges_require_open_endpoints() -> None:
    fabric = OrchorbitalFabric()
    a = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="A",
        join_to_caller=False,
    )
    b = fabric.spawn(
        "AUTH:ROOT",
        "OWL",
        node_id="B",
        join_to_caller=False,
    )
    finish_local(fabric, b.node_id, "b")
    fabric.close(b.node_id)

    with pytest.raises(RuntimeError, match="node is not open"):
        fabric.add_coordination_edge(a.node_id, b.node_id)


def test_center_ranking_prefers_graph_locality_before_phase() -> None:
    fabric = OrchorbitalFabric()
    caller = fabric.spawn(
        "AUTH:ROOT",
        "MOLE",
        node_id="CALLER",
        join_to_caller=False,
    )
    near = fabric.spawn(
        "AUTH:ROOT",
        "BEES",
        node_id="NEAR",
        phase36=phase(2.5),
        join_to_caller=False,
    )
    far = fabric.spawn(
        "AUTH:ROOT",
        "OWL",
        node_id="FAR",
        phase36=phase(0.1),
        join_to_caller=False,
    )
    fabric.add_coordination_edge(caller.node_id, near.node_id)

    ranked = fabric.rank_centers(
        caller.node_id,
        (near.node_id, far.node_id),
        phase36=phase(0.1),
    )

    assert ranked[0] == near.node_id
    assert fabric.locality_distance(caller.node_id, near.node_id) == 1.0
    assert fabric.locality_distance(caller.node_id, far.node_id) == 2.0


def test_center_ranking_uses_t36_as_equal_distance_tiebreak() -> None:
    fabric = OrchorbitalFabric()
    near_phase = fabric.spawn(
        "AUTH:ROOT",
        "BEES",
        node_id="PHASE_NEAR",
        phase36=phase(0.2),
        join_to_caller=False,
    )
    far_phase = fabric.spawn(
        "AUTH:ROOT",
        "OWL",
        node_id="PHASE_FAR",
        phase36=phase(2.5),
        join_to_caller=False,
    )

    ranked = fabric.rank_centers(
        "AUTH:ROOT",
        (far_phase.node_id, near_phase.node_id),
        phase36=phase(0.21),
    )

    assert ranked[0] == near_phase.node_id


def test_octopus_selects_runtime_center_from_candidates() -> None:
    fabric = OrchorbitalFabric()
    a = fabric.spawn(
        "AUTH:ROOT",
        "BEES",
        node_id="A",
        phase36=phase(0.2),
        join_to_caller=False,
    )
    b = fabric.spawn(
        "AUTH:ROOT",
        "OWL",
        node_id="B",
        phase36=phase(2.5),
        join_to_caller=False,
    )

    allocation = allocate_invocation(
        fabric,
        "AUTH:ROOT",
        ("graph",),
        operators(),
        budget=BUDGET,
        candidate_centers_by_operator={
            "SPIDER:T0": (b.node_id, a.node_id),
        },
        phase36_by_operator={
            "SPIDER:T0": phase(0.21),
        },
    )

    node = allocation.nodes[0]
    assert node.center_id == a.node_id
    assert dict(allocation.operator_to_center) == {"SPIDER:T0": a.node_id}
    assert allocation.receipt()["operator_to_center"] == {"SPIDER:T0": a.node_id}


def test_octopus_rejects_ambiguous_explicit_and_candidate_center_policy() -> None:
    fabric = OrchorbitalFabric()
    anchor = fabric.spawn(
        "AUTH:ROOT",
        "BEES",
        node_id="ANCHOR",
        join_to_caller=False,
    )

    with pytest.raises(ValueError, match="overlap"):
        allocate_invocation(
            fabric,
            "AUTH:ROOT",
            ("graph",),
            operators(),
            budget=BUDGET,
            center_by_operator={"SPIDER:T0": anchor.node_id},
            candidate_centers_by_operator={
                "SPIDER:T0": (anchor.node_id,),
            },
        )
