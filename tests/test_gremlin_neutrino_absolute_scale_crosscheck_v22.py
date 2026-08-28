from __future__ import annotations

import copy
import math
import pytest

from tools.gremlin_neutrino_absolute_scale_crosscheck_v22 import (
    NeutrinoAbsoluteScaleCrosscheckError,
    absolute_masses_from_ratio_and_splittings_v22,
    build_neutrino_absolute_scale_crosscheck_v22,
    resonance_triplet_from_absolute_masses_v22,
    validate_neutrino_absolute_scale_crosscheck_v22,
)

BASE = dict(
    audit_id="abs-scale-v22",
    delta_m21_sq_eV2=7.42e-5,
    delta_m31_sq_eV2=2.517e-3,
    structural_ratio_squared=7.0/6.0,
    declared_sum_eV=0.098,
    mu0_witness_a_eV2=0.01,
    mu0_witness_b_eV2=0.02,
    ratio_source_ref="Reality_as_Graded_Projection:neutrino m2/m1=sqrt(7/6)",
    declared_sum_source_ref="Reality_as_Graded_Projection:Sigma_mnu=mK=98meV",
    mass_resonance_source_ref="Theory_of_Everything:m_i^2=mu0(1-R_i)",
)


def test_ratio_plus_splittings_derives_absolute_masses_and_sum():
    receipt = build_neutrino_absolute_scale_crosscheck_v22(**BASE)
    m = receipt["absolute_masses_meV"]
    assert m[0] == pytest.approx(21.0997630318, rel=1e-10)
    assert m[1] == pytest.approx(22.7903488345, rel=1e-10)
    assert m[2] == pytest.approx(54.4260966816, rel=1e-10)
    assert receipt["mass_sum_meV"] == pytest.approx(98.3162085480, rel=1e-10)
    assert receipt["declared_sum_not_used_to_derive_masses"] is True
    assert float.fromhex(receipt["sum_crosscheck_relative_error_f64_hex"]) < 0.004


def test_analytic_7_over_6_relation_is_exact_at_binary64_tolerance():
    m = absolute_masses_from_ratio_and_splittings_v22(m2_over_m1=math.sqrt(7.0/6.0), delta_m21_sq_eV2=7.42e-5, delta_m31_sq_eV2=2.517e-3)
    assert m[0]**2 == pytest.approx(6.0*7.42e-5, rel=1e-14)
    assert m[1]**2 == pytest.approx(7.0*7.42e-5, rel=1e-14)
    assert m[2]**2-m[0]**2 == pytest.approx(2.517e-3, rel=1e-14)


def test_absolute_masses_still_leave_continuous_mu0_family():
    receipt = build_neutrino_absolute_scale_crosscheck_v22(**BASE)
    assert receipt["mu0_remains_nonunique_after_absolute_mass_scale"] is True
    assert receipt["mass_resonance_mu0_status"] == "STILL_UNBOUND_GENERIC_MASS_SCALE_PARAMETER"
    assert receipt["remaining_source_spectrum_degrees"] == ["mu0 normalization", "three-mode symbolic-projector selection"]


def test_too_small_mu0_fails_closed():
    masses = absolute_masses_from_ratio_and_splittings_v22(m2_over_m1=math.sqrt(7.0/6.0), delta_m21_sq_eV2=7.42e-5, delta_m31_sq_eV2=2.517e-3)
    with pytest.raises(NeutrinoAbsoluteScaleCrosscheckError):
        resonance_triplet_from_absolute_masses_v22(masses_eV=masses, mu0_eV2=0.001)


def test_receipt_tamper_fails():
    receipt = build_neutrino_absolute_scale_crosscheck_v22(**BASE)
    assert validate_neutrino_absolute_scale_crosscheck_v22(receipt)
    tampered = copy.deepcopy(receipt)
    tampered["mass_resonance_mu0_status"] = "CLOSED"
    with pytest.raises(NeutrinoAbsoluteScaleCrosscheckError):
        validate_neutrino_absolute_scale_crosscheck_v22(tampered)
