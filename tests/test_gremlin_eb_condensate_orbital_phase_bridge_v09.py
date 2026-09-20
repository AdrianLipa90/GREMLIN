import math

import pytest

from tools.gremlin_eb_condensate_orbital_phase_bridge_v09 import (
    condensate_quantum_pressure,
    eb_information_orbital_omega_squared,
    eb_orbital_closure_residual,
    eb_source_strength,
    effective_winding,
    information_potential_gradient,
    phase_winding_omega,
    pure_source_radius_from_winding,
)


def test_rfs22_plus_v08_composes_to_eb_source_strength():
    assert eb_source_strength(4.0, 2.5) == 10.0


def test_berry_holonomy_shifts_mechanical_winding():
    q = effective_winding(3, math.pi)
    assert math.isclose(q, 2.5)


def test_phase_winding_rate_scales_as_inverse_radius_squared():
    a = phase_winding_omega(2.0, 4.0, 3.0, winding=2)
    b = phase_winding_omega(2.0, 4.0, 6.0, winding=2)
    assert math.isclose(b, a / 4.0)


def test_information_gradient_composes_into_orbital_balance():
    got = eb_information_orbital_omega_squared(
        4.0,
        2.0,
        0.5,
        2.0,
        4.0,
        xi_gradient=3.0,
        alpha_i=2.0,
        kappa_e=4.0,
    )
    expected_source = (8.0 * 0.5) / 8.0
    expected_info = ((2.0 / 4.0) * 3.0) / (4.0 * 2.0)
    assert math.isclose(got, expected_source + expected_info)


def test_pure_source_radius_closes_phase_and_kepler_branches():
    kwargs = dict(
        action_scale=2.0,
        inertial_mass=3.0,
        hamiltonian_eb=5.0,
        source_coefficient=0.4,
        eta_g=0.5,
        winding=2,
        berry_holonomy=0.0,
    )
    radius = pure_source_radius_from_winding(**kwargs)
    residual = eb_orbital_closure_residual(radius=radius, **kwargs)
    assert abs(residual) < 1e-12


def test_zero_information_gradient_reduces_to_eb_kepler_source():
    mu = eb_source_strength(9.0, 0.25)
    got = eb_information_orbital_omega_squared(
        9.0, 0.25, 2.0, 3.0, 5.0
    )
    assert math.isclose(got, mu * 2.0 / 27.0)


def test_quantum_pressure_flat_amplitude_is_zero():
    assert condensate_quantum_pressure(
        2.0,
        0.0,
        action_scale=3.0,
        inertial_mass=4.0,
    ) == 0.0


def test_invalid_domains_fail_closed():
    with pytest.raises(ValueError):
        eb_source_strength(0.0, 1.0)
    with pytest.raises(ValueError):
        pure_source_radius_from_winding(
            1.0, 1.0, 1.0, 1.0, 1.0, winding=0
        )
    with pytest.raises(ValueError):
        information_potential_gradient(1.0, alpha_i=1.0, kappa_e=0.0)
