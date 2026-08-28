import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "provenance" / "NUFIT61_TIR_RATIO33_CORRELATED_SURFACE_RECEIPT_V2_6.json"


def _receipt():
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def test_receipt_is_non_promoting_and_successful():
    r = _receipt()
    assert r["status"] == "OFFICIAL_SURFACE_REPLAY_COMPATIBLE__CLAIM_PROMOTION_FALSE"
    assert r["github_actions"]["conclusion"] == "success"
    assert r["statistical_firewall"]["claim_promotion"] is False


def test_exact_ratio_identity_is_locked():
    r = _receipt()
    assert r["tested_relation"]["mass_ratio"] == [1, 2, 10]
    assert "= 33" in r["tested_relation"]["exact_identity"]
    assert r["tested_relation"]["surface_line"] == "Delta_m31^2 = 33 Delta_m21^2"


def test_both_official_surface_replays_are_inside_2d_one_sigma_reference():
    r = _receipt()
    threshold = r["confidence_reference"]["two_dof_one_sigma_delta_chi2_approx"]
    assert r["confidence_reference"]["both_ratio_line_minima_inside_two_dof_one_sigma_contour"] is True
    assert r["results"]["TBoff-NO"]["delta_chi2_min_on_ratio33_line"] < threshold
    assert r["results"]["TByes-NO"]["delta_chi2_min_on_ratio33_line"] < threshold


def test_source_hashes_and_acquisition_firewall_are_locked():
    r = _receipt()
    assert r["results"]["TBoff-NO"]["source_sha256"] == "58b113927c13f55925558e1ef0a598b357a237cde5c466b9f660cc08569970f6"
    assert r["results"]["TByes-NO"]["source_sha256"] == "c74bd6df84297a8429cd3b9e1239751cd0762756f1ec0c2a31248d78570b26e4"
    assert all(
        result["acquisition_mode"] == "explicit_insecure_tls_fallback_with_sha256_pin"
        for result in r["results"].values()
    )


def test_profile_minima_obey_exact_ratio_numerically():
    r = _receipt()
    for result in r["results"].values():
        dm21 = result["delta_m21_sq_eV2_at_profile_min"]
        dm31 = result["delta_m31_sq_eV2_at_profile_min"]
        assert abs(dm31 / dm21 - 33.0) < 1e-12
