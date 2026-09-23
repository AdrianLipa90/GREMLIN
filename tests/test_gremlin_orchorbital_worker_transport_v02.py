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


def test_worker_claim_prefers_same_orbital_context_branch_when_geometry_ties() -> None:
    fabric = OrchorbitalFabric()
    parent_a = fabric.spawn(
        "AUTH:ROOT",
        "BEES",
        node_id="PARENT-A",
        join_to_caller=False,
    )
    parent_b = fabric.spawn(
        "AUTH:ROOT",
        "BEES",
        node_id="PARENT-B",
        join_to_caller=False,
    )
    a1 = fabric.spawn(
        parent_a.node_id,
        "SPIDER",
        node_id="A1",
        join_to_caller=False,
    )
    a2 = fabric.spawn(
        parent_a.node_id,
        "SPIDER",
        node_id="A2",
        join_to_caller=False,
    )
    b1 = fabric.spawn(
        parent_b.node_id,
        "SPIDER",
        node_id="B1",
        join_to_caller=False,
    )

    store = OrbitalContextStore(fabric)
    store.bind_root({"shared": "root"})
    store.inherit_from_caller(parent_a.node_id, set_values={"branch": "A"})
    store.inherit_from_caller(parent_b.node_id, set_values={"branch": "B"})
    store.inherit_from_caller(a1.node_id, set_values={"leaf": "A1"})
    store.inherit_from_caller(a2.node_id, set_values={"leaf": "A2"})
    store.inherit_from_caller(b1.node_id, set_values={"leaf": "B1"})

    broker = WorkerBroker()
    broker.register_worker("affinity-worker", ["SPIDER"], vector_width=64, max_batch=2)

    common_phase = [0.75] * 36
    broker.enqueue(
        "SPIDER",
        {
            "_gremlin_scheduler": {
                "phase36": common_phase,
                "urgency": 1.0,
                "ready": True,
            },
            PACKET_PAYLOAD_KEY: store.packet(a1.node_id),
        },
        task_id="A1",
    )
    broker.enqueue(
        "SPIDER",
        {
            "_gremlin_scheduler": {
                "phase36": common_phase,
                "urgency": 0.0,
                "ready": True,
            },
            PACKET_PAYLOAD_KEY: store.packet(a2.node_id),
        },
        task_id="A2",
    )
    broker.enqueue(
        "SPIDER",
        {
            "_gremlin_scheduler": {
                "phase36": common_phase,
                "urgency": 0.0,
                "ready": True,
            },
            PACKET_PAYLOAD_KEY: store.packet(b1.node_id),
        },
        task_id="B1",
    )

    lease = broker.claim("affinity-worker", species="SPIDER", limit=2)
    ids = [task["task_id"] for task in lease["tasks"]]

    assert ids == ["A1", "A2"]
    scheduler = lease["scheduler"]["batch_selection"]
    assert scheduler["context_affinity_active"] is True
    assert scheduler["mean_context_affinity"] > 0.5
    assert lease["orchorbital_context_transport"]["bundle_used"] is True


def test_worker_claim_species_selection_prefers_receiver_cached_branch_on_geometry_tie() -> None:
    fabric = OrchorbitalFabric()
    parent_a = fabric.spawn(
        "AUTH:ROOT",
        "BEES",
        node_id="SPECIES-PARENT-A",
        join_to_caller=False,
    )
    parent_b = fabric.spawn(
        "AUTH:ROOT",
        "BEES",
        node_id="SPECIES-PARENT-B",
        join_to_caller=False,
    )
    spider = fabric.spawn(
        parent_a.node_id,
        "SPIDER",
        node_id="SPECIES-SPIDER",
        join_to_caller=False,
    )
    owl = fabric.spawn(
        parent_b.node_id,
        "OWL",
        node_id="SPECIES-OWL",
        join_to_caller=False,
    )

    store = OrbitalContextStore(fabric)
    store.bind_root({"shared": "root"})
    store.inherit_from_caller(parent_a.node_id, set_values={"branch": "A"})
    store.inherit_from_caller(parent_b.node_id, set_values={"branch": "B"})
    store.inherit_from_caller(spider.node_id, set_values={"leaf": "SPIDER"})
    store.inherit_from_caller(owl.node_id, set_values={"leaf": "OWL"})

    broker = WorkerBroker()
    broker.register_worker(
        "species-locality-worker",
        ["SPIDER", "OWL"],
        vector_width=8,
        max_batch=2,
    )
    common_scheduler = {
        "phase36": [1.25] * 36,
        "ready": True,
        "noise": 0.05,
        "urgency": 0.0,
        "temperature": 0.4,
    }
    broker.enqueue(
        "SPIDER",
        {
            "_gremlin_scheduler": common_scheduler,
            PACKET_PAYLOAD_KEY: store.packet(spider.node_id),
        },
        task_id="cached-species-task",
    )
    broker.enqueue(
        "OWL",
        {
            "_gremlin_scheduler": common_scheduler,
            PACKET_PAYLOAD_KEY: store.packet(owl.node_id),
        },
        task_id="other-species-task",
    )

    parent_a_frame = store.frame(parent_a.node_id).frame_commitment
    lease = broker.claim(
        "species-locality-worker",
        known_context_frames=(parent_a_frame,),
        limit=1,
    )

    assert lease["species"] == "SPIDER"
    selection = lease["scheduler"]["species_selection"]
    assert selection["selection_basis"] == (
        "GEOMETRY_PHASE_STATE_PLUS_RECEIVER_LOCALITY_THEN_CADENCE"
    )
    assert selection["queues"]["SPIDER"]["receiver_locality_hint"] > 0.0
    assert selection["queues"]["OWL"]["receiver_locality_hint"] == 0.0


