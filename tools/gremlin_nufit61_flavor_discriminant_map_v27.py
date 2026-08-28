from __future__ import annotations

import argparse
import cmath
import json
import lzma
import math
import pathlib
from dataclasses import dataclass

from tools.gremlin_nufit61_correlated_ratio_line_v26 import (
    NUFIT61_SOURCES,
    TIR_DM31_OVER_DM21,
    download_source,
    profile_ratio_line,
    read_dms_dma_grid,
    verify_source,
)


FLAVORS = ("e", "mu", "tau")
OSCILLATION_PHASE_COEFF = 2.0 * 1.267


@dataclass(frozen=True)
class PMNSPoint:
    sin2_theta12: float
    sin2_theta13: float
    sin2_theta23: float
    delta_cp_deg: float


@dataclass(frozen=True)
class SpectrumPoint:
    dm21_eV2: float
    dm31_eV2: float

    @property
    def dm32_eV2(self) -> float:
        return self.dm31_eV2 - self.dm21_eV2

    @property
    def ratio31_21(self) -> float:
        return self.dm31_eV2 / self.dm21_eV2


def _read_projection_rows(path: pathlib.Path, tag: str, columns: int) -> list[tuple[float, ...]]:
    marker = f"# {tag} projection:"
    rows: list[tuple[float, ...]] = []
    active = False
    found = False
    with lzma.open(path, "rt", encoding="utf-8") as handle:
        for raw in handle:
            if raw.startswith("# "):
                if raw.startswith(marker):
                    active = True
                    found = True
                elif active:
                    break
                else:
                    active = False
                continue
            if not active or not raw.strip():
                continue
            fields = raw.split()
            if len(fields) != columns:
                raise ValueError(f"section {tag} expected {columns} columns, got {len(fields)}")
            rows.append(tuple(float(value) for value in fields))
    if not found or not rows:
        raise ValueError(f"projection {tag} not found or empty")
    return rows


def _minimum_row(rows: list[tuple[float, ...]]) -> tuple[float, ...]:
    if not rows:
        raise ValueError("cannot minimize empty rows")
    return min(rows, key=lambda row: row[-1])


def extract_profile_bestfit_coordinates(path: pathlib.Path) -> dict:
    t13_t12 = _minimum_row(_read_projection_rows(path, "T13/T12", 3))
    t23_dma_dcp = _minimum_row(_read_projection_rows(path, "T23/DMA/DCP", 4))
    dms_dma = _minimum_row(_read_projection_rows(path, "DMS/DMA", 3))

    sin2_theta13, sin2_theta12, chi_t13_t12 = t13_t12
    sin2_theta23, dma_1e3, delta_cp_deg, chi_t23_dma_dcp = t23_dma_dcp
    log10_dm21, dma_mass_1e3, chi_dms_dma = dms_dma

    if not (0.0 < sin2_theta12 < 1.0 and 0.0 < sin2_theta13 < 1.0 and 0.0 < sin2_theta23 < 1.0):
        raise ValueError("invalid PMNS profile coordinate")

    return {
        "pmns": PMNSPoint(
            sin2_theta12=sin2_theta12,
            sin2_theta13=sin2_theta13,
            sin2_theta23=sin2_theta23,
            delta_cp_deg=delta_cp_deg,
        ),
        "spectrum": SpectrumPoint(
            dm21_eV2=10.0 ** log10_dm21,
            dm31_eV2=dma_mass_1e3 * 1.0e-3,
        ),
        "profile_minima_delta_chi2": {
            "T13/T12": chi_t13_t12,
            "T23/DMA/DCP": chi_t23_dma_dcp,
            "DMS/DMA": chi_dms_dma,
        },
        "dma_consistency_eV2": {
            "from_T23_DMA_DCP": dma_1e3 * 1.0e-3,
            "from_DMS_DMA": dma_mass_1e3 * 1.0e-3,
            "absolute_difference": abs(dma_1e3 - dma_mass_1e3) * 1.0e-3,
        },
    }


def pmns_matrix(point: PMNSPoint) -> tuple[tuple[complex, ...], ...]:
    s12 = math.sqrt(point.sin2_theta12)
    c12 = math.sqrt(1.0 - point.sin2_theta12)
    s13 = math.sqrt(point.sin2_theta13)
    c13 = math.sqrt(1.0 - point.sin2_theta13)
    s23 = math.sqrt(point.sin2_theta23)
    c23 = math.sqrt(1.0 - point.sin2_theta23)
    delta = math.radians(point.delta_cp_deg)
    eid = cmath.exp(1j * delta)
    emid = eid.conjugate()
    return (
        (c12 * c13, s12 * c13, s13 * emid),
        (
            -s12 * c23 - c12 * s13 * s23 * eid,
            c12 * c23 - s12 * s13 * s23 * eid,
            c13 * s23,
        ),
        (
            s12 * s23 - c12 * s13 * c23 * eid,
            -c12 * s23 - s12 * s13 * c23 * eid,
            c13 * c23,
        ),
    )


