"""GREMLIN radial-medium identifiability diagnostics v0.1.

Pure algebraic diagnostics for stationary central scalar models. These helpers do
not assign a measured residual to an information, holonomy, condensate, or
gravitational source.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


class RadialIdentifiabilityError(ValueError):
    pass


def _finite(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise RadialIdentifiabilityError(f"{name} must be finite")
    return value


def _positive(name: str, value: float) -> float:
    value = _finite(name, value)
    if value <= 0.0:
        raise RadialIdentifiabilityError(f"{name} must be > 0")
    return value


@dataclass(frozen=True)
class RadialDiagnostic:
    radius: float
    omega_sq: float
    kappa_sq: float

    @property
    def k_obs(self) -> float:
        r = _positive("radius", self.radius)
        return r**3 * _finite("omega_sq", self.omega_sq)

    @property
    def non_kepler_indicator(self) -> float:
        r = _positive("radius", self.radius)
        return r**2 * (
            _finite("kappa_sq", self.kappa_sq)
            - _finite("omega_sq", self.omega_sq)
        )


def epicyclic_prediction(
    radius: float, omega_sq: float, d_omega_sq_dr: float
) -> float:
    r = _positive("radius", radius)
    return 4.0 * _finite("omega_sq", omega_sq) + r * _finite(
        "d_omega_sq_dr", d_omega_sq_dr
    )


def central_consistency_residual(
    radius: float,
    omega_sq: float,
    d_omega_sq_dr: float,
    measured_kappa_sq: float,
) -> float:
    return _finite("measured_kappa_sq", measured_kappa_sq) - epicyclic_prediction(
        radius, omega_sq, d_omega_sq_dr
    )


def k_obs_gradient_from_epicycle(
    radius: float, omega_sq: float, kappa_sq: float
) -> float:
    r = _positive("radius", radius)
    return r**2 * (
        _finite("kappa_sq", kappa_sq) - _finite("omega_sq", omega_sq)
    )


def precession_per_orbit(omega_sq: float, kappa_sq: float) -> float:
    w2 = _positive("omega_sq", omega_sq)
    k2 = _positive("kappa_sq", kappa_sq)
    return 2.0 * math.pi * (math.sqrt(w2 / k2) - 1.0)


def near_kepler_precession_from_log_k_slope(log_k_slope: float) -> float:
    return -math.pi * _finite("log_k_slope", log_k_slope)


def holonomy_shell_susceptibility_tau(
    radius: float,
    circulation_scale: float,
    effective_winding: float,
    kappa_sq: float,
) -> float:
    r = _positive("radius", radius)
    lam = _positive("circulation_scale", circulation_scale)
    nu = _finite("effective_winding", effective_winding)
    k2 = _finite("kappa_sq", kappa_sq)
    if k2 == 0.0:
        raise RadialIdentifiabilityError("kappa_sq must be non-zero")
    return -(lam * lam * nu) / (math.pi * r**3 * k2)


def condensate_subtracted_residual(
    radius: float,
    omega_sq: float,
    *,
    k_orb: float,
    mobility: float,
    coupling_g: float,
    density_gradient: float,
    quantum_density_gradient: float,
) -> float:
    r = _positive("radius", radius)
    m = _positive("mobility", mobility)
    return (
        r * _finite("omega_sq", omega_sq)
        - _finite("k_orb", k_orb) / r**2
        - 2.0
        * m
        * _finite("coupling_g", coupling_g)
        * _finite("density_gradient", density_gradient)
        + 2.0
        * m
        * m
        * _finite("quantum_density_gradient", quantum_density_gradient)
    )


def candidate_information_holonomy_residual(
    g_residual: float,
    mobility: float,
) -> float:
    """Return the residual normalized as G_res/(2 M).

    The result is intentionally source-neutral. A later caller may compare it
    against independently constrained candidate terms such as
    c_I Xi_I' - J' cos(epsilon) + J sin(epsilon) epsilon'.
    """

    m = _positive("mobility", mobility)
    return _finite("g_residual", g_residual) / (2.0 * m)


def is_kepler_camouflage_potential(
    *,
    c0: float,
    c1: float,
    radius: float,
) -> tuple[float, float]:
    """Return (delta_phi, delta_omega_sq) for C0 + C1/r.

    This exposes the exact r^-3 orbital correction while keeping the function
    free of source attribution.
    """

    r = _positive("radius", radius)
    return (
        _finite("c0", c0) + _finite("c1", c1) / r,
        -_finite("c1", c1) / r**3,
    )
