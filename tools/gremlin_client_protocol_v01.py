from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from tools.gremlin_experiment_harness_v01 import run_reference_experiment
from tools.gremlin_phasenav_compiler_v01 import compile_phasenav_ir
from tools.gremlin_prototype_builder_v01 import build_python_reference_prototype

REQUEST_SCHEMA = "GREMLIN_CLIENT_PROTOTYPE_REQUEST_V0_1"
RESPONSE_SCHEMA = "GREMLIN_CLIENT_PROTOTYPE_RESPONSE_V0_1"
RESPONSE_DOMAIN = b"GREMLIN-CLIENT-PROTOTYPE-RESPONSE/v0.1\x00"


class GremlinClientProtocolError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def run_client_request(request: Mapping[str, Any]) -> dict[str, Any]:
    if request.get("schema") != REQUEST_SCHEMA:
        raise GremlinClientProtocolError("unsupported client request schema")
    if request.get("target", "python_reference") != "python_reference":
        raise GremlinClientProtocolError("v0.1 supports python_reference prototypes only")
    if request.get("request_execution_admission") is True:
        raise GremlinClientProtocolError("client cannot grant production execution admission")
    if request.get("request_canon_promotion") is True:
        raise GremlinClientProtocolError("client cannot promote GREMLIN output to canon")

    candidate = request.get("candidate")
    if not isinstance(candidate, Mapping):
        raise GremlinClientProtocolError("candidate mapping required")

    ir = compile_phasenav_ir(candidate)
    prototype = build_python_reference_prototype(ir)
    receipt = run_reference_experiment(
        ir,
        prototype,
        sample_count=int(request.get("sample_count", 64)),
        tolerance=float(request.get("tolerance", 1e-12)),
    )

    core = {
        "schema": RESPONSE_SCHEMA,
        "request_id": str(request.get("request_id", "")),
        "candidate_id": str(candidate.get("candidate_id", "")),
        "pipeline": [
            "SURVIVED_AUDIT",
            "PHASENAV_IR_CANDIDATE",
            "UNTRUSTED_PROTOTYPE",
            receipt["status"],
        ],
        "artifacts": {
            "phasenav_ir": ir,
            "prototype": prototype,
            "experiment_receipt": receipt,
        },
        "status": receipt["status"],
        "validation_scope": receipt["validation_scope"],
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
    response_commitment = hashlib.blake2b(RESPONSE_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    return {**core, "response_commitment": response_commitment}
