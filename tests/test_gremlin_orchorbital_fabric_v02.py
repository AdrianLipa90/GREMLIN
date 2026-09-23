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


def test_n_node_coordination_point_creates_locality_without_causal_edges() -> None:
    fabric = OrchorbitalFabric()
    a = fabric.spawn("AUTH:ROOT", "SPIDER", node_id="A", join_to_caller=False)
    b = fabric.spawn("AUTH:ROOT", "MOLE", node_id="B", join_to_caller=False)
    c = fabric.spawn("AUTH:ROOT", "OWL", node_id="C", join_to_caller=False)

    point = fabric.create_coordination_point(
        (a.node_id, b.node_id, c.node_id),
        point_id="L1",
        weight=2.0,
    )

    assert point.point_id == "L1"
    assert point.physical_claim is False
    assert fabric.locality_distance(a.node_id, b.node_id) == 1.0
    assert fabric.locality_distance(a.node_id, c.node_id) == 1.0

    receipt = fabric.receipt()
    assert receipt["coordination_point_count"] == 1
    assert receipt["causal_edge_count"] == 0


def test_coordination_point_requires_unique_open_members() -> None:
    fabric = OrchorbitalFabric()
    a = fabric.spawn("AUTH:ROOT", "SPIDER", node_id="A", join_to_caller=False)
    b = fabric.spawn("AUTH:ROOT", "MOLE", node_id="B", join_to_caller=False)

    with pytest.raises(ValueError, match="members must be unique"):
        fabric.create_coordination_point((a.node_id, a.node_id))

    finish_local(fabric, b.node_id, "b")
    fabric.close(b.node_id)

    with pytest.raises(RuntimeError, match="node is not open"):
        fabric.create_coordination_point((a.node_id, b.node_id))


def test_octopus_center_ranking_can_use_n_node_coordination_point() -> None:
    fabric = OrchorbitalFabric()
    caller = fabric.spawn(
        "AUTH:ROOT",
        "MOLE",
        node_id="CALLER",
        join_to_caller=False,
    )
    preferred = fabric.spawn(
        "AUTH:ROOT",
        "BEES",
        node_id="PREFERRED",
        phase36=phase(2.0),
        join_to_caller=False,
    )
    other = fabric.spawn(
        "AUTH:ROOT",
        "OWL",
        node_id="OTHER",
        phase36=phase(0.1),
        join_to_caller=False,
    )
    fabric.create_coordination_point(
        (caller.node_id, preferred.node_id),
        point_id="LOCAL",
    )

    allocation = allocate_invocation(
        fabric,
        caller.node_id,
        ("graph",),
        operators(),
        budget=BUDGET,
        candidate_centers_by_operator={
            "SPIDER:T0": (other.node_id, preferred.node_id),
        },
        phase36_by_operator={
            "SPIDER:T0": phase(0.1),
        },
    )

    assert allocation.nodes[0].center_id == preferred.node_id


def test_self_complete_node_cannot_spawn_new_work() -> None:
    fabric = OrchorbitalFabric()
    parent = fabric.spawn(
        "AUTH:ROOT",
        "MOLE",
        node_id="PARENT",
        join_to_caller=False,
    )
    finish_local(fabric, parent.node_id, "parent-local")

    with pytest.raises(RuntimeError, match="self-complete node cannot spawn"):
        fabric.spawn(
            parent.node_id,
            "SPIDER",
            node_id="LATE",
        )


def test_join_set_is_sealed_after_self_completion() -> None:
    fabric = OrchorbitalFabric()
    consumer = fabric.spawn(
        "AUTH:ROOT",
        "MOLE",
        node_id="CONSUMER",
        join_to_caller=False,
    )
    child = fabric.spawn(
        "AUTH:ROOT",
        "OWL",
        node_id="CHILD",
        join_to_caller=False,
    )
    finish_local(fabric, consumer.node_id, "consumer-local")

    with pytest.raises(RuntimeError, match="join dependencies are sealed"):
        fabric.add_join_dependency(consumer.node_id, child.node_id)