def test_malformed_context_packet_is_rejected_at_enqueue_admission() -> None:
    broker = WorkerBroker()
    malformed = {
        "schema": "GREMLIN_ORCHORBITAL_CONTEXT_PACKET_V0_1",
        "target_node_id": "BAD",
        "target_frame_commitment": "0" * 64,
        "target_materialized_commitment": "0" * 64,
        "required_base_frame_commitment": None,
        "frames": [],
        "packet_commitment": "0" * 64,
        "materialized_context_bytes": 1,
        "packet_bytes": 1,
    }

    try:
        broker.enqueue(
            "SPIDER",
            {PACKET_PAYLOAD_KEY: malformed},
            task_id="bad-context-admission",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("malformed canonical context must fail at enqueue")

    assert "bad-context-admission" not in broker._tasks


def test_reduced_context_packet_cannot_be_enqueued_as_canonical_task() -> None:
    _, node, store = _context_task()
    full_packet = store.packet(node.node_id)
    root = store.frame("AUTH:ROOT").frame_commitment
    from gremlin_mcp.orchorbital_context import reduce_context_packet

    reduced = reduce_context_packet(
        full_packet,
        receiver_known_frames=(root,),
    )
    assert reduced["required_base_frame_commitment"] == root

    broker = WorkerBroker()
    try:
        broker.enqueue(
            "SPIDER",
            {PACKET_PAYLOAD_KEY: reduced},
            task_id="reduced-canonical",
        )
    except ValueError as exc:
        assert "self-contained" in str(exc)
    else:
        raise AssertionError("reduced packet must not become canonical task state")


def test_bundle_transport_fields_are_rejected_at_enqueue_boundary() -> None:
    broker = WorkerBroker()

    for task_id, key in (
        ("bundle-owned", BUNDLE_PAYLOAD_KEY),
        ("bundle-ref-owned", BUNDLE_REF_PAYLOAD_KEY),
    ):
        try:
            broker.enqueue(
                "SPIDER",
                {key: {"not": "caller-owned"}},
                task_id=task_id,
            )
        except ValueError as exc:
            assert "broker-owned transport fields" in str(exc)
        else:
            raise AssertionError("transport-only context field must fail at enqueue")

        assert task_id not in broker._tasks


def _same_species_index_fixture(*, local_count: int = 3, unrelated_count: int = 20):
    fabric = OrchorbitalFabric(max_nodes=local_count + unrelated_count + 3)
    target_anchor = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="INDEX-TARGET-ANCHOR",
        join_to_caller=False,
    )
    other_anchor = fabric.spawn(
        "AUTH:ROOT",
        "SPIDER",
        node_id="INDEX-OTHER-ANCHOR",
        join_to_caller=False,
    )
    store = OrbitalContextStore(fabric)
    store.bind_root({"shared": "same-species-index"})
    store.inherit_from_caller(
        target_anchor.node_id,
        set_values={"branch": "target"},
    )
    store.inherit_from_caller(
        other_anchor.node_id,
        set_values={"branch": "other"},
    )

    broker = WorkerBroker(max_pending=local_count + unrelated_count + 8)
    broker.register_worker(
        "same-species-index-worker",
        ["SPIDER"],
        vector_width=64,
        max_batch=16,
    )
    scheduler = {
        "phase36": [0.4] * 36,
        "ready": True,
        "noise": 0.05,
        "urgency": 0.0,
    }

    local_ids = []
    for index in range(local_count):
        node = fabric.spawn(
            target_anchor.node_id,
            "SPIDER",
            node_id=f"INDEX-TARGET-{index}",
            join_to_caller=False,
        )
        store.inherit_from_caller(node.node_id, set_values={"leaf": index})
        task_id = f"index-target-{index}"
        local_ids.append(task_id)
        broker.enqueue(
            "SPIDER",
            {
                "class": "target",
                "_gremlin_scheduler": scheduler,
                PACKET_PAYLOAD_KEY: store.packet(node.node_id),
            },
            task_id=task_id,
        )

    for index in range(unrelated_count):
        node = fabric.spawn(
            other_anchor.node_id,
            "SPIDER",
            node_id=f"INDEX-OTHER-{index}",
            join_to_caller=False,
        )
        store.inherit_from_caller(node.node_id, set_values={"leaf": index})
        broker.enqueue(
            "SPIDER",
            {
                "class": "other",
                "_gremlin_scheduler": scheduler,
                PACKET_PAYLOAD_KEY: store.packet(node.node_id),
            },
            task_id=f"index-other-{index}",
        )

    known = (
        store.frame("AUTH:ROOT").frame_commitment,
        store.frame(target_anchor.node_id).frame_commitment,
    )
    return broker, store, target_anchor, local_ids, known


