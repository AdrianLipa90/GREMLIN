from __future__ import annotations

from copy import deepcopy

import pytest

from gremlin_mcp.orchorbital_context import (
    OrbitalContextStore,
    apply_context_packet,
)
from gremlin_mcp.orchorbital_fabric import OrchorbitalFabric


def fabric_with_chain():
    fabric = OrchorbitalFabric()
    a = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="A",
        join_to_caller=False,
    )
    b = fabric.spawn(
        a.node_id,
        "MOLE",
        node_id="B",
        join_to_caller=False,
    )
    return fabric, a, b


def test_context_inheritance_is_lossless_base_plus_delta() -> None:
    fabric, a, b = fabric_with_chain()
    store = OrbitalContextStore(fabric)
    store.bind_root(
        {
            "request": "shared problem statement",
            "memory": "shared memory slice",
            "mode": "root",
        }
    )
    store.inherit_from_caller(
        a.node_id,
        set_values={"mode": "spider", "graph": "local delta"},
    )
    store.inherit_from_caller(
        b.node_id,
        set_values={"mode": "mole", "derive": "deep delta"},
    )

    assert store.materialize(b.node_id) == {
        "request": "shared problem statement",
        "memory": "shared memory slice",
        "mode": "mole",
        "graph": "local delta",
        "derive": "deep delta",
    }


def test_context_delete_is_explicit_and_lossless() -> None:
    fabric, a, _ = fabric_with_chain()
    store = OrbitalContextStore(fabric)
    store.bind_root({"a": 1, "b": 2, "c": 3})
    store.inherit_from_caller(
        a.node_id,
        set_values={"d": 4},
        delete_keys=("b",),
    )

    assert store.materialize(a.node_id) == {"a": 1, "c": 3, "d": 4}


def test_context_frame_is_immutable_after_binding() -> None:
    fabric, a, _ = fabric_with_chain()
    store = OrbitalContextStore(fabric)
    store.bind_root({"x": 1})

    first = store.inherit_from_caller(a.node_id, set_values={"y": 2})
    replay = store.inherit_from_caller(a.node_id, set_values={"y": 2})
    assert replay.frame_commitment == first.frame_commitment

    with pytest.raises(RuntimeError, match="immutable"):
        store.inherit_from_caller(a.node_id, set_values={"y": 3})


def test_context_base_does_not_mutate_when_orbital_center_moves() -> None:
    fabric, a, b = fabric_with_chain()
    anchor = fabric.spawn(
        "AUTH:ROOT",
        "BEES",
        node_id="ANCHOR",
        join_to_caller=False,
    )
    store = OrbitalContextStore(fabric)
    store.bind_root({"root": True})
    store.inherit_from_caller(a.node_id, set_values={"a": 1})
    frame = store.inherit_from_caller(b.node_id, set_values={"b": 2})
    store.inherit_from_caller(anchor.node_id, set_values={"anchor": 1})

    fabric.recenter(b.node_id, anchor.node_id)

    after = store.frame(b.node_id)
    assert after.base_node_id == a.node_id
    assert after.base_frame_commitment == frame.base_frame_commitment
    assert store.materialize(b.node_id) == {"root": True, "a": 1, "b": 2}


def test_full_packet_reconstructs_exact_materialized_context() -> None:
    fabric, a, b = fabric_with_chain()
    store = OrbitalContextStore(fabric)
    store.bind_root({"shared": "X" * 200, "mode": "root"})
    store.inherit_from_caller(a.node_id, set_values={"mode": "A"})
    store.inherit_from_caller(b.node_id, set_values={"local": "B"})

    packet = store.packet(b.node_id)
    decoded = apply_context_packet(packet)

    assert decoded["materialized_context"] == store.materialize(b.node_id)
    assert decoded["target_frame_commitment"] == store.frame(b.node_id).frame_commitment


