import lzma
import math

from tools.gremlin_nufit61_flavor_discriminant_map_v27 import (
    PMNSPoint,
    SpectrumPoint,
    _unitarity_residual,
    extract_profile_bestfit_coordinates,
    mutual_information_uniform,
    pmns_matrix,
    scan_discriminant,
    smeared_probability_matrix,
    vacuum_probability_matrix,
)


PMNS = PMNSPoint(0.3088, 0.0222, 0.47, 210.0)
FREE = SpectrumPoint(7.54e-5, 2.511e-3)
RATIO33 = SpectrumPoint(7.59e-5, 33.0 * 7.59e-5)


def test_pmns_is_unitary():
    assert _unitarity_residual(pmns_matrix(PMNS)) < 1e-14


def test_zero_baseline_is_identity_channel():
    p = vacuum_probability_matrix(PMNS, FREE, 0.0)
    for a in range(3):
        for b in range(3):
            target = 1.0 if a == b else 0.0
            assert math.isclose(p[a][b], target, abs_tol=2e-15)
    assert math.isclose(mutual_information_uniform(p), math.log2(3.0), rel_tol=1e-14)


def test_probability_conservation_over_nonzero_baseline():
    p = vacuum_probability_matrix(PMNS, FREE, 517.0)
    for row in p:
        assert math.isclose(sum(row), 1.0, abs_tol=2e-12)
        assert all(0.0 <= value <= 1.0 + 1e-14 for value in row)


def test_smearing_preserves_probability_conservation():
    p = smeared_probability_matrix(PMNS, FREE, 517.0, 0.10)
    for row in p:
        assert math.isclose(sum(row), 1.0, abs_tol=2e-12)


def test_identical_spectra_have_zero_discriminant():
    result = scan_discriminant(PMNS, FREE, FREE, max_l_over_e=1000.0, samples=201)
    assert result["largest_probability_separation"]["max_abs_delta_probability"] == 0.0
    assert result["largest_mutual_information_separation"]["delta_mutual_information_bits"] == 0.0


def test_ratio33_shift_produces_nonzero_flavor_discriminant():
    result = scan_discriminant(PMNS, FREE, RATIO33, max_l_over_e=2000.0, samples=501)
    assert result["largest_probability_separation"]["max_abs_delta_probability"] > 0.0
    assert abs(result["largest_mutual_information_separation"]["delta_mutual_information_bits"]) > 0.0
    assert result["largest_probability_separation"]["channel"] in {
        "e->e", "e->mu", "e->tau", "mu->e", "mu->mu", "mu->tau", "tau->e", "tau->mu", "tau->tau"
    }


def test_profile_coordinate_parser_uses_minimum_rows(tmp_path):
    path = tmp_path / "profiles.txt.xz"
    content = """# T13/T12 projection:\n0.0220 0.305 1.0\n0.0222 0.309 0.0\n# T23/DMA/DCP projection:\n0.47 2.510 210.0 0.0\n0.50 2.520 180.0 2.0\n# DMS/DMA projection:\n-4.123 2.510 0.0\n-4.122 2.515 1.0\n# DMS projection:\n-4.123 0.0\n"""
    with lzma.open(path, "wt", encoding="utf-8") as handle:
        handle.write(content)
    result = extract_profile_bestfit_coordinates(path)
    point = result["pmns"]
    spectrum = result["spectrum"]
    assert point.sin2_theta13 == 0.0222
    assert point.sin2_theta12 == 0.309
    assert point.sin2_theta23 == 0.47
    assert point.delta_cp_deg == 210.0
    assert math.isclose(spectrum.dm21_eV2, 10.0 ** -4.123, rel_tol=1e-15)
    assert spectrum.dm31_eV2 == 2.510e-3
    assert all(value == 0.0 for value in result["profile_minima_delta_chi2"].values())
