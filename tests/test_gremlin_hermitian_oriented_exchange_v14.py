from __future__ import annotations

import copy
import math

import pytest

from tools.gremlin_connection_path_holonomy_v09 import (
    build_connection_path_integral_v09,
    build_derived_geometry_holonomy_v09,
    build_qhtri_connection_derived_lag_v09,
)
from tools.gremlin_hermitian_oriented_exchange_v14 import (
    HermitianOrientedExchangeError,
    build_hermitian_oriented_exchange_v14,
    build_oriented_exchange_evolution_v14,
    validate_hermitian_oriented_exchange_v14,
    validate_oriented_exchange_evolution_v14,
)
from tools.gremlin_joint_quantum_witness_v10 import HBAR_SI, build_joint_pure_state_v10
from tools.gremlin_oriented_relational_coupling_v13 import build_oriented_relational_coupling_v13
from tools.gremlin_relational_coupling_energy_v11 import build_relational_coupling_energy_partition_v11
from tools.gremlin_relational_lambda_holonomy_v08 import (
    build_relational_lambda_energy_v08,
    build_relational_lambda_field_v08,
)

H = "a" * 64


def _decode_complex(value):
    return complex(float.fromhex(value["re_f64_hex"]), float.fromhex(value["im_f64_hex"]))


def _wrap_pi(x):
    y = (x + math.pi) % (2.0 * math.pi) - math.pi
    return 0.0 if y == -0.0 else y


def _stack(tau: float):
    field = build_relational_lambda_field_v08(
        relation_id="R:Lambda",
        spacetime_point_id="x:0",
        lambda_m2=1.1e-52,
        source_ref="source:model",
        source_commitment=H,
        epistemic_status="MODEL_CANDIDATE",
    )
    energy = build_relational_lambda_energy_v08(field=field, support_volume_m3=1.0)
    path = build_connection_path_integral_v09(
        energy=energy,
        geometry_adapter_id="adapter:test",
        metric_commitment="b" * 64,
        connection_commitment="c" * 64,
        loop_id="gamma:test",
        connection_projection_rad_per_m=[tau],
        segment_lengths_m=[1.0],
        source_ref="geometry:test",
        epistemic_status="MODEL_CANDIDATE",
    )
    derived = build_derived_geometry_holonomy_v09(energy=energy, path=path)
    qhtri = build_qhtri_connection_derived_lag_v09(
        derived_geometry=derived,
        oscillator_i="nu:i",
        oscillator_j="nu:j",
        n=1,
        m=1,
        theta_i_rad=0.0,
        theta_j_rad=0.0,
    )
    partition = build_relational_coupling_energy_partition_v11(energy=energy, path=path)
    oriented = build_oriented_relational_coupling_v13(energy=energy, path=path, partition=partition)
    hamiltonian = build_hermitian_oriented_exchange_v14(
        oriented=oriented,
        energy=energy,
        path=path,
        partition=partition,
    )
    assert validate_hermitian_oriented_exchange_v14(
        hamiltonian,
        oriented=oriented,
        energy=energy,
        path=path,
        partition=partition,
    )
    return energy, path, qhtri, partition, oriented, hamiltonian


def _evolve(tau: float, amplitudes, phase_fraction: float):
    energy, path, qhtri, partition, oriented, hamiltonian = _stack(tau)
    state = build_joint_pure_state_v10(
        qhtri_receipt=qhtri,
        amplitudes=amplitudes,
        source_ref="state:test",
        epistemic_status="MODEL_DIAGNOSTIC",
    )
    magnitude = float.fromhex(hamiltonian["J_magnitude_j_f64_hex"])
    duration = phase_fraction * math.pi * HBAR_SI / magnitude
    evolution = build_oriented_exchange_evolution_v14(
        qhtri_receipt=qhtri,
        initial_state=state,
        hamiltonian=hamiltonian,
        oriented=oriented,
        energy=energy,
        path=path,
        partition=partition,
        duration_s=duration,
    )
    assert validate_oriented_exchange_evolution_v14(
        evolution,
        qhtri_receipt=qhtri,
        initial_state=state,
        hamiltonian=hamiltonian,
        oriented=oriented,
        energy=energy,
        path=path,
        partition=partition,
    )
    return hamiltonian, evolution


def test_exchange_matrix_is_explicitly_hermitian():
    _, _, _, _, _, h = _stack(0.61)
    matrix = [[_decode_complex(z) for z in row] for row in h["hamiltonian_matrix_j"]]
    for i in range(4):
        for j in range(4):
            assert matrix[i][j] == pytest.approx(matrix[j][i].conjugate())
    assert h["hermitian_by_construction"] is True
    assert h["orientation_quadrature_embedded"] is True


