from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import math
from typing import Sequence

import numpy as np

from tools.gremlin_bestiary_phasenav_phase_gates_v01 import (
    DIM,
    REALIZATION_MODE,
    SPECIES,
    TAU,
    PhaseGate36,
    PhaseGateError,
    PhaseState36,
    circular_delta,
)
from tools.gremlin_bestiary_phasenav_numpy_v01 import step_batch_vectorized

CONTRACT_ID = "GREMLIN_BESTIARY_PHASENAV_THREEWAY_V0_1"
SCHEMA = "GREMLIN_BESTIARY_PHASENAV_THREEWAY_SUITE_V0_1"

ANALOG_CORE_SPECIES = frozenset(
    name for name, mode in REALIZATION_MODE.items()
    if mode == "ANALOG_CORE_HYBRID_CONTROL"
)

HYBRID_SPECIES = frozenset(
    name for name, mode in REALIZATION_MODE.items()
    if mode == "HYBRID"
)

AUTHORITY_BOUNDARY_SPECIES = frozenset(
    name for name, mode in REALIZATION_MODE.items()
    if mode == "HYBRID_AUTHORITY_BOUNDARY"
)

if ANALOG_CORE_SPECIES | HYBRID_SPECIES | AUTHORITY_BOUNDARY_SPECIES != frozenset(SPECIES):
    raise RuntimeError("realization classes must partition the exact Bestiary")


def _matrix(states: Sequence[PhaseState36]) -> np.ndarray:
    if not states:
        raise PhaseGateError("at least one PhaseState36 is required")
    if any(not isinstance(s, PhaseState36) for s in states):
        raise PhaseGateError("all entries must be PhaseState36")
    out = np.asarray([s.theta for s in states], dtype=np.float64)
    if out.shape != (len(states), DIM) or not np.isfinite(out).all():
        raise PhaseGateError("invalid T^36 batch")
    if np.any(out < 0.0) or np.any(out >= TAU):
        raise PhaseGateError("phase coordinates must lie in [0,2pi)")
    return out


def _target(gate: PhaseGate36, target: Sequence[float] | None = None) -> np.ndarray:
    raw = gate.phase_bias if target is None else PhaseState36(target).theta
    out = np.asarray(raw, dtype=np.float64)
    if out.shape != (DIM,) or not np.isfinite(out).all():
        raise PhaseGateError("invalid target")
    return out


