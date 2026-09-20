from __future__ import annotations

import hashlib
import json
import math

import pytest

from gremlin_mcp.bestiary_memory_gateway import (
    build_hive_inventory_as_beast,
    export_hive_delta_as_beast,
    ingest_exchange_envelope_as_beast,
    plan_hive_delta_as_beast,
    read_hive_head,
)
from gremlin_mcp.hive_authority import HiveAuthorityRuntime
from gremlin_mcp.memory_anti_entropy import (
    build_hive_inventory,
    build_hive_manifest,
    divergent_hive_buckets,
)
from gremlin_mcp.memory_capabilities import issue_capability_token


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
    subject_id: str = "spectroscopy:ring-6",
    *,
    generation_id: str = "gen-001",
    sequence: int = 0,
    route: tuple[float, ...] = (0.2, -0.05),
) -> dict:
    payload = {
        "kind": "GRAPH_SNAPSHOT",
        "nodes": ["ring-6", "holonomy"],
        "edges": [["ring-6", "holonomy"]],
    }
    payload_sha = _sha(payload)
    core = {
        "schema": "PHASENAV_MEMORY_INFORMATION_EXCHANGE_V0_1",
        "version": "0.1.0",
        "subject_id": subject_id,
        "producer_id": "SPIDER",
        "generation_id": generation_id,
        "sequence": sequence,
        "source_layer": "SEMANTIC",
        "target_layer": "RELATIONAL",
        "payload_sha256": payload_sha,
        "parent_envelope_ids": [],
        "provenance": ["run:gateway"],
        "dependencies": ["model:ring6"],
        "route_edge_potentials": list(route),
        "hop_count": 0,
        "hop_limit": 8,
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


def _token(
    *,
    beast: str,
    operation: str,
    artifact_type: str,
    subject_scope: str,
    generation_scope: str,
    task_scope: str,
):
    return issue_capability_token(
        beast=beast,
        layer="RELATIONAL",
        operation=operation,
        artifact_type=artifact_type,
        subject_scope=subject_scope,
        generation_scope=generation_scope,
        task_scope=task_scope,
    )


def test_spider_graph_append_ingests_exchange_and_binds_capability_receipt() -> None:
    runtime = HiveAuthorityRuntime()
    packet = _packet()
    token = _token(
        beast="SPIDER",
        operation="GRAPH_APPEND",
        artifact_type="GRAPH_SNAPSHOT",
        subject_scope=packet["subject_id"],
        generation_scope=packet["generation_id"],
        task_scope="spider-ingest",
    )

    result = ingest_exchange_envelope_as_beast(
        runtime,
        packet,
        beast="SPIDER",
        operation="GRAPH_APPEND",
        artifact_type="GRAPH_SNAPSHOT",
        task_id="spider-ingest",
        token=token,
    )

    assert result["schema"] == "GREMLIN_BESTIARY_MEMORY_GATEWAY_V0_1"
    assert result["capability_receipt"]["decision"] == "ALLOW"
    assert result["capability_receipt"]["beast"] == "SPIDER"
    assert result["capability_receipt"]["operation"] == "GRAPH_APPEND"
    assert result["result"]["created"] is True
    assert result["result"]["hive_state"] == "OPEN"


def test_graph_ingest_rejects_read_only_intent_even_with_valid_read_token() -> None:
    runtime = HiveAuthorityRuntime()
    packet = _packet()
    token = _token(
        beast="SPIDER",
        operation="READ_PAYLOAD",
        artifact_type="GRAPH_SNAPSHOT",
        subject_scope=packet["subject_id"],
        generation_scope=packet["generation_id"],
        task_scope="wrong-intent",
    )

    with pytest.raises(PermissionError, match="append/proposal intent"):
        ingest_exchange_envelope_as_beast(
            runtime,
            packet,
            beast="SPIDER",
            operation="READ_PAYLOAD",
            artifact_type="GRAPH_SNAPSHOT",
            task_id="wrong-intent",
            token=token,
        )

    assert runtime.table() == ()


def test_raven_cannot_mint_spider_graph_write_capability() -> None:
    with pytest.raises(PermissionError):
        _token(
            beast="RAVEN",
            operation="GRAPH_APPEND",
            artifact_type="GRAPH_SNAPSHOT",
            subject_scope="spectroscopy:ring-6",
            generation_scope="gen-001",
            task_scope="raven-graph",
        )


def test_hive_read_uses_logical_subject_not_technical_exchange_key() -> None:
    runtime = HiveAuthorityRuntime()
    packet = _packet()
    write_token = _token(
        beast="SPIDER",
        operation="GRAPH_APPEND",
        artifact_type="GRAPH_SNAPSHOT",
        subject_scope=packet["subject_id"],
        generation_scope=packet["generation_id"],
        task_scope="write",
    )
    written = ingest_exchange_envelope_as_beast(
        runtime,
        packet,
        beast="SPIDER",
        operation="GRAPH_APPEND",
        artifact_type="GRAPH_SNAPSHOT",
        task_id="write",
        token=write_token,
    )

    read_token = _token(
        beast="SPIDER",
        operation="READ_PAYLOAD",
        artifact_type="GRAPH_SNAPSHOT",
        subject_scope=packet["subject_id"],
        generation_scope=packet["generation_id"],
        task_scope="read",
    )
    read = read_hive_head(
        runtime,
        beast="SPIDER",
        artifact_type="GRAPH_SNAPSHOT",
        hive_subject_id=written["result"]["hive_subject_id"],
        subject_id=packet["subject_id"],
        generation_id=packet["generation_id"],
        task_id="read",
        token=read_token,
        include_payload=True,
    )
    assert read["capability_receipt"]["decision"] == "ALLOW"
    assert read["result"]["payload"]["subject_id"] == packet["subject_id"]
    assert read["result"]["payload"]["generation_id"] == packet["generation_id"]

    with pytest.raises(PermissionError, match="outside authorized"):
        read_hive_head(
            runtime,
            beast="SPIDER",
            artifact_type="GRAPH_SNAPSHOT",
            hive_subject_id=written["result"]["hive_subject_id"],
            subject_id="another-subject",
            generation_id=packet["generation_id"],
            task_id="read-other",
            token=_token(
                beast="SPIDER",
                operation="READ_PAYLOAD",
                artifact_type="GRAPH_SNAPSHOT",
                subject_scope="another-subject",
                generation_scope=packet["generation_id"],
                task_scope="read-other",
            ),
            include_payload=True,
        )


def test_raven_can_receive_whole_hive_metadata_inventory_but_not_payload_export() -> None:
    runtime = HiveAuthorityRuntime()
    packet = _packet()
    write_token = _token(
        beast="SPIDER",
        operation="GRAPH_APPEND",
        artifact_type="GRAPH_SNAPSHOT",
        subject_scope=packet["subject_id"],
        generation_scope=packet["generation_id"],
        task_scope="seed",
    )
    ingest_exchange_envelope_as_beast(
        runtime,
        packet,
        beast="SPIDER",
        operation="GRAPH_APPEND",
        artifact_type="GRAPH_SNAPSHOT",
        task_id="seed",
        token=write_token,
    )

    inventory_token = _token(
        beast="RAVEN",
        operation="READ_METADATA",
        artifact_type="MEMORY_INDEX",
        subject_scope="*",
        generation_scope="*",
        task_scope="inventory",
    )
    inventory = build_hive_inventory_as_beast(
        runtime,
        beast="RAVEN",
        artifact_type="MEMORY_INDEX",
        task_id="inventory",
        token=inventory_token,
        node_id="HIVE-A",
    )
    assert inventory["capability_receipt"]["decision"] == "ALLOW"
    assert inventory["result"]["exchange_envelope_count"] == 1
    assert inventory["result"]["claims"]["exchange_memory_only"] is True

    with pytest.raises(PermissionError):
        _token(
            beast="RAVEN",
            operation="READ_PAYLOAD",
            artifact_type="MEMORY_INDEX",
            subject_scope="*",
            generation_scope="*",
            task_scope="export",
        )


def test_owl_can_plan_metadata_delta_and_gremlin_can_export_payload_delta() -> None:
    sender = HiveAuthorityRuntime()
    receiver = HiveAuthorityRuntime()
    packet = _packet("delta-subject")
    spider_token = _token(
        beast="SPIDER",
        operation="GRAPH_APPEND",
        artifact_type="GRAPH_SNAPSHOT",
        subject_scope=packet["subject_id"],
        generation_scope=packet["generation_id"],
        task_scope="delta-seed",
    )
    ingest_exchange_envelope_as_beast(
        sender,
        packet,
        beast="SPIDER",
        operation="GRAPH_APPEND",
        artifact_type="GRAPH_SNAPSHOT",
        task_id="delta-seed",
        token=spider_token,
    )

    sender_inventory = build_hive_inventory(sender, node_id="HIVE-A")
    receiver_inventory = build_hive_inventory(receiver, node_id="HIVE-B")
    prefixes = divergent_hive_buckets(sender_inventory, receiver_inventory)
    sender_manifest = build_hive_manifest(sender, node_id="HIVE-A", prefixes=prefixes)
    receiver_manifest = build_hive_manifest(receiver, node_id="HIVE-B", prefixes=prefixes)

    owl_token = _token(
        beast="OWL",
        operation="COMPARE",
        artifact_type="MEMORY_INDEX",
        subject_scope="*",
        generation_scope="*",
        task_scope="delta-plan",
    )
    plan = plan_hive_delta_as_beast(
        beast="OWL",
        artifact_type="MEMORY_INDEX",
        task_id="delta-plan",
        token=owl_token,
        sender_inventory=sender_inventory,
        receiver_inventory=receiver_inventory,
        sender_manifest=sender_manifest,
        receiver_manifest=receiver_manifest,
    )
    assert plan["capability_receipt"]["decision"] == "ALLOW"
    assert plan["result"]["send_envelope_ids"] == [packet["envelope_id"]]

    gremlin_token = _token(
        beast="GREMLIN",
        operation="READ_PAYLOAD",
        artifact_type="MEMORY_INDEX",
        subject_scope="*",
        generation_scope="*",
        task_scope="delta-export",
    )
    delta = export_hive_delta_as_beast(
        sender,
        plan["result"],
        beast="GREMLIN",
        artifact_type="MEMORY_INDEX",
        task_id="delta-export",
        token=gremlin_token,
    )
    assert delta["capability_receipt"]["decision"] == "ALLOW"
    assert delta["result"]["transfers"][0]["envelope_id"] == packet["envelope_id"]
    assert delta["result"]["claims"]["local_priority_not_replicated"] is True


def test_spider_cannot_mint_whole_hive_metadata_token() -> None:
    with pytest.raises(PermissionError, match="scope"):
        _token(
            beast="SPIDER",
            operation="READ_METADATA",
            artifact_type="GRAPH_SNAPSHOT",
            subject_scope="*",
            generation_scope="*",
            task_scope="whole-hive",
        )
