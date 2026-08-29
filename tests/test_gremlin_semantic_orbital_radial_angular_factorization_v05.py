import math

from tools.gremlin_semantic_orbital_radial_angular_factorization_v05 import (
    ALPHA_M,
    DELTA7,
    KAPPA,
    RadialAngularAuditError,
    classify_c7,
    constant_R_step,
    partial_c7_coefficient,
    semantic_mass_unrounded,
    summarize,
)


def test_constant_R_mass_step_is_kappa_alpha_exactly_before_rounding():
    R = 0.22852419636
    for k in (1, 2, 17, 74, 114):
        delta = semantic_mass_unrounded(k + 1, R) - semantic_mass_unrounded(k, R)
        assert abs(delta - KAPPA * ALPHA_M) < 2e-17
        assert abs(delta - constant_R_step()) < 2e-17


def test_c7_classifier_recovers_all_global_heptad_shifts():
    reference = [0.11 + 0.07 * j for j in range(36)]
    for n in range(7):
        vector = [x - n * DELTA7 for x in reference]
        got, residual = classify_c7(reference, vector)
        assert got == n
        assert abs(residual) < 2e-15


def test_radial_mass_progression_is_separable_from_nontrivial_c7_schedule():
    ks = [float(k) for k in range(1, 33)]
    # Deliberately use a non-monotonic angular schedule.
    ns = [float(v) for v in ([0, 3, 1, 2, 0, 1, 0, 3] * 4)]
    masses = [semantic_mass_unrounded(int(k), 0.23) for k in ks]
    summary = summarize(masses, ks, ns)
    assert summary.mass_vs_phase_index_corr > 1.0 - 1e-14
    assert abs(summary.c7_coefficient_after_phase_index) < 1e-14


def test_partial_c7_coefficient_detects_injected_angular_mass_term():
    ks = [float(k) for k in range(1, 33)]
    ns = [float(v) for v in ([0, 3, 1, 2, 0, 1, 0, 3] * 4)]
    injected = 0.0125
    masses = [semantic_mass_unrounded(int(k), 0.23) + injected * n for k, n in zip(ks, ns)]
    coeff = partial_c7_coefficient(masses, ks, ns)
    assert abs(coeff - injected) < 1e-14


def test_classifier_and_mass_model_fail_closed_on_bad_inputs():
    bad = [
        lambda: semantic_mass_unrounded(0, 0.2),
        lambda: semantic_mass_unrounded(1, -0.1),
        lambda: semantic_mass_unrounded(1, float("nan")),
        lambda: classify_c7([0.0] * 35, [0.0] * 35),
    ]
    for fn in bad:
        try:
            fn()
        except RadialAngularAuditError:
            pass
        else:
            raise AssertionError("invalid radial/angular audit input accepted")
