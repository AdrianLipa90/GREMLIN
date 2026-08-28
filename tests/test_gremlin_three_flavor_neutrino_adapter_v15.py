from __future__ import annotations

import math

from tools.gremlin_three_flavor_neutrino_adapter_v15 import (
    ADAPTER_SCHEMA,
    build_three_flavor_neutrino_propagation_v15,
    pmns_matrix_v15,
    flavor_cycle_phase_v15,
    rephase_flavor_hamiltonian_v15,
)


def _enc(z: complex) -> dict[str, str]:
    return {"re_f64_hex": float(z.real).hex(), "im_f64_hex": float(z.imag).hex()}


def _mat(a):
    return [[_enc(complex(v)) for v in row] for row in a]


def _minimal_adapter():
    j = 1.0e-21
    h = [
        [0.0, j, 0.25j * j],
        [j, 0.0, 0.7 * j],
        [-0.25j * j, 0.7 * j, 0.0],
    ]
    return {
        "schema": ADAPTER_SCHEMA,
        "three_flavor_neutrino_hamiltonian_commitment": "0" * 64,
        "H_standard_j": _mat(h),
        "H_total_j": _mat(h),
    }


def test_pmns_matrix_is_unitary():
    u = pmns_matrix_v15(math.radians(33.41), math.radians(8.54), math.radians(42.2), math.radians(246.0))
    for i in range(3):
        for j in range(3):
            inner = sum(u[k][i].conjugate() * u[k][j] for k in range(3))
            target = 1.0 if i == j else 0.0
            assert abs(inner - target) < 5e-15


def test_propagation_zero_baseline_is_identity():
    p = build_three_flavor_neutrino_propagation_v15(adapter=_minimal_adapter(), baseline_m=0.0)
    for beta in range(3):
        for alpha in range(3):
            actual = float.fromhex(p["P_standard"][beta][alpha])
            assert abs(actual - (1.0 if beta == alpha else 0.0)) < 1e-15
    assert float.fromhex(p["standard_probability_conservation_residual_f64_hex"]) < 1e-14


def test_propagation_is_unitary_and_probability_conserving():
    p = build_three_flavor_neutrino_propagation_v15(adapter=_minimal_adapter(), baseline_m=1.0e-5)
    assert float.fromhex(p["standard_unitarity_residual_f64_hex"]) < 2e-11
    assert float.fromhex(p["standard_probability_conservation_residual_f64_hex"]) < 2e-11


def test_cycle_phase_is_rephasing_invariant():
    h = [
        [0.0j, 1.0 + 0.2j, 0.4 - 0.1j],
        [1.0 - 0.2j, 0.0j, 0.7 + 0.3j],
        [0.4 + 0.1j, 0.7 - 0.3j, 0.0j],
    ]
    base = flavor_cycle_phase_v15(h)
    transformed = rephase_flavor_hamiltonian_v15(h, [0.31, -0.77, 1.19])
    shifted = flavor_cycle_phase_v15(transformed)
    assert base["status"] == shifted["status"] == "DEFINED"
    assert abs(base["phase_rad"] - shifted["phase_rad"]) < 2e-15
