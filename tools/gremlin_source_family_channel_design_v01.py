"""GREMLIN source-family measurement channel design v0.1.

Exact rank-lift/nullspace diagnostics plus a deterministic greedy planning
heuristic. This module does not select a physical source and does not assert
experimental feasibility.
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
    signature_geometry,
)


SCHEMA = "GREMLIN_SOURCE_FAMILY_CHANNEL_DESIGN_V0_1"


class SourceFamilyChannelDesignError(ValueError):
    pass


def _finite(name: str, value: float) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise SourceFamilyChannelDesignError(f"{name} must be finite") from exc
    if not math.isfinite(value):
        raise SourceFamilyChannelDesignError(f"{name} must be finite")
    return value


def _positive(name: str, value: float) -> float:
    value = _finite(name, value)
    if value <= 0.0:
        raise SourceFamilyChannelDesignError(f"{name} must be > 0")
    return value


def _nonempty(name: str, value: str) -> str:
    value = str(value).strip()
    if not value:
        raise SourceFamilyChannelDesignError(f"{name} must be non-empty")
    return value


def _canonical_json(value) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


@dataclass(frozen=True)
class CandidateMeasurementChannel:
    name: str
    source_response: Sequence[float]
    sigma: float
    provenance: EvidenceProvenance
    normalization: str
    independent_of_existing: bool = True
    feasibility_note: str = "NOT_ASSESSED"

    def validate(self, source_count: int) -> np.ndarray:
        _nonempty("channel.name", self.name)
        _nonempty("channel.normalization", self.normalization)
        _nonempty("channel.feasibility_note", self.feasibility_note)
        _positive("channel.sigma", self.sigma)
        if self.independent_of_existing is not True:
            raise SourceFamilyChannelDesignError(
                "v0.1 admits only channels explicitly independent of the "
                "existing covariance block"
            )
        try:
            self.provenance.validate()
        except CrossModalEvidenceError as exc:
            raise SourceFamilyChannelDesignError(
                f"channel[{self.name}] provenance invalid: {exc}"
            ) from exc

        response = np.asarray(self.source_response, dtype=float)
        if response.ndim != 1 or response.size != source_count:
            raise SourceFamilyChannelDesignError(
                f"channel[{self.name}].source_response must contain exactly "
                f"{source_count} source-family values"
            )
        if not np.all(np.isfinite(response)):
            raise SourceFamilyChannelDesignError(
                f"channel[{self.name}].source_response must be finite"
            )
        return response


@dataclass(frozen=True)
class ChannelEvaluation:
    name: str
    classification: str
    current_rank: int
    augmented_rank: int
    rank_gain: int
    nullspace_projection_norm: float
    smallest_singular_before: float
    smallest_singular_after: float
    condition_before: float
    condition_after: float


@dataclass(frozen=True)
class ChannelSetEvaluation:
    current_rank: int
    augmented_rank: int
    rank_gain: int
    current_nullity: int
    nullspace_coverage_rank: int
    full_nullspace_covered: bool
    final_condition_number: float


@dataclass(frozen=True)
class GreedyChannelPlan:
    route: str
    selected_channels: tuple[str, ...]
    initial_rank: int
    final_rank: int
    source_count: int
    initial_condition_number: float
    final_condition_number: float
    full_rank_reached: bool
    conditioning_gate_passed: bool
    experimental_feasibility_asserted: bool = False
    physical_source_selected: bool = False


def _current_whitened_geometry(
    signatures: Iterable[SourceFamilySignature],
    covariance,
    *,
    rank_rtol: float,
    max_condition_number: float,
    collinear_tol: float,
) -> tuple[
    tuple[SourceFamilySignature, ...],
    np.ndarray,
    np.ndarray,
    int,
    np.ndarray,
    float,
    float,
    int,
]:
    rows = tuple(signatures)
    try:
        report, matrix, sigma, validated_rows = signature_geometry(
            rows,
            covariance,
            rank_rtol=rank_rtol,
            max_condition_number=max_condition_number,
            collinear_tol=collinear_tol,
        )
    except SourceFamilyIdentifiabilityError as exc:
        raise SourceFamilyChannelDesignError(str(exc)) from exc

    chol = np.linalg.cholesky(sigma)
    whitened = np.linalg.solve(chol, matrix)
    _, singular_values, vh = np.linalg.svd(whitened, full_matrices=True)
    null_basis = vh[report.rank:, :]
    smallest = (
        float(singular_values[report.source_count - 1])
        if report.rank == report.source_count
        else 0.0
    )
    return (
        validated_rows,
        whitened,
        null_basis,
        report.rank,
        singular_values,
        smallest,
        report.condition_number,
        report.source_count,
    )


def _rank_condition(
    matrix: np.ndarray,
    *,
    source_count: int,
    rank_rtol: float,
) -> tuple[int, float, float, float]:
    _, singular_values, _ = np.linalg.svd(matrix, full_matrices=True)
    if singular_values.size:
        threshold = (
            rank_rtol * max(matrix.shape) * float(singular_values[0])
        )
        rank = int(np.count_nonzero(singular_values > threshold))
    else:
        threshold = 0.0
        rank = 0

    if rank == source_count:
        smallest = float(singular_values[source_count - 1])
        condition = float(singular_values[0]) / smallest
    else:
        smallest = 0.0
        condition = math.inf
    return rank, smallest, condition, float(threshold)


def evaluate_candidate_channel(
    signatures: Iterable[SourceFamilySignature],
    covariance,
    channel: CandidateMeasurementChannel,
    *,
    rank_rtol: float = 1e-10,
    max_condition_number: float = 1e8,
    collinear_tol: float = 1e-8,
    improvement_rtol: float = 1e-12,
) -> ChannelEvaluation:
    rank_rtol = _positive("rank_rtol", rank_rtol)
    _positive("max_condition_number", max_condition_number)
    _positive("collinear_tol", collinear_tol)
    improvement_rtol = _positive("improvement_rtol", improvement_rtol)

    (
        rows,
        whitened,
        null_basis,
        current_rank,
        _,
        smallest_before,
        condition_before,
        source_count,
    ) = _current_whitened_geometry(
        signatures,
        covariance,
        rank_rtol=rank_rtol,
        max_condition_number=max_condition_number,
        collinear_tol=collinear_tol,
    )

    response = channel.validate(source_count)
    whitened_row = response / float(channel.sigma)
    augmented = np.vstack([whitened, whitened_row])
    augmented_rank, smallest_after, condition_after, _ = _rank_condition(
        augmented,
        source_count=source_count,
        rank_rtol=rank_rtol,
    )
    rank_gain = augmented_rank - current_rank

    if null_basis.size:
        projection = null_basis @ whitened_row
        projection_norm = float(np.linalg.norm(projection))
    else:
        projection_norm = 0.0

    if rank_gain > 0:
        classification = "RANK_LIFTING"
    elif current_rank < source_count:
        classification = "NULLSPACE_BLIND"
    else:
        condition_improved = (
            math.isfinite(condition_after)
            and condition_after
            < condition_before * (1.0 - improvement_rtol)
        )
        smallest_improved = (
            smallest_after
            > smallest_before * (1.0 + improvement_rtol)
        )
        classification = (
            "CONDITION_IMPROVING"
            if condition_improved or smallest_improved
            else "NO_GEOMETRIC_GAIN"
        )

    if rank_gain < 0 or rank_gain > 1:
        raise SourceFamilyChannelDesignError(
            "single scalar channel produced impossible rank gain"
        )

    return ChannelEvaluation(
        name=channel.name,
        classification=classification,
        current_rank=current_rank,
        augmented_rank=augmented_rank,
        rank_gain=rank_gain,
        nullspace_projection_norm=projection_norm,
        smallest_singular_before=smallest_before,
        smallest_singular_after=smallest_after,
        condition_before=condition_before,
        condition_after=condition_after,
    )


def evaluate_candidate_channel_set(
    signatures: Iterable[SourceFamilySignature],
    covariance,
    channels: Iterable[CandidateMeasurementChannel],
    *,
    rank_rtol: float = 1e-10,
    max_condition_number: float = 1e8,
    collinear_tol: float = 1e-8,
) -> ChannelSetEvaluation:
    rank_rtol = _positive("rank_rtol", rank_rtol)
    _positive("max_condition_number", max_condition_number)
    _positive("collinear_tol", collinear_tol)

    (
        _,
        whitened,
        null_basis,
        current_rank,
        _,
        _,
        _,
        source_count,
    ) = _current_whitened_geometry(
        signatures,
        covariance,
        rank_rtol=rank_rtol,
        max_condition_number=max_condition_number,
        collinear_tol=collinear_tol,
    )

    channel_rows = tuple(channels)
    if not channel_rows:
        raise SourceFamilyChannelDesignError(
            "at least one candidate channel is required"
        )
    names = [row.name for row in channel_rows]
    if len(set(names)) != len(names):
        raise SourceFamilyChannelDesignError(
            "candidate channel names must be unique"
        )

    whitened_rows = np.vstack(
        [
            row.validate(source_count) / float(row.sigma)
            for row in channel_rows
        ]
    )
    augmented = np.vstack([whitened, whitened_rows])
    augmented_rank, _, final_condition, _ = _rank_condition(
        augmented,
        source_count=source_count,
        rank_rtol=rank_rtol,
    )

    if null_basis.size:
        coverage = whitened_rows @ null_basis.T
        coverage_singular = np.linalg.svd(
            coverage,
            compute_uv=False,
        )
        if coverage_singular.size:
            coverage_threshold = (
                rank_rtol
                * max(coverage.shape)
                * float(coverage_singular[0])
            )
            coverage_rank = int(
                np.count_nonzero(coverage_singular > coverage_threshold)
            )
        else:
            coverage_rank = 0
    else:
        coverage_rank = 0

    rank_gain = augmented_rank - current_rank
    if rank_gain != coverage_rank:
        raise SourceFamilyChannelDesignError(
            "numerical rank-lift/nullspace-coverage inconsistency"
        )

    current_nullity = source_count - current_rank
    return ChannelSetEvaluation(
        current_rank=current_rank,
        augmented_rank=augmented_rank,
        rank_gain=rank_gain,
        current_nullity=current_nullity,
        nullspace_coverage_rank=coverage_rank,
        full_nullspace_covered=(coverage_rank == current_nullity),
        final_condition_number=final_condition,
    )


def greedy_channel_plan(
    signatures: Iterable[SourceFamilySignature],
    covariance,
    channels: Iterable[CandidateMeasurementChannel],
    *,
    rank_rtol: float = 1e-10,
    max_condition_number: float = 1e8,
    collinear_tol: float = 1e-8,
    max_channels: int | None = None,
) -> GreedyChannelPlan:
    rank_rtol = _positive("rank_rtol", rank_rtol)
    max_condition_number = _positive(
        "max_condition_number",
        max_condition_number,
    )
    _positive("collinear_tol", collinear_tol)

    (
        _,
        current_matrix,
        _,
        initial_rank,
        _,
        _,
        initial_condition,
        source_count,
    ) = _current_whitened_geometry(
        signatures,
        covariance,
        rank_rtol=rank_rtol,
        max_condition_number=max_condition_number,
        collinear_tol=collinear_tol,
    )

    candidates = tuple(channels)
    if not candidates:
        raise SourceFamilyChannelDesignError(
            "at least one candidate channel is required"
        )
    if len({row.name for row in candidates}) != len(candidates):
        raise SourceFamilyChannelDesignError(
            "candidate channel names must be unique"
        )
    for row in candidates:
        row.validate(source_count)

    if max_channels is None:
        budget = len(candidates)
    else:
        if not isinstance(max_channels, int) or max_channels <= 0:
            raise SourceFamilyChannelDesignError(
                "max_channels must be a positive integer"
            )
        budget = min(max_channels, len(candidates))

    selected: list[str] = []
    remaining = list(candidates)
    matrix = current_matrix.copy()
    current_rank, current_smallest, current_condition, _ = _rank_condition(
        matrix,
        source_count=source_count,
        rank_rtol=rank_rtol,
    )

    for _ in range(budget):
        if (
            current_rank == source_count
            and current_condition <= max_condition_number
        ):
            break

        evaluations: list[tuple[CandidateMeasurementChannel, int, float, float]] = []
        for candidate in remaining:
            row = candidate.validate(source_count) / float(candidate.sigma)
            augmented = np.vstack([matrix, row])
            rank_after, smallest_after, condition_after, _ = _rank_condition(
                augmented,
                source_count=source_count,
                rank_rtol=rank_rtol,
            )
            evaluations.append(
                (
                    candidate,
                    rank_after - current_rank,
                    smallest_after,
                    condition_after,
                )
            )

        evaluations.sort(
            key=lambda item: (
                -item[1],
                -item[2],
                item[3],
                item[0].name,
            )
        )
        candidate, rank_gain, smallest_after, condition_after = evaluations[0]

        condition_improved = (
            math.isfinite(condition_after)
            and (
                not math.isfinite(current_condition)
                or condition_after < current_condition
            )
        )
        smallest_improved = smallest_after > current_smallest

        if rank_gain <= 0 and not condition_improved and not smallest_improved:
            break

        row = candidate.validate(source_count) / float(candidate.sigma)
        matrix = np.vstack([matrix, row])
        selected.append(candidate.name)
        remaining = [row_candidate for row_candidate in remaining if row_candidate.name != candidate.name]
        current_rank, current_smallest, current_condition, _ = _rank_condition(
            matrix,
            source_count=source_count,
            rank_rtol=rank_rtol,
        )

    full_rank = current_rank == source_count
    conditioning_pass = (
        full_rank and current_condition <= max_condition_number
    )

    if initial_rank < source_count:
        if not selected or current_rank == initial_rank:
            route = "NO_AVAILABLE_CHANNEL_BREAKS_DEGENERACY"
        else:
            route = "PROPOSE_RANK_LIFTING_MEASUREMENT"
    elif initial_condition > max_condition_number:
        if selected and current_condition < initial_condition:
            route = "PROPOSE_CONDITIONING_MEASUREMENT"
        else:
            route = "NO_AVAILABLE_CHANNEL_IMPROVES_CONDITIONING"
    else:
        route = "OPTIONAL_PRECISION_PLANNING"

    return GreedyChannelPlan(
        route=route,
        selected_channels=tuple(selected),
        initial_rank=initial_rank,
        final_rank=current_rank,
        source_count=source_count,
        initial_condition_number=initial_condition,
        final_condition_number=current_condition,
        full_rank_reached=full_rank,
        conditioning_gate_passed=conditioning_pass,
    )


def channel_design_payload(
    signatures: Iterable[SourceFamilySignature],
    covariance,
    channels: Iterable[CandidateMeasurementChannel],
    *,
    rank_rtol: float = 1e-10,
    max_condition_number: float = 1e8,
    collinear_tol: float = 1e-8,
    max_channels: int | None = None,
) -> dict:
    signature_rows = tuple(signatures)
    channel_rows = tuple(channels)

    try:
        parent_geometry, _, _, _ = signature_geometry(
            signature_rows,
            covariance,
            rank_rtol=rank_rtol,
            max_condition_number=max_condition_number,
            collinear_tol=collinear_tol,
        )
    except SourceFamilyIdentifiabilityError as exc:
        raise SourceFamilyChannelDesignError(str(exc)) from exc

    evaluations = [
        evaluate_candidate_channel(
            signature_rows,
            covariance,
            channel,
            rank_rtol=rank_rtol,
            max_condition_number=max_condition_number,
            collinear_tol=collinear_tol,
        )
        for channel in channel_rows
    ]
    plan = greedy_channel_plan(
        signature_rows,
        covariance,
        channel_rows,
        rank_rtol=rank_rtol,
        max_condition_number=max_condition_number,
        collinear_tol=collinear_tol,
        max_channels=max_channels,
    )

    payload = {
        "schema": SCHEMA,
        "status": "CANDIDATE_ONLY",
        "physical_source_selected": False,
        "experimental_feasibility_asserted": False,
        "parent_source_family_state": parent_geometry.state,
        "parent_rank": parent_geometry.rank,
        "parent_nullity": parent_geometry.nullity,
        "source_families": [row.name for row in signature_rows],
        "candidate_channels": [
            {
                "name": channel.name,
                "source_response": [
                    float(x)
                    for x in channel.validate(parent_geometry.source_count)
                ],
                "sigma": float(channel.sigma),
                "normalization": channel.normalization,
                "independent_of_existing": channel.independent_of_existing,
                "feasibility_note": channel.feasibility_note,
                "provenance": asdict(channel.provenance),
            }
            for channel in channel_rows
        ],
        "evaluations": [
            {
                **asdict(evaluation),
                "condition_before": (
                    evaluation.condition_before
                    if math.isfinite(evaluation.condition_before)
                    else "INF"
                ),
                "condition_after": (
                    evaluation.condition_after
                    if math.isfinite(evaluation.condition_after)
                    else "INF"
                ),
            }
            for evaluation in evaluations
        ],
        "greedy_plan": {
            **asdict(plan),
            "initial_condition_number": (
                plan.initial_condition_number
                if math.isfinite(plan.initial_condition_number)
                else "INF"
            ),
            "final_condition_number": (
                plan.final_condition_number
                if math.isfinite(plan.final_condition_number)
                else "INF"
            ),
        },
        "policy": {
            "rank_rtol": float(rank_rtol),
            "max_condition_number": float(max_condition_number),
            "collinear_tol": float(collinear_tol),
            "max_channels": max_channels,
        },
    }
    payload["packet_sha256"] = hashlib.sha256(
        _canonical_json(payload)
    ).hexdigest()
    verify_channel_design_payload(payload)
    return payload


def verify_channel_design_payload(payload: dict) -> None:
    if payload.get("schema") != SCHEMA:
        raise SourceFamilyChannelDesignError("unexpected payload schema")
    if payload.get("physical_source_selected") is not False:
        raise SourceFamilyChannelDesignError(
            "physical_source_selected must be exactly false"
        )
    if payload.get("experimental_feasibility_asserted") is not False:
        raise SourceFamilyChannelDesignError(
            "experimental_feasibility_asserted must be exactly false"
        )
    if payload.get("parent_source_family_state") not in {
        "UNDERDETERMINED",
        "ILL_CONDITIONED",
        "IDENTIFIABLE",
    }:
        raise SourceFamilyChannelDesignError(
            "invalid parent_source_family_state"
        )

    channels = payload.get("candidate_channels")
    if not isinstance(channels, list) or not channels:
        raise SourceFamilyChannelDesignError(
            "candidate_channels must be a non-empty list"
        )
    names = [row.get("name") for row in channels if isinstance(row, dict)]
    if len(names) != len(channels) or len(set(names)) != len(names):
        raise SourceFamilyChannelDesignError(
            "candidate channel names must be unique"
        )

    plan = payload.get("greedy_plan")
    if not isinstance(plan, dict):
        raise SourceFamilyChannelDesignError(
            "greedy_plan must be a mapping"
        )
    if plan.get("physical_source_selected") is not False:
        raise SourceFamilyChannelDesignError(
            "greedy plan must not select a physical source"
        )
    if plan.get("experimental_feasibility_asserted") is not False:
        raise SourceFamilyChannelDesignError(
            "greedy plan must not assert experimental feasibility"
        )
    if plan.get("route") not in {
        "NO_AVAILABLE_CHANNEL_BREAKS_DEGENERACY",
        "PROPOSE_RANK_LIFTING_MEASUREMENT",
        "PROPOSE_CONDITIONING_MEASUREMENT",
        "NO_AVAILABLE_CHANNEL_IMPROVES_CONDITIONING",
        "OPTIONAL_PRECISION_PLANNING",
    }:
        raise SourceFamilyChannelDesignError(
            "invalid greedy channel-design route"
        )

    digest = payload.get("packet_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise SourceFamilyChannelDesignError(
            "packet_sha256 must be a 64-character digest"
        )
    if any(ch not in "0123456789abcdef" for ch in digest.lower()):
        raise SourceFamilyChannelDesignError(
            "packet_sha256 must be hexadecimal"
        )
    base = dict(payload)
    base.pop("packet_sha256", None)
    expected = hashlib.sha256(_canonical_json(base)).hexdigest()
    if digest.lower() != expected:
        raise SourceFamilyChannelDesignError("packet_sha256 mismatch")
