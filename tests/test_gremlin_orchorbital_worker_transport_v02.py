from __future__ import annotations

from copy import deepcopy

from gremlin_mcp.orchorbital_context import (
    BUNDLE_PAYLOAD_KEY,
    BUNDLE_REF_PAYLOAD_KEY,
    BUNDLE_SCHEMA,
    PACKET_PAYLOAD_KEY,
    OrbitalContextStore,
    apply_context_bundle,
    apply_context_packet,
)
from gremlin_mcp.orchorbital_fabric import OrchorbitalFabric
from gremlin_mcp.workers import WorkerBroker


def _context_task():
    fabric = OrchorbitalFabric()
    node = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="CTX-SPIDER",
        join_to_caller=False,
    )
    store = OrbitalContextStore(fabric)
    store.bind_root(
        {
            "shared": "S" * 4096,
            "request": "shared orbital context",
            "mode": "root",
        }
    )
    store.inherit_from_caller(
        node.node_id,
        set_values={"mode": "spider", "local": "delta"},
    )
    return fabric, node, store


def test_worker_claim_reduces_context_against_declared_cache_without_mutating_task() -> None:
    _, node, store = _context_task()
    broker = WorkerBroker()
    broker.register_worker("ctx-worker", ["SPIDER"], vector_width=4, max_batch=4)

    full_packet = store.packet(node.node_id)
    root_frame = store.frame("AUTH:ROOT")
    payload = {
        "input": {"query": "relations"},
        PACKET_PAYLOAD_KEY: full_packet,
    }
    queued = broker.enqueue("SPIDER", payload, task_id="ctx-task")

    lease = broker.claim(
        "ctx-worker",
        species="SPIDER",
        limit=1,
        known_context_frames=(root_frame.frame_commitment,),
    )
    delivered = lease["tasks"][0]
    reduced = delivered["payload"][PACKET_PAYLOAD_KEY]

    assert delivered["task_commitment"] == queued["task_commitment"]
    assert reduced["required_base_frame_commitment"] == root_frame.frame_commitment
    assert len(reduced["frames"]) == 1
    assert reduced["packet_bytes"] < full_packet["packet_bytes"]
    transport = lease["orchorbital_context_transport"]
    assert transport["cache_hit_task_count"] == 1
    assert transport["transport_packet_bytes"] < transport["full_packet_bytes"]
    assert transport["canonical_task_commitment_unchanged"] is True
    assert transport["token_saving_claim"] is False

    # Delivery reduction must never rewrite the canonical committed task.
    canonical_packet = broker._tasks["ctx-task"].payload[PACKET_PAYLOAD_KEY]
    assert canonical_packet == full_packet
    assert canonical_packet["required_base_frame_commitment"] is None


def test_reduced_delivery_packet_reconstructs_with_cached_base() -> None:
    _, node, store = _context_task()
    broker = WorkerBroker()
    broker.register_worker("ctx-worker", ["SPIDER"])

    full_packet = store.packet(node.node_id)
    root_frame = store.frame("AUTH:ROOT")
    root_context = store.materialize("AUTH:ROOT")
    broker.enqueue(
        "SPIDER",
        {PACKET_PAYLOAD_KEY: full_packet},
        task_id="ctx-reconstruct",
    )
    lease = broker.claim(
        "ctx-worker",
        species="SPIDER",
        limit=1,
        known_context_frames=(root_frame.frame_commitment,),
    )
    reduced = lease["tasks"][0]["payload"][PACKET_PAYLOAD_KEY]
    decoded = apply_context_packet(
        reduced,
        known_contexts={root_frame.frame_commitment: root_context},
    )

    assert decoded["materialized_context"] == store.materialize(node.node_id)


