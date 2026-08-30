from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

SCHEMA = "GREMLIN_ORBIT_SOURCE_COUPLING_IDENTIFIABILITY_V0_8"
PASS_EXACT_IDENTIFIABILITY = "PASS_EXACT_IDENTIFIABILITY"
FAIL_UNSOURCED_FACTORIZATION = "FAIL_UNSOURCED_FACTORIZATION"


class OrbitSourceIdentifiabilityError(ValueError):
    pass


def _positive(value: float, name: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise OrbitSourceIdentifiabilityError(f"{name} must be finite and positive") from exc
    if not math.isfinite(out) or out <= 0.0:
        raise OrbitSourceIdentifiabilityError(f"{name} must be finite and positive")
    return out


def _nonnegative(value: float, name: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise OrbitSourceIdentifiabilityError(f"{name} must be finite and non-negative") from exc
    if not math.isfinite(out) or out < 0.0:
        raise OrbitSourceIdentifiabilityError(f"{name} must be finite and non-negative")
    return out


def orbit_strength(omega: float, radius: float) -> float:
    """Identifiable circular-orbit invariant K_orb = omega^2 r^3."""
    w = _positive(omega, "omega")
    r = _positive(radius, "radius")
    return w * w * r**3


def eta_g(q_coupling: float, m_inertial: float) -> float:
    q = _positive(q_coupling, "q_coupling")
    m = _positive(m_inertial, "m_inertial")
    return q / m


def source_coupling_product(mu_source: float, eta: float) -> float:
    mu = _positive(mu_source, "mu_source")
    e = _positive(eta, "eta_g")
    return mu * e


def role_kernel_omega(mu_source: float, q_coupling: float, m_inertial: float, radius: float) -> float:
    mu = _positive(mu_source, "mu_source")
    r = _positive(radius, "radius")
    e = eta_g(q_coupling, m_inertial)
    return math.sqrt(mu * e / r**3)


@dataclass(frozen=True)
class FactorizationWitness:
    orbit_strength: float
    mu_source: float
    eta_g: float
    scale_lambda: float

    @property
    def product(self) -> float:
        return self.mu_source * self.eta_g


def rescale_factorization(mu_source: float, eta: float, scale_lambda: float) -> FactorizationWitness:
    """Positive factorization gauge: mu -> lambda*mu, eta -> eta/lambda."""
    mu = _positive(mu_source, "mu_source")
    e = _positive(eta, "eta_g")
    lam = _positive(scale_lambda, "scale_lambda")
    return FactorizationWitness(
        orbit_strength=mu * e,
        mu_source=lam * mu,
        eta_g=e / lam,
        scale_lambda=lam,
    )


def infer_mu_given_eta(k_orb: float, eta: float) -> float:
    k = _positive(k_orb, "k_orb")
    e = _positive(eta, "eta_g")
    return k / e


def infer_eta_given_mu(k_orb: float, mu_source: float) -> float:
    k = _positive(k_orb, "k_orb")
    mu = _positive(mu_source, "mu_source")
    return k / mu


@dataclass(frozen=True)
class IdentifiabilityWitness:
    schema: str
    status: str
    admitted: bool
    orbit_strength: float
    mu_source: float | None
    eta_g: float | None
    mu_source_profile_id: str | None
    eta_g_profile_id: str | None
    residual: float | None


def resolve_factorization(
    omega: float,
    radius: float,
    *,
    mu_source: float | None = None,
    eta: float | None = None,
    mu_source_profile_id: str | None = None,
    eta_g_profile_id: str | None = None,
    rel_tol: float = 1e-12,
    abs_tol: float = 1e-15,
) -> IdentifiabilityWitness:
    """Resolve only factorizations backed by explicit source identifiers."""
    k = orbit_strength(omega, radius)
    if mu_source is None and eta is None:
        return IdentifiabilityWitness(
            schema=SCHEMA,
            status=FAIL_UNSOURCED_FACTORIZATION,
            admitted=False,
            orbit_strength=k,
            mu_source=None,
            eta_g=None,
            mu_source_profile_id=None,
            eta_g_profile_id=None,
            residual=None,
        )

    if mu_source is not None and not str(mu_source_profile_id or "").strip():
        raise OrbitSourceIdentifiabilityError("mu_source_profile_id is required when mu_source is supplied")
    if eta is not None and not str(eta_g_profile_id or "").strip():
        raise OrbitSourceIdentifiabilityError("eta_g_profile_id is required when eta_g is supplied")

    if mu_source is None:
        e = _positive(eta, "eta_g")
        mu = infer_mu_given_eta(k, e)
        residual = abs(mu * e - k)
        return IdentifiabilityWitness(
            schema=SCHEMA,
            status=PASS_EXACT_IDENTIFIABILITY,
            admitted=True,
            orbit_strength=k,
            mu_source=mu,
            eta_g=e,
            mu_source_profile_id="RECONSTRUCTED_FROM_ORBIT_AND_ETA",
            eta_g_profile_id=str(eta_g_profile_id),
            residual=residual,
        )

    if eta is None:
        mu = _positive(mu_source, "mu_source")
        e = infer_eta_given_mu(k, mu)
        residual = abs(mu * e - k)
        return IdentifiabilityWitness(
            schema=SCHEMA,
            status=PASS_EXACT_IDENTIFIABILITY,
            admitted=True,
            orbit_strength=k,
            mu_source=mu,
            eta_g=e,
            mu_source_profile_id=str(mu_source_profile_id),
            eta_g_profile_id="RECONSTRUCTED_FROM_ORBIT_AND_SOURCE",
            residual=residual,
        )

    mu = _positive(mu_source, "mu_source")
    e = _positive(eta, "eta_g")
    product = mu * e
    residual = abs(product - k)
    if not math.isclose(product, k, rel_tol=rel_tol, abs_tol=abs_tol):
        raise OrbitSourceIdentifiabilityError(
            f"supplied factorization does not match K_orb: residual={residual}"
        )
    return IdentifiabilityWitness(
        schema=SCHEMA,
        status=PASS_EXACT_IDENTIFIABILITY,
        admitted=True,
        orbit_strength=k,
        mu_source=mu,
        eta_g=e,
        mu_source_profile_id=str(mu_source_profile_id),
        eta_g_profile_id=str(eta_g_profile_id),
        residual=residual,
    )


def extensive_source_energy(cell_volumes: Iterable[float], rho_g: Iterable[float]) -> float:
    """Finite-cell E_Sigma = sum_a V_a rho_G,a from an explicitly bound RFC cell measure."""
    volumes = tuple(cell_volumes)
    densities = tuple(rho_g)
    if not volumes or len(volumes) != len(densities):
        raise OrbitSourceIdentifiabilityError("matching non-empty cell_volumes and rho_g are required")
    total = 0.0
    for i, (v, rho) in enumerate(zip(volumes, densities)):
        vv = _positive(v, f"cell_volumes[{i}]")
        rr = _nonnegative(rho, f"rho_g[{i}]")
        total += vv * rr
    if not math.isfinite(total) or total <= 0.0:
        raise OrbitSourceIdentifiabilityError("extensive source energy must be finite and positive")
    return total


def candidate_mu_from_extensive_source(extensive_source: float, conversion_c_mu: float) -> float:
    """Candidate-only conversion requiring an explicit independently sourced coefficient C_mu."""
    e = _positive(extensive_source, "extensive_source")
    c = _positive(conversion_c_mu, "conversion_c_mu")
    return c * e


def conversion_required_for_mu(extensive_source: float, mu_source: float) -> float:
    e = _positive(extensive_source, "extensive_source")
    mu = _positive(mu_source, "mu_source")
    return mu / e
