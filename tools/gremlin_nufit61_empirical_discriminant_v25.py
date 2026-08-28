from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class OscillationSnapshot:
    name: str
    dm21_eV2: float
    dm21_plus_eV2: float
    dm21_minus_eV2: float
    dm21_3sigma_low_eV2: float
    dm21_3sigma_high_eV2: float
    dm31_eV2: float
    dm31_plus_eV2: float
    dm31_minus_eV2: float
    dm31_3sigma_low_eV2: float
    dm31_3sigma_high_eV2: float
    source_url: str


NUFIT61_IC24_WITH_SK_NO = OscillationSnapshot(
    name="NuFIT 6.1 (2025) / IC24 with SK-atm / Normal Ordering",
    dm21_eV2=7.537e-5,
    dm21_plus_eV2=0.094e-5,
    dm21_minus_eV2=0.100e-5,
    dm21_3sigma_low_eV2=7.236e-5,
    dm21_3sigma_high_eV2=7.823e-5,
    dm31_eV2=2.511e-3,
    dm31_plus_eV2=0.021e-3,
    dm31_minus_eV2=0.020e-3,
    dm31_3sigma_low_eV2=2.450e-3,
    dm31_3sigma_high_eV2=2.576e-3,
    source_url="https://www.nu-fit.org/sites/default/files/v61.tbl-parameters.pdf",
)

TIR_TETRAHEDRON_MASS_RATIOS = (1.0, 2.0, 10.0)
TIR_TETRAHEDRON_SPLITTING_RATIO = 33.0
GRADED_PROJECTION_M2_M1 = math.sqrt(7.0 / 6.0)

CROSS_REPO_PINS = {
    "TIR_phase_clock_area_scale": "b69ba6055c0535c666e12dbba069ffb87238eee6",
    "IDT_relational_lapse_rate": "11fcd5b798445265fa5f8cd4dc3386f3b0a463c4",
    "RFC_relational_lapse_normal_phase_rate": "8611783d2471a3f6700d2c409b222f40b9752ec5",
    "SOH_half_interface": "206e49e306b246c4b0f4d182b0d32d5511739408",
    "GREMLIN_framework_holonomy_firewall_v24": "76a2d6b46e485723eeaa0a97badd2dae6b9b3b14",
}


def _sym_sigma(plus: float, minus: float) -> float:
    if plus <= 0.0 or minus <= 0.0:
        raise ValueError("positive asymmetric uncertainties required")
    return 0.5 * (plus + minus)


def tetrahedron_ratio_prediction() -> float:
    r1, _, r3 = TIR_TETRAHEDRON_MASS_RATIOS
    return (r3 * r3 - r1 * r1) / (2.0 * 2.0 - r1 * r1)


def tetrahedron_spectrum_from_dm21(dm21_eV2: float) -> tuple[float, float, float]:
    if dm21_eV2 <= 0.0:
        raise ValueError("dm21_eV2 must be positive")
    m1 = math.sqrt(dm21_eV2 / 3.0)
    return m1, 2.0 * m1, 10.0 * m1


def graded_projection_spectrum(dm21_eV2: float, dm31_eV2: float) -> tuple[float, float, float]:
    if dm21_eV2 <= 0.0 or dm31_eV2 <= 0.0:
        raise ValueError("positive mass-squared splittings required")
    m1_sq = 6.0 * dm21_eV2
    m2_sq = 7.0 * dm21_eV2
    m3_sq = m1_sq + dm31_eV2
    return math.sqrt(m1_sq), math.sqrt(m2_sq), math.sqrt(m3_sq)