def _unitarity_residual(matrix: tuple[tuple[complex, ...], ...]) -> float:
    residual = 0.0
    for i in range(3):
        for j in range(3):
            inner = sum(matrix[k][i].conjugate() * matrix[k][j] for k in range(3))
            target = 1.0 if i == j else 0.0
            residual = max(residual, abs(inner - target))
    return residual


def vacuum_probability_matrix(
    pmns: PMNSPoint,
    spectrum: SpectrumPoint,
    l_over_e_km_per_gev: float,
) -> tuple[tuple[float, ...], ...]:
    if l_over_e_km_per_gev < 0.0:
        raise ValueError("L/E must be non-negative")
    if spectrum.dm21_eV2 <= 0.0 or spectrum.dm31_eV2 <= spectrum.dm21_eV2:
        raise ValueError("normal-ordering positive spectrum required")
    u = pmns_matrix(pmns)
    if _unitarity_residual(u) > 5e-14:
        raise ValueError("PMNS matrix failed unitarity check")
    mass_sq = (0.0, spectrum.dm21_eV2, spectrum.dm31_eV2)
    phases = tuple(
        cmath.exp(-1j * OSCILLATION_PHASE_COEFF * dm2 * l_over_e_km_per_gev)
        for dm2 in mass_sq
    )
    rows: list[tuple[float, ...]] = []
    for alpha in range(3):
        probs: list[float] = []
        for beta in range(3):
            amp = sum(u[beta][i] * phases[i] * u[alpha][i].conjugate() for i in range(3))
            probs.append(abs(amp) ** 2)
        norm = sum(probs)
        if abs(norm - 1.0) > 2e-12:
            raise ValueError("flavor probability conservation failed")
        rows.append(tuple(probs))
    return tuple(rows)


def mutual_information_uniform(channel: tuple[tuple[float, ...], ...]) -> float:
    p_input = 1.0 / 3.0
    p_output = [sum(channel[a][b] for a in range(3)) * p_input for b in range(3)]
    information = 0.0
    for a in range(3):
        for b in range(3):
            joint = p_input * channel[a][b]
            if joint > 0.0 and p_output[b] > 0.0:
                information += joint * math.log2(joint / (p_input * p_output[b]))
    return information


def smeared_probability_matrix(
    pmns: PMNSPoint,
    spectrum: SpectrumPoint,
    center_l_over_e: float,
    fractional_sigma: float,
    nodes: int = 21,
) -> tuple[tuple[float, ...], ...]:
    if fractional_sigma < 0.0:
        raise ValueError("fractional sigma must be non-negative")
    if fractional_sigma == 0.0 or center_l_over_e == 0.0:
        return vacuum_probability_matrix(pmns, spectrum, center_l_over_e)
    if nodes < 5 or nodes % 2 == 0:
        raise ValueError("odd node count >= 5 required")
    half = nodes // 2
    accum = [[0.0] * 3 for _ in range(3)]
    total_weight = 0.0
    for index in range(-half, half + 1):
        z = 3.0 * index / half
        x = center_l_over_e * (1.0 + fractional_sigma * z)
        if x < 0.0:
            continue
        weight = math.exp(-0.5 * z * z)
        matrix = vacuum_probability_matrix(pmns, spectrum, x)
        total_weight += weight
        for a in range(3):
            for b in range(3):
                accum[a][b] += weight * matrix[a][b]
    return tuple(tuple(accum[a][b] / total_weight for b in range(3)) for a in range(3))


def _matrix_delta(a: tuple[tuple[float, ...], ...], b: tuple[tuple[float, ...], ...]) -> dict:
    maximum = -1.0
    channel = None
    signed = 0.0
    for alpha in range(3):
        for beta in range(3):
            delta = a[alpha][beta] - b[alpha][beta]
            if abs(delta) > maximum:
                maximum = abs(delta)
                signed = delta
                channel = f"{FLAVORS[alpha]}->{FLAVORS[beta]}"
    return {"max_abs_delta_probability": maximum, "channel": channel, "signed_delta_probability": signed}


