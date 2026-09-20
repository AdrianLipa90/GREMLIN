import math
import pytest

from tools.gremlin_eb_radial_stability_nullspace_v010 import (
    RadialStabilityError,
    full_orbital_omega_squared,
    information_coupling_from_precession,
    inverse_radius_nullspace,
    radial_epicyclic_omega_squared,
    source_amplitude,
    source_amplitude_shift_from_inverse_radius,
    total_radial_derivatives,
)


def test_epicyclic_minus_orbital_equals_total_radial_laplacian_over_mass():
    terms = dict(
        information_gradient=3.0,
        information_hessian=-0.5,
        information_coupling=0.25,
        quantum_pressure_gradient=0.2,
        quantum_pressure_hessian=0.1,
        trap_gradient=-0.1,
        trap_hessian=0.4,
        interaction_gradient=0.3,
        interaction_hessian=-0.2,
    )
    radius = 2.0
    mass = 4.0
    omega2 = full_orbital_omega_squared(5.0, 0.4, 0.5, radius, mass, **terms)
    kappa2 = radial_epicyclic_omega_squared(5.0, 0.4, 0.5, radius, mass, **terms)
    deriv = total_radial_derivatives(radius, **terms)
    assert math.isclose(kappa2 - omega2, deriv.laplacian_3d / mass)


def test_source_term_cancels_from_precession_difference():
    terms = dict(information_gradient=1.5, information_hessian=0.25, information_coupling=0.75)
    a = (
        full_orbital_omega_squared(3.0, 0.2, 0.5, 2.0, 7.0, **terms),
        radial_epicyclic_omega_squared(3.0, 0.2, 0.5, 2.0, 7.0, **terms),
    )
    b = (
        full_orbital_omega_squared(30.0, 2.0, 5.0, 2.0, 7.0, **terms),
        radial_epicyclic_omega_squared(30.0, 2.0, 5.0, 2.0, 7.0, **terms),
    )
    assert math.isclose(a[1] - a[0], b[1] - b[0])


def test_inverse_radius_is_exact_radial_harmonic_null():
    w = inverse_radius_nullspace(3.0, offset=8.0, strength=5.0)
    assert abs(w.laplacian_3d) < 1e-15


def test_inverse_radius_orbit_shift_is_source_degenerate():
    radius = 4.0
    mass = 2.0
    lam = 3.0
    base_a = source_amplitude(5.0, 0.4, 0.5)
    null = inverse_radius_nullspace(radius, strength=lam)
    shifted_by_potential = base_a / radius**3 + null.first_derivative / (mass * radius)
    shifted_a = base_a + source_amplitude_shift_from_inverse_radius(lam, mass)
    assert math.isclose(shifted_by_potential, shifted_a / radius**3)


def test_precession_recovers_information_coupling_after_control_subtraction():
    radius = 2.5
    mass = 3.0
    g_i = -0.4
    xi1 = 1.2
    xi2 = 0.7
    control1 = 0.3
    control2 = -0.15
    terms = dict(
        information_gradient=xi1,
        information_hessian=xi2,
        information_coupling=g_i,
        quantum_pressure_gradient=control1,
        quantum_pressure_hessian=control2,
    )
    omega2 = full_orbital_omega_squared(4.0, 0.5, 0.8, radius, mass, **terms)
    kappa2 = radial_epicyclic_omega_squared(4.0, 0.5, 0.8, radius, mass, **terms)
    control_laplacian = control2 + 2.0 * control1 / radius
    got = information_coupling_from_precession(
        omega2, kappa2, mass, radius, xi1, xi2, control_laplacian=control_laplacian
    )
    assert math.isclose(got, g_i)


def test_precession_identifier_fails_closed_on_inverse_radius_xi_null():
    radius = 2.0
    lam = 1.5
    null = inverse_radius_nullspace(radius, strength=lam)
    with pytest.raises(RadialStabilityError):
        information_coupling_from_precession(
            1.0,
            1.0,
            2.0,
            radius,
            null.first_derivative,
            null.second_derivative,
        )


def test_invalid_radius_fails_closed():
    with pytest.raises(RadialStabilityError):
        inverse_radius_nullspace(0.0, strength=1.0)
