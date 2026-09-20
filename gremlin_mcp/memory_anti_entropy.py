from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .hive_authority import HiveAuthorityRuntime
from .memory_exchange import (
    AUTHORITY,
    EPISTEMIC,
    IDENTITY_AUTHENTICATION,
    build_exchange_ack,
    ingest_exchange_bundle,
    ingest_exchange_envelope,
    validate_exchange_bundle,
    validate_exchange_envelope,
)

HIVE_SYNC_VERSION = "0.1.0"
HIVE_SYNC_INVENTORY_SCHEMA = "GREMLIN_HIVE_MEMORY_ANTI_ENTROPY_INVENTORY_V0_1"
HIVE_SYNC_MANIFEST_SCHEMA = "GREMLIN_HIVE_MEMORY_ANTI_ENTROPY_BUCKET_MANIFEST_V0_1"
HIVE_SYNC_PLAN_SCHEMA = "GREMLIN_HIVE_MEMORY_ANTI_ENTROPY_DELTA_PLAN_V0_1"
HIVE_SYNC_DELTA_SCHEMA = "GREMLIN_HIVE_MEMORY_ANTI_ENTROPY_DELTA_V0_1"
BUCKET_HEX_WIDTH = 2
EXCHANGE_KIND = "PHASENAV_MEMORY_INFORMATION_EXCHANGE"


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
        raise ValueError("Hive sync values must be finite JSON data") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    out = value.strip()
    if not out:
        raise ValueError(f"{field} must be non-empty")
    return out


def _commitment(value: Any, field: str) -> str:
    text = _text(value, field).lower()
    if len(text) != 64:
        raise ValueError(f"{field} must be 64 hexadecimal characters")
    try:
        int(text, 16)
    except ValueError as exc:
        raise ValueError(f"{field} must be hexadecimal") from exc
    return text


def _envelope_id(value: Any) -> str:
    text = _text(value, "envelope_id")
    if not text.startswith("px:"):
        raise ValueError("envelope_id must start with px:")
    _commitment(text[3:], "envelope_id commitment")
    return text


def _bucket(envelope_id: str) -> str:
    return _envelope_id(envelope_id)[3:3 + BUCKET_HEX_WIDTH]


def _prefix(value: Any) -> str:
    text = _text(value, "bucket_prefix").lower()
    if len(text) != BUCKET_HEX_WIDTH:
        raise ValueError("bucket prefix must contain two hex characters")
    try:
        int(text, 16)
    except ValueError as exc:
        raise ValueError("bucket prefix must be hexadecimal") from exc
    return text


def _exchange_records(runtime: HiveAuthorityRuntime):
    rows = []
    for record in runtime.table():
        payload = dict(record.payload)
        if payload.get("kind") != EXCHANGE_KIND:
            continue
        envelope_id = _envelope_id(payload.get("envelope_id"))
        if record.subject_id != f"exchange:{envelope_id}":
            raise RuntimeError("exchange Hive subject/envelope mismatch")
        rows.append(record)
    return tuple(sorted(rows, key=lambda record: dict(record.payload)["envelope_id"]))


def _descriptor(record) -> dict[str, Any]:
    payload = dict(record.payload)
    envelope_id = _envelope_id(payload.get("envelope_id"))
    proof_kind = "LEGACY_UNEXPORTABLE"
    proof_sha256 = _sha256({
        "envelope_id": envelope_id,
        "record_id": record.record_id,
        "stored_payload": payload,
    })
    exportable = False

    bundle = payload.get("lineage_bundle")
    packet = payload.get("exchange_packet")
    if isinstance(bundle, Mapping):
        validated = validate_exchange_bundle(bundle)
        if validated["target_envelope_id"] != envelope_id:
            raise RuntimeError("stored lineage bundle target does not match Hive envelope")
        proof_kind = "LINEAGE_BUNDLE"
        proof_sha256 = validated["bundle_sha256"]
        exportable = True
    elif isinstance(packet, Mapping):
        validated = validate_exchange_envelope(packet)
        if validated["envelope_id"] != envelope_id:
            raise RuntimeError("stored exchange packet does not match Hive envelope")
        proof_kind = "ENVELOPE"
        proof_sha256 = _sha256(validated)
        exportable = True

    return {
        "envelope_id": envelope_id,
        "proof_kind": proof_kind,
        "proof_sha256": proof_sha256,
        "replication_exportable": exportable,
    }


