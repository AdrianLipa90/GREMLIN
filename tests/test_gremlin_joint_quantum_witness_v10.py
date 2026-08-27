from __future__ import annotations

import copy
import math

import pytest

from tools.gremlin_connection_path_holonomy_v09 import (
    build_connection_path_integral_v09,
    build_derived_geometry_holonomy_v09,
    build_qhtri_connection_derived_lag_v09,
)
from tools.gremlin_joint_quantum_witness_v10 import (
    HBAR_SI,
    JointQuantumWitnessError,
    build_entanglement_witness_v10,
    build_joint_pure_state_v10,
    build_zz_coupling_evolution_v10,
    validate_entanglement_witness_v10,
    validate_joint_pure_state_v10,
    validate_zz_coupling_evolution_v10,
)
from tools.gremlin_relational_lambda_holonomy_v08 import (
    build_relational_lambda_energy_v08,
    build_relational_lambda_field_v08,
)

H = "a" * 64


def _energy():
    field = build_relational_lambda_field_v08(
        relation_id="R:Lambda",
        spacetime_point_id="x:0",
        lambda_m2=1.1e-52,
        source_ref="source:imploding-universe3:p4",
        source_commitment=H,
        epistemic_status="MODEL_CANDIDATE",
    )
    return build_relational_lambda_energy_v08(field=field, support_volume_m3=1.0)


def _qhtri(*, theta_i=0.3, theta_j=0.3, omega=0.0, n=1, m=1):
    energy = _energy()
    path = build_connection_path_integral_v09(
        energy=energy,
        geometry_adapter_id="adapter:spin-connection-projection:v1",
        metric_commitment="b" * 64,
        connection_commitment="c" * 64,
        loop_id="gamma:ij",
        connection_projection_rad_per_m=[omega],
        segment_lengths_m=[1.0],
        source_ref="geometry:upstream:witness",
        epistemic_status="MODEL_CANDIDATE",
    )
    geometry = build_derived_geometry_holonomy_v09(energy=energy, path=path)
    return build_qhtri_connection_derived_lag_v09(
        derived_geometry=geometry,
        oscillator_i="nu:i",
        oscillator_j="nu:j",
        n=n,
        m=m,
        theta_i_rad=theta_i,
        theta_j_rad=theta_j,
    )


def _state(amplitudes):
    return build_joint_pure_state_v10(
        qhtri_receipt=_qhtri(),
        amplitudes=amplitudes,
        source_ref="joint-state:model-input",
        epistemic_status="MODEL_CANDIDATE",
    )


def test_product_state_has_zero_concurrence():
    state = _state([0.5, 0.5, 0.5, 0.5])
    assert validate_joint_pure_state_v10(state)
    witness = build_entanglement_witness_v10(state=state)
    assert validate_entanglement_witness_v10(witness, state=state)
    assert float.fromhex(witness["concurrence_f64_hex"]) == pytest.approx(0.0)
    assert witness["witness_status"] == "SEPARABLE_WITHIN_TOLERANCE"


def test_bell_state_has_unit_concurrence():
    state = _state([1.0, 0.0, 0.0, 1.0])
    witness = build_entanglement_witness_v10(state=state)
    assert float.fromhex(witness["concurrence_f64_hex"]) == pytest.approx(1.0)
    assert float.fromhex(witness["reduced_single_qubit_purity_f64_hex"]) == pytest.approx(0.5)
    assert witness["witness_status"] == "ENTANGLED_PURE_STATE_WITNESS"


def test_perfect_qhtri_phase_lock_does_not_imply_entanglement():
    qhtri = _qhtri(theta_i=0.7, theta_j=0.7, omega=0.0, n=1, m=1)
    inner = qhtri["qhtri_holonomy_lag_v08"]
    assert float.fromhex(inner["phase_lock_C_f64_hex"]) == pytest.approx(1.0)
    state = build_joint_pure_state_v10(
        qhtri_receipt=qhtri,
        amplitudes=[0.5, 0.5, 0.5, 0.5],
        source_ref="synchronized-product-state",
        epistemic_status="MODEL_CANDIDATE",
    )
    witness = build_entanglement_witness_v10(state=state)
    assert witness["synchronization_entanglement_equivalence"] is False
    assert float.fromhex(witness["concurrence_f64_hex"]) == pytest.approx(0.0)


def test_state_normalization_is_deterministic_and_preserves_bell_structure():
    state = _state([2.0, 0.0, 0.0, 2.0])
    assert float.fromhex(state["input_norm2_f64_hex"]) == pytest.approx(8.0)
    assert float.fromhex(state["normalized_norm2_f64_hex"]) == pytest.approx(1.0)
    witness = build_entanglement_witness_v10(state=state)
    assert float.fromhex(witness["concurrence_f64_hex"]) == pytest.approx(1.0)


