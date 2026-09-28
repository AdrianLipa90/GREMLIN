from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "GREMLIN_PBH_RELATIONAL_TIDAL_V0_1"


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


def _mv(m: Sequence[Sequence[float]], v: Sequence[float]) -> tuple[float, float, float]:
    return tuple(sum(float(m[i][j]) * float(v[j]) for j in range(3)) for i in range(3))


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(float(x) * float(y) for x, y in zip(a, b))


def _frob(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> float:
    return sum(float(a[i][j]) * float(b[i][j]) for i in range(3) for j in range(3))


def tidal_shape(axis: Sequence[float]) -> tuple[tuple[float, float, float], ...]:
    u = _unit(axis)
    return tuple(
        tuple(3.0 * u[i] * u[j] - (1.0 if i == j else 0.0) for j in range(3))
        for i in range(3)
    )


def source_axis_from_tensor(
    tensor: Sequence[Sequence[float]],
    *,
    iterations: int = 64,
) -> tuple[float, float, float]:
    """Principal positive-eigenvalue axis for a distant-point-mass tidal tensor."""
    t = _mat3(tensor)
    v = _unit((1.0, 1.0, 1.0))
    for _ in range(iterations):
        v = _unit(_mv(t, v))
    # Sign is physically degenerate for a static quadrupolar tidal field.
    for x in v:
        if abs(x) > 1e-15:
            if x < 0.0:
                v = tuple(-y for y in v)
            break
    return v


def tidal_amplitude_from_tensor(
    tensor: Sequence[Sequence[float]],
    axis: Sequence[float],
) -> float:
    """Least-squares mu for T ~= mu*(3uu^T-I).  Q:Q = 6."""
    t = _mat3(tensor)
    q = tidal_shape(axis)
    return _frob(t, q) / 6.0


def tensor_shape_consistency(
    left: Sequence[Sequence[float]],
    right: Sequence[Sequence[float]],
) -> float:
    """Cosine of the Frobenius angle, mapped to [0,1] by absolute value."""
    a = _mat3(left)
    b = _mat3(right)
    na = math.sqrt(_frob(a, a))
    nb = math.sqrt(_frob(b, b))
    if na <= 0.0 or nb <= 0.0:
        raise ValueError("zero tensor")
    return abs(_frob(a, b) / (na * nb))


def build_relational_source_packet(
    fits: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Aggregate independent fitted tidal tensors without inventing a PBH.

    Each fit is expected to contain:
      id, tensor_3x3, provenance, independent_data_layer.
    """
    if len(fits) < 2:
        raise ValueError("at least two independent fitted tensors are required")

    rows = []
    for fit in fits:
        tensor = _mat3(fit["tensor_3x3"])
        axis = source_axis_from_tensor(tensor)
        mu = tidal_amplitude_from_tensor(tensor, axis)
        rows.append(
            {
                "id": str(fit["id"]),
                "independent_data_layer": str(fit["independent_data_layer"]),
                "provenance": fit.get("provenance"),
                "axis_sign_degenerate": list(axis),
                "mu_fit": mu,
                "tensor_3x3": [list(row) for row in tensor],
            }
        )

    pairwise = {}
    axis_overlaps = []
    tensor_overlaps = []
    for i, left in enumerate(rows):
        for right in rows[i + 1 :]:
            key = f'{left["id"]}__{right["id"]}'
            axis_overlap = abs(_dot(left["axis_sign_degenerate"], right["axis_sign_degenerate"]))
            tensor_overlap = tensor_shape_consistency(left["tensor_3x3"], right["tensor_3x3"])
            pairwise[key] = {
                "axis_overlap_abs": axis_overlap,
                "tensor_shape_consistency": tensor_overlap,
            }
            axis_overlaps.append(axis_overlap)
            tensor_overlaps.append(tensor_overlap)

    mus = [row["mu_fit"] for row in rows]
    mu_mean = sum(mus) / len(mus)
    mu_scale = max(abs(mu_mean), 1e-30)
    mu_rel_spread = math.sqrt(sum((x - mu_mean) ** 2 for x in mus) / len(mus)) / mu_scale

    return {
        "schema": SCHEMA,
        "status": "RELATIONAL_SOURCE_CANDIDATE",
        "fits": rows,
        "pairwise": pairwise,
        "aggregate": {
            "mean_axis_overlap_abs": sum(axis_overlaps) / len(axis_overlaps),
            "mean_tensor_shape_consistency": sum(tensor_overlaps) / len(tensor_overlaps),
            "mean_mu": mu_mean,
            "relative_mu_spread": mu_rel_spread,
        },
        "promotion_gate": {
            "requires_independent_layers": True,
            "requires_common_axis": True,
            "requires_compatible_mu": True,
            "mass_distance_degeneracy_unbroken": True,
            "PBH_identity_not_inferred_from_gravity_alone": True,
        },
        "authority": "CANDIDATE_ONLY",
        "canon_allowed": False,
    }
