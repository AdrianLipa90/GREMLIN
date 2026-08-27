from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

DIM = 36
CANDIDATE_SCHEMA = "GREMLIN_RELATION_CANDIDATE_V0_1"
IR_SCHEMA = "GREMLIN_PHASENAV_IR_V0_1"
IR_DOMAIN = b"GREMLIN-PHASENAV-IR/v0.1\x00"


class GremlinPhaseNavCompilerError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise GremlinPhaseNavCompilerError(f"{name} must be finite")
    return x


def _lane(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise GremlinPhaseNavCompilerError(f"{name} must be an integer lane")
    lane = int(value)
    if lane < 0 or lane >= DIM:
        raise GremlinPhaseNavCompilerError(f"{name} outside T^36 lane range")
    return lane


def _wrap_phase(value: float) -> float:
    x = math.remainder(float(value), 2.0 * math.pi)
    if x <= -math.pi:
        x += 2.0 * math.pi
    if x > math.pi:
        x -= 2.0 * math.pi
    return 0.0 if x == 0.0 else x


def _canonical_mode(ell: Sequence[int], tau: float) -> tuple[tuple[int, ...], float]:
    if len(ell) != DIM:
        raise GremlinPhaseNavCompilerError("character ell must contain exactly 36 integers")
    mode = tuple(int(v) for v in ell)
    if all(v == 0 for v in mode):
        raise GremlinPhaseNavCompilerError("zero character mode has no phase force")
    phase = _finite(tau, "tau")
    first = next(v for v in mode if v != 0)
    if first < 0:
        mode = tuple(-v for v in mode)
        phase = -phase
    return mode, _wrap_phase(phase)


def _term(kind: str, relation: Mapping[str, Any]) -> dict[str, Any]:
    gain = _finite(relation.get("gain", 1.0), "gain")
    if gain < 0.0:
        raise GremlinPhaseNavCompilerError("gain must be non-negative")

    if kind == "anchor":
        ell = [0] * DIM
        ell[_lane(relation["lane"], "lane")] = 1
        tau = _finite(relation.get("tau", 0.0), "tau")
    elif kind in {"phase_lock", "anti_lock"}:
        a = _lane(relation["a"], "a")
        b = _lane(relation["b"], "b")
        if a == b:
            raise GremlinPhaseNavCompilerError("lock relation requires distinct lanes")
        ell = [0] * DIM
        ell[a] = 1
        ell[b] = -1
        tau = 0.0 if kind == "phase_lock" else math.pi
        tau += _finite(relation.get("tau_offset", 0.0), "tau_offset")
    elif kind == "torsion":
        i = _lane(relation["i"], "i")
        j = _lane(relation["j"], "j")
        if i == j:
            raise GremlinPhaseNavCompilerError("torsion relation requires distinct lanes")
        m = int(relation["m"])
        n = int(relation["n"])
        if m == 0 or n == 0:
            raise GremlinPhaseNavCompilerError("torsion m and n must be non-zero")
        ell = [0] * DIM
        ell[i] = n
        ell[j] = -m
        tau = _finite(relation.get("tau", 0.0), "tau")
    elif kind == "character":
        ell = [int(v) for v in relation["ell"]]
        tau = _finite(relation.get("tau", 0.0), "tau")
    else:
        raise GremlinPhaseNavCompilerError(f"unsupported relation kind: {kind}")

    mode, phase = _canonical_mode(ell, tau)
    return {
        "kind": kind,
        "ell": list(mode),
        "tau_f64_hex": phase.hex(),
        "gain_f64_hex": gain.hex(),
        "source_ref": str(relation.get("source_ref", "")),
    }


def compile_phasenav_ir(candidate: Mapping[str, Any]) -> dict[str, Any]:
    if candidate.get("schema") != CANDIDATE_SCHEMA:
        raise GremlinPhaseNavCompilerError("unsupported candidate schema")
    if candidate.get("status") != "SURVIVED_AUDIT":
        raise GremlinPhaseNavCompilerError("candidate must survive audit before compilation")
    audit = candidate.get("audit")
    if not isinstance(audit, Mapping) or audit.get("belzebub_result") != "SURVIVED":
        raise GremlinPhaseNavCompilerError("BELZEBUB survival receipt required")

    relations = candidate.get("relations")
    if not isinstance(relations, list) or not relations:
        raise GremlinPhaseNavCompilerError("candidate requires at least one relation")
    if len(relations) > 256:
        raise GremlinPhaseNavCompilerError("candidate relation count exceeds v0.1 bound")

    terms = []
    for relation in relations:
        if not isinstance(relation, Mapping):
            raise GremlinPhaseNavCompilerError("relation must be a mapping")
        terms.append(_term(str(relation.get("kind", "")), relation))

    terms.sort(key=lambda t: (tuple(t["ell"]), t["tau_f64_hex"], t["gain_f64_hex"], t["kind"], t["source_ref"]))
    core = {
        "schema": IR_SCHEMA,
        "candidate_id": str(candidate.get("candidate_id", "")),
        "candidate_status": "SURVIVED_AUDIT",
        "geometry": {
            "space": "T^36",
            "dual_lattice": "Z^36",
            "dimension": DIM,
            "whole_semantic_lanes": True,
            "coordinate_position_mapping": False,
        },
        "operator": "KCHI_TORUS_CHARACTER_FIELD",
        "terms": terms,
        "normalization": {
            "first_nonzero_ell_positive": True,
            "tau_principal_wrap": True,
            "gain_nonnegative": True,
            "gcd_reduction": False,
        },
        "status": "PHASENAV_IR_CANDIDATE",
        "execution_admitted": False,
        "canon_allowed": False,
    }
    commitment = hashlib.blake2b(IR_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    return {**core, "ir_commitment": commitment}


def validate_phasenav_ir(ir: Mapping[str, Any]) -> bool:
    if ir.get("schema") != IR_SCHEMA:
        raise GremlinPhaseNavCompilerError("unsupported PhaseNav IR schema")
    geometry = ir.get("geometry")
    if not isinstance(geometry, Mapping):
        raise GremlinPhaseNavCompilerError("missing PhaseNav geometry")
    if geometry.get("space") != "T^36" or geometry.get("dual_lattice") != "Z^36" or int(geometry.get("dimension")) != DIM:
        raise GremlinPhaseNavCompilerError("invalid PhaseNav geometry")
    if geometry.get("whole_semantic_lanes") is not True or geometry.get("coordinate_position_mapping") is not False:
        raise GremlinPhaseNavCompilerError("invalid semantic-lane geometry")
    if ir.get("operator") != "KCHI_TORUS_CHARACTER_FIELD":
        raise GremlinPhaseNavCompilerError("unsupported v0.1 operator")
    if ir.get("status") != "PHASENAV_IR_CANDIDATE":
        raise GremlinPhaseNavCompilerError("wrong IR epistemic status")
    if ir.get("execution_admitted") is not False or ir.get("canon_allowed") is not False:
        raise GremlinPhaseNavCompilerError("IR authority boundary violated")
    norm = ir.get("normalization")
    if not isinstance(norm, Mapping) or norm.get("gcd_reduction") is not False:
        raise GremlinPhaseNavCompilerError("gcd reduction forbidden")

    terms = ir.get("terms")
    if not isinstance(terms, list) or not terms:
        raise GremlinPhaseNavCompilerError("non-empty character term list required")
    for term in terms:
        if not isinstance(term, Mapping):
            raise GremlinPhaseNavCompilerError("character term must be a mapping")
        mode, tau = _canonical_mode(term["ell"], float.fromhex(str(term["tau_f64_hex"])))
        if list(mode) != [int(v) for v in term["ell"]] or tau.hex() != str(term["tau_f64_hex"]):
            raise GremlinPhaseNavCompilerError("non-canonical character term")
        gain = float.fromhex(str(term["gain_f64_hex"]))
        if not math.isfinite(gain) or gain < 0.0:
            raise GremlinPhaseNavCompilerError("invalid character gain")

    supplied = str(ir.get("ir_commitment", ""))
    core = dict(ir)
    core.pop("ir_commitment", None)
    expected = hashlib.blake2b(IR_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    if supplied != expected:
        raise GremlinPhaseNavCompilerError("IR commitment mismatch")
    return True


def evaluate_ir(theta: Sequence[float], ir: Mapping[str, Any]) -> tuple[float, tuple[float, ...]]:
    validate_phasenav_ir(ir)
    if len(theta) != DIM:
        raise GremlinPhaseNavCompilerError("theta must contain exactly 36 phases")
    state = tuple(_finite(v, "theta") for v in theta)
    force = [0.0] * DIM
    potential = 0.0
    for term in ir["terms"]:
        ell = tuple(int(v) for v in term["ell"])
        tau = float.fromhex(str(term["tau_f64_hex"]))
        gain = float.fromhex(str(term["gain_f64_hex"]))
        epsilon = math.fsum(c * x for c, x in zip(ell, state)) - tau
        potential += -gain * math.cos(epsilon)
        s = gain * math.sin(epsilon)
        for lane, coeff in enumerate(ell):
            if coeff:
                force[lane] += -coeff * s
    return potential, tuple(force)
