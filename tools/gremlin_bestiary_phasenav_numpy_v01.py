from __future__ import annotations

import math
from time import perf_counter
from typing import Sequence

try:
    import numpy as np
except ImportError as exc:  # fail loud: this backend is explicitly NumPy-backed
    raise RuntimeError(
        "GREMLIN PhaseNav NumPy backend requires numpy; no silent scalar fallback is allowed"
    ) from exc

from tools.gremlin_bestiary_phasenav_phase_gates_v01 import (
    DIM,
    TAU,
    PhaseGate36,
    PhaseGateError,
    PhaseState36,
    REALIZATION_MODE,
    SPECIES,
    torus_distance,
)

CONTRACT_ID = "GREMLIN_BESTIARY_PHASENAV_NUMPY_BATCH_V0_1"
BACKEND = "NUMPY_FLOAT64_BATCH"
NO_SILENT_SCALAR_FALLBACK = True


def _state_matrix(states: Sequence[PhaseState36]) -> "np.ndarray":
    if not states:
        raise PhaseGateError("at least one PhaseState36 is required")
    if any(not isinstance(s, PhaseState36) for s in states):
        raise PhaseGateError("all batch entries must be PhaseState36")
    matrix = np.asarray([s.theta for s in states], dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[1] != DIM:
        raise PhaseGateError(f"batch must have shape (N,{DIM})")
    if not np.isfinite(matrix).all():
        raise PhaseGateError("batch contains non-finite values")
    if np.any(matrix < 0.0) or np.any(matrix >= TAU):
        raise PhaseGateError("batch phase coordinates must lie in [0,2pi)")
    return matrix


def _target_row(gate: PhaseGate36, target: Sequence[float] | None) -> "np.ndarray":
    if target is None:
        raw = gate.phase_bias
    else:
        raw = PhaseState36(target).theta
    row = np.asarray(raw, dtype=np.float64)
    if row.shape != (DIM,) or not np.isfinite(row).all():
        raise PhaseGateError("target must be one finite 36D phase vector")
    return row


def _circular_delta_array(a: "np.ndarray", b: "np.ndarray") -> "np.ndarray":
    return np.mod(a - b + math.pi, TAU) - math.pi


def step_batch_vectorized(
    gate: PhaseGate36,
    states: Sequence[PhaseState36],
    target: Sequence[float] | None = None,
) -> tuple[PhaseState36, ...]:
    """Execute the v0.1 PhaseNav gate as one batch-array kernel.

    This is a computational vector backend. It does not claim physical analog
    realization or guaranteed CPU SIMD; NumPy owns the low-level realization.
    """
    if not isinstance(gate, PhaseGate36):
        raise PhaseGateError("PhaseGate36 required")

    theta = _state_matrix(states)
    bias = _target_row(gate, target)[None, :]

    drive = gate.drive_gain * np.sin(_circular_delta_array(bias, theta))
    left = np.roll(theta, 1, axis=1)
    right = np.roll(theta, -1, axis=1)
    coupling = 0.5 * gate.neighbor_coupling * (
        np.sin(_circular_delta_array(left, theta))
        + np.sin(_circular_delta_array(right, theta))
    )
    harmonic = gate.harmonic_gain * np.sin(
        2.0 * _circular_delta_array(bias, theta)
    )

    out = np.mod(theta + gate.dt * (drive + coupling + harmonic), TAU)
    if out.shape != theta.shape or not np.isfinite(out).all():
        raise PhaseGateError("vectorized phase gate produced invalid output")

    return tuple(PhaseState36(row.tolist()) for row in out)


def max_torus_error(
    left: Sequence[PhaseState36], right: Sequence[PhaseState36]
) -> float:
    if len(left) != len(right):
        raise PhaseGateError("state batches differ in length")
    if not left:
        return 0.0
    return max(torus_distance(a.theta, b.theta) for a, b in zip(left, right))


def scalar_vector_equivalence(
    species: str,
    states: Sequence[PhaseState36],
    *,
    target: Sequence[float] | None = None,
) -> dict[str, object]:
    gate = PhaseGate36(species)
    scalar = tuple(gate.step(s, target=target) for s in states)
    vector = step_batch_vectorized(gate, states, target=target)
    err = max_torus_error(scalar, vector)
    return {
        "schema": "GREMLIN_BESTIARY_PHASENAV_NUMPY_EQUIVALENCE_V0_1",
        "contract_id": CONTRACT_ID,
        "species": gate.species,
        "realization_mode": REALIZATION_MODE[gate.species],
        "backend": BACKEND,
        "batch_size": len(states),
        "max_torus_error": err,
        "external_effects": False,
        "physical_analog_claim": False,
        "silent_scalar_fallback": False,
    }


def analog_kernel_continuity_probe(
    species: str,
    state: PhaseState36,
    *,
    epsilon: float = 1e-8,
) -> dict[str, object]:
    """Numerically probe continuity on the torus, not hardware analogity."""
    eps = float(epsilon)
    if not math.isfinite(eps) or eps <= 0.0 or eps >= 1e-2:
        raise PhaseGateError("epsilon must be finite in (0,1e-2)")

    perturbed = list(state.theta)
    perturbed[0] = (perturbed[0] + eps) % TAU
    other = PhaseState36(perturbed)
    gate = PhaseGate36(species)
    a = gate.step(state)
    b = gate.step(other)
    input_distance = torus_distance(state.theta, other.theta)
    output_distance = torus_distance(a.theta, b.theta)
    local_gain = output_distance / input_distance
    return {
        "schema": "GREMLIN_BESTIARY_PHASE_CONTINUITY_PROBE_V0_1",
        "contract_id": CONTRACT_ID,
        "species": gate.species,
        "input_distance": input_distance,
        "output_distance": output_distance,
        "local_gain": local_gain,
        "finite": math.isfinite(local_gain),
        "phase_kernel_continuity_candidate": math.isfinite(local_gain)
        and local_gain < 100.0,
        "physical_analog_claim": False,
    }


def benchmark_scalar_vs_vector(
    species: str,
    states: Sequence[PhaseState36],
    *,
    repeats: int = 7,
) -> dict[str, object]:
    if repeats < 1 or repeats > 1000:
        raise PhaseGateError("repeats must be in [1,1000]")
    gate = PhaseGate36(species)
    frozen = tuple(states)
    if not frozen:
        raise PhaseGateError("benchmark requires at least one state")

    scalar_times: list[float] = []
    vector_times: list[float] = []
    max_error = 0.0

    for _ in range(repeats):
        t0 = perf_counter()
        scalar = tuple(gate.step(s) for s in frozen)
        scalar_times.append(perf_counter() - t0)

        t0 = perf_counter()
        vector = step_batch_vectorized(gate, frozen)
        vector_times.append(perf_counter() - t0)

        max_error = max(max_error, max_torus_error(scalar, vector))

    scalar_times.sort()
    vector_times.sort()
    scalar_median = scalar_times[len(scalar_times) // 2]
    vector_median = vector_times[len(vector_times) // 2]
    return {
        "schema": "GREMLIN_BESTIARY_PHASENAV_NUMPY_BENCHMARK_V0_1",
        "contract_id": CONTRACT_ID,
        "species": gate.species,
        "batch_size": len(frozen),
        "repeats": repeats,
        "scalar_median_s": scalar_median,
        "vector_median_s": vector_median,
        "speedup": scalar_median / vector_median if vector_median > 0.0 else math.inf,
        "max_torus_error": max_error,
        "backend": BACKEND,
        "silent_scalar_fallback": False,
        "physical_analog_claim": False,
        "external_effects": False,
    }


def backend_manifest() -> dict[str, object]:
    return {
        "schema": "GREMLIN_BESTIARY_PHASENAV_NUMPY_BACKEND_V0_1",
        "contract_id": CONTRACT_ID,
        "backend": BACKEND,
        "dimension": DIM,
        "space": "T^36",
        "species": list(SPECIES),
        "realization_mode": dict(REALIZATION_MODE),
        "silent_scalar_fallback": False,
        "physical_analog_claim": False,
        "external_effects": False,
    }
