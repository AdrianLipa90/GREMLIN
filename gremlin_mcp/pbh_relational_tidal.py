from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

SCHEMA = "GREMLIN_PBH_RELATIONAL_TIDAL_V0_2"


def _vec3(v: Sequence[float]) -> tuple[float, float, float]:
    if len(v) != 3:
        raise ValueError("expected 3-vector")
    out = tuple(float(x) for x in v)
    if not all(math.isfinite(x) for x in out):
        raise ValueError("non-finite vector")
    return out


def _mat3(m: Sequence[Sequence[float]]) -> tuple[tuple[float, float, float], ...]:
    if len(m) != 3 or any(len(row) != 3 for row in m):
        raise ValueError("expected 3x3 matrix")
    out = tuple(tuple(float(x) for x in row) for row in m)
    if not all(math.isfinite(x) for row in out for x in row):
        raise ValueError("non-finite matrix")
    return out


def _norm(v: Sequence[float]) -> float:
    return math.sqrt(sum(float(x) ** 2 for x in v))


def _unit(v: Sequence[float]) -> tuple[float, float, float]:
    x = _vec3(v)
    n = _norm(x)
    if n <= 0.0:
        raise ValueError("zero vector")
    return tuple(y / n for y in x)


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(float(x) * float(y) for x, y in zip(a, b))