def _descriptors(runtime: HiveAuthorityRuntime) -> tuple[dict[str, Any], ...]:
    return tuple(_descriptor(record) for record in _exchange_records(runtime))


def _bucket_root(prefix: str, envelope_ids: Sequence[str]) -> str:
    return _sha256({
        "prefix": _prefix(prefix),
        "envelope_ids": sorted(envelope_ids),
    })


def build_hive_inventory(
    runtime: HiveAuthorityRuntime,
    *,
    node_id: str,
) -> dict[str, Any]:
    node = _text(node_id, "node_id")
    by_bucket: dict[str, list[str]] = {}
    descriptors = _descriptors(runtime)
    for descriptor in descriptors:
        by_bucket.setdefault(_bucket(descriptor["envelope_id"]), []).append(
            descriptor["envelope_id"]
        )
    buckets = {
        prefix: {
            "envelope_count": len(ids),
            "root_sha256": _bucket_root(prefix, ids),
        }
        for prefix, ids in sorted(by_bucket.items())
    }
    content_core = {
        "exchange_envelope_count": len(descriptors),
        "buckets": buckets,
    }
    core = {
        "schema": HIVE_SYNC_INVENTORY_SCHEMA,
        "version": HIVE_SYNC_VERSION,
        "node_id": node,
        "content_root_sha256": _sha256(content_core),
        **content_core,
        "authentication": IDENTITY_AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    return {
        **core,
        "inventory_sha256": _sha256(core),
        "claims": {
            "exchange_memory_only": True,
            "full_hive_state_replication": False,
            "node_identity_authenticated": False,
            "deletion_authority": False,
            "overwrite_authority": False,
            "canon_promoted": False,
        },
    }


def validate_hive_inventory(packet: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, Mapping):
        raise ValueError("Hive inventory must be a mapping")
    row = dict(packet)
    if row.get("schema") != HIVE_SYNC_INVENTORY_SCHEMA or row.get("version") != HIVE_SYNC_VERSION:
        raise ValueError("unsupported Hive anti-entropy inventory")
    node = _text(row.get("node_id"), "node_id")
    count = row.get("exchange_envelope_count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError("exchange_envelope_count must be non-negative")
    raw_buckets = row.get("buckets")
    if not isinstance(raw_buckets, Mapping):
        raise ValueError("inventory buckets must be a mapping")
    buckets: dict[str, dict[str, Any]] = {}
    total = 0
    for raw_prefix, raw_summary in raw_buckets.items():
        prefix = _prefix(raw_prefix)
        if not isinstance(raw_summary, Mapping):
            raise ValueError("bucket summary must be a mapping")
        n = raw_summary.get("envelope_count")
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
            raise ValueError("non-empty inventory buckets require positive count")
        root = _commitment(raw_summary.get("root_sha256"), "root_sha256")
        buckets[prefix] = {"envelope_count": n, "root_sha256": root}
        total += n
    if total != count:
        raise ValueError("inventory bucket counts do not match total")
    content_core = {"exchange_envelope_count": count, "buckets": buckets}
    content_root = _sha256(content_core)
    if row.get("content_root_sha256") != content_root:
        raise ValueError("content_root_sha256 mismatch")
    if row.get("authentication") != IDENTITY_AUTHENTICATION:
        raise ValueError("inventory authentication boundary mismatch")
    if row.get("epistemic") != EPISTEMIC or row.get("authority") != AUTHORITY:
        raise ValueError("inventory epistemic/authority mismatch")
    if row.get("canon_allowed") is not False:
        raise ValueError("inventory must remain canon_allowed=false")
    core = {
        "schema": HIVE_SYNC_INVENTORY_SCHEMA,
        "version": HIVE_SYNC_VERSION,
        "node_id": node,
        "content_root_sha256": content_root,
        **content_core,
        "authentication": IDENTITY_AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    inventory_sha = _sha256(core)
    if row.get("inventory_sha256") != inventory_sha:
        raise ValueError("inventory_sha256 mismatch")
    claims = row.get("claims")
    if not isinstance(claims, Mapping) or claims.get("exchange_memory_only") is not True:
        raise ValueError("inventory must remain exchange-memory-only")
    for key in (
        "full_hive_state_replication",
        "node_identity_authenticated",
        "deletion_authority",
        "overwrite_authority",
        "canon_promoted",
    ):
        if claims.get(key) is not False:
            raise ValueError(f"inventory claim must remain false: {key}")
    return {**core, "inventory_sha256": inventory_sha, "claims": dict(claims)}


def divergent_hive_buckets(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> tuple[str, ...]:
    a = validate_hive_inventory(left)
    b = validate_hive_inventory(right)
    prefixes = sorted(set(a["buckets"]) | set(b["buckets"]))
    return tuple(
        prefix
        for prefix in prefixes
        if a["buckets"].get(prefix) != b["buckets"].get(prefix)
    )


def build_hive_manifest(
    runtime: HiveAuthorityRuntime,
    *,
    node_id: str,
    prefixes: Sequence[str],
) -> dict[str, Any]:
    inventory = build_hive_inventory(runtime, node_id=node_id)
    normalized_prefixes = tuple(sorted({_prefix(prefix) for prefix in prefixes}))
    desc_by_bucket: dict[str, list[dict[str, Any]]] = {}
    for descriptor in _descriptors(runtime):
        desc_by_bucket.setdefault(_bucket(descriptor["envelope_id"]), []).append(descriptor)
    buckets: dict[str, dict[str, Any]] = {}
    for prefix in normalized_prefixes:
        descriptors = sorted(
            desc_by_bucket.get(prefix, ()),
            key=lambda row: row["envelope_id"],
        )
        ids = [row["envelope_id"] for row in descriptors]
        buckets[prefix] = {
            "descriptors": descriptors,
            "envelope_count": len(ids),
            "root_sha256": _bucket_root(prefix, ids),
        }
    core = {
        "schema": HIVE_SYNC_MANIFEST_SCHEMA,
        "version": HIVE_SYNC_VERSION,
        "node_id": inventory["node_id"],
        "inventory_sha256": inventory["inventory_sha256"],
        "prefixes": list(normalized_prefixes),
        "buckets": buckets,
        "authentication": IDENTITY_AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    return {
        **core,
        "manifest_sha256": _sha256(core),
        "claims": {
            "metadata_only": True,
            "proof_payload_transferred": False,
            "node_identity_authenticated": False,
            "deletion_authority": False,
            "overwrite_authority": False,
        },
    }


def validate_hive_manifest(
    packet: Mapping[str, Any],
    inventory: Mapping[str, Any],
) -> dict[str, Any]:
    inv = validate_hive_inventory(inventory)
    if not isinstance(packet, Mapping):
        raise ValueError("Hive manifest must be a mapping")
    row = dict(packet)
    if row.get("schema") != HIVE_SYNC_MANIFEST_SCHEMA or row.get("version") != HIVE_SYNC_VERSION:
        raise ValueError("unsupported Hive anti-entropy manifest")
    if _text(row.get("node_id"), "node_id") != inv["node_id"]:
        raise ValueError("manifest node_id mismatch")
    if row.get("inventory_sha256") != inv["inventory_sha256"]:
        raise ValueError("manifest inventory binding mismatch")
    raw_prefixes = row.get("prefixes")
    if not isinstance(raw_prefixes, Sequence) or isinstance(raw_prefixes, (str, bytes)):
        raise ValueError("manifest prefixes must be a sequence")
    prefixes = tuple(sorted({_prefix(prefix) for prefix in raw_prefixes}))
    if list(prefixes) != list(raw_prefixes):
        raise ValueError("manifest prefixes must be unique and sorted")
    raw_buckets = row.get("buckets")
    if not isinstance(raw_buckets, Mapping) or set(raw_buckets) != set(prefixes):
        raise ValueError("manifest bucket keys must equal prefixes")
    buckets: dict[str, dict[str, Any]] = {}
    for prefix in prefixes:
        raw = raw_buckets[prefix]
        if not isinstance(raw, Mapping):
            raise ValueError("manifest bucket must be a mapping")
        descs = raw.get("descriptors")
        if not isinstance(descs, Sequence) or isinstance(descs, (str, bytes)):
            raise ValueError("manifest descriptors must be a sequence")
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for descriptor in descs:
            if not isinstance(descriptor, Mapping):
                raise ValueError("manifest descriptor must be a mapping")
            desc = dict(descriptor)
            envelope_id = _envelope_id(desc.get("envelope_id"))
            if _bucket(envelope_id) != prefix or envelope_id in seen:
                raise ValueError("invalid or duplicate manifest envelope")
            proof_kind = _text(desc.get("proof_kind"), "proof_kind")
            if proof_kind not in {"ENVELOPE", "LINEAGE_BUNDLE", "LEGACY_UNEXPORTABLE"}:
                raise ValueError("unsupported proof_kind")
            proof_sha = _commitment(desc.get("proof_sha256"), "proof_sha256")
            exportable = desc.get("replication_exportable")
            if not isinstance(exportable, bool):
                raise ValueError("replication_exportable must be boolean")
            if exportable != (proof_kind != "LEGACY_UNEXPORTABLE"):
                raise ValueError("replication_exportable/proof_kind mismatch")
            normalized.append({
                "envelope_id": envelope_id,
                "proof_kind": proof_kind,
                "proof_sha256": proof_sha,
                "replication_exportable": exportable,
            })
            seen.add(envelope_id)
        normalized.sort(key=lambda item: item["envelope_id"])
        ids = [item["envelope_id"] for item in normalized]
        summary = {
            "descriptors": normalized,
            "envelope_count": len(ids),
            "root_sha256": _bucket_root(prefix, ids),
        }
        if raw.get("envelope_count") != summary["envelope_count"]:
            raise ValueError("manifest envelope_count mismatch")
        if raw.get("root_sha256") != summary["root_sha256"]:
            raise ValueError("manifest bucket root mismatch")
        inv_summary = inv["buckets"].get(prefix)
        if inv_summary is None:
            if ids:
                raise ValueError("manifest contains envelope absent from inventory")
        elif inv_summary != {
            "envelope_count": summary["envelope_count"],
            "root_sha256": summary["root_sha256"],
        }:
            raise ValueError("manifest bucket does not match inventory")
        buckets[prefix] = summary

    if row.get("authentication") != IDENTITY_AUTHENTICATION:
        raise ValueError("manifest authentication boundary mismatch")
    if row.get("epistemic") != EPISTEMIC or row.get("authority") != AUTHORITY:
        raise ValueError("manifest epistemic/authority mismatch")
    if row.get("canon_allowed") is not False:
        raise ValueError("manifest must remain canon_allowed=false")
    core = {
        "schema": HIVE_SYNC_MANIFEST_SCHEMA,
        "version": HIVE_SYNC_VERSION,
        "node_id": inv["node_id"],
        "inventory_sha256": inv["inventory_sha256"],
        "prefixes": list(prefixes),
        "buckets": buckets,
        "authentication": IDENTITY_AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    manifest_sha = _sha256(core)
    if row.get("manifest_sha256") != manifest_sha:
        raise ValueError("manifest_sha256 mismatch")
    claims = row.get("claims")
    if not isinstance(claims, Mapping):
        raise ValueError("manifest claims must be a mapping")
    if claims.get("metadata_only") is not True or claims.get("proof_payload_transferred") is not False:
        raise ValueError("manifest must remain metadata-only")
    for key in ("node_identity_authenticated", "deletion_authority", "overwrite_authority"):
        if claims.get(key) is not False:
            raise ValueError(f"manifest claim must remain false: {key}")
    return {**core, "manifest_sha256": manifest_sha, "claims": dict(claims)}


def plan_hive_delta(
    sender_inventory: Mapping[str, Any],
    receiver_inventory: Mapping[str, Any],
    sender_manifest: Mapping[str, Any],
    receiver_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    sender_inv = validate_hive_inventory(sender_inventory)
    receiver_inv = validate_hive_inventory(receiver_inventory)
    prefixes = divergent_hive_buckets(sender_inv, receiver_inv)
    sender_man = validate_hive_manifest(sender_manifest, sender_inv)
    receiver_man = validate_hive_manifest(receiver_manifest, receiver_inv)
    if tuple(sender_man["prefixes"]) != prefixes or tuple(receiver_man["prefixes"]) != prefixes:
        raise ValueError("manifests must cover exactly all divergent buckets")

    sender_desc: dict[str, dict[str, Any]] = {}
    receiver_desc: dict[str, dict[str, Any]] = {}
    for prefix in prefixes:
        for descriptor in sender_man["buckets"][prefix]["descriptors"]:
            sender_desc[descriptor["envelope_id"]] = descriptor
        for descriptor in receiver_man["buckets"][prefix]["descriptors"]:
            receiver_desc[descriptor["envelope_id"]] = descriptor

    send_ids = sorted(set(sender_desc) - set(receiver_desc))
    receiver_only = sorted(set(receiver_desc) - set(sender_desc))
    blocked = sorted(
        envelope_id
        for envelope_id in send_ids
        if not sender_desc[envelope_id]["replication_exportable"]
    )
    exportable = sorted(set(send_ids) - set(blocked))
    core = {
        "schema": HIVE_SYNC_PLAN_SCHEMA,
        "version": HIVE_SYNC_VERSION,
        "sender_node_id": sender_inv["node_id"],
        "receiver_node_id": receiver_inv["node_id"],
        "sender_inventory_sha256": sender_inv["inventory_sha256"],
        "receiver_inventory_sha256": receiver_inv["inventory_sha256"],
        "divergent_prefixes": list(prefixes),
        "send_envelope_ids": exportable,
        "blocked_unexportable_envelope_ids": blocked,
        "receiver_only_envelope_ids": receiver_only,
        "authentication": IDENTITY_AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    return {
        **core,
        "plan_sha256": _sha256(core),
        "claims": {
            "exchange_memory_only": True,
            "append_only_delta": True,
            "delete_receiver_only_items": False,
            "overwrite_receiver_items": False,
            "node_identity_authenticated": False,
            "canon_promoted": False,
        },
    }


def validate_hive_plan(packet: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, Mapping):
        raise ValueError("Hive delta plan must be a mapping")
    row = dict(packet)
    if row.get("schema") != HIVE_SYNC_PLAN_SCHEMA or row.get("version") != HIVE_SYNC_VERSION:
        raise ValueError("unsupported Hive delta plan")
    sender = _text(row.get("sender_node_id"), "sender_node_id")
    receiver = _text(row.get("receiver_node_id"), "receiver_node_id")
    sender_inv = _commitment(row.get("sender_inventory_sha256"), "sender_inventory_sha256")
    receiver_inv = _commitment(row.get("receiver_inventory_sha256"), "receiver_inventory_sha256")
    raw_prefixes = row.get("divergent_prefixes")
    if not isinstance(raw_prefixes, Sequence) or isinstance(raw_prefixes, (str, bytes)):
        raise ValueError("divergent_prefixes must be a sequence")
    prefixes = tuple(sorted({_prefix(prefix) for prefix in raw_prefixes}))
    if list(prefixes) != list(raw_prefixes):
        raise ValueError("divergent_prefixes must be unique and sorted")

    def ids(field: str) -> list[str]:
        raw = row.get(field)
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            raise ValueError(f"{field} must be a sequence")
        out = sorted({_envelope_id(item) for item in raw})
        if out != list(raw):
            raise ValueError(f"{field} must be unique and sorted")
        return out

    send_ids = ids("send_envelope_ids")
    blocked = ids("blocked_unexportable_envelope_ids")
    receiver_only = ids("receiver_only_envelope_ids")
    if set(send_ids) & set(blocked):
        raise ValueError("exportable and blocked envelope ids must be disjoint")
    if row.get("authentication") != IDENTITY_AUTHENTICATION:
        raise ValueError("plan authentication boundary mismatch")
    if row.get("epistemic") != EPISTEMIC or row.get("authority") != AUTHORITY:
        raise ValueError("plan epistemic/authority mismatch")
    if row.get("canon_allowed") is not False:
        raise ValueError("plan must remain canon_allowed=false")
    core = {
        "schema": HIVE_SYNC_PLAN_SCHEMA,
        "version": HIVE_SYNC_VERSION,
        "sender_node_id": sender,
        "receiver_node_id": receiver,
        "sender_inventory_sha256": sender_inv,
        "receiver_inventory_sha256": receiver_inv,
        "divergent_prefixes": list(prefixes),
        "send_envelope_ids": send_ids,
        "blocked_unexportable_envelope_ids": blocked,
        "receiver_only_envelope_ids": receiver_only,
        "authentication": IDENTITY_AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    plan_sha = _sha256(core)
    if row.get("plan_sha256") != plan_sha:
        raise ValueError("plan_sha256 mismatch")
    claims = row.get("claims")
    if not isinstance(claims, Mapping) or claims.get("append_only_delta") is not True:
        raise ValueError("plan must remain append-only")
    if claims.get("exchange_memory_only") is not True:
        raise ValueError("plan must remain exchange-memory-only")
    for key in ("delete_receiver_only_items", "overwrite_receiver_items", "node_identity_authenticated", "canon_promoted"):
        if claims.get(key) is not False:
            raise ValueError(f"plan claim must remain false: {key}")
    return {**core, "plan_sha256": plan_sha, "claims": dict(claims)}


def export_hive_delta(
    runtime: HiveAuthorityRuntime,
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    validated = validate_hive_plan(plan)
    if validated["blocked_unexportable_envelope_ids"]:
        raise RuntimeError(
            "delta contains legacy/unexportable Hive exchange records; "
            "re-ingest with retained exchange proof before replication"
        )
    records = {
        dict(record.payload)["envelope_id"]: record
        for record in _exchange_records(runtime)
    }
    transfers = []
    for envelope_id in validated["send_envelope_ids"]:
        try:
            record = records[envelope_id]
        except KeyError as exc:
            raise KeyError("delta plan references envelope absent from sender Hive") from exc
        payload = dict(record.payload)
        if isinstance(payload.get("lineage_bundle"), Mapping):
            proof_kind = "LINEAGE_BUNDLE"
            proof = dict(payload["lineage_bundle"])
            proof_sha = validate_exchange_bundle(proof)["bundle_sha256"]
        elif isinstance(payload.get("exchange_packet"), Mapping):
            proof_kind = "ENVELOPE"
            proof = dict(payload["exchange_packet"])
            proof_sha = _sha256(validate_exchange_envelope(proof))
        else:
            raise RuntimeError("sender record lost replication proof after planning")
        transfers.append({
            "envelope_id": envelope_id,
            "proof_kind": proof_kind,
            "proof_sha256": proof_sha,
            "proof": proof,
        })
    transfers.sort(key=lambda item: item["envelope_id"])
    core = {
        "schema": HIVE_SYNC_DELTA_SCHEMA,
        "version": HIVE_SYNC_VERSION,
        "plan_sha256": validated["plan_sha256"],
        "sender_node_id": validated["sender_node_id"],
        "receiver_node_id": validated["receiver_node_id"],
        "sender_inventory_sha256": validated["sender_inventory_sha256"],
        "receiver_inventory_sha256": validated["receiver_inventory_sha256"],
        "transfers": transfers,
        "authentication": IDENTITY_AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    return {
        **core,
        "delta_sha256": _sha256(core),
        "claims": {
            "exchange_memory_only": True,
            "append_only_delta": True,
            "local_priority_not_replicated": True,
            "deletion_authority": False,
            "overwrite_authority": False,
            "node_identity_authenticated": False,
            "canon_promoted": False,
        },
    }


def validate_hive_delta(packet: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, Mapping):
        raise ValueError("Hive delta must be a mapping")
    row = dict(packet)
    if row.get("schema") != HIVE_SYNC_DELTA_SCHEMA or row.get("version") != HIVE_SYNC_VERSION:
        raise ValueError("unsupported Hive anti-entropy delta")
    plan_sha = _commitment(row.get("plan_sha256"), "plan_sha256")
    sender = _text(row.get("sender_node_id"), "sender_node_id")
    receiver = _text(row.get("receiver_node_id"), "receiver_node_id")
    sender_inv = _commitment(row.get("sender_inventory_sha256"), "sender_inventory_sha256")
    receiver_inv = _commitment(row.get("receiver_inventory_sha256"), "receiver_inventory_sha256")
    raw = row.get("transfers")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("transfers must be a sequence")
    transfers = []
    seen: set[str] = set()
    for transfer in raw:
        if not isinstance(transfer, Mapping):
            raise ValueError("transfer must be a mapping")
        item = dict(transfer)
        envelope_id = _envelope_id(item.get("envelope_id"))
        if envelope_id in seen:
            raise ValueError("duplicate transfer envelope_id")
        kind = _text(item.get("proof_kind"), "proof_kind")
        proof = item.get("proof")
        if not isinstance(proof, Mapping):
            raise ValueError("transfer proof must be a mapping")
        if kind == "LINEAGE_BUNDLE":
            validated = validate_exchange_bundle(proof)
            if validated["target_envelope_id"] != envelope_id:
                raise ValueError("bundle transfer target mismatch")
            proof_sha = validated["bundle_sha256"]
            target = validated["target_envelope"]
        elif kind == "ENVELOPE":
            target = validate_exchange_envelope(proof)
            if target["envelope_id"] != envelope_id:
                raise ValueError("envelope transfer target mismatch")
            proof_sha = _sha256(target)
        else:
            raise ValueError("unsupported transfer proof_kind")
        if item.get("proof_sha256") != proof_sha:
            raise ValueError("transfer proof_sha256 mismatch")
        if target["target_layer"] != "RELATIONAL":
            raise ValueError("Hive replication target must remain RELATIONAL")
        transfers.append({
            "envelope_id": envelope_id,
            "proof_kind": kind,
            "proof_sha256": proof_sha,
            "proof": dict(proof),
            "_target": target,
        })
        seen.add(envelope_id)
    if [item["envelope_id"] for item in transfers] != sorted(seen):
        raise ValueError("transfers must be sorted by envelope_id")
    if row.get("authentication") != IDENTITY_AUTHENTICATION:
        raise ValueError("delta authentication boundary mismatch")
    if row.get("epistemic") != EPISTEMIC or row.get("authority") != AUTHORITY:
        raise ValueError("delta epistemic/authority mismatch")
    if row.get("canon_allowed") is not False:
        raise ValueError("delta must remain canon_allowed=false")
    core_transfers = [
        {
            "envelope_id": item["envelope_id"],
            "proof_kind": item["proof_kind"],
            "proof_sha256": item["proof_sha256"],
            "proof": item["proof"],
        }
        for item in transfers
    ]
    core = {
        "schema": HIVE_SYNC_DELTA_SCHEMA,
        "version": HIVE_SYNC_VERSION,
        "plan_sha256": plan_sha,
        "sender_node_id": sender,
        "receiver_node_id": receiver,
        "sender_inventory_sha256": sender_inv,
        "receiver_inventory_sha256": receiver_inv,
        "transfers": core_transfers,
        "authentication": IDENTITY_AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    delta_sha = _sha256(core)
    if row.get("delta_sha256") != delta_sha:
        raise ValueError("delta_sha256 mismatch")
    claims = row.get("claims")
    if not isinstance(claims, Mapping):
        raise ValueError("delta claims must be a mapping")
    if claims.get("exchange_memory_only") is not True or claims.get("append_only_delta") is not True:
        raise ValueError("delta must remain append-only exchange-memory-only")
    if claims.get("local_priority_not_replicated") is not True:
        raise ValueError("local priority must remain receiver-local")
    for key in ("deletion_authority", "overwrite_authority", "node_identity_authenticated", "canon_promoted"):
        if claims.get(key) is not False:
            raise ValueError(f"delta claim must remain false: {key}")
    return {**core, "delta_sha256": delta_sha, "claims": dict(claims), "_transfers": transfers}


def _current_descriptor_map(runtime: HiveAuthorityRuntime) -> dict[str, dict[str, Any]]:
    return {descriptor["envelope_id"]: descriptor for descriptor in _descriptors(runtime)}


def _receiver_lineage_state(runtime: HiveAuthorityRuntime) -> dict[str, tuple[str, int]]:
    out = {}
    for record in _exchange_records(runtime):
        payload = dict(record.payload)
        out[_envelope_id(payload["envelope_id"])] = (
            _text(payload.get("generation_id"), "generation_id"),
            int(payload.get("sequence")),
        )
    return out


def _preflight_transfers(
    runtime: HiveAuthorityRuntime,
    transfers: Sequence[dict[str, Any]],
) -> None:
    existing = _receiver_lineage_state(runtime)
    staged = {
        item["envelope_id"]: (
            item["_target"]["generation_id"],
            int(item["_target"]["sequence"]),
        )
        for item in transfers
    }
    available = {**existing, **staged}
    for item in transfers:
        if item["proof_kind"] != "ENVELOPE":
            continue
        target = item["_target"]
        for parent_id in target["parent_envelope_ids"]:
            parent = available.get(parent_id)
            if parent is None:
                raise RuntimeError("direct replicated envelope is missing its RELATIONAL parent")
            generation_id, sequence = parent
            if generation_id != target["generation_id"]:
                raise RuntimeError("replicated parent generation mismatch")
            if sequence >= int(target["sequence"]):
                raise RuntimeError("replicated child sequence must exceed parent sequence")


def _acks_for_transfers(
    transfers: Sequence[dict[str, Any]],
    *,
    receiver_node_id: str,
) -> list[dict[str, Any]]:
    return [
        build_exchange_ack(
            item["_target"],
            consumer_id=f"GREMLIN-HIVE:{receiver_node_id}",
            outcome="ACCEPTED",
            reason_code="HIVE_ANTI_ENTROPY_PRESENT",
        )
        for item in transfers
    ]


def apply_hive_delta(
    runtime: HiveAuthorityRuntime,
    delta: Mapping[str, Any],
    *,
    receiver_node_id: str,
    priority: float = 0.82,
) -> dict[str, Any]:
    validated = validate_hive_delta(delta)
    receiver = _text(receiver_node_id, "receiver_node_id")
    if validated["receiver_node_id"] != receiver:
        raise ValueError("delta receiver_node_id mismatch")

    current = build_hive_inventory(runtime, node_id=receiver)
    existing_ids = set(_current_descriptor_map(runtime))
    transfer_ids = {item["envelope_id"] for item in validated["_transfers"]}
    if transfer_ids <= existing_ids:
        return {
            "status": "ALREADY_APPLIED",
            "delta_sha256": validated["delta_sha256"],
            "created": 0,
            "acks": _acks_for_transfers(validated["_transfers"], receiver_node_id=receiver),
            "inventory_sha256": current["inventory_sha256"],
            "content_root_sha256": current["content_root_sha256"],
            "append_only": True,
            "canon_allowed": False,
        }
    if current["inventory_sha256"] != validated["receiver_inventory_sha256"]:
        raise RuntimeError("receiver Hive exchange inventory changed since delta planning")

    _preflight_transfers(runtime, validated["_transfers"])
    ordered = sorted(
        validated["_transfers"],
        key=lambda item: (int(item["_target"]["sequence"]), item["envelope_id"]),
    )
    created = 0
    for item in ordered:
        if item["proof_kind"] == "LINEAGE_BUNDLE":
            result = ingest_exchange_bundle(
                runtime,
                item["proof"],
                priority=priority,
                consumer_id=f"GREMLIN-HIVE:{receiver}",
            )
        else:
            result = ingest_exchange_envelope(
                runtime,
                item["proof"],
                priority=priority,
                consumer_id=f"GREMLIN-HIVE:{receiver}",
            )
        created += int(bool(result["created"]))

    acks = _acks_for_transfers(validated["_transfers"], receiver_node_id=receiver)
    after = build_hive_inventory(runtime, node_id=receiver)
    return {
        "status": "APPLIED",
        "delta_sha256": validated["delta_sha256"],
        "created": created,
        "acks": sorted(acks, key=lambda row: row["ack_id"]),
        "before_inventory_sha256": current["inventory_sha256"],
        "after_inventory_sha256": after["inventory_sha256"],
        "content_root_sha256": after["content_root_sha256"],
        "append_only": True,
        "canon_allowed": False,
    }


__all__ = [
    "BUCKET_HEX_WIDTH",
    "HIVE_SYNC_DELTA_SCHEMA",
    "HIVE_SYNC_INVENTORY_SCHEMA",
    "HIVE_SYNC_MANIFEST_SCHEMA",
    "HIVE_SYNC_PLAN_SCHEMA",
    "HIVE_SYNC_VERSION",
    "apply_hive_delta",
    "build_hive_inventory",
    "build_hive_manifest",
    "divergent_hive_buckets",
    "export_hive_delta",
    "plan_hive_delta",
    "validate_hive_delta",
    "validate_hive_inventory",
    "validate_hive_manifest",
    "validate_hive_plan",
]
