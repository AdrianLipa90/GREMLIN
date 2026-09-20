from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .memory_exchange import (
    AUTHORITY,
    EPISTEMIC,
    IDENTITY_AUTHENTICATION,
    validate_exchange_envelope,
)

SCHEMA = "GREMLIN_MEMORY_CONSOLIDATION_ROUTE_V0_1"
VERSION = "0.1.0"
PHASENAV_PLAN_SCHEMA = "PHASENAV_MEMORY_CONSOLIDATION_PLAN_V0_1"
PHASENAV_RECEIPT_SCHEMA = "PHASENAV_MEMORY_CONSOLIDATION_RECEIPT_V0_1"
PHASENAV_RETENTION_SCHEMA = "PHASENAV_MEMORY_RETENTION_MANIFEST_V0_1"
PHASENAV_DERIVED_KIND = "PHASENAV_MEMORY_CONSOLIDATED_SEMANTIC_V0_1"


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("consolidation values must be finite JSON data") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    out = value.strip()
    if not out:
        raise ValueError(f"{field} must be non-empty")
    return out


def _hex64(value: Any, field: str) -> str:
    text = _text(value, field).lower()
    if len(text) != 64:
        raise ValueError(f"{field} must be a 64-hex commitment")
    try:
        int(text, 16)
    except ValueError as exc:
        raise ValueError(f"{field} must be hexadecimal") from exc
    return text


def _envelope_id(value: Any) -> str:
    text = _text(value, "envelope_id")
    if not text.startswith("px:"):
        raise ValueError("envelope_id must start with px:")
    _hex64(text[3:], "envelope_id commitment")
    return text


def _ack_id(value: Any) -> str:
    text = _text(value, "ack_id")
    if not text.startswith("pxa:"):
        raise ValueError("ack_id must start with pxa:")
    _hex64(text[4:], "ack_id commitment")
    return text