def test_cached_base_allows_delta_only_packet() -> None:
    fabric, a, b = fabric_with_chain()
    store = OrbitalContextStore(fabric)
    store.bind_root({"shared": "X" * 2000, "mode": "root"})
    store.inherit_from_caller(a.node_id, set_values={"mode": "A"})
    store.inherit_from_caller(b.node_id, set_values={"local": "tiny"})

    base_frame = store.frame(a.node_id)
    base_context = store.materialize(a.node_id)
    packet = store.packet(
        b.node_id,
        receiver_known_frames=(base_frame.frame_commitment,),
    )

    assert packet["required_base_frame_commitment"] == base_frame.frame_commitment
    assert len(packet["frames"]) == 1
    decoded = apply_context_packet(
        packet,
        known_contexts={base_frame.frame_commitment: base_context},
    )
    assert decoded["materialized_context"] == store.materialize(b.node_id)
    assert packet["packet_bytes"] < packet["materialized_context_bytes"]
    assert packet["token_saving_claim"] is False


def test_target_already_cached_requires_no_frames() -> None:
    fabric, a, _ = fabric_with_chain()
    store = OrbitalContextStore(fabric)
    store.bind_root({"shared": "x"})
    store.inherit_from_caller(a.node_id, set_values={"a": 1})
    target = store.frame(a.node_id)
    context = store.materialize(a.node_id)

    packet = store.packet(
        a.node_id,
        receiver_known_frames=(target.frame_commitment,),
    )

    assert packet["frames"] == []
    assert packet["required_base_frame_commitment"] == target.frame_commitment
    decoded = apply_context_packet(
        packet,
        known_contexts={target.frame_commitment: context},
    )
    assert decoded["materialized_context"] == context


def test_tampered_context_frame_is_rejected() -> None:
    fabric, a, _ = fabric_with_chain()
    store = OrbitalContextStore(fabric)
    store.bind_root({"shared": "root"})
    store.inherit_from_caller(a.node_id, set_values={"local": "original"})
    packet = store.packet(a.node_id)

    tampered = deepcopy(packet)
    tampered["frames"][-1]["set_values"]["local"] = "tampered"

    with pytest.raises(ValueError, match="commitment mismatch"):
        apply_context_packet(tampered)


def test_missing_cached_base_fails_closed() -> None:
    fabric, a, b = fabric_with_chain()
    store = OrbitalContextStore(fabric)
    store.bind_root({"root": 1})
    store.inherit_from_caller(a.node_id, set_values={"a": 1})
    store.inherit_from_caller(b.node_id, set_values={"b": 1})
    base = store.frame(a.node_id)
    packet = store.packet(
        b.node_id,
        receiver_known_frames=(base.frame_commitment,),
    )

    with pytest.raises(ValueError, match="required base context is unavailable"):
        apply_context_packet(packet)


def test_privacy_safe_context_snapshot_excludes_raw_values() -> None:
    fabric, a, _ = fabric_with_chain()
    store = OrbitalContextStore(fabric)
    store.bind_root({"secret-context": "do-not-put-in-snapshot"})
    store.inherit_from_caller(a.node_id, set_values={"local": "value"})

    snapshot = store.snapshot()
    serialized = repr(snapshot)

    assert snapshot["raw_values_included"] is False
    assert "do-not-put-in-snapshot" not in serialized
    assert "frame_commitment" in serialized


def test_only_authority_root_can_bind_context_without_base() -> None:
    fabric, a, _ = fabric_with_chain()
    store = OrbitalContextStore(fabric)

    with pytest.raises(ValueError, match="only authority root"):
        store._bind(
            node_id=a.node_id,
            base_node_id=None,
            set_values={"x": 1},
            delete_keys=(),
        )


def test_set_and_delete_same_key_fails_closed() -> None:
    fabric, a, _ = fabric_with_chain()
    store = OrbitalContextStore(fabric)
    store.bind_root({"x": 1})

    with pytest.raises(ValueError, match="set and deleted together"):
        store.inherit_from_caller(
            a.node_id,
            set_values={"x": 2},
            delete_keys=("x",),
        )


