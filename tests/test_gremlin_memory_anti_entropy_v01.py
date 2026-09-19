from __future__ import annotations

import hashlib
import json
import math

import pytest

from gremlin_mcp.hive_authority import HiveAuthorityRuntime
from gremlin_mcp.memory_anti_entropy import (
    apply_hive_delta,
    build_hive_inventory,
    build_hive_manifest,
    divergent_hive_buckets,
    export_hive_delta,
    plan_hive_delta,
    validate_hive_delta,
    validate_hive_inventory,
    validate_hive_manifest,
    validate_hive_plan,
)
from gremlin_mcp.memory_exchange import (
    build_exchange_ack,
    ingest_exchange_bundle,
    ingest_exchange_envelope,
)


def _canonical(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha(value) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _packet(
    subject: str,
    *,
    generation_id: str = "gen-001",
    sequence: int = 0,
    source_layer: str = "SEMANTIC",
    target_layer: str = "RELATIONAL",
    parents: tuple[str, ...] = (),
    route: tuple[float, ...] = (0.2, -0.05),
    hop_count: int = 0,
    hop_limit: int = 8,
) -> dict:
    payload = {"kind": "OBSERVATION", "subject": subject, "value": 3}
    payload_sha = _sha(payload)
    core = {
        "schema": "PHASENAV_MEMORY_INFORMATION_EXCHANGE_V0_1",
        "version": "0.1.0",
        "subject_id": subject,
        "producer_id": "PHASENAV",
        "generation_id": generation_id,
        "sequence": sequence,
        "source_layer": source_layer,
        "target_layer": target_layer,
        "payload_sha256": payload_sha,
        "parent_envelope_ids": sorted(set(parents)),
        "provenance": ["run:123"],
        "dependencies": [f"model:{subject}"],
        "route_edge_potentials": list(route),
        "hop_count": hop_count,
        "hop_limit": hop_limit,
        "epistemic": "CHYBA",
        "authority": "SHARED_COGNITION_ONLY",
        "canon_allowed": False,
    }
    theta = math.fsum(route)
    return {
        **core,
        "envelope_id": "px:" + _sha(core),
        "payload": payload,
        "transport": {
            "real": math.cos(theta),
            "imag": math.sin(theta),
            "phase": math.atan2(math.sin(theta), math.cos(theta)),
            "modulus": 1.0,
        },
        "claims": {
            "content_addressed_payload": True,
            "causal_lineage": True,
            "computational_u1_route_phase": True,
            "producer_identity_authenticated": False,
            "physical_nonlocal_signalling": False,
            "physical_channel_identified": False,
            "canon_promoted": False,
        },
    }


def _bundle(subject: str = "bundle-subject") -> tuple[dict, dict]:
    episodic = _packet(
        subject,
        sequence=0,
        source_layer="WORKING",
        target_layer="EPISODIC",
        parents=(),
        hop_count=0,
    )
    semantic = _packet(
        subject,
        sequence=1,
        source_layer="EPISODIC",
        target_layer="SEMANTIC",
        parents=(episodic["envelope_id"],),
        route=(0.3,),
        hop_count=1,
    )
    relational = _packet(
        subject,
        sequence=2,
        source_layer="SEMANTIC",
        target_layer="RELATIONAL",
        parents=(semantic["envelope_id"],),
        route=(0.4, -0.1),
        hop_count=2,
    )
    acks = [
        build_exchange_ack(
            episodic,
            consumer_id="EPISODIC-STORE",
            outcome="ACCEPTED",
            reason_code="EPISODIC_INGESTED",
        ),
        build_exchange_ack(
            semantic,
            consumer_id="SEMANTIC-STORE",
            outcome="ACCEPTED",
            reason_code="SEMANTIC_INGESTED",
        ),
    ]
    core = {
        "schema": "PHASENAV_MEMORY_INFORMATION_EXCHANGE_BUNDLE_V0_1",
        "version": "0.1.0",
        "target_envelope_id": relational["envelope_id"],
        "envelopes": [episodic, semantic, relational],
        "acks": acks,
        "epistemic": "CHYBA",
        "authority": "SHARED_COGNITION_ONLY",
        "canon_allowed": False,
    }
    bundle = {
        **core,
        "bundle_sha256": _sha(core),
        "claims": {
            "causal_lineage_bundle": True,
            "ack_origin_authenticated": False,
            "physical_nonlocal_signalling": False,
            "physical_channel_identified": False,
            "canon_promoted": False,
        },
    }
    return bundle, relational


def _sync(sender: HiveAuthorityRuntime, receiver: HiveAuthorityRuntime):
    sender_inventory = build_hive_inventory(sender, node_id="HIVE-A")
    receiver_inventory = build_hive_inventory(receiver, node_id="HIVE-B")
    prefixes = divergent_hive_buckets(sender_inventory, receiver_inventory)
    sender_manifest = build_hive_manifest(sender, node_id="HIVE-A", prefixes=prefixes)
    receiver_manifest = build_hive_manifest(receiver, node_id="HIVE-B", prefixes=prefixes)
    plan = plan_hive_delta(
        sender_inventory,
        receiver_inventory,
        sender_manifest,
        receiver_manifest,
    )
    return sender_inventory, receiver_inventory, prefixes, sender_manifest, receiver_manifest, plan


def test_new_exchange_ingest_retains_exportable_proof() -> None:
    runtime = HiveAuthorityRuntime()
    packet = _packet("direct-a")
    ingest_exchange_envelope(runtime, packet)
    record = runtime.head(f"exchange:{packet['envelope_id']}")
    assert record.payload["exchange_packet"]["envelope_id"] == packet["envelope_id"]

    bundle, relational = _bundle()
    ingest_exchange_bundle(runtime, bundle)
    record = runtime.head(f"exchange:{relational['envelope_id']}")
    assert record.payload["lineage_bundle"]["bundle_sha256"] == bundle["bundle_sha256"]


def test_hive_inventory_content_root_is_node_independent() -> None:
    a = HiveAuthorityRuntime()
    b = HiveAuthorityRuntime()
    for runtime in (a, b):
        ingest_exchange_envelope(runtime, _packet("same-a"))
        ingest_exchange_envelope(runtime, _packet("same-b"))

    inv_a = build_hive_inventory(a, node_id="HIVE-A")
    inv_b = build_hive_inventory(b, node_id="HIVE-B")
    assert inv_a["content_root_sha256"] == inv_b["content_root_sha256"]
    assert inv_a["inventory_sha256"] != inv_b["inventory_sha256"]
    assert divergent_hive_buckets(inv_a, inv_b) == ()
    assert validate_hive_inventory(inv_a)["inventory_sha256"] == inv_a["inventory_sha256"]


def test_manifest_is_metadata_only_and_bound_to_inventory() -> None:
    sender = HiveAuthorityRuntime()
    receiver = HiveAuthorityRuntime()
    ingest_exchange_envelope(sender, _packet("a"))
    ingest_exchange_envelope(sender, _packet("b"))
    ingest_exchange_envelope(receiver, _packet("a"))

    sender_inv = build_hive_inventory(sender, node_id="HIVE-A")
    receiver_inv = build_hive_inventory(receiver, node_id="HIVE-B")
    prefixes = divergent_hive_buckets(sender_inv, receiver_inv)
    manifest = build_hive_manifest(sender, node_id="HIVE-A", prefixes=prefixes)
    validated = validate_hive_manifest(manifest, sender_inv)

    assert validated["claims"]["metadata_only"] is True
    assert validated["claims"]["proof_payload_transferred"] is False
    assert "'proof':" not in repr(validated)
    with pytest.raises(ValueError):
        validate_hive_manifest(manifest, receiver_inv)


def test_plan_and_delta_transfer_only_missing_exchange_envelopes() -> None:
    sender = HiveAuthorityRuntime()
    receiver = HiveAuthorityRuntime()
    packet_a = _packet("a")
    packet_b = _packet("b")
    ingest_exchange_envelope(sender, packet_a)
    ingest_exchange_envelope(sender, packet_b)
    ingest_exchange_envelope(receiver, packet_a)

    *_, plan = _sync(sender, receiver)
    validated = validate_hive_plan(plan)
    assert validated["send_envelope_ids"] == [packet_b["envelope_id"]]
    assert validated["receiver_only_envelope_ids"] == []
    assert validated["blocked_unexportable_envelope_ids"] == []

    delta = export_hive_delta(sender, plan)
    assert len(delta["transfers"]) == 1
    assert delta["transfers"][0]["envelope_id"] == packet_b["envelope_id"]
    assert validate_hive_delta(delta)["delta_sha256"] == delta["delta_sha256"]


def test_apply_hive_delta_converges_exchange_set_and_returns_stable_peer_ack() -> None:
    sender = HiveAuthorityRuntime()
    receiver = HiveAuthorityRuntime()
    packet_a = _packet("a")
    packet_b = _packet("b")
    ingest_exchange_envelope(sender, packet_a)
    ingest_exchange_envelope(sender, packet_b)
    ingest_exchange_envelope(receiver, packet_a)

    sender_inv, _, _, _, _, plan = _sync(sender, receiver)
    delta = export_hive_delta(sender, plan)
    first = apply_hive_delta(receiver, delta, receiver_node_id="HIVE-B")
    second = apply_hive_delta(receiver, delta, receiver_node_id="HIVE-B")

    after = build_hive_inventory(receiver, node_id="HIVE-B")
    assert first["status"] == "APPLIED"
    assert first["created"] == 1
    assert second["status"] == "ALREADY_APPLIED"
    assert first["acks"] == second["acks"]
    assert first["acks"][0]["consumer_id"] == "GREMLIN-HIVE:HIVE-B"
    assert first["acks"][0]["reason_code"] == "HIVE_ANTI_ENTROPY_PRESENT"
    assert after["content_root_sha256"] == sender_inv["content_root_sha256"]


def test_bundle_replication_persists_target_only_with_full_witness() -> None:
    sender = HiveAuthorityRuntime()
    receiver = HiveAuthorityRuntime()
    bundle, relational = _bundle()
    ingest_exchange_bundle(sender, bundle)

    *_, plan = _sync(sender, receiver)
    delta = export_hive_delta(sender, plan)
    result = apply_hive_delta(receiver, delta, receiver_node_id="HIVE-B")

    assert result["created"] == 1
    assert len(receiver.table()) == 1
    record = receiver.head(f"exchange:{relational['envelope_id']}")
    assert record.payload["lineage_bundle"]["bundle_sha256"] == bundle["bundle_sha256"]
    assert record.payload["lineage_witness_envelope_ids"] == [
        bundle["envelopes"][0]["envelope_id"],
        bundle["envelopes"][1]["envelope_id"],
    ]


def test_receiver_only_exchange_memory_is_preserved() -> None:
    sender = HiveAuthorityRuntime()
    receiver = HiveAuthorityRuntime()
    common = _packet("common")
    sender_only = _packet("sender-only")
    receiver_only = _packet("receiver-only")
    for packet in (common, sender_only):
        ingest_exchange_envelope(sender, packet)
    for packet in (common, receiver_only):
        ingest_exchange_envelope(receiver, packet)

    *_, plan = _sync(sender, receiver)
    assert receiver_only["envelope_id"] in plan["receiver_only_envelope_ids"]
    delta = export_hive_delta(sender, plan)
    apply_hive_delta(receiver, delta, receiver_node_id="HIVE-B")

    assert receiver.head(f"exchange:{receiver_only['envelope_id']}").payload["envelope_id"] == receiver_only["envelope_id"]


def test_stale_receiver_exchange_inventory_rejects_delta() -> None:
    sender = HiveAuthorityRuntime()
    receiver = HiveAuthorityRuntime()
    ingest_exchange_envelope(sender, _packet("a"))
    *_, plan = _sync(sender, receiver)
    delta = export_hive_delta(sender, plan)

    ingest_exchange_envelope(receiver, _packet("receiver-new"))
    before_ids = {row.payload["envelope_id"] for row in receiver.table()}

    with pytest.raises(RuntimeError, match="changed since delta planning"):
        apply_hive_delta(receiver, delta, receiver_node_id="HIVE-B")

    assert {row.payload["envelope_id"] for row in receiver.table()} == before_ids


def test_non_exchange_hive_state_does_not_invalidate_exchange_sync_plan() -> None:
    sender = HiveAuthorityRuntime()
    receiver = HiveAuthorityRuntime()
    ingest_exchange_envelope(sender, _packet("a"))
    *_, plan = _sync(sender, receiver)
    delta = export_hive_delta(sender, plan)

    receiver.place_idempotent(
        subject_id="local:note",
        payload={"kind": "LOCAL", "text": "receiver-local cognition"},
        priority=0.5,
        semantic_key="local/note",
        relation_phase=0.0,
    )
    result = apply_hive_delta(receiver, delta, receiver_node_id="HIVE-B")
    assert result["status"] == "APPLIED"
    assert receiver.head("local:note").payload["kind"] == "LOCAL"


def test_legacy_exchange_record_is_visible_but_blocked_from_export() -> None:
    sender = HiveAuthorityRuntime()
    receiver = HiveAuthorityRuntime()
    packet = _packet("legacy")
    sender.place_idempotent(
        subject_id=f"exchange:{packet['envelope_id']}",
        payload={
            "kind": "PHASENAV_MEMORY_INFORMATION_EXCHANGE",
            "envelope_id": packet["envelope_id"],
            "generation_id": packet["generation_id"],
            "sequence": packet["sequence"],
        },
        priority=0.82,
        semantic_key="memory-exchange/legacy",
        relation_phase=0.0,
    )

    *_, plan = _sync(sender, receiver)
    assert plan["send_envelope_ids"] == []
    assert plan["blocked_unexportable_envelope_ids"] == [packet["envelope_id"]]
    with pytest.raises(RuntimeError, match="unexportable"):
        export_hive_delta(sender, plan)


def test_sqlite_receiver_preserves_synced_exchange_after_restart(tmp_path) -> None:
    sender = HiveAuthorityRuntime()
    packet = _packet("durable")
    ingest_exchange_envelope(sender, packet)

    path = tmp_path / "receiver.sqlite3"
    receiver = HiveAuthorityRuntime(path)
    *_, plan = _sync(sender, receiver)
    delta = export_hive_delta(sender, plan)
    apply_hive_delta(receiver, delta, receiver_node_id="HIVE-B")
    expected = build_hive_inventory(receiver, node_id="HIVE-B")["content_root_sha256"]
    receiver.close()

    reopened = HiveAuthorityRuntime(path)
    actual = build_hive_inventory(reopened, node_id="HIVE-B")["content_root_sha256"]
    reopened.close()
    assert actual == expected
