from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from tools.gremlin_phasenav_compiler_v01 import DIM, validate_phasenav_ir

PROTOTYPE_SCHEMA = "GREMLIN_UNTRUSTED_PROTOTYPE_V0_1"
PROTOTYPE_DOMAIN = b"GREMLIN-UNTRUSTED-PROTOTYPE/v0.1\x00"


class GremlinPrototypeBuilderError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _linear_expression(ell: list[int]) -> str:
    pieces = []
    for lane, coeff in enumerate(ell):
        if coeff:
            pieces.append(f"({coeff}) * theta[{lane}]")
    return " + ".join(pieces) if pieces else "0.0"


def _source_for_ir(ir: Mapping[str, Any]) -> str:
    lines = [
        "def evaluate(theta):",
        f"    if len(theta) != {DIM}:",
        f"        raise ValueError('theta must contain exactly {DIM} phases')",
        f"    force = [0.0] * {DIM}",
        "    potential = 0.0",
    ]
    for index, term in enumerate(ir["terms"]):
        ell = [int(v) for v in term["ell"]]
        tau = float.fromhex(str(term["tau_f64_hex"]))
        gain = float.fromhex(str(term["gain_f64_hex"]))
        lines.append(f"    epsilon_{index} = ({_linear_expression(ell)}) - ({tau.hex()})")
        lines.append(f"    potential += -({gain.hex()}) * math.cos(epsilon_{index})")
        lines.append(f"    s_{index} = ({gain.hex()}) * math.sin(epsilon_{index})")
        for lane, coeff in enumerate(ell):
            if coeff:
                lines.append(f"    force[{lane}] += -({coeff}) * s_{index}")
    lines.append("    return potential, tuple(force)")
    lines.append("")
    return "\n".join(lines)


def build_python_reference_prototype(ir: Mapping[str, Any]) -> dict[str, Any]:
    validate_phasenav_ir(ir)
    source = _source_for_ir(ir)
    core = {
        "schema": PROTOTYPE_SCHEMA,
        "target": "python_reference",
        "source_ir_commitment": str(ir["ir_commitment"]),
        "entrypoint": "evaluate",
        "source": source,
        "status": "UNTRUSTED_PROTOTYPE",
        "sandbox_required": True,
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
    commitment = hashlib.blake2b(PROTOTYPE_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    return {**core, "prototype_commitment": commitment}


def validate_prototype(prototype: Mapping[str, Any], ir: Mapping[str, Any]) -> bool:
    validate_phasenav_ir(ir)
    if prototype.get("schema") != PROTOTYPE_SCHEMA:
        raise GremlinPrototypeBuilderError("unsupported prototype schema")
    if prototype.get("target") != "python_reference" or prototype.get("entrypoint") != "evaluate":
        raise GremlinPrototypeBuilderError("unsupported prototype target")
    if prototype.get("source_ir_commitment") != ir.get("ir_commitment"):
        raise GremlinPrototypeBuilderError("prototype/IR lineage mismatch")
    if prototype.get("status") != "UNTRUSTED_PROTOTYPE":
        raise GremlinPrototypeBuilderError("wrong prototype epistemic status")
    if prototype.get("sandbox_required") is not True or prototype.get("production_runtime_write") is not False:
        raise GremlinPrototypeBuilderError("prototype sandbox boundary violated")
    if prototype.get("execution_admitted") is not False or prototype.get("canon_allowed") is not False:
        raise GremlinPrototypeBuilderError("prototype authority boundary violated")
    if str(prototype.get("source", "")) != _source_for_ir(ir):
        raise GremlinPrototypeBuilderError("prototype source is not deterministic from IR")

    supplied = str(prototype.get("prototype_commitment", ""))
    core = dict(prototype)
    core.pop("prototype_commitment", None)
    expected = hashlib.blake2b(PROTOTYPE_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    if supplied != expected:
        raise GremlinPrototypeBuilderError("prototype commitment mismatch")
    return True
