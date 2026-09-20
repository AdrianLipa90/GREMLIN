"""GREMLIN source-family signature identifiability v0.1.

Weighted signature geometry, exact/nullspace degeneracy, conditioning,
candidate amplitude recovery and independent held-out validation.

This module never selects a physical source.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

import numpy as np

from tools.gremlin_cross_modal_relational_evidence_v01 import (
    CrossModalEvidenceError,
    EvidenceProvenance,
)


SCHEMA = "GREMLIN_SOURCE_FAMILY_SIGNATURE_IDENTIFIABILITY_V0_1"


class SourceFamilyIdentifiabilityError(ValueError):
    pass


def _finite(name: str, value: float) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise SourceFamilyIdentifiabilityError(f"{name} must be finite") from exc
    if not math.isfinite(value):
        raise SourceFamilyIdentifiabilityError(f"{name} must be finite")
    return value


def _positive(name: str, value: float) -> float:
    value = _finite(name, value)
    if value <= 0.0:
        raise SourceFamilyIdentifiabilityError(f"{name} must be > 0")
    return value


def _nonempty(name: str, value: str) -> str:
    value = str(value).strip()
    if not value:
        raise SourceFamilyIdentifiabilityError(f"{name} must be non-empty")
    return value


def _canonical_json(value) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _validate_covariance(covariance, size: int, *, name: str) -> np.ndarray:
    sigma = np.asarray(covariance, dtype=float)
    if sigma.shape != (size, size):
        raise SourceFamilyIdentifiabilityError(
            f"{name} must have shape ({size}, {size})"
        )
    if not np.all(np.isfinite(sigma)):
        raise SourceFamilyIdentifiabilityError(f"{name} must be finite")
    if not np.allclose(sigma, sigma.T, rtol=0.0, atol=1e-12):
        raise SourceFamilyIdentifiabilityError(f"{name} must be symmetric")
    try:
        np.linalg.cholesky(sigma)
    except np.linalg.LinAlgError as exc:
        raise SourceFamilyIdentifiabilityError(
            f"{name} must be positive definite"
        ) from exc
    return sigma


def _validate_vector(values, *, name: str) -> np.ndarray:
    vector = np.asarray(values, dtype=float)
    if vector.ndim != 1 or vector.size == 0:
        raise SourceFamilyIdentifiabilityError(
            f"{name} must be a non-empty one-dimensional vector"
        )
    if not np.all(np.isfinite(vector)):
        raise SourceFamilyIdentifiabilityError(f"{name} must be finite")
    return vector


@dataclass(frozen=True)
class SourceFamilySignature:
    name: str
    values: Sequence[float]
    provenance: EvidenceProvenance
    normalization: str

    def validate(self) -> np.ndarray:
        _nonempty("signature.name", self.name)
        _nonempty("signature.normalization", self.normalization)
        try:
            self.provenance.validate()
        except CrossModalEvidenceError as exc:
            raise SourceFamilyIdentifiabilityError(
                f"signature[{self.name}] provenance invalid: {exc}"
            ) from exc
        return _validate_vector(self.values, name=f"signature[{self.name}].values")


@dataclass(frozen=True)
class SignatureGeometryReport:
    state: str
    channel_count: int
    source_count: int
    rank: int
    nullity: int
    singular_values: tuple[float, ...]
    rank_threshold: float
    condition_number: float
    max_condition_number: float
    zero_signature_names: tuple[str, ...]
    pairwise_degeneracy_classes: tuple[tuple[str, ...], ...]
    nullspace_basis: tuple[tuple[float, ...], ...]


@dataclass(frozen=True)
class SourceFamilyFitReport:
    geometry: SignatureGeometryReport
    route: str
    amplitudes: tuple[float, ...] | None
    amplitude_std: tuple[float, ...] | None
    fit_chi_square: float | None
    fit_null_chi_square: float | None
    fit_delta_chi_square: float | None
    heldout_chi_square: float | None
    heldout_null_chi_square: float | None
    heldout_delta_chi_square: float | None
    heldout_independent: bool
    cross_modal_source_routing_admissible: bool
    physical_source_selected: bool = False


def _signature_matrix(
    signatures: Iterable[SourceFamilySignature],
) -> tuple[tuple[SourceFamilySignature, ...], np.ndarray]:
    rows = tuple(signatures)
    if not rows:
        raise SourceFamilyIdentifiabilityError(
            "at least one source-family signature is required"
        )

    names = [row.name for row in rows]
    if len(set(names)) != len(names):
        raise SourceFamilyIdentifiabilityError("signature names must be unique")

    columns = [row.validate() for row in rows]
    channel_count = int(columns[0].size)
    if any(int(column.size) != channel_count for column in columns):
        raise SourceFamilyIdentifiabilityError(
            "all source-family signatures must have the same channel count"
        )

    matrix = np.column_stack(columns)
    return rows, matrix


def _canonicalize_null_vector(vector: np.ndarray) -> tuple[float, ...]:
    vector = np.asarray(vector, dtype=float).copy()
    if vector.ndim != 1:
        raise SourceFamilyIdentifiabilityError("nullspace vector must be 1D")
    if vector.size:
        index = int(np.argmax(np.abs(vector)))
        if vector[index] < 0.0:
            vector *= -1.0
    return tuple(float(x) for x in vector)


def _pairwise_degeneracy_classes(
    whitened_matrix: np.ndarray,
    names: Sequence[str],
    *,
    zero_tol: float,
    collinear_tol: float,
) -> tuple[tuple[str, ...], ...]:
    norms = np.linalg.norm(whitened_matrix, axis=0)
    n = len(names)
    adjacency = [set() for _ in range(n)]

    for i in range(n):
        if norms[i] <= zero_tol:
            continue
        for j in range(i + 1, n):
            if norms[j] <= zero_tol:
                continue
            cosine = float(
                whitened_matrix[:, i] @ whitened_matrix[:, j]
                / (norms[i] * norms[j])
            )
            if abs(cosine) >= 1.0 - collinear_tol:
                adjacency[i].add(j)
                adjacency[j].add(i)

    seen: set[int] = set()
    classes: list[tuple[str, ...]] = []
    for start in range(n):
        if start in seen or not adjacency[start]:
            continue
        stack = [start]
        component: list[int] = []
        seen.add(start)
        while stack:
            current = stack.pop()
            component.append(current)
            for nxt in adjacency[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        classes.append(tuple(sorted(names[index] for index in component)))

    return tuple(sorted(classes))


def signature_geometry(
    signatures: Iterable[SourceFamilySignature],
    covariance,
    *,
    rank_rtol: float = 1e-10,
    max_condition_number: float = 1e8,
    collinear_tol: float = 1e-8,
) -> tuple[SignatureGeometryReport, np.ndarray, np.ndarray, tuple[SourceFamilySignature, ...]]:
    rows, matrix = _signature_matrix(signatures)
    channel_count, source_count = matrix.shape

    rank_rtol = _positive("rank_rtol", rank_rtol)
    max_condition_number = _positive(
        "max_condition_number", max_condition_number
    )
    collinear_tol = _positive("collinear_tol", collinear_tol)
    if collinear_tol >= 1.0:
        raise SourceFamilyIdentifiabilityError("collinear_tol must be < 1")

    sigma = _validate_covariance(
        covariance,
        channel_count,
        name="covariance",
    )
    chol = np.linalg.cholesky(sigma)
    whitened = np.linalg.solve(chol, matrix)

    _, singular_values, vh = np.linalg.svd(whitened, full_matrices=True)
    if singular_values.size:
        rank_threshold = (
            rank_rtol * max(whitened.shape) * float(singular_values[0])
        )
        rank = int(np.count_nonzero(singular_values > rank_threshold))
    else:
        rank_threshold = 0.0
        rank = 0

    nullity = source_count - rank
    if rank < source_count:
        condition_number = math.inf
        state = "UNDERDETERMINED"
    else:
        smallest = float(singular_values[source_count - 1])
        largest = float(singular_values[0])
        condition_number = largest / smallest
        state = (
            "IDENTIFIABLE"
            if condition_number <= max_condition_number
            else "ILL_CONDITIONED"
        )

    norms = np.linalg.norm(whitened, axis=0)
    zero_signature_names = tuple(
        sorted(
            rows[index].name
            for index, norm in enumerate(norms)
            if norm <= rank_threshold
        )
    )

    pairwise_classes = _pairwise_degeneracy_classes(
        whitened,
        [row.name for row in rows],
        zero_tol=rank_threshold,
        collinear_tol=collinear_tol,
    )

    nullspace = tuple(
        _canonicalize_null_vector(vector)
        for vector in vh[rank:, :]
    )

    report = SignatureGeometryReport(
        state=state,
        channel_count=channel_count,
        source_count=source_count,
        rank=rank,
        nullity=nullity,
        singular_values=tuple(float(x) for x in singular_values),
        rank_threshold=float(rank_threshold),
        condition_number=float(condition_number),
        max_condition_number=float(max_condition_number),
        zero_signature_names=zero_signature_names,
        pairwise_degeneracy_classes=pairwise_classes,
        nullspace_basis=nullspace,
    )
    return report, matrix, sigma, rows


def weighted_gram_matrix(
    signatures: Iterable[SourceFamilySignature],
    covariance,
) -> np.ndarray:
    rows, matrix = _signature_matrix(signatures)
    sigma = _validate_covariance(
        covariance,
        matrix.shape[0],
        name="covariance",
    )
    solved = np.linalg.solve(sigma, matrix)
    gram = matrix.T @ solved
    if gram.shape != (len(rows), len(rows)):
        raise SourceFamilyIdentifiabilityError("internal Gram shape mismatch")
    return gram


def analyze_source_family_signatures(
    signatures: Iterable[SourceFamilySignature],
    residual,
    covariance,
    *,
    heldout_signatures: Iterable[SourceFamilySignature] | None = None,
    heldout_residual=None,
    heldout_covariance=None,
    heldout_independent: bool = False,
    cross_modal_source_routing_admissible: bool = False,
    rank_rtol: float = 1e-10,
    max_condition_number: float = 1e8,
    collinear_tol: float = 1e-8,
) -> SourceFamilyFitReport:
    geometry, matrix, sigma, rows = signature_geometry(
        signatures,
        covariance,
        rank_rtol=rank_rtol,
        max_condition_number=max_condition_number,
        collinear_tol=collinear_tol,
    )

    residual_vector = _validate_vector(residual, name="residual")
    if residual_vector.size != geometry.channel_count:
        raise SourceFamilyIdentifiabilityError(
            "residual length must match signature channel count"
        )

    if not isinstance(heldout_independent, bool):
        raise SourceFamilyIdentifiabilityError(
            "heldout_independent must be boolean"
        )
    if not isinstance(cross_modal_source_routing_admissible, bool):
        raise SourceFamilyIdentifiabilityError(
            "cross_modal_source_routing_admissible must be boolean"
        )

    if geometry.state == "UNDERDETERMINED":
        return SourceFamilyFitReport(
            geometry=geometry,
            route="REQUEST_MORE_INDEPENDENT_CHANNELS",
            amplitudes=None,
            amplitude_std=None,
            fit_chi_square=None,
            fit_null_chi_square=None,
            fit_delta_chi_square=None,
            heldout_chi_square=None,
            heldout_null_chi_square=None,
            heldout_delta_chi_square=None,
            heldout_independent=heldout_independent,
            cross_modal_source_routing_admissible=
                cross_modal_source_routing_admissible,
        )

    if geometry.state == "ILL_CONDITIONED":
        return SourceFamilyFitReport(
            geometry=geometry,
            route="REQUEST_BETTER_CONDITIONING",
            amplitudes=None,
            amplitude_std=None,
            fit_chi_square=None,
            fit_null_chi_square=None,
            fit_delta_chi_square=None,
            heldout_chi_square=None,
            heldout_null_chi_square=None,
            heldout_delta_chi_square=None,
            heldout_independent=heldout_independent,
            cross_modal_source_routing_admissible=
                cross_modal_source_routing_admissible,
        )

    chol = np.linalg.cholesky(sigma)
    whitened_matrix = np.linalg.solve(chol, matrix)
    whitened_residual = np.linalg.solve(chol, residual_vector)

    gram = whitened_matrix.T @ whitened_matrix
    rhs = whitened_matrix.T @ whitened_residual
    amplitudes_array = np.linalg.solve(gram, rhs)
    amplitude_covariance = np.linalg.inv(gram)
    amplitude_std_array = np.sqrt(np.diag(amplitude_covariance))

    fit_error = whitened_residual - whitened_matrix @ amplitudes_array
    fit_chi_square = float(fit_error @ fit_error)
    fit_null_chi_square = float(whitened_residual @ whitened_residual)
    fit_delta = fit_null_chi_square - fit_chi_square

    holdout_supplied = any(
        value is not None
        for value in (
            heldout_signatures,
            heldout_residual,
            heldout_covariance,
        )
    )
    if not holdout_supplied:
        route = (
            "NO_SOURCE_ROUTE"
            if not cross_modal_source_routing_admissible
            else "REQUEST_HELD_OUT_VALIDATION"
        )
        return SourceFamilyFitReport(
            geometry=geometry,
            route=route,
            amplitudes=tuple(float(x) for x in amplitudes_array),
            amplitude_std=tuple(float(x) for x in amplitude_std_array),
            fit_chi_square=fit_chi_square,
            fit_null_chi_square=fit_null_chi_square,
            fit_delta_chi_square=float(fit_delta),
            heldout_chi_square=None,
            heldout_null_chi_square=None,
            heldout_delta_chi_square=None,
            heldout_independent=False,
            cross_modal_source_routing_admissible=
                cross_modal_source_routing_admissible,
        )

    if (
        heldout_signatures is None
        or heldout_residual is None
        or heldout_covariance is None
    ):
        raise SourceFamilyIdentifiabilityError(
            "heldout_signatures, heldout_residual and heldout_covariance "
            "must be supplied together"
        )

    heldout_rows, heldout_matrix = _signature_matrix(heldout_signatures)
    fit_names = tuple(row.name for row in rows)
    heldout_names = tuple(row.name for row in heldout_rows)
    if heldout_names != fit_names:
        raise SourceFamilyIdentifiabilityError(
            "held-out signature family order/names must match fit signatures"
        )

    heldout_vector = _validate_vector(
        heldout_residual,
        name="heldout_residual",
    )
    if heldout_vector.size != heldout_matrix.shape[0]:
        raise SourceFamilyIdentifiabilityError(
            "heldout_residual length must match held-out channel count"
        )

    heldout_sigma = _validate_covariance(
        heldout_covariance,
        heldout_matrix.shape[0],
        name="heldout_covariance",
    )
    heldout_chol = np.linalg.cholesky(heldout_sigma)
    heldout_error = np.linalg.solve(
        heldout_chol,
        heldout_vector - heldout_matrix @ amplitudes_array,
    )
    heldout_null = np.linalg.solve(heldout_chol, heldout_vector)

    heldout_chi_square = float(heldout_error @ heldout_error)
    heldout_null_chi_square = float(heldout_null @ heldout_null)
    heldout_delta = heldout_null_chi_square - heldout_chi_square

    if not heldout_independent:
        route = "REQUEST_HELD_OUT_VALIDATION"
    elif not cross_modal_source_routing_admissible:
        route = "NO_SOURCE_ROUTE"
    elif heldout_delta <= 0.0:
        route = "STOP_DECLARED_SOURCE_FAMILY_MODEL"
    else:
        route = "ALLOW_CANDIDATE_SOURCE_FAMILY_TESTS"

    return SourceFamilyFitReport(
        geometry=geometry,
        route=route,
        amplitudes=tuple(float(x) for x in amplitudes_array),
        amplitude_std=tuple(float(x) for x in amplitude_std_array),
        fit_chi_square=fit_chi_square,
        fit_null_chi_square=fit_null_chi_square,
        fit_delta_chi_square=float(fit_delta),
        heldout_chi_square=heldout_chi_square,
        heldout_null_chi_square=heldout_null_chi_square,
        heldout_delta_chi_square=float(heldout_delta),
        heldout_independent=heldout_independent,
        cross_modal_source_routing_admissible=
            cross_modal_source_routing_admissible,
    )


def source_family_payload(
    signatures: Iterable[SourceFamilySignature],
    residual,
    covariance,
    **kwargs,
) -> dict:
    rows = tuple(signatures)
    call_kwargs = dict(kwargs)

    heldout_rows = None
    if call_kwargs.get("heldout_signatures") is not None:
        heldout_rows = tuple(call_kwargs["heldout_signatures"])
        call_kwargs["heldout_signatures"] = heldout_rows

    report = analyze_source_family_signatures(
        rows,
        residual,
        covariance,
        **call_kwargs,
    )

    fit_residual = _validate_vector(residual, name="residual")
    fit_covariance = _validate_covariance(
        covariance,
        fit_residual.size,
        name="covariance",
    )

    heldout_input = None
    if heldout_rows is not None:
        heldout_residual = _validate_vector(
            call_kwargs["heldout_residual"],
            name="heldout_residual",
        )
        heldout_covariance = _validate_covariance(
            call_kwargs["heldout_covariance"],
            heldout_residual.size,
            name="heldout_covariance",
        )
        heldout_input = {
            "signatures": [
                {
                    "name": row.name,
                    "values": [float(x) for x in row.validate()],
                    "normalization": row.normalization,
                    "provenance": asdict(row.provenance),
                }
                for row in heldout_rows
            ],
            "residual": [float(x) for x in heldout_residual],
            "covariance": heldout_covariance.tolist(),
            "independent": bool(report.heldout_independent),
        }

    payload = {
        "schema": SCHEMA,
        "status": "CANDIDATE_ONLY",
        "physical_source_selected": False,
        "source_family_state": report.geometry.state,
        "route": report.route,
        "geometry": {
            **asdict(report.geometry),
            "condition_number": (
                report.geometry.condition_number
                if math.isfinite(report.geometry.condition_number)
                else "INF"
            ),
        },
        "fit_input": {
            "signatures": [
                {
                    "name": row.name,
                    "values": [float(x) for x in row.validate()],
                    "normalization": row.normalization,
                    "provenance": asdict(row.provenance),
                }
                for row in rows
            ],
            "residual": [float(x) for x in fit_residual],
            "covariance": fit_covariance.tolist(),
        },
        "fit": {
            "amplitudes": (
                [float(x) for x in report.amplitudes]
                if report.amplitudes is not None
                else None
            ),
            "amplitude_std": (
                [float(x) for x in report.amplitude_std]
                if report.amplitude_std is not None
                else None
            ),
            "chi_square": report.fit_chi_square,
            "null_chi_square": report.fit_null_chi_square,
            "delta_chi_square": report.fit_delta_chi_square,
        },
        "heldout_input": heldout_input,
        "heldout": {
            "independent": report.heldout_independent,
            "chi_square": report.heldout_chi_square,
            "null_chi_square": report.heldout_null_chi_square,
            "delta_chi_square": report.heldout_delta_chi_square,
        },
        "cross_modal_source_routing_admissible":
            report.cross_modal_source_routing_admissible,
    }
    payload["packet_sha256"] = hashlib.sha256(
        _canonical_json(payload)
    ).hexdigest()
    verify_source_family_payload(payload)
    return payload


def verify_source_family_payload(payload: dict) -> None:
    if payload.get("schema") != SCHEMA:
        raise SourceFamilyIdentifiabilityError("unexpected payload schema")
    if payload.get("physical_source_selected") is not False:
        raise SourceFamilyIdentifiabilityError(
            "physical_source_selected must be exactly false"
        )
    if payload.get("source_family_state") not in {
        "UNDERDETERMINED",
        "ILL_CONDITIONED",
        "IDENTIFIABLE",
    }:
        raise SourceFamilyIdentifiabilityError("invalid source_family_state")
    if payload.get("route") not in {
        "REQUEST_MORE_INDEPENDENT_CHANNELS",
        "REQUEST_BETTER_CONDITIONING",
        "REQUEST_HELD_OUT_VALIDATION",
        "NO_SOURCE_ROUTE",
        "STOP_DECLARED_SOURCE_FAMILY_MODEL",
        "ALLOW_CANDIDATE_SOURCE_FAMILY_TESTS",
    }:
        raise SourceFamilyIdentifiabilityError("invalid source-family route")

    fit_input = payload.get("fit_input")
    if not isinstance(fit_input, dict):
        raise SourceFamilyIdentifiabilityError("fit_input must be a mapping")
    signatures = fit_input.get("signatures")
    if not isinstance(signatures, list) or not signatures:
        raise SourceFamilyIdentifiabilityError(
            "fit_input.signatures must be a non-empty list"
        )
    names = []
    channel_count = None
    for index, signature in enumerate(signatures):
        if not isinstance(signature, dict):
            raise SourceFamilyIdentifiabilityError(
                f"fit_input.signatures[{index}] must be a mapping"
            )
        name = _nonempty(
            f"fit_input.signatures[{index}].name",
            signature.get("name"),
        )
        names.append(name)
        _nonempty(
            f"fit_input.signatures[{index}].normalization",
            signature.get("normalization"),
        )
        values = _validate_vector(
            signature.get("values"),
            name=f"fit_input.signatures[{index}].values",
        )
        if channel_count is None:
            channel_count = int(values.size)
        elif int(values.size) != channel_count:
            raise SourceFamilyIdentifiabilityError(
                "fit signature channel counts must match"
            )
    if len(set(names)) != len(names):
        raise SourceFamilyIdentifiabilityError(
            "fit signature names must be unique"
        )

    residual = _validate_vector(
        fit_input.get("residual"),
        name="fit_input.residual",
    )
    if residual.size != channel_count:
        raise SourceFamilyIdentifiabilityError(
            "fit residual length must match signature channel count"
        )
    _validate_covariance(
        fit_input.get("covariance"),
        int(residual.size),
        name="fit_input.covariance",
    )

    fit = payload.get("fit")
    if not isinstance(fit, dict):
        raise SourceFamilyIdentifiabilityError("fit must be a mapping")
    state = payload["source_family_state"]
    amplitudes = fit.get("amplitudes")
    if state in {"UNDERDETERMINED", "ILL_CONDITIONED"}:
        if amplitudes is not None:
            raise SourceFamilyIdentifiabilityError(
                "non-identifiable states must not claim unique amplitudes"
            )
    elif not isinstance(amplitudes, list) or len(amplitudes) != len(signatures):
        raise SourceFamilyIdentifiabilityError(
            "IDENTIFIABLE payload must contain one amplitude per source family"
        )

    digest = payload.get("packet_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise SourceFamilyIdentifiabilityError(
            "packet_sha256 must be a 64-character digest"
        )
    if any(ch not in "0123456789abcdef" for ch in digest.lower()):
        raise SourceFamilyIdentifiabilityError(
            "packet_sha256 must be hexadecimal"
        )

    base = dict(payload)
    base.pop("packet_sha256", None)
    expected = hashlib.sha256(_canonical_json(base)).hexdigest()
    if digest.lower() != expected:
        raise SourceFamilyIdentifiabilityError("packet_sha256 mismatch")
