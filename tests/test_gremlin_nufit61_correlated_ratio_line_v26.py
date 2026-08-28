import lzma
import math

import pytest

from tools.gremlin_nufit61_correlated_ratio_line_v26 import (
    Grid2D,
    _line_log_dms,
    profile_ratio_line,
    read_dms_dma_grid,
    verify_source,
)


def _synthetic_rows():
    x_axis = (-4.13, -4.12, -4.11)
    y_axis = (2.45, 2.50, 2.55)
    rows = []
    for x in x_axis:
        for y in y_axis:
            z = ((x + 4.1206) / 0.01) ** 2 + ((y - 2.50) / 0.05) ** 2
            rows.append((x, y, z))
    return rows


def test_exact_tir_line_is_dm21_equal_dm31_over_33():
    y = 2.511
    x = _line_log_dms(y, 33.0)
    assert math.isclose(10.0**x, y * 1.0e-3 / 33.0, rel_tol=1e-15)


def test_grid_interpolation_hits_nodes_exactly():
    grid = Grid2D.from_rows(_synthetic_rows())
    for x, y, z in _synthetic_rows():
        assert math.isclose(grid.interpolate(x, y)["delta_chi2"], z, rel_tol=1e-14, abs_tol=1e-14)


def test_profile_finds_low_chi2_region_on_exact_ratio_line():
    grid = Grid2D.from_rows(_synthetic_rows())
    receipt = profile_ratio_line(grid, samples=10001)
    assert receipt["dm31_over_dm21"] == 33.0
    assert 2.45 <= receipt["delta_m31_sq_eV2"] * 1e3 <= 2.55
    assert receipt["delta_chi2"] < 0.2
    assert math.isclose(
        receipt["delta_m31_sq_eV2"],
        33.0 * receipt["delta_m21_sq_eV2"],
        rel_tol=1e-15,
    )


def test_xz_parser_extracts_only_dms_dma_section(tmp_path):
    path = tmp_path / "fixture.txt.xz"
    lines = ["# T13/T12 projection:\n", "0.02 0.30 9.0\n", "# DMS/DMA projection:\n"]
    for x, y, z in _synthetic_rows():
        lines.append(f"{x} {y} {z}\n")
    lines.extend(["# DMS projection:\n", "-4.12 0.0\n"])
    with lzma.open(path, "wt", encoding="utf-8") as handle:
        handle.writelines(lines)
    grid = read_dms_dma_grid(path)
    assert len(grid.values) == 9
    assert grid.x_axis == (-4.13, -4.12, -4.11)
    assert grid.y_axis == (2.45, 2.5, 2.55)


def test_incomplete_grid_fails_closed():
    rows = _synthetic_rows()[:-1]
    with pytest.raises(ValueError, match="complete rectilinear grid"):
        Grid2D.from_rows(rows)


def test_no_extrapolation():
    grid = Grid2D.from_rows(_synthetic_rows())
    with pytest.raises(ValueError, match="extrapolation forbidden"):
        grid.interpolate(-4.2, 2.5)


def test_bad_ratio_and_too_few_samples_fail_closed():
    grid = Grid2D.from_rows(_synthetic_rows())
    with pytest.raises(ValueError):
        _line_log_dms(2.5, 1.0)
    with pytest.raises(ValueError, match="at least 1001"):
        profile_ratio_line(grid, samples=100)


def test_source_hash_mismatch_fails_closed(tmp_path):
    path = tmp_path / "fake.xz"
    path.write_bytes(b"not the official NuFIT table")
    with pytest.raises(ValueError, match="integrity mismatch"):
        verify_source(path, "TByes-NO")
