from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from tools.gremlin_scalar_acquisition_v02 import (
    validate_acquired_radical_scalar_admission,
)
from tools.gremlin_scalar_admitted_phasenav_v02 import (
    compile_scalar_admitted_phasenav_ir_v02,
    validate_scalar_admitted_phasenav_ir_v02,
)

SCHEMA = "GREMLIN_ACQUISITION_BOUND_PHASENAV_IR_V0_3"
DOMAIN = b"GREMLIN-ACQUISITION-BOUND-PHASENAV-IR/v0.3\x00"


class GremlinAcquisitionBoundCompileError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash64(value: Any, name: str) -> str:
    text = str(value)
    if len(text) != 64:
        raise GremlinAcquisitionBoundCompileError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise GremlinAcquisitionBoundCompileError(f"{name} must be hexadecimal") from exc
    return text


def _acquisition_lineage(acquired_radical: Mapping[str, Any]) -> dict[str, Any]:
    radical_receipts = acquired_radical["radical_observation_receipts"]
    ordered_kaku = acquired_radical["ordered_acquired_kaku"]
    return {
        "acquired_radical_commitment": str(acquired_radical["acquired_radical_commitment"]),
        "radical_observations": {
            name: str(receipt["observation_receipt_commitment"])
            for name, receipt in sorted(radical_receipts.items())
        },
        "ordered_kaku": [
            {
                "kaku_id": str(item["kaku_packet_v01"]["kaku_id"]),
                "acquired_kaku_commitment": str(item["acquired_kaku_commitment"]),
                "observations": {
                    name: str(receipt["observation_receipt_commitment"])
                    for name, receipt in sorted(item["observation_receipts"].items())
                },
            }
            for item in ordered_kaku
        ],
    }


