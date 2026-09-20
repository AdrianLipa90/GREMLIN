from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence


SCHEMA = "GREMLIN_CROSS_DOMAIN_COUPLING_IDENTIFIABILITY_V0_11"


class CrossDomainIdentifiabilityError(ValueError):
    pass


def _finite(value: float, name: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise CrossDomainIdentifiabilityError(f"{name} must be finite") from exc
    if not math.isfinite(out):
        raise CrossDomainIdentifiabilityError(f"{name} must be finite")
    return out


def _positive(value: float, name: str) -> float:
    out = _finite(value, name)
    if out <= 0.0:
        raise CrossDomainIdentifiabilityError(f"{name} must be finite and positive")
    return out


def _matrix(values: Sequence[Sequence[float]], name: str) -> tuple[tuple[float, ...], ...]:
    rows = tuple(tuple(_finite(v, f"{name}[{i}][{j}]") for j, v in enumerate(row)) for i, row in enumerate(values))
    if not rows or not rows[0]:
        raise CrossDomainIdentifiabilityError(f"{name} must be a non-empty rectangular matrix")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise CrossDomainIdentifiabilityError(f"{name} must be rectangular")
    return rows


def optical_coupling_from_hessians(
    measured_phase_hessian: Sequence[Sequence[float]],
    projected_xi_hessian: Sequence[Sequence[float]],
    *,
    chi_phi: float,
    zero_tol: float = 1e-15,
) -> float:
    """g_I from H_Phi = -chi_phi g_I H_Xi using a Frobenius projection."""
    h_phi = _matrix(measured_phase_hessian, "measured_phase_hessian")
    h_xi = _matrix(projected_xi_hessian, "projected_xi_hessian")
    if (len(h_phi), len(h_phi[0])) != (len(h_xi), len(h_xi[0])):
        raise CrossDomainIdentifiabilityError("Hessian shapes must match")
    chi = _finite(chi_phi, "chi_phi")
    tol = _positive(zero_tol, "zero_tol")
    if abs(chi) <= tol:
        raise CrossDomainIdentifiabilityError("chi_phi must be non-zero")
    inner = sum(a * b for row_a, row_b in zip(h_phi, h_xi) for a, b in zip(row_a, row_b))
    norm2 = sum(b * b for row in h_xi for b in row)
    if norm2 <= tol:
        raise CrossDomainIdentifiabilityError("projected Xi Hessian is zero/degenerate")
    return -inner / (chi * norm2)


def spectroscopic_coupling_from_shift(
    delta_omega_mn: float,
    delta_xi_expectation: float,
    *,
    hbar: float = 1.0,
    zero_tol: float = 1e-15,
) -> float:
    """g_I = hbar Delta omega / (Delta <Xi>) for a non-common-mode adapter."""
    dw = _finite(delta_omega_mn, "delta_omega_mn")
    dxi = _finite(delta_xi_expectation, "delta_xi_expectation")
    hb = _positive(hbar, "hbar")
    tol = _positive(zero_tol, "zero_tol")
    if abs(dxi) <= tol:
        raise CrossDomainIdentifiabilityError(
            "common-mode/degenerate spectroscopy cannot identify g_I"
        )
    return hb * dw / dxi


def projected_inverse_radius_phase_hessian_eigenvalues(
    inverse_radius_strength: float,
    impact_parameter: float,
    *,
    chi_phi: float,
) -> tuple[float, float]:
    """Long symmetric-path projection of U=-lambda/r after removing the common offset."""
    lam = _finite(inverse_radius_strength, "inverse_radius_strength")
    b = _positive(impact_parameter, "impact_parameter")
    chi = _finite(chi_phi, "chi_phi")
    radial = 2.0 * chi * lam / b**2
    tangential = -radial
    return radial, tangential


@dataclass(frozen=True)
class CouplingConsistencyWitness:
    schema: str
    admitted: bool
    reference_estimator: str
    coupling: float
    estimators: tuple[tuple[str, float], ...]
    max_abs_residual: float


def resolve_cross_domain_information_coupling(
    estimates: Mapping[str, float],
    *,
    rel_tol: float = 1e-10,
    abs_tol: float = 1e-12,
    min_independent: int = 2,
) -> CouplingConsistencyWitness:
    """Compare independent estimators without fitting one route to another."""
    if min_independent < 2:
        raise CrossDomainIdentifiabilityError("min_independent must be at least 2")
    items = tuple((str(k), _finite(v, f"estimates[{k}]")) for k, v in estimates.items())
    if len(items) < min_independent:
        raise CrossDomainIdentifiabilityError("insufficient independent coupling estimators")
    ref_name, ref = items[0]
    residuals = [abs(value - ref) for _, value in items]
    for name, value in items[1:]:
        if not math.isclose(value, ref, rel_tol=rel_tol, abs_tol=abs_tol):
            raise CrossDomainIdentifiabilityError(
                f"cross-domain g_I mismatch: {ref_name}={ref}, {name}={value}"
            )
    return CouplingConsistencyWitness(
        schema=SCHEMA,
        admitted=True,
        reference_estimator=ref_name,
        coupling=ref,
        estimators=items,
        max_abs_residual=max(residuals),
    )


def beta_g_from_orbital_subtraction(
    orbital_omega_squared: float,
    radius: float,
    hamiltonian_eb: float,
    inertial_mass: float,
    information_coupling: float,
    xi_gradient: float,
    *,
    control_gradient: float = 0.0,
) -> float:
    """beta_G=C_mu eta_G after subtracting information and declared radial controls."""
    omega2 = _finite(orbital_omega_squared, "orbital_omega_squared")
    r = _positive(radius, "radius")
    h = _positive(hamiltonian_eb, "hamiltonian_eb")
    mass = _positive(inertial_mass, "inertial_mass")
    g_i = _finite(information_coupling, "information_coupling")
    xi1 = _finite(xi_gradient, "xi_gradient")
    controls = _finite(control_gradient, "control_gradient")
    corrected = omega2 - (g_i * xi1 + controls) / (mass * r)
    beta = r**3 * corrected / h
    if not math.isfinite(beta) or beta <= 0.0:
        raise CrossDomainIdentifiabilityError(
            "orbital subtraction did not produce a finite positive beta_G"
        )
    return beta


@dataclass(frozen=True)
class BetaConstancyWitness:
    admitted: bool
    reference_point: str
    beta_g: float
    points: tuple[tuple[str, float], ...]
    max_abs_residual: float


def resolve_constant_beta_g(
    beta_by_point: Mapping[str, float],
    *,
    rel_tol: float = 1e-10,
    abs_tol: float = 1e-12,
    min_points: int = 2,
) -> BetaConstancyWitness:
    if min_points < 2:
        raise CrossDomainIdentifiabilityError("min_points must be at least 2")
    items = tuple((str(k), _positive(v, f"beta_by_point[{k}]")) for k, v in beta_by_point.items())
    if len(items) < min_points:
        raise CrossDomainIdentifiabilityError("insufficient points for beta_G constancy test")
    ref_name, ref = items[0]
    residuals = [abs(value - ref) for _, value in items]
    for name, value in items[1:]:
        if not math.isclose(value, ref, rel_tol=rel_tol, abs_tol=abs_tol):
            raise CrossDomainIdentifiabilityError(
                f"beta_G is not constant: {ref_name}={ref}, {name}={value}"
            )
    return BetaConstancyWitness(
        admitted=True,
        reference_point=ref_name,
        beta_g=ref,
        points=items,
        max_abs_residual=max(residuals),
    )


@dataclass(frozen=True)
class FactorizationRankWitness:
    rank: int
    d_omega2_d_c_mu: tuple[float, ...]
    d_omega2_d_eta_g: tuple[float, ...]
    proportionality: float


def factorization_rank_witness(
    hamiltonian_eb: float,
    source_coefficient: float,
    eta_g: float,
    radii: Sequence[float],
) -> FactorizationRankWitness:
    """Exact Jacobian no-go: C_mu and eta_G columns are proportional for orbital data."""
    h = _positive(hamiltonian_eb, "hamiltonian_eb")
    c_mu = _positive(source_coefficient, "source_coefficient")
    eta = _positive(eta_g, "eta_g")
    rs = tuple(_positive(r, f"radii[{i}]") for i, r in enumerate(radii))
    if not rs:
        raise CrossDomainIdentifiabilityError("at least one radius is required")
    col_c = tuple(h * eta / r**3 for r in rs)
    col_eta = tuple(h * c_mu / r**3 for r in rs)
    return FactorizationRankWitness(
        rank=1,
        d_omega2_d_c_mu=col_c,
        d_omega2_d_eta_g=col_eta,
        proportionality=c_mu / eta,
    )


@dataclass(frozen=True)
class SourceCouplingResolution:
    admitted: bool
    beta_g: float
    c_mu: float
    eta_g: float
    c_mu_receipt_id: str
    eta_g_receipt_id: str


def resolve_source_coupling_factorization(
    beta_g: float,
    *,
    c_mu: float | None = None,
    eta_g: float | None = None,
    c_mu_receipt_id: str | None = None,
    eta_g_receipt_id: str | None = None,
    rel_tol: float = 1e-12,
    abs_tol: float = 1e-15,
) -> SourceCouplingResolution:
    beta = _positive(beta_g, "beta_g")
    if c_mu is None and eta_g is None:
        raise CrossDomainIdentifiabilityError(
            "C_mu and eta_G cannot be factorized without an independent receipt"
        )
    if c_mu is not None and not str(c_mu_receipt_id or "").strip():
        raise CrossDomainIdentifiabilityError("c_mu_receipt_id is required for supplied C_mu")
    if eta_g is not None and not str(eta_g_receipt_id or "").strip():
        raise CrossDomainIdentifiabilityError("eta_g_receipt_id is required for supplied eta_G")

    if c_mu is None:
        eta = _positive(eta_g, "eta_g")
        c = beta / eta
        return SourceCouplingResolution(
            True, beta, c, eta, "RECONSTRUCTED_FROM_BETA_AND_ETA", str(eta_g_receipt_id)
        )
    if eta_g is None:
        c = _positive(c_mu, "c_mu")
        eta = beta / c
        return SourceCouplingResolution(
            True, beta, c, eta, str(c_mu_receipt_id), "RECONSTRUCTED_FROM_BETA_AND_C_MU"
        )

    c = _positive(c_mu, "c_mu")
    eta = _positive(eta_g, "eta_g")
    if not math.isclose(c * eta, beta, rel_tol=rel_tol, abs_tol=abs_tol):
        raise CrossDomainIdentifiabilityError("supplied C_mu*eta_G does not match beta_G")
    return SourceCouplingResolution(
        True, beta, c, eta, str(c_mu_receipt_id), str(eta_g_receipt_id)
    )


def berry_holonomy_from_independent_circulation(
    circulation: float,
    inertial_mass: float,
    action_scale: float,
    *,
    winding: int,
    circulation_receipt_id: str,
) -> float:
    """gamma_B=2*pi*n-(m_I/eta_phi)*circulation with an independent receipt."""
    if isinstance(winding, bool) or not isinstance(winding, int):
        raise CrossDomainIdentifiabilityError("winding must be an integer")
    if not str(circulation_receipt_id or "").strip():
        raise CrossDomainIdentifiabilityError("circulation_receipt_id is required")
    circ = _finite(circulation, "circulation")
    mass = _positive(inertial_mass, "inertial_mass")
    eta = _positive(action_scale, "action_scale")
    return 2.0 * math.pi * winding - (mass / eta) * circ
