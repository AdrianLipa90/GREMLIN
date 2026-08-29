import math

from tools.gremlin_bestiary_mass_role_typed_scheduler_v07 import (
    BESTIARY_COMPAT,
    EQUIVALENCE_CANDIDATE,
    FOUNDATION_COMPAT,
    TypedSchedulerError,
    bestiary_species_witness,
    cadence_rank_typed,
    equivalence_candidate_witness,
    foundation_witness,
    general_radius_from_period,
)
from tools.gremlin_bestiary_orbital_scheduler_v02 import PROFILES, cadence_rank, service_omega


def test_all_current_bestiary_species_match_legacy_frequency():
    residuals = []
    for species, profile in PROFILES.items():
        witness = bestiary_species_witness(species)
        assert witness.mass_role_profile_id == BESTIARY_COMPAT
        expected = service_omega(profile)
        residuals.append(abs(witness.omega - expected))
        assert abs(witness.omega - expected) < 2e-12
        assert witness.m_inertial == profile.mass
        assert witness.radius == profile.radius
        assert witness.q_coupling == 1.0
    assert max(residuals) <= 2e-12


def test_typed_cadence_order_matches_legacy_order():
    expected = cadence_rank(PROFILES.keys())
    assert cadence_rank_typed() == expected


def test_foundation_profile_matches_T_squared_equals_r_cubed_over_M():
    for M, r in ((0.4, 0.2), (0.94, 0.63), (1.7, 0.81)):
        witness = foundation_witness(M, r, carrier_mass=3.7)
        assert witness.mass_role_profile_id == FOUNDATION_COMPAT
        expected_period = math.sqrt(r**3 / M)
        assert abs(witness.period - expected_period) < 2e-14
        assert witness.q_coupling == witness.m_inertial


def test_equivalence_candidate_frequency_is_carrier_mass_independent():
    mu, r = 2.7, 1.3
    ws = [equivalence_candidate_witness(mu, m, r) for m in (0.1, 0.7, 1.0, 9.0)]
    assert all(w.mass_role_profile_id == EQUIVALENCE_CANDIDATE for w in ws)
    assert max(w.omega for w in ws) - min(w.omega for w in ws) < 2e-15


def test_general_radius_inverse_roundtrips_each_bestiary_witness():
    for species in PROFILES:
        w = bestiary_species_witness(species)
        recovered = general_radius_from_period(
            w.period,
            mu_source=w.mu_source,
            q_coupling=w.q_coupling,
            m_inertial=w.m_inertial,
        )
        assert abs(recovered - w.radius) < 2e-12


def test_unknown_species_and_invalid_values_fail_closed():
    bad = [
        lambda: bestiary_species_witness("DRAGON"),
        lambda: bestiary_species_witness("HOUND", tau=0.0),
        lambda: foundation_witness(0.0, 1.0),
        lambda: equivalence_candidate_witness(1.0, 0.0, 1.0),
        lambda: general_radius_from_period(0.0, mu_source=1.0, q_coupling=1.0, m_inertial=1.0),
    ]
    for fn in bad:
        try:
            fn()
        except TypedSchedulerError:
            pass
        else:
            raise AssertionError("invalid typed scheduler input accepted")
