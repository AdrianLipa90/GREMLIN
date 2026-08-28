from __future__ import annotations

import copy
import math

import pytest

from tools.gremlin_relational_lambda_holonomy_v08 import (
    C_SI,
    G_SI,
    RelationalLambdaHolonomyError,
    build_qhtri_holonomy_lag_v08,
    build_relational_geometry_holonomy_v08,
    build_relational_lambda_energy_v08,
    build_relational_lambda_field_v08,
    validate_qhtri_holonomy_lag_v08,
    validate_relational_geometry_holonomy_v08,
    validate_relational_lambda_energy_v08,
    validate_relational_lambda_field_v08,
    wrap_pi,
)

H1 = "11" * 32
H2 = "22" * 32
H3 = "33" * 32


def field(lambda_m2: float = 1.1e-52) -> dict:
    return build_relational_lambda_field_v08(
        relation_id="REL:lambda:1",
        spacetime_point_id="x:observer:1",
        lambda_m2=lambda_m2,
        source_ref="source:imploding-universe3:eq6",
        source_commitment=H1,
        epistemic_status="MODEL_CANDIDATE",
    )


def energy(lambda_m2: float = 1.1e-52, volume: float = 1.0) -> dict:
    return build_relational_lambda_energy_v08(field=field(lambda_m2), support_volume_m3=volume)


def geometry(phase: float = 0.75) -> dict:
    return build_relational_geometry_holonomy_v08(
        energy=energy(),
        geometry_adapter_id="adapter:spin-connection:u1-projection:v1",
        metric_commitment=H2,
        connection_commitment=H3,
        loop_id="loop:gamma:1",
        holonomy_phase_rad=phase,
        source_ref="geometry:witness:1",
        epistemic_status="GEOMETRY_ADAPTER_CANDIDATE",
    )


def qhtri(phase: float = 0.75, theta_i: float = 1.2, theta_j: float = 0.4, n: int = 2, m: int = 1) -> dict:
    return build_qhtri_holonomy_lag_v08(
        geometry=geometry(phase),
        oscillator_i="nu:i",
        oscillator_j="nu:j",
        n=n,
        m=m,
        theta_i_rad=theta_i,
        theta_j_rad=theta_j,
    )


def test_relational_lambda_field_binds_si_scalar_and_open_frontier_statuses() -> None:
    receipt = field()
    assert validate_relational_lambda_field_v08(receipt)
    assert receipt["field_units"] == "m^-2"
    assert receipt["field_semantics"] == "RELATIONAL_SCALAR_FIELD_CANDIDATE"
    assert float.fromhex(receipt["lambda_R_m_minus_2_f64_hex"]) == 1.1e-52
    assert receipt["geometry_derivation_status"] == "OPEN"
    assert receipt["holonomy_derivation_status"] == "OPEN"
    assert receipt["entanglement_status"] == "OPEN_REQUIRES_QUANTUM_WITNESS"
    assert receipt["execution_status"] == "RESEARCH_BINDING_ONLY"
    assert receipt["canon_status"] == "CANDIDATE"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_relational_lambda_field_rejects_nonfinite_values(bad: float) -> None:
    with pytest.raises(RelationalLambdaHolonomyError):
        field(bad)


def test_relational_lambda_effective_source_energy_has_declared_si_law() -> None:
    lam = 1.1e-52
    volume = 2.5
    receipt = energy(lam, volume)
    assert validate_relational_lambda_energy_v08(receipt)
    expected_density = lam * C_SI**4 / (8.0 * math.pi * G_SI)
    expected_energy = expected_density * volume
    assert float.fromhex(receipt["effective_source_energy_density_j_m3_f64_hex"]) == expected_density
    assert float.fromhex(receipt["effective_source_energy_j_f64_hex"]) == expected_energy
    assert receipt["energy_density_law"] == "u_R = Lambda_R*c^4/(8*pi*G)"
    assert receipt["geometry_adapter_status"] == "REQUIRED"
    assert receipt["dynamic_scalar_energy_terms_status"] == "OPEN"
    assert receipt["execution_status"] == "RESEARCH_BINDING_ONLY"
    assert receipt["canon_status"] == "CANDIDATE"


def test_relational_lambda_energy_requires_positive_declared_support_volume() -> None:
    with pytest.raises(RelationalLambdaHolonomyError):
        build_relational_lambda_energy_v08(field=field(), support_volume_m3=0.0)
    with pytest.raises(RelationalLambdaHolonomyError):
        build_relational_lambda_energy_v08(field=field(), support_volume_m3=-1.0)


def test_geometry_holonomy_requires_explicit_metric_connection_and_u1_projection() -> None:
    receipt = geometry(phase=7.0)
    assert validate_relational_geometry_holonomy_v08(receipt)
    assert receipt["metric_commitment"] == H2
    assert receipt["connection_commitment"] == H3
    assert receipt["holonomy_projection"] == "U1_PHASE_PROJECTION"
    assert receipt["connection_semantics"] == "INTERNAL_ROTATION_GEOMETRY_CANDIDATE"
    assert receipt["geometry_provenance"] == "UPSTREAM_ADAPTER_WITNESS"
    assert receipt["connection_derivation_contract"] == "EXPLICIT_GEOMETRY_ADAPTER_REQUIRED"
    assert float.fromhex(receipt["holonomy_phase_wrapped_rad_f64_hex"]) == wrap_pi(7.0)
    assert receipt["entanglement_status"] == "OPEN_REQUIRES_QUANTUM_WITNESS"


