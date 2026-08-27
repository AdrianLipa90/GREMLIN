from __future__ import annotations

import copy
import math

import pytest

from tools.gremlin_maxsym_spin_geometry_v010 import (
    MaxSymSpinGeometryError,
    build_maxsym_spin_geometry_v010,
    build_maxsym_spin_qhtri_bridge_v010,
    validate_maxsym_spin_geometry_v010,
    validate_maxsym_spin_qhtri_bridge_v010,
)
from tools.gremlin_relational_lambda_holonomy_v08 import (
    build_relational_lambda_energy_v08,
    build_relational_lambda_field_v08,
)

H = "d" * 64


def _energy(lam: float):
    field = build_relational_lambda_field_v08(
        relation_id="R:Lambda:maxsym",
        spacetime_point_id="x:test",
        lambda_m2=lam,
        source_ref="source:relational-lambda:test",
        source_commitment=H,
        epistemic_status="MODEL_CANDIDATE",
    )
    return build_relational_lambda_energy_v08(field=field, support_volume_m3=1.0)


def test_flat_limit_removes_polar_frame_gauge_rotation():
    g = build_maxsym_spin_geometry_v010(energy=_energy(0.0), radius_m=3.0)
    assert validate_maxsym_spin_geometry_v010(g)
    assert float.fromhex(g["sectional_curvature_K_m_minus_2_f64_hex"]) == 0.0
    assert float.fromhex(g["section_radius_S_K_m_f64_hex"]) == 3.0
    assert float.fromhex(g["S_K_prime_f64_hex"]) == 1.0
    assert float.fromhex(g["vector_curvature_holonomy_rad_f64_hex"]) == 0.0
    assert float.fromhex(g["spin_half_curvature_holonomy_rad_f64_hex"]) == 0.0
    assert float.fromhex(g["spin_connection"]["spin_half_projection_rad_per_m_f64_hex"]) == 0.0
    assert g["polar_frame_gauge_baseline_removed"] is True


def test_positive_lambda_closes_einstein_maxsym_curvature_and_stokes():
    lam = 0.12
    g = build_maxsym_spin_geometry_v010(energy=_energy(lam), radius_m=2.0)
    assert validate_maxsym_spin_geometry_v010(g)
    k = float.fromhex(g["sectional_curvature_K_m_minus_2_f64_hex"])
    area = float.fromhex(g["disk_area_m2_f64_hex"])
    phi = float.fromhex(g["vector_curvature_holonomy_rad_f64_hex"])
    tau = float.fromhex(g["spin_half_curvature_holonomy_rad_f64_hex"])
    assert k == pytest.approx(lam / 3.0)
    assert float.fromhex(g["ricci_scalar_4d_m_minus_2_f64_hex"]) == pytest.approx(4.0 * lam)
    assert float.fromhex(g["ricci_scalar_section_2d_m_minus_2_f64_hex"]) == pytest.approx(2.0 * k)
    assert phi == pytest.approx(k * area)
    assert tau == pytest.approx(phi / 2.0)
    assert phi > 0.0


def test_negative_lambda_closes_hyperbolic_section_and_signed_holonomy():
    lam = -0.12
    g = build_maxsym_spin_geometry_v010(energy=_energy(lam), radius_m=2.0)
    assert validate_maxsym_spin_geometry_v010(g)
    k = float.fromhex(g["sectional_curvature_K_m_minus_2_f64_hex"])
    area = float.fromhex(g["disk_area_m2_f64_hex"])
    phi = float.fromhex(g["vector_curvature_holonomy_rad_f64_hex"])
    assert area > 0.0
    assert phi == pytest.approx(k * area)
    assert phi < 0.0


def test_cosmological_scale_is_numerically_resolved_on_cosmic_radius():
    g = build_maxsym_spin_geometry_v010(energy=_energy(1.1e-52), radius_m=1.0e26)
    assert validate_maxsym_spin_geometry_v010(g)
    assert abs(float.fromhex(g["spin_half_curvature_holonomy_rad_f64_hex"])) > 0.0


def test_positive_curvature_rejects_radius_at_or_beyond_antipode():
    lam = 3.0
    k = lam / 3.0
    with pytest.raises(MaxSymSpinGeometryError):
        build_maxsym_spin_geometry_v010(energy=_energy(lam), radius_m=math.pi / math.sqrt(k))


def test_tetrad_and_connection_are_content_bound():
    g = build_maxsym_spin_geometry_v010(energy=_energy(0.12), radius_m=2.0)
    broken = copy.deepcopy(g)
    broken["spin_connection"]["spin_half_u1_dphi_f64_hex"] = (0.4).hex()
    with pytest.raises(MaxSymSpinGeometryError):
        validate_maxsym_spin_geometry_v010(broken)


def test_spin_half_projection_integrates_to_half_curvature_holonomy():
    g = build_maxsym_spin_geometry_v010(energy=_energy(0.12), radius_m=2.0)
    projection = float.fromhex(g["spin_connection"]["spin_half_projection_rad_per_m_f64_hex"])
    circumference = float.fromhex(g["circle_circumference_m_f64_hex"])
    tau = float.fromhex(g["spin_half_curvature_holonomy_rad_f64_hex"])
    assert projection * circumference == pytest.approx(tau)


def test_qhtri_bridge_has_no_manual_tau_and_preserves_winding_identity():
    energy = _energy(0.12)
    g = build_maxsym_spin_geometry_v010(energy=energy, radius_m=2.0)
    receipt = build_maxsym_spin_qhtri_bridge_v010(
        energy=energy,
        geometry=g,
        oscillator_i="nu:1",
        oscillator_j="nu:2",
        n=2,
        m=4,
        theta_i_rad=1.1,
        theta_j_rad=0.3,
    )
    assert validate_maxsym_spin_qhtri_bridge_v010(receipt)
    assert receipt["manual_tau_present"] is False
    assert receipt["tau_origin"] == "LAMBDA_TO_MAXSYM_METRIC_TO_TETRAD_TO_SPIN_CONNECTION_TO_CURVATURE_HOLONOMY"
    inner = receipt["qhtri_connection_derived_lag_v09"]["qhtri_holonomy_lag_v08"]
    assert inner["n"] == 2
    assert inner["m"] == 4
    assert receipt["entanglement_status"] == "OPEN_REQUIRES_JOINT_QUANTUM_WITNESS"


def test_flat_lambda_qhtri_bridge_produces_zero_geometric_tau():
    energy = _energy(0.0)
    g = build_maxsym_spin_geometry_v010(energy=energy, radius_m=2.0)
    receipt = build_maxsym_spin_qhtri_bridge_v010(
        energy=energy,
        geometry=g,
        oscillator_i="nu:1",
        oscillator_j="nu:2",
        n=1,
        m=1,
        theta_i_rad=0.7,
        theta_j_rad=0.2,
    )
    inner = receipt["qhtri_connection_derived_lag_v09"]["qhtri_holonomy_lag_v08"]
    assert float.fromhex(inner["tau_holonomy_rad_f64_hex"]) == 0.0
