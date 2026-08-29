from __future__ import annotations

from dataclasses import dataclass
import cmath
import math

KAPPA = math.log(2.0) / (24.0 * math.pi)
DELTA7 = 2.0 * math.pi / 7.0
OMEGA0 = 2.0 * math.pi * 7.83


def wrap_pi(x: float) -> float:
    return (float(x) + math.pi) % (2.0 * math.pi) - math.pi


def lattice_phase(phi0: float, n: int, *, wrapped: bool = False) -> float:
    if int(n) != n:
        raise ValueError("heptad index must be integral")
    value = float(phi0) - int(n) * DELTA7
    return wrap_pi(value) if wrapped else value


def semantic_value(B: float, omega: float, N: float, A_R: float, phi_lift: float) -> float:
    vals = tuple(map(float, (B, omega, N, A_R, phi_lift)))
    if not all(math.isfinite(v) for v in vals):
        raise ValueError("semantic carrier inputs must be finite")
    if A_R == 0.0:
        raise ValueError("A_R must be non-zero")
    return (B * omega * N / A_R) * (phi_lift + KAPPA)


def complex_orbital(m_sem: float, phi: float) -> complex:
    m = float(m_sem)
    p = float(phi)
    if not math.isfinite(m) or m <= 0.0 or not math.isfinite(p):
        raise ValueError("semantic mass must be finite/positive and phase finite")
    return m * cmath.exp(1j * p)


def pair_carrier(z_a: complex, z_b: complex) -> complex:
    return complex(z_a).conjugate() * complex(z_b)


def real_projection(z_a: complex, z_b: complex) -> float:
    return float(pair_carrier(z_a, z_b).real)


def transport(z: complex, tau: float) -> complex:
    t = float(tau)
    if not math.isfinite(t):
        raise ValueError("holonomy phase must be finite")
    return complex(z) * cmath.exp(1j * t)


def semantic_mu(mass: float, *, tau: float = 1.0, omega0: float = OMEGA0) -> float:
    m, t, o = map(float, (mass, tau, omega0))
    if not all(math.isfinite(x) and x > 0.0 for x in (m, t, o)):
        raise ValueError("mass, tau and omega0 must be finite and positive")
    return (o * t) ** 2 / m


def scheduler_omega(mass: float, radius: float, *, tau: float = 1.0, omega0: float = OMEGA0) -> float:
    m, r, t, o = map(float, (mass, radius, tau, omega0))
    if not all(math.isfinite(x) and x > 0.0 for x in (m, r, t, o)):
        raise ValueError("mass, radius, tau and omega0 must be finite and positive")
    return o * t / math.sqrt(m * r**3)


def kepler_form_omega(mass: float, radius: float, *, tau: float = 1.0, omega0: float = OMEGA0) -> float:
    r = float(radius)
    if not math.isfinite(r) or r <= 0.0:
        raise ValueError("radius must be finite and positive")
    return math.sqrt(semantic_mu(mass, tau=tau, omega0=omega0) / r**3)


@dataclass(frozen=True)
class PhaseClassAudit:
    n: int
    expected_shift: float
    observed_shift: float
    residual: float


def audit_heptad_shift(observed_shift: float) -> PhaseClassAudit:
    shift = wrap_pi(float(observed_shift))
    candidates = [(abs(wrap_pi(shift + n * DELTA7)), n) for n in range(7)]
    _, n = min(candidates)
    expected = wrap_pi(-n * DELTA7)
    return PhaseClassAudit(n=n, expected_shift=expected, observed_shift=shift, residual=wrap_pi(shift - expected))
