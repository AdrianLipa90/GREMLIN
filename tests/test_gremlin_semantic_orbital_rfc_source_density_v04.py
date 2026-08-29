import math

from tools.gremlin_semantic_orbital_rfc_source_density_v04 import (
    DELTA7,
    KAPPA,
    SemanticSourceDensityError,
    adjacent_lift_increment,
    complex_semantic_orbital,
    full_turn_increment,
    lift_index,
    lifted_phase,
    source_density,
    source_prefactor,
)


def test_integer_lift_coordinate_matches_heptad_plus_winding():
    phi0 = -2.84156
    for n in range(7):
        for w in (-2, -1, 0, 1, 2):
            q = lift_index(n, w)
            assert abs(lifted_phase(phi0, n, w) - (phi0 + q * DELTA7)) < 1e-15


def test_complex_orbital_is_periodic_under_one_full_c7_turn():
    phi0 = -2.84156
    m = 1.7
    z0 = complex_semantic_orbital(m, phi0, 0, 0)
    z1 = complex_semantic_orbital(m, phi0, 0, 1)
    assert abs(z1 - z0) < 2e-15


def test_source_density_retains_winding_increment():
    args = dict(B=0.7, omega=3.2, occupation=5.0, area=1.4, radius=2.1)
    rho0 = source_density(**args, phi0=0.2, n=4, winding=0)
    rho1 = source_density(**args, phi0=0.2, n=4, winding=1)
    assert abs((rho1 - rho0) - full_turn_increment(**args)) < 2e-14


def test_adjacent_integer_lift_states_form_uniform_density_ladder():
    args = dict(B=1.1, omega=2.4, occupation=3.0, area=0.8, radius=1.9)
    q = source_prefactor(**args)
    phi0 = -0.4
    # q_lift increases by one when (n,w) goes (3,0) -> (2,0).
    rho_a = source_density(**args, phi0=phi0, n=3, winding=0)
    rho_b = source_density(**args, phi0=phi0, n=2, winding=0)
    assert abs((rho_b - rho_a) - adjacent_lift_increment(**args)) < 2e-14
    assert abs(adjacent_lift_increment(**args) - q * DELTA7) < 1e-15


def test_current_c7_classes_have_exact_normalized_step_on_lifted_branch():
    phi0 = -2.84156
    # Normalize the prefactor to one: B=omega=N=A=R=1.
    rho = [source_density(1.0, 1.0, 1.0, 1.0, 1.0, phi0, n, 0) for n in range(4)]
    for a, b in zip(rho, rho[1:]):
        assert abs((b - a) + DELTA7) < 2e-15
    assert abs(rho[0] - (phi0 + KAPPA)) < 1e-15


def test_zero_occupation_is_zero_source_density():
    rho = source_density(2.0, 3.0, 0.0, 4.0, 5.0, 0.7, 2, 1)
    assert rho == 0.0


def test_invalid_source_inputs_fail_closed():
    bad = [
        lambda: source_prefactor(1.0, 0.0, 1.0, 1.0, 1.0),
        lambda: source_prefactor(1.0, 1.0, -1.0, 1.0, 1.0),
        lambda: source_prefactor(1.0, 1.0, 1.0, 0.0, 1.0),
        lambda: source_prefactor(1.0, 1.0, 1.0, 1.0, 0.0),
        lambda: lifted_phase(0.0, 7, 0),
        lambda: lifted_phase(0.0, 0, 0.5),
        lambda: complex_semantic_orbital(0.0, 0.0, 0, 0),
        lambda: source_prefactor(float("nan"), 1.0, 1.0, 1.0, 1.0),
    ]
    for fn in bad:
        try:
            fn()
        except SemanticSourceDensityError:
            pass
        else:
            raise AssertionError("invalid source-density input accepted")
