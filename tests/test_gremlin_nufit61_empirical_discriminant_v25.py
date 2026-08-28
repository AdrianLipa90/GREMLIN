import math

import pytest

from tools.gremlin_nufit61_empirical_discriminant_v25 import (
    GRADED_PROJECTION_M2_M1,
    NUFIT61_IC24_WITH_SK_NO,
    OscillationSnapshot,
    evaluate_tetrahedron_discriminant,
    graded_projection_spectrum,
    tetrahedron_ratio_prediction,
    tetrahedron_spectrum_from_dm21,
)


def test_tetrahedron_ratio_is_exactly_33():
    assert tetrahedron_ratio_prediction() == 33.0


def test_current_nufit61_ratio_and_pull_are_stable():
    receipt = evaluate_tetrahedron_discriminant()
    assert math.isclose(receipt["observed_best_fit_splitting_ratio"], 33.31564282871169, rel_tol=1e-14)
    assert 0.5 < receipt["ratio_pull_diagonal"] < 0.8
    assert 0.5 < receipt["dm31_pull_diagonal"] < 0.8
    assert receipt["verdict"] == "COMPATIBLE_NOT_DISCRIMINATING"


def test_current_three_sigma_rectangles_overlap():
    receipt = evaluate_tetrahedron_discriminant()
    assert receipt["has_3sigma_rectangular_overlap"] is True
    pred_lo, pred_hi = receipt["predicted_3sigma_dm31_interval_eV2"]
    fit_lo, fit_hi = receipt["nufit_3sigma_dm31_interval_eV2"]
    assert max(pred_lo, fit_lo) <= min(pred_hi, fit_hi)


def test_tetrahedron_spectrum_reproduces_dm21_and_exact_ratio():
    m1, m2, m3 = tetrahedron_spectrum_from_dm21(NUFIT61_IC24_WITH_SK_NO.dm21_eV2)
    assert math.isclose(m2 / m1, 2.0, rel_tol=1e-15)
    assert math.isclose(m3 / m1, 10.0, rel_tol=1e-15)
    assert math.isclose(m2 * m2 - m1 * m1, NUFIT61_IC24_WITH_SK_NO.dm21_eV2, rel_tol=1e-15)
    assert math.isclose((m3 * m3 - m1 * m1) / (m2 * m2 - m1 * m1), 33.0, rel_tol=1e-15)


def test_graded_projection_spectrum_reproduces_input_splittings():
    m1, m2, m3 = graded_projection_spectrum(
        NUFIT61_IC24_WITH_SK_NO.dm21_eV2,
        NUFIT61_IC24_WITH_SK_NO.dm31_eV2,
    )
    assert math.isclose(m2 / m1, GRADED_PROJECTION_M2_M1, rel_tol=1e-15)
    assert math.isclose(m2 * m2 - m1 * m1, NUFIT61_IC24_WITH_SK_NO.dm21_eV2, rel_tol=1e-14)
    assert math.isclose(m3 * m3 - m1 * m1, NUFIT61_IC24_WITH_SK_NO.dm31_eV2, rel_tol=1e-14)


def test_current_branch_sums_are_recorded_without_promotion():
    receipt = evaluate_tetrahedron_discriminant()
    assert math.isclose(receipt["tetrahedron_sum_eV"], 0.06516013607515975, rel_tol=1e-14)
    assert math.isclose(receipt["graded_projection_sum_eV"], 0.09867025871444429, rel_tol=1e-14)
    assert receipt["claim_promotion"] is False
    assert receipt["global_fit_data_are_external_input"] is True


def test_diagonal_pull_firewall_is_explicit():
    receipt = evaluate_tetrahedron_discriminant()
    assert receipt["covariance_used"] is False
    assert receipt["diagonal_pull_is_approximation"] is True
    assert "correlated chi-square" in receipt["next_required_test"]


def test_cross_repo_pins_are_present():
    pins = evaluate_tetrahedron_discriminant()["cross_repo_pins"]
    assert set(pins) == {
        "TIR_phase_clock_area_scale",
        "IDT_relational_lapse_rate",
        "RFC_relational_lapse_normal_phase_rate",
        "SOH_half_interface",
        "GREMLIN_framework_holonomy_firewall_v24",
    }
    assert all(len(sha) == 40 for sha in pins.values())


def test_future_large_mismatch_triggers_tension_gate():
    s = NUFIT61_IC24_WITH_SK_NO
    shifted = OscillationSnapshot(
        name="synthetic future stress case",
        dm21_eV2=s.dm21_eV2,
        dm21_plus_eV2=s.dm21_plus_eV2,
        dm21_minus_eV2=s.dm21_minus_eV2,
        dm21_3sigma_low_eV2=s.dm21_3sigma_low_eV2,
        dm21_3sigma_high_eV2=s.dm21_3sigma_high_eV2,
        dm31_eV2=2.90e-3,
        dm31_plus_eV2=0.010e-3,
        dm31_minus_eV2=0.010e-3,
        dm31_3sigma_low_eV2=2.87e-3,
        dm31_3sigma_high_eV2=2.93e-3,
        source_url="stress://future",
    )
    receipt = evaluate_tetrahedron_discriminant(shifted)
    assert receipt["has_3sigma_rectangular_overlap"] is False
    assert receipt["verdict"] == "TENSION_REQUIRES_FULL_CORRELATED_LIKELIHOOD"


def test_invalid_inputs_fail_closed():
    with pytest.raises(ValueError):
        tetrahedron_spectrum_from_dm21(0.0)
    with pytest.raises(ValueError):
        graded_projection_spectrum(1.0, 0.0)
