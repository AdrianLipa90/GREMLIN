import math

from tools.gremlin_semantic_orbital_imaginary_real_bridge_v01 import (
    DELTA7,
    KAPPA,
    audit_heptad_shift,
    complex_orbital,
    kepler_form_omega,
    lattice_phase,
    pair_carrier,
    real_projection,
    scheduler_omega,
    semantic_value,
    transport,
    wrap_pi,
)


def test_c7_lattice_intention_index_three_from_reference():
    phi0 = -2.84156
    phi = lattice_phase(phi0, 3, wrapped=True)
    assert abs(phi - 0.7488316041026213) < 1e-12
    audit = audit_heptad_shift(wrap_pi(phi - phi0))
    assert audit.n == 3
    assert abs(audit.residual) < 1e-12


def test_serialized_intention_vector_reconstruction_is_close_to_exact_c7_value():
    exact = lattice_phase(-2.84156, 3, wrapped=True)
    serialized_vector_reconstruction = 0.7488316043875249
    assert abs(serialized_vector_reconstruction - exact) < 3e-10


def test_current_observed_shifts_map_to_indices_zero_through_three():
    observed = [0.0, -0.8975978930626973, -1.795195809729364, -2.6927937027920614]
    indices = sorted(audit_heptad_shift(x).n for x in observed)
    assert indices == [0, 1, 2, 3]
    assert max(abs(audit_heptad_shift(x).residual) for x in observed) < 1e-8


def test_semantic_law_requires_lifted_phase_to_preserve_winding():
    base = semantic_value(1.0, 1.0, 1.0, 1.0, 0.25)
    wound = semantic_value(1.0, 1.0, 1.0, 1.0, 0.25 + 2.0 * math.pi)
    assert abs((wound - base) - 2.0 * math.pi) < 1e-12
    assert KAPPA > 0.0


def test_complex_orbital_norm_and_real_projection():
    za = complex_orbital(2.0, 0.3)
    zb = complex_orbital(3.0, 1.1)
    assert abs(abs(za) - 2.0) < 1e-12
    expected = 6.0 * math.cos(0.8)
    assert abs(real_projection(za, zb) - expected) < 1e-12
    assert abs(real_projection(za, zb) - real_projection(zb, za)) < 1e-12


def test_common_global_phase_cancels_from_pair_carrier():
    za = complex_orbital(1.4, -0.2)
    zb = complex_orbital(0.7, 0.9)
    alpha = 0.731
    rot = complex(math.cos(alpha), math.sin(alpha))
    assert abs(pair_carrier(za * rot, zb * rot) - pair_carrier(za, zb)) < 1e-12


def test_differential_holonomy_enters_only_as_relative_phase():
    za = complex_orbital(1.2, 0.1)
    zb = complex_orbital(0.8, 0.5)
    ta, tb = 0.11, -0.23
    lhs = pair_carrier(transport(za, ta), transport(zb, tb))
    rhs = pair_carrier(za, zb) * complex(math.cos(tb - ta), math.sin(tb - ta))
    assert abs(lhs - rhs) < 1e-12


def test_scheduler_is_exact_kepler_form_reparameterization():
    profiles = [
        (0.05, 0.39),
        (0.70, 0.55),
        (0.80, 0.72),
        (0.90, 0.90),
        (1.00, 1.00),
        (1.10, 1.15),
        (1.20, 1.35),
        (1.60, 2.20),
        (2.60, 5.20),
    ]
    for mass, radius in profiles:
        assert abs(scheduler_omega(mass, radius) - kepler_form_omega(mass, radius)) < 2e-12


def test_invalid_sources_fail_closed():
    for bad_mass in (0.0, -1.0, float("nan")):
        try:
            complex_orbital(bad_mass, 0.0)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid semantic mass accepted")
    try:
        semantic_value(1.0, 1.0, 1.0, 0.0, 0.0)
    except ValueError:
        pass
    else:
        raise AssertionError("zero A_R accepted")
