from __future__ import annotations

import copy
import pytest

from tools.gremlin_resonance_mass_source_no_go_v21 import (
    ResonanceMassSourceNoGoError,
    build_resonance_mass_source_no_go_v21,
    normalized_resonant_hamiltonian_gaps_v21,
    resonance_triplet_from_splittings_v21,
    validate_resonance_mass_source_no_go_v21,
)

BASE = dict(
    audit_id="source-spectrum-v21",
    delta_m21_sq_eV2=7.42e-5,
    delta_m31_sq_eV2=2.517e-3,
    witness_a_mu0_eV2=0.01,
    witness_a_R1=0.80,
    witness_b_mu0_eV2=0.02,
    witness_b_R1=0.90,
    mass_resonance_source_ref="Theory_of_Everything.pdf:m^2=mu0(1-R)",
    resonant_hamiltonian_source_ref="Theory_of_Everything.pdf:H_sT=sum omega_n|S_n><S_n|",
)


def test_two_distinct_resonance_spectra_reproduce_same_mass_splittings():
    receipt = build_resonance_mass_source_no_go_v21(**BASE)
    assert receipt["same_mass_splittings"] is True
    assert receipt["different_resonance_triplets"] is True
    assert receipt["different_normalized_resonant_hamiltonian_gaps"] is True
    assert receipt["source_side_M_I_identified"] is False
    assert receipt["belzebub_verdict"] == "CURRENT_MASS_SPLITTINGS_DO_NOT_IDENTIFY_RESONANCE_SOURCE_SPECTRUM"


def test_family_formula_exactly_reconstructs_splittings():
    r = resonance_triplet_from_splittings_v21(mu0_eV2=0.015, R1=0.85, delta_m21_sq_eV2=7.42e-5, delta_m31_sq_eV2=2.517e-3)
    assert abs(0.015*(r[0]-r[1]) - 7.42e-5) < 1e-16
    assert abs(0.015*(r[0]-r[2]) - 2.517e-3) < 1e-16


def test_resonant_hamiltonian_log_gaps_change_across_family():
    a = resonance_triplet_from_splittings_v21(mu0_eV2=0.01, R1=0.80, delta_m21_sq_eV2=7.42e-5, delta_m31_sq_eV2=2.517e-3)
    b = resonance_triplet_from_splittings_v21(mu0_eV2=0.02, R1=0.90, delta_m21_sq_eV2=7.42e-5, delta_m31_sq_eV2=2.517e-3)
    ga = normalized_resonant_hamiltonian_gaps_v21(a)
    gb = normalized_resonant_hamiltonian_gaps_v21(b)
    assert max(abs(ga[i]-gb[i]) for i in range(2)) > 1e-3


def test_invalid_resonance_range_fails_closed():
    with pytest.raises(ResonanceMassSourceNoGoError):
        resonance_triplet_from_splittings_v21(mu0_eV2=0.001, R1=0.2, delta_m21_sq_eV2=7.42e-5, delta_m31_sq_eV2=2.517e-3)


def test_receipt_tamper_fails():
    receipt = build_resonance_mass_source_no_go_v21(**BASE)
    assert validate_resonance_mass_source_no_go_v21(receipt)
    tampered = copy.deepcopy(receipt)
    tampered["source_side_M_I_identified"] = True
    with pytest.raises(ResonanceMassSourceNoGoError):
        validate_resonance_mass_source_no_go_v21(tampered)
