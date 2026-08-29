from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Mapping

OMEGA0 = 2.0 * math.pi * 7.83


@dataclass(frozen=True)
class OrbitProfile:
    name: str
    mass: float
    radius: float


PROFILES = {
    "HUMMINGBIRD": OrbitProfile("HUMMINGBIRD", 0.05, 0.39),
    "MANTIS": OrbitProfile("MANTIS", 0.70, 0.55),
    "ANT": OrbitProfile("ANT", 0.80, 0.72),
    "RAVEN": OrbitProfile("RAVEN", 0.90, 0.90),
    "HOUND": OrbitProfile("HOUND", 1.00, 1.00),
    "OWL": OrbitProfile("OWL", 1.10, 1.15),
    "SPIDER": OrbitProfile("SPIDER", 1.20, 1.35),
    "MOLE": OrbitProfile("MOLE", 1.60, 2.20),
    "BELZEBUB": OrbitProfile("BELZEBUB", 2.60, 5.20),
}


def service_omega(profile: OrbitProfile, *, tau: float = 1.0, omega0: float = OMEGA0) -> float:
    """Scheduler cadence band: omega = omega0*tau/sqrt(m*r^3)."""
    m = float(profile.mass)
    r = float(profile.radius)
    t = float(tau)
    o = float(omega0)
    if not all(math.isfinite(x) and x > 0.0 for x in (m, r, t, o)):
        raise ValueError("mass, radius, tau and omega0 must be finite and positive")
    return o * t / math.sqrt(m * r**3)


def service_period(profile: OrbitProfile, *, tau: float = 1.0, omega0: float = OMEGA0) -> float:
    return 2.0 * math.pi / service_omega(profile, tau=tau, omega0=omega0)


def cadence_rank(names: Iterable[str], *, tau: float = 1.0) -> tuple[str, ...]:
    ns = tuple(names)
    if any(name not in PROFILES for name in ns):
        raise KeyError("unknown Bestiary species")
    return tuple(sorted(ns, key=lambda name: (-service_omega(PROFILES[name], tau=tau), name)))


def bounded_batch_size(
    route_counts: Mapping[str, int],
    item_count: int,
    workers: int,
    *,
    lo: int = 8,
    hi: int = 128,
) -> int:
    """Derive a bounded heavy-orbit batch from routed semantic mass/cadence."""
    n = int(item_count)
    w = int(workers)
    if n <= 0 or w <= 0:
        raise ValueError("item_count and workers must be positive")
    weighted = 0.0
    for role, count in route_counts.items():
        if role not in PROFILES or role in {"HUMMINGBIRD", "BELZEBUB"}:
            continue
        c = max(0, int(count))
        p = PROFILES[role]
        weighted += c * p.mass / max(service_omega(p), 1e-15)
    per_item = weighted / n
    jupiter = PROFILES["BELZEBUB"]
    ratio = max(1.0, (jupiter.mass / service_omega(jupiter)) / max(per_item, 1e-15))
    size = int(round(lo * math.sqrt(ratio) * max(1.0, w / 2.0)))
    return max(int(lo), min(int(hi), size))


def ideal_scalar_ceiling(serial_work: float, routed_work: float, workers: int) -> float:
    """Ideal no-overhead ceiling for unchanged scalar transforms."""
    s = float(serial_work)
    r = float(routed_work)
    w = int(workers)
    if s <= 0.0 or r <= 0.0 or w <= 0:
        raise ValueError("work and workers must be positive")
    return w * s / r
