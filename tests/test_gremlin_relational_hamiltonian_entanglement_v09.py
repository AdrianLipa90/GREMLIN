from __future__ import annotations

import copy
import math

import pytest

from tools.gremlin_relational_entanglement_firewall_v09 import validate_entanglement_lineage_v09
from tools.gremlin_relational_hamiltonian_entanglement_v09 import (
    HBAR_SI,
    RelationalHamiltonianEntanglementError,
    build_pair_entanglement_witness_v09,
    build_phased_exchange_hamiltonian_v09,
    build_relational_coupling_energy_v09,
    validate_pair_entanglement_witness_v09,
    validate_phased_exchange_hamiltonian_v09,
    validate_relational_coupling_energy_v09,
)
from tools.gremlin_relational_lambda_holonomy_v08 import (
    build_qhtri_holonomy_lag_v08,
    build_relational_geometry_holonomy_v08,
    build_relational_lambda_energy_v08,
    build_relational_lambda_field_v08,
)

H1 = "11" * 32
H2 = "22" * 32
H3 = "33" * 32
H4 = "44" * 32


def qhtri(holonomy_phase: float = 0.3) -> dict:
    field = build_relational_lambda_field_v08(
        relation_id="REL:lambda:pair",
        spacetime_point_id="x:pair:1",
        lambda_m2=1.1e-52,
        source_ref="source:imploding-universe3:eq6",
        source_commitment=H1,
        epistemic_status="MODEL_CANDIDATE",
    )
    energy = build_relational_lambda_energy_v08(field=field, support_volume_m3=1.0)
    geometry = build_relational_geometry_holonomy_v08(
        energy=energy,
        geometry_adapter_id="adapter:spin-connection:u1-projection:v1",
        metric_commitment=H2,
        connection_commitment=H3,
        loop_id="loop:gamma:pair",
        holonomy_phase_rad=holonomy_phase,
        source_ref="geometry:witness:pair",
        epistemic_status="GEOMETRY_ADAPTER_CANDIDATE",
    )
    return build_qhtri_holonomy_lag_v08(
        geometry=geometry,
        oscillator_i="nu:i",
        oscillator_j="nu:j",
        n=1,
        m=1,
        theta_i_rad=1.1,
        theta_j_rad=0.2,
    )


def coupling(J: float = 2.0e-25, holonomy_phase: float = 0.3) -> dict:
    return build_relational_coupling_energy_v09(
        qhtri_binding=qhtri(holonomy_phase),
        coupling_J_joule=J,
        source_ref="model:pair-exchange:J",
        source_commitment=H4,
        epistemic_status="MODEL_PARAMETER",
    )


def hamiltonian(J: float = 2.0e-25, holonomy_phase: float = 0.3) -> tuple[dict, dict]:
    c = coupling(J, holonomy_phase)
    return c, build_phased_exchange_hamiltonian_v09(coupling=c)


def witness(J: float = 2.0e-25, holonomy_phase: float = 0.3, t: float | None = None) -> tuple[dict, dict, dict]:
    c, h = hamiltonian(J, holonomy_phase)
    if t is None:
        t = math.pi * HBAR_SI / (4.0 * abs(J)) if J != 0.0 else 1.0
    w = build_pair_entanglement_witness_v09(coupling=c, hamiltonian=h, interaction_time_s=t)
    return c, h, w


def cmath_phase(z: complex) -> float:
    return math.atan2(z.imag, z.real)


def test_coupling_energy_binds_qhtri_potential_and_torsion_generator() -> None:
    c = coupling(J=3.0e-25)
    assert validate_relational_coupling_energy_v09(c)
    J = float.fromhex(c["coupling_J_joule_f64_hex"])
    epsilon = float.fromhex(c["epsilon_qhtri_rad_f64_hex"])
    assert float.fromhex(c["qhtri_potential_energy_joule_f64_hex"]) == -J * math.cos(epsilon)
    assert float.fromhex(c["qhtri_torsion_generator_joule_f64_hex"]) == -J * math.sin(epsilon)
    assert c["torsion_generator_law"] == "Q_epsilon=-dV/depsilon=-J_ij*sin(epsilon_ij)"
    assert c["coupling_energy_scale_status"] == "BOUND_MODEL_PARAMETER"
    assert c["physical_interaction_identification_status"] == "OPEN"


def test_phased_exchange_hamiltonian_is_exactly_hermitian() -> None:
    c, h = hamiltonian(J=2.0e-25, holonomy_phase=0.77)
    assert validate_relational_coupling_energy_v09(c)
    assert validate_phased_exchange_hamiltonian_v09(h)
    a = complex(float.fromhex(h["H_01_10_joule"]["re_f64_hex"]), float.fromhex(h["H_01_10_joule"]["im_f64_hex"]))
    b = complex(float.fromhex(h["H_10_01_joule"]["re_f64_hex"]), float.fromhex(h["H_10_01_joule"]["im_f64_hex"]))
    assert b == a.conjugate()
    assert h["holonomy_role"] == "RELATIONAL_EXCHANGE_PHASE"
    assert h["hermiticity_status"] == "EXACT_BY_CONSTRUCTION"


