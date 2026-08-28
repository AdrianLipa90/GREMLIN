from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import lzma
import math
import pathlib
import ssl
import urllib.request
from dataclasses import dataclass


NUFIT61_SOURCES = {
    "TBoff-NO": {
        "url": "https://www.nu-fit.org/sites/default/files/v61.release-TBoff-NO.txt.xz",
        "sha256": "58b113927c13f55925558e1ef0a598b357a237cde5c466b9f660cc08569970f6",
        "bytes": 3996028,
        "atmospheric_treatment": "IC23 without the tabulated Super-Kamiokande atmospheric likelihood",
    },
    "TByes-NO": {
        "url": "https://www.nu-fit.org/sites/default/files/v61.release-TByes-NO.txt.xz",
        "sha256": "c74bd6df84297a8429cd3b9e1239751cd0762756f1ec0c2a31248d78570b26e4",
        "bytes": 3996408,
        "atmospheric_treatment": "IC24 with the tabulated Super-Kamiokande atmospheric likelihood",
    },
}

TIR_DM31_OVER_DM21 = 33.0
SECTION_HEADER = "# DMS/DMA projection:"


@dataclass(frozen=True)
class Grid2D:
    x_axis: tuple[float, ...]
    y_axis: tuple[float, ...]
    values: dict[tuple[float, float], float]

    @classmethod
    def from_rows(cls, rows: list[tuple[float, float, float]]) -> "Grid2D":
        if not rows:
            raise ValueError("DMS/DMA section is empty")
        x_axis = tuple(sorted({x for x, _, _ in rows}))
        y_axis = tuple(sorted({y for _, y, _ in rows}))
        values: dict[tuple[float, float], float] = {}
        for x, y, z in rows:
            key = (x, y)
            if key in values and values[key] != z:
                raise ValueError(f"conflicting duplicate DMS/DMA point {key}")
            values[key] = z
        if len(values) != len(x_axis) * len(y_axis):
            raise ValueError("DMS/DMA section is not a complete rectilinear grid")
        return cls(x_axis, y_axis, values)

    @staticmethod
    def _bracket(axis: tuple[float, ...], value: float) -> tuple[float, float, float]:
        if value < axis[0] or value > axis[-1]:
            raise ValueError("interpolation point outside grid; extrapolation forbidden")
        upper = bisect.bisect_right(axis, value)
        if upper == 0:
            i0, i1 = 0, 1
        elif upper == len(axis):
            i0, i1 = len(axis) - 2, len(axis) - 1
        else:
            i0, i1 = upper - 1, upper
        a0, a1 = axis[i0], axis[i1]
        return a0, a1, (value - a0) / (a1 - a0)

    def interpolate(self, x: float, y: float) -> dict:
        x0, x1, tx = self._bracket(self.x_axis, x)
        y0, y1, ty = self._bracket(self.y_axis, y)
        z00 = self.values[(x0, y0)]
        z10 = self.values[(x1, y0)]
        z01 = self.values[(x0, y1)]
        z11 = self.values[(x1, y1)]
        z = (
            (1.0 - tx) * (1.0 - ty) * z00
            + tx * (1.0 - ty) * z10
            + (1.0 - tx) * ty * z01
            + tx * ty * z11
        )
        return {
            "delta_chi2": float(z),
            "point": [float(x), float(y)],
            "cell": {
                "x": [x0, x1],
                "y": [y0, y1],
                "corner_delta_chi2": [z00, z10, z01, z11],
            },
            "interpolation": "bilinear_no_extrapolation",
        }


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_source(path: pathlib.Path, source_id: str) -> dict:
    source = NUFIT61_SOURCES[source_id]
    actual_hash = sha256(path)
    actual_bytes = path.stat().st_size
    if actual_hash != source["sha256"] or actual_bytes != source["bytes"]:
        raise ValueError(
            f"NuFIT source integrity mismatch: sha256={actual_hash}, bytes={actual_bytes}"
        )
    return {
        "source_id": source_id,
        "url": source["url"],
        "sha256": actual_hash,
        "bytes": actual_bytes,
        "atmospheric_treatment": source["atmospheric_treatment"],
    }


def download_source(source_id: str, destination: pathlib.Path, allow_insecure_tls: bool = False) -> dict:
    source = NUFIT61_SOURCES[source_id]
    mode = "strict_tls"
    try:
        with urllib.request.urlopen(source["url"], timeout=60) as response:
            payload = response.read()
    except Exception as strict_error:
        if not allow_insecure_tls:
            raise RuntimeError(f"strict TLS download failed: {strict_error}") from strict_error
        mode = "explicit_insecure_tls_fallback_with_sha256_pin"
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(source["url"], timeout=60, context=context) as response:
            payload = response.read()
    destination.write_bytes(payload)
    verified = verify_source(destination, source_id)
    verified["acquisition_mode"] = mode
    return verified


