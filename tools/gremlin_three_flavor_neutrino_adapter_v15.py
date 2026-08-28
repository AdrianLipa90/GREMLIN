from __future__ import annotations

import cmath
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from tools.gremlin_connection_path_holonomy_v09 import validate_qhtri_connection_derived_lag_v09
from tools.gremlin_hermitian_oriented_exchange_v14 import validate_hermitian_oriented_exchange_v14

EV_J = 1.602_176_634e-19
HBAR_SI = 1.054_571_817e-34
C_SI = 299_792_458.0
FLAVORS = ("e", "mu", "tau")

ADAPTER_SCHEMA = "GREMLIN_THREE_FLAVOR_NEUTRINO_HAMILTONIAN_V1_5"
ADAPTER_DOMAIN = b"GREMLIN-THREE-FLAVOR-NEUTRINO-HAMILTONIAN/v1.5\x00"
PROPAGATION_SCHEMA = "GREMLIN_THREE_FLAVOR_NEUTRINO_PROPAGATION_V1_5"
PROPAGATION_DOMAIN = b"GREMLIN-THREE-FLAVOR-NEUTRINO-PROPAGATION/v1.5\x00"


class ThreeFlavorNeutrinoAdapterError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(domain: bytes, value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    text = str(value)
    if not text:
        raise ThreeFlavorNeutrinoAdapterError(f"{name} must be non-empty")
    return text


def _hash64(value: Any, name: str) -> str:
    text = _nonempty(value, name)
    if len(text) != 64:
        raise ThreeFlavorNeutrinoAdapterError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise ThreeFlavorNeutrinoAdapterError(f"{name} must be hexadecimal") from exc
    return text


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise ThreeFlavorNeutrinoAdapterError(f"{name} must be finite")
    return x


def _positive(value: Any, name: str) -> float:
    x = _finite(value, name)
    if x <= 0.0:
        raise ThreeFlavorNeutrinoAdapterError(f"{name} must be positive")
    return x


def _nonnegative(value: Any, name: str) -> float:
    x = _finite(value, name)
    if x < 0.0:
        raise ThreeFlavorNeutrinoAdapterError(f"{name} must be non-negative")
    return x


def _from_hex(value: Any, name: str) -> float:
    try:
        return _finite(float.fromhex(str(value)), name)
    except ValueError as exc:
        raise ThreeFlavorNeutrinoAdapterError(f"{name} must be a binary64 hex float") from exc


def _encode_complex(z: complex) -> dict[str, str]:
    return {"re_f64_hex": float(z.real).hex(), "im_f64_hex": float(z.imag).hex()}


def _decode_complex(value: Mapping[str, Any], name: str) -> complex:
    if not isinstance(value, Mapping):
        raise ThreeFlavorNeutrinoAdapterError(f"{name} must be a complex encoding")
    try:
        re = float.fromhex(str(value.get("re_f64_hex")))
        im = float.fromhex(str(value.get("im_f64_hex")))
    except (TypeError, ValueError) as exc:
        raise ThreeFlavorNeutrinoAdapterError(f"{name} complex encoding malformed") from exc
    if not math.isfinite(re) or not math.isfinite(im):
        raise ThreeFlavorNeutrinoAdapterError(f"{name} must be finite")
    return complex(re, im)


def _zeros(n: int = 3) -> list[list[complex]]:
    return [[0.0j for _ in range(n)] for _ in range(n)]


def _identity(n: int = 3) -> list[list[complex]]:
    out = _zeros(n)
    for i in range(n):
        out[i][i] = 1.0 + 0.0j
    return out


def _dagger(a: Sequence[Sequence[complex]]) -> list[list[complex]]:
    n = len(a)
    return [[complex(a[j][i]).conjugate() for j in range(n)] for i in range(n)]


def _matmul(a: Sequence[Sequence[complex]], b: Sequence[Sequence[complex]]) -> list[list[complex]]:
    n = len(a)
    out = _zeros(n)
    for i in range(n):
        for j in range(n):
            out[i][j] = sum((a[i][k] * b[k][j] for k in range(n)), 0.0j)
    return out


def _matadd(a: Sequence[Sequence[complex]], b: Sequence[Sequence[complex]]) -> list[list[complex]]:
    return [[a[i][j] + b[i][j] for j in range(len(a))] for i in range(len(a))]


def _matsub(a: Sequence[Sequence[complex]], b: Sequence[Sequence[complex]]) -> list[list[complex]]:
    return [[a[i][j] - b[i][j] for j in range(len(a))] for i in range(len(a))]


def _matscale(a: Sequence[Sequence[complex]], scalar: complex) -> list[list[complex]]:
    return [[scalar * a[i][j] for j in range(len(a))] for i in range(len(a))]


def _trace(a: Sequence[Sequence[complex]]) -> complex:
    return sum((a[i][i] for i in range(len(a))), 0.0j)


def _matrix_norm_inf(a: Sequence[Sequence[complex]]) -> float:
    return max(sum(abs(z) for z in row) for row in a)


def _max_abs_matrix(a: Sequence[Sequence[complex]]) -> float:
    return max(abs(z) for row in a for z in row)


def _assert_square3(a: Sequence[Sequence[complex]], name: str) -> None:
    if len(a) != 3 or any(len(row) != 3 for row in a):
        raise ThreeFlavorNeutrinoAdapterError(f"{name} must be 3x3")


def _assert_hermitian(a: Sequence[Sequence[complex]], name: str, tol: float = 1e-24) -> None:
    _assert_square3(a, name)
    scale = max(_max_abs_matrix(a), 1e-300)
    threshold = max(tol, scale * 1e-13)
    for i in range(3):
        for j in range(3):
            if abs(a[i][j] - a[j][i].conjugate()) > threshold:
                raise ThreeFlavorNeutrinoAdapterError(f"{name} Hermiticity mismatch at ({i},{j})")


def _unitarity_residual(u: Sequence[Sequence[complex]]) -> float:
    product = _matmul(_dagger(u), u)
    return _max_abs_matrix(_matsub(product, _identity(3)))


def _encode_matrix(a: Sequence[Sequence[complex]]) -> list[list[dict[str, str]]]:
    return [[_encode_complex(z) for z in row] for row in a]


def _decode_matrix(value: Any, name: str) -> list[list[complex]]:
    if not isinstance(value, list) or len(value) != 3:
        raise ThreeFlavorNeutrinoAdapterError(f"{name} must be encoded 3x3 matrix")
    matrix: list[list[complex]] = []
    for i, row in enumerate(value):
        if not isinstance(row, list) or len(row) != 3:
            raise ThreeFlavorNeutrinoAdapterError(f"{name} must be encoded 3x3 matrix")
        matrix.append([_decode_complex(z, f"{name}[{i},{j}]") for j, z in enumerate(row)])
    return matrix


def _wrap_pi(x: float) -> float:
    y = (x + math.pi) % (2.0 * math.pi) - math.pi
    return 0.0 if y == -0.0 else y


def pmns_matrix_v15(theta12_rad: Any, theta13_rad: Any, theta23_rad: Any, delta_cp_rad: Any) -> list[list[complex]]:
    t12 = _finite(theta12_rad, "theta12_rad")
    t13 = _finite(theta13_rad, "theta13_rad")
    t23 = _finite(theta23_rad, "theta23_rad")
    delta = _finite(delta_cp_rad, "delta_cp_rad")
    for theta, name in ((t12, "theta12_rad"), (t13, "theta13_rad"), (t23, "theta23_rad")):
        if theta < 0.0 or theta > math.pi / 2.0:
            raise ThreeFlavorNeutrinoAdapterError(f"{name} must lie in [0,pi/2]")
    c12, s12 = math.cos(t12), math.sin(t12)
    c13, s13 = math.cos(t13), math.sin(t13)
    c23, s23 = math.cos(t23), math.sin(t23)
    eid = cmath.exp(1j * delta)
    emid = eid.conjugate()
    u = [
        [c12 * c13, s12 * c13, s13 * emid],
        [
            -s12 * c23 - c12 * s13 * s23 * eid,
            c12 * c23 - s12 * s13 * s23 * eid,
            c13 * s23,
        ],
        [
            s12 * s23 - c12 * s13 * c23 * eid,
            -c12 * s23 - s12 * s13 * c23 * eid,
            c13 * c23,
        ],
    ]
    residual = _unitarity_residual(u)
    if residual > 5e-15:
        raise ThreeFlavorNeutrinoAdapterError(f"PMNS unitarity residual too large: {residual}")
    return u


def _vacuum_hamiltonian_j(
    *,
    pmns: Sequence[Sequence[complex]],
    neutrino_energy_eV: float,
    delta_m21_sq_eV2: float,
    delta_m31_sq_eV2: float,
) -> list[list[complex]]:
    diagonal_eV = [0.0, delta_m21_sq_eV2 / (2.0 * neutrino_energy_eV), delta_m31_sq_eV2 / (2.0 * neutrino_energy_eV)]
    d = _zeros(3)
    for i, value in enumerate(diagonal_eV):
        d[i][i] = complex(value * EV_J, 0.0)
    return _matmul(_matmul(pmns, d), _dagger(pmns))


def _matter_hamiltonian_j(electron_matter_potential_eV: float) -> list[list[complex]]:
    out = _zeros(3)
    out[0][0] = complex(electron_matter_potential_eV * EV_J, 0.0)
    return out


def _rf_hamiltonian_j(j: complex, edge: tuple[str, str]) -> list[list[complex]]:
    a, b = edge
    if a not in FLAVORS or b not in FLAVORS or a == b:
        raise ThreeFlavorNeutrinoAdapterError("rf_edge must contain two distinct flavor labels")
    i, k = FLAVORS.index(a), FLAVORS.index(b)
    out = _zeros(3)
    out[i][k] = j
    out[k][i] = j.conjugate()
    return out


def flavor_cycle_phase_v15(matrix: Sequence[Sequence[complex]], zero_tolerance: float = 1e-300) -> dict[str, Any]:
    _assert_square3(matrix, "flavor Hamiltonian")
    product = matrix[0][1] * matrix[1][2] * matrix[2][0]
    magnitude = abs(product)
    if magnitude <= zero_tolerance:
        return {
            "status": "UNRESOLVED_ZERO_LOOP_PRODUCT",
            "product": product,
            "magnitude": magnitude,
            "phase_rad": None,
        }
    return {
        "status": "DEFINED",
        "product": product,
        "magnitude": magnitude,
        "phase_rad": _wrap_pi(cmath.phase(product)),
    }


def rephase_flavor_hamiltonian_v15(matrix: Sequence[Sequence[complex]], phases_rad: Sequence[Any]) -> list[list[complex]]:
    _assert_square3(matrix, "flavor Hamiltonian")
    if len(phases_rad) != 3:
        raise ThreeFlavorNeutrinoAdapterError("three flavor rephasing angles are required")
    phases = [_finite(v, f"phase[{i}]") for i, v in enumerate(phases_rad)]
    # |nu_alpha>' = exp(i phi_alpha)|nu_alpha>, hence H' = D^dagger H D.
    d = _zeros(3)
    for i, phase in enumerate(phases):
        d[i][i] = cmath.exp(1j * phase)
    return _matmul(_matmul(_dagger(d), matrix), d)


def _traceless(a: Sequence[Sequence[complex]]) -> tuple[list[list[complex]], complex]:
    common = _trace(a) / 3.0
    out = [[a[i][j] for j in range(3)] for i in range(3)]
    for i in range(3):
        out[i][i] -= common
    return out, common


def _matrix_exponential(a: Sequence[Sequence[complex]]) -> tuple[list[list[complex]], int, int]:
    _assert_square3(a, "matrix exponential input")
    norm = _matrix_norm_inf(a)
    if not math.isfinite(norm):
        raise ThreeFlavorNeutrinoAdapterError("matrix exponential norm must be finite")
    if norm == 0.0:
        return _identity(3), 0, 0
    scaling = max(0, int(math.ceil(math.log2(norm / 0.5)))) if norm > 0.5 else 0
    if scaling > 256:
        raise ThreeFlavorNeutrinoAdapterError("matrix exponential scaling depth exceeds 256")
    b = _matscale(a, 1.0 / (2.0 ** scaling))
    result = _identity(3)
    term = _identity(3)
    iterations = 0
    for k in range(1, 129):
        term = _matscale(_matmul(term, b), 1.0 / k)
        result = _matadd(result, term)
        iterations = k
        if _matrix_norm_inf(term) < 2e-16:
            break
    else:
        raise ThreeFlavorNeutrinoAdapterError("matrix exponential Taylor series did not converge")
    for _ in range(scaling):
        result = _matmul(result, result)
    return result, scaling, iterations


def _probability_matrix(unitary: Sequence[Sequence[complex]]) -> list[list[float]]:
    # Rows are final flavor beta, columns are initial flavor alpha.
    return [[abs(unitary[beta][alpha]) ** 2 for alpha in range(3)] for beta in range(3)]


def _probability_conservation_residual(probabilities: Sequence[Sequence[float]]) -> float:
    column_residual = max(abs(sum(probabilities[beta][alpha] for beta in range(3)) - 1.0) for alpha in range(3))
    row_residual = max(abs(sum(probabilities[beta][alpha] for alpha in range(3)) - 1.0) for beta in range(3))
    return max(column_residual, row_residual)


def _encode_probability_matrix(p: Sequence[Sequence[float]]) -> list[list[str]]:
    return [[float(v).hex() for v in row] for row in p]


def _decode_probability_matrix(value: Any, name: str) -> list[list[float]]:
    if not isinstance(value, list) or len(value) != 3 or any(not isinstance(row, list) or len(row) != 3 for row in value):
        raise ThreeFlavorNeutrinoAdapterError(f"{name} must be encoded 3x3 probability matrix")
    return [[_from_hex(value[i][j], f"{name}[{i},{j}]") for j in range(3)] for i in range(3)]


def build_three_flavor_neutrino_hamiltonian_v15(
    *,
    qhtri_receipt: Mapping[str, Any],
    hamiltonian_v14: Mapping[str, Any],
    oriented: Mapping[str, Any],
    energy: Mapping[str, Any],
    path: Mapping[str, Any],
    partition: Mapping[str, Any],
    theta12_rad: Any,
    theta13_rad: Any,
    theta23_rad: Any,
    delta_cp_rad: Any,
    delta_m21_sq_eV2: Any,
    delta_m31_sq_eV2: Any,
    neutrino_energy_eV: Any,
    electron_matter_potential_eV: Any,
    rf_edge: Sequence[str],
    standard_model_source_ref: str,
    standard_model_source_commitment: str,
    epistemic_status: str,
) -> dict[str, Any]:
    validate_qhtri_connection_derived_lag_v09(qhtri_receipt)
    validate_hermitian_oriented_exchange_v14(
        hamiltonian_v14,
        oriented=oriented,
        energy=energy,
        path=path,
        partition=partition,
    )
    if str(qhtri_receipt["qhtri_holonomy_lag_v08"]["relation_id"]) != str(hamiltonian_v14["relation_id"]):
        raise ThreeFlavorNeutrinoAdapterError("QHTRI/RF Hamiltonian relation lineage mismatch")
    if str(qhtri_receipt["qhtri_holonomy_lag_v08"]["loop_id"]) != str(path["loop_id"]):
        raise ThreeFlavorNeutrinoAdapterError("QHTRI/connection loop lineage mismatch")

    t12 = _finite(theta12_rad, "theta12_rad")
    t13 = _finite(theta13_rad, "theta13_rad")
    t23 = _finite(theta23_rad, "theta23_rad")
    delta = _finite(delta_cp_rad, "delta_cp_rad")
    dm21 = _finite(delta_m21_sq_eV2, "delta_m21_sq_eV2")
    dm31 = _finite(delta_m31_sq_eV2, "delta_m31_sq_eV2")
    enu = _positive(neutrino_energy_eV, "neutrino_energy_eV")
    ve = _finite(electron_matter_potential_eV, "electron_matter_potential_eV")
    if len(rf_edge) != 2:
        raise ThreeFlavorNeutrinoAdapterError("rf_edge must contain two flavor labels")
    edge = (str(rf_edge[0]), str(rf_edge[1]))

    pmns = pmns_matrix_v15(t12, t13, t23, delta)
    h_vac = _vacuum_hamiltonian_j(pmns=pmns, neutrino_energy_eV=enu, delta_m21_sq_eV2=dm21, delta_m31_sq_eV2=dm31)
    h_mat = _matter_hamiltonian_j(ve)
    h_std = _matadd(h_vac, h_mat)
    j = complex(
        _from_hex(hamiltonian_v14["J_real_j_f64_hex"], "J_real"),
        _from_hex(hamiltonian_v14["J_imag_j_f64_hex"], "J_imag"),
    )
    h_rf = _rf_hamiltonian_j(j, edge)
    h_total = _matadd(h_std, h_rf)
    for matrix, name in ((h_vac, "H_vac"), (h_mat, "H_matter"), (h_std, "H_std"), (h_rf, "H_RF"), (h_total, "H_total")):
        _assert_hermitian(matrix, name)

    standard_cycle = flavor_cycle_phase_v15(h_std)
    total_cycle = flavor_cycle_phase_v15(h_total)
    if standard_cycle["phase_rad"] is None or total_cycle["phase_rad"] is None:
        cycle_shift = None
        cycle_shift_status = "UNRESOLVED_ZERO_LOOP_PRODUCT"
    else:
        cycle_shift = _wrap_pi(float(total_cycle["phase_rad"]) - float(standard_cycle["phase_rad"]))
        cycle_shift_status = "DEFINED"

    trace_std = _trace(h_std)
    trace_total = _trace(h_total)
    trace_delta = trace_total - trace_std

    core = {
        "schema": ADAPTER_SCHEMA,
        "flavor_basis_order": list(FLAVORS),
        "particle_sector": "NEUTRINO",
        "standard_hamiltonian_basis": "FLAVOR",
        "standard_hamiltonian_law": "H_std=U*diag(0,dm21^2,dm31^2)/(2E)*U^dagger+diag(V_e,0,0)",
        "mass_phase_gauge": "m1_squared_subtracted_global_phase",
        "pmns_convention": "PDG_STANDARD_DIRAC_OSCILLATION_CONVENTION",
        "theta12_rad_f64_hex": t12.hex(),
        "theta13_rad_f64_hex": t13.hex(),
        "theta23_rad_f64_hex": t23.hex(),
        "delta_cp_rad_f64_hex": delta.hex(),
        "delta_m21_sq_eV2_f64_hex": dm21.hex(),
        "delta_m31_sq_eV2_f64_hex": dm31.hex(),
        "neutrino_energy_eV_f64_hex": enu.hex(),
        "electron_matter_potential_eV_f64_hex": ve.hex(),
        "matter_potential_convention": "V_e=sqrt(2)*G_F*n_e; common neutral-current identity removed",
        "pmns_matrix": _encode_matrix(pmns),
        "pmns_unitarity_residual_f64_hex": _unitarity_residual(pmns).hex(),
        "H_vacuum_j": _encode_matrix(h_vac),
        "H_matter_j": _encode_matrix(h_mat),
        "H_standard_j": _encode_matrix(h_std),
        "rf_edge": list(edge),
        "rf_edge_attribution": "EXPLICIT_TEST_ADAPTER_SELECTION",
        "rf_edge_physical_attribution": "OPEN",
        "hermitian_oriented_exchange_commitment": str(hamiltonian_v14["hermitian_oriented_exchange_commitment"]),
        "oriented_relational_coupling_commitment": str(oriented["oriented_relational_coupling_commitment"]),
        "qhtri_connection_derived_commitment": str(qhtri_receipt["qhtri_connection_derived_commitment"]),
        "H_RF_j": _encode_matrix(h_rf),
        "H_total_j": _encode_matrix(h_total),
        "total_hamiltonian_law": "H_total=H_vacuum+H_matter+H_RF",
        "rf_zero_limit_contract": "H_RF=0 implies H_total=H_standard exactly",
        "standard_trace_j": _encode_complex(trace_std),
        "total_trace_j": _encode_complex(trace_total),
        "rf_trace_delta_j": _encode_complex(trace_delta),
        "rf_trace_free": abs(trace_delta) <= max(_max_abs_matrix(h_total) * 1e-14, 1e-300),
        "standard_cycle_phase_status": str(standard_cycle["status"]),
        "standard_cycle_product_j3": _encode_complex(complex(standard_cycle["product"])),
        "standard_cycle_phase_rad_f64_hex": None if standard_cycle["phase_rad"] is None else float(standard_cycle["phase_rad"]).hex(),
        "total_cycle_phase_status": str(total_cycle["status"]),
        "total_cycle_product_j3": _encode_complex(complex(total_cycle["product"])),
        "total_cycle_phase_rad_f64_hex": None if total_cycle["phase_rad"] is None else float(total_cycle["phase_rad"]).hex(),
        "relational_cycle_phase_shift_status": cycle_shift_status,
        "relational_cycle_phase_shift_rad_f64_hex": None if cycle_shift is None else cycle_shift.hex(),
        "cycle_phase_law": "Phi_3=arg(H_e_mu*H_mu_tau*H_tau_e), invariant under local flavor rephasing",
        "standard_model_source_ref": _nonempty(standard_model_source_ref, "standard_model_source_ref"),
        "standard_model_source_commitment": _hash64(standard_model_source_commitment, "standard_model_source_commitment"),
        "epistemic_status": _nonempty(epistemic_status, "epistemic_status"),
        "antineutrino_extension_status": "OPEN_REQUIRES_RF_CP_TRANSFORMATION_RULE",
        "physical_neutrino_RF_attribution": "OPEN_REQUIRES_DATA_AND_TARGET_EDGE_BINDING",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "THREE_FLAVOR_NEUTRINO_HAMILTONIAN_BOUND",
    }
    return {**core, "three_flavor_neutrino_hamiltonian_commitment": _seal(ADAPTER_DOMAIN, core)}


def validate_three_flavor_neutrino_hamiltonian_v15(
    receipt: Mapping[str, Any],
    *,
    qhtri_receipt: Mapping[str, Any],
    hamiltonian_v14: Mapping[str, Any],
    oriented: Mapping[str, Any],
    energy: Mapping[str, Any],
    path: Mapping[str, Any],
    partition: Mapping[str, Any],
) -> bool:
    if receipt.get("schema") != ADAPTER_SCHEMA:
        raise ThreeFlavorNeutrinoAdapterError("unsupported three-flavor adapter schema")
    expected = build_three_flavor_neutrino_hamiltonian_v15(
        qhtri_receipt=qhtri_receipt,
        hamiltonian_v14=hamiltonian_v14,
        oriented=oriented,
        energy=energy,
        path=path,
        partition=partition,
        theta12_rad=_from_hex(receipt.get("theta12_rad_f64_hex"), "theta12_rad"),
        theta13_rad=_from_hex(receipt.get("theta13_rad_f64_hex"), "theta13_rad"),
        theta23_rad=_from_hex(receipt.get("theta23_rad_f64_hex"), "theta23_rad"),
        delta_cp_rad=_from_hex(receipt.get("delta_cp_rad_f64_hex"), "delta_cp_rad"),
        delta_m21_sq_eV2=_from_hex(receipt.get("delta_m21_sq_eV2_f64_hex"), "delta_m21_sq_eV2"),
        delta_m31_sq_eV2=_from_hex(receipt.get("delta_m31_sq_eV2_f64_hex"), "delta_m31_sq_eV2"),
        neutrino_energy_eV=_from_hex(receipt.get("neutrino_energy_eV_f64_hex"), "neutrino_energy_eV"),
        electron_matter_potential_eV=_from_hex(receipt.get("electron_matter_potential_eV_f64_hex"), "electron_matter_potential_eV"),
        rf_edge=receipt.get("rf_edge"),
        standard_model_source_ref=str(receipt.get("standard_model_source_ref")),
        standard_model_source_commitment=str(receipt.get("standard_model_source_commitment")),
        epistemic_status=str(receipt.get("epistemic_status")),
    )
    for key, value in expected.items():
        if key == "three_flavor_neutrino_hamiltonian_commitment":
            continue
        if receipt.get(key) != value:
            raise ThreeFlavorNeutrinoAdapterError(f"three-flavor adapter mismatch: {key}")
    supplied = _hash64(
        receipt.get("three_flavor_neutrino_hamiltonian_commitment"),
        "three_flavor_neutrino_hamiltonian_commitment",
    )
    core = dict(receipt)
    core.pop("three_flavor_neutrino_hamiltonian_commitment", None)
    if supplied != _seal(ADAPTER_DOMAIN, core):
        raise ThreeFlavorNeutrinoAdapterError("three-flavor adapter commitment mismatch")
    return True


def build_three_flavor_neutrino_propagation_v15(
    *,
    adapter: Mapping[str, Any],
    baseline_m: Any,
) -> dict[str, Any]:
    if adapter.get("schema") != ADAPTER_SCHEMA:
        raise ThreeFlavorNeutrinoAdapterError("unsupported three-flavor adapter schema")
    _hash64(adapter.get("three_flavor_neutrino_hamiltonian_commitment"), "three_flavor_neutrino_hamiltonian_commitment")
    baseline = _nonnegative(baseline_m, "baseline_m")
    h_std = _decode_matrix(adapter.get("H_standard_j"), "H_standard_j")
    h_total = _decode_matrix(adapter.get("H_total_j"), "H_total_j")
    _assert_hermitian(h_std, "H_standard_j")
    _assert_hermitian(h_total, "H_total_j")

    h_std_tl, common_std = _traceless(h_std)
    h_total_tl, common_total = _traceless(h_total)
    factor = -1j * baseline / (HBAR_SI * C_SI)
    u_std, scaling_std, iterations_std = _matrix_exponential(_matscale(h_std_tl, factor))
    u_total, scaling_total, iterations_total = _matrix_exponential(_matscale(h_total_tl, factor))

    unitary_std = _unitarity_residual(u_std)
    unitary_total = _unitarity_residual(u_total)
    if unitary_std > 2e-11 or unitary_total > 2e-11:
        raise ThreeFlavorNeutrinoAdapterError("propagator unitarity residual exceeds tolerance")

    p_std = _probability_matrix(u_std)
    p_total = _probability_matrix(u_total)
    p_residual = [[p_total[i][j] - p_std[i][j] for j in range(3)] for i in range(3)]
    conservation_std = _probability_conservation_residual(p_std)
    conservation_total = _probability_conservation_residual(p_total)

    core = {
        "schema": PROPAGATION_SCHEMA,
        "three_flavor_neutrino_hamiltonian_commitment": str(adapter["three_flavor_neutrino_hamiltonian_commitment"]),
        "flavor_basis_order": list(FLAVORS),
        "probability_matrix_orientation": "rows=final_flavor_beta; columns=initial_flavor_alpha",
        "baseline_m_f64_hex": baseline.hex(),
        "time_ultrarelativistic_s_f64_hex": (baseline / C_SI).hex(),
        "evolution_law": "U(L)=exp(-i*H*L/(hbar*c)); trace(H)/3 identity removed before exponentiation",
        "standard_common_phase_energy_j": _encode_complex(common_std),
        "total_common_phase_energy_j": _encode_complex(common_total),
        "U_standard": _encode_matrix(u_std),
        "U_total": _encode_matrix(u_total),
        "standard_unitarity_residual_f64_hex": unitary_std.hex(),
        "total_unitarity_residual_f64_hex": unitary_total.hex(),
        "standard_expm_scaling_steps": scaling_std,
        "total_expm_scaling_steps": scaling_total,
        "standard_expm_taylor_iterations": iterations_std,
        "total_expm_taylor_iterations": iterations_total,
        "P_standard": _encode_probability_matrix(p_std),
        "P_total": _encode_probability_matrix(p_total),
        "P_relational_residual": _encode_probability_matrix(p_residual),
        "standard_probability_conservation_residual_f64_hex": conservation_std.hex(),
        "total_probability_conservation_residual_f64_hex": conservation_total.hex(),
        "rf_zero_limit_interpretation": "P_total converges exactly to P_standard when H_RF is exactly zero",
        "physical_prediction_status": "MODEL_RESIDUAL_REQUIRES_PARAMETER_AND_GEOMETRY_WITNESS",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "THREE_FLAVOR_NEUTRINO_PROPAGATION_ASSESSED",
    }
    return {**core, "three_flavor_neutrino_propagation_commitment": _seal(PROPAGATION_DOMAIN, core)}


def validate_three_flavor_neutrino_propagation_v15(
    receipt: Mapping[str, Any],
    *,
    adapter: Mapping[str, Any],
) -> bool:
    if receipt.get("schema") != PROPAGATION_SCHEMA:
        raise ThreeFlavorNeutrinoAdapterError("unsupported three-flavor propagation schema")
    expected = build_three_flavor_neutrino_propagation_v15(
        adapter=adapter,
        baseline_m=_from_hex(receipt.get("baseline_m_f64_hex"), "baseline_m"),
    )
    for key, value in expected.items():
        if key == "three_flavor_neutrino_propagation_commitment":
            continue
        if receipt.get(key) != value:
            raise ThreeFlavorNeutrinoAdapterError(f"three-flavor propagation mismatch: {key}")
    supplied = _hash64(
        receipt.get("three_flavor_neutrino_propagation_commitment"),
        "three_flavor_neutrino_propagation_commitment",
    )
    core = dict(receipt)
    core.pop("three_flavor_neutrino_propagation_commitment", None)
    if supplied != _seal(PROPAGATION_DOMAIN, core):
        raise ThreeFlavorNeutrinoAdapterError("three-flavor propagation commitment mismatch")
    return True