def test_quarter_exchange_pulse_gives_maximal_model_concurrence() -> None:
    c, h, w = witness(J=2.0e-25, holonomy_phase=0.4)
    assert validate_pair_entanglement_witness_v09(w)
    assert validate_entanglement_lineage_v09(coupling=c, hamiltonian=h, witness=w)
    concurrence = float.fromhex(w["pure_state_concurrence_f64_hex"])
    purity = float.fromhex(w["reduced_single_mode_purity_f64_hex"])
    assert math.isclose(concurrence, 1.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(purity, 0.5, rel_tol=0.0, abs_tol=1e-12)
    assert w["entanglement_witness_state"] == "ENTANGLED_MODEL_WITNESS"
    assert w["physical_neutrino_pair_validation_status"] == "OPEN"
    assert w["witness_scope"] == "TWO_MODE_MODEL_LEVEL"


def test_holonomy_changes_relational_state_phase_while_concurrence_is_preserved() -> None:
    c1, h1, w1 = witness(J=2.0e-25, holonomy_phase=0.1)
    c2, h2, w2 = witness(J=2.0e-25, holonomy_phase=1.1)
    assert validate_entanglement_lineage_v09(coupling=c1, hamiltonian=h1, witness=w1)
    assert validate_entanglement_lineage_v09(coupling=c2, hamiltonian=h2, witness=w2)
    a1 = complex(float.fromhex(w1["amplitude_01"]["re_f64_hex"]), float.fromhex(w1["amplitude_01"]["im_f64_hex"]))
    a2 = complex(float.fromhex(w2["amplitude_01"]["re_f64_hex"]), float.fromhex(w2["amplitude_01"]["im_f64_hex"]))
    assert not math.isclose(cmath_phase(a1), cmath_phase(a2), rel_tol=0.0, abs_tol=1e-6)
    assert math.isclose(
        float.fromhex(w1["pure_state_concurrence_f64_hex"]),
        float.fromhex(w2["pure_state_concurrence_f64_hex"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    )


def test_zero_exchange_energy_is_control_sample_with_zero_concurrence() -> None:
    c, h, w = witness(J=0.0, holonomy_phase=0.7, t=3.0)
    assert validate_entanglement_lineage_v09(coupling=c, hamiltonian=h, witness=w)
    assert float.fromhex(w["pure_state_concurrence_f64_hex"]) == 0.0
    assert w["entanglement_witness_state"] == "SEPARABLE_MODEL_SAMPLE"


def test_zero_interaction_time_is_control_sample_with_zero_concurrence() -> None:
    c, h, w = witness(J=2.0e-25, holonomy_phase=0.7, t=0.0)
    assert validate_entanglement_lineage_v09(coupling=c, hamiltonian=h, witness=w)
    assert float.fromhex(w["pure_state_concurrence_f64_hex"]) == 0.0
    assert w["entanglement_witness_state"] == "SEPARABLE_MODEL_SAMPLE"


def test_negative_interaction_time_and_unsupported_initial_state_fail_closed() -> None:
    c, h = hamiltonian()
    with pytest.raises(RelationalHamiltonianEntanglementError):
        build_pair_entanglement_witness_v09(coupling=c, hamiltonian=h, interaction_time_s=-1.0)
    with pytest.raises(RelationalHamiltonianEntanglementError):
        build_pair_entanglement_witness_v09(coupling=c, hamiltonian=h, interaction_time_s=1.0, initial_state="|00>")


def test_tamper_fails_closed_at_coupling_hamiltonian_and_cross_lineage_firewall() -> None:
    c, h, w = witness()

    tc = copy.deepcopy(c)
    tc["qhtri_potential_energy_joule_f64_hex"] = float(0.0).hex()
    with pytest.raises(RelationalHamiltonianEntanglementError):
        validate_relational_coupling_energy_v09(tc)

    th = copy.deepcopy(h)
    th["H_10_01_joule"]["im_f64_hex"] = float(9.0).hex()
    with pytest.raises(RelationalHamiltonianEntanglementError):
        validate_phased_exchange_hamiltonian_v09(th)

    tw = copy.deepcopy(w)
    tw["amplitude_01"]["re_f64_hex"] = float(0.0).hex()
    with pytest.raises(RelationalHamiltonianEntanglementError):
        validate_pair_entanglement_witness_v09(tw)

    c_other, h_other, _ = witness(J=4.0e-25, holonomy_phase=1.0)
    with pytest.raises(RelationalHamiltonianEntanglementError):
        validate_entanglement_lineage_v09(coupling=c_other, hamiltonian=h_other, witness=w)
