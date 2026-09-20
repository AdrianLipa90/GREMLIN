from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

import numpy as np

from tools.gremlin_radial_medium_identifiability_v01 import central_consistency_residual

SCHEMA = "GREMLIN_ENDOGENOUS_EB_CONDENSATE_NORMAL_MODES_V0_12"


class EndogenousEBNormalModeError(ValueError):
    pass


def _finite(value: float, name: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise EndogenousEBNormalModeError(f"{name} must be finite") from exc
    if not math.isfinite(out):
        raise EndogenousEBNormalModeError(f"{name} must be finite")
    return out


def _positive(value: float, name: str) -> float:
    out = _finite(value, name)
    if out <= 0.0:
        raise EndogenousEBNormalModeError(f"{name} must be finite and positive")
    return out


def _nonzero(value: float, name: str) -> float:
    out = _finite(value, name)
    if out == 0.0:
        raise EndogenousEBNormalModeError(f"{name} must be non-zero")
    return out


def endogenous_lambda_eb(
    radius: float,
    *,
    source_coefficient: float,
    eta_g: float,
    phase_inertia: float,
    effective_winding: float,
    clock_factor: float = 1.0,
) -> float:
    r = _positive(radius, "radius")
    c_mu = _positive(source_coefficient, "source_coefficient")
    eta = _positive(eta_g, "eta_g")
    inertia = _positive(phase_inertia, "phase_inertia")
    q = _nonzero(effective_winding, "effective_winding")
    zeta = _nonzero(clock_factor, "clock_factor")
    return 0.5 * c_mu * eta * inertia * (q * zeta) ** 2 / r**3


def pure_endogenous_radius(
    *,
    source_coefficient: float,
    eta_g: float,
    phase_inertia: float,
    effective_winding: float,
    clock_factor: float = 1.0,
) -> float:
    c_mu = _positive(source_coefficient, "source_coefficient")
    eta = _positive(eta_g, "eta_g")
    inertia = _positive(phase_inertia, "phase_inertia")
    q = _nonzero(effective_winding, "effective_winding")
    zeta = _nonzero(clock_factor, "clock_factor")
    return (0.5 * c_mu * eta * inertia * (q * zeta) ** 2) ** (1.0 / 3.0)


def winding_omega(
    action_scale: float,
    inertial_mass: float,
    radius: float,
    effective_winding: float,
) -> float:
    eta_phi = _positive(action_scale, "action_scale")
    mass = _positive(inertial_mass, "inertial_mass")
    r = _positive(radius, "radius")
    q = _nonzero(effective_winding, "effective_winding")
    return eta_phi * q / (mass * r**2)


def phase_energy_from_locked_orbit(
    phase_inertia: float,
    effective_winding: float,
    omega: float,
    *,
    clock_factor: float = 1.0,
) -> float:
    inertia = _positive(phase_inertia, "phase_inertia")
    q = _nonzero(effective_winding, "effective_winding")
    w = _finite(omega, "omega")
    zeta = _nonzero(clock_factor, "clock_factor")
    return 0.5 * inertia * (q * zeta * w) ** 2


def radial_budget_term(
    radial_gradient: float,
    radius: float,
    inertial_mass: float,
    omega_squared: float,
) -> float:
    grad = _finite(radial_gradient, "radial_gradient")
    r = _positive(radius, "radius")
    mass = _positive(inertial_mass, "inertial_mass")
    omega2 = _positive(omega_squared, "omega_squared")
    return grad / (mass * r * omega2)


@dataclass(frozen=True)
class BudgetClosureWitness:
    lambda_eb: float
    radial_terms: tuple[float, ...]
    total: float
    residual: float
    closed: bool


def budget_closure(
    lambda_eb: float,
    radial_terms: Iterable[float] = (),
    *,
    tolerance: float = 1e-10,
) -> BudgetClosureWitness:
    lam = _finite(lambda_eb, "lambda_eb")
    terms = tuple(_finite(x, f"radial_terms[{i}]") for i, x in enumerate(radial_terms))
    tol = _positive(tolerance, "tolerance")
    total = lam + sum(terms)
    residual = 1.0 - total
    return BudgetClosureWitness(lam, terms, total, residual, abs(residual) <= tol)


def endogenous_radial_stiffness_squared_unreduced(
    omega_squared: float,
    lambda_eb: float,
    inertial_mass: float,
    radial_hessian: float = 0.0,
) -> float:
    omega2 = _positive(omega_squared, "omega_squared")
    lam = _finite(lambda_eb, "lambda_eb")
    mass = _positive(inertial_mass, "inertial_mass")
    hess = _finite(radial_hessian, "radial_hessian")
    return (3.0 - 6.0 * lam) * omega2 + hess / mass


def endogenous_radial_stiffness_squared_from_budget(
    omega_squared: float,
    radius: float,
    inertial_mass: float,
    radial_gradient: float,
    radial_hessian: float,
    *,
    lambda_eb: float,
    closure_tolerance: float = 1e-10,
) -> float:
    omega2 = _positive(omega_squared, "omega_squared")
    r = _positive(radius, "radius")
    mass = _positive(inertial_mass, "inertial_mass")
    grad = _finite(radial_gradient, "radial_gradient")
    hess = _finite(radial_hessian, "radial_hessian")
    lam_rad = radial_budget_term(grad, r, mass, omega2)
    closure = budget_closure(lambda_eb, [lam_rad], tolerance=closure_tolerance)
    if not closure.closed:
        raise EndogenousEBNormalModeError(
            f"endogenous equilibrium budget does not close: residual={closure.residual}"
        )
    return -3.0 * omega2 + (hess + 6.0 * grad / r) / mass


@dataclass(frozen=True)
class StabilizationWitness:
    support: float
    threshold: float
    kappa_squared_over_omega_squared: float
    stable: bool


def stabilization_witness(
    omega_squared: float,
    radius: float,
    inertial_mass: float,
    radial_gradient: float,
    radial_hessian: float,
) -> StabilizationWitness:
    omega2 = _positive(omega_squared, "omega_squared")
    r = _positive(radius, "radius")
    mass = _positive(inertial_mass, "inertial_mass")
    grad = _finite(radial_gradient, "radial_gradient")
    hess = _finite(radial_hessian, "radial_hessian")
    support = (hess + 6.0 * grad / r) / (mass * omega2)
    score = support - 3.0
    return StabilizationWitness(support, 3.0, score, score > 0.0)


def pure_endogenous_stationary_central_residual(
    radius: float,
    omega_squared: float,
) -> float:
    r = _positive(radius, "radius")
    omega2 = _positive(omega_squared, "omega_squared")
    # On the pure same-carrier endogenous branch the source force scales as r^-6,
    # so the circular-family law is Omega^2 ~ r^-7.  The winding law Omega~r^-2
    # is the fixed-q trajectory constraint, not the derivative to insert into the
    # stationary-central epicyclic identity.
    derivative = -7.0 * omega2 / r
    endogenous_kappa2 = -3.0 * omega2
    return central_consistency_residual(r, omega2, derivative, endogenous_kappa2)


def source_acceleration_phase_rate_sensitivity(
    radius: float,
    source_coefficient: float,
    eta_g: float,
    phase_inertia: float,
    phase_rate: float,
) -> float:
    r = _positive(radius, "radius")
    c_mu = _positive(source_coefficient, "source_coefficient")
    eta = _positive(eta_g, "eta_g")
    inertia = _positive(phase_inertia, "phase_inertia")
    rate = _finite(phase_rate, "phase_rate")
    return -c_mu * eta * inertia * rate / r**2


def relative_phase_inertia(
    phase_inertia: float,
    orbital_inertia: float,
    effective_winding: float,
) -> float:
    i_phi = _positive(phase_inertia, "phase_inertia")
    j_theta = _positive(orbital_inertia, "orbital_inertia")
    q = _finite(effective_winding, "effective_winding")
    return i_phi * j_theta / (j_theta + q * q * i_phi)


def relative_phase_frequency_squared(
    lock_stiffness: float,
    phase_inertia: float,
    orbital_inertia: float,
    effective_winding: float,
) -> float:
    stiffness = _finite(lock_stiffness, "lock_stiffness")
    if stiffness < 0.0:
        raise EndogenousEBNormalModeError("lock_stiffness must be non-negative")
    i_rel = relative_phase_inertia(phase_inertia, orbital_inertia, effective_winding)
    return stiffness / i_rel


@dataclass(frozen=True)
class CollectiveMatrices:
    mass: np.ndarray
    gyroscopic: np.ndarray
    stiffness: np.ndarray


def collective_matrices_3x3(
    *,
    radial_mass: float,
    density_mass: float,
    relative_phase_mass: float,
    k_rr: float,
    k_rho_rho: float,
    k_psi_psi: float,
    k_r_rho: float = 0.0,
    k_r_psi: float = 0.0,
    k_rho_psi: float = 0.0,
    g_r_rho: float = 0.0,
    g_r_psi: float = 0.0,
    g_rho_psi: float = 0.0,
) -> CollectiveMatrices:
    masses = [
        _positive(radial_mass, "radial_mass"),
        _positive(density_mass, "density_mass"),
        _positive(relative_phase_mass, "relative_phase_mass"),
    ]
    vals = {
        "k_rr": k_rr,
        "k_rho_rho": k_rho_rho,
        "k_psi_psi": k_psi_psi,
        "k_r_rho": k_r_rho,
        "k_r_psi": k_r_psi,
        "k_rho_psi": k_rho_psi,
        "g_r_rho": g_r_rho,
        "g_r_psi": g_r_psi,
        "g_rho_psi": g_rho_psi,
    }
    v = {name: _finite(value, name) for name, value in vals.items()}
    mass = np.diag(masses).astype(float)
    stiffness = np.array(
        [
            [v["k_rr"], v["k_r_rho"], v["k_r_psi"]],
            [v["k_r_rho"], v["k_rho_rho"], v["k_rho_psi"]],
            [v["k_r_psi"], v["k_rho_psi"], v["k_psi_psi"]],
        ],
        dtype=float,
    )
    gyroscopic = np.array(
        [
            [0.0, v["g_r_rho"], v["g_r_psi"]],
            [-v["g_r_rho"], 0.0, v["g_rho_psi"]],
            [-v["g_r_psi"], -v["g_rho_psi"], 0.0],
        ],
        dtype=float,
    )
    return CollectiveMatrices(mass, gyroscopic, stiffness)


@dataclass(frozen=True)
class CollectiveSpectrum:
    eigenvalues: tuple[complex, ...]
    positive_frequencies: tuple[float, ...]
    max_growth_rate: float
    stable: bool


def collective_mode_spectrum(
    matrices: CollectiveMatrices,
    *,
    stability_tolerance: float = 1e-10,
) -> CollectiveSpectrum:
    tol = _positive(stability_tolerance, "stability_tolerance")
    m = np.asarray(matrices.mass, dtype=float)
    g = np.asarray(matrices.gyroscopic, dtype=float)
    k = np.asarray(matrices.stiffness, dtype=float)
    for name, arr in (("mass", m), ("gyroscopic", g), ("stiffness", k)):
        if arr.shape != (3, 3) or not np.isfinite(arr).all():
            raise EndogenousEBNormalModeError(f"{name} matrix must be finite 3x3")
    if not np.allclose(m, m.T, atol=tol, rtol=0.0):
        raise EndogenousEBNormalModeError("mass matrix must be symmetric")
    if np.min(np.linalg.eigvalsh(m)) <= 0.0:
        raise EndogenousEBNormalModeError("mass matrix must be positive definite")
    if not np.allclose(k, k.T, atol=tol, rtol=0.0):
        raise EndogenousEBNormalModeError("stiffness matrix must be symmetric")
    if not np.allclose(g, -g.T, atol=tol, rtol=0.0):
        raise EndogenousEBNormalModeError("gyroscopic matrix must be antisymmetric")

    inv_m = np.linalg.inv(m)
    zero = np.zeros((3, 3), dtype=float)
    eye = np.eye(3, dtype=float)
    evolution = np.block([[zero, eye], [-inv_m @ k, -inv_m @ g]])
    eig = tuple(complex(x) for x in np.linalg.eigvals(evolution))
    max_growth = max(x.real for x in eig)
    frequencies = sorted(
        x.imag for x in eig if x.imag > tol and abs(x.real) <= tol
    )
    return CollectiveSpectrum(
        eigenvalues=tuple(sorted(eig, key=lambda z: (round(z.real, 12), round(z.imag, 12)))),
        positive_frequencies=tuple(float(x) for x in frequencies),
        max_growth_rate=float(max_growth),
        stable=max_growth <= tol,
    )
