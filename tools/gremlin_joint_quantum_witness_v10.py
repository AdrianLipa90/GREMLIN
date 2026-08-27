from __future__ import annotations

import cmath
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from tools.gremlin_connection_path_holonomy_v09 import validate_qhtri_connection_derived_lag_v09

HBAR_SI = 1.054_571_817e-34

JOINT_STATE_SCHEMA = "GREMLIN_JOINT_PURE_STATE_V1_0"
JOINT_STATE_DOMAIN = b"GREMLIN-JOINT-PURE-STATE/v1.0\x00"
ENTANGLEMENT_WITNESS_SCHEMA = "GREMLIN_PURE_TWO_QUBIT_ENTANGLEMENT_WITNESS_V1_0"
ENTANGLEMENT_WITNESS_DOMAIN = b"GREMLIN-PURE-TWO-QUBIT-ENTANGLEMENT-WITNESS/v1.0\x00"
ZZ_EVOLUTION_SCHEMA = "GREMLIN_RELATIONAL_ZZ_COUPLING_EVOLUTION_V1_0"
ZZ_EVOLUTION_DOMAIN = b"GREMLIN-RELATIONAL-ZZ-COUPLING-EVOLUTION/v1.0\x00"

BASIS = ("00", "01", "10", "11")


class JointQuantumWitnessError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(domain: bytes, value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    text = str(value)
    if not text:
        raise JointQuantumWitnessError(f"{name} must be non-empty")
    return text


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise JointQuantumWitnessError(f"{name} must be finite")
    return x


def _nonnegative(value: Any, name: str) -> float:
    x = _finite(value, name)
    if x < 0.0:
        raise JointQuantumWitnessError(f"{name} must be non-negative")
    return x


def _hash64(value: Any, name: str) -> str:
    text = _nonempty(value, name)
    if len(text) != 64:
        raise JointQuantumWitnessError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise JointQuantumWitnessError(f"{name} must be hexadecimal") from exc
    return text


def _complex(value: Any, name: str) -> complex:
    if isinstance(value, complex):
        z = value
    elif isinstance(value, (tuple, list)) and len(value) == 2:
        z = complex(_finite(value[0], f"{name}.re"), _finite(value[1], f"{name}.im"))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        z = complex(_finite(value, name), 0.0)
    else:
        raise JointQuantumWitnessError(f"{name} must be complex, real, or [re, im]")
    if not math.isfinite(z.real) or not math.isfinite(z.imag):
        raise JointQuantumWitnessError(f"{name} must be finite")
    return z


def _encode_complex(z: complex) -> dict[str, str]:
    return {"re_f64_hex": float(z.real).hex(), "im_f64_hex": float(z.imag).hex()}


def _decode_complex(value: Mapping[str, Any], name: str) -> complex:
    if not isinstance(value, Mapping):
        raise JointQuantumWitnessError(f"{name} must be a complex encoding")
    try:
        re = float.fromhex(str(value.get("re_f64_hex")))
        im = float.fromhex(str(value.get("im_f64_hex")))
    except (TypeError, ValueError) as exc:
        raise JointQuantumWitnessError(f"{name} complex encoding malformed") from exc
    return _complex(complex(re, im), name)


def _decode_amplitudes(encoded: Sequence[Mapping[str, Any]]) -> list[complex]:
    if not isinstance(encoded, list) or len(encoded) != 4:
        raise JointQuantumWitnessError("joint state requires exactly four amplitudes")
    return [_decode_complex(v, f"amplitude[{i}]") for i, v in enumerate(encoded)]


def _concurrence(amplitudes: Sequence[complex]) -> float:
    a00, a01, a10, a11 = amplitudes
    c = 2.0 * abs(a00 * a11 - a01 * a10)
    if c < 0.0:
        c = 0.0
    if c > 1.0 and c < 1.0 + 1e-12:
        c = 1.0
    return c


def build_joint_pure_state_v10(
    *,
    qhtri_receipt: Mapping[str, Any],
    amplitudes: Sequence[Any],
    source_ref: str,
    epistemic_status: str,
) -> dict[str, Any]:
    validate_qhtri_connection_derived_lag_v09(qhtri_receipt)
    if len(amplitudes) != 4:
        raise JointQuantumWitnessError("joint pure state requires four basis amplitudes")
    raw = [_complex(v, f"amplitude[{i}]") for i, v in enumerate(amplitudes)]
    norm2 = math.fsum((z.real * z.real + z.imag * z.imag) for z in raw)
    if norm2 <= 0.0:
        raise JointQuantumWitnessError("joint pure state norm must be positive")
    norm = math.sqrt(norm2)
    normalized = [z / norm for z in raw]
    normalized_norm2 = math.fsum((z.real * z.real + z.imag * z.imag) for z in normalized)
    core = {
        "schema": JOINT_STATE_SCHEMA,
        "basis_order": list(BASIS),
        "state_dimension": 4,
        "state_kind": "PURE_TWO_QUBIT_RELATIONAL_CANDIDATE",
        "qhtri_connection_derived_commitment": str(qhtri_receipt["qhtri_connection_derived_commitment"]),
        "tau_origin": str(qhtri_receipt["tau_origin"]),
        "input_norm2_f64_hex": norm2.hex(),
        "normalized_norm2_f64_hex": normalized_norm2.hex(),
        "amplitudes": [_encode_complex(z) for z in normalized],
        "normalization_law": "psi=psi_raw/sqrt(sum_k(|a_k|^2))",
        "source_ref": _nonempty(source_ref, "source_ref"),
        "epistemic_status": _nonempty(epistemic_status, "epistemic_status"),
        "state_generation_attribution": "OPEN",
        "entanglement_status": "UNASSESSED",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "JOINT_PURE_STATE_BOUND",
    }
    return {**core, "joint_state_commitment": _seal(JOINT_STATE_DOMAIN, core)}


def validate_joint_pure_state_v10(state: Mapping[str, Any]) -> bool:
    if state.get("schema") != JOINT_STATE_SCHEMA:
        raise JointQuantumWitnessError("unsupported joint-state schema")
    if state.get("basis_order") != list(BASIS) or state.get("state_dimension") != 4:
        raise JointQuantumWitnessError("joint-state basis/dimension mismatch")
    if state.get("state_kind") != "PURE_TWO_QUBIT_RELATIONAL_CANDIDATE":
        raise JointQuantumWitnessError("joint-state kind mismatch")
    _hash64(state.get("qhtri_connection_derived_commitment"), "qhtri_connection_derived_commitment")
    if state.get("tau_origin") != "CONNECTION_PATH_INTEGRAL":
        raise JointQuantumWitnessError("joint-state tau provenance mismatch")
    amplitudes = _decode_amplitudes(state.get("amplitudes"))
    norm2 = math.fsum((z.real * z.real + z.imag * z.imag) for z in amplitudes)
    if abs(norm2 - 1.0) > 1e-12:
        raise JointQuantumWitnessError("joint state must remain normalized")
    input_norm2 = _nonnegative(float.fromhex(str(state.get("input_norm2_f64_hex"))), "input_norm2")
    normalized_norm2 = _nonnegative(float.fromhex(str(state.get("normalized_norm2_f64_hex"))), "normalized_norm2")
    if input_norm2 <= 0.0 or abs(normalized_norm2 - norm2) > 1e-15:
        raise JointQuantumWitnessError("joint-state normalization receipt mismatch")
    if state.get("normalization_law") != "psi=psi_raw/sqrt(sum_k(|a_k|^2))":
        raise JointQuantumWitnessError("joint-state normalization law mismatch")
    _nonempty(state.get("source_ref"), "source_ref")
    _nonempty(state.get("epistemic_status"), "epistemic_status")
    expected = {
        "state_generation_attribution": "OPEN",
        "entanglement_status": "UNASSESSED",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "JOINT_PURE_STATE_BOUND",
    }
    for key, value in expected.items():
        if state.get(key) != value:
            raise JointQuantumWitnessError(f"joint-state status mismatch: {key}")
    supplied = _hash64(state.get("joint_state_commitment"), "joint_state_commitment")
    core = dict(state)
    core.pop("joint_state_commitment", None)
    if supplied != _seal(JOINT_STATE_DOMAIN, core):
        raise JointQuantumWitnessError("joint-state commitment mismatch")
    return True


def build_entanglement_witness_v10(
    *,
    state: Mapping[str, Any],
    witness_tolerance: Any = 1e-12,
) -> dict[str, Any]:
    validate_joint_pure_state_v10(state)
    tol = _nonnegative(witness_tolerance, "witness_tolerance")
    amplitudes = _decode_amplitudes(state["amplitudes"])
    concurrence = _concurrence(amplitudes)
    reduced_purity = 1.0 - 0.5 * concurrence * concurrence
    separable = concurrence <= tol
    witness_status = "SEPARABLE_WITHIN_TOLERANCE" if separable else "ENTANGLED_PURE_STATE_WITNESS"
    core = {
        "schema": ENTANGLEMENT_WITNESS_SCHEMA,
        "joint_state_commitment": str(state["joint_state_commitment"]),
        "concurrence_f64_hex": concurrence.hex(),
        "concurrence_law": "C=2*abs(a00*a11-a01*a10)",
        "reduced_single_qubit_purity_f64_hex": reduced_purity.hex(),
        "purity_law": "Tr(rho_A^2)=1-C^2/2 for pure two-qubit states",
        "witness_tolerance_f64_hex": tol.hex(),
        "separable_within_tolerance": separable,
        "witness_status": witness_status,
        "synchronization_entanglement_equivalence": False,
        "generation_attribution": "OPEN_REQUIRES_EVOLUTION_WITNESS",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "PURE_TWO_QUBIT_ENTANGLEMENT_ASSESSED",
    }
    return {**core, "entanglement_witness_commitment": _seal(ENTANGLEMENT_WITNESS_DOMAIN, core)}


def validate_entanglement_witness_v10(witness: Mapping[str, Any], *, state: Mapping[str, Any]) -> bool:
    validate_joint_pure_state_v10(state)
    if witness.get("schema") != ENTANGLEMENT_WITNESS_SCHEMA:
        raise JointQuantumWitnessError("unsupported entanglement-witness schema")
    if str(witness.get("joint_state_commitment")) != str(state["joint_state_commitment"]):
        raise JointQuantumWitnessError("entanglement witness state lineage mismatch")
    amplitudes = _decode_amplitudes(state["amplitudes"])
    expected_c = _concurrence(amplitudes)
    actual_c = _nonnegative(float.fromhex(str(witness.get("concurrence_f64_hex"))), "concurrence")
    if actual_c.hex() != expected_c.hex():
        raise JointQuantumWitnessError("concurrence mismatch")
    expected_purity = 1.0 - 0.5 * expected_c * expected_c
    actual_purity = _finite(float.fromhex(str(witness.get("reduced_single_qubit_purity_f64_hex"))), "reduced_purity")
    if actual_purity.hex() != expected_purity.hex():
        raise JointQuantumWitnessError("reduced purity mismatch")
    tol = _nonnegative(float.fromhex(str(witness.get("witness_tolerance_f64_hex"))), "witness_tolerance")
    separable = expected_c <= tol
    expected_status = "SEPARABLE_WITHIN_TOLERANCE" if separable else "ENTANGLED_PURE_STATE_WITNESS"
    if witness.get("separable_within_tolerance") is not separable or witness.get("witness_status") != expected_status:
        raise JointQuantumWitnessError("entanglement classification mismatch")
    if witness.get("concurrence_law") != "C=2*abs(a00*a11-a01*a10)":
        raise JointQuantumWitnessError("concurrence law mismatch")
    if witness.get("purity_law") != "Tr(rho_A^2)=1-C^2/2 for pure two-qubit states":
        raise JointQuantumWitnessError("purity law mismatch")
    expected = {
        "synchronization_entanglement_equivalence": False,
        "generation_attribution": "OPEN_REQUIRES_EVOLUTION_WITNESS",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "PURE_TWO_QUBIT_ENTANGLEMENT_ASSESSED",
    }
    for key, value in expected.items():
        if witness.get(key) != value:
            raise JointQuantumWitnessError(f"entanglement witness status mismatch: {key}")
    supplied = _hash64(witness.get("entanglement_witness_commitment"), "entanglement_witness_commitment")
    core = dict(witness)
    core.pop("entanglement_witness_commitment", None)
    if supplied != _seal(ENTANGLEMENT_WITNESS_DOMAIN, core):
        raise JointQuantumWitnessError("entanglement witness commitment mismatch")
    return True


def build_zz_coupling_evolution_v10(
    *,
    initial_state: Mapping[str, Any],
    coupling_energy_j: Any,
    duration_s: Any,
    coupling_source_ref: str,
    coupling_source_commitment: str,
    coupling_epistemic_status: str,
    witness_tolerance: Any = 1e-12,
) -> dict[str, Any]:
    validate_joint_pure_state_v10(initial_state)
    j_rel = _finite(coupling_energy_j, "coupling_energy_j")
    dt = _nonnegative(duration_s, "duration_s")
    tol = _nonnegative(witness_tolerance, "witness_tolerance")
    chi = (j_rel * dt) / HBAR_SI
    if not math.isfinite(chi):
        raise JointQuantumWitnessError("dimensionless coupling phase chi must be finite")
    initial = _decode_amplitudes(initial_state["amplitudes"])
    phase_same = cmath.exp(-1j * chi)
    phase_opposite = cmath.exp(1j * chi)
    final = [
        initial[0] * phase_same,
        initial[1] * phase_opposite,
        initial[2] * phase_opposite,
        initial[3] * phase_same,
    ]
    initial_c = _concurrence(initial)
    final_c = _concurrence(final)
    generated = initial_c <= tol and final_c > tol
    generation_status = (
        "ENTANGLEMENT_GENERATED_BY_DECLARED_ZZ_COUPLING_WITHIN_MODEL"
        if generated
        else "NO_NEW_ENTANGLEMENT_WITNESSED_WITHIN_MODEL"
    )
    core = {
        "schema": ZZ_EVOLUTION_SCHEMA,
        "initial_joint_state_commitment": str(initial_state["joint_state_commitment"]),
        "qhtri_connection_derived_commitment": str(initial_state["qhtri_connection_derived_commitment"]),
        "tau_origin": str(initial_state["tau_origin"]),
        "hamiltonian_law": "H_rel=J_rel*(sigma_z tensor sigma_z)",
        "unitary_law": "U_rel=exp(-i*H_rel*dt/hbar)",
        "coupling_energy_j_f64_hex": j_rel.hex(),
        "duration_s_f64_hex": dt.hex(),
        "chi_Jdt_over_hbar_f64_hex": chi.hex(),
        "final_amplitudes": [_encode_complex(z) for z in final],
        "initial_concurrence_f64_hex": initial_c.hex(),
        "final_concurrence_f64_hex": final_c.hex(),
        "witness_tolerance_f64_hex": tol.hex(),
        "entanglement_generated": generated,
        "generation_status": generation_status,
        "coupling_source_ref": _nonempty(coupling_source_ref, "coupling_source_ref"),
        "coupling_source_commitment": _hash64(coupling_source_commitment, "coupling_source_commitment"),
        "coupling_epistemic_status": _nonempty(coupling_epistemic_status, "coupling_epistemic_status"),
        "coupling_energy_scale_origin": "EXPLICIT_UPSTREAM_OR_MODEL_ADAPTER",
        "lambda_holonomy_to_J_rel_derivation_status": "OPEN",
        "entanglement_generation_attribution_scope": "DECLARED_ZZ_MODEL_ONLY",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "RELATIONAL_ZZ_COUPLING_EVOLUTION_ASSESSED",
    }
    return {**core, "zz_evolution_commitment": _seal(ZZ_EVOLUTION_DOMAIN, core)}


def validate_zz_coupling_evolution_v10(evolution: Mapping[str, Any], *, initial_state: Mapping[str, Any]) -> bool:
    validate_joint_pure_state_v10(initial_state)
    if evolution.get("schema") != ZZ_EVOLUTION_SCHEMA:
        raise JointQuantumWitnessError("unsupported ZZ-evolution schema")
    if str(evolution.get("initial_joint_state_commitment")) != str(initial_state["joint_state_commitment"]):
        raise JointQuantumWitnessError("ZZ evolution initial-state lineage mismatch")
    if str(evolution.get("qhtri_connection_derived_commitment")) != str(initial_state["qhtri_connection_derived_commitment"]):
        raise JointQuantumWitnessError("ZZ evolution QHTRI lineage mismatch")
    if evolution.get("tau_origin") != "CONNECTION_PATH_INTEGRAL":
        raise JointQuantumWitnessError("ZZ evolution tau provenance mismatch")
    j_rel = _finite(float.fromhex(str(evolution.get("coupling_energy_j_f64_hex"))), "coupling_energy_j")
    dt = _nonnegative(float.fromhex(str(evolution.get("duration_s_f64_hex"))), "duration_s")
    expected_chi = (j_rel * dt) / HBAR_SI
    actual_chi = _finite(float.fromhex(str(evolution.get("chi_Jdt_over_hbar_f64_hex"))), "chi")
    if actual_chi.hex() != expected_chi.hex():
        raise JointQuantumWitnessError("ZZ evolution chi mismatch")
    initial = _decode_amplitudes(initial_state["amplitudes"])
    phase_same = cmath.exp(-1j * expected_chi)
    phase_opposite = cmath.exp(1j * expected_chi)
    expected_final = [initial[0] * phase_same, initial[1] * phase_opposite, initial[2] * phase_opposite, initial[3] * phase_same]
    actual_final = _decode_amplitudes(evolution.get("final_amplitudes"))
    for i, (a, b) in enumerate(zip(actual_final, expected_final)):
        if a.real.hex() != b.real.hex() or a.imag.hex() != b.imag.hex():
            raise JointQuantumWitnessError(f"ZZ final amplitude mismatch at basis index {i}")
    expected_initial_c = _concurrence(initial)
    expected_final_c = _concurrence(expected_final)
    actual_initial_c = _nonnegative(float.fromhex(str(evolution.get("initial_concurrence_f64_hex"))), "initial_concurrence")
    actual_final_c = _nonnegative(float.fromhex(str(evolution.get("final_concurrence_f64_hex"))), "final_concurrence")
    if actual_initial_c.hex() != expected_initial_c.hex() or actual_final_c.hex() != expected_final_c.hex():
        raise JointQuantumWitnessError("ZZ concurrence receipt mismatch")
    tol = _nonnegative(float.fromhex(str(evolution.get("witness_tolerance_f64_hex"))), "witness_tolerance")
    generated = expected_initial_c <= tol and expected_final_c > tol
    expected_generation_status = (
        "ENTANGLEMENT_GENERATED_BY_DECLARED_ZZ_COUPLING_WITHIN_MODEL"
        if generated
        else "NO_NEW_ENTANGLEMENT_WITNESSED_WITHIN_MODEL"
    )
    if evolution.get("entanglement_generated") is not generated or evolution.get("generation_status") != expected_generation_status:
        raise JointQuantumWitnessError("ZZ entanglement-generation classification mismatch")
    if evolution.get("hamiltonian_law") != "H_rel=J_rel*(sigma_z tensor sigma_z)" or evolution.get("unitary_law") != "U_rel=exp(-i*H_rel*dt/hbar)":
        raise JointQuantumWitnessError("ZZ evolution law mismatch")
    _nonempty(evolution.get("coupling_source_ref"), "coupling_source_ref")
    _hash64(evolution.get("coupling_source_commitment"), "coupling_source_commitment")
    _nonempty(evolution.get("coupling_epistemic_status"), "coupling_epistemic_status")
    expected = {
        "coupling_energy_scale_origin": "EXPLICIT_UPSTREAM_OR_MODEL_ADAPTER",
        "lambda_holonomy_to_J_rel_derivation_status": "OPEN",
        "entanglement_generation_attribution_scope": "DECLARED_ZZ_MODEL_ONLY",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "RELATIONAL_ZZ_COUPLING_EVOLUTION_ASSESSED",
    }
    for key, value in expected.items():
        if evolution.get(key) != value:
            raise JointQuantumWitnessError(f"ZZ evolution status mismatch: {key}")
    supplied = _hash64(evolution.get("zz_evolution_commitment"), "zz_evolution_commitment")
    core = dict(evolution)
    core.pop("zz_evolution_commitment", None)
    if supplied != _seal(ZZ_EVOLUTION_DOMAIN, core):
        raise JointQuantumWitnessError("ZZ evolution commitment mismatch")
    return True