def _delta(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.mod(a - b + math.pi, TAU) - math.pi


def phase_field(
    gate: PhaseGate36,
    theta: np.ndarray,
    *,
    target: Sequence[float] | None = None,
) -> np.ndarray:
    """Continuous T^36 vector field whose forward-Euler step is PhaseGate36.step.

    This is a mathematical/numerical field definition.  It is not a physical
    analog-hardware witness.
    """
    if not isinstance(gate, PhaseGate36):
        raise PhaseGateError("PhaseGate36 required")
    state = np.asarray(theta, dtype=np.float64)
    if state.ndim != 2 or state.shape[1] != DIM or not np.isfinite(state).all():
        raise PhaseGateError(f"theta must have shape (N,{DIM})")
    bias = _target(gate, target)[None, :]

    drive = gate.drive_gain * np.sin(_delta(bias, state))
    left = np.roll(state, 1, axis=1)
    right = np.roll(state, -1, axis=1)
    coupling = 0.5 * gate.neighbor_coupling * (
        np.sin(_delta(left, state)) + np.sin(_delta(right, state))
    )
    harmonic = gate.harmonic_gain * np.sin(2.0 * _delta(bias, state))
    field = drive + coupling + harmonic
    if field.shape != state.shape or not np.isfinite(field).all():
        raise PhaseGateError("phase field produced non-finite output")
    return field


def _states(matrix: np.ndarray) -> tuple[PhaseState36, ...]:
    wrapped = np.mod(matrix, TAU)
    if not np.isfinite(wrapped).all():
        raise PhaseGateError("trajectory produced non-finite phase state")
    return tuple(PhaseState36(row.tolist()) for row in wrapped)


def rk4_continuous_batch(
    gate: PhaseGate36,
    states: Sequence[PhaseState36],
    *,
    horizon: float = 1.6,
    substeps: int = 512,
    target: Sequence[float] | None = None,
) -> tuple[PhaseState36, ...]:
    horizon_f = float(horizon)
    if not math.isfinite(horizon_f) or horizon_f <= 0.0:
        raise PhaseGateError("horizon must be finite and positive")
    if isinstance(substeps, bool) or not isinstance(substeps, int) or not (4 <= substeps <= 100000):
        raise PhaseGateError("substeps must be an integer in [4,100000]")

    y = _matrix(states).copy()
    h = horizon_f / substeps
    for _ in range(substeps):
        k1 = phase_field(gate, y, target=target)
        k2 = phase_field(gate, np.mod(y + 0.5 * h * k1, TAU), target=target)
        k3 = phase_field(gate, np.mod(y + 0.5 * h * k2, TAU), target=target)
        k4 = phase_field(gate, np.mod(y + h * k3, TAU), target=target)
        y = np.mod(y + (h / 6.0) * (k1 + 2.0*k2 + 2.0*k3 + k4), TAU)
        if not np.isfinite(y).all():
            raise PhaseGateError("RK4 phase-flow diverged")
    return _states(y)


def scalar_euler_batch(
    gate: PhaseGate36,
    states: Sequence[PhaseState36],
    *,
    horizon: float = 1.6,
    steps: int = 64,
    target: Sequence[float] | None = None,
) -> tuple[PhaseState36, ...]:
    horizon_f = float(horizon)
    if not math.isfinite(horizon_f) or horizon_f <= 0.0:
        raise PhaseGateError("horizon must be finite and positive")
    if isinstance(steps, bool) or not isinstance(steps, int) or not (1 <= steps <= 100000):
        raise PhaseGateError("steps must be an integer in [1,100000]")
    local_gate = replace(gate, dt=horizon_f / steps)
    current = tuple(states)
    if not current:
        raise PhaseGateError("at least one PhaseState36 is required")
    for _ in range(steps):
        current = tuple(local_gate.step(s, target=target) for s in current)
    return current


def vector_euler_batch(
    gate: PhaseGate36,
    states: Sequence[PhaseState36],
    *,
    horizon: float = 1.6,
    steps: int = 64,
    target: Sequence[float] | None = None,
) -> tuple[PhaseState36, ...]:
    horizon_f = float(horizon)
    if not math.isfinite(horizon_f) or horizon_f <= 0.0:
        raise PhaseGateError("horizon must be finite and positive")
    if isinstance(steps, bool) or not isinstance(steps, int) or not (1 <= steps <= 100000):
        raise PhaseGateError("steps must be an integer in [1,100000]")
    local_gate = replace(gate, dt=horizon_f / steps)
    current = tuple(states)
    if not current:
        raise PhaseGateError("at least one PhaseState36 is required")
    for _ in range(steps):
        current = step_batch_vectorized(local_gate, current, target=target)
    return current


def max_coordinate_error(
    left: Sequence[PhaseState36],
    right: Sequence[PhaseState36],
) -> float:
    if len(left) != len(right):
        raise PhaseGateError("trajectory batches differ in length")
    if not left:
        return 0.0
    return max(
        abs(circular_delta(a, b))
        for sl, sr in zip(left, right)
        for a, b in zip(sl.theta, sr.theta)
    )


def max_rms_torus_error(
    left: Sequence[PhaseState36],
    right: Sequence[PhaseState36],
) -> float:
    if len(left) != len(right):
        raise PhaseGateError("trajectory batches differ in length")
    if not left:
        return 0.0
    return max(
        math.sqrt(
            sum(circular_delta(a, b)**2 for a, b in zip(sl.theta, sr.theta)) / DIM
        )
        for sl, sr in zip(left, right)
    )


def frozen_workload(n: int = 48) -> tuple[PhaseState36, ...]:
    if isinstance(n, bool) or not isinstance(n, int) or n < 4:
        raise PhaseGateError("frozen workload requires at least four states")
    out = []
    for j in range(n):
        theta = [
            (
                0.119 * (i + 1)
                + 0.083 * (j + 1)
                + 0.021 * math.sin((i + 1) * (j + 3) / 11.0)
                + 0.017 * math.cos((i + 5) * (j + 1) / 23.0)
            ) % TAU
            for i in range(DIM)
        ]
        out.append(PhaseState36(theta))
    return tuple(out)


def workload_sha256(states: Sequence[PhaseState36]) -> str:
    payload = [[float(x) for x in s.theta] for s in states]
    raw = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def classify_species(
    species: str,
    *,
    scalar_vector_error: float,
    fine_continuous_error: float,
    convergence_ratio: float,
    scalar_vector_tolerance: float,
    continuous_error_tolerance: float,
    convergence_ratio_max: float,
) -> str:
    name = str(species).strip().upper()
    if name not in SPECIES:
        raise PhaseGateError(f"unknown species: {species!r}")
    numerical_pass = (
        scalar_vector_error <= scalar_vector_tolerance
        and fine_continuous_error <= continuous_error_tolerance
        and convergence_ratio <= convergence_ratio_max
    )
    if not numerical_pass:
        return "FAIL_BLOCKED"
    if name in ANALOG_CORE_SPECIES:
        return "ANALOG_CORE_NUMERICAL_PASS_HYBRID_CONTROL"
    if name in AUTHORITY_BOUNDARY_SPECIES:
        return "HYBRID_AUTHORITY_BOUNDARY_PASS"
    return "HYBRID_PASS"


def evaluate_species(
    species: str,
    states: Sequence[PhaseState36],
    *,
    horizon: float = 1.6,
    coarse_steps: int = 8,
    fine_steps: int = 64,
    rk4_substeps: int = 512,
    scalar_vector_tolerance: float = 1e-12,
    continuous_error_tolerance: float = 0.01,
    convergence_ratio_max: float = 0.50,
) -> dict[str, object]:
    name = str(species).strip().upper()
    gate = PhaseGate36(name)
    reference = rk4_continuous_batch(
        gate, states, horizon=horizon, substeps=rk4_substeps
    )

    scalar_coarse = scalar_euler_batch(
        gate, states, horizon=horizon, steps=coarse_steps
    )
    scalar_fine = scalar_euler_batch(
        gate, states, horizon=horizon, steps=fine_steps
    )
    vector_fine = vector_euler_batch(
        gate, states, horizon=horizon, steps=fine_steps
    )

    scalar_vector_error = max_coordinate_error(scalar_fine, vector_fine)
    coarse_error = max_rms_torus_error(scalar_coarse, reference)
    fine_error = max_rms_torus_error(scalar_fine, reference)
    ratio = 0.0 if coarse_error <= 1e-15 else fine_error / coarse_error

    classification = classify_species(
        name,
        scalar_vector_error=scalar_vector_error,
        fine_continuous_error=fine_error,
        convergence_ratio=ratio,
        scalar_vector_tolerance=scalar_vector_tolerance,
        continuous_error_tolerance=continuous_error_tolerance,
        convergence_ratio_max=convergence_ratio_max,
    )
    return {
        "schema": "GREMLIN_BESTIARY_PHASENAV_THREEWAY_SPECIES_V0_1",
        "contract_id": CONTRACT_ID,
        "species": name,
        "declared_realization_mode": REALIZATION_MODE[name],
        "classification": classification,
        "horizon": horizon,
        "coarse_steps": coarse_steps,
        "fine_steps": fine_steps,
        "rk4_substeps": rk4_substeps,
        "scalar_vector_max_coordinate_error": scalar_vector_error,
        "coarse_euler_vs_continuous_max_rms_error": coarse_error,
        "fine_euler_vs_continuous_max_rms_error": fine_error,
        "fine_to_coarse_error_ratio": ratio,
        "gates": {
            "scalar_vector_equivalent": scalar_vector_error <= scalar_vector_tolerance,
            "continuous_error_within_tolerance": fine_error <= continuous_error_tolerance,
            "euler_converges_toward_continuous": ratio <= convergence_ratio_max,
        },
        "thresholds": {
            "scalar_vector_tolerance": scalar_vector_tolerance,
            "continuous_error_tolerance": continuous_error_tolerance,
            "convergence_ratio_max": convergence_ratio_max,
        },
        "physical_analog_claim": False,
        "hardware_analog_witness": False,
        "external_effects": False,
        "canon_allowed": False,
    }


def run_threeway_suite(
    *,
    batch_size: int = 48,
    horizon: float = 1.6,
    coarse_steps: int = 8,
    fine_steps: int = 64,
    rk4_substeps: int = 512,
) -> dict[str, object]:
    states = frozen_workload(batch_size)
    results = [
        evaluate_species(
            name,
            states,
            horizon=horizon,
            coarse_steps=coarse_steps,
            fine_steps=fine_steps,
            rk4_substeps=rk4_substeps,
        )
        for name in SPECIES
    ]
    failures = [r["species"] for r in results if r["classification"] == "FAIL_BLOCKED"]
    classifications = {str(r["species"]): str(r["classification"]) for r in results}
    analog_pass = sorted(
        name for name, cls in classifications.items()
        if cls == "ANALOG_CORE_NUMERICAL_PASS_HYBRID_CONTROL"
    )
    hybrid_pass = sorted(
        name for name, cls in classifications.items()
        if cls in {"HYBRID_PASS", "HYBRID_AUTHORITY_BOUNDARY_PASS"}
    )

    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "workload": {
            "batch_size": batch_size,
            "dimension": DIM,
            "space": "T^36",
            "sha256": workload_sha256(states),
            "construction": "deterministic_trigonometric_fixture",
        },
        "configuration": {
            "horizon": horizon,
            "coarse_steps": coarse_steps,
            "fine_steps": fine_steps,
            "rk4_substeps": rk4_substeps,
            "continuous_reference": "RK4_NUMERICAL_REFERENCE_OF_EXACT_PHASE_FIELD",
            "digital_reference": "FORWARD_EULER_PHASEGATE36",
            "vector_reference": "NUMPY_BATCH_FORWARD_EULER_SAME_FIELD",
        },
        "results": results,
        "summary": {
            "species_count": len(results),
            "all_species_pass": not failures,
            "failures": failures,
            "analog_core_numerical_pass_count": len(analog_pass),
            "analog_core_numerical_pass_species": analog_pass,
            "hybrid_pass_count": len(hybrid_pass),
            "hybrid_pass_species": hybrid_pass,
            "fully_analog_physical_pass_count": 0,
            "physical_analog_claim": False,
            "hardware_analog_witness": False,
            "external_effects": False,
            "canon_allowed": False,
            "max_scalar_vector_error": max(float(r["scalar_vector_max_coordinate_error"]) for r in results),
            "max_fine_continuous_error": max(float(r["fine_euler_vs_continuous_max_rms_error"]) for r in results),
            "max_convergence_ratio": max(float(r["fine_to_coarse_error_ratio"]) for r in results),
        },
    }
