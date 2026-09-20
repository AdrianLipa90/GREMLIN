from __future__ import annotations

import copy
import hashlib
import json
import math

import pytest

from gremlin_mcp.hive_authority import HiveAuthorityRuntime
from gremlin_mcp.memory_consolidation import (
    build_consolidation_route,
    validate_consolidation_plan,
    validate_consolidation_receipt,
)
from gremlin_mcp.memory_exchange import (
    build_exchange_ack,
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
    *,
    subject_id: str,
    producer_id: str,
    generation_id: str,
    sequence: int,
    source_layer: str,
    target_layer: str,
    payload: dict,
    parents: list[str],
    provenance: list[str],
    dependencies: list[str],
    route: tuple[float, ...],
    hop_count: int,
    hop_limit: int,
) -> dict:
    payload_sha = _sha(payload)
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
        "parent_envelope_ids": sorted(set(parents)),
        "provenance": sorted(set(provenance)),
        "dependencies": sorted(set(dependencies)),
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


def _source(sequence: int, value: int) -> dict:
    return _packet(
        subject_id="spectroscopy:ring-6",
        producer_id="SENSOR",
        generation_id="gen-001",
        sequence=sequence,
        source_layer="WORKING",
        target_layer="EPISODIC",
        payload={"kind": "OBSERVATION", "value": value},
        parents=[],
        provenance=[f"run:{sequence}"],
        dependencies=["instrument:spec-1"],
        route=(0.1 * (sequence + 1),),
        hop_count=0,
        hop_limit=8,
    )


def _retention(source_ids: list[str], derived_id: str) -> dict:
    entries = [
        {
            "envelope_id": envelope_id,
            "role": "SOURCE",
            "retention_tier": "COLD",
            "deletion_allowed": False,
            "overwrite_allowed": False,
            "retrievable": True,
        }
        for envelope_id in sorted(source_ids)
    ]
    entries.append(
        {
            "envelope_id": derived_id,
            "role": "DERIVED",
            "retention_tier": "HOT",
            "deletion_allowed": False,
            "overwrite_allowed": False,
            "retrievable": True,
        }
    )
    entries.sort(key=lambda row: (row["role"], row["envelope_id"]))
    core = {
        "schema": "PHASENAV_MEMORY_RETENTION_MANIFEST_V0_1",
        "version": "0.1.0",
        "entries": entries,
        "policy": "RETENTION_HINT_ONLY_NO_DELETION_AUTHORITY",
        "epistemic": "CHYBA",
        "authority": "SHARED_COGNITION_ONLY",
        "canon_allowed": False,
    }
    return {
        **core,
        "manifest_sha256": _sha(core),
        "claims": {
            "source_preservation_required": True,
            "retention_tier_is_storage_hint": True,
            "deletion_authority": False,
            "overwrite_authority": False,
            "canon_promoted": False,
        },
    }


