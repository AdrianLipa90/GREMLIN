from __future__ import annotations

import cmath
import math

from tools.gremlin_semantic_orbital_imaginary_real_bridge_v01 import (
    KAPPA,
    complex_orbital,
    pair_carrier,
    semantic_mu,
)


def _positive(name: str, value: float) -> float:
    x = float(value)
    if not math.isfinite(x) or x <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return x


def kepler_omega(mu_sem: float, radius: float) -> float:
    mu = _positive("mu_sem", mu_sem)
    r = _positive("radius", radius)
    return math.sqrt(mu / r**3)


def kepler_period(mu_sem: float, radius: float) -> float:
    return 2.0 * math.pi / kepler_omega(mu_sem, radius)


def newton_potential(mu_sem: float, radius: float) -> float:
    mu = _positive("mu_sem", mu_sem)
    r = _positive("radius", radius)
    return -mu / r


def circular_specific_angular_momentum(mu_sem: float, radius: float) -> float:
    mu = _positive("mu_sem", mu_sem)
    r = _positive("radius", radius)
    return math.sqrt(mu * r)


def rotation_phase_per_orbit(mu_sem: float, radius: float, omega_rot: float) -> float:
    om = float(omega_rot)
    if not math.isfinite(om):
        raise ValueError("omega_rot must be finite")
    return -om * kepler_period(mu_sem, radius)


def weak_field_apsidal_phase(mu_sem: float, radius: float, c: float) -> float:
    mu = _positive("mu_sem", mu_sem)
    r = _positive("radius", radius)
    cc = _positive("c", c)
    return 6.0 * math.pi * mu / (r * cc**2)


def total_phase(rotation_phase: float, gr_phase: float, ab_phase: float) -> float:
    vals = tuple(map(float, (rotation_phase, gr_phase, ab_phase)))
    if not all(math.isfinite(v) for v in vals):
        raise ValueError("phase contributions must be finite")
    return sum(vals)


def phase_factor(rotation_phase: float, gr_phase: float, ab_phase: float) -> complex:
    tau = total_phase(rotation_phase, gr_phase, ab_phase)
    return cmath.exp(1j * tau)


def transported_orbital(m_sem: float, phi: float, tau_total: float) -> complex:
    t = float(tau_total)
    if not math.isfinite(t):
        raise ValueError("tau_total must be finite")
    return complex_orbital(m_sem, phi) * cmath.exp(1j * t)


def transported_real_relation(
    m_a: float,
    phi_a: float,
    tau_a: float,
    m_b: float,
    phi_b: float,
    tau_b: float,
) -> float:
    za = transported_orbital(m_a, phi_a, tau_a)
    zb = transported_orbital(m_b, phi_b, tau_b)
    return float(pair_carrier(za, zb).real)


def transported_semantic_value(
    B: float,
    omega: float,
    N: float,
    A_R: float,
    phi_lift: float,
    tau_total: float,
) -> float:
    vals = tuple(map(float, (B, omega, N, A_R, phi_lift, tau_total)))
    if not all(math.isfinite(v) for v in vals):
        raise ValueError("semantic transport inputs must be finite")
    if A_R == 0.0:
        raise ValueError("A_R must be non-zero")
    return (B * omega * N / A_R) * (phi_lift + tau_total + KAPPA)


def scheduler_kepler_bundle(mass: float, radius: float, *, tau: float, omega0: float) -> dict[str, float]:
    mu = semantic_mu(mass, tau=tau, omega0=omega0)
    omega = kepler_omega(mu, radius)
    ell = circular_specific_angular_momentum(mu, radius)
    return {
        "mu_sem": mu,
        "omega": omega,
        "period": 2.0 * math.pi / omega,
        "newton_potential": newton_potential(mu, radius),
        "specific_angular_momentum": ell,
    }