def test_spectrum_is_zero_zero_plus_minus_source_magnitude():
    energy, _, _, _, _, h = _stack(0.9)
    source = abs(float.fromhex(energy["effective_source_energy_j_f64_hex"]))
    eigen = [float.fromhex(v) for v in h["single_excitation_eigenvalues_j_f64_hex"]]
    assert eigen[0] == pytest.approx(-source)
    assert eigen[1] == pytest.approx(source)
    assert h["zero_eigenvalue_multiplicity"] == 2


def test_quarter_exchange_from_10_generates_maximal_two_qubit_concurrence():
    _, e = _evolve(0.47, [0.0, 0.0, 1.0, 0.0], phase_fraction=0.25)
    assert float.fromhex(e["exchange_phase_absJ_dt_over_hbar_f64_hex"]) == pytest.approx(math.pi / 4.0)
    assert float.fromhex(e["final_concurrence_f64_hex"]) == pytest.approx(1.0)
    assert e["entanglement_generated"] is True
    assert e["excitation_expectation_conserved"] is True
    assert float.fromhex(e["final_norm2_f64_hex"]) == pytest.approx(1.0)


def test_half_exchange_from_10_transfers_population_to_01():
    _, e = _evolve(0.73, [0.0, 0.0, 1.0, 0.0], phase_fraction=0.5)
    final = [_decode_complex(z) for z in e["final_amplitudes"]]
    assert abs(final[1]) ** 2 == pytest.approx(1.0)
    assert abs(final[2]) ** 2 == pytest.approx(0.0, abs=1e-14)
    assert float.fromhex(e["final_concurrence_f64_hex"]) == pytest.approx(0.0, abs=1e-14)


def test_orientation_reversal_preserves_population_and_reverses_transfer_phase():
    tau = 0.64
    _, pos = _evolve(tau, [0.0, 0.0, 1.0, 0.0], phase_fraction=0.25)
    _, neg = _evolve(-tau, [0.0, 0.0, 1.0, 0.0], phase_fraction=0.25)
    pos_final = [_decode_complex(z) for z in pos["final_amplitudes"]]
    neg_final = [_decode_complex(z) for z in neg["final_amplitudes"]]
    assert abs(pos_final[1]) ** 2 == pytest.approx(abs(neg_final[1]) ** 2)
    assert abs(pos_final[2]) ** 2 == pytest.approx(abs(neg_final[2]) ** 2)
    phase_pos = float.fromhex(pos["transfer_phase_rad_f64_hex"])
    phase_neg = float.fromhex(neg["transfer_phase_rad_f64_hex"])
    assert _wrap_pi(phase_pos - phase_neg) == pytest.approx(_wrap_pi(2.0 * tau))
    assert pos["population_dynamics_orientation_blind"] is True
    assert pos["transfer_phase_orientation_sensitive"] is True


def test_zero_and_double_excitation_sectors_are_stationary_under_exchange():
    _, zero = _evolve(0.4, [1.0, 0.0, 0.0, 0.0], phase_fraction=0.37)
    _, double = _evolve(0.4, [0.0, 0.0, 0.0, 1.0], phase_fraction=0.37)
    zf = [_decode_complex(z) for z in zero["final_amplitudes"]]
    df = [_decode_complex(z) for z in double["final_amplitudes"]]
    assert zf == pytest.approx([1.0, 0.0, 0.0, 0.0])
    assert df == pytest.approx([0.0, 0.0, 0.0, 1.0])


def test_tampered_off_diagonal_breaks_hermitian_receipt_validation():
    energy, path, _, partition, oriented, h = _stack(0.31)
    broken = copy.deepcopy(h)
    broken["hamiltonian_matrix_j"][2][1]["im_f64_hex"] = (0.0).hex()
    with pytest.raises(HermitianOrientedExchangeError):
        validate_hermitian_oriented_exchange_v14(
            broken,
            oriented=oriented,
            energy=energy,
            path=path,
            partition=partition,
        )


def test_operator_authority_remains_candidate_and_target_attribution_open():
    _, _, _, _, _, h = _stack(0.2)
    assert h["parameter_free_given_oriented_coupling"] is True
    assert h["physical_target_attribution"] == "OPEN"
    assert h["execution_status"] == "RESEARCH_BINDING_ONLY"
    assert h["canon_status"] == "CANDIDATE"
