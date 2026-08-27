from __future__ import annotations

import cmath
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from tools.gremlin_connection_path_holonomy_v09 import validate_qhtri_connection_derived_lag_v09
from tools.gremlin_joint_quantum_witness_v10 import HBAR_SI, validate_joint_pure_state_v10
from tools.gremlin_oriented_relational_coupling_v13 import validate_oriented_relational_coupling_v13

HAMILTONIAN_SCHEMA = "GREMLIN_HERMITIAN_ORIENTED_EXCHANGE_V1_4"
HAMILTONIAN_DOMAIN = b"GREMLIN-HERMITIAN-ORIENTED-EXCHANGE/v1.4\x00"
EVOLUTION_SCHEMA = "GREMLIN_HERMITIAN_ORIENTED_EXCHANGE_EVOLUTION_V1_4"
EVOLUTION_DOMAIN = b"GREMLIN-HERMITIAN-ORIENTED-EXCHANGE-EVOLUTION/v1.4\x00"
BASIS = ("00", "01", "10", "11")


class HermitianOrientedExchangeError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(domain: bytes, value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise HermitianOrientedExchangeError(f"{name} must be finite")
    return x


def _nonnegative(value: Any, name: str) -> float:
    x = _finite(value, name)
    if x < 0.0:
        raise HermitianOrientedExchangeError(f"{name} must be non-negative")
    return x


def _hash64(value: Any, name: str) -> str:
    text = str(value)
    if len(text) != 64:
        raise HermitianOrientedExchangeError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise HermitianOrientedExchangeError(f"{name} must be hexadecimal") from exc
    return text


def _from_hex(value: Any, name: str) -> float:
    try:
        return _finite(float.fromhex(str(value)), name)
    except ValueError as exc:
        raise HermitianOrientedExchangeError(f"{name} must be a binary64 hex float") from exc


def _encode_complex(z: complex) -> dict[str, str]:
    return {"re_f64_hex": float(z.real).hex(), "im_f64_hex": float(z.imag).hex()}


def _decode_complex(value: Mapping[str, Any], name: str) -> complex:
    if not isinstance(value, Mapping):
        raise HermitianOrientedExchangeError(f"{name} must be a complex encoding")
    try:
        re = float.fromhex(str(value.get("re_f64_hex")))
        im = float.fromhex(str(value.get("im_f64_hex")))
    except (TypeError, ValueError) as exc:
        raise HermitianOrientedExchangeError(f"{name} complex encoding malformed") from exc
    if not math.isfinite(re) or not math.isfinite(im):
        raise HermitianOrientedExchangeError(f"{name} must be finite")
    return complex(re, im)


def _decode_amplitudes(encoded: Any) -> list[complex]:
    if not isinstance(encoded, list) or len(encoded) != 4:
        raise HermitianOrientedExchangeError("joint state requires four encoded amplitudes")
    return [_decode_complex(value, f"amplitude[{i}]") for i, value in enumerate(encoded)]


def _concurrence(amplitudes: Sequence[complex]) -> float:
    a00, a01, a10, a11 = amplitudes
    value = 2.0 * abs(a00 * a11 - a01 * a10)
    if value > 1.0 and value < 1.0 + 1e-12:
        value = 1.0
    return value


def _wrap_pi(x: float) -> float:
    y = (x + math.pi) % (2.0 * math.pi) - math.pi
    return 0.0 if y == -0.0 else y


def _matrix(j: complex) -> list[list[complex]]:
    zero = 0.0 + 0.0j
    return [
        [zero, zero, zero, zero],
        [zero, zero, j, zero],
        [zero, j.conjugate(), zero, zero],
        [zero, zero, zero, zero],
    ]


def _encode_matrix(matrix: Sequence[Sequence[complex]]) -> list[list[dict[str, str]]]:
    return [[_encode_complex(z) for z in row] for row in matrix]


def _decode_matrix(encoded: Any) -> list[list[complex]]:
    if not isinstance(encoded, list) or len(encoded) != 4:
        raise HermitianOrientedExchangeError("Hamiltonian matrix must be 4x4")
    matrix: list[list[complex]] = []
    for i, row in enumerate(encoded):
        if not isinstance(row, list) or len(row) != 4:
            raise HermitianOrientedExchangeError("Hamiltonian matrix must be 4x4")
        matrix.append([_decode_complex(value, f"H[{i},{j}]") for j, value in enumerate(row)])
    return matrix


def _assert_hermitian(matrix: Sequence[Sequence[complex]], tol: float = 1e-15) -> None:
    for i in range(4):
        for j in range(4):
            if abs(matrix[i][j] - matrix[j][i].conjugate()) > tol:
                raise HermitianOrientedExchangeError("Hamiltonian matrix Hermiticity mismatch")


def build_hermitian_oriented_exchange_v14(
    *,
    oriented: Mapping[str, Any],
    energy: Mapping[str, Any],
    path: Mapping[str, Any],
    partition: Mapping[str, Any],
) -> dict[str, Any]:
    validate_oriented_relational_coupling_v13(oriented, energy=energy, path=path, partition=partition)
    j_re = _from_hex(oriented["oriented_coupling_real_j_f64_hex"], "J_real")
    j_im = _from_hex(oriented["oriented_coupling_imag_j_f64_hex"], "J_imag")
    j = complex(j_re, j_im)
    magnitude = abs(j)
    source_magnitude = abs(_from_hex(partition["source_energy_j_f64_hex"], "source_energy"))
    tolerance = max(source_magnitude * 1e-14, 1e-300)
    if not math.isclose(magnitude, source_magnitude, rel_tol=1e-14, abs_tol=tolerance):
        raise HermitianOrientedExchangeError("oriented exchange magnitude/source-energy mismatch")

    matrix = _matrix(j)
    _assert_hermitian(matrix)
    phase = 0.0 if magnitude == 0.0 else math.atan2(j.imag, j.real)

    core = {
        "schema": HAMILTONIAN_SCHEMA,
        "basis_order": list(BASIS),
        "oriented_relational_coupling_commitment": str(oriented["oriented_relational_coupling_commitment"]),
        "relation_id": str(oriented["relation_id"]),
        "spacetime_point_id": str(oriented["spacetime_point_id"]),
        "tau_holonomy_rad_f64_hex": str(oriented["tau_holonomy_rad_f64_hex"]),
        "J_real_j_f64_hex": j_re.hex(),
        "J_imag_j_f64_hex": j_im.hex(),
        "J_magnitude_j_f64_hex": magnitude.hex(),
        "J_phase_rad_f64_hex": phase.hex(),
        "hamiltonian_matrix_j": _encode_matrix(matrix),
        "exchange_law": "H_ex=J_complex*|01><10|+conj(J_complex)*|10><01|",
        "pauli_law": "H_ex=Re(J)/2*(XX+YY)+Im(J)/2*(XY-YX)",
        "single_excitation_eigenvalues_j_f64_hex": [(-magnitude).hex(), magnitude.hex()],
        "zero_eigenvalue_multiplicity": 2,
        "spectral_radius_j_f64_hex": magnitude.hex(),
        "hermitian_by_construction": True,
        "excitation_number_preserving": True,
        "parameter_free_given_oriented_coupling": True,
        "orientation_quadrature_embedded": True,
        "operator_family": "ORIENTED_COMPLEX_EXCHANGE_CANDIDATE",
        "physical_target_attribution": "OPEN",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "HERMITIAN_ORIENTED_EXCHANGE_BOUND",
    }
    return {**core, "hermitian_oriented_exchange_commitment": _seal(HAMILTONIAN_DOMAIN, core)}


def validate_hermitian_oriented_exchange_v14(
    receipt: Mapping[str, Any],
    *,
    oriented: Mapping[str, Any],
    energy: Mapping[str, Any],
    path: Mapping[str, Any],
    partition: Mapping[str, Any],
) -> bool:
    expected = build_hermitian_oriented_exchange_v14(
        oriented=oriented,
        energy=energy,
        path=path,
        partition=partition,
    )
    if receipt.get("schema") != HAMILTONIAN_SCHEMA:
        raise HermitianOrientedExchangeError("unsupported oriented exchange schema")
    matrix = _decode_matrix(receipt.get("hamiltonian_matrix_j"))
    _assert_hermitian(matrix)
    for key, value in expected.items():
        if key == "hermitian_oriented_exchange_commitment":
            continue
        if receipt.get(key) != value:
            raise HermitianOrientedExchangeError(f"oriented exchange mismatch: {key}")
    supplied = _hash64(
        receipt.get("hermitian_oriented_exchange_commitment"),
        "hermitian_oriented_exchange_commitment",
    )
    core = dict(receipt)
    core.pop("hermitian_oriented_exchange_commitment", None)
    if supplied != _seal(HAMILTONIAN_DOMAIN, core):
        raise HermitianOrientedExchangeError("oriented exchange commitment mismatch")
    return True


def build_oriented_exchange_evolution_v14(
    *,
    qhtri_receipt: Mapping[str, Any],
    initial_state: Mapping[str, Any],
    hamiltonian: Mapping[str, Any],
    oriented: Mapping[str, Any],
    energy: Mapping[str, Any],
    path: Mapping[str, Any],
    partition: Mapping[str, Any],
    duration_s: Any,
    witness_tolerance: Any = 1e-12,
) -> dict[str, Any]:
    validate_qhtri_connection_derived_lag_v09(qhtri_receipt)
    validate_joint_pure_state_v10(initial_state)
    validate_hermitian_oriented_exchange_v14(
        hamiltonian,
        oriented=oriented,
        energy=energy,
        path=path,
        partition=partition,
    )
    if str(initial_state["qhtri_connection_derived_commitment"]) != str(qhtri_receipt["qhtri_connection_derived_commitment"]):
        raise HermitianOrientedExchangeError("initial-state/QHTRI lineage mismatch")
    if str(qhtri_receipt["qhtri_holonomy_lag_v08"]["relation_id"]) != str(hamiltonian["relation_id"]):
        raise HermitianOrientedExchangeError("QHTRI/Hamiltonian relation lineage mismatch")

    dt = _nonnegative(duration_s, "duration_s")
    tol = _nonnegative(witness_tolerance, "witness_tolerance")
    j = complex(
        _from_hex(hamiltonian["J_real_j_f64_hex"], "J_real"),
        _from_hex(hamiltonian["J_imag_j_f64_hex"], "J_imag"),
    )
    magnitude = abs(j)
    initial = _decode_amplitudes(initial_state["amplitudes"])
    final = list(initial)
    if magnitude == 0.0:
        phi = 0.0
        transfer_phase = 0.0
    else:
        phi = magnitude * dt / HBAR_SI
        if not math.isfinite(phi):
            raise HermitianOrientedExchangeError("exchange evolution phase must be finite")
        c = math.cos(phi)
        s = math.sin(phi)
        unit_j = j / magnitude
        a01 = initial[1]
        a10 = initial[2]
        final[1] = c * a01 - 1j * s * unit_j * a10
        final[2] = c * a10 - 1j * s * unit_j.conjugate() * a01
        transfer_phase = _wrap_pi(cmath.phase(-1j * unit_j))

    initial_norm = math.fsum(abs(z) ** 2 for z in initial)
    final_norm = math.fsum(abs(z) ** 2 for z in final)
    if abs(final_norm - initial_norm) > 1e-12:
        raise HermitianOrientedExchangeError("unitary norm closure failed")
    initial_c = _concurrence(initial)
    final_c = _concurrence(final)
    generated = initial_c <= tol and final_c > tol

    p00_i, p01_i, p10_i, p11_i = [abs(z) ** 2 for z in initial]
    p00_f, p01_f, p10_f, p11_f = [abs(z) ** 2 for z in final]
    excitation_i = p01_i + p10_i + 2.0 * p11_i
    excitation_f = p01_f + p10_f + 2.0 * p11_f

    core = {
        "schema": EVOLUTION_SCHEMA,
        "initial_joint_state_commitment": str(initial_state["joint_state_commitment"]),
        "qhtri_connection_derived_commitment": str(qhtri_receipt["qhtri_connection_derived_commitment"]),
        "hermitian_oriented_exchange_commitment": str(hamiltonian["hermitian_oriented_exchange_commitment"]),
        "oriented_relational_coupling_commitment": str(oriented["oriented_relational_coupling_commitment"]),
        "duration_s_f64_hex": dt.hex(),
        "exchange_phase_absJ_dt_over_hbar_f64_hex": phi.hex(),
        "transfer_phase_rad_f64_hex": transfer_phase.hex(),
        "unitary_law": "U_ex=exp(-i*H_ex*dt/hbar)",
        "single_excitation_update_law": "[a01',a10']=[c*a01-i*s*(J/|J|)*a10,c*a10-i*s*conj(J/|J|)*a01]",
        "final_amplitudes": [_encode_complex(z) for z in final],
        "initial_norm2_f64_hex": initial_norm.hex(),
        "final_norm2_f64_hex": final_norm.hex(),
        "initial_concurrence_f64_hex": initial_c.hex(),
        "final_concurrence_f64_hex": final_c.hex(),
        "witness_tolerance_f64_hex": tol.hex(),
        "entanglement_generated": generated,
        "generation_status": "ENTANGLEMENT_GENERATED_BY_ORIENTED_EXCHANGE_WITHIN_MODEL" if generated else "NO_NEW_ENTANGLEMENT_WITNESSED_WITHIN_MODEL",
        "initial_excitation_expectation_f64_hex": excitation_i.hex(),
        "final_excitation_expectation_f64_hex": excitation_f.hex(),
        "excitation_expectation_conserved": math.isclose(excitation_i, excitation_f, rel_tol=1e-13, abs_tol=1e-13),
        "population_dynamics_orientation_blind": True,
        "transfer_phase_orientation_sensitive": True,
        "physical_target_attribution": "OPEN",
        "entanglement_attribution_scope": "DECLARED_ORIENTED_EXCHANGE_MODEL_ONLY",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "HERMITIAN_ORIENTED_EXCHANGE_EVOLUTION_ASSESSED",
    }
    return {**core, "oriented_exchange_evolution_commitment": _seal(EVOLUTION_DOMAIN, core)}


def validate_oriented_exchange_evolution_v14(
    receipt: Mapping[str, Any],
    *,
    qhtri_receipt: Mapping[str, Any],
    initial_state: Mapping[str, Any],
    hamiltonian: Mapping[str, Any],
    oriented: Mapping[str, Any],
    energy: Mapping[str, Any],
    path: Mapping[str, Any],
    partition: Mapping[str, Any],
) -> bool:
    expected = build_oriented_exchange_evolution_v14(
        qhtri_receipt=qhtri_receipt,
        initial_state=initial_state,
        hamiltonian=hamiltonian,
        oriented=oriented,
        energy=energy,
        path=path,
        partition=partition,
        duration_s=_from_hex(receipt.get("duration_s_f64_hex"), "duration_s"),
        witness_tolerance=_from_hex(receipt.get("witness_tolerance_f64_hex"), "witness_tolerance"),
    )
    if receipt.get("schema") != EVOLUTION_SCHEMA:
        raise HermitianOrientedExchangeError("unsupported oriented exchange evolution schema")
    for key, value in expected.items():
        if key == "oriented_exchange_evolution_commitment":
            continue
        if receipt.get(key) != value:
            raise HermitianOrientedExchangeError(f"oriented exchange evolution mismatch: {key}")
    supplied = _hash64(
        receipt.get("oriented_exchange_evolution_commitment"),
        "oriented_exchange_evolution_commitment",
    )
    core = dict(receipt)
    core.pop("oriented_exchange_evolution_commitment", None)
    if supplied != _seal(EVOLUTION_DOMAIN, core):
        raise HermitianOrientedExchangeError("oriented exchange evolution commitment mismatch")
    return True
