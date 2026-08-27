from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from tools.gremlin_kaku_radical_writer_v01 import validate_radical_record
from tools.gremlin_scalar_admitted_phasenav_v02 import (
    POST_REALIZATION_REQUIRED,
    validate_scalar_admitted_phasenav_ir_v02,
)

SCHEMA = "GREMLIN_OPERATOR_PERSISTENCE_RECORD_V0_1"
STORE_RECEIPT_SCHEMA = "GREMLIN_OPERATOR_IMMUTABLE_STORE_RECEIPT_V0_1"
DOMAIN = b"GREMLIN-OPERATOR-PERSISTENCE/v0.1\x00"


class GremlinOperatorRecordError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _commit(value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(DOMAIN + _canonical(value), digest_size=32).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    text = str(value)
    if not text:
        raise GremlinOperatorRecordError(f"{name} must be non-empty")
    return text


def _digest(value: Any, name: str) -> str:
    text = _nonempty(value, name)
    if len(text) != 64:
        raise GremlinOperatorRecordError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise GremlinOperatorRecordError(f"{name} must be hex") from exc
    return text


def build_operator_record(
    *,
    radical_record: Mapping[str, Any],
    scalar_admitted_ir: Mapping[str, Any],
) -> dict[str, Any]:
    validate_radical_record(radical_record)
    validate_scalar_admitted_phasenav_ir_v02(scalar_admitted_ir)

    radical_payload = radical_record["payload"]
    if radical_record.get("pre_vector_status") != "PRE_VECTOR_ADMITTED":
        raise GremlinOperatorRecordError("Operator candidate requires PRE_VECTOR_ADMITTED Radical")
    if radical_record.get("vector_synthesis_allowed") is not True:
        raise GremlinOperatorRecordError("Operator candidate requires open vector synthesis gate")
    if scalar_admitted_ir.get("candidate_id") != radical_record.get("candidate_id"):
        raise GremlinOperatorRecordError("Operator candidate/Radical candidate identity mismatch")
    if scalar_admitted_ir.get("radical_id") != radical_record.get("radical_id"):
        raise GremlinOperatorRecordError("Operator candidate/Radical identity mismatch")
    if scalar_admitted_ir.get("radical_scalar_commitment") != radical_record.get("radical_scalar_commitment"):
        raise GremlinOperatorRecordError("Operator candidate/Radical scalar commitment mismatch")
    if list(scalar_admitted_ir.get("relation_lineage", ())) != list(radical_record.get("relation_ids", ())):
        raise GremlinOperatorRecordError("Operator candidate relation lineage differs from persisted Radical")

    phasenav_ir = scalar_admitted_ir["phasenav_ir"]
    terms_commitment = hashlib.blake2b(
        b"GREMLIN-OPERATOR-TERMS/v0.1\x00" + _canonical(phasenav_ir["terms"]),
        digest_size=32,
    ).hexdigest()

    core = {
        "schema": SCHEMA,
        "record_type": "OPERATOR",
        "candidate_id": str(radical_record["candidate_id"]),
        "radical_id": str(radical_record["radical_id"]),
        "radical_record_id": str(radical_record["record_id"]),
        "radical_scalar_commitment": str(radical_record["radical_scalar_commitment"]),
        "ordered_kaku_record_ids": list(radical_record["ordered_kaku_record_ids"]),
        "scalar_admitted_ir_commitment": str(scalar_admitted_ir["scalar_admitted_ir_commitment"]),
        "phasenav_ir_commitment": str(phasenav_ir["ir_commitment"]),
        "operator_kind": str(phasenav_ir["operator"]),
        "geometry": dict(phasenav_ir["geometry"]),
        "relation_lineage": list(scalar_admitted_ir["relation_lineage"]),
        "term_count": len(phasenav_ir["terms"]),
        "terms_commitment": terms_commitment,
        "normalization": dict(phasenav_ir["normalization"]),
        "payload_schema": str(scalar_admitted_ir["schema"]),
        "payload": dict(scalar_admitted_ir),
        "parent_record_ids": [str(radical_record["record_id"])],
        "stage": "OPERATOR_CANDIDATE_AFTER_PRE_VECTOR_ADMISSION",
        "post_realization_scalars_required": list(POST_REALIZATION_REQUIRED),
        "post_realization_complete": False,
        "realization_receipt_bound": False,
        "storage_role": "CONTENT_ADDRESSED_PERSISTENCE_OBJECT",
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "OPERATOR_RECORD_READY",
    }
    return {**core, "operator_record_commitment": _commit(core)}


def validate_operator_record(record: Mapping[str, Any], radical_record: Mapping[str, Any] | None = None) -> bool:
    if record.get("schema") != SCHEMA or record.get("record_type") != "OPERATOR":
        raise GremlinOperatorRecordError("unsupported OPERATOR record schema/type")
    payload = record.get("payload")
    if not isinstance(payload, Mapping):
        raise GremlinOperatorRecordError("OPERATOR payload required")
    validate_scalar_admitted_phasenav_ir_v02(payload)
    phasenav_ir = payload["phasenav_ir"]

    for key in ("candidate_id", "radical_id", "radical_scalar_commitment", "scalar_admitted_ir_commitment"):
        payload_key = key
        if record.get(key) != payload.get(payload_key):
            raise GremlinOperatorRecordError(f"OPERATOR {key} mismatch")
    if record.get("phasenav_ir_commitment") != phasenav_ir.get("ir_commitment"):
        raise GremlinOperatorRecordError("OPERATOR PhaseNav IR commitment mismatch")
    if record.get("operator_kind") != phasenav_ir.get("operator"):
        raise GremlinOperatorRecordError("OPERATOR kind mismatch")
    if record.get("geometry") != phasenav_ir.get("geometry"):
        raise GremlinOperatorRecordError("OPERATOR geometry mismatch")
    if record.get("relation_lineage") != payload.get("relation_lineage"):
        raise GremlinOperatorRecordError("OPERATOR relation lineage mismatch")
    if record.get("term_count") != len(phasenav_ir.get("terms", ())):
        raise GremlinOperatorRecordError("OPERATOR term count mismatch")
    expected_terms_commitment = hashlib.blake2b(
        b"GREMLIN-OPERATOR-TERMS/v0.1\x00" + _canonical(phasenav_ir["terms"]),
        digest_size=32,
    ).hexdigest()
    if record.get("terms_commitment") != expected_terms_commitment:
        raise GremlinOperatorRecordError("OPERATOR terms commitment mismatch")
    if record.get("normalization") != phasenav_ir.get("normalization"):
        raise GremlinOperatorRecordError("OPERATOR normalization mismatch")
    if record.get("payload_schema") != payload.get("schema"):
        raise GremlinOperatorRecordError("OPERATOR payload schema mismatch")

    radical_record_id = _digest(record.get("radical_record_id"), "radical_record_id")
    parents = record.get("parent_record_ids")
    if parents != [radical_record_id]:
        raise GremlinOperatorRecordError("OPERATOR parent lineage mismatch")
    kaku_record_ids = record.get("ordered_kaku_record_ids")
    if not isinstance(kaku_record_ids, list) or not kaku_record_ids:
        raise GremlinOperatorRecordError("OPERATOR KAKU persistence lineage required")
    for item in kaku_record_ids:
        _digest(item, "ordered_kaku_record_id")
    if len(set(kaku_record_ids)) != len(kaku_record_ids):
        raise GremlinOperatorRecordError("duplicate OPERATOR KAKU persistence parent")

    if tuple(record.get("post_realization_scalars_required", ())) != POST_REALIZATION_REQUIRED:
        raise GremlinOperatorRecordError("OPERATOR post-realization scalar contract mismatch")
    if record.get("stage") != "OPERATOR_CANDIDATE_AFTER_PRE_VECTOR_ADMISSION":
        raise GremlinOperatorRecordError("OPERATOR stage mismatch")
    if record.get("post_realization_complete") is not False or record.get("realization_receipt_bound") is not False:
        raise GremlinOperatorRecordError("OPERATOR realization boundary violated")
    if record.get("storage_role") != "CONTENT_ADDRESSED_PERSISTENCE_OBJECT":
        raise GremlinOperatorRecordError("OPERATOR storage role mismatch")
    if record.get("production_runtime_write") is not False or record.get("execution_admitted") is not False or record.get("canon_allowed") is not False:
        raise GremlinOperatorRecordError("OPERATOR authority boundary violated")
    if record.get("status") != "OPERATOR_RECORD_READY":
        raise GremlinOperatorRecordError("invalid OPERATOR record status")

    if radical_record is not None:
        validate_radical_record(radical_record)
        if radical_record.get("record_id") != radical_record_id:
            raise GremlinOperatorRecordError("OPERATOR persisted Radical parent mismatch")
        if radical_record.get("candidate_id") != record.get("candidate_id"):
            raise GremlinOperatorRecordError("OPERATOR candidate parent mismatch")
        if radical_record.get("radical_id") != record.get("radical_id"):
            raise GremlinOperatorRecordError("OPERATOR Radical identity parent mismatch")
        if radical_record.get("radical_scalar_commitment") != record.get("radical_scalar_commitment"):
            raise GremlinOperatorRecordError("OPERATOR Radical scalar parent mismatch")
        if radical_record.get("ordered_kaku_record_ids") != record.get("ordered_kaku_record_ids"):
            raise GremlinOperatorRecordError("OPERATOR KAKU parent lineage mismatch")
        if radical_record.get("relation_ids") != record.get("relation_lineage"):
            raise GremlinOperatorRecordError("OPERATOR Radical relation parent mismatch")

    supplied = _digest(record.get("operator_record_commitment"), "operator_record_commitment")
    core = dict(record)
    core.pop("operator_record_commitment", None)
    if supplied != _commit(core):
        raise GremlinOperatorRecordError("OPERATOR persistence commitment mismatch")
    return True


def render_operator_json(record: Mapping[str, Any]) -> bytes:
    validate_operator_record(record)
    return _canonical(record) + b"\n"


def write_immutable_operator_json(
    path: str | os.PathLike[str],
    record: Mapping[str, Any],
    *,
    create_parents: bool = False,
) -> dict[str, Any]:
    validate_operator_record(record)
    data = render_operator_json(record)
    target = Path(path)
    if create_parents:
        target.parent.mkdir(parents=True, exist_ok=True)
    if not target.parent.exists():
        raise GremlinOperatorRecordError("target parent directory does not exist")
    sha = hashlib.sha256(data).hexdigest()

    if target.exists():
        existing = target.read_bytes()
        if existing != data:
            raise GremlinOperatorRecordError("immutable OPERATOR persistence path collision")
        restored = json.loads(existing.decode("utf-8"))
        validate_operator_record(restored)
        return {
            "schema": STORE_RECEIPT_SCHEMA,
            "path": str(target),
            "operator_record_commitment": record["operator_record_commitment"],
            "sha256": sha,
            "size_bytes": len(data),
            "write_mode": "IDEMPOTENT_EXISTING_BYTES",
            "execution_admitted": False,
            "canon_allowed": False,
            "status": "IMMUTABLE_OPERATOR_STORE_CONFIRMED",
        }

    temp = target.with_name(f".{target.name}.tmp.{os.getpid()}")
    if temp.exists():
        raise GremlinOperatorRecordError("temporary OPERATOR persistence path already exists")
    try:
        with temp.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if target.exists():
            raise GremlinOperatorRecordError("immutable OPERATOR persistence path appeared during write")
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()

    return {
        "schema": STORE_RECEIPT_SCHEMA,
        "path": str(target),
        "operator_record_commitment": record["operator_record_commitment"],
        "sha256": sha,
        "size_bytes": len(data),
        "write_mode": "NEW_IMMUTABLE_OBJECT",
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "IMMUTABLE_OPERATOR_STORE_CONFIRMED",
    }