def test_cross_relation_causal_join_deadlock_fails_closed() -> None:
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
    fabric.add_causal_dependency(a.node_id, b.node_id)

    with pytest.raises(ValueError, match="cross-relation cycle"):
        fabric.add_join_dependency(b.node_id, a.node_id)


def test_failed_node_never_satisfies_join_without_explicit_replacement() -> None:
    fabric = OrchorbitalFabric()
    parent = fabric.spawn(
        "AUTH:ROOT",
        "MOLE",
        node_id="PARENT",
        join_to_caller=False,
    )
    child = fabric.spawn(
        parent.node_id,
        "SPIDER",
        obligations=("graph",),
        node_id="CHILD",
    )
    finish_local(fabric, parent.node_id, "parent-local")

    fabric.fail(child.node_id, reason="worker crash")

    assert child.node_id not in fabric.closable_nodes()
    assert parent.node_id not in fabric.closable_nodes()
    assert fabric.replacement_for(child.node_id) is None

    replacement = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        obligations=("graph",),
        node_id="REPLACEMENT",
        join_to_caller=False,
    )
    fabric.bind_replacement(child.node_id, replacement.node_id)
    finish_local(fabric, replacement.node_id, "replacement-result")
    fabric.close(replacement.node_id)

    assert parent.node_id in fabric.closable_nodes()


def test_replacement_must_cover_failed_obligations() -> None:
    fabric = OrchorbitalFabric()
    source = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        obligations=("graph", "relations"),
        node_id="SOURCE",
        join_to_caller=False,
    )
    fabric.fail(source.node_id, reason="worker crash")

    replacement = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        obligations=("graph",),
        node_id="REPLACEMENT",
        join_to_caller=False,
    )

    with pytest.raises(ValueError, match="does not cover source obligations"):
        fabric.bind_replacement(source.node_id, replacement.node_id)


def test_replacement_cannot_create_cross_relation_cycle() -> None:
    fabric = OrchorbitalFabric()
    source = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        obligations=("graph",),
        node_id="SOURCE",
        join_to_caller=False,
    )
    replacement = fabric.spawn(
        "AUTH:ROOT",
        "OWL",
        obligations=("graph",),
        node_id="REPLACEMENT",
        join_to_caller=False,
    )
    fabric.add_causal_dependency(replacement.node_id, source.node_id)
    fabric.fail(source.node_id, reason="worker crash")

    with pytest.raises(ValueError, match="blocking cycle"):
        fabric.bind_replacement(source.node_id, replacement.node_id)


def test_failure_rehomes_live_satellites_and_barycenter() -> None:
    fabric = OrchorbitalFabric()
    center = fabric.spawn(
        "AUTH:ROOT",
        "MOLE",
        node_id="CENTER",
        join_to_caller=False,
    )
    satellite = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        center_id=center.node_id,
        node_id="SATELLITE",
        join_to_caller=False,
    )
    fabric.move_barycenter(center.node_id)

    failed = fabric.fail(center.node_id, reason="worker lost")

    assert failed.status == "FAILED"
    assert fabric.computational_barycenter_id == "AUTH:ROOT"
    assert fabric.node(satellite.node_id).center_id == "AUTH:ROOT"


def test_failure_uses_nearest_open_caller_when_direct_caller_is_closed() -> None:
    fabric = OrchorbitalFabric()
    ancestor = fabric.spawn(
        "AUTH:ROOT",
        "MOLE",
        node_id="ANCESTOR",
        join_to_caller=False,
    )
    child = fabric.spawn(
        ancestor.node_id,
        "SPIDER",
        node_id="CHILD",
        join_to_caller=False,
    )
    satellite = fabric.spawn(
        "AUTH:ROOT",
        "OWL",
        center_id=child.node_id,
        node_id="SATELLITE",
        join_to_caller=False,
    )

    fabric.recenter(child.node_id, "AUTH:ROOT")
    finish_local(fabric, ancestor.node_id, "ancestor")
    fabric.close(ancestor.node_id)
    fabric.fail(child.node_id, reason="child crash after caller close")

    assert fabric.node(satellite.node_id).center_id == "AUTH:ROOT"


