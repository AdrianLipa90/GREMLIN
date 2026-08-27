from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from tools.gremlin_kaku_radical_scalar_plane_v01 import (
    validate_kaku_scalar_packet,
    validate_radical_scalar_admission,
)

KAKU_RECORD_SCHEMA = "GREMLIN_KAKU_PERSISTENCE_RECORD_V0_1"
RADICAL_RECORD_SCHEMA = "GREMLIN_RADICAL_PERSISTENCE_RECORD_V0_1"
BUNDLE_SCHEMA = "GREMLIN_KAKU_RADICAL_PERSISTENCE_BUNDLE_V0_1"
BUNDLE_RECEIPT_SCHEMA = "GREMLIN_KAKU_RADICAL_JSONL_RECEIPT_V0_1"

KAKU_DOMAIN = b"GREMLIN-KAKU-PERSISTENCE/v0.1\x00"
RADICAL_DOMAIN = b"GREMLIN-RADICAL-PERSISTENCE/v0.1\x00"
BUNDLE_DOMAIN = b"GREMLIN-KAKU-RADICAL-BUNDLE/v0.1\x00"


class GremlinKakuRadicalWriterError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _nonempty(value: Any, name: str) -> str:
    text = str(value)
    if not text:
        raise GremlinKakuRadicalWriterError(f"{name} must be non-empty")
    return text


def _digest(value: Any, name: str) -> str:
    text = _nonempty(value, name)
    if len(text) != 64:
        raise GremlinKakuRadicalWriterError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise GremlinKakuRadicalWriterError(f"{name} must be hex") from exc
    return text