def scan_discriminant(
    pmns: PMNSPoint,
    free_spectrum: SpectrumPoint,
    ratio33_spectrum: SpectrumPoint,
    max_l_over_e: float = 2000.0,
    samples: int = 4001,
    fractional_sigma: float = 0.0,
) -> dict:
    if max_l_over_e <= 0.0 or samples < 101:
        raise ValueError("positive scan range and >=101 samples required")
    best_probability = None
    best_information = None
    for index in range(samples):
        x = max_l_over_e * index / (samples - 1)
        free = smeared_probability_matrix(pmns, free_spectrum, x, fractional_sigma)
        constrained = smeared_probability_matrix(pmns, ratio33_spectrum, x, fractional_sigma)
        delta = _matrix_delta(constrained, free)
        info_free = mutual_information_uniform(free)
        info_constrained = mutual_information_uniform(constrained)
        info_delta = info_constrained - info_free
        if best_probability is None or delta["max_abs_delta_probability"] > best_probability["max_abs_delta_probability"]:
            best_probability = {"l_over_e_km_per_gev": x, **delta}
        if best_information is None or abs(info_delta) > abs(best_information["delta_mutual_information_bits"]):
            best_information = {
                "l_over_e_km_per_gev": x,
                "delta_mutual_information_bits": info_delta,
                "free_mutual_information_bits": info_free,
                "ratio33_mutual_information_bits": info_constrained,
            }
    assert best_probability is not None and best_information is not None
    return {
        "max_l_over_e_km_per_gev": max_l_over_e,
        "samples": samples,
        "fractional_l_over_e_sigma": fractional_sigma,
        "largest_probability_separation": best_probability,
        "largest_mutual_information_separation": best_information,
    }


def evaluate_file(path: pathlib.Path, source_id: str) -> dict:
    source = verify_source(path, source_id)
    profile = extract_profile_bestfit_coordinates(path)
    pmns = profile["pmns"]
    free_spectrum = profile["spectrum"]
    dms_dma_grid = read_dms_dma_grid(path)
    ratio_profile = profile_ratio_line(dms_dma_grid, dm31_over_dm21=TIR_DM31_OVER_DM21, samples=40001)
    ratio33_spectrum = SpectrumPoint(
        dm21_eV2=ratio_profile["delta_m21_sq_eV2"],
        dm31_eV2=ratio_profile["delta_m31_sq_eV2"],
    )

    exact_short = scan_discriminant(pmns, free_spectrum, ratio33_spectrum, 2000.0, 4001, 0.0)
    smeared_short = scan_discriminant(pmns, free_spectrum, ratio33_spectrum, 2000.0, 2001, 0.10)
    exact_extended = scan_discriminant(pmns, free_spectrum, ratio33_spectrum, 10000.0, 5001, 0.0)

    return {
        "schema": "GREMLIN_NUFIT61_FLAVOR_DISCRIMINANT_MAP_V2_7",
        "source": source,
        "pmns_profile_coordinates": {
            "sin2_theta12": pmns.sin2_theta12,
            "sin2_theta13": pmns.sin2_theta13,
            "sin2_theta23": pmns.sin2_theta23,
            "delta_cp_deg": pmns.delta_cp_deg,
            "unitarity_residual": _unitarity_residual(pmns_matrix(pmns)),
        },
        "profile_minima_delta_chi2": profile["profile_minima_delta_chi2"],
        "dma_profile_consistency": profile["dma_consistency_eV2"],
        "free_profile_spectrum": {
            "dm21_eV2": free_spectrum.dm21_eV2,
            "dm31_eV2": free_spectrum.dm31_eV2,
            "ratio31_21": free_spectrum.ratio31_21,
        },
        "tir_ratio33_profiled_spectrum": {
            "dm21_eV2": ratio33_spectrum.dm21_eV2,
            "dm31_eV2": ratio33_spectrum.dm31_eV2,
            "ratio31_21": ratio33_spectrum.ratio31_21,
            "surface_delta_chi2": ratio_profile["delta_chi2"],
        },
        "comparison_policy": "same NuFIT PMNS profile coordinates; isolate mass-splitting-ratio effect",
        "vacuum_phase_policy": "standard three-flavor vacuum PMNS evolution with phase coefficient 2*1.267*Delta_m2*L/E",
        "scans": {
            "ideal_0_2000": exact_short,
            "ten_percent_L_over_E_smearing_0_2000": smeared_short,
            "ideal_0_10000": exact_extended,
        },
        "matter_effects_included": False,
        "detector_response_included": False,
        "claim_promotion": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", choices=tuple(NUFIT61_SOURCES), required=True)
    parser.add_argument("--input", type=pathlib.Path)
    parser.add_argument("--download", type=pathlib.Path)
    parser.add_argument("--allow-insecure-tls", action="store_true")
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    path = args.input
    acquisition = None
    if args.download is not None:
        path = args.download
        acquisition = download_source(args.source_id, path, args.allow_insecure_tls)
    if path is None:
        raise SystemExit("provide --input or --download")
    result = evaluate_file(path, args.source_id)
    if acquisition is not None:
        result["source"]["acquisition_mode"] = acquisition["acquisition_mode"]
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
