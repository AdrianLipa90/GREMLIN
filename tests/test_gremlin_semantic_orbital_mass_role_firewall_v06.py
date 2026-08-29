import math

from tools.gremlin_semantic_orbital_mass_role_firewall_v06 import (
    MassRoleFirewallError,
    bestiary_omega,
    bestiary_role_embedding,
    equivalence_branch_omega,
    foundation_omega,
    foundation_role_embedding,
    nbody_role_embedding,
    objectcard_required_source_charge_exponent,
    omega_sq_mass_exponent,
    period_mass_exponent_from_omega_sq,
    profile_audits,
    role_separated_omega,
)


def test_bestiary_embedding_is_exact_for_reference_profiles():
    cases = [
        (0.05, 0.39, 1.0),
        (0.70, 0.55, 0.8),
        (1.0, 1.0, 1.0),
        (1.6, 2.2, 1.25),
        (2.6, 5.2, 1.0),
    ]
    for mass, radius, tau in cases:
        direct = bestiary_omega(mass, radius, tau=tau)
        embedded = bestiary_role_embedding(mass, radius, tau=tau)
        assert abs(direct - embedded) < 2e-13


def test_foundation_p3_embedding_is_exact_and_carrier_mass_cancels():
    for M_sem, radius in ((0.4, 0.2), (0.94, 0.63), (1.7, 0.81)):
        direct = foundation_omega(M_sem, radius)
        for carrier_mass in (0.1, 1.0, 7.3):
            embedded = foundation_role_embedding(M_sem, radius, carrier_mass=carrier_mass)
            assert abs(direct - embedded) < 2e-13


def test_equivalence_branch_cancels_test_carrier_mass():
    mu, radius = 3.7, 1.4
    values = [equivalence_branch_omega(mu, m, radius) for m in (0.05, 0.5, 1.0, 12.0)]
    assert max(values) - min(values) < 2e-15
    assert abs(values[0] - math.sqrt(mu / radius**3)) < 2e-15


def test_nbody_relative_embedding_has_standard_sum_source_parameter():
    G, M1, M2, r = 0.42, 2.0, 0.7, 1.9
    got = nbody_role_embedding(G, M1, M2, r)
    expected = math.sqrt(G * (M1 + M2) / r**3)
    assert abs(got - expected) < 2e-15


def test_mass_exponents_separate_three_historical_profiles():
    audits = {row.profile_id: row for row in profile_audits()}
    assert audits["GREMLIN_BESTIARY_INTERNAL_SERVICE_CADENCE"].omega_sq_mass_exponent == -1.0
    assert audits["GREMLIN_BESTIARY_INTERNAL_SERVICE_CADENCE"].period_mass_exponent == 0.5
    assert audits["CIEL_FOUNDATION_P3_SOURCE_MASS"].omega_sq_mass_exponent == 1.0
    assert audits["CIEL_FOUNDATION_P3_SOURCE_MASS"].period_mass_exponent == -0.5
    assert audits["CIEL_OBJECTCARD_LEGACY"].omega_sq_mass_exponent == -3.0
    assert audits["CIEL_OBJECTCARD_LEGACY"].period_mass_exponent == 1.5


def test_objectcard_exponent_needs_extra_minus_two_source_charge_scaling_if_mass_is_inertial():
    required = objectcard_required_source_charge_exponent(inertial_exponent=1.0)
    assert required == -2.0
    assert omega_sq_mass_exponent(source_exponent=required, inertial_exponent=1.0) == -3.0
    assert period_mass_exponent_from_omega_sq(-3.0) == 1.5


def test_fixed_source_fixed_charge_inertial_mass_cannot_reproduce_objectcard_exponent():
    exponent = omega_sq_mass_exponent(source_exponent=0.0, charge_exponent=0.0, inertial_exponent=1.0)
    assert exponent == -1.0
    assert exponent != -3.0


def test_invalid_role_values_fail_closed():
    bad = [
        lambda: role_separated_omega(0.0, 1.0, 1.0, 1.0),
        lambda: role_separated_omega(1.0, 0.0, 1.0, 1.0),
        lambda: role_separated_omega(1.0, 1.0, 0.0, 1.0),
        lambda: role_separated_omega(1.0, 1.0, 1.0, 0.0),
        lambda: bestiary_role_embedding(float("nan"), 1.0),
        lambda: foundation_role_embedding(1.0, float("inf")),
        lambda: objectcard_required_source_charge_exponent(inertial_exponent=float("nan")),
    ]
    for fn in bad:
        try:
            fn()
        except MassRoleFirewallError:
            pass
        else:
            raise AssertionError("invalid mass-role input accepted")