def test_holonomy_phase_is_periodic_modulo_two_pi() -> None:
    a = geometry(phase=0.37)
    b = geometry(phase=0.37 + 2.0 * math.pi)
    pa = float.fromhex(a["holonomy_phase_wrapped_rad_f64_hex"])
    pb = float.fromhex(b["holonomy_phase_wrapped_rad_f64_hex"])
    assert math.isclose(pa, pb, rel_tol=0.0, abs_tol=1e-15)


def test_qhtri_tau_is_geometric_holonomy_projection_and_epsilon_is_exactly_recomputed() -> None:
    phase = 0.75
    theta_i = 1.2
    theta_j = 0.4
    n, m = 2, 1
    receipt = qhtri(phase, theta_i, theta_j, n, m)
    assert validate_qhtri_holonomy_lag_v08(receipt)
    tau = wrap_pi(phase)
    epsilon = wrap_pi(n * theta_i - m * theta_j - tau)
    assert float.fromhex(receipt["tau_holonomy_rad_f64_hex"]) == tau
    assert float.fromhex(receipt["epsilon_qhtri_rad_f64_hex"]) == epsilon
    assert receipt["tau_origin"] == "U1_PROJECTED_GEOMETRIC_HOLONOMY"
    assert receipt["epsilon_law"] == "epsilon=wrap_pi(n*theta_i-m*theta_j-tau_holonomy)"


def test_qhtri_potential_force_and_phase_lock_follow_one_epsilon() -> None:
    receipt = qhtri(phase=-0.2, theta_i=0.9, theta_j=0.1, n=3, m=2)
    epsilon = float.fromhex(receipt["epsilon_qhtri_rad_f64_hex"])
    assert float.fromhex(receipt["unit_potential_shape_f64_hex"]) == -math.cos(epsilon)
    assert float.fromhex(receipt["unit_torsion_force_shape_f64_hex"]) == -math.sin(epsilon)
    assert float.fromhex(receipt["phase_lock_C_f64_hex"]) == math.cos(epsilon / 2.0) ** 2
    assert receipt["phase_lock_law"] == "C=cos^2(epsilon/2)"


def test_qhtri_preserves_exact_integer_winding_identity() -> None:
    a = qhtri(n=2, m=1)
    b = qhtri(n=4, m=2)
    assert a["n"] == 2 and a["m"] == 1
    assert b["n"] == 4 and b["m"] == 2
    assert a["qhtri_holonomy_lag_commitment"] != b["qhtri_holonomy_lag_commitment"]

    with pytest.raises(RelationalLambdaHolonomyError):
        qhtri(n=0, m=0)
    with pytest.raises(RelationalLambdaHolonomyError):
        build_qhtri_holonomy_lag_v08(
            geometry=geometry(),
            oscillator_i="nu:i",
            oscillator_j="nu:j",
            n=True,
            m=1,
            theta_i_rad=0.1,
            theta_j_rad=0.2,
        )


def test_qhtri_holonomy_binding_exposes_open_energy_entanglement_and_vector_frontiers() -> None:
    receipt = qhtri()
    assert receipt["coupling_energy_scale_status"] == "OPEN"
    assert receipt["entanglement_witness_status"] == "OPEN"
    assert receipt["entanglement_status"] == "OPEN_REQUIRES_QUANTUM_WITNESS"
    assert receipt["vector_synthesis_status"] == "HELD_FOR_PREVECTOR_ADMISSION"
    assert receipt["execution_status"] == "RESEARCH_BINDING_ONLY"
    assert receipt["canon_status"] == "CANDIDATE"


def test_commitment_tamper_fails_closed_across_all_four_layers() -> None:
    f = field()
    tf = copy.deepcopy(f)
    tf["lambda_R_m_minus_2_f64_hex"] = float(9.9e-52).hex()
    with pytest.raises(RelationalLambdaHolonomyError):
        validate_relational_lambda_field_v08(tf)

    e = energy()
    te = copy.deepcopy(e)
    te["effective_source_energy_j_f64_hex"] = float(1.0).hex()
    with pytest.raises(RelationalLambdaHolonomyError):
        validate_relational_lambda_energy_v08(te)

    g = geometry()
    tg = copy.deepcopy(g)
    tg["holonomy_phase_wrapped_rad_f64_hex"] = float(0.2).hex()
    with pytest.raises(RelationalLambdaHolonomyError):
        validate_relational_geometry_holonomy_v08(tg)

    q = qhtri()
    tq = copy.deepcopy(q)
    tq["epsilon_qhtri_rad_f64_hex"] = float(0.0).hex()
    with pytest.raises(RelationalLambdaHolonomyError):
        validate_qhtri_holonomy_lag_v08(tq)
