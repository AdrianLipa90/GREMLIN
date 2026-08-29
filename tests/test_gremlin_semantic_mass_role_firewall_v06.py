import math

import pytest

from tools.gremlin_semantic_mass_role_firewall_v06 import (
    MassRoleError,
    admit_pnlf_period_model,
    bestiary_orbit,
    historical_inertial_sim_orbit,
    inertial_radius_from_period,
    period_squared_mass_exponent,
    source_mass_kepler_period,
    source_radius_from_period,
)


def test_bestiary_exact_scheduler_relation():
    omega0, tau, mass, radius = 7.83, 1.25, 0.75, 2.4
    orbit = bestiary_orbit(
        omega0=omega0,
        tau=tau,
        semantic_mass=mass,
        radius=radius,
    )
    expected = (omega0 * tau) ** 2 / (mass * radius**3)
    assert math.isclose(orbit.omega_squared, expected, rel_tol=0.0, abs_tol=1e-15)


def test_historical_inertial_sim_is_same_mass_role():
    k, mass, radius = 2.5, 0.8, 1.7
    orbit = historical_inertial_sim_orbit(k=k, semantic_mass=mass, radius=radius)
    assert math.isclose(orbit.omega_squared, k / (mass * radius**3), rel_tol=0.0, abs_tol=1e-15)


def test_historical_stored_period_has_opposite_mass_exponent():
    radius = 1.3
    source_t1 = source_mass_kepler_period(semantic_mass=1.0, radius=radius)
    source_t4 = source_mass_kepler_period(semantic_mass=4.0, radius=radius)
    assert math.isclose(source_t4 / source_t1, 0.5, rel_tol=0.0, abs_tol=1e-15)

    inertial_t1 = bestiary_orbit(
        omega0=2.0 * math.pi,
        tau=1.0,
        semantic_mass=1.0,
        radius=radius,
    ).period
    inertial_t4 = bestiary_orbit(
        omega0=2.0 * math.pi,
        tau=1.0,
        semantic_mass=4.0,
        radius=radius,
    ).period
    assert math.isclose(inertial_t4 / inertial_t1, 2.0, rel_tol=0.0, abs_tol=1e-15)


def test_inverse_radius_is_role_specific_and_exact():
    radius = 2.2
    mass = 0.7
    omega0 = 3.0
    tau = 1.1

    period = bestiary_orbit(
        omega0=omega0,
        tau=tau,
        semantic_mass=mass,
        radius=radius,
    ).period
    recovered = inertial_radius_from_period(
        period=period,
        coupling_scale=omega0,
        tau=tau,
        inertial_mass=mass,
    )
    assert math.isclose(recovered, radius, rel_tol=1e-14, abs_tol=1e-14)

    source_period = source_mass_kepler_period(semantic_mass=mass, radius=radius)
    recovered_source = source_radius_from_period(period=source_period, source_mass=mass)
    assert math.isclose(recovered_source, radius, rel_tol=1e-14, abs_tol=1e-14)


def test_mass_exponent_classifier():
    assert period_squared_mass_exponent("INERTIAL_LOAD") == 1.0
    assert period_squared_mass_exponent("SOURCE_STRENGTH") == -1.0
    assert period_squared_mass_exponent("EQUIVALENCE_CANCELLED") == 0.0
    assert period_squared_mass_exponent("OBJECTCARD_CADENCE") == 3.0


def test_pnlf_period_model_gate_fails_closed():
    admit_pnlf_period_model(
        mass_role="INERTIAL_LOAD",
        orbit_period_model_id="GREMLIN_BESTIARY_MASS_ORBIT_SCHEDULER_V0_2",
    )

    with pytest.raises(MassRoleError):
        admit_pnlf_period_model(
            mass_role="SOURCE_STRENGTH",
            orbit_period_model_id="GREMLIN_BESTIARY_MASS_ORBIT_SCHEDULER_V0_2",
        )

    with pytest.raises(MassRoleError):
        admit_pnlf_period_model(
            mass_role="INERTIAL_LOAD",
            orbit_period_model_id="UNKNOWN",
        )