def compile_acquisition_bound_phasenav_ir_v03(
    candidate: Mapping[str, Any],
    acquired_radical: Mapping[str, Any],
) -> dict[str, Any]:
    validate_acquired_radical_scalar_admission(acquired_radical)
    if acquired_radical.get("status") != "ACQUIRED_PRE_VECTOR_ADMITTED":
        raise GremlinAcquisitionBoundCompileError("acquired Radical is not admitted for PhaseNav realization")

    legacy_radical = acquired_radical["radical_admission_v01"]
    scalar_admitted_ir = compile_scalar_admitted_phasenav_ir_v02(candidate, legacy_radical)
    validate_scalar_admitted_phasenav_ir_v02(scalar_admitted_ir)

    core = {
        "schema": SCHEMA,
        "candidate_id": str(scalar_admitted_ir["candidate_id"]),
        "radical_id": str(scalar_admitted_ir["radical_id"]),
        "radical_scalar_commitment": str(scalar_admitted_ir["radical_scalar_commitment"]),
        "acquired_radical_v02": dict(acquired_radical),
        "acquisition_lineage": _acquisition_lineage(acquired_radical),
        "scalar_admitted_phasenav_ir_v02": scalar_admitted_ir,
        "realization_stage": "ACQUISITION_BOUND_PHASENAV_IR_AFTER_PRE_VECTOR_ADMISSION",
        "post_realization_complete": False,
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
    commitment = hashlib.blake2b(DOMAIN + _canonical(core), digest_size=32).hexdigest()
    return {**core, "acquisition_bound_ir_commitment": commitment}


def validate_acquisition_bound_phasenav_ir_v03(record: Mapping[str, Any]) -> bool:
    if record.get("schema") != SCHEMA:
        raise GremlinAcquisitionBoundCompileError("unsupported acquisition-bound PhaseNav schema")
    if not str(record.get("candidate_id", "")) or not str(record.get("radical_id", "")):
        raise GremlinAcquisitionBoundCompileError("candidate and Radical identity required")
    _hash64(record.get("radical_scalar_commitment"), "radical_scalar_commitment")

    acquired = record.get("acquired_radical_v02")
    if not isinstance(acquired, Mapping):
        raise GremlinAcquisitionBoundCompileError("acquired Radical envelope required")
    validate_acquired_radical_scalar_admission(acquired)
    if acquired.get("status") != "ACQUIRED_PRE_VECTOR_ADMITTED":
        raise GremlinAcquisitionBoundCompileError("acquired Radical envelope is not admitted")

    lineage = record.get("acquisition_lineage")
    if not isinstance(lineage, Mapping):
        raise GremlinAcquisitionBoundCompileError("acquisition lineage required")
    if lineage != _acquisition_lineage(acquired):
        raise GremlinAcquisitionBoundCompileError("acquisition lineage differs from acquired Radical envelope")
    _hash64(lineage.get("acquired_radical_commitment"), "acquired_radical_commitment")

    radical_observations = lineage.get("radical_observations")
    if not isinstance(radical_observations, Mapping) or not radical_observations:
        raise GremlinAcquisitionBoundCompileError("Radical observation lineage required")
    for name, commitment in radical_observations.items():
        if not str(name):
            raise GremlinAcquisitionBoundCompileError("Radical observation name required")
        _hash64(commitment, f"radical_observations.{name}")

    ordered_kaku = lineage.get("ordered_kaku")
    if not isinstance(ordered_kaku, list) or not ordered_kaku:
        raise GremlinAcquisitionBoundCompileError("ordered acquired KAKU lineage required")
    kaku_ids = []
    for item in ordered_kaku:
        if not isinstance(item, Mapping):
            raise GremlinAcquisitionBoundCompileError("acquired KAKU lineage entry must be a mapping")
        kaku_id = str(item.get("kaku_id", ""))
        if not kaku_id:
            raise GremlinAcquisitionBoundCompileError("KAKU identity required")
        kaku_ids.append(kaku_id)
        _hash64(item.get("acquired_kaku_commitment"), f"{kaku_id}.acquired_kaku_commitment")
        observations = item.get("observations")
        if not isinstance(observations, Mapping) or not observations:
            raise GremlinAcquisitionBoundCompileError(f"{kaku_id} observation lineage required")
        for name, commitment in observations.items():
            _hash64(commitment, f"{kaku_id}.observations.{name}")
    if len(set(kaku_ids)) != len(kaku_ids):
        raise GremlinAcquisitionBoundCompileError("duplicate KAKU identity in acquisition lineage")

    base = record.get("scalar_admitted_phasenav_ir_v02")
    if not isinstance(base, Mapping):
        raise GremlinAcquisitionBoundCompileError("scalar-admitted PhaseNav binding required")
    validate_scalar_admitted_phasenav_ir_v02(base)
    if str(base.get("candidate_id")) != str(record.get("candidate_id")):
        raise GremlinAcquisitionBoundCompileError("candidate lineage mismatch")
    if str(base.get("radical_id")) != str(record.get("radical_id")):
        raise GremlinAcquisitionBoundCompileError("Radical lineage mismatch")
    if str(base.get("radical_scalar_commitment")) != str(record.get("radical_scalar_commitment")):
        raise GremlinAcquisitionBoundCompileError("Radical scalar commitment mismatch")

    legacy_radical = acquired["radical_admission_v01"]
    if str(legacy_radical.get("radical_id")) != str(record.get("radical_id")):
        raise GremlinAcquisitionBoundCompileError("acquired Radical identity mismatch")
    if str(legacy_radical.get("candidate_id")) != str(record.get("candidate_id")):
        raise GremlinAcquisitionBoundCompileError("acquired candidate identity mismatch")
    if str(legacy_radical.get("radical_scalar_commitment")) != str(record.get("radical_scalar_commitment")):
        raise GremlinAcquisitionBoundCompileError("acquired Radical scalar commitment mismatch")

    if record.get("realization_stage") != "ACQUISITION_BOUND_PHASENAV_IR_AFTER_PRE_VECTOR_ADMISSION":
        raise GremlinAcquisitionBoundCompileError("wrong acquisition-bound realization stage")
    if record.get("post_realization_complete") is not False:
        raise GremlinAcquisitionBoundCompileError("post-realization state cannot be predeclared complete")
    if record.get("production_runtime_write") is not False:
        raise GremlinAcquisitionBoundCompileError("acquisition-bound IR cannot grant production runtime write")
    if record.get("execution_admitted") is not False or record.get("canon_allowed") is not False:
        raise GremlinAcquisitionBoundCompileError("acquisition-bound IR authority boundary violated")

    supplied = _hash64(record.get("acquisition_bound_ir_commitment"), "acquisition_bound_ir_commitment")
    core = dict(record)
    core.pop("acquisition_bound_ir_commitment", None)
    expected = hashlib.blake2b(DOMAIN + _canonical(core), digest_size=32).hexdigest()
    if supplied != expected:
        raise GremlinAcquisitionBoundCompileError("acquisition-bound IR commitment mismatch")
    return True
