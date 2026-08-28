from __future__ import annotations

import cmath
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

SCHEMA = "GREMLIN_COMPLEX_OVERLAP_FRAME_BRIDGE_V2_3"
DOMAIN = b"GREMLIN-COMPLEX-OVERLAP-FRAME-BRIDGE/v2.3\x00"


class ComplexOverlapFrameBridgeError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(DOMAIN + _canonical(value), digest_size=32).hexdigest()


def _vec(value: Sequence[Any], name: str) -> list[complex]:
    if len(value) != 3:
        raise ComplexOverlapFrameBridgeError(f"{name} must have dimension three")
    out = [complex(z) for z in value]
    if any(not math.isfinite(z.real) or not math.isfinite(z.imag) for z in out):
        raise ComplexOverlapFrameBridgeError(f"{name} must be finite")
    return out


def _inner(a: Sequence[complex], b: Sequence[complex]) -> complex:
    return sum((complex(a[i]).conjugate() * complex(b[i]) for i in range(3)), 0j)


def _norm2(a: Sequence[complex]) -> float:
    return float(sum(abs(complex(z)) ** 2 for z in a))


def validate_orthonormal_frame_v23(frame: Sequence[Sequence[Any]], tol: float = 2e-12) -> bool:
    if len(frame) != 3:
        raise ComplexOverlapFrameBridgeError("frame must contain three states")
    f = [_vec(v, f"frame[{i}]") for i, v in enumerate(frame)]
    for i in range(3):
        for j in range(3):
            target = 1.0 if i == j else 0.0
            if abs(_inner(f[i], f[j]) - target) > tol:
                raise ComplexOverlapFrameBridgeError("frame must be orthonormal")
    return True


def flavor_amplitudes_from_overlap_frame_v23(*, frame: Sequence[Sequence[Any]], intention: Sequence[Any]) -> list[complex]:
    validate_orthonormal_frame_v23(frame)
    state = _vec(intention, "intention")
    return [_inner(_vec(frame[i], f"frame[{i}]"), state) for i in range(3)]


def _mat3(value: Sequence[Sequence[Any]], name: str) -> list[list[complex]]:
    if len(value) != 3 or any(len(row) != 3 for row in value):
        raise ComplexOverlapFrameBridgeError(f"{name} must be 3x3")
    out = [[complex(value[i][j]) for j in range(3)] for i in range(3)]
    if any(not math.isfinite(z.real) or not math.isfinite(z.imag) for row in out for z in row):
        raise ComplexOverlapFrameBridgeError(f"{name} must be finite")
    return out


def _dagger(a: Sequence[Sequence[complex]]) -> list[list[complex]]:
    return [[complex(a[j][i]).conjugate() for j in range(3)] for i in range(3)]


def _matvec(a: Sequence[Sequence[complex]], v: Sequence[complex]) -> list[complex]:
    return [sum((complex(a[i][j]) * complex(v[j]) for j in range(3)), 0j) for i in range(3)]


def _unitarity_residual(a: Sequence[Sequence[complex]]) -> float:
    u = _mat3(a, "pmns")
    ud = _dagger(u)
    worst = 0.0
    for i in range(3):
        for j in range(3):
            z = sum((ud[i][k] * u[k][j] for k in range(3)), 0j)
            worst = max(worst, abs(z - (1.0 if i == j else 0.0)))
    return worst


def mass_amplitudes_from_overlap_frame_v23(*, frame: Sequence[Sequence[Any]], intention: Sequence[Any], pmns: Sequence[Sequence[Any]]) -> list[complex]:
    u = _mat3(pmns, "pmns")
    if _unitarity_residual(u) > 2e-11:
        raise ComplexOverlapFrameBridgeError("pmns must be unitary")
    flavor = flavor_amplitudes_from_overlap_frame_v23(frame=frame, intention=intention)
    return _matvec(_dagger(u), flavor)


def probability_shadow_v23(amplitudes: Sequence[Any]) -> list[float]:
    if len(amplitudes) != 3:
        raise ComplexOverlapFrameBridgeError("three amplitudes are required")
    return [abs(complex(z)) ** 2 for z in amplitudes]


def phase_loss_witness_v23(*, pmns: Sequence[Sequence[Any]], phase_rad: float = 0.73) -> dict[str, Any]:
    a = [1 / math.sqrt(2), 1 / math.sqrt(2), 0j]
    b = [1 / math.sqrt(2), cmath.exp(1j * phase_rad) / math.sqrt(2), 0j]
    frame = [[1 + 0j, 0j, 0j], [0j, 1 + 0j, 0j], [0j, 0j, 1 + 0j]]
    ma = mass_amplitudes_from_overlap_frame_v23(frame=frame, intention=a, pmns=pmns)
    mb = mass_amplitudes_from_overlap_frame_v23(frame=frame, intention=b, pmns=pmns)
    same_R = max(abs(x - y) for x, y in zip(probability_shadow_v23(a), probability_shadow_v23(b))) <= 2e-15
    mass_amp_delta = max(abs(ma[i] - mb[i]) for i in range(3))
    return {"same_probability_shadow": same_R, "mass_amplitude_delta": mass_amp_delta}