def test_unknown_cache_commitment_does_not_create_false_hit() -> None:
    _, node, store = _context_task()
    broker = WorkerBroker()
    broker.register_worker("ctx-worker", ["SPIDER"])
    full_packet = store.packet(node.node_id)
    broker.enqueue(
        "SPIDER",
        {PACKET_PAYLOAD_KEY: full_packet},
        task_id="ctx-no-hit",
    )
    unknown = "f" * 64
    lease = broker.claim(
        "ctx-worker",
        species="SPIDER",
        limit=1,
        known_context_frames=(unknown,),
    )
    delivered = lease["tasks"][0]["payload"][PACKET_PAYLOAD_KEY]

    assert delivered["required_base_frame_commitment"] is None
    assert lease["orchorbital_context_transport"]["cache_hit_task_count"] == 0


def test_enqueue_deepcopies_nested_payload_before_commitment_boundary() -> None:
    broker = WorkerBroker()
    nested = {"nested": {"values": [1, 2, 3]}}
    queued = broker.enqueue("SPIDER", nested, task_id="deep-payload")
    nested["nested"]["values"].append(999)

    stored = broker._tasks["deep-payload"].payload
    assert stored == {"nested": {"values": [1, 2, 3]}}
    replay = broker.enqueue(
        "SPIDER",
        {"nested": {"values": [1, 2, 3]}},
        task_id="deep-payload",
    )
    assert replay["task_commitment"] == queued["task_commitment"]


def test_submit_and_result_view_deepcopy_candidate_output() -> None:
    broker = WorkerBroker()
    broker.register_worker("deep-worker", ["SPIDER"])
    broker.enqueue("SPIDER", {"input": 1}, task_id="deep-result")
    lease = broker.claim("deep-worker", species="SPIDER", limit=1)

    output = {"candidate": {"edges": [["a", "b"]]}}
    broker.submit(
        "deep-worker",
        lease["lease_id"],
        [{"task_id": "deep-result", "output": output}],
    )
    output["candidate"]["edges"].append(["corrupt", "outside"])

    first = broker.task_result("deep-result")
    assert first["result"] == {"candidate": {"edges": [["a", "b"]]}}
    first["result"]["candidate"]["edges"].append(["mutate", "view"])
    second = broker.task_result("deep-result")
    assert second["result"] == {"candidate": {"edges": [["a", "b"]]}}


def test_invalid_context_cache_commitment_fails_closed_before_lease() -> None:
    broker = WorkerBroker()
    broker.register_worker("ctx-worker", ["SPIDER"])
    broker.enqueue("SPIDER", {"x": 1}, task_id="ctx-invalid")

    try:
        broker.claim(
            "ctx-worker",
            species="SPIDER",
            known_context_frames=("not-a-commitment",),
        )
    except ValueError as exc:
        assert "64-character hex commitment" in str(exc)
    else:
        raise AssertionError("invalid cache commitment must fail closed")

    assert broker._tasks["ctx-invalid"].state == "QUEUED"


def test_malformed_context_packet_cannot_strand_task_in_lease() -> None:
    broker = WorkerBroker()
    broker.register_worker("ctx-worker-malformed", ["SPIDER"])
    broker.enqueue(
        "SPIDER",
        {
            PACKET_PAYLOAD_KEY: {
                "schema": "GREMLIN_ORCHORBITAL_CONTEXT_PACKET_V0_1",
                "target_node_id": "BROKEN",
                "target_frame_commitment": "0" * 64,
                "target_materialized_commitment": "0" * 64,
                "required_base_frame_commitment": None,
                "frames": [],
                "packet_commitment": "0" * 64,
                "materialized_context_bytes": 1,
                "packet_bytes": 1,
            }
        },
        task_id="ctx-malformed",
    )

    try:
        broker.claim("ctx-worker-malformed", species="SPIDER", limit=1)
    except ValueError:
        pass
    else:
        raise AssertionError("malformed context packet must fail closed")

    assert broker._tasks["ctx-malformed"].state == "QUEUED"
    assert broker._tasks["ctx-malformed"].lease_id is None
    assert broker._tasks["ctx-malformed"].leased_to is None
    assert broker._tasks["ctx-malformed"].lease_expires_ns is None
    assert broker.queue_status()["active_leases"] == 0


