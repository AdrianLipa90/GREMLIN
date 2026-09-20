import math

import pytest

from tools.gremlin_endogenous_eb_condensate_normal_modes_v012 import (
    EndogenousEBNormalModeError,
    budget_closure,
    collective_matrices_3x3,
    collective_mode_spectrum,
    endogenous_lambda_eb,
    endogenous_radial_stiffness_squared_from_budget,
    endogenous_radial_stiffness_squared_unreduced,
    phase_energy_from_locked_orbit,
    pure_endogenous_radius,
    pure_endogenous_stationary_central_residual,
    radial_budget_term,
    relative_phase_frequency_squared,
    relative_phase_inertia,
    source_acceleration_phase_rate_sensitivity,
    stabilization_witness,
    winding_omega,
)


def test_pure_radius_closes_lambda_eb():
    r = pure_endogenous_radius(
        source_coefficient=0.4,
        eta_g=0.5,
        phase_inertia=6.0,
        effective_winding=3.0,
    )
    lam = endogenous_lambda_eb(
        r,
        source_coefficient=0.4,
        eta_g=0.5,
        phase_inertia=6.0,
        effective_winding=3.0,
    )
    assert lam == pytest.approx(1.0)


def test_q_scaling_r_omega_h_is_two_thirds_minus_one_third_four_thirds():
    kwargs = dict(source_coefficient=0.7, eta_g=0.8, phase_inertia=5.0)
    r1 = pure_endogenous_radius(effective_winding=1.0, **kwargs)
    r8 = pure_endogenous_radius(effective_winding=8.0, **kwargs)
    assert r8 / r1 == pytest.approx(8.0 ** (2.0 / 3.0))
    w1 = abs(winding_omega(2.0, 3.0, r1, 1.0))
    w8 = abs(winding_omega(2.0, 3.0, r8, 8.0))
    assert w8 / w1 == pytest.approx(8.0 ** (-1.0 / 3.0))
    h1 = phase_energy_from_locked_orbit(5.0, 1.0, w1)
    h8 = phase_energy_from_locked_orbit(5.0, 8.0, w8)
    assert h8 / h1 == pytest.approx(8.0 ** (4.0 / 3.0))


def test_pure_endogenous_branch_has_negative_three_omega_squared_stiffness():
    assert endogenous_radial_stiffness_squared_unreduced(
        2.0, lambda_eb=1.0, inertial_mass=4.0
    ) == pytest.approx(-6.0)


def test_budget_reduced_and_unreduced_stiffness_agree():
    omega2 = 2.5
    r = 3.0
    mass = 4.0
    grad = 1.2
    hess = -0.3
    lam_rad = radial_budget_term(grad, r, mass, omega2)
    lam_eb = 1.0 - lam_rad
    a = endogenous_radial_stiffness_squared_unreduced(
        omega2, lam_eb, mass, hess
    )
    b = endogenous_radial_stiffness_squared_from_budget(
        omega2, r, mass, grad, hess, lambda_eb=lam_eb
    )
    assert a == pytest.approx(b)


def test_budget_reduced_stiffness_fails_closed_when_equilibrium_does_not_close():
    with pytest.raises(EndogenousEBNormalModeError):
        endogenous_radial_stiffness_squared_from_budget(
            1.0, 2.0, 3.0, 0.0, 0.0, lambda_eb=0.7
        )


def test_stabilization_requires_support_above_three():
    unstable = stabilization_witness(1.0, 2.0, 1.0, 0.0, 2.9)
    stable = stabilization_witness(1.0, 2.0, 1.0, 0.0, 3.1)
    assert not unstable.stable
    assert stable.stable


def test_pure_endogenous_matches_stationary_central_power_law_identity():
    residual = pure_endogenous_stationary_central_residual(3.0, 2.0)
    assert residual == pytest.approx(0.0)


def test_phase_source_velocity_sensitivity_is_nonzero_off_zero_rate():
    got = source_acceleration_phase_rate_sensitivity(
        2.0, 0.4, 0.5, 6.0, 3.0
    )
    assert got == pytest.approx(-0.4 * 0.5 * 6.0 * 3.0 / 4.0)


def test_relative_phase_reduced_inertia():
    got = relative_phase_inertia(4.0, 9.0, 2.0)
    assert got == pytest.approx(4.0 * 9.0 / (9.0 + 4.0 * 4.0))


def test_hard_lock_limit_pushes_relative_phase_mode_upward():
    a = relative_phase_frequency_squared(1.0, 4.0, 9.0, 2.0)
    b = relative_phase_frequency_squared(100.0, 4.0, 9.0, 2.0)
    assert b / a == pytest.approx(100.0)


def test_collective_diagonal_modes_match_sqrt_k_over_m():
    mats = collective_matrices_3x3(
        radial_mass=2.0,
        density_mass=3.0,
        relative_phase_mass=4.0,
        k_rr=8.0,
        k_rho_rho=27.0,
        k_psi_psi=64.0,
    )
    spec = collective_mode_spectrum(mats)
    assert spec.stable
    assert spec.positive_frequencies == pytest.approx((2.0, 3.0, 4.0))


def test_negative_endogenous_radial_stiffness_creates_growth_mode():
    mats = collective_matrices_3x3(
        radial_mass=2.0,
        density_mass=3.0,
        relative_phase_mass=4.0,
        k_rr=-6.0,
        k_rho_rho=27.0,
        k_psi_psi=64.0,
    )
    spec = collective_mode_spectrum(mats)
    assert not spec.stable
    assert spec.max_growth_rate == pytest.approx(math.sqrt(3.0))


def test_gyroscopic_matrix_is_admitted():
    mats = collective_matrices_3x3(
        radial_mass=1.0,
        density_mass=1.0,
        relative_phase_mass=1.0,
        k_rr=4.0,
        k_rho_rho=9.0,
        k_psi_psi=16.0,
        g_r_psi=0.5,
    )
    spec = collective_mode_spectrum(mats)
    assert len(spec.eigenvalues) == 6


def test_invalid_domains_fail_closed():
    with pytest.raises(EndogenousEBNormalModeError):
        pure_endogenous_radius(
            source_coefficient=1.0,
            eta_g=1.0,
            phase_inertia=1.0,
            effective_winding=0.0,
        )
    with pytest.raises(EndogenousEBNormalModeError):
        relative_phase_frequency_squared(-1.0, 1.0, 1.0, 1.0)


def test_budget_witness_reports_residual_without_silently_normalizing():
    w = budget_closure(0.8, [0.1])
    assert not w.closed
    assert w.residual == pytest.approx(0.1)