def test_same_species_warm_ancestry_index_bounds_scheduler_candidate_set() -> None:
    broker, _, _, local_ids, known = _same_species_index_fixture(
        local_count=3,
        unrelated_count=40,
    )

    lease = broker.claim(
        "same-species-index-worker",
        species="SPIDER",
        limit=3,
        known_context_frames=known,
    )
    scope = lease["scheduler"]["context_candidate_scope"]
    claimed = [row["task_id"] for row in lease["tasks"]]

    assert scope["active"] is True
    assert scope["hit"] is True
    assert scope["species_queue_count"] == 43
    assert scope["indexed_local_count"] == 3
    assert scope["fairness_candidate_count"] <= 4
    assert scope["candidate_count"] <= 7
    assert scope["candidate_scan_reduction_proxy"] > 0.80
    assert set(claimed) == set(local_ids)
    assert all(row["payload"]["class"] == "target" for row in lease["tasks"])


def test_same_species_cold_claim_preserves_full_queue_candidate_semantics() -> None:
    broker, _, _, _, _ = _same_species_index_fixture(
        local_count=2,
        unrelated_count=8,
    )

    lease = broker.claim(
        "same-species-index-worker",
        species="SPIDER",
        limit=2,
    )
    scope = lease["scheduler"]["context_candidate_scope"]

    assert scope["active"] is False
    assert scope["hit"] is False
    assert scope["species_queue_count"] == 10
    assert scope["candidate_count"] == 10
    assert scope["candidate_scan_reduction_proxy"] == 0.0


def test_same_species_context_index_includes_bounded_oldest_fairness_window() -> None:
    broker, _, _, _, known = _same_species_index_fixture(
        local_count=1,
        unrelated_count=12,
    )

    lease = broker.claim(
        "same-species-index-worker",
        species="SPIDER",
        limit=1,
        known_context_frames=known,
    )
    scope = lease["scheduler"]["context_candidate_scope"]

    assert scope["indexed_local_count"] == 1
    assert scope["fairness_candidate_count"] == 4
    assert scope["candidate_count"] == 5
    assert scope["candidate_count"] < scope["species_queue_count"]


def test_context_ancestry_index_membership_is_removed_when_task_leaves_queue() -> None:
    broker, _, _, _, known = _same_species_index_fixture(
        local_count=1,
        unrelated_count=5,
    )
    before = broker.queue_status()
    before_refs = before["context_index_member_references"]["SPIDER"]

    lease = broker.claim(
        "same-species-index-worker",
        species="SPIDER",
        limit=1,
        known_context_frames=known,
    )
    after = broker.queue_status()
    after_refs = after["context_index_member_references"]["SPIDER"]

    assert lease["tasks"][0]["payload"]["class"] == "target"
    assert after_refs < before_refs
    assert after["queued_index_counts"]["SPIDER"] == 5