def test_zero_norm_state_is_rejected():
    with pytest.raises(JointQuantumWitnessError):
        _state([0.0, 0.0, 0.0, 0.0])


def test_joint_state_tamper_fails_validation():
    state = _state([1.0, 0.0, 0.0, 0.0])
    broken = copy.deepcopy(state)
    broken["amplitudes"][0]["re_f64_hex"] = (0.5).hex()
    with pytest.raises(JointQuantumWitnessError):
        validate_joint_pure_state_v10(broken)


def test_witness_tamper_fails_validation():
    state = _state([1.0, 0.0, 0.0, 1.0])
    witness = build_entanglement_witness_v10(state=state)
    broken = copy.deepcopy(witness)
    broken["concurrence_f64_hex"] = (0.25).hex()
    with pytest.raises(JointQuantumWitnessError):
        validate_entanglement_witness_v10(broken, state=state)


def test_declared_zz_coupling_can_generate_entanglement_from_product_state():
    state = _state([0.5, 0.5, 0.5, 0.5])
    coupling_j = HBAR_SI * math.pi / 4.0
    evolution = build_zz_coupling_evolution_v10(
        initial_state=state,
        coupling_energy_j=coupling_j,
        duration_s=1.0,
        coupling_source_ref="model:J_rel:declared",
        coupling_source_commitment="d" * 64,
        coupling_epistemic_status="MODEL_COUPLING_CANDIDATE",
    )
    assert validate_zz_coupling_evolution_v10(evolution, initial_state=state)
    assert float.fromhex(evolution["initial_concurrence_f64_hex"]) == pytest.approx(0.0)
    assert float.fromhex(evolution["final_concurrence_f64_hex"]) == pytest.approx(1.0)
    assert evolution["entanglement_generated"] is True
    assert evolution["generation_status"] == "ENTANGLEMENT_GENERATED_BY_DECLARED_ZZ_COUPLING_WITHIN_MODEL"
    assert evolution["lambda_holonomy_to_J_rel_derivation_status"] == "OPEN"


def test_zero_zz_coupling_preserves_product_separability():
    state = _state([0.5, 0.5, 0.5, 0.5])
    evolution = build_zz_coupling_evolution_v10(
        initial_state=state,
        coupling_energy_j=0.0,
        duration_s=10.0,
        coupling_source_ref="model:J_rel:zero-control",
        coupling_source_commitment="e" * 64,
        coupling_epistemic_status="CONTROL",
    )
    assert float.fromhex(evolution["final_concurrence_f64_hex"]) == pytest.approx(0.0)
    assert evolution["entanglement_generated"] is False


def test_zz_evolution_tamper_fails_validation():
    state = _state([0.5, 0.5, 0.5, 0.5])
    evolution = build_zz_coupling_evolution_v10(
        initial_state=state,
        coupling_energy_j=HBAR_SI * 0.2,
        duration_s=1.0,
        coupling_source_ref="model:J_rel",
        coupling_source_commitment="f" * 64,
        coupling_epistemic_status="MODEL_COUPLING_CANDIDATE",
    )
    broken = copy.deepcopy(evolution)
    broken["final_amplitudes"][0]["re_f64_hex"] = (0.0).hex()
    with pytest.raises(JointQuantumWitnessError):
        validate_zz_coupling_evolution_v10(broken, initial_state=state)


def test_qhtri_connection_lineage_is_preserved_into_joint_state_and_evolution():
    qhtri = _qhtri(theta_i=1.1, theta_j=0.2, omega=0.4, n=2, m=3)
    state = build_joint_pure_state_v10(
        qhtri_receipt=qhtri,
        amplitudes=[1.0, 0.0, 0.0, 0.0],
        source_ref="state:lineage",
        epistemic_status="MODEL_CANDIDATE",
    )
    assert state["tau_origin"] == "CONNECTION_PATH_INTEGRAL"
    assert state["qhtri_connection_derived_commitment"] == qhtri["qhtri_connection_derived_commitment"]
    evolution = build_zz_coupling_evolution_v10(
        initial_state=state,
        coupling_energy_j=HBAR_SI * 0.1,
        duration_s=1.0,
        coupling_source_ref="model:J_rel",
        coupling_source_commitment="1" * 64,
        coupling_epistemic_status="MODEL_COUPLING_CANDIDATE",
    )
    assert evolution["qhtri_connection_derived_commitment"] == qhtri["qhtri_connection_derived_commitment"]
    assert evolution["tau_origin"] == "CONNECTION_PATH_INTEGRAL"