def _frob(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> float:
    return sum(float(a[i][j]) * float(b[i][j]) for i in range(3) for j in range(3))


def _frob_norm(a: Sequence[Sequence[float]]) -> float:
    return math.sqrt(_frob(a, a))


def _transpose(a: Sequence[Sequence[float]]) -> tuple[tuple[float, float, float], ...]:
    return tuple(tuple(float(a[j][i]) for j in range(3)) for i in range(3))


def _symmetrize(a: Sequence[Sequence[float]]) -> tuple[tuple[float, float, float], ...]:
    at = _transpose(a)
    return tuple(
        tuple(0.5 * (float(a[i][j]) + float(at[i][j])) for j in range(3))
        for i in range(3)
    )


def _sub(
    a: Sequence[Sequence[float]],
    b: Sequence[Sequence[float]],
) -> tuple[tuple[float, float, float], ...]:
    return tuple(
        tuple(float(a[i][j]) - float(b[i][j]) for j in range(3))
        for i in range(3)
    )


def _scale(
    a: Sequence[Sequence[float]],
    s: float,
) -> tuple[tuple[float, float, float], ...]:
    return tuple(tuple(float(s) * float(x) for x in row) for row in a)


def _trace(a: Sequence[Sequence[float]]) -> float:
    return sum(float(a[i][i]) for i in range(3))


def _jacobi_eigh3(
    matrix: Sequence[Sequence[float]],
    *,
    iterations: int = 64,
    tolerance: float = 1e-15,
) -> tuple[
    tuple[float, float, float],
    tuple[tuple[float, float, float], ...],
]:
    """Eigenpairs of a real symmetric 3x3 matrix using Jacobi rotations.

    Returns ascending eigenvalues and matching eigenvectors as columns.
    No optional numerical dependency is required.
    """
    m = _mat3(matrix)
    a = [[float(m[i][j]) for j in range(3)] for i in range(3)]
    v = [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]

    for _ in range(iterations):
        offdiag = [
            (abs(a[0][1]), 0, 1),
            (abs(a[0][2]), 0, 2),
            (abs(a[1][2]), 1, 2),
        ]
        largest, p, q = max(offdiag)
        scale = max(
            1.0,
            max(abs(a[i][j]) for i in range(3) for j in range(3)),
        )
        if largest <= tolerance * scale:
            break

        app = a[p][p]
        aqq = a[q][q]
        apq = a[p][q]
        phi = 0.5 * math.atan2(2.0 * apq, aqq - app)
        c = math.cos(phi)
        s = math.sin(phi)

        for k in range(3):
            if k in (p, q):
                continue
            akp = a[k][p]
            akq = a[k][q]
            a[k][p] = a[p][k] = c * akp - s * akq
            a[k][q] = a[q][k] = s * akp + c * akq

        a[p][p] = c * c * app - 2.0 * s * c * apq + s * s * aqq
        a[q][q] = s * s * app + 2.0 * s * c * apq + c * c * aqq
        a[p][q] = a[q][p] = 0.0

        for k in range(3):
            vkp = v[k][p]
            vkq = v[k][q]
            v[k][p] = c * vkp - s * vkq
            v[k][q] = s * vkp + c * vkq

    eigenvalues = [a[i][i] for i in range(3)]
    eigenvectors = [
        tuple(v[row][col] for row in range(3))
        for col in range(3)
    ]
    order = sorted(range(3), key=lambda i: eigenvalues[i])
    values = tuple(eigenvalues[i] for i in order)
    vectors = tuple(_unit(eigenvectors[i]) for i in order)
    return values, vectors


def tidal_shape(axis: Sequence[float]) -> tuple[tuple[float, float, float], ...]:
    u = _unit(axis)
    return tuple(
        tuple(3.0 * u[i] * u[j] - (1.0 if i == j else 0.0) for j in range(3))
        for i in range(3)
    )


def tensor_diagnostics(
    tensor: Sequence[Sequence[float]],
    *,
    max_symmetry_error: float = 1e-8,
    max_trace_ratio: float = 0.10,
    max_point_shape_residual: float = 0.20,
    max_transverse_split_over_mu: float = 0.40,
) -> dict[str, Any]:
    """Diagnose whether a fitted tensor has distant-point-mass tidal shape.

    The raw tensor is *not* silently made trace-free. Symmetry and trace errors
    remain explicit gate quantities.
    """
    raw = _mat3(tensor)
    sym = _symmetrize(raw)
    norm_raw = max(_frob_norm(raw), 1e-300)
    symmetry_error = _frob_norm(_sub(raw, _transpose(raw))) / norm_raw
    trace_ratio = abs(_trace(sym)) / max(_frob_norm(sym), 1e-300)

    eigvals, eigvecs = _jacobi_eigh3(sym)
    axis = eigvecs[-1]
    for x in axis:
        if abs(x) > 1e-15:
            if x < 0.0:
                axis = tuple(-y for y in axis)
            break

    q = tidal_shape(axis)
    mu = _frob(sym, q) / 6.0
    point = _scale(q, mu)
    shape_residual = _frob_norm(_sub(sym, point)) / max(_frob_norm(sym), 1e-300)
    transverse_split = abs(eigvals[1] - eigvals[0]) / max(abs(mu), 1e-300)

    passes = {
        "finite": True,
        "symmetric": symmetry_error <= max_symmetry_error,
        "trace_free_compatible": trace_ratio <= max_trace_ratio,
        "positive_mu": mu > 0.0,
        "point_mass_shape": shape_residual <= max_point_shape_residual,
        "transverse_degeneracy":
            transverse_split <= max_transverse_split_over_mu,
    }
    passes["all"] = all(passes.values())

    return {
        "eigenvalues_ascending": list(eigvals),
        "axis_sign_degenerate": list(axis),
        "mu_fit": mu,
        "symmetry_error": symmetry_error,
        "trace_ratio": trace_ratio,
        "point_mass_shape_residual": shape_residual,
        "transverse_eigenvalue_split_over_mu": transverse_split,
        "point_mass_tensor_3x3": [list(row) for row in point],
        "thresholds": {
            "max_symmetry_error": max_symmetry_error,
            "max_trace_ratio": max_trace_ratio,
            "max_point_mass_shape_residual": max_point_shape_residual,
            "max_transverse_split_over_mu": max_transverse_split_over_mu,
        },
        "passes": passes,
    }


def source_axis_from_tensor(
    tensor: Sequence[Sequence[float]],
    *,
    iterations: int = 64,
) -> tuple[float, float, float]:
    """Largest-eigenvalue axis; sign remains physically degenerate."""
    del iterations  # retained for backward-compatible signature
    diag = tensor_diagnostics(tensor)
    return tuple(float(x) for x in diag["axis_sign_degenerate"])


def tidal_amplitude_from_tensor(
    tensor: Sequence[Sequence[float]],
    axis: Sequence[float],
) -> float:
    """Least-squares mu for T ~= mu*(3uu^T-I). Q:Q = 6."""
    t = _mat3(tensor)
    q = tidal_shape(axis)
    return _frob(t, q) / 6.0


def tensor_shape_consistency(
    left: Sequence[Sequence[float]],
    right: Sequence[Sequence[float]],
) -> float:
    """Absolute cosine of the Frobenius angle."""
    a = _mat3(left)
    b = _mat3(right)
    na = _frob_norm(a)
    nb = _frob_norm(b)
    if na <= 0.0 or nb <= 0.0:
        raise ValueError("zero tensor")
    return abs(_frob(a, b) / (na * nb))


def build_relational_source_packet(
    fits: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Aggregate independent fitted tidal tensors without inventing a PBH."""
    if len(fits) < 2:
        raise ValueError("at least two independent fitted tensors are required")

    rows = []
    for fit in fits:
        tensor = _mat3(fit["tensor_3x3"])
        diag = tensor_diagnostics(tensor)
        rows.append(
            {
                "id": str(fit["id"]),
                "independent_data_layer": str(fit["independent_data_layer"]),
                "provenance": fit.get("provenance"),
                "axis_sign_degenerate": diag["axis_sign_degenerate"],
                "mu_fit": diag["mu_fit"],
                "tensor_3x3": [list(row) for row in tensor],
                "point_mass_diagnostics": diag,
            }
        )

    pairwise = {}
    axis_overlaps = []
    tensor_overlaps = []
    for i, left in enumerate(rows):
        for right in rows[i + 1 :]:
            key = f'{left["id"]}__{right["id"]}'
            axis_overlap = abs(
                _dot(left["axis_sign_degenerate"], right["axis_sign_degenerate"])
            )
            tensor_overlap = tensor_shape_consistency(
                left["tensor_3x3"], right["tensor_3x3"]
            )
            pairwise[key] = {
                "axis_overlap_abs": axis_overlap,
                "tensor_shape_consistency": tensor_overlap,
            }
            axis_overlaps.append(axis_overlap)
            tensor_overlaps.append(tensor_overlap)

    mus = [row["mu_fit"] for row in rows]
    mu_mean = sum(mus) / len(mus)
    mu_scale = max(abs(mu_mean), 1e-30)
    mu_rel_spread = (
        math.sqrt(sum((x - mu_mean) ** 2 for x in mus) / len(mus)) / mu_scale
    )
    all_point_mass_shape_pass = all(
        row["point_mass_diagnostics"]["passes"]["all"]
        for row in rows
    )

    return {
        "schema": SCHEMA,
        "status": (
            "RELATIONAL_POINT_MASS_CANDIDATE"
            if all_point_mass_shape_pass
            else "RELATIONAL_TENSOR_ONLY"
        ),
        "fits": rows,
        "pairwise": pairwise,
        "aggregate": {
            "mean_axis_overlap_abs": sum(axis_overlaps) / len(axis_overlaps),
            "mean_tensor_shape_consistency": sum(tensor_overlaps) / len(tensor_overlaps),
            "mean_mu": mu_mean,
            "relative_mu_spread": mu_rel_spread,
            "all_point_mass_shape_pass": all_point_mass_shape_pass,
        },
        "promotion_gate": {
            "requires_independent_layers": True,
            "requires_each_tensor_point_mass_eigenshape": True,
            "requires_common_axis": True,
            "requires_compatible_mu": True,
            "mass_distance_degeneracy_unbroken": True,
            "PBH_identity_not_inferred_from_gravity_alone": True,
        },
        "authority": "CANDIDATE_ONLY",
        "canon_allowed": False,
    }