def read_dms_dma_grid(path: pathlib.Path) -> Grid2D:
    rows: list[tuple[float, float, float]] = []
    active = False
    found = False
    with lzma.open(path, "rt", encoding="utf-8") as handle:
        for raw in handle:
            if raw.startswith("# "):
                if raw.startswith(SECTION_HEADER):
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
            if len(fields) != 3:
                raise ValueError(f"DMS/DMA row expected 3 columns, got {len(fields)}")
            rows.append(tuple(float(v) for v in fields))
    if not found:
        raise ValueError("DMS/DMA projection section not found")
    return Grid2D.from_rows(rows)


def _line_log_dms(dma_1e3: float, dm31_over_dm21: float) -> float:
    if dma_1e3 <= 0.0 or dm31_over_dm21 <= 1.0:
        raise ValueError("positive DMA and ratio > 1 required")
    dm21_eV2 = dma_1e3 * 1.0e-3 / dm31_over_dm21
    return math.log10(dm21_eV2)


def profile_ratio_line(
    grid: Grid2D,
    dm31_over_dm21: float = TIR_DM31_OVER_DM21,
    samples: int = 40001,
) -> dict:
    if samples < 1001:
        raise ValueError("at least 1001 profile samples required")

    valid_y: list[float] = []
    for y in grid.y_axis:
        x = _line_log_dms(y, dm31_over_dm21)
        if grid.x_axis[0] <= x <= grid.x_axis[-1]:
            valid_y.append(y)
    if len(valid_y) < 2:
        raise ValueError("ratio line does not cross enough of the DMS/DMA grid")

    y_min, y_max = min(valid_y), max(valid_y)
    best: dict | None = None
    for index in range(samples):
        y = y_min + (y_max - y_min) * index / (samples - 1)
        x = _line_log_dms(y, dm31_over_dm21)
        if x < grid.x_axis[0] or x > grid.x_axis[-1]:
            continue
        point = grid.interpolate(x, y)
        if best is None or point["delta_chi2"] < best["delta_chi2"]:
            dm31_eV2 = y * 1.0e-3
            dm21_eV2 = dm31_eV2 / dm31_over_dm21
            best = {
                **point,
                "delta_m21_sq_eV2": dm21_eV2,
                "delta_m31_sq_eV2": dm31_eV2,
                "delta_m32_sq_eV2": dm31_eV2 - dm21_eV2,
            }
    if best is None:
        raise ValueError("no valid points sampled on ratio line")
    best["dm31_over_dm21"] = dm31_over_dm21
    best["samples"] = samples
    best["curve"] = "Delta_m31^2 = ratio * Delta_m21^2"
    return best


def evaluate_file(path: pathlib.Path, source_id: str, samples: int = 40001) -> dict:
    source = verify_source(path, source_id)
    grid = read_dms_dma_grid(path)
    fine = profile_ratio_line(grid, samples=samples)
    coarse_samples = max(1001, (samples + 1) // 2)
    coarse = profile_ratio_line(grid, samples=coarse_samples)
    fine["half_resolution_samples"] = coarse_samples
    fine["half_resolution_delta_chi2_difference"] = abs(fine["delta_chi2"] - coarse["delta_chi2"])
    return {
        "schema": "GREMLIN_NUFIT61_CORRELATED_RATIO_LINE_V2_6",
        "source": source,
        "tir_exact_relation": "Delta_m31^2 = 33 Delta_m21^2",
        "profile": fine,
        "published_surface": "NuFIT 6.1 DMS/DMA two-dimensional marginalized Delta-chi-square projection",
        "profiles_summed": False,
        "claim_promotion": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", choices=tuple(NUFIT61_SOURCES), required=True)
    parser.add_argument("--input", type=pathlib.Path)
    parser.add_argument("--download", type=pathlib.Path)
    parser.add_argument("--allow-insecure-tls", action="store_true")
    parser.add_argument("--samples", type=int, default=40001)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    path = args.input
    acquisition = None
    if args.download is not None:
        path = args.download
        acquisition = download_source(args.source_id, path, args.allow_insecure_tls)
    if path is None:
        raise SystemExit("provide --input or --download")

    receipt = evaluate_file(path, args.source_id, args.samples)
    if acquisition is not None:
        receipt["source"].update({"acquisition_mode": acquisition["acquisition_mode"]})
    text = json.dumps(receipt, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
