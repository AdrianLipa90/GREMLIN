from __future__ import annotations

from dataclasses import dataclass
import math

OMEGA0 = 2.0 * math.pi * 7.83


class PNLFRadiusSourceError(ValueError):
    pass


def _positive(value: float, name: str) -> float:
    out = float(value)
    if not math.isfinite(out) or out <= 0.0:
        raise PNLFRadiusSourceError(f"{name} must be finite and positive")
    return out


def omega_from_period(orbit_period: float) -> float:
    T = _positive(orbit_period, "orbit_period")
    return 2.0 * math.pi / T


def scheduler_radius_from_pnlf(
    semantic_mass: float,
    orbit_period: float,
    *,
    tau: float = 1.0,
    omega0: float = OMEGA0,
) -> float:
    """Invert omega=omega0*tau/sqrt(m*r^3) using PNLF mass and period."""
    m = _positive(semantic_mass, "semantic_mass")
    T = _positive(orbit_period, "orbit_period")
    t = _positive(tau, "tau")
    o0 = _positive(omega0, "omega0")
    omega = 2.0 * math.pi / T
    return ((o0 * t) ** 2 / (m * omega**2)) ** (1.0 / 3.0)


def scheduler_period_from_radius(
    semantic_mass: float,
    scheduler_radius: float,
    *,
    tau: float = 1.0,
    omega0: float = OMEGA0,
) -> float:
    m = _positive(semantic_mass, "semantic_mass")
    r = _positive(scheduler_radius, "scheduler_radius")
    t = _positive(tau, "tau")
    o0 = _positive(omega0, "omega0")
    omega = o0 * t / math.sqrt(m * r**3)
    return 2.0 * math.pi / omega


@dataclass(frozen=True)
class PNLFRadiusWitness:
    semantic_mass: float
    orbit_period: float
    tau: float
    omega0: float
    scheduler_radius: float
    reconstructed_period: float
    period_residual: float


def build_radius_witness(
    semantic_mass: float,
    orbit_period: float,
    *,
    tau: float = 1.0,
    omega0: float = OMEGA0,
) -> PNLFRadiusWitness:
    m = _positive(semantic_mass, "semantic_mass")
    T = _positive(orbit_period, "orbit_period")
    t = _positive(tau, "tau")
    o0 = _positive(omega0, "omega0")
    r = scheduler_radius_from_pnlf(m, T, tau=t, omega0=o0)
    T2 = scheduler_period_from_radius(m, r, tau=t, omega0=o0)
    return PNLFRadiusWitness(
        semantic_mass=m,
        orbit_period=T,
        tau=t,
        omega0=o0,
        scheduler_radius=r,
        reconstructed_period=T2,
        period_residual=T2 - T,
    )