def _validate_retention_manifest(
    packet: Mapping[str, Any],
    *,
    source_ids: Sequence[str],
    derived_id: str,
) -> dict[str, Any]:
    if not isinstance(packet, Mapping):
        raise ValueError("retention manifest must be a mapping")
    row = dict(packet)
    if row.get("schema") != PHASENAV_RETENTION_SCHEMA or row.get("version") != VERSION:
        raise ValueError("unsupported retention manifest")
    entries_raw = row.get("entries")
    if not isinstance(entries_raw, Sequence) or isinstance(entries_raw, (str, bytes)):
        raise ValueError("retention entries must be a sequence")
    entries = []
    source_set: set[str] = set()
    derived_set: set[str] = set()
    seen: set[str] = set()
    for raw in entries_raw:
        if not isinstance(raw, Mapping):
            raise ValueError("retention entry must be a mapping")
        item = dict(raw)
        envelope_id = _envelope_id(item.get("envelope_id"))
        if envelope_id in seen:
            raise ValueError("duplicate retention envelope")
        seen.add(envelope_id)
        role = _text(item.get("role"), "role").upper()
        if role not in {"SOURCE", "DERIVED"}:
            raise ValueError("unsupported retention role")
        tier = _text(item.get("retention_tier"), "retention_tier").upper()
        if tier not in {"HOT", "WARM", "COLD", "PINNED"}:
            raise ValueError("unsupported retention tier")
        if item.get("deletion_allowed") is not False:
            raise ValueError("retention cannot grant deletion authority")
        if item.get("overwrite_allowed") is not False:
            raise ValueError("retention cannot grant overwrite authority")
        if item.get("retrievable") is not True:
            raise ValueError("retained memory must remain retrievable")
        if role == "SOURCE":
            source_set.add(envelope_id)
        else:
            derived_set.add(envelope_id)
        entries.append({
            "envelope_id": envelope_id,
            "role": role,
            "retention_tier": tier,
            "deletion_allowed": False,
            "overwrite_allowed": False,
            "retrievable": True,
        })
    if source_set != set(source_ids):
        raise ValueError("retention source set mismatch")
    if derived_set != {derived_id}:
        raise ValueError("retention derived set mismatch")
    entries.sort(key=lambda item: (item["role"], item["envelope_id"]))
    core = {
        "schema": PHASENAV_RETENTION_SCHEMA,
        "version": VERSION,
        "entries": entries,
        "policy": "RETENTION_HINT_ONLY_NO_DELETION_AUTHORITY",
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    manifest_sha = _sha256(core)
    if row.get("manifest_sha256") != manifest_sha:
        raise ValueError("retention manifest commitment mismatch")
    claims = row.get("claims")
    if not isinstance(claims, Mapping):
        raise ValueError("retention claims must be a mapping")
    if claims.get("source_preservation_required") is not True:
        raise ValueError("source preservation must remain required")
    if claims.get("retention_tier_is_storage_hint") is not True:
        raise ValueError("retention tier must remain a storage hint")
    for key in ("deletion_authority", "overwrite_authority", "canon_promoted"):
        if claims.get(key) is not False:
            raise ValueError(f"retention claim must remain false: {key}")
    return {**core, "manifest_sha256": manifest_sha, "claims": dict(claims)}


def validate_consolidation_plan(packet: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, Mapping):
        raise ValueError("consolidation plan must be a mapping")
    row = dict(packet)
    if row.get("schema") != PHASENAV_PLAN_SCHEMA or row.get("version") != VERSION:
        raise ValueError("unsupported consolidation plan")
    subject = _text(row.get("subject_id"), "subject_id")
    generation = _text(row.get("generation_id"), "generation_id")
    producer = _text(row.get("producer_id"), "producer_id")
    reducer = _text(row.get("reducer_id"), "reducer_id")

    source_raw = row.get("source_descriptors")
    if not isinstance(source_raw, Sequence) or isinstance(source_raw, (str, bytes)):
        raise ValueError("source_descriptors must be a sequence")
    if len(source_raw) < 2:
        raise ValueError("consolidation requires at least two source descriptors")
    sources = []
    source_ids: list[str] = []
    source_sequences: list[int] = []
    for raw in source_raw:
        if not isinstance(raw, Mapping):
            raise ValueError("source descriptor must be a mapping")
        item = dict(raw)
        envelope_id = _envelope_id(item.get("envelope_id"))
        if envelope_id in source_ids:
            raise ValueError("duplicate consolidation source")
        if _text(item.get("subject_id"), "source.subject_id") != subject:
            raise ValueError("source subject_id mismatch")
        if _text(item.get("generation_id"), "source.generation_id") != generation:
            raise ValueError("source generation_id mismatch")
        sequence = item.get("sequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            raise ValueError("source sequence must be non-negative")
        payload_sha = _hex64(item.get("payload_sha256"), "source.payload_sha256")
        if _text(item.get("target_layer"), "source.target_layer").upper() != "EPISODIC":
            raise ValueError("consolidation source must target EPISODIC")
        sources.append({
            "envelope_id": envelope_id,
            "subject_id": subject,
            "generation_id": generation,
            "sequence": sequence,
            "payload_sha256": payload_sha,
            "target_layer": "EPISODIC",
        })
        source_ids.append(envelope_id)
        source_sequences.append(sequence)
    sources.sort(key=lambda item: (item["sequence"], item["envelope_id"]))
    if list(source_raw) != sources:
        raise ValueError("source_descriptors must be canonical and sorted")

    raw_acks = row.get("required_accepted_ack_ids")
    if not isinstance(raw_acks, Mapping) or set(raw_acks) != set(source_ids):
        raise ValueError("required accepted ACK map must cover every source")
    required_acks = {
        envelope_id: _ack_id(raw_acks[envelope_id])
        for envelope_id in sorted(source_ids)
    }

    derived_raw = row.get("derived_envelope")
    if not isinstance(derived_raw, Mapping):
        raise ValueError("derived_envelope must be a mapping")
    derived = validate_exchange_envelope(derived_raw)
    if derived["subject_id"] != subject or derived["generation_id"] != generation:
        raise ValueError("derived subject/generation mismatch")
    if derived["producer_id"] != producer:
        raise ValueError("derived producer_id mismatch")
    if derived["source_layer"] != "EPISODIC" or derived["target_layer"] != "SEMANTIC":
        raise ValueError("derived envelope must be EPISODIC -> SEMANTIC")
    if set(derived["parent_envelope_ids"]) != set(source_ids):
        raise ValueError("derived parent set mismatch")
    if int(derived["sequence"]) <= max(source_sequences):
        raise ValueError("derived sequence must exceed every source")

    payload = derived["payload"]
    if payload.get("kind") != PHASENAV_DERIVED_KIND:
        raise ValueError("derived semantic kind mismatch")
    if payload.get("derivation_mode") != "CALLER_SUPPLIED_SEMANTIC_REDUCTION":
        raise ValueError("unsupported consolidation derivation mode")
    if payload.get("reducer_id") != reducer:
        raise ValueError("reducer_id mismatch")
    if payload.get("source_envelope_ids") != sorted(source_ids):
        raise ValueError("derived source list mismatch")
    if payload.get("semantic_equivalence_proven") is not False:
        raise ValueError("semantic equivalence must remain unproven")
    source_payloads = payload.get("source_payload_sha256")
    expected_source_payloads = {
        item["envelope_id"]: item["payload_sha256"] for item in sources
    }
    if not isinstance(source_payloads, Mapping) or dict(source_payloads) != expected_source_payloads:
        raise ValueError("derived source payload commitments mismatch")
    if not isinstance(payload.get("semantic_payload"), Mapping):
        raise ValueError("semantic_payload must be a mapping")

    retention = _validate_retention_manifest(
        row.get("retention_manifest"),
        source_ids=source_ids,
        derived_id=derived["envelope_id"],
    )
    if row.get("authentication") != IDENTITY_AUTHENTICATION:
        raise ValueError("consolidation authentication boundary mismatch")
    if row.get("epistemic") != EPISTEMIC or row.get("authority") != AUTHORITY:
        raise ValueError("consolidation epistemic/authority mismatch")
    if row.get("canon_allowed") is not False:
        raise ValueError("consolidation must remain canon_allowed=false")

    core = {
        "schema": PHASENAV_PLAN_SCHEMA,
        "version": VERSION,
        "subject_id": subject,
        "generation_id": generation,
        "producer_id": producer,
        "reducer_id": reducer,
        "source_descriptors": sources,
        "required_accepted_ack_ids": required_acks,
        "derived_envelope": derived,
        "retention_manifest": retention,
        "authentication": IDENTITY_AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    plan_sha = _sha256(core)
    if row.get("plan_sha256") != plan_sha:
        raise ValueError("consolidation plan commitment mismatch")
    claims = row.get("claims")
    if not isinstance(claims, Mapping):
        raise ValueError("consolidation claims must be a mapping")
    if claims.get("multi_parent_derivation") is not True:
        raise ValueError("multi_parent_derivation must remain true")
    if claims.get("source_immutability_required") is not True:
        raise ValueError("source immutability must remain required")
    if claims.get("semantic_equivalence_proven") is not False:
        raise ValueError("semantic equivalence must remain unproven")
    for key in (
        "source_deletion_authority",
        "source_overwrite_authority",
        "reducer_identity_authenticated",
        "canon_promoted",
    ):
        if claims.get(key) is not False:
            raise ValueError(f"consolidation claim must remain false: {key}")
    return {**core, "plan_sha256": plan_sha, "claims": dict(claims)}


def validate_consolidation_receipt(
    receipt: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    validated_plan = validate_consolidation_plan(plan)
    if not isinstance(receipt, Mapping):
        raise ValueError("consolidation receipt must be a mapping")
    row = dict(receipt)
    if row.get("schema") != PHASENAV_RECEIPT_SCHEMA or row.get("version") != VERSION:
        raise ValueError("unsupported consolidation receipt")
    status = _text(row.get("status"), "status")
    if status not in {"APPLIED", "ALREADY_APPLIED"}:
        raise ValueError("unsupported consolidation receipt status")
    created = row.get("created")
    if not isinstance(created, bool):
        raise ValueError("created must be boolean")
    if created != (status == "APPLIED"):
        raise ValueError("receipt status/created mismatch")
    if row.get("plan_sha256") != validated_plan["plan_sha256"]:
        raise ValueError("receipt plan commitment mismatch")
    derived = validated_plan["derived_envelope"]
    if row.get("derived_envelope_id") != derived["envelope_id"]:
        raise ValueError("receipt derived envelope mismatch")
    if row.get("derived_payload_sha256") != derived["payload_sha256"]:
        raise ValueError("receipt derived payload mismatch")
    expected_sources = sorted(
        item["envelope_id"] for item in validated_plan["source_descriptors"]
    )
    if row.get("source_envelope_ids") != expected_sources:
        raise ValueError("receipt source set mismatch")
    if row.get("source_count") != len(expected_sources):
        raise ValueError("receipt source_count mismatch")
    if row.get("retention_manifest_sha256") != validated_plan["retention_manifest"]["manifest_sha256"]:
        raise ValueError("receipt retention manifest mismatch")
    before_sha = _hex64(row.get("before_ledger_sha256"), "before_ledger_sha256")
    after_sha = _hex64(row.get("after_ledger_sha256"), "after_ledger_sha256")
    if row.get("authentication") != IDENTITY_AUTHENTICATION:
        raise ValueError("receipt authentication boundary mismatch")
    if row.get("epistemic") != EPISTEMIC or row.get("authority") != AUTHORITY:
        raise ValueError("receipt epistemic/authority mismatch")
    if row.get("canon_allowed") is not False:
        raise ValueError("receipt must remain canon_allowed=false")

    core = {
        "schema": PHASENAV_RECEIPT_SCHEMA,
        "version": VERSION,
        "status": status,
        "created": created,
        "plan_sha256": validated_plan["plan_sha256"],
        "derived_envelope_id": derived["envelope_id"],
        "derived_payload_sha256": derived["payload_sha256"],
        "source_envelope_ids": expected_sources,
        "source_count": len(expected_sources),
        "retention_manifest_sha256": validated_plan["retention_manifest"]["manifest_sha256"],
        "before_ledger_sha256": before_sha,
        "after_ledger_sha256": after_sha,
        "authentication": IDENTITY_AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    receipt_sha = _sha256(core)
    if row.get("receipt_sha256") != receipt_sha:
        raise ValueError("receipt commitment mismatch")
    if row.get("derived_envelope") != derived:
        raise ValueError("receipt derived envelope packet mismatch")
    if row.get("retention_manifest") != validated_plan["retention_manifest"]:
        raise ValueError("receipt retention manifest packet mismatch")
    claims = row.get("claims")
    if not isinstance(claims, Mapping):
        raise ValueError("receipt claims must be a mapping")
    required_true = ("sources_preserved", "derived_semantic_is_additive")
    for key in required_true:
        if claims.get(key) is not True:
            raise ValueError(f"receipt claim must be true: {key}")
    for key in (
        "semantic_equivalence_proven",
        "deletion_performed",
        "overwrite_performed",
        "canon_promoted",
    ):
        if claims.get(key) is not False:
            raise ValueError(f"receipt claim must remain false: {key}")
    return {**core, "receipt_sha256": receipt_sha, "claims": dict(claims)}


def build_consolidation_route(
    plan: Mapping[str, Any],
    receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the only admitted route from consolidated SEMANTIC state to Hive."""
    validated_plan = validate_consolidation_plan(plan)
    validated_receipt = (
        None if receipt is None else validate_consolidation_receipt(receipt, validated_plan)
    )
    applied = validated_receipt is not None
    derived = validated_plan["derived_envelope"]
    steps = [
        {
            "order": 1,
            "action": "PHASENAV_APPLY_CONSOLIDATION",
            "status": "COMPLETE" if applied else "REQUIRED",
        },
        {
            "order": 2,
            "action": "SEMANTIC_STORE_ACCEPTED_ACK",
            "status": "REQUIRED",
        },
        {
            "order": 3,
            "action": "PHASENAV_PROMOTE_SEMANTIC_TO_RELATIONAL",
            "status": "BLOCKED_UNTIL_PREVIOUS",
        },
        {
            "order": 4,
            "action": "PHASENAV_BUILD_LINEAGE_BUNDLE",
            "status": "BLOCKED_UNTIL_PREVIOUS",
        },
        {
            "order": 5,
            "action": "GREMLIN_HIVE_EXCHANGE_BUNDLE_INGEST",
            "status": "BLOCKED_UNTIL_PREVIOUS",
        },
    ]
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "READY_FOR_SEMANTIC_STORE_ACK" if applied else "AWAITING_PHASENAV_APPLY",
        "plan_sha256": validated_plan["plan_sha256"],
        "receipt_sha256": None if validated_receipt is None else validated_receipt["receipt_sha256"],
        "subject_id": validated_plan["subject_id"],
        "generation_id": validated_plan["generation_id"],
        "derived_envelope_id": derived["envelope_id"],
        "derived_target_layer": derived["target_layer"],
        "source_count": len(validated_plan["source_descriptors"]),
        "retention_manifest_sha256": validated_plan["retention_manifest"]["manifest_sha256"],
        "steps": steps,
        "direct_hive_ingest_allowed": False,
        "semantic_store_ack_required": True,
        "authentication": IDENTITY_AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    return {
        **core,
        "route_sha256": _sha256(core),
        "claims": {
            "memory_layer_firewall_enforced": True,
            "semantic_to_hive_shortcut_allowed": False,
            "semantic_equivalence_proven": False,
            "mutation_authority": False,
            "canon_promoted": False,
        },
    }


__all__ = [
    "PHASENAV_DERIVED_KIND",
    "PHASENAV_PLAN_SCHEMA",
    "PHASENAV_RECEIPT_SCHEMA",
    "PHASENAV_RETENTION_SCHEMA",
    "SCHEMA",
    "VERSION",
    "build_consolidation_route",
    "validate_consolidation_plan",
    "validate_consolidation_receipt",
]