def _plan_and_receipt() -> tuple[dict, dict]:
    first = _source(0, 3)
    second = _source(1, 5)
    source_ids = sorted([first["envelope_id"], second["envelope_id"]])
    ack_first = build_exchange_ack(
        first,
        consumer_id="EPISODIC-STORE",
        outcome="ACCEPTED",
        reason_code="EPISODIC_INGESTED",
    )
    ack_second = build_exchange_ack(
        second,
        consumer_id="EPISODIC-STORE",
        outcome="ACCEPTED",
        reason_code="EPISODIC_INGESTED",
    )
    ack_map = {
        first["envelope_id"]: ack_first["ack_id"],
        second["envelope_id"]: ack_second["ack_id"],
    }
    source_payloads = {
        first["envelope_id"]: first["payload_sha256"],
        second["envelope_id"]: second["payload_sha256"],
    }
    derived_payload = {
        "kind": "PHASENAV_MEMORY_CONSOLIDATED_SEMANTIC_V0_1",
        "derivation_mode": "CALLER_SUPPLIED_SEMANTIC_REDUCTION",
        "reducer_id": "semantic-reducer-v1",
        "source_envelope_ids": source_ids,
        "source_payload_sha256": source_payloads,
        "semantic_payload": {
            "pattern": "stable_pair",
            "observations": 2,
            "mean_value": 4.0,
        },
        "semantic_equivalence_proven": False,
    }
    provenance = sorted({
        "run:0",
        "run:1",
        "consolidation-reducer:semantic-reducer-v1",
    })
    dependencies = sorted({
        "instrument:spec-1",
        *(f"source:{envelope_id}" for envelope_id in source_ids),
        *(f"ack:{ack_id}" for ack_id in ack_map.values()),
    })
    derived = _packet(
        subject_id="spectroscopy:ring-6",
        producer_id="PHASENAV-CONSOLIDATOR",
        generation_id="gen-001",
        sequence=2,
        source_layer="EPISODIC",
        target_layer="SEMANTIC",
        payload=derived_payload,
        parents=source_ids,
        provenance=provenance,
        dependencies=dependencies,
        route=(0.2, -0.05),
        hop_count=1,
        hop_limit=8,
    )
    retention = _retention(source_ids, derived["envelope_id"])
    descriptors = [
        {
            "envelope_id": first["envelope_id"],
            "subject_id": "spectroscopy:ring-6",
            "generation_id": "gen-001",
            "sequence": 0,
            "payload_sha256": first["payload_sha256"],
            "target_layer": "EPISODIC",
        },
        {
            "envelope_id": second["envelope_id"],
            "subject_id": "spectroscopy:ring-6",
            "generation_id": "gen-001",
            "sequence": 1,
            "payload_sha256": second["payload_sha256"],
            "target_layer": "EPISODIC",
        },
    ]
    plan_core = {
        "schema": "PHASENAV_MEMORY_CONSOLIDATION_PLAN_V0_1",
        "version": "0.1.0",
        "subject_id": "spectroscopy:ring-6",
        "generation_id": "gen-001",
        "producer_id": "PHASENAV-CONSOLIDATOR",
        "reducer_id": "semantic-reducer-v1",
        "source_descriptors": descriptors,
        "required_accepted_ack_ids": dict(sorted(ack_map.items())),
        "derived_envelope": derived,
        "retention_manifest": retention,
        "authentication": "UNSIGNED_CONTENT_COMMITMENT",
        "epistemic": "CHYBA",
        "authority": "SHARED_COGNITION_ONLY",
        "canon_allowed": False,
    }
    plan = {
        **plan_core,
        "plan_sha256": _sha(plan_core),
        "claims": {
            "multi_parent_derivation": True,
            "source_immutability_required": True,
            "source_deletion_authority": False,
            "source_overwrite_authority": False,
            "semantic_equivalence_proven": False,
            "reducer_identity_authenticated": False,
            "canon_promoted": False,
        },
    }
    receipt_core = {
        "schema": "PHASENAV_MEMORY_CONSOLIDATION_RECEIPT_V0_1",
        "version": "0.1.0",
        "status": "APPLIED",
        "created": True,
        "plan_sha256": plan["plan_sha256"],
        "derived_envelope_id": derived["envelope_id"],
        "derived_payload_sha256": derived["payload_sha256"],
        "source_envelope_ids": source_ids,
        "source_count": 2,
        "retention_manifest_sha256": retention["manifest_sha256"],
        "before_ledger_sha256": "1" * 64,
        "after_ledger_sha256": "2" * 64,
        "authentication": "UNSIGNED_CONTENT_COMMITMENT",
        "epistemic": "CHYBA",
        "authority": "SHARED_COGNITION_ONLY",
        "canon_allowed": False,
    }
    receipt = {
        **receipt_core,
        "receipt_sha256": _sha(receipt_core),
        "derived_envelope": derived,
        "retention_manifest": retention,
        "claims": {
            "sources_preserved": True,
            "derived_semantic_is_additive": True,
            "semantic_equivalence_proven": False,
            "deletion_performed": False,
            "overwrite_performed": False,
            "canon_promoted": False,
        },
    }
    return plan, receipt


