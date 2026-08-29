from __future__ import annotations

from dataclasses import dataclass
import math

SCHEMA = "GREMLIN_SEMANTIC_MASS_ROLE_FIREWALL_V0_6"


class MassRoleError(ValueError):
    pass


def _positive(value: float, name: str) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise MassRoleError(f"{name} must be finite positive") from exc
    if not math.isfinite(x) or x <= 0.0:
        raise MassRoleError(f"{name} must be finite positive")
    return x


@dataclass(frozen=True)
class MassRoleOrbit:
    coupling_scale: float
    tau: float
    source_charge: float
    orbital_charge: float
    inertial_mass: float
    radius: float

    def __post_init__(self) -> None:
        for name in (
            "coupling_scale",
            "tau",
            "source_charge",
            "orbital_charge",
            "inertial_mass",
            "radius",
        ):
            object.__setattr__(self, name, _positive(getattr(self, name), name))

    @property
    def omega_squared(self) -> float:
        return (
            (self.coupling_scale * self.tau) ** 2
            * self.source_charge
            * self.orbital_charge
            / (self.inertial_mass * self.radius**3)
        )

    @property
    def omega(self) -> float:
        return math.sqrt(self.omega_squared)

    @property
    def period(self) -> float:
        return 2.0 * math.pi / self.omega


def bestiary_orbit(*, omega0: float, tau: float, semantic_mass: float, radius: float) -> MassRoleOrbit:
    return MassRoleOrbit(
        coupling_scale=omega0,
        tau=tau,
        source_charge=1.0,
        orbital_charge=1.0,
        inertial_mass=semantic_mass,
        radius=radius,
    )


def historical_inertial_sim_orbit(*, k: float, semantic_mass: float, radius: float) -> MassRoleOrbit:
    # Historical CIEL kepler_ciel_sim.py:
    # v_circ^2 = k / (M_sem * r), hence omega^2 = k/(M_sem*r^3).
    return MassRoleOrbit(
        coupling_scale=math.sqrt(_positive(k, "k")),
        tau=1.0,
        source_charge=1.0,
        orbital_charge=1.0,
        inertial_mass=semantic_mass,
        radius=radius,
    )


def source_mass_kepler_period(*, semantic_mass: float, radius: float) -> float:
    # Historical ciel_geometry/semantic_mass.py stored law:
    # T^2 = r^3 / M_sem.
    m = _positive(semantic_mass, "semantic_mass")
    r = _positive(radius, "radius")
    return math.sqrt(r**3 / m)


def inertial_radius_from_period(
    *,
    period: float,
    coupling_scale: float,
    tau: float,
    inertial_mass: float,
    source_charge: float = 1.0,
    orbital_charge: float = 1.0,
) -> float:
    T = _positive(period, "period")
    lam = _positive(coupling_scale, "coupling_scale")
    tau = _positive(tau, "tau")
    m = _positive(inertial_mass, "inertial_mass")
    qs = _positive(source_charge, "source_charge")
    qo = _positive(orbital_charge, "orbital_charge")
    omega = 2.0 * math.pi / T
    return (((lam * tau) ** 2 * qs * qo) / (m * omega**2)) ** (1.0 / 3.0)


def source_radius_from_period(*, period: float, source_mass: float) -> float:
    T = _positive(period, "period")
    M = _positive(source_mass, "source_mass")
    return (M * T**2) ** (1.0 / 3.0)


def period_squared_mass_exponent(role: str) -> float:
    key = str(role).strip().upper()
    table = {
        "INERTIAL_LOAD": +1.0,
        "SOURCE_STRENGTH": -1.0,
        "EQUIVALENCE_CANCELLED": 0.0,
        "OBJECTCARD_CADENCE": +3.0,
    }
    if key not in table:
        raise MassRoleError(f"unknown mass role: {role}")
    return table[key]


def admit_pnlf_period_model(*, mass_role: str, orbit_period_model_id: str) -> None:
    role = str(mass_role).strip().upper()
    model = str(orbit_period_model_id).strip()
    if not model:
        raise MassRoleError("orbit_period_model_id required")
    if role != "INERTIAL_LOAD":
        raise MassRoleError("PNLF -> Bestiary inverse radius requires INERTIAL_LOAD mass role")
    if model not in {
        "GREMLIN_BESTIARY_MASS_ORBIT_SCHEDULER_V0_2",
        "CIEL_KEPLER_INERTIAL_SIM_COMPAT",
    }:
        raise MassRoleError("PNLF orbit_period model is not admitted for Bestiary inverse radius")
