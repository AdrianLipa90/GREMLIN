from __future__ import annotations

from dataclasses import dataclass
import math

from tools.gremlin_eb_condensate_orbital_phase_bridge_v09 import eb_source_strength


SCHEMA = "GREMLIN_EB_RADIAL_STABILITY_AND_NULLSPACE_V0_10"


class RadialStabilityError(ValueError):
    pass


def _finite(value: float, name: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise RadialStabilityError(f"{name} must be finite") from exc
    if not math.isfinite(out):
        raise RadialStabilityError(f"{name} must be finite")
    return out


def _positive(value: float, name: str) -> float:
    out = _finite(value, name)
    if out <= 0.0:
        raise RadialStabilityError(f"{name} must be finite and positive")
    return out


@dataclass(frozen=True)
class RadialDerivativeWitness:
    first_derivative: float
    second_derivative: float
    laplacian_3d: float


def radial_curvature_operator(
    radius: float,
    first_derivative: float,
    second_derivative: float,
) -> float:
    """Radial 3D Laplacian: W'' + 2 W'/r for r > 0."""
    r = _positive(radius, "radius")
    first = _finite(first_derivative, "first_derivative")
    second = _finite(second_derivative, "second_derivative")
    return second + 2.0 * first / r


def total_radial_derivatives(
    radius: float,
    *,
    information_gradient: float = 0.0,
    information_hessian: float = 0.0,
    information_coupling: float = 0.0,
    quantum_pressure_gradient: float = 0.0,
    quantum_pressure_hessian: float = 0.0,
    trap_gradient: float = 0.0,
    trap_hessian: float = 0.0,
    interaction_gradient: float = 0.0,
    interaction_hessian: float = 0.0,
) -> RadialDerivativeWitness:
    """Keep U_I, Q_rho, trap and interaction contributions explicit."""
    r = _positive(radius, "radius")
    g_i = _finite(information_coupling, "information_coupling")
    first = (
        g_i * _finite(information_gradient, "information_gradient")
        + _finite(quantum_pressure_gradient, "quantum_pressure_gradient")
        + _finite(trap_gradient, "trap_gradient")
        + _finite(interaction_gradient, "interaction_gradient")
    )
    second = (
        g_i * _finite(information_hessian, "information_hessian")
        + _finite(quantum_pressure_hessian, "quantum_pressure_hessian")
        + _finite(trap_hessian, "trap_hessian")
        + _finite(interaction_hessian, "interaction_hessian")
    )
    return RadialDerivativeWitness(
        first_derivative=first,
        second_derivative=second,
        laplacian_3d=radial_curvature_operator(r, first, second),
    )


def source_amplitude(
    hamiltonian_eb: float,
    source_coefficient: float,
    eta_g: float,
) -> float:
    """A_G = C_mu H_Phi^EB eta_G."""
    eta = _positive(eta_g, "eta_g")
    return eb_source_strength(hamiltonian_eb, source_coefficient) * eta


def full_orbital_omega_squared(
    hamiltonian_eb: float,
    source_coefficient: float,
    eta_g: float,
    radius: float,
    inertial_mass: float,
    **radial_terms: float,
) -> float:
    """Omega^2 = A_G/r^3 + W'/(m_I r)."""
    r = _positive(radius, "radius")
    mass = _positive(inertial_mass, "inertial_mass")
    deriv = total_radial_derivatives(r, **radial_terms)
    return source_amplitude(hamiltonian_eb, source_coefficient, eta_g) / r**3 + deriv.first_derivative / (mass * r)


def radial_epicyclic_omega_squared(
    hamiltonian_eb: float,
    source_coefficient: float,
    eta_g: float,
    radius: float,
    inertial_mass: float,
    **radial_terms: float,
) -> float:
    """kappa_r^2 = A_G/r^3 + (W'' + 3 W'/r)/m_I."""
    r = _positive(radius, "radius")
    mass = _positive(inertial_mass, "inertial_mass")
    deriv = total_radial_derivatives(r, **radial_terms)
    return (
        source_amplitude(hamiltonian_eb, source_coefficient, eta_g) / r**3
        + (deriv.second_derivative + 3.0 * deriv.first_derivative / r) / mass
    )


def total_curvature_from_precession(
    orbital_omega_squared: float,
    epicyclic_omega_squared: float,
    inertial_mass: float,
) -> float:
    """Recover Delta_3 W = m_I (kappa_r^2 - Omega^2)."""
    omega2 = _finite(orbital_omega_squared, "orbital_omega_squared")
    kappa2 = _finite(epicyclic_omega_squared, "epicyclic_omega_squared")
    mass = _positive(inertial_mass, "inertial_mass")
    return mass * (kappa2 - omega2)


def information_coupling_from_precession(
    orbital_omega_squared: float,
    epicyclic_omega_squared: float,
    inertial_mass: float,
    radius: float,
    xi_gradient: float,
    xi_hessian: float,
    *,
    control_laplacian: float = 0.0,
    zero_tol: float = 1e-15,
) -> float:
    """Recover g_I after explicitly subtracting non-informational radial controls."""
    _positive(radius, "radius")
    total = total_curvature_from_precession(
        orbital_omega_squared, epicyclic_omega_squared, inertial_mass
    )
    controls = _finite(control_laplacian, "control_laplacian")
    xi_laplacian = radial_curvature_operator(radius, xi_gradient, xi_hessian)
    tol = _positive(zero_tol, "zero_tol")
    if abs(xi_laplacian) <= tol:
        raise RadialStabilityError(
            "information radial Laplacian is zero/degenerate; precession cannot identify g_I"
        )
    return (total - controls) / xi_laplacian


@dataclass(frozen=True)
class InverseRadiusNullspaceWitness:
    potential: float
    first_derivative: float
    second_derivative: float
    laplacian_3d: float


def inverse_radius_nullspace(
    radius: float,
    *,
    offset: float = 0.0,
    strength: float,
) -> InverseRadiusNullspaceWitness:
    """U(r)=u0-lambda/r, the radial harmonic null outside the source."""
    r = _positive(radius, "radius")
    u0 = _finite(offset, "offset")
    lam = _finite(strength, "strength")
    potential = u0 - lam / r
    first = lam / r**2
    second = -2.0 * lam / r**3
    return InverseRadiusNullspaceWitness(
        potential=potential,
        first_derivative=first,
        second_derivative=second,
        laplacian_3d=radial_curvature_operator(r, first, second),
    )


def source_amplitude_shift_from_inverse_radius(
    strength: float,
    inertial_mass: float,
) -> float:
    """-lambda/r contributes exactly like A_G -> A_G + lambda/m_I."""
    lam = _finite(strength, "strength")
    mass = _positive(inertial_mass, "inertial_mass")
    return lam / mass
