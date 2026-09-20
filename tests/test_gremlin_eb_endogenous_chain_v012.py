import math

import pytest

from tools.gremlin_eb_condensate_orbital_phase_bridge_v09 import (
    eb_information_orbital_omega_squared,
    eb_source_strength,
    effective_winding,
    orbital_omega_squared,
    phase_winding_omega,
)
from tools.gremlin_eb_radial_stability_nullspace_v010 import (
    radial_epicyclic_omega_squared,
)
from tools.gremlin_endogenous_eb_condensate_normal_modes_v012 import (
    endogenous_lambda_eb,
    endogenous_radial_stiffness_squared_from_budget,
    endogenous_radial_stiffness_squared_unreduced,
    phase_energy_from_locked_orbit,
    pure_endogenous_radius,
    radial_budget_term,
    stabilization_witness,
)


def test_v09_to_v012_pure_same_carrier_roundtrip_and_external_firewall():
    winding = 3
    gamma_b = math.pi
    q_eff = effective_winding(winding, gamma_b)
    c_mu = 0.4
    eta_g = 0.5
    i_phi = 6.0
    action_scale = 2.0
    mass = 3.0

    radius = pure_endogenous_radius(
        source_coefficient=c_mu,
        eta_g=eta_g,
        phase_inertia=i_phi,
        effective_winding=q_eff,
    )
    omega = phase_winding_omega(
        action_scale,
        mass,
        radius,
        winding=winding,
        berry_holonomy=gamma_b,
    )
    h_eb = phase_energy_from_locked_orbit(i_phi, q_eff, omega)

    omega_balance_sq = eb_information_orbital_omega_squared(
        h_eb,
        c_mu,
        eta_g,
        radius,
        mass,
    )
    assert omega_balance_sq == pytest.approx(omega * omega)
    assert endogenous_lambda_eb(
        radius,
        source_coefficient=c_mu,
        eta_g=eta_g,
        phase_inertia=i_phi,
        effective_winding=q_eff,
    ) == pytest.approx(1.0)

    frozen_source_kappa_sq = radial_epicyclic_omega_squared(
        h_eb,
        c_mu,
        eta_g,
        radius,
        mass,
    )
    endogenous_kappa_sq = endogenous_radial_stiffness_squared_unreduced(
        omega * omega,
        1.0,
        mass,
    )

    assert frozen_source_kappa_sq == pytest.approx(omega * omega)
    assert endogenous_kappa_sq == pytest.approx(-3.0 * omega * omega)


def test_v09_v012_mixed_budget_closes_and_can_be_stabilized():
    q_eff = 2.0
    c_mu = 0.6
    eta_g = 0.7
    i_phi = 5.0
    action_scale = 1.5
    mass = 2.5

    pure_radius = pure_endogenous_radius(
        source_coefficient=c_mu,
        eta_g=eta_g,
        phase_inertia=i_phi,
        effective_winding=q_eff,
    )
    radius = pure_radius * (2.0 ** (1.0 / 3.0))
    omega = action_scale * q_eff / (mass * radius**2)
    omega_sq = omega * omega
    h_eb = phase_energy_from_locked_orbit(i_phi, q_eff, omega)
    lam_eb = endogenous_lambda_eb(
        radius,
        source_coefficient=c_mu,
        eta_g=eta_g,
        phase_inertia=i_phi,
        effective_winding=q_eff,
    )
    assert lam_eb == pytest.approx(0.5)

    lam_rad = 1.0 - lam_eb
    gradient = lam_rad * mass * radius * omega_sq
    mu_source = eb_source_strength(h_eb, c_mu)
    closed_omega_sq = orbital_omega_squared(
        mu_source,
        eta_g,
        radius,
        mass,
        potential_gradient=gradient,
    )
    assert closed_omega_sq == pytest.approx(omega_sq)
    assert radial_budget_term(gradient, radius, mass, omega_sq) == pytest.approx(lam_rad)

    hessian = 4.0 * mass * omega_sq
    kappa_sq = endogenous_radial_stiffness_squared_from_budget(
        omega_sq,
        radius,
        mass,
        gradient,
        hessian,
        lambda_eb=lam_eb,
    )
    witness = stabilization_witness(
        omega_sq,
        radius,
        mass,
        gradient,
        hessian,
    )
    assert kappa_sq > 0.0
    assert witness.stable