def test_authority_root_cannot_close_over_unrecovered_failed_node() -> None:
    fabric = OrchorbitalFabric()
    child = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        obligations=("graph",),
        node_id="CHILD",
        join_to_caller=False,
    )
    fabric.fail(child.node_id, reason="unrecovered failure")
    fabric.mark_started("AUTH:ROOT")
    fabric.mark_self_complete("AUTH:ROOT", result_commitment="root-local")

    with pytest.raises(RuntimeError, match="other nodes are unresolved"):
        fabric.close("AUTH:ROOT")


def test_quarantined_node_requires_same_explicit_recovery_semantics() -> None:
    fabric = OrchorbitalFabric()
    source = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        obligations=("graph",),
        node_id="SOURCE",
        join_to_caller=False,
    )
    quarantined = fabric.quarantine(source.node_id, reason="suspect output")
    assert quarantined.status == "QUARANTINED"
    assert fabric.receipt()["failed_or_quarantined_counts_as_closed"] is False


def test_default_topology_snapshot_does_not_expose_raw_obligations() -> None:
    fabric = OrchorbitalFabric()
    fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        obligations=("sensitive-local-obligation",),
        node_id="A",
        join_to_caller=False,
    )

    snapshot = fabric.topology_snapshot()
    row = next(item for item in snapshot["nodes"] if item["node_id"] == "A")

    assert "obligations" not in row
    assert row["obligation_commitments"]
    assert "sensitive-local-obligation" not in str(snapshot)
    assert snapshot["worker_payloads_included"] is False
    assert snapshot["raw_obligations_included"] is False


def test_explicit_snapshot_can_include_obligations_for_local_audit() -> None:
    fabric = OrchorbitalFabric()
    fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        obligations=("graph",),
        node_id="A",
        join_to_caller=False,
    )

    snapshot = fabric.topology_snapshot(include_obligations=True)
    row = next(item for item in snapshot["nodes"] if item["node_id"] == "A")
    assert row["obligations"] == ["graph"]
    assert snapshot["raw_obligations_included"] is True


def test_topology_commitment_is_deterministic_and_changes_with_topology() -> None:
    left = OrchorbitalFabric()
    right = OrchorbitalFabric()

    left.spawn(
        "AUTH:ROOT",
        "SPIDER",
        obligations=("graph",),
        node_id="A",
        join_to_caller=False,
    )
    right.spawn(
        "AUTH:ROOT",
        "SPIDER",
        obligations=("graph",),
        node_id="A",
        join_to_caller=False,
    )

    assert left.topology_commitment() == right.topology_commitment()

    anchor = left.spawn(
        "AUTH:ROOT",
        "BEES",
        node_id="B",
        join_to_caller=False,
    )
    left.recenter("A", anchor.node_id)

    assert left.topology_commitment() != right.topology_commitment()
    assert left.receipt()["topology_commitment"] == left.topology_commitment()


def test_cross_relation_cycle_during_spawn_rolls_back_entire_batch() -> None:
    fabric = OrchorbitalFabric()
    caller = fabric.spawn(
        "AUTH:ROOT",
        "MOLE",
        node_id="CALLER",
        join_to_caller=False,
    )
    before_nodes = fabric.nodes()
    before_events = fabric.events()

    with pytest.raises(RuntimeError, match="blocking graph contains"):
        fabric.spawn(
            caller.node_id,
            "OWL",
            node_id="CYCLIC",
            causal_dependencies=(caller.node_id,),
            join_to_caller=True,
        )

    assert fabric.nodes() == before_nodes
    assert fabric.events() == before_events
    with pytest.raises(ValueError, match="unknown node_id"):
        fabric.node("CYCLIC")


