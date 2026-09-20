from __future__ import annotations

import math


TWO_PI = 2.0 * math.pi


def _finite(name: str, value: float) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise ValueError(f"{name} must be finite")
    return x


def _positive(name: str, value: float) -> float:
    x = _finite(name, value)
    if x <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return x


def effective_winding(winding: int, berry_holonomy: float = 0.0) -> float:
    """Mechanical phase winding q_eff = n - gamma_B/(2*pi).

    Sign convention: the mechanical momentum is grad(S) - A_B and
    gamma_B = integral(A_B . dl) / action_scale.
    """
    if isinstance(winding, bool) or not isinstance(winding, int):
        raise ValueError("winding must be an integer")
    gamma = _finite("berry_holonomy", berry_holonomy)
    return float(winding) - gamma / TWO_PI


def phase_winding_omega(
    action_scale: float,
    inertial_mass: float,
    radius: float,
    *,
    winding: int,
    berry_holonomy: float = 0.0,
) -> float:
    """Azimuthal angular rate from a typed phase winding.

    For S = action_scale*n*theta and an admitted U(1) connection,
    v_theta = action_scale*q_eff/(m*r) and omega = v_theta/r.
    """
    eta = _positive("action_scale", action_scale)
    mass = _positive("inertial_mass", inertial_mass)
    r = _positive("radius", radius)
    q = effective_winding(winding, berry_holonomy)
    return eta * q / (mass * r * r)


def eb_source_strength(hamiltonian_eb: float, source_coefficient: float) -> float:
    """Conditional composition mu_source = C_mu * H_Phi^EB.

    RF-S22 supplies E_G = H_Phi^EB on its admitted matched-H branch.
    GREMLIN v0.8 supplies mu_source = C_mu * E_Sigma with C_mu explicit.
    """
    h = _positive("hamiltonian_eb", hamiltonian_eb)
    c_mu = _positive("source_coefficient", source_coefficient)
    return c_mu * h


def information_potential_gradient(
    xi_gradient: float,
    *,
    alpha_i: float,
    kappa_e: float,
) -> float:
    """dU_I/dr = (alpha_I/kappa_E) dXi_I/dr."""
    grad = _finite("xi_gradient", xi_gradient)
    alpha = _finite("alpha_i", alpha_i)
    kappa = _finite("kappa_e", kappa_e)
    if kappa == 0.0:
        raise ValueError("kappa_e must be non-zero")
    return (alpha / kappa) * grad


def orbital_omega_squared(
    mu_source: float,
    eta_g: float,
    radius: float,
    inertial_mass: float,
    *,
    potential_gradient: float = 0.0,
) -> float:
    """Conditional circular-orbit balance.

    omega^2 = mu_source*eta_G/r^3 + (1/(m_I*r))*dU_extra/dr.

    eta_G is the already role-separated q_coupling/m_inertial coordinate.
    """
    mu = _positive("mu_source", mu_source)
    coupling = _positive("eta_g", eta_g)
    r = _positive("radius", radius)
    mass = _positive("inertial_mass", inertial_mass)
    du = _finite("potential_gradient", potential_gradient)
    return mu * coupling / (r**3) + du / (mass * r)


def eb_information_orbital_omega_squared(
    hamiltonian_eb: float,
    source_coefficient: float,
    eta_g: float,
    radius: float,
    inertial_mass: float,
    *,
    xi_gradient: float = 0.0,
    alpha_i: float = 0.0,
    kappa_e: float = 1.0,
) -> float:
    """Compose RFC EB source closure, GREMLIN orbital kernel and U_I gradient."""
    mu = eb_source_strength(hamiltonian_eb, source_coefficient)
    du = information_potential_gradient(
        xi_gradient,
        alpha_i=alpha_i,
        kappa_e=kappa_e,
    )
    return orbital_omega_squared(
        mu,
        eta_g,
        radius,
        inertial_mass,
        potential_gradient=du,
    )


def pure_source_radius_from_winding(
    action_scale: float,
    inertial_mass: float,
    hamiltonian_eb: float,
    source_coefficient: float,
    eta_g: float,
    *,
    winding: int,
    berry_holonomy: float = 0.0,
) -> float:
    """Radius solving phase-winding omega == pure Kepler source omega.

    This excludes an extra informational-potential gradient.  It is therefore a
    conditional algebraic branch, not a universal orbital quantisation claim.
    """
    eta = _positive("action_scale", action_scale)
    mass = _positive("inertial_mass", inertial_mass)
    mu = eb_source_strength(hamiltonian_eb, source_coefficient)
    coupling = _positive("eta_g", eta_g)
    q = effective_winding(winding, berry_holonomy)
    if q == 0.0:
        raise ValueError("effective winding must be non-zero")
    return eta * eta * q * q / (mass * mass * mu * coupling)


def eb_orbital_closure_residual(
    action_scale: float,
    inertial_mass: float,
    radius: float,
    hamiltonian_eb: float,
    source_coefficient: float,
    eta_g: float,
    *,
    winding: int,
    berry_holonomy: float = 0.0,
    xi_gradient: float = 0.0,
    alpha_i: float = 0.0,
    kappa_e: float = 1.0,
) -> float:
    """Return winding omega^2 minus source+information circular-balance omega^2."""
    omega_phase = phase_winding_omega(
        action_scale,
        inertial_mass,
        radius,
        winding=winding,
        berry_holonomy=berry_holonomy,
    )
    omega_balance_sq = eb_information_orbital_omega_squared(
        hamiltonian_eb,
        source_coefficient,
        eta_g,
        radius,
        inertial_mass,
        xi_gradient=xi_gradient,
        alpha_i=alpha_i,
        kappa_e=kappa_e,
    )
    return omega_phase * omega_phase - omega_balance_sq


def condensate_quantum_pressure(
    sqrt_density: float,
    laplacian_sqrt_density: float,
    *,
    action_scale: float,
    inertial_mass: float,
) -> float:
    """Standard Madelung/Bohm quantum-pressure coordinate.

    Q = -(eta^2/(2m)) * (Delta sqrt(rho))/sqrt(rho).

    The caller owns the spatial Laplacian and density provenance.
    """
    amp = _positive("sqrt_density", sqrt_density)
    lap = _finite("laplacian_sqrt_density", laplacian_sqrt_density)
    eta = _positive("action_scale", action_scale)
    mass = _positive("inertial_mass", inertial_mass)
    return -(eta * eta / (2.0 * mass)) * (lap / amp)