def test_multi_task_lease_deduplicates_shared_context_into_one_bundle() -> None:
    fabric = OrchorbitalFabric()
    first = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="CTX-A",
        join_to_caller=False,
    )
    second = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="CTX-B",
        join_to_caller=False,
    )
    store = OrbitalContextStore(fabric)
    store.bind_root(
        {
            "shared": "S" * 8192,
            "memory": "M" * 8192,
            "mode": "root",
        }
    )
    store.inherit_from_caller(first.node_id, set_values={"mode": "a", "local": "A"})
    store.inherit_from_caller(second.node_id, set_values={"mode": "b", "local": "B"})

    broker = WorkerBroker()
    broker.register_worker("ctx-bundle-worker", ["SPIDER"], vector_width=64, max_batch=8)
    scheduler = {"phase36": [0.1] * 36}
    queued_a = broker.enqueue(
        "SPIDER",
        {
            "input": {"query": "same-cluster"},
            "_gremlin_scheduler": scheduler,
            PACKET_PAYLOAD_KEY: store.packet(first.node_id),
        },
        task_id="ctx-bundle-a",
    )
    queued_b = broker.enqueue(
        "SPIDER",
        {
            "input": {"query": "same-cluster"},
            "_gremlin_scheduler": scheduler,
            PACKET_PAYLOAD_KEY: store.packet(second.node_id),
        },
        task_id="ctx-bundle-b",
    )

    lease = broker.claim("ctx-bundle-worker", species="SPIDER", limit=2)
    assert lease["batch_size"] == 2
    bundle = lease[BUNDLE_PAYLOAD_KEY]
    assert bundle is not None
    assert bundle["schema"] == BUNDLE_SCHEMA
    assert bundle["unique_frame_count"] == 3

    commitments = {
        queued_a["task_id"]: queued_a["task_commitment"],
        queued_b["task_id"]: queued_b["task_commitment"],
    }
    refs = {}
    for task in lease["tasks"]:
        payload = task["payload"]
        assert PACKET_PAYLOAD_KEY not in payload
        assert BUNDLE_REF_PAYLOAD_KEY in payload
        assert task["task_commitment"] == commitments[task["task_id"]]
        refs[task["task_id"]] = payload[BUNDLE_REF_PAYLOAD_KEY]

    decoded = apply_context_bundle(bundle)
    updates = decoded["cache_updates"]
    assert updates[refs["ctx-bundle-a"]["target_frame_commitment"]] == store.materialize(
        first.node_id
    )
    assert updates[refs["ctx-bundle-b"]["target_frame_commitment"]] == store.materialize(
        second.node_id
    )

    transport = lease["orchorbital_context_transport"]
    assert transport["bundle_used"] is True
    assert transport["bundle_unique_frame_count"] == 3
    assert transport["transport_packet_bytes"] < transport["full_packet_bytes"]
    assert transport["canonical_task_commitment_unchanged"] is True

    assert broker._tasks["ctx-bundle-a"].payload[PACKET_PAYLOAD_KEY] == store.packet(
        first.node_id
    )
    assert broker._tasks["ctx-bundle-b"].payload[PACKET_PAYLOAD_KEY] == store.packet(
        second.node_id
    )


def test_single_context_task_keeps_backward_compatible_packet_transport() -> None:
    _, node, store = _context_task()
    broker = WorkerBroker()
    broker.register_worker("ctx-single-worker", ["SPIDER"])
    broker.enqueue(
        "SPIDER",
        {PACKET_PAYLOAD_KEY: store.packet(node.node_id)},
        task_id="ctx-single",
    )

    lease = broker.claim("ctx-single-worker", species="SPIDER", limit=1)

    assert lease[BUNDLE_PAYLOAD_KEY] is None
    assert PACKET_PAYLOAD_KEY in lease["tasks"][0]["payload"]
    assert BUNDLE_REF_PAYLOAD_KEY not in lease["tasks"][0]["payload"]
    assert lease["orchorbital_context_transport"]["bundle_used"] is False
