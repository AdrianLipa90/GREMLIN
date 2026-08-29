from __future__ import annotations

import cmath
import math

KAPPA = math.log(2.0) / (24.0 * math.pi)
DELTA7 = 2.0 * math.pi / 7.0


class SemanticSourceDensityError(ValueError):
    pass


def _finite(value: float, name: str) -> float:
    out = float(value)
    if not math.isfinite(out):
        raise SemanticSourceDensityError(f"{name} must be finite")
    return out


def _positive(value: float, name: str) -> float:
    out = _finite(value, name)
    if out <= 0.0:
        raise SemanticSourceDensityError(f"{name} must be positive")
    return out


def lift_index(n: int, winding: int) -> int:
    if int(n) != n or not 0 <= int(n) <= 6:
        raise SemanticSourceDensityError("heptad index n must be an integer in 0..6")
    if int(winding) != winding:
        raise SemanticSourceDensityError("winding must be integral")
    return 7 * int(winding) - int(n)


def lifted_phase(phi0: float, n: int, winding: int) -> float:
    p0 = _finite(phi0, "phi0")
    return p0 + lift_index(n, winding) * DELTA7


def complex_semantic_orbital(m_sem: float, phi0: float, n: int, winding: int) -> complex:
    m = _positive(m_sem, "m_sem")
    phi = lifted_phase(phi0, n, winding)
    return m * cmath.exp(1j * phi)


def source_prefactor(B: float, omega: float, occupation: float, area: float, radius: float) -> float:
    b = _finite(B, "B")
    o = _positive(omega, "omega")
    occ = _finite(occupation, "occupation")
    if occ < 0.0:
        raise SemanticSourceDensityError("occupation must be non-negative")
    a = _positive(area, "area")
    r = _positive(radius, "radius")
    return b * o * occ / (a * r)


def source_density(
    B: float,
    omega: float,
    occupation: float,
    area: float,
    radius: float,
    phi0: float,
    n: int,
    winding: int,
) -> float:
    q = source_prefactor(B, omega, occupation, area, radius)
    return q * (lifted_phase(phi0, n, winding) + KAPPA)


def adjacent_lift_increment(B: float, omega: float, occupation: float, area: float, radius: float) -> float:
    return source_prefactor(B, omega, occupation, area, radius) * DELTA7


def full_turn_increment(B: float, omega: float, occupation: float, area: float, radius: float) -> float:
    return source_prefactor(B, omega, occupation, area, radius) * 2.0 * math.pi