def build_complex_overlap_frame_bridge_v23(
    *,
    audit_id: str,
    frame: Sequence[Sequence[Any]],
    intention: Sequence[Any],
    pmns: Sequence[Sequence[Any]],
    symbolic_hilbert_source_ref: str,
    resonance_source_ref: str,
    neutrino_fixed_point_source_ref: str,
    pmns_source_ref: str,
    embedding_source_status: str = "UNRESOLVED_CROSS_HILBERT_IDENTIFICATION",
    epistemic_status: str = "CANDIDATE",
) -> dict[str, Any]:
    if not str(audit_id):
        raise ComplexOverlapFrameBridgeError("audit_id must be non-empty")
    for value, name in (
        (symbolic_hilbert_source_ref, "symbolic_hilbert_source_ref"),
        (resonance_source_ref, "resonance_source_ref"),
        (neutrino_fixed_point_source_ref, "neutrino_fixed_point_source_ref"),
        (pmns_source_ref, "pmns_source_ref"),
        (embedding_source_status, "embedding_source_status"),
        (epistemic_status, "epistemic_status"),
    ):
        if not str(value):
            raise ComplexOverlapFrameBridgeError(f"{name} must be non-empty")
    validate_orthonormal_frame_v23(frame)
    state = _vec(intention, "intention")
    u = _mat3(pmns, "pmns")
    ures = _unitarity_residual(u)
    if ures > 2e-11:
        raise ComplexOverlapFrameBridgeError("pmns must be unitary")
    flav = flavor_amplitudes_from_overlap_frame_v23(frame=frame, intention=state)
    mass = mass_amplitudes_from_overlap_frame_v23(frame=frame, intention=state, pmns=u)
    frame_span_norm_residual = abs(_norm2(state) - _norm2(flav))
    pmns_norm_residual = abs(_norm2(flav) - _norm2(mass))
    witness = phase_loss_witness_v23(pmns=u)
    physical_bound = embedding_source_status == "SOURCE_BOUND_ORTHONORMAL_NEUTRINO_TRIPLE"
    core = {
        "schema": SCHEMA,
        "audit_id": str(audit_id),
        "auditor": "BELZEBUB",
        "candidate_generator": "GREMLIN",
        "construction": "C_nu(I)_alpha=<S_nu_alpha|I>; J_mass=U_PMNS^dagger C_nu",
        "frame_dimension": 3,
        "frame_orthonormal": True,
        "frame_span_norm_residual_f64_hex": frame_span_norm_residual.hex(),
        "pmns_unitarity_residual_f64_hex": ures.hex(),
        "pmns_norm_residual_f64_hex": pmns_norm_residual.hex(),
        "flavor_probability_shadow": [v.hex() for v in probability_shadow_v23(flav)],
        "phase_loss_witness": {"same_R": bool(witness["same_probability_shadow"]), "mass_amplitude_delta_f64_hex": float(witness["mass_amplitude_delta"]).hex()},
        "R_is_probability_shadow_not_full_bridge": True,
        "complex_overlap_required": True,
        "conditional_J_matrix_freedom": "NONE_ON_BOUND_LABELED_ORTHONORMAL_TRIPLE_EXCEPT_BASIS_PHASE_CONVENTIONS",
        "symbolic_hilbert_source_ref": str(symbolic_hilbert_source_ref),
        "resonance_source_ref": str(resonance_source_ref),
        "neutrino_fixed_point_source_ref": str(neutrino_fixed_point_source_ref),
        "pmns_source_ref": str(pmns_source_ref),
        "embedding_source_status": str(embedding_source_status),
        "physical_J_identified": physical_bound,
        "remaining_bridge_debt": [] if physical_bound else [
            "bind the geometric neutrino triple to an orthonormal triple in the same symbolic/intention Hilbert space",
            "bind the PMNS orientation with declared source provenance",
        ],
        "belzebub_verdict": "CONDITIONAL_COMPLEX_OVERLAP_BRIDGE_CLOSES_ARBITRARY_U3__PHYSICAL_EMBEDDING_STILL_OPEN" if not physical_bound else "SOURCE_BOUND_COMPLEX_OVERLAP_BRIDGE_IDENTIFIED",
        "canon_status": "CANDIDATE",
        "execution_status": "RESEARCH_AUDIT_ONLY",
        "epistemic_status": str(epistemic_status),
    }
    return {**core, "complex_overlap_frame_bridge_commitment": _seal(core)}


def validate_complex_overlap_frame_bridge_v23(receipt: Mapping[str, Any]) -> bool:
    if receipt.get("schema") != SCHEMA:
        raise ComplexOverlapFrameBridgeError("unsupported v2.3 schema")
    commitment = str(receipt.get("complex_overlap_frame_bridge_commitment", ""))
    if len(commitment) != 64:
        raise ComplexOverlapFrameBridgeError("missing v2.3 commitment")
    try:
        bytes.fromhex(commitment)
    except ValueError as exc:
        raise ComplexOverlapFrameBridgeError("commitment must be hexadecimal") from exc
    core = dict(receipt)
    core.pop("complex_overlap_frame_bridge_commitment", None)
    if commitment != _seal(core):
        raise ComplexOverlapFrameBridgeError("v2.3 commitment mismatch")
    return True
