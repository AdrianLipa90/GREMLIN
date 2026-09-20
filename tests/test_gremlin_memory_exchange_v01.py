from __future__ import annotations

import hashlib
import json
import math

import pytest

from gremlin_mcp.hive_authority import HiveAuthorityRuntime
from gremlin_mcp.memory_exchange import (
    build_exchange_ack,
    ingest_exchange_bundle,
    ingest_exchange_envelope,
    validate_exchange_bundle,
    validate_exchange_envelope,
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
    *,
    subject_id: str = "spectroscopy:ring-6",
    producer_id: str = "PHASENAV",
    generation_id: str = "gen-001",
    sequence: int = 0,
    source_layer: str = "SEMANTIC",
    target_layer: str = "RELATIONAL",
    payload: dict | None = None,
    parents: tuple[str, ...] = (),
    route: tuple[float, ...] = (0.20, -0.05),
    hop_count: int = 0,
    hop_limit: int = 4,
) -> dict:
    body = {"kind": "OBSERVATION", "value": 3} if payload is None else dict(payload)
    payload_sha = _sha(body)
    parent_ids = sorted(set(parents))
    provenance = ["run:123"]
    dependencies = ["model:ring6"]
    core = {
        "schema": "PHASENAV_MEMORY_INFORMATION_EXCHANGE_V0_1",
        "version": "0.1.0",
        "subject_id": subject_id,
        "producer_id": producer_id,
        "generation_id": generation_id,
        "sequence": sequence,
        "source_layer": source_layer,
        "target_layer": target_layer,
        "payload_sha256": payload_sha,
        "parent_envelope_ids": parent_ids,
        "provenance": provenance,
        "dependencies": dependencies,
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
        "payload": body,
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


def _bundle(envelopes: list[dict], acks: list[dict], *, target_id: str) -> dict:
    core = {
        "schema": "PHASENAV_MEMORY_INFORMATION_EXCHANGE_BUNDLE_V0_1",
        "version": "0.1.0",
        "target_envelope_id": target_id,
        "envelopes": envelopes,
        "acks": acks,
        "epistemic": "CHYBA",
        "authority": "SHARED_COGNITION_ONLY",
        "canon_allowed": False,
    }
    return {
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


def _promotion_chain() -> tuple[dict, dict, dict, list[dict]]:
    episodic = _packet(
        sequence=0,
        source_layer="WORKING",
        target_layer="EPISODIC",
        parents=(),
        hop_count=0,
    )
    semantic = _packet(
        producer_id="RAVEN",
        sequence=1,
        source_layer="EPISODIC",
        target_layer="SEMANTIC",
        parents=(episodic["envelope_id"],),
        route=(0.3,),
        hop_count=1,
    )
    relational = _packet(
        producer_id="SPIDER",
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
    return episodic, semantic, relational, acks


def test_validator_recomputes_payload_envelope_and_transport() -> None:
    packet = _packet()
    normalized = validate_exchange_envelope(packet)
    assert normalized["envelope_id"] == packet["envelope_id"]
    assert normalized["payload_sha256"] == packet["payload_sha256"]
    assert abs(normalized["transport"]["modulus"] - 1.0) < 1.0e-12


def test_hive_ingest_is_open_shared_cognition_and_never_auto_latches() -> None:
    runtime = HiveAuthorityRuntime()
    packet = _packet()
    result = ingest_exchange_envelope(runtime, packet)
    assert result["created"] is True
    assert result["hive_state"] == "OPEN"
    assert result["automatic_latch"] is False
    assert all(value is False for value in result["hive_gates"].values())
    assert result["ack"]["outcome"] == "ACCEPTED"
    assert result["ack"]["reason_code"] == "HIVE_INGESTED"
    assert result["authority"] == "SHARED_COGNITION_ONLY"
    assert result["canon_allowed"] is False


def test_replay_is_idempotent_and_returns_the_same_ack() -> None:
    runtime = HiveAuthorityRuntime()
    packet = _packet()
    first = ingest_exchange_envelope(runtime, packet)
    second = ingest_exchange_envelope(runtime, packet)
    assert first["created"] is True
    assert second["created"] is False
    assert first["hive_record_id"] == second["hive_record_id"]
    assert first["ack"] == second["ack"]


def test_child_ingest_requires_parent_first_and_monotonic_sequence() -> None:
    runtime = HiveAuthorityRuntime()
    parent = _packet()
    child = _packet(
        producer_id="GREMLIN",
        sequence=1,
        source_layer="RELATIONAL",
        parents=(parent["envelope_id"],),
        route=(0.3,),
        hop_count=1,
    )

    with pytest.raises(RuntimeError, match="parent not present"):
        ingest_exchange_envelope(runtime, child)

    ingest_exchange_envelope(runtime, parent)
    accepted = ingest_exchange_envelope(runtime, child)
    assert accepted["created"] is True
    child_record = runtime.head(f"exchange:{child['envelope_id']}")
    assert f"exchange:{parent['envelope_id']}" in child_record.dependencies


def test_child_generation_and_sequence_mismatch_fail_closed() -> None:
    runtime = HiveAuthorityRuntime()
    parent = _packet()
    ingest_exchange_envelope(runtime, parent)

    bad_generation = _packet(
        generation_id="gen-002",
        sequence=1,
        source_layer="RELATIONAL",
        parents=(parent["envelope_id"],),
        hop_count=1,
    )
    with pytest.raises(RuntimeError, match="generation mismatch"):
        ingest_exchange_envelope(runtime, bad_generation)

    bad_sequence = _packet(
        sequence=0,
        source_layer="RELATIONAL",
        parents=(parent["envelope_id"],),
        hop_count=1,
    )
    with pytest.raises(RuntimeError, match="sequence"):
        ingest_exchange_envelope(runtime, bad_sequence)


def test_corruption_and_claim_promotion_fail_closed() -> None:
    bad_payload = _packet()
    bad_payload["payload"]["value"] = 4
    with pytest.raises(ValueError, match="payload_sha256"):
        validate_exchange_envelope(bad_payload)

    bad_transport = _packet()
    bad_transport["transport"]["real"] += 0.1
    with pytest.raises(ValueError, match="transport"):
        validate_exchange_envelope(bad_transport)

    bad_claim = _packet()
    bad_claim["claims"]["physical_nonlocal_signalling"] = True
    with pytest.raises(ValueError, match="unsupported claim"):
        validate_exchange_envelope(bad_claim)


def test_hive_ingest_requires_relational_target() -> None:
    runtime = HiveAuthorityRuntime()
    with pytest.raises(ValueError, match="target_layer=RELATIONAL"):
        ingest_exchange_envelope(runtime, _packet(target_layer="SEMANTIC"))


def test_ack_is_exactly_content_bound() -> None:
    packet = _packet()
    ack = build_exchange_ack(packet, consumer_id="GREMLIN-HIVE")
    assert ack["schema"] == "PHASENAV_MEMORY_INFORMATION_EXCHANGE_ACK_V0_1"
    assert ack["envelope_id"] == packet["envelope_id"]
    assert ack["payload_sha256"] == packet["payload_sha256"]
    assert ack["ack_id"].startswith("pxa:")
    assert len(ack["ack_id"]) == 68
    assert ack["authentication"] == "UNSIGNED_CONTENT_COMMITMENT"


def test_durable_restart_preserves_idempotent_exchange_ingest(tmp_path) -> None:
    path = tmp_path / "hive.sqlite3"
    packet = _packet()

    first_runtime = HiveAuthorityRuntime(path)
    first = ingest_exchange_envelope(first_runtime, packet)
    first_runtime.close()

    second_runtime = HiveAuthorityRuntime(path)
    second = ingest_exchange_envelope(second_runtime, packet)
    second_runtime.close()

    assert first["created"] is True
    assert second["created"] is False
    assert first["hive_record_id"] == second["hive_record_id"]
    assert first["ack"] == second["ack"]



def test_lineage_bundle_allows_cross_layer_parent_witnesses_without_hive_pollution() -> None:
    episodic, semantic, relational, acks = _promotion_chain()
    bundle = _bundle(
        [episodic, semantic, relational],
        acks,
        target_id=relational["envelope_id"],
    )

    validated = validate_exchange_bundle(bundle)
    assert validated["target_envelope"]["target_layer"] == "RELATIONAL"
    assert len(validated["accepted_ancestor_ack_ids"]) == 2

    runtime = HiveAuthorityRuntime()
    result = ingest_exchange_bundle(runtime, bundle)
    assert result["created"] is True
    assert result["mode"] == "LINEAGE_BUNDLE"
    assert result["ack"]["outcome"] == "ACCEPTED"
    assert result["ack"]["reason_code"] == "HIVE_LINEAGE_BUNDLE_INGESTED"
    assert len(runtime.table()) == 1

    record = runtime.head(f"exchange:{relational['envelope_id']}")
    assert record.payload["envelope_id"] == relational["envelope_id"]
    assert record.payload["lineage_witness_envelope_ids"] == [
        episodic["envelope_id"],
        semantic["envelope_id"],
    ]
    assert f"lineage:{episodic['envelope_id']}" in record.dependencies
    assert f"lineage:{semantic['envelope_id']}" in record.dependencies


def test_lineage_bundle_replay_is_idempotent() -> None:
    episodic, semantic, relational, acks = _promotion_chain()
    bundle = _bundle(
        [episodic, semantic, relational],
        acks,
        target_id=relational["envelope_id"],
    )
    runtime = HiveAuthorityRuntime()
    first = ingest_exchange_bundle(runtime, bundle)
    second = ingest_exchange_bundle(runtime, bundle)
    assert first["created"] is True
    assert second["created"] is False
    assert first["hive_record_id"] == second["hive_record_id"]
    assert first["ack"] == second["ack"]


def test_lineage_bundle_requires_accepted_ack_for_every_ancestor() -> None:
    episodic, semantic, relational, acks = _promotion_chain()
    bundle = _bundle(
        [episodic, semantic, relational],
        acks[:1],
        target_id=relational["envelope_id"],
    )
    with pytest.raises(ValueError, match="requires an ACCEPTED ACK"):
        validate_exchange_bundle(bundle)


def test_lineage_bundle_rejects_extraneous_non_ancestor_envelope() -> None:
    episodic, semantic, relational, acks = _promotion_chain()
    unrelated = _packet(
        subject_id="other",
        generation_id="gen-other",
        sequence=0,
        source_layer="WORKING",
        target_layer="EPISODIC",
    )
    bundle = _bundle(
        [episodic, unrelated, semantic, relational],
        acks,
        target_id=relational["envelope_id"],
    )
    with pytest.raises(ValueError, match="outside target ancestry"):
        validate_exchange_bundle(bundle)
