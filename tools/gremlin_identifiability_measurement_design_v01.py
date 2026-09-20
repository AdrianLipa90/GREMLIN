"""GREMLIN identifiability-driven measurement design v0.1.

Computes how candidate measurement channels change source-family information
geometry. Supports independent scalar channels and correlated measurement
blocks through a Schur-complement conditional update.

This module does not select physical sources.
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
from tools.gremlin_source_family_signature_identifiability_v01 import (
    SourceFamilyIdentifiabilityError,
    SourceFamilySignature,
    weighted_gram_matrix,
)


SCHEMA = "GREMLIN_IDENTIFIABILITY_MEASUREMENT_DESIGN_V0_1"


class MeasurementDesignError(ValueError):
    pass


def _finite(name: str, value: float) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise MeasurementDesignError(f"{name} must be finite") from exc
    if not math.isfinite(value):
        raise MeasurementDesignError(f"{name} must be finite")
    return value


def _positive(name: str, value: float) -> float:
    value = _finite(name, value)
    if value <= 0.0:
        raise MeasurementDesignError(f"{name} must be > 0")
    return value


def _nonempty(name: str, value: str) -> str:
    value = str(value).strip()
    if not value:
        raise MeasurementDesignError(f"{name} must be non-empty")
    return value


def _canonical_json(value) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _vector(values, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0:
        raise MeasurementDesignError(
            f"{name} must be a non-empty one-dimensional vector"
        )
    if not np.all(np.isfinite(array)):
        raise MeasurementDesignError(f"{name} must be finite")
    return array


def _matrix(values, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 2 or min(array.shape) <= 0:
        raise MeasurementDesignError(
            f"{name} must be a non-empty two-dimensional matrix"
        )
    if not np.all(np.isfinite(array)):
        raise MeasurementDesignError(f"{name} must be finite")
    return array


def _positive_definite(values, *, size: int, name: str) -> np.ndarray:
    array = _matrix(values, name=name)
    if array.shape != (size, size):
        raise MeasurementDesignError(
            f"{name} must have shape ({size}, {size})"
        )
    if not np.allclose(array, array.T, rtol=0.0, atol=1e-12):
        raise MeasurementDesignError(f"{name} must be symmetric")
    try:
        np.linalg.cholesky(array)
    except np.linalg.LinAlgError as exc:
        raise MeasurementDesignError(
            f"{name} must be positive definite"
        ) from exc
    return array


def _validate_provenance(provenance: EvidenceProvenance) -> None:
    try:
        provenance.validate()
    except CrossModalEvidenceError as exc:
        raise MeasurementDesignError(
            f"measurement provenance invalid: {exc}"
        ) from exc


@dataclass(frozen=True)
class MeasurementSignature:
    name: str
    source_signature: Sequence[float]
    provenance: EvidenceProvenance

    def validate(self, source_count: int) -> np.ndarray:
        _nonempty("measurement.name", self.name)
        _validate_provenance(self.provenance)
        signature = _vector(
            self.source_signature,
            name=f"measurement[{self.name}].source_signature",
        )
        if signature.size != source_count:
            raise MeasurementDesignError(
                f"measurement[{self.name}] signature length must equal "
                f"source count {source_count}"
            )
        return signature


@dataclass(frozen=True)
class IndependentMeasurement:
    signature: MeasurementSignature
    variance: float

    def validate(self, source_count: int) -> np.ndarray:
        q = self.signature.validate(source_count)
        _positive(
            f"measurement[{self.signature.name}].variance",
            self.variance,
        )
        return q


@dataclass(frozen=True)
class MeasurementGeometryUpdate:
    state_before: str
    state_after: str
    rank_before: int
    rank_after: int
    rank_gain: int
    nullity_before: int
    nullity_after: int
    nullspace_power: float
    condition_before: float
    condition_after: float
    lambda_min_before: float | None
    lambda_min_after: float | None
    e_optimal_gain: float | None
    d_optimal_gain: float | None
    delta_gram: tuple[tuple[float, ...], ...]


def _gram_geometry(
    gram,
    *,
    rank_rtol: float,
    max_condition_number: float,
) -> dict:
    g = _matrix(gram, name="gram")
    if g.shape[0] != g.shape[1]:
        raise MeasurementDesignError("gram must be square")
    if not np.allclose(g, g.T, rtol=0.0, atol=1e-12):
        raise MeasurementDesignError("gram must be symmetric")

    eigvals, eigvecs = np.linalg.eigh(g)
    scale = max(1.0, float(np.max(np.abs(eigvals))))
    negative_tol = rank_rtol * max(g.shape) * scale
    if float(np.min(eigvals)) < -negative_tol:
        raise MeasurementDesignError("gram must be positive semidefinite")

    eigvals = np.where(eigvals < 0.0, 0.0, eigvals)
    largest = float(eigvals[-1]) if eigvals.size else 0.0
    threshold = rank_rtol * max(g.shape) * max(1.0, largest)
    rank = int(np.count_nonzero(eigvals > threshold))
    source_count = g.shape[0]
    nullity = source_count - rank

    if rank < source_count:
        state = "UNDERDETERMINED"
        condition = math.inf
        lambda_min = None
    else:
        smallest = float(eigvals[0])
        condition = largest / smallest
        lambda_min = smallest
        state = (
            "IDENTIFIABLE"
            if condition <= max_condition_number
            else "ILL_CONDITIONED"
        )

    null_mask = eigvals <= threshold
    nullspace = eigvecs[:, null_mask]
    return {
        "state": state,
        "rank": rank,
        "nullity": nullity,
        "condition": float(condition),
        "lambda_min": lambda_min,
        "nullspace": nullspace,
        "threshold": float(threshold),
        "eigvals": eigvals,
    }


def _geometry_update(
    gram,
    delta_gram,
    *,
    rank_rtol: float,
    max_condition_number: float,
) -> MeasurementGeometryUpdate:
    rank_rtol = _positive("rank_rtol", rank_rtol)
    max_condition_number = _positive(
        "max_condition_number", max_condition_number
    )
    g = _matrix(gram, name="gram")
    delta = _matrix(delta_gram, name="delta_gram")
    if delta.shape != g.shape:
        raise MeasurementDesignError(
            "delta_gram must have the same shape as gram"
        )
    if not np.allclose(delta, delta.T, rtol=0.0, atol=1e-12):
        raise MeasurementDesignError("delta_gram must be symmetric")

    before = _gram_geometry(
        g,
        rank_rtol=rank_rtol,
        max_condition_number=max_condition_number,
    )
    after_g = g + delta
    after = _gram_geometry(
        after_g,
        rank_rtol=rank_rtol,
        max_condition_number=max_condition_number,
    )

    nullspace = before["nullspace"]
    if nullspace.shape[1] == 0:
        nullspace_power = 0.0
    else:
        nullspace_power = float(
            np.trace(nullspace.T @ delta @ nullspace)
        )

    if before["rank"] == g.shape[0]:
        e_gain = float(after["lambda_min"] - before["lambda_min"])
        sign0, logdet0 = np.linalg.slogdet(g)
        sign1, logdet1 = np.linalg.slogdet(after_g)
        if sign0 <= 0.0 or sign1 <= 0.0:
            raise MeasurementDesignError(
                "full-rank Gram matrices must have positive determinant"
            )
        d_gain = float(logdet1 - logdet0)
    else:
        e_gain = None
        d_gain = None

    return MeasurementGeometryUpdate(
        state_before=before["state"],
        state_after=after["state"],
        rank_before=before["rank"],
        rank_after=after["rank"],
        rank_gain=after["rank"] - before["rank"],
        nullity_before=before["nullity"],
        nullity_after=after["nullity"],
        nullspace_power=float(nullspace_power),
        condition_before=float(before["condition"]),
        condition_after=float(after["condition"]),
        lambda_min_before=before["lambda_min"],
        lambda_min_after=after["lambda_min"],
        e_optimal_gain=e_gain,
        d_optimal_gain=d_gain,
        delta_gram=tuple(
            tuple(float(x) for x in row)
            for row in delta
        ),
    )


def _base_signature_matrix(
    signatures: Iterable[SourceFamilySignature],
) -> tuple[tuple[SourceFamilySignature, ...], np.ndarray]:
    rows = tuple(signatures)
    if not rows:
        raise MeasurementDesignError(
            "at least one current source-family signature is required"
        )
    columns = []
    channel_count = None
    names = []
    for row in rows:
        names.append(row.name)
        try:
            vector = row.validate()
        except SourceFamilyIdentifiabilityError as exc:
            raise MeasurementDesignError(
                f"source-family signature invalid: {exc}"
            ) from exc
        if channel_count is None:
            channel_count = int(vector.size)
        elif int(vector.size) != channel_count:
            raise MeasurementDesignError(
                "all current source-family signatures must have equal "
                "channel count"
            )
        columns.append(vector)
    if len(set(names)) != len(names):
        raise MeasurementDesignError(
            "source-family signature names must be unique"
        )
    return rows, np.column_stack(columns)


def independent_measurement_update(
    signatures: Iterable[SourceFamilySignature],
    covariance,
    measurement: IndependentMeasurement,
    *,
    rank_rtol: float = 1e-10,
    max_condition_number: float = 1e8,
) -> MeasurementGeometryUpdate:
    rows, matrix = _base_signature_matrix(signatures)
    source_count = len(rows)
    q = measurement.validate(source_count)
    variance = _positive(
        f"measurement[{measurement.signature.name}].variance",
        measurement.variance,
    )

    try:
        gram = weighted_gram_matrix(rows, covariance)
    except SourceFamilyIdentifiabilityError as exc:
        raise MeasurementDesignError(str(exc)) from exc

    delta = np.outer(q, q) / variance
    return _geometry_update(
        gram,
        delta,
        rank_rtol=rank_rtol,
        max_condition_number=max_condition_number,
    )


def correlated_measurement_block_update(
    signatures: Iterable[SourceFamilySignature],
    covariance,
    measurements: Iterable[MeasurementSignature],
    candidate_covariance,
    cross_covariance,
    *,
    rank_rtol: float = 1e-10,
    max_condition_number: float = 1e8,
) -> MeasurementGeometryUpdate:
    rows, matrix = _base_signature_matrix(signatures)
    source_count = len(rows)
    channel_count = matrix.shape[0]

    block = tuple(measurements)
    if not block:
        raise MeasurementDesignError(
            "at least one candidate measurement is required"
        )
    names = [measurement.name for measurement in block]
    if len(set(names)) != len(names):
        raise MeasurementDesignError(
            "candidate measurement names must be unique"
        )
    q = np.vstack(
        [measurement.validate(source_count) for measurement in block]
    )
    candidate_count = q.shape[0]

    sigma = _positive_definite(
        covariance,
        size=channel_count,
        name="covariance",
    )
    omega = _positive_definite(
        candidate_covariance,
        size=candidate_count,
        name="candidate_covariance",
    )
    cross = _matrix(
        cross_covariance,
        name="cross_covariance",
    )
    if cross.shape != (channel_count, candidate_count):
        raise MeasurementDesignError(
            "cross_covariance must have shape "
            f"({channel_count}, {candidate_count})"
        )

    joint = np.block(
        [
            [sigma, cross],
            [cross.T, omega],
        ]
    )
    _positive_definite(
        joint,
        size=channel_count + candidate_count,
        name="joint_covariance",
    )

    sigma_inv_cross = np.linalg.solve(sigma, cross)
    sigma_inv_matrix = np.linalg.solve(sigma, matrix)
    omega_cond = omega - cross.T @ sigma_inv_cross
    q_cond = q - cross.T @ sigma_inv_matrix

    _positive_definite(
        omega_cond,
        size=candidate_count,
        name="conditional_candidate_covariance",
    )
    delta = q_cond.T @ np.linalg.solve(omega_cond, q_cond)

    try:
        gram = weighted_gram_matrix(rows, sigma)
    except SourceFamilyIdentifiabilityError as exc:
        raise MeasurementDesignError(str(exc)) from exc

    return _geometry_update(
        gram,
        delta,
        rank_rtol=rank_rtol,
        max_condition_number=max_condition_number,
    )


def rank_independent_measurements(
    signatures: Iterable[SourceFamilySignature],
    covariance,
    candidates: Iterable[IndependentMeasurement],
    *,
    policy: str,
    rank_rtol: float = 1e-10,
    max_condition_number: float = 1e8,
) -> tuple[tuple[str, MeasurementGeometryUpdate], ...]:
    rows = tuple(signatures)
    options = tuple(candidates)
    if not options:
        raise MeasurementDesignError(
            "at least one candidate measurement is required"
        )
    policy = _nonempty("policy", policy)
    if policy not in {
        "RANK_THEN_NULLSPACE",
        "E_OPTIMAL",
        "D_OPTIMAL",
    }:
        raise MeasurementDesignError("unsupported measurement design policy")

    reports = [
        (
            option.signature.name,
            independent_measurement_update(
                rows,
                covariance,
                option,
                rank_rtol=rank_rtol,
                max_condition_number=max_condition_number,
            ),
        )
        for option in options
    ]

    state_before = reports[0][1].state_before
    if any(report.state_before != state_before for _, report in reports):
        raise MeasurementDesignError(
            "candidate reports disagree on current geometry state"
        )

    if state_before == "UNDERDETERMINED":
        if policy != "RANK_THEN_NULLSPACE":
            raise MeasurementDesignError(
                "rank-deficient geometry requires RANK_THEN_NULLSPACE policy"
            )
        key = lambda item: (
            -item[1].rank_gain,
            -item[1].nullspace_power,
            item[0],
        )
    else:
        if policy == "RANK_THEN_NULLSPACE":
            raise MeasurementDesignError(
                "full-rank geometry requires E_OPTIMAL or D_OPTIMAL policy"
            )
        if policy == "E_OPTIMAL":
            key = lambda item: (
                -(item[1].e_optimal_gain or 0.0),
                item[0],
            )
        else:
            key = lambda item: (
                -(item[1].d_optimal_gain or 0.0),
                item[0],
            )

    return tuple(sorted(reports, key=key))


def measurement_design_payload(
    signatures: Iterable[SourceFamilySignature],
    covariance,
    candidates: Iterable[IndependentMeasurement],
    *,
    policy: str,
    rank_rtol: float = 1e-10,
    max_condition_number: float = 1e8,
) -> dict:
    rows = tuple(signatures)
    options = tuple(candidates)
    ranked = rank_independent_measurements(
        rows,
        covariance,
        options,
        policy=policy,
        rank_rtol=rank_rtol,
        max_condition_number=max_condition_number,
    )

    by_name = {option.signature.name: option for option in options}
    payload = {
        "schema": SCHEMA,
        "status": "CANDIDATE_ONLY",
        "physical_source_selected": False,
        "policy": policy,
        "current_source_families": [
            {
                "name": row.name,
                "values": [float(x) for x in row.validate()],
                "normalization": row.normalization,
                "provenance": asdict(row.provenance),
            }
            for row in rows
        ],
        "covariance": np.asarray(covariance, dtype=float).tolist(),
        "candidates": [
            {
                "name": name,
                "source_signature": [
                    float(x)
                    for x in by_name[name].signature.validate(len(rows))
                ],
                "variance": float(by_name[name].variance),
                "provenance": asdict(by_name[name].signature.provenance),
                "geometry_update": {
                    **asdict(report),
                    "condition_before": (
                        report.condition_before
                        if math.isfinite(report.condition_before)
                        else "INF"
                    ),
                    "condition_after": (
                        report.condition_after
                        if math.isfinite(report.condition_after)
                        else "INF"
                    ),
                },
            }
            for name, report in ranked
        ],
        "selected_candidate": ranked[0][0],
        "selection_is_physical_experiment_verdict": False,
    }
    payload["packet_sha256"] = hashlib.sha256(
        _canonical_json(payload)
    ).hexdigest()
    verify_measurement_design_payload(payload)
    return payload


def verify_measurement_design_payload(payload: dict) -> None:
    if payload.get("schema") != SCHEMA:
        raise MeasurementDesignError("unexpected payload schema")
    if payload.get("physical_source_selected") is not False:
        raise MeasurementDesignError(
            "physical_source_selected must be exactly false"
        )
    if payload.get("selection_is_physical_experiment_verdict") is not False:
        raise MeasurementDesignError(
            "measurement selection must not be a physical experiment verdict"
        )
    if payload.get("policy") not in {
        "RANK_THEN_NULLSPACE",
        "E_OPTIMAL",
        "D_OPTIMAL",
    }:
        raise MeasurementDesignError("invalid measurement policy")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise MeasurementDesignError(
            "candidates must be a non-empty list"
        )
    selected = payload.get("selected_candidate")
    if selected != candidates[0].get("name"):
        raise MeasurementDesignError(
            "selected_candidate must equal the first ranked candidate"
        )

    digest = payload.get("packet_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise MeasurementDesignError(
            "packet_sha256 must be a 64-character digest"
        )
    if any(ch not in "0123456789abcdef" for ch in digest.lower()):
        raise MeasurementDesignError("packet_sha256 must be hexadecimal")

    base = dict(payload)
    base.pop("packet_sha256", None)
    expected = hashlib.sha256(_canonical_json(base)).hexdigest()
    if digest.lower() != expected:
        raise MeasurementDesignError("packet_sha256 mismatch")
