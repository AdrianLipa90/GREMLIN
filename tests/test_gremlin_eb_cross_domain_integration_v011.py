import math

import pytest

from tools.gremlin_eb_condensate_orbital_phase_bridge_v09 import (
    effective_winding,
    information_potential_gradient,
)
from tools.gremlin_eb_radial_stability_nullspace_v010 import (
    full_orbital_omega_squared,
    information_coupling_from_precession,
    inverse_radius_nullspace,
    radial_epicyclic_omega_squared,
)
from tools.gremlin_cross_domain_coupling_identifiability_v011 import (
    CrossDomainIdentifiabilityError,
    berry_holonomy_from_independent_circulation,
    beta_g_from_orbital_subtraction,
    optical_coupling_from_hessians,
    projected_inverse_radius_phase_hessian_eigenvalues,
    resolve_cross_domain_information_coupling,
    resolve_source_coupling_factorization,
)


def test_v09_v10_v11_synthetic_information_coupling_roundtrip():
    radius = 3.0
    mass = 2.0
    g_i = 0.4
    xi1 = 1.25
    xi2 = -0.15
    q1 = 0.08
    q2 = -0.03
    trap1 = -0.05
    trap2 = 0.02

    assert math.isclose(
        information_potential_gradient(xi1, alpha_i=2.0, kappa_e=5.0),
        g_i * xi1,
    )

    terms = dict(
        information_gradient=xi1,
        information_hessian=xi2,
        information_coupling=g_i,
        quantum_pressure_gradient=q1,
        quantum_pressure_hessian=q2,
        trap_gradient=trap1,
        trap_hessian=trap2,
    )
    omega2 = full_orbital_omega_squared(
        7.0, 0.3, 0.6, radius, mass, **terms
    )
    kappa2 = radial_epicyclic_omega_squared(
        7.0, 0.3, 0.6, radius, mass, **terms
    )
    control_laplacian = (q2 + trap2) + 2.0 * (q1 + trap1) / radius

    g_prec = information_coupling_from_precession(
        omega2,
        kappa2,
        mass,
        radius,
        xi1,
        xi2,
        control_laplacian=control_laplacian,
    )

    h_xi = ((2.0, 0.5), (0.5, -1.0))
    chi = 1.75
    h_phi = tuple(tuple(-chi * g_i * x for x in row) for row in h_xi)
    g_opt = optical_coupling_from_hessians(h_phi, h_xi, chi_phi=chi)

    witness = resolve_cross_domain_information_coupling(
        {"precession": g_prec, "optics": g_opt}
    )
    assert witness.admitted
    assert math.isclose(witness.coupling, g_i)


def test_inverse_radius_is_precession_null_but_optically_visible():
    radius = 4.0
    lam = 2.5
    null = inverse_radius_nullspace(radius, strength=lam)
    assert abs(null.laplacian_3d) < 1e-15

    radial, tangential = projected_inverse_radius_phase_hessian_eigenvalues(
        lam, impact_parameter=radius, chi_phi=3.0
    )
    assert math.isclose(radial + tangential, 0.0)
    assert not math.isclose(radial - tangential, 0.0)


def test_beta_recovery_then_factorization_remains_fail_closed():
    radius = 2.0
    h_eb = 5.0
    mass = 4.0
    beta = 0.72
    g_i = 0.3
    xi1 = 1.4
    controls = -0.2

    omega2 = beta * h_eb / radius**3 + (g_i * xi1 + controls) / (mass * radius)
    recovered = beta_g_from_orbital_subtraction(
        omega2,
        radius,
        h_eb,
        mass,
        g_i,
        xi1,
        control_gradient=controls,
    )
    assert math.isclose(recovered, beta)

    with pytest.raises(CrossDomainIdentifiabilityError):
        resolve_source_coupling_factorization(recovered)

    resolved = resolve_source_coupling_factorization(
        recovered,
        eta_g=0.8,
        eta_g_receipt_id="ETA-INDEPENDENT-TEST",
    )
    assert math.isclose(resolved.c_mu, 0.9)
    assert math.isclose(resolved.c_mu * resolved.eta_g, beta)


def test_independent_circulation_reconstructs_v09_effective_winding():
    eta_phi = 2.0
    mass = 3.0
    winding = 4
    gamma_target = 0.75
    circulation = (eta_phi / mass) * (2.0 * math.pi * winding - gamma_target)

    gamma = berry_holonomy_from_independent_circulation(
        circulation,
        mass,
        eta_phi,
        winding=winding,
        circulation_receipt_id="INDEPENDENT-LOOP-TEST",
    )
    assert math.isclose(gamma, gamma_target)

    q = effective_winding(winding, gamma)
    assert math.isclose(q, winding - gamma_target / (2.0 * math.pi))