def test_duplicate_edges_are_idempotent_and_do_not_pollute_event_log() -> None:
    fabric = OrchorbitalFabric()
    a = fabric.spawn("AUTH:ROOT", "SPIDER", node_id="A", join_to_caller=False)
    b = fabric.spawn("AUTH:ROOT", "OWL", node_id="B", join_to_caller=False)

    fabric.add_causal_dependency(a.node_id, b.node_id)
    first_event_count = len(fabric.events())
    fabric.add_causal_dependency(a.node_id, b.node_id)
    assert len(fabric.events()) == first_event_count

    other = OrchorbitalFabric()
    x = other.spawn("AUTH:ROOT", "MOLE", node_id="X", join_to_caller=False)
    y = other.spawn("AUTH:ROOT", "OWL", node_id="Y", join_to_caller=False)
    other.add_join_dependency(x.node_id, y.node_id)
    join_event_count = len(other.events())
    other.add_join_dependency(x.node_id, y.node_id)
    assert len(other.events()) == join_event_count

    other.add_coordination_edge(x.node_id, y.node_id)
    coordination_event_count = len(other.events())
    other.add_coordination_edge(x.node_id, y.node_id)
    assert len(other.events()) == coordination_event_count


def test_corrupted_closed_state_with_unresolved_join_fails_loud() -> None:
    fabric = OrchorbitalFabric()
    parent = fabric.spawn(
        "AUTH:ROOT",
        "MOLE",
        node_id="PARENT",
        join_to_caller=False,
    )
    child = fabric.spawn(
        parent.node_id,
        "OWL",
        node_id="CHILD",
    )
    fabric.mark_started(parent.node_id)
    fabric.mark_self_complete(parent.node_id, result_commitment="parent-local")

    fabric._nodes[parent.node_id] = replace(
        fabric._nodes[parent.node_id],
        status="CLOSED",
    )

    with pytest.raises(RuntimeError, match="closed node has unresolved join"):
        fabric.receipt()


def test_corrupted_open_node_cannot_point_to_terminal_center() -> None:
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
        node_id="SATELLITE",
        join_to_caller=False,
    )
    finish_local(fabric, center.node_id, "center")
    fabric.close(center.node_id)

    fabric._nodes[satellite.node_id] = replace(
        fabric._nodes[satellite.node_id],
        center_id=center.node_id,
    )

    with pytest.raises(RuntimeError, match="terminal center"):
        fabric.receipt()


def test_failure_transition_rolls_back_on_invariant_failure(monkeypatch) -> None:
    fabric = OrchorbitalFabric()
    node = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="A",
        join_to_caller=False,
    )
    before_nodes = fabric.nodes()
    before_events = fabric.events()
    original = fabric._assert_invariants

    def forced_failure():
        raise RuntimeError("forced invariant failure")

    monkeypatch.setattr(fabric, "_assert_invariants", forced_failure)
    with pytest.raises(RuntimeError, match="forced invariant failure"):
        fabric.fail(node.node_id, reason="test failure")
    monkeypatch.setattr(fabric, "_assert_invariants", original)

    assert fabric.nodes() == before_nodes
    assert fabric.events() == before_events
    assert fabric.node(node.node_id).status == "OPEN"


def test_replacement_binding_rolls_back_on_invariant_failure(monkeypatch) -> None:
    fabric = OrchorbitalFabric()
    source = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        obligations=("graph",),
        node_id="SOURCE",
        join_to_caller=False,
    )
    replacement = fabric.spawn(
        "AUTH:ROOT",
        "OWL",
        obligations=("graph",),
        node_id="REPLACEMENT",
        join_to_caller=False,
    )
    fabric.fail(source.node_id, reason="worker failure")
    before_events = fabric.events()
    original = fabric._assert_invariants

    def forced_failure():
        raise RuntimeError("forced invariant failure")

    monkeypatch.setattr(fabric, "_assert_invariants", forced_failure)
    with pytest.raises(RuntimeError, match="forced invariant failure"):
        fabric.bind_replacement(source.node_id, replacement.node_id)
    monkeypatch.setattr(fabric, "_assert_invariants", original)

    assert fabric.replacement_for(source.node_id) is None
    assert fabric.events() == before_events