def test_shared_context_frame_can_fan_out_to_multiple_nodes_losslessly() -> None:
    fabric, a, b = fabric_with_chain()
    sibling = fabric.spawn(
        a.node_id,
        "OWL",
        node_id="SIBLING",
        join_to_caller=False,
    )
    store = OrbitalContextStore(fabric)
    store.bind_root({"root": "shared"})
    store.inherit_from_caller(a.node_id, set_values={"branch": "A"})
    shared = store.bind_shared_frame(
        "CTX:DISC:test-shared",
        base_frame_id=a.node_id,
        set_values={"handoff": {"summary": "once"}},
    )
    store.bind_node(
        b.node_id,
        base_node_id=shared.node_id,
        set_values={"child": "B"},
    )
    store.bind_node(
        sibling.node_id,
        base_node_id=shared.node_id,
        set_values={"child": "S"},
    )

    assert store.frame(b.node_id).base_node_id == shared.node_id
    assert store.frame(sibling.node_id).base_node_id == shared.node_id
    assert store.materialize(b.node_id) == {
        "root": "shared",
        "branch": "A",
        "handoff": {"summary": "once"},
        "child": "B",
    }
    assert store.materialize(sibling.node_id) == {
        "root": "shared",
        "branch": "A",
        "handoff": {"summary": "once"},
        "child": "S",
    }


def test_shared_context_frame_binding_is_idempotent_but_immutable() -> None:
    fabric, a, _ = fabric_with_chain()
    store = OrbitalContextStore(fabric)
    store.bind_root({"root": 1})
    store.inherit_from_caller(a.node_id, set_values={"a": 1})

    first = store.bind_shared_frame(
        "CTX:DISC:idempotent",
        base_frame_id=a.node_id,
        set_values={"handoff": 1},
    )
    replay = store.bind_shared_frame(
        "CTX:DISC:idempotent",
        base_frame_id=a.node_id,
        set_values={"handoff": 1},
    )
    assert replay.frame_commitment == first.frame_commitment

    with pytest.raises(RuntimeError, match="immutable"):
        store.bind_shared_frame(
            "CTX:DISC:idempotent",
            base_frame_id=a.node_id,
            set_values={"handoff": 2},
        )


def test_shared_context_frame_id_cannot_collide_with_fabric_node() -> None:
    fabric, a, _ = fabric_with_chain()
    store = OrbitalContextStore(fabric)
    store.bind_root({"root": True})

    with pytest.raises(ValueError, match="must not collide"):
        store.bind_shared_frame(
            a.node_id,
            base_frame_id="AUTH:ROOT",
            set_values={"x": 1},
        )


def test_packet_reconstructs_through_shared_context_frame() -> None:
    fabric, a, b = fabric_with_chain()
    store = OrbitalContextStore(fabric)
    store.bind_root({"root": "R"})
    store.inherit_from_caller(a.node_id, set_values={"a": "A"})
    shared = store.bind_shared_frame(
        "CTX:DISC:packet",
        base_frame_id=a.node_id,
        set_values={"handoff": "H"},
    )
    store.bind_node(
        b.node_id,
        base_node_id=shared.node_id,
        set_values={"b": "B"},
    )

    packet = store.packet(b.node_id)
    decoded = apply_context_packet(packet)

    assert [frame["node_id"] for frame in packet["frames"]] == [
        "AUTH:ROOT",
        a.node_id,
        shared.node_id,
        b.node_id,
    ]
    assert decoded["materialized_context"] == store.materialize(b.node_id)


def test_snapshot_marks_shared_frames_without_exposing_values() -> None:
    fabric, a, _ = fabric_with_chain()
    store = OrbitalContextStore(fabric)
    store.bind_root({"root-secret": "never-show"})
    store.inherit_from_caller(a.node_id)
    store.bind_shared_frame(
        "CTX:DISC:snapshot",
        base_frame_id=a.node_id,
        set_values={"handoff-secret": "never-show-either"},
    )

    snapshot = store.snapshot()
    shared = next(
        row for row in snapshot["frames"]
        if row["node_id"] == "CTX:DISC:snapshot"
    )

    assert shared["frame_kind"] == "SHARED"
    assert snapshot["raw_values_included"] is False
    serialized = repr(snapshot)
    assert "never-show" not in serialized
    assert "never-show-either" not in serialized
