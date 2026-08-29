from __future__ import annotations

from dataclasses import dataclass
import math

from tools.gremlin_bestiary_orbital_scheduler_v02 import OMEGA0, PROFILES, service_omega
from tools.gremlin_semantic_orbital_mass_role_firewall_v06 import role_separated_omega

BESTIARY_COMPAT = "GREMLIN_BESTIARY_V02_INERTIAL_SERVICE_LOAD_COMPAT"
FOUNDATION_COMPAT = "CIEL_FOUNDATION_P3_SOURCE_ATTRACTOR_COMPAT"
EQUIVALENCE_CANDIDATE = "SEMANTIC_EQUIVALENCE_CANDIDATE"

KNOWN_PROFILE_IDS = frozenset({BESTIARY_COMPAT, FOUNDATION_COMPAT, EQUIVALENCE_CANDIDATE})


class TypedSchedulerError(ValueError):
    pass


def _positive(value: float, name: str) -> float:
    out = float(value)
    if not math.isfinite(out) or out <= 0.0:
        raise TypedSchedulerError(f"{name} must be finite and positive")
    return out


def _profile_id(profile_id: str) -> str:
    pid = str(profile_id)
    if pid not in KNOWN_PROFILE_IDS:
        raise TypedSchedulerError("unknown mass_role_profile_id")
    return pid


@dataclass(frozen=True)
class TypedOrbitWitness:
    species: str | None
    mass_role_profile_id: str
    mu_source: float
    q_coupling: float
    m_inertial: float
    radius: float
    tau: float
    omega0: float
    omega: float
    period: float
    legacy_omega: float | None
    compatibility_residual: float | None


def _witness(
    *,
    species: str | None,
    profile_id: str,
    mu_source: float,
    q_coupling: float,
    m_inertial: float,
    radius: float,
    tau: float,
    omega0: float,
    legacy_omega: float | None = None,
) -> TypedOrbitWitness:
    pid = _profile_id(profile_id)
    mu = _positive(mu_source, "mu_source")
    q = _positive(q_coupling, "q_coupling")
    mi = _positive(m_inertial, "m_inertial")
    r = _positive(radius, "radius")
    t = _positive(tau, "tau")
    o0 = _positive(omega0, "omega0")
    omega = role_separated_omega(mu, q, mi, r)
    period = 2.0 * math.pi / omega
    legacy = None if legacy_omega is None else _positive(legacy_omega, "legacy_omega")
    residual = None if legacy is None else omega - legacy
    return TypedOrbitWitness(
        species=species,
        mass_role_profile_id=pid,
        mu_source=mu,
        q_coupling=q,
        m_inertial=mi,
        radius=r,
        tau=t,
        omega0=o0,
        omega=omega,
        period=period,
        legacy_omega=legacy,
        compatibility_residual=residual,
    )


def bestiary_species_witness(species: str, *, tau: float = 1.0, omega0: float = OMEGA0) -> TypedOrbitWitness:
    if species not in PROFILES:
        raise TypedSchedulerError("unknown Bestiary species")
    t = _positive(tau, "tau")
    o0 = _positive(omega0, "omega0")
    legacy_profile = PROFILES[species]
    legacy = service_omega(legacy_profile, tau=t, omega0=o0)
    return _witness(
        species=species,
        profile_id=BESTIARY_COMPAT,
        mu_source=(o0 * t) ** 2,
        q_coupling=1.0,
        m_inertial=legacy_profile.mass,
        radius=legacy_profile.radius,
        tau=t,
        omega0=o0,
        legacy_omega=legacy,
    )


def foundation_witness(
    M_sem: float,
    radius: float,
    *,
    carrier_mass: float = 1.0,
) -> TypedOrbitWitness:
    M = _positive(M_sem, "M_sem")
    r = _positive(radius, "radius")
    m = _positive(carrier_mass, "carrier_mass")
    return _witness(
        species=None,
        profile_id=FOUNDATION_COMPAT,
        mu_source=4.0 * math.pi**2 * M,
        q_coupling=m,
        m_inertial=m,
        radius=r,
        tau=1.0,
        omega0=2.0 * math.pi,
    )


def equivalence_candidate_witness(
    mu_source: float,
    carrier_mass: float,
    radius: float,
) -> TypedOrbitWitness:
    mu = _positive(mu_source, "mu_source")
    m = _positive(carrier_mass, "carrier_mass")
    r = _positive(radius, "radius")
    return _witness(
        species=None,
        profile_id=EQUIVALENCE_CANDIDATE,
        mu_source=mu,
        q_coupling=m,
        m_inertial=m,
        radius=r,
        tau=1.0,
        omega0=1.0,
    )


def general_radius_from_period(
    period: float,
    *,
    mu_source: float,
    q_coupling: float,
    m_inertial: float,
) -> float:
    T = _positive(period, "period")
    mu = _positive(mu_source, "mu_source")
    q = _positive(q_coupling, "q_coupling")
    mi = _positive(m_inertial, "m_inertial")
    omega = 2.0 * math.pi / T
    return (mu * q / (mi * omega**2)) ** (1.0 / 3.0)


def cadence_rank_typed() -> tuple[str, ...]:
    return tuple(
        sorted(PROFILES, key=lambda name: (-bestiary_species_witness(name).omega, name))
    )