def _commit(domain: bytes, value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def build_kaku_record(packet: Mapping[str, Any]) -> dict[str, Any]:
    validate_kaku_scalar_packet(packet)
    core = {
        "schema": KAKU_RECORD_SCHEMA,
        "record_type": "KAKU",
        "kaku_id": str(packet["kaku_id"]),
        "kaku_scalar_commitment": str(packet["kaku_scalar_commitment"]),
        "operator_kind": str(packet["operator_kind"]),
        "operator_classification": str(packet["operator_classification"]),
        "payload_schema": str(packet["schema"]),
        "payload": dict(packet),
        "storage_role": "CONTENT_ADDRESSED_PERSISTENCE_OBJECT",
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "KAKU_RECORD_READY",
    }
    return {**core, "record_id": _commit(KAKU_DOMAIN, core)}


def validate_kaku_record(record: Mapping[str, Any]) -> bool:
    if record.get("schema") != KAKU_RECORD_SCHEMA or record.get("record_type") != "KAKU":
        raise GremlinKakuRadicalWriterError("unsupported KAKU record schema/type")
    payload = record.get("payload")
    if not isinstance(payload, Mapping):
        raise GremlinKakuRadicalWriterError("KAKU payload required")
    validate_kaku_scalar_packet(payload)
    if record.get("kaku_id") != payload.get("kaku_id"):
        raise GremlinKakuRadicalWriterError("KAKU identity mismatch")
    if record.get("kaku_scalar_commitment") != payload.get("kaku_scalar_commitment"):
        raise GremlinKakuRadicalWriterError("KAKU commitment mismatch")
    if record.get("operator_kind") != payload.get("operator_kind"):
        raise GremlinKakuRadicalWriterError("KAKU operator mismatch")
    if record.get("operator_classification") != payload.get("operator_classification"):
        raise GremlinKakuRadicalWriterError("KAKU operator classification mismatch")
    if record.get("payload_schema") != payload.get("schema"):
        raise GremlinKakuRadicalWriterError("KAKU payload schema mismatch")
    if record.get("storage_role") != "CONTENT_ADDRESSED_PERSISTENCE_OBJECT":
        raise GremlinKakuRadicalWriterError("KAKU storage role mismatch")
    if record.get("execution_admitted") is not False or record.get("canon_allowed") is not False:
        raise GremlinKakuRadicalWriterError("KAKU persistence authority boundary violated")
    if record.get("status") != "KAKU_RECORD_READY":
        raise GremlinKakuRadicalWriterError("invalid KAKU persistence status")
    supplied = _digest(record.get("record_id"), "record_id")
    core = dict(record)
    core.pop("record_id", None)
    if supplied != _commit(KAKU_DOMAIN, core):
        raise GremlinKakuRadicalWriterError("KAKU persistence record commitment mismatch")
    return True


def build_radical_record(
    radical_admission: Mapping[str, Any],
    ordered_kaku_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    validate_radical_scalar_admission(radical_admission)
    if not ordered_kaku_records:
        raise GremlinKakuRadicalWriterError("Radical persistence requires KAKU records")

    records = []
    seen_ids = set()
    for record in ordered_kaku_records:
        validate_kaku_record(record)
        rid = str(record["record_id"])
        if rid in seen_ids:
            raise GremlinKakuRadicalWriterError("duplicate KAKU persistence record")
        seen_ids.add(rid)
        records.append(record)

    expected_lineage = [
        (str(item["kaku_id"]), str(item["kaku_scalar_commitment"]), str(item["operator_kind"]), str(item["operator_classification"]))
        for item in radical_admission["ordered_kaku"]
    ]
    supplied_lineage = [
        (str(item["kaku_id"]), str(item["kaku_scalar_commitment"]), str(item["operator_kind"]), str(item["operator_classification"]))
        for item in records
    ]
    if supplied_lineage != expected_lineage:
        raise GremlinKakuRadicalWriterError("ordered KAKU persistence lineage differs from Radical admission")

    core = {
        "schema": RADICAL_RECORD_SCHEMA,
        "record_type": "RADICAL",
        "radical_id": str(radical_admission["radical_id"]),
        "candidate_id": str(radical_admission["candidate_id"]),
        "radical_scalar_commitment": str(radical_admission["radical_scalar_commitment"]),
        "ordered_kaku_record_ids": [str(item["record_id"]) for item in records],
        "ordered_kaku_ids": [str(item["kaku_id"]) for item in records],
        "relation_ids": list(radical_admission["relation_ids"]),
        "pre_vector_status": str(radical_admission["status"]),
        "vector_synthesis_allowed": bool(radical_admission["vector_synthesis_allowed"]),
        "payload_schema": str(radical_admission["schema"]),
        "payload": dict(radical_admission),
        "storage_role": "CONTENT_ADDRESSED_PERSISTENCE_OBJECT",
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "RADICAL_RECORD_READY",
    }
    return {**core, "record_id": _commit(RADICAL_DOMAIN, core)}


def validate_radical_record(
    record: Mapping[str, Any],
    ordered_kaku_records: Sequence[Mapping[str, Any]] | None = None,
) -> bool:
    if record.get("schema") != RADICAL_RECORD_SCHEMA or record.get("record_type") != "RADICAL":
        raise GremlinKakuRadicalWriterError("unsupported Radical record schema/type")
    payload = record.get("payload")
    if not isinstance(payload, Mapping):
        raise GremlinKakuRadicalWriterError("Radical payload required")
    validate_radical_scalar_admission(payload)
    for key in ("radical_id", "candidate_id", "radical_scalar_commitment"):
        if record.get(key) != payload.get(key):
            raise GremlinKakuRadicalWriterError(f"Radical {key} mismatch")
    if record.get("relation_ids") != payload.get("relation_ids"):
        raise GremlinKakuRadicalWriterError("Radical relation lineage mismatch")
    if record.get("pre_vector_status") != payload.get("status"):
        raise GremlinKakuRadicalWriterError("Radical admission status mismatch")
    if record.get("vector_synthesis_allowed") is not payload.get("vector_synthesis_allowed"):
        raise GremlinKakuRadicalWriterError("Radical vector synthesis flag mismatch")
    if record.get("payload_schema") != payload.get("schema"):
        raise GremlinKakuRadicalWriterError("Radical payload schema mismatch")
    record_ids = record.get("ordered_kaku_record_ids")
    kaku_ids = record.get("ordered_kaku_ids")
    if not isinstance(record_ids, list) or not isinstance(kaku_ids, list) or not record_ids or len(record_ids) != len(kaku_ids):
        raise GremlinKakuRadicalWriterError("Radical KAKU persistence lineage required")
    for rid in record_ids:
        _digest(rid, "ordered_kaku_record_id")
    if len(set(record_ids)) != len(record_ids):
        raise GremlinKakuRadicalWriterError("duplicate KAKU record id in Radical lineage")
    if record.get("storage_role") != "CONTENT_ADDRESSED_PERSISTENCE_OBJECT":
        raise GremlinKakuRadicalWriterError("Radical storage role mismatch")
    if record.get("execution_admitted") is not False or record.get("canon_allowed") is not False:
        raise GremlinKakuRadicalWriterError("Radical persistence authority boundary violated")
    if record.get("status") != "RADICAL_RECORD_READY":
        raise GremlinKakuRadicalWriterError("invalid Radical persistence status")

    if ordered_kaku_records is not None:
        if len(ordered_kaku_records) != len(record_ids):
            raise GremlinKakuRadicalWriterError("Radical KAKU record count mismatch")
        for item in ordered_kaku_records:
            validate_kaku_record(item)
        if [str(item["record_id"]) for item in ordered_kaku_records] != list(record_ids):
            raise GremlinKakuRadicalWriterError("Radical ordered KAKU record ids mismatch")
        expected = [
            (str(x["kaku_id"]), str(x["kaku_scalar_commitment"]), str(x["operator_kind"]), str(x["operator_classification"]))
            for x in payload["ordered_kaku"]
        ]
        supplied = [
            (str(x["kaku_id"]), str(x["kaku_scalar_commitment"]), str(x["operator_kind"]), str(x["operator_classification"]))
            for x in ordered_kaku_records
        ]
        if supplied != expected:
            raise GremlinKakuRadicalWriterError("Radical KAKU content lineage mismatch")

    supplied_record_id = _digest(record.get("record_id"), "record_id")
    core = dict(record)
    core.pop("record_id", None)
    if supplied_record_id != _commit(RADICAL_DOMAIN, core):
        raise GremlinKakuRadicalWriterError("Radical persistence record commitment mismatch")
    return True


def build_persistence_bundle(
    ordered_kaku_records: Sequence[Mapping[str, Any]],
    radical_record: Mapping[str, Any],
) -> dict[str, Any]:
    records = [dict(item) for item in ordered_kaku_records]
    for item in records:
        validate_kaku_record(item)
    validate_radical_record(radical_record, records)
    all_records = records + [dict(radical_record)]
    record_ids = [str(item["record_id"]) for item in all_records]
    core = {
        "schema": BUNDLE_SCHEMA,
        "records": all_records,
        "record_ids": record_ids,
        "kaku_count": len(records),
        "radical_count": 1,
        "record_order": "ORDERED_KAKU_THEN_RADICAL",
        "serialization": "CANONICAL_JSONL_UTF8_LF",
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "PERSISTENCE_BUNDLE_READY",
    }
    return {**core, "bundle_commitment": _commit(BUNDLE_DOMAIN, core)}


def validate_persistence_bundle(bundle: Mapping[str, Any]) -> bool:
    if bundle.get("schema") != BUNDLE_SCHEMA:
        raise GremlinKakuRadicalWriterError("unsupported persistence bundle schema")
    records = bundle.get("records")
    if not isinstance(records, list) or len(records) < 2:
        raise GremlinKakuRadicalWriterError("persistence bundle records required")
    kaku_records = records[:-1]
    radical_record = records[-1]
    for item in kaku_records:
        validate_kaku_record(item)
    validate_radical_record(radical_record, kaku_records)
    expected_ids = [str(item["record_id"]) for item in records]
    if bundle.get("record_ids") != expected_ids:
        raise GremlinKakuRadicalWriterError("persistence bundle record order mismatch")
    if bundle.get("kaku_count") != len(kaku_records) or bundle.get("radical_count") != 1:
        raise GremlinKakuRadicalWriterError("persistence bundle count mismatch")
    if bundle.get("record_order") != "ORDERED_KAKU_THEN_RADICAL":
        raise GremlinKakuRadicalWriterError("persistence bundle order contract mismatch")
    if bundle.get("serialization") != "CANONICAL_JSONL_UTF8_LF":
        raise GremlinKakuRadicalWriterError("persistence serialization contract mismatch")
    if bundle.get("execution_admitted") is not False or bundle.get("canon_allowed") is not False:
        raise GremlinKakuRadicalWriterError("persistence bundle authority boundary violated")
    if bundle.get("status") != "PERSISTENCE_BUNDLE_READY":
        raise GremlinKakuRadicalWriterError("invalid persistence bundle status")
    supplied = _digest(bundle.get("bundle_commitment"), "bundle_commitment")
    core = dict(bundle)
    core.pop("bundle_commitment", None)
    if supplied != _commit(BUNDLE_DOMAIN, core):
        raise GremlinKakuRadicalWriterError("persistence bundle commitment mismatch")
    return True


def render_bundle_jsonl(bundle: Mapping[str, Any]) -> bytes:
    validate_persistence_bundle(bundle)
    lines = [_canonical(record) for record in bundle["records"]]
    footer = {
        "schema": BUNDLE_RECEIPT_SCHEMA,
        "bundle_commitment": bundle["bundle_commitment"],
        "record_ids": list(bundle["record_ids"]),
        "record_order": bundle["record_order"],
        "serialization": bundle["serialization"],
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "JSONL_BUNDLE_RECEIPT",
    }
    lines.append(_canonical(footer))
    return b"\n".join(lines) + b"\n"


def write_bundle_jsonl(path: str | os.PathLike[str], bundle: Mapping[str, Any], *, create_parents: bool = False) -> dict[str, Any]:
    data = render_bundle_jsonl(bundle)
    target = Path(path)
    if create_parents:
        target.parent.mkdir(parents=True, exist_ok=True)
    if not target.parent.exists():
        raise GremlinKakuRadicalWriterError("target parent directory does not exist")
    temp = target.with_name(f".{target.name}.tmp.{os.getpid()}")
    if temp.exists():
        raise GremlinKakuRadicalWriterError("temporary writer path already exists")
    try:
        with temp.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()
    return {
        "schema": BUNDLE_RECEIPT_SCHEMA,
        "path": str(target),
        "bundle_commitment": bundle["bundle_commitment"],
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "record_count": len(bundle["records"]),
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "JSONL_WRITE_COMPLETE",
    }


def read_bundle_jsonl(path: str | os.PathLike[str]) -> dict[str, Any]:
    target = Path(path)
    raw_lines = target.read_bytes().splitlines()
    if len(raw_lines) < 3:
        raise GremlinKakuRadicalWriterError("JSONL bundle requires KAKU, Radical and receipt records")
    decoded = [json.loads(line.decode("utf-8")) for line in raw_lines]
    records = decoded[:-1]
    footer = decoded[-1]
    if footer.get("schema") != BUNDLE_RECEIPT_SCHEMA or footer.get("status") != "JSONL_BUNDLE_RECEIPT":
        raise GremlinKakuRadicalWriterError("JSONL bundle footer receipt missing")
    kaku_records = records[:-1]
    radical_record = records[-1]
    bundle = build_persistence_bundle(kaku_records, radical_record)
    if footer.get("bundle_commitment") != bundle["bundle_commitment"]:
        raise GremlinKakuRadicalWriterError("JSONL bundle commitment mismatch")
    if footer.get("record_ids") != bundle["record_ids"]:
        raise GremlinKakuRadicalWriterError("JSONL record lineage mismatch")
    return bundle