def test_coordination_point_creation_rolls_back_on_invariant_failure(monkeypatch) -> None:
    fabric = OrchorbitalFabric()
    a = fabric.spawn("AUTH:ROOT", "SPIDER", node_id="A", join_to_caller=False)
    b = fabric.spawn("AUTH:ROOT", "OWL", node_id="B", join_to_caller=False)
    before_events = fabric.events()
    original = fabric._assert_invariants

    def forced_failure():
        raise RuntimeError("forced invariant failure")

    monkeypatch.setattr(fabric, "_assert_invariants", forced_failure)
    with pytest.raises(RuntimeError, match="forced invariant failure"):
        fabric.create_coordination_point(
            (a.node_id, b.node_id),
            point_id="FAIL-POINT",
        )
    monkeypatch.setattr(fabric, "_assert_invariants", original)

    assert fabric.coordination_points() == ()
    assert fabric.events() == before_events


def test_coordination_point_is_not_materialized_as_quadratic_clique() -> None:
    fabric = OrchorbitalFabric(max_nodes=80)
    members = [
        fabric.spawn(
            "AUTH:ROOT",
            "SPIDER",
            node_id=f"N{index}",
            join_to_caller=False,
        )
        for index in range(64)
    ]
    fabric.create_coordination_point(
        tuple(node.node_id for node in members),
        point_id="HYPEREDGE",
    )

    direct = fabric._locality_adjacency()
    assert members[1].node_id not in direct[members[0].node_id]
    assert fabric.locality_distance(members[0].node_id, members[-1].node_id) == 1.0
    assert fabric.receipt()["coordination_point_clique_materialized"] is False


def test_authority_root_cannot_be_used_as_replacement_target() -> None:
    fabric = OrchorbitalFabric()
    source = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="SOURCE",
        join_to_caller=False,
    )
    fabric.fail(source.node_id, reason="worker failure")

    with pytest.raises(ValueError, match="authority root cannot serve"):
        fabric.bind_replacement(source.node_id, "AUTH:ROOT")


def test_resolution_diagnostics_distinguish_terminal_from_resolved() -> None:
    fabric = OrchorbitalFabric()
    source = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        obligations=("graph",),
        node_id="SOURCE",
        join_to_caller=False,
    )
    fabric.fail(source.node_id, reason="worker failure")

    assert fabric.is_resolved(source.node_id) is False
    assert fabric.unresolved_terminal_nodes() == (source.node_id,)
    assert fabric.receipt()["unresolved_terminal_node_count"] == 1

    replacement = fabric.spawn(
        "AUTH:ROOT",
        "OWL",
        obligations=("graph",),
        node_id="REPLACEMENT",
        join_to_caller=False,
    )
    fabric.bind_replacement(source.node_id, replacement.node_id)
    finish_local(fabric, replacement.node_id, "replacement")
    fabric.close(replacement.node_id)

    assert fabric.is_resolved(source.node_id) is True
    assert fabric.unresolved_terminal_nodes() == ()
    assert fabric.receipt()["unresolved_terminal_node_count"] == 0


def test_deterministic_allocation_replays_same_nodes_exactly_once() -> None:
    fabric = OrchorbitalFabric()
    first = allocate_invocation(
        fabric,
        "AUTH:ROOT",
        ("graph", "audit"),
        operators(),
        budget=BUDGET,
        allocation_key="worker-result-abc",
    )
    before_count = fabric.receipt()["node_count"]

    second = allocate_invocation(
        fabric,
        "AUTH:ROOT",
        ("graph", "audit"),
        operators(),
        budget=BUDGET,
        allocation_key="worker-result-abc",
    )

    assert [node.node_id for node in second.nodes] == [node.node_id for node in first.nodes]
    assert fabric.receipt()["node_count"] == before_count
    assert second.receipt()["deterministic_replay"] is True


def test_deterministic_allocation_key_cannot_be_reused_for_different_work() -> None:
    fabric = OrchorbitalFabric()
    allocate_invocation(
        fabric,
        "AUTH:ROOT",
        ("graph",),
        operators(),
        budget=BUDGET,
        allocation_key="same-key",
    )

    with pytest.raises(RuntimeError, match="partial deterministic allocation|obligation mismatch"):
        allocate_invocation(
            fabric,
            "AUTH:ROOT",
            ("graph", "audit"),
            operators(),
            budget=BUDGET,
            allocation_key="same-key",
        )
