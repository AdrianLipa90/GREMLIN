"""GREMLIN cross-modal relational evidence packet v0.1.

This module joins independently constrained residual channels and phase
identifiability metadata. It is deliberately source-neutral and fail-closed.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

import numpy as np


SCHEMA = "GREMLIN_CROSS_MODAL_RELATIONAL_EVIDENCE_PACKET_V0_1"


class CrossModalEvidenceError(ValueError):
    pass


def _finite(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise CrossModalEvidenceError(f"{name} must be finite")
    return value


def _positive(name: str, value: float) -> float:
    value = _finite(name, value)
    if value <= 0.0:
        raise CrossModalEvidenceError(f"{name} must be > 0")
    return value


def _nonempty(name: str, value: str) -> str:
    value = str(value).strip()
    if not value:
        raise CrossModalEvidenceError(f"{name} must be non-empty")
    return value


@dataclass(frozen=True)
class EvidenceProvenance:
    repository: str
    branch: str
    commit: str
    schema: str
    receipt: str
    epistemic: str = "CHYBA"

    def validate(self) -> None:
        _nonempty("repository", self.repository)
        _nonempty("branch", self.branch)
        commit = _nonempty("commit", self.commit)
        if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit.lower()):
            raise CrossModalEvidenceError(
                "commit must be a 40-character hexadecimal SHA"
            )
        _nonempty("schema", self.schema)
        _nonempty("receipt", self.receipt)
        _nonempty("epistemic", self.epistemic)


@dataclass(frozen=True)
class ResidualChannel:
    name: str
    observed: float
    predicted: float
    sigma: float
    provenance: EvidenceProvenance
    independently_constrained: bool = True
    circular_fit: bool = False

    def validate(self) -> None:
        _nonempty("channel.name", self.name)
        _finite("channel.observed", self.observed)
        _finite("channel.predicted", self.predicted)
        _positive("channel.sigma", self.sigma)
        self.provenance.validate()

    @property
    def residual(self) -> float:
        self.validate()
        return float(self.observed) - float(self.predicted)

    @property
    def normalized_residual(self) -> float:
        return self.residual / float(self.sigma)


@dataclass(frozen=True)
class PhaseIdentifiability:
    phase_count: int
    cycle_rank: int
    jacobian_rank: int
    fisher_rank: int

    def validate(self) -> None:
        for name, value in (
            ("phase_count", self.phase_count),
            ("cycle_rank", self.cycle_rank),
            ("jacobian_rank", self.jacobian_rank),
            ("fisher_rank", self.fisher_rank),
        ):
            if not isinstance(value, int) or value < 0:
                raise CrossModalEvidenceError(f"{name} must be a non-negative integer")
        if self.cycle_rank > self.phase_count:
            raise CrossModalEvidenceError("cycle_rank cannot exceed phase_count")
        if self.jacobian_rank > self.phase_count:
            raise CrossModalEvidenceError("jacobian_rank cannot exceed phase_count")
        if self.fisher_rank > self.phase_count:
            raise CrossModalEvidenceError("fisher_rank cannot exceed phase_count")

    @property
    def fully_identifiable(self) -> bool:
        self.validate()
        return (
            self.jacobian_rank >= self.cycle_rank
            and self.fisher_rank >= self.cycle_rank
        )


@dataclass(frozen=True)
class CrossModalEvidenceReport:
    consistency_state: str
    source_attribution_admissible: bool
    phase_fully_identifiable: bool
    known_sectors_independently_constrained: bool
    circular_fit_present: bool
    residual_resolved: bool
    chi_square: float
    residual_dof: int
    max_abs_normalized_residual: float
    packet_sha256: str


def _canonical_json(value) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _validate_covariance(covariance, size: int) -> np.ndarray:
    sigma = np.asarray(covariance, dtype=float)
    if sigma.shape != (size, size):
        raise CrossModalEvidenceError(
            "covariance must be square with dimension equal to channel count"
        )
    if not np.all(np.isfinite(sigma)):
        raise CrossModalEvidenceError("covariance must be finite")
    if not np.allclose(sigma, sigma.T, rtol=0.0, atol=1e-12):
        raise CrossModalEvidenceError("covariance must be symmetric")
    try:
        np.linalg.cholesky(sigma)
    except np.linalg.LinAlgError as exc:
        raise CrossModalEvidenceError("covariance must be positive definite") from exc
    return sigma


def covariance_chi_square(
    residuals: Sequence[float],
    covariance,
) -> float:
    r = np.asarray(residuals, dtype=float)
    if r.ndim != 1 or r.size == 0 or not np.all(np.isfinite(r)):
        raise CrossModalEvidenceError("residuals must be a finite non-empty vector")
    sigma = _validate_covariance(covariance, int(r.size))
    solved = np.linalg.solve(sigma, r)
    return float(r @ solved)


def build_cross_modal_report(
    channels: Iterable[ResidualChannel],
    *,
    phase_identifiability: PhaseIdentifiability,
    covariance=None,
    per_channel_sigma_threshold: float = 3.0,
    residual_resolution_sigma: float = 1.0,
    required_source_bindings_admitted: bool = False,
) -> CrossModalEvidenceReport:
    rows = tuple(channels)
    if not rows:
        raise CrossModalEvidenceError("at least one residual channel is required")

    phase_identifiability.validate()
    threshold = _positive(
        "per_channel_sigma_threshold", per_channel_sigma_threshold
    )
    resolution = _positive("residual_resolution_sigma", residual_resolution_sigma)

    for row in rows:
        row.validate()

    residuals = np.asarray([row.residual for row in rows], dtype=float)
    normalized = np.asarray(
        [row.normalized_residual for row in rows],
        dtype=float,
    )

    if covariance is None:
        chi_square = float(np.sum(normalized**2))
    else:
        chi_square = covariance_chi_square(residuals, covariance)

    max_abs = float(np.max(np.abs(normalized)))
    model_consistent = bool(max_abs <= threshold)

    known_independent = all(row.independently_constrained for row in rows)
    circular_fit = any(row.circular_fit for row in rows)
    phase_ok = phase_identifiability.fully_identifiable

    # "Resolved" means the surviving cross-modal residual is measurably non-zero.
    # This is not a source identification.
    residual_resolved = bool(max_abs >= resolution)

    if not phase_ok or not known_independent or circular_fit:
        state = "UNDERDETERMINED"
    elif model_consistent:
        state = "CONSISTENT"
    else:
        state = "INCONSISTENT"

    source_admissible = bool(
        state != "INCONSISTENT"
        and phase_ok
        and known_independent
        and not circular_fit
        and residual_resolved
        and required_source_bindings_admitted
    )

    packet_without_hash = {
        "schema": SCHEMA,
        "channels": [
            {
                "name": row.name,
                "observed": float(row.observed),
                "predicted": float(row.predicted),
                "sigma": float(row.sigma),
                "residual": float(row.residual),
                "normalized_residual": float(row.normalized_residual),
                "independently_constrained": bool(row.independently_constrained),
                "circular_fit": bool(row.circular_fit),
                "provenance": asdict(row.provenance),
            }
            for row in rows
        ],
        "phase_identifiability": {
            **asdict(phase_identifiability),
            "fully_identifiable": phase_ok,
        },
        "consistency": {
            "state": state,
            "chi_square": chi_square,
            "residual_dof": len(rows),
            "max_abs_normalized_residual": max_abs,
            "per_channel_sigma_threshold": threshold,
            "residual_resolution_sigma": resolution,
        },
        "source_attribution": {
            "admissible": source_admissible,
            "known_sectors_independently_constrained": known_independent,
            "circular_fit_present": circular_fit,
            "residual_resolved": residual_resolved,
            "required_source_bindings_admitted": bool(
                required_source_bindings_admitted
            ),
            "physical_source_selected": False,
        },
    }
    packet_sha = hashlib.sha256(_canonical_json(packet_without_hash)).hexdigest()

    return CrossModalEvidenceReport(
        consistency_state=state,
        source_attribution_admissible=source_admissible,
        phase_fully_identifiable=phase_ok,
        known_sectors_independently_constrained=known_independent,
        circular_fit_present=circular_fit,
        residual_resolved=residual_resolved,
        chi_square=chi_square,
        residual_dof=len(rows),
        max_abs_normalized_residual=max_abs,
        packet_sha256=packet_sha,
    )


def packet_payload(
    channels: Iterable[ResidualChannel],
    *,
    phase_identifiability: PhaseIdentifiability,
    covariance=None,
    per_channel_sigma_threshold: float = 3.0,
    residual_resolution_sigma: float = 1.0,
    required_source_bindings_admitted: bool = False,
) -> dict:
    rows = tuple(channels)
    report = build_cross_modal_report(
        rows,
        phase_identifiability=phase_identifiability,
        covariance=covariance,
        per_channel_sigma_threshold=per_channel_sigma_threshold,
        residual_resolution_sigma=residual_resolution_sigma,
        required_source_bindings_admitted=required_source_bindings_admitted,
    )

    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_ONLY",
        "consistency_state": report.consistency_state,
        "source_attribution_admissible": report.source_attribution_admissible,
        "physical_source_selected": False,
        "phase_identifiability": {
            **asdict(phase_identifiability),
            "fully_identifiable": report.phase_fully_identifiable,
        },
        "channels": [
            {
                "name": row.name,
                "observed": float(row.observed),
                "predicted": float(row.predicted),
                "sigma": float(row.sigma),
                "residual": float(row.residual),
                "normalized_residual": float(row.normalized_residual),
                "independently_constrained": bool(row.independently_constrained),
                "circular_fit": bool(row.circular_fit),
                "provenance": asdict(row.provenance),
            }
            for row in rows
        ],
        "consistency": {
            "chi_square": report.chi_square,
            "residual_dof": report.residual_dof,
            "max_abs_normalized_residual": report.max_abs_normalized_residual,
        },
        "source_attribution": {
            "known_sectors_independently_constrained":
                report.known_sectors_independently_constrained,
            "circular_fit_present": report.circular_fit_present,
            "residual_resolved": report.residual_resolved,
            "required_source_bindings_admitted":
                bool(required_source_bindings_admitted),
            "admissible": report.source_attribution_admissible,
        },
        "packet_sha256": report.packet_sha256,
    }
