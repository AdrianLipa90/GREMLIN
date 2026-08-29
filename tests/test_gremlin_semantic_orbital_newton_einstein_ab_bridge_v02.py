import cmath
import math

from tools.gremlin_semantic_orbital_imaginary_real_bridge_v01 import OMEGA0, scheduler_omega
from tools.gremlin_semantic_orbital_newton_einstein_ab_bridge_v02 import (
    circular_specific_angular_momentum,
    kepler_omega,
    newton_potential,
    phase_factor,
    rotation_phase_per_orbit,
    scheduler_kepler_bundle,
    total_phase,
    transported_real_relation,
    transported_semantic_value,
    weak_field_apsidal_phase,
)


def test_parent_scheduler_equals_kepler_bundle_frequency():
    for mass, radius in [(0.05, 0.39), (1.0, 1.0), (2.6, 5.2)]:
        bundle = scheduler_kepler_bundle(mass, radius, tau=1.0, omega0=OMEGA0)
        assert abs(bundle["omega"] - scheduler_omega(mass, radius)) < 2e-12


def test_newton_circular_balance_identity():
    mu, r = 2.3, 1.7
    ell = circular_specific_angular_momentum(mu, r)
    centripetal = ell**2 / r**3
    newton = mu / r**2
    assert abs(centripetal - newton) < 1e-12
    assert newton_potential(mu, r) < 0.0


def test_u1_phase_contributions_add_and_multiply_equivalently():
    rot, gr, ab = -0.31, 0.07, 0.42
    lhs = phase_factor(rot, gr, ab)
    rhs = cmath.exp(1j * rot) * cmath.exp(1j * gr) * cmath.exp(1j * ab)
    assert abs(lhs - rhs) < 1e-12
    assert abs(total_phase(rot, gr, ab) - (rot + gr + ab)) < 1e-15


def test_common_total_transport_cancels_from_real_pair_relation():
    common = 0.63
    base = transported_real_relation(1.2, 0.1, 0.0, 0.8, 0.7, 0.0)
    moved = transported_real_relation(1.2, 0.1, common, 0.8, 0.7, common)
    assert abs(base - moved) < 1e-12


def test_differential_total_transport_enters_real_relation_as_phase_difference():
    ma, mb = 1.2, 0.8
    pa, pb = 0.1, 0.7
    ta, tb = -0.2, 0.35
    got = transported_real_relation(ma, pa, ta, mb, pb, tb)
    expected = ma * mb * math.cos((pb - pa) + (tb - ta))
    assert abs(got - expected) < 1e-12


def test_rotation_phase_is_frame_rate_times_kepler_period():
    mu, r, omega_rot = 4.0, 2.0, 0.25
    omega = kepler_omega(mu, r)
    expected = -omega_rot * (2.0 * math.pi / omega)
    assert abs(rotation_phase_per_orbit(mu, r, omega_rot) - expected) < 1e-12


def test_weak_field_apsidal_phase_scaling():
    mu, r, c = 2.0, 10.0, 100.0
    tau = weak_field_apsidal_phase(mu, r, c)
    assert abs(tau - 6.0 * math.pi * mu / (r * c**2)) < 1e-15
    assert abs(weak_field_apsidal_phase(mu, 2.0 * r, c) - tau / 2.0) < 1e-15


def test_semantic_law_uses_same_transported_lifted_phase():
    B, omega, N, A_R, phi = 2.0, 3.0, 4.0, 5.0, 0.7
    tau = 0.2
    base = transported_semantic_value(B, omega, N, A_R, phi, 0.0)
    moved = transported_semantic_value(B, omega, N, A_R, phi, tau)
    assert abs((moved - base) - (B * omega * N / A_R) * tau) < 1e-12


def test_invalid_domains_fail_closed():
    for mu, r in [(0.0, 1.0), (-1.0, 1.0), (1.0, 0.0)]:
        try:
            kepler_omega(mu, r)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid Kepler domain accepted")
    try:
        weak_field_apsidal_phase(1.0, 1.0, 0.0)
    except ValueError:
        pass
    else:
        raise AssertionError("zero c accepted")