def test_plan_and_receipt_validate_independently() -> None:
    plan, receipt = _plan_and_receipt()
    validated_plan = validate_consolidation_plan(plan)
    validated_receipt = validate_consolidation_receipt(receipt, plan)

    assert validated_plan["derived_envelope"]["target_layer"] == "SEMANTIC"
    assert validated_plan["claims"]["semantic_equivalence_proven"] is False
    assert validated_receipt["status"] == "APPLIED"
    assert validated_receipt["claims"]["sources_preserved"] is True


def test_route_without_receipt_waits_for_phasenav_apply() -> None:
    plan, _ = _plan_and_receipt()
    route = build_consolidation_route(plan)

    assert route["status"] == "AWAITING_PHASENAV_APPLY"
    assert route["steps"][0]["status"] == "REQUIRED"
    assert route["direct_hive_ingest_allowed"] is False
    assert route["semantic_store_ack_required"] is True


def test_route_with_receipt_requires_semantic_store_ack_next() -> None:
    plan, receipt = _plan_and_receipt()
    route = build_consolidation_route(plan, receipt)

    assert route["status"] == "READY_FOR_SEMANTIC_STORE_ACK"
    assert route["steps"][0]["status"] == "COMPLETE"
    assert route["steps"][1] == {
        "order": 2,
        "action": "SEMANTIC_STORE_ACCEPTED_ACK",
        "status": "REQUIRED",
    }
    assert route["steps"][-1]["action"] == "GREMLIN_HIVE_EXCHANGE_BUNDLE_INGEST"
    assert route["claims"]["memory_layer_firewall_enforced"] is True


def test_derived_semantic_cannot_bypass_relational_hive_firewall() -> None:
    plan, receipt = _plan_and_receipt()
    validate_consolidation_receipt(receipt, plan)
    derived = plan["derived_envelope"]

    with pytest.raises(ValueError, match="target_layer=RELATIONAL"):
        ingest_exchange_envelope(HiveAuthorityRuntime(), derived)


def test_retention_deletion_and_semantic_equivalence_tamper_fail_closed() -> None:
    plan, _ = _plan_and_receipt()

    bad_retention = copy.deepcopy(plan)
    bad_retention["retention_manifest"]["entries"][0]["deletion_allowed"] = True
    with pytest.raises(ValueError, match="deletion"):
        validate_consolidation_plan(bad_retention)

    bad_semantics = copy.deepcopy(plan)
    bad_semantics["derived_envelope"]["payload"]["semantic_equivalence_proven"] = True
    with pytest.raises(ValueError):
        validate_consolidation_plan(bad_semantics)


def test_receipt_cannot_switch_derived_envelope_or_plan() -> None:
    plan, receipt = _plan_and_receipt()

    bad_plan = copy.deepcopy(receipt)
    bad_plan["plan_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="plan commitment"):
        validate_consolidation_receipt(bad_plan, plan)

    bad_derived = copy.deepcopy(receipt)
    bad_derived["derived_envelope_id"] = "px:" + ("0" * 64)
    with pytest.raises(ValueError, match="derived envelope"):
        validate_consolidation_receipt(bad_derived, plan)


def test_reducer_and_node_identity_remain_unsigned() -> None:
    plan, receipt = _plan_and_receipt()
    route = build_consolidation_route(plan, receipt)

    assert plan["authentication"] == "UNSIGNED_CONTENT_COMMITMENT"
    assert plan["claims"]["reducer_identity_authenticated"] is False
    assert route["authentication"] == "UNSIGNED_CONTENT_COMMITMENT"
    assert route["claims"]["mutation_authority"] is False
