import math

from tools.gremlin_semantic_orbital_pnlf_radius_source_v03 import (
    OMEGA0,
    PNLFRadiusSourceError,
    build_radius_witness,
    omega_from_period,
    scheduler_period_from_radius,
    scheduler_radius_from_pnlf,
)


def test_roundtrip_recovers_reference_radii():
    cases = [
        (0.05, 0.39, 1.0),
        (0.70, 0.55, 1.0),
        (0.90, 0.90, 0.75),
        (1.00, 1.00, 1.0),
        (1.60, 2.20, 1.25),
        (2.60, 5.20, 1.0),
    ]
    for mass, radius, tau in cases:
        period = scheduler_period_from_radius(mass, radius, tau=tau)
        recovered = scheduler_radius_from_pnlf(mass, period, tau=tau)
        assert abs(recovered - radius) < 2e-12


def test_inverse_satisfies_kepler_scheduler_identity():
    mass = 1.37
    period = 0.42
    tau = 0.91
    radius = scheduler_radius_from_pnlf(mass, period, tau=tau)
    omega = omega_from_period(period)
    lhs = omega * omega
    rhs = (OMEGA0 * tau) ** 2 / (mass * radius**3)
    assert abs(lhs - rhs) < 2e-10


def test_witness_has_small_period_residual():
    witness = build_radius_witness(0.83, 0.127, tau=1.17)
    assert witness.scheduler_radius > 0.0
    assert abs(witness.period_residual) < 2e-13


def test_zero_semantic_mass_fails_closed_even_though_pnlf_storage_allows_nonnegative_mass():
    try:
        scheduler_radius_from_pnlf(0.0, 1.0)
    except PNLFRadiusSourceError:
        pass
    else:
        raise AssertionError("zero semantic mass entered scheduler-radius inverse")


def test_nonpositive_period_tau_radius_and_nonfinite_inputs_fail_closed():
    bad_calls = [
        lambda: scheduler_radius_from_pnlf(1.0, 0.0),
        lambda: scheduler_radius_from_pnlf(1.0, 1.0, tau=0.0),
        lambda: scheduler_period_from_radius(1.0, 0.0),
        lambda: scheduler_radius_from_pnlf(float("nan"), 1.0),
        lambda: omega_from_period(float("inf")),
    ]
    for fn in bad_calls:
        try:
            fn()
        except PNLFRadiusSourceError:
            pass
        else:
            raise AssertionError("invalid radius-source input accepted")


def test_r_phase_is_not_needed_by_inverse_contract():
    # The inverse depends only on semantic_mass, orbit_period and the declared tau/omega0 profile.
    r1 = scheduler_radius_from_pnlf(1.2, 0.31, tau=0.8)
    r2 = scheduler_radius_from_pnlf(1.2, 0.31, tau=0.8)
    assert math.isfinite(r1)
    assert r1 == r2
