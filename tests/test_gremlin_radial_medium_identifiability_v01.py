import math

import pytest

from tools.gremlin_radial_medium_identifiability_v01 import (
    RadialDiagnostic,
    RadialIdentifiabilityError,
    candidate_information_holonomy_residual,
    central_consistency_residual,
    condensate_subtracted_residual,
    epicyclic_prediction,
    holonomy_shell_susceptibility_tau,
    is_kepler_camouflage_potential,
    k_obs_gradient_from_epicycle,
    near_kepler_precession_from_log_k_slope,
    precession_per_orbit,
)


@pytest.mark.parametrize(("q", "ratio"), [(0.0, 4.0), (2.0, 2.0), (3.0, 1.0)])
def test_power_law_epicycle(q, ratio):
    r = 2.7
    amplitude = 1.3
    omega_sq = amplitude * r ** (-q)
    derivative = -q * amplitude * r ** (-q - 1.0)
    assert epicyclic_prediction(r, omega_sq, derivative) == pytest.approx(
        ratio * omega_sq
    )


def test_belzebub_residual_zero_for_central_model():
    r = 3.0
    omega_sq = 0.4
    derivative = -0.07
    predicted = epicyclic_prediction(r, omega_sq, derivative)
    assert central_consistency_residual(
        r, omega_sq, derivative, predicted
    ) == pytest.approx(0.0)


def test_kobs_gradient_identity():
    r = 4.0
    omega_sq = 0.25
    kappa_sq = 0.4
    assert k_obs_gradient_from_epicycle(r, omega_sq, kappa_sq) == pytest.approx(
        r**2 * (kappa_sq - omega_sq)
    )
    diag = RadialDiagnostic(r, omega_sq, kappa_sq)
    assert diag.non_kepler_indicator == pytest.approx(
        k_obs_gradient_from_epicycle(r, omega_sq, kappa_sq)
    )


def test_kepler_has_no_apsidal_precession():
    assert precession_per_orbit(1.0, 1.0) == pytest.approx(0.0)


def test_flat_rotation_has_retrograde_epicyclic_offset():
    omega_sq = 1.0
    kappa_sq = 2.0
    expected = 2.0 * math.pi * (1.0 / math.sqrt(2.0) - 1.0)
    assert precession_per_orbit(omega_sq, kappa_sq) == pytest.approx(expected)


def test_near_kepler_log_slope_formula():
    slope = 0.02
    assert near_kepler_precession_from_log_k_slope(slope) == pytest.approx(
        -math.pi * slope
    )


def test_holonomy_susceptibility_scales_as_inverse_kappa_sq():
    args = dict(radius=3.0, circulation_scale=2.0, effective_winding=1.5)
    s1 = abs(holonomy_shell_susceptibility_tau(kappa_sq=1.0, **args))
    s2 = abs(holonomy_shell_susceptibility_tau(kappa_sq=0.1, **args))
    assert s2 == pytest.approx(10.0 * s1)


def test_condensate_subtraction_and_normalization():
    r = 2.0
    mobility = 0.6
    coupling = 1.1
    k_orb = 3.0
    rho_prime = -0.2
    q_prime = 0.05
    target_residual = 0.4
    omega_sq = (
        target_residual
        + k_orb / r**2
        + 2.0 * mobility * coupling * rho_prime
        - 2.0 * mobility**2 * q_prime
    ) / r
    g_res = condensate_subtracted_residual(
        r,
        omega_sq,
        k_orb=k_orb,
        mobility=mobility,
        coupling_g=coupling,
        density_gradient=rho_prime,
        quantum_density_gradient=q_prime,
    )
    assert g_res == pytest.approx(target_residual)
    assert candidate_information_holonomy_residual(
        g_res, mobility
    ) == pytest.approx(target_residual / (2.0 * mobility))


def test_kepler_camouflage_is_exact_inverse_cube_orbital_shift():
    r = 5.0
    c0 = 7.0
    c1 = -2.0
    phi, delta_omega_sq = is_kepler_camouflage_potential(
        c0=c0, c1=c1, radius=r
    )
    assert phi == pytest.approx(c0 + c1 / r)
    assert delta_omega_sq == pytest.approx(-c1 / r**3)


@pytest.mark.parametrize(
    "call",
    [
        lambda: epicyclic_prediction(0.0, 1.0, 0.0),
        lambda: precession_per_orbit(1.0, 0.0),
        lambda: holonomy_shell_susceptibility_tau(1.0, 1.0, 1.0, 0.0),
    ],
)
def test_fail_closed(call):
    with pytest.raises(RadialIdentifiabilityError):
        call()