def evaluate_tetrahedron_discriminant(snapshot: OscillationSnapshot = NUFIT61_IC24_WITH_SK_NO) -> dict:
    if snapshot.dm21_eV2 <= 0.0 or snapshot.dm31_eV2 <= 0.0:
        raise ValueError("positive best-fit splittings required")

    observed_ratio = snapshot.dm31_eV2 / snapshot.dm21_eV2
    sigma21 = _sym_sigma(snapshot.dm21_plus_eV2, snapshot.dm21_minus_eV2)
    sigma31 = _sym_sigma(snapshot.dm31_plus_eV2, snapshot.dm31_minus_eV2)
    ratio_sigma_diagonal = observed_ratio * math.sqrt(
        (sigma31 / snapshot.dm31_eV2) ** 2 + (sigma21 / snapshot.dm21_eV2) ** 2
    )
    ratio_pull_diagonal = (observed_ratio - TIR_TETRAHEDRON_SPLITTING_RATIO) / ratio_sigma_diagonal

    predicted_dm31 = TIR_TETRAHEDRON_SPLITTING_RATIO * snapshot.dm21_eV2
    predicted_dm31_sigma = TIR_TETRAHEDRON_SPLITTING_RATIO * sigma21
    combined_sigma_diagonal = math.hypot(sigma31, predicted_dm31_sigma)
    dm31_pull_diagonal = (snapshot.dm31_eV2 - predicted_dm31) / combined_sigma_diagonal

    predicted_3sigma_dm31_low = TIR_TETRAHEDRON_SPLITTING_RATIO * snapshot.dm21_3sigma_low_eV2
    predicted_3sigma_dm31_high = TIR_TETRAHEDRON_SPLITTING_RATIO * snapshot.dm21_3sigma_high_eV2
    overlap_3sigma_low = max(predicted_3sigma_dm31_low, snapshot.dm31_3sigma_low_eV2)
    overlap_3sigma_high = min(predicted_3sigma_dm31_high, snapshot.dm31_3sigma_high_eV2)
    has_3sigma_rectangular_overlap = overlap_3sigma_low <= overlap_3sigma_high

    tetra = tetrahedron_spectrum_from_dm21(snapshot.dm21_eV2)
    graded = graded_projection_spectrum(snapshot.dm21_eV2, snapshot.dm31_eV2)

    if has_3sigma_rectangular_overlap and abs(dm31_pull_diagonal) < 3.0:
        verdict = "COMPATIBLE_NOT_DISCRIMINATING"
    else:
        verdict = "TENSION_REQUIRES_FULL_CORRELATED_LIKELIHOOD"

    return {
        "schema": "GREMLIN_NUFIT61_EMPIRICAL_DISCRIMINANT_V2_5",
        "snapshot": snapshot.name,
        "source_url": snapshot.source_url,
        "tetrahedron_exact_splitting_ratio": TIR_TETRAHEDRON_SPLITTING_RATIO,
        "tetrahedron_ratio_rederived": tetrahedron_ratio_prediction(),
        "observed_best_fit_splitting_ratio": observed_ratio,
        "ratio_sigma_diagonal": ratio_sigma_diagonal,
        "ratio_pull_diagonal": ratio_pull_diagonal,
        "predicted_dm31_eV2_from_tetrahedron": predicted_dm31,
        "dm31_pull_diagonal": dm31_pull_diagonal,
        "predicted_3sigma_dm31_interval_eV2": [predicted_3sigma_dm31_low, predicted_3sigma_dm31_high],
        "nufit_3sigma_dm31_interval_eV2": [snapshot.dm31_3sigma_low_eV2, snapshot.dm31_3sigma_high_eV2],
        "has_3sigma_rectangular_overlap": has_3sigma_rectangular_overlap,
        "tetrahedron_spectrum_eV": tetra,
        "tetrahedron_sum_eV": sum(tetra),
        "graded_projection_spectrum_eV": graded,
        "graded_projection_sum_eV": sum(graded),
        "graded_projection_m2_m1": graded[1] / graded[0],
        "verdict": verdict,
        "covariance_used": False,
        "diagonal_pull_is_approximation": True,
        "global_fit_data_are_external_input": True,
        "cross_repo_pins": dict(CROSS_REPO_PINS),
        "claim_promotion": False,
        "next_required_test": "Evaluate the exact TIR ratio line against the NuFIT 6.1 DMS/DMA correlated chi-square surface.",
    }
