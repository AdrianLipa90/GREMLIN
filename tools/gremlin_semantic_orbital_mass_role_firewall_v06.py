from __future__ import annotations

from dataclasses import dataclass
import math

OMEGA0 = 2.0 * math.pi * 7.83


class MassRoleFirewallError(ValueError):
    pass


def _positive(value: float, name: str) -> float:
    out = float(value)
    if not math.isfinite(out) or out <= 0.0:
        raise MassRoleFirewallError(f"{name} must be finite and positive")
    return out


def role_separated_omega_sq(
    mu_source: float,
    q_coupling: float,
    m_inertial: float,
    radius: float,
) -> float:
    mu = _positive(mu_source, "mu_source")
    q = _positive(q_coupling, "q_coupling")
    mi = _positive(m_inertial, "m_inertial")
    r = _positive(radius, "radius")
    return mu * (q / mi) / r**3


def role_separated_omega(
    mu_source: float,
    q_coupling: float,
    m_inertial: float,
    radius: float,
) -> float:
    return math.sqrt(role_separated_omega_sq(mu_source, q_coupling, m_inertial, radius))


def bestiary_omega(mass: float, radius: float, *, tau: float = 1.0, omega0: float = OMEGA0) -> float:
    m = _positive(mass, "mass")
    r = _positive(radius, "radius")
    t = _positive(tau, "tau")
    o0 = _positive(omega0, "omega0")
    return o0 * t / math.sqrt(m * r**3)


def bestiary_role_embedding(mass: float, radius: float, *, tau: float = 1.0, omega0: float = OMEGA0) -> float:
    m = _positive(mass, "mass")
    t = _positive(tau, "tau")
    o0 = _positive(omega0, "omega0")
    return role_separated_omega(
        mu_source=(o0 * t) ** 2,
        q_coupling=1.0,
        m_inertial=m,
        radius=radius,
    )


def foundation_omega(M_sem: float, radius: float) -> float:
    M = _positive(M_sem, "M_sem")
    r = _positive(radius, "radius")
    return 2.0 * math.pi * math.sqrt(M / r**3)


def foundation_role_embedding(M_sem: float, radius: float, *, carrier_mass: float = 1.0) -> float:
    M = _positive(M_sem, "M_sem")
    c = _positive(carrier_mass, "carrier_mass")
    return role_separated_omega(
        mu_source=4.0 * math.pi**2 * M,
        q_coupling=c,
        m_inertial=c,
        radius=radius,
    )


def nbody_role_embedding(G: float, M1: float, M2: float, radius: float) -> float:
    g = _positive(G, "G")
    m1 = _positive(M1, "M1")
    m2 = _positive(M2, "M2")
    return role_separated_omega(
        mu_source=g * (m1 + m2),
        q_coupling=1.0,
        m_inertial=1.0,
        radius=radius,
    )


def equivalence_branch_omega(mu_source: float, carrier_mass: float, radius: float) -> float:
    m = _positive(carrier_mass, "carrier_mass")
    return role_separated_omega(mu_source, m, m, radius)


def omega_sq_mass_exponent(
    *,
    source_exponent: float = 0.0,
    charge_exponent: float = 0.0,
    inertial_exponent: float = 0.0,
) -> float:
    vals = [float(source_exponent), float(charge_exponent), float(inertial_exponent)]
    if not all(math.isfinite(v) for v in vals):
        raise MassRoleFirewallError("mass exponents must be finite")
    return vals[0] + vals[1] - vals[2]


def period_mass_exponent_from_omega_sq(exponent: float) -> float:
    e = float(exponent)
    if not math.isfinite(e):
        raise MassRoleFirewallError("omega-squared exponent must be finite")
    return -0.5 * e


@dataclass(frozen=True)
class RoleProfileAudit:
    profile_id: str
    omega_sq_mass_exponent: float
    period_mass_exponent: float
    classification: str


def profile_audits() -> tuple[RoleProfileAudit, ...]:
    return (
        RoleProfileAudit(
            profile_id="GREMLIN_BESTIARY_INTERNAL_SERVICE_CADENCE",
            omega_sq_mass_exponent=-1.0,
            period_mass_exponent=0.5,
            classification="INERTIAL_SERVICE_LOAD_EMBEDDING",
        ),
        RoleProfileAudit(
            profile_id="CIEL_FOUNDATION_P3_SOURCE_MASS",
            omega_sq_mass_exponent=1.0,
            period_mass_exponent=-0.5,
            classification="SOURCE_ATTRACTOR_EMBEDDING",
        ),
        RoleProfileAudit(
            profile_id="CIEL_OBJECTCARD_LEGACY",
            omega_sq_mass_exponent=-3.0,
            period_mass_exponent=1.5,
            classification="ROLE_SOURCE_UNRESOLVED",
        ),
    )


def objectcard_required_source_charge_exponent(*, inertial_exponent: float = 1.0) -> float:
    """Net exponent of mu_source*q_coupling needed for omega^2 ~ m^-3."""
    ie = float(inertial_exponent)
    if not math.isfinite(ie):
        raise MassRoleFirewallError("inertial exponent must be finite")
    # target = source_plus_charge - inertial
    # -3 = s_q - ie -> s_q = -3 + ie
    return -3.0 + ie
