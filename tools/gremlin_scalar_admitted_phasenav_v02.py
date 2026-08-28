from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from tools.gremlin_kaku_radical_scalar_plane_v01 import (
    validate_radical_scalar_admission,
)
from tools.gremlin_phasenav_compiler_v01 import compile_phasenav_ir, validate_phasenav_ir

SCHEMA = "GREMLIN_SCALAR_ADMITTED_PHASENAV_IR_V0_2"
DOMAIN = b"GREMLIN-SCALAR-ADMITTED-PHASENAV-IR/v0.2\x00"
POST_REALIZATION_REQUIRED = (
    "PHASE_COHERENCE_R_K",
    "SEMANTIC_MASS",
    "MASS_AWARE_GRAPH_COST",
    "OPERATOR_STABILITY_BOUND",
)


class GremlinScalarAdmissionCompileError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _candidate_relation_ids(candidate: Mapping[str, Any]) -> tuple[str, ...]:
    relations = candidate.get("relations")
    if not isinstance(relations, list) or not relations:
        raise GremlinScalarAdmissionCompileError("candidate requires explicit relations")
    refs = []
    for relation in relations:
        if not isinstance(relation, Mapping):
            raise GremlinScalarAdmissionCompileError("candidate relation must be a mapping")
        ref = str(relation.get("source_ref", ""))
        if not ref:
            raise GremlinScalarAdmissionCompileError("scalar-admitted compilation requires source_ref on every relation")
        refs.append(ref)
    if len(set(refs)) != len(refs):
        raise GremlinScalarAdmissionCompileError("candidate relation source_ref values must be unique")
    return tuple(refs)


def compile_scalar_admitted_phasenav_ir_v02(
    candidate: Mapping[str, Any],
    radical_admission: Mapping[str, Any],
) -> dict[str, Any]:
    validate_radical_scalar_admission(radical_admission)
    if radical_admission.get("status") != "PRE_VECTOR_ADMITTED":
        raise GremlinScalarAdmissionCompileError("Radical is not admitted for vector synthesis")
    if radical_admission.get("vector_synthesis_allowed") is not True:
        raise GremlinScalarAdmissionCompileError("vector synthesis gate is closed")

    candidate_id = str(candidate.get("candidate_id", ""))
    if not candidate_id or candidate_id != str(radical_admission.get("candidate_id", "")):
        raise GremlinScalarAdmissionCompileError("candidate/Radical identity mismatch")

    candidate_refs = _candidate_relation_ids(candidate)
    admitted_refs = tuple(str(v) for v in radical_admission.get("relation_ids", ()))
    if len(set(admitted_refs)) != len(admitted_refs):
        raise GremlinScalarAdmissionCompileError("Radical relation lineage contains duplicates")
    if set(candidate_refs) != set(admitted_refs):
        raise GremlinScalarAdmissionCompileError("candidate relation lineage differs from scalar-admitted Radical")

    base_ir = compile_phasenav_ir(candidate)
    validate_phasenav_ir(base_ir)

    core = {
        "schema": SCHEMA,
        "candidate_id": candidate_id,
        "radical_id": str(radical_admission["radical_id"]),
        "radical_scalar_commitment": str(radical_admission["radical_scalar_commitment"]),
        "pre_vector_admission": {
            "status": "PRE_VECTOR_ADMITTED",
            "vector_synthesis_allowed": True,
            "hard_gates": radical_admission["hard_gates"],
        },
        "relation_lineage": list(candidate_refs),
        "phasenav_ir": base_ir,
        "post_realization_scalars_required": list(POST_REALIZATION_REQUIRED),
        "realization_stage": "PHASENAV_IR_AFTER_PRE_VECTOR_ADMISSION",
        "post_realization_complete": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
    commitment = hashlib.blake2b(DOMAIN + _canonical(core), digest_size=32).hexdigest()
    return {**core, "scalar_admitted_ir_commitment": commitment}


def validate_scalar_admitted_phasenav_ir_v02(record: Mapping[str, Any]) -> bool:
    if record.get("schema") != SCHEMA:
        raise GremlinScalarAdmissionCompileError("unsupported scalar-admitted PhaseNav schema")
    if not str(record.get("candidate_id", "")) or not str(record.get("radical_id", "")):
        raise GremlinScalarAdmissionCompileError("candidate and Radical identity required")
    radical_commitment = str(record.get("radical_scalar_commitment", ""))
    if len(radical_commitment) != 64:
        raise GremlinScalarAdmissionCompileError("invalid Radical scalar commitment")
    try:
        bytes.fromhex(radical_commitment)
    except ValueError as exc:
        raise GremlinScalarAdmissionCompileError("invalid Radical scalar commitment") from exc

    admission = record.get("pre_vector_admission")
    if not isinstance(admission, Mapping):
        raise GremlinScalarAdmissionCompileError("pre-vector admission binding required")
    if admission.get("status") != "PRE_VECTOR_ADMITTED" or admission.get("vector_synthesis_allowed") is not True:
        raise GremlinScalarAdmissionCompileError("pre-vector admission binding is closed")
    gates = admission.get("hard_gates")
    if not isinstance(gates, Mapping):
        raise GremlinScalarAdmissionCompileError("hard-gate lineage required")
    expected = {
        "consent": "GRANTED",
        "reversibility": "SATISFIED",
        "no_go": "CLEAR",
    }
    for name, required in expected.items():
        gate = gates.get(name)
        if not isinstance(gate, Mapping) or gate.get("status") != required:
            raise GremlinScalarAdmissionCompileError(f"{name} gate is not admitted")

    lineage = record.get("relation_lineage")
    if not isinstance(lineage, list) or not lineage or len(set(map(str, lineage))) != len(lineage):
        raise GremlinScalarAdmissionCompileError("unique relation lineage required")

    ir = record.get("phasenav_ir")
    if not isinstance(ir, Mapping):
        raise GremlinScalarAdmissionCompileError("PhaseNav IR binding required")
    validate_phasenav_ir(ir)
    if str(ir.get("candidate_id", "")) != str(record.get("candidate_id", "")):
        raise GremlinScalarAdmissionCompileError("PhaseNav IR candidate lineage mismatch")

    if tuple(record.get("post_realization_scalars_required", ())) != POST_REALIZATION_REQUIRED:
        raise GremlinScalarAdmissionCompileError("post-realization scalar contract mismatch")
    if record.get("realization_stage") != "PHASENAV_IR_AFTER_PRE_VECTOR_ADMISSION":
        raise GremlinScalarAdmissionCompileError("wrong realization stage")
    if record.get("post_realization_complete") is not False:
        raise GremlinScalarAdmissionCompileError("post-realization scalars cannot be predeclared complete")
    if record.get("execution_admitted") is not False or record.get("canon_allowed") is not False:
        raise GremlinScalarAdmissionCompileError("scalar-admitted IR authority boundary violated")

    supplied = str(record.get("scalar_admitted_ir_commitment", ""))
    core = dict(record)
    core.pop("scalar_admitted_ir_commitment", None)
    expected_commitment = hashlib.blake2b(DOMAIN + _canonical(core), digest_size=32).hexdigest()
    if supplied != expected_commitment:
        raise GremlinScalarAdmissionCompileError("scalar-admitted IR commitment mismatch")
    return True
