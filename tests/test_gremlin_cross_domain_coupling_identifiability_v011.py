import math
import pytest

from tools.gremlin_cross_domain_coupling_identifiability_v011 import (
    CrossDomainIdentifiabilityError,
    berry_holonomy_from_independent_circulation,
    beta_g_from_orbital_subtraction,
    factorization_rank_witness,
    optical_coupling_from_hessians,
    projected_inverse_radius_phase_hessian_eigenvalues,
    resolve_constant_beta_g,
    resolve_cross_domain_information_coupling,
    resolve_source_coupling_factorization,
    spectroscopic_coupling_from_shift,
)


def test_optical_hessian_recovers_information_coupling():
    g_i = 0.375
    chi = 2.0
    h_xi = ((2.0, -1.0), (-1.0, 3.0))
    h_phi = tuple(tuple(-chi * g_i * x for x in row) for row in h_xi)
    assert math.isclose(
        optical_coupling_from_hessians(h_phi, h_xi, chi_phi=chi),
        g_i,
    )


def test_inverse_radius_is_visible_as_shear_even_with_zero_trace():
    radial, tangential = projected_inverse_radius_phase_hessian_eigenvalues(
        3.0, 2.0, chi_phi=5.0
    )
    assert radial != 0.0
    assert math.isclose(radial + tangential, 0.0)
    assert not math.isclose(radial - tangential, 0.0)


def test_common_mode_spectroscopy_fails_closed():
    with pytest.raises(CrossDomainIdentifiabilityError):
        spectroscopic_coupling_from_shift(1.0, 0.0)


def test_independent_cross_domain_estimates_must_agree_without_refitting():
    w = resolve_cross_domain_information_coupling(
        {"precession": 0.25, "optics": 0.25, "spectroscopy": 0.25}
    )
    assert w.admitted
    assert w.coupling == 0.25
    with pytest.raises(CrossDomainIdentifiabilityError):
        resolve_cross_domain_information_coupling(
            {"precession": 0.25, "optics": 0.30}
        )


def test_beta_g_is_recovered_after_information_and_control_subtraction():
    r = 2.0
    h = 5.0
    mass = 4.0
    beta = 0.6
    g_i = 0.25
    xi1 = 3.0
    control1 = -0.5
    omega2 = beta * h / r**3 + (g_i * xi1 + control1) / (mass * r)
    got = beta_g_from_orbital_subtraction(
        omega2, r, h, mass, g_i, xi1, control_gradient=control1
    )
    assert math.isclose(got, beta)


def test_beta_g_must_be_constant_across_independent_points():
    w = resolve_constant_beta_g({"r1": 0.6, "r2": 0.6, "r3": 0.6})
    assert w.admitted and w.beta_g == 0.6
    with pytest.raises(CrossDomainIdentifiabilityError):
        resolve_constant_beta_g({"r1": 0.6, "r2": 0.7})


def test_c_mu_eta_g_jacobian_has_exact_rank_one():
    w = factorization_rank_witness(5.0, 0.4, 0.8, [1.0, 2.0, 3.0])
    assert w.rank == 1
    for a, b in zip(w.d_omega2_d_c_mu, w.d_omega2_d_eta_g):
        assert math.isclose(b, w.proportionality * a)


def test_factorization_requires_independent_receipt():
    with pytest.raises(CrossDomainIdentifiabilityError):
        resolve_source_coupling_factorization(0.6)
    w = resolve_source_coupling_factorization(
        0.6, eta_g=0.75, eta_g_receipt_id="ETA-INDEPENDENT-001"
    )
    assert math.isclose(w.c_mu, 0.8)
    assert math.isclose(w.c_mu * w.eta_g, 0.6)


def test_berry_holonomy_requires_independent_circulation_receipt():
    with pytest.raises(CrossDomainIdentifiabilityError):
        berry_holonomy_from_independent_circulation(
            2.0, 3.0, 4.0, winding=1, circulation_receipt_id=""
        )
    gamma = berry_holonomy_from_independent_circulation(
        2.0, 3.0, 4.0, winding=1, circulation_receipt_id="PHASE-LOOP-001"
    )
    assert math.isclose(gamma, 2.0 * math.pi - 1.5)
