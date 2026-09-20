from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence, Any

import numpy as np

SCHEMA = "GREMLIN_COGNITIVE_ACTION_PRINCIPLE_V0_1"


class CognitiveActionError(ValueError):
    pass


def _finite_scalar(value: float, name: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise CognitiveActionError(f"{name} must be finite") from exc
    if not math.isfinite(out):
        raise CognitiveActionError(f"{name} must be finite")
    return out


def _vector(value: Sequence[float] | np.ndarray, name: str, n: int | None = None) -> np.ndarray:
    out = np.asarray(value, dtype=float).reshape(-1)
    if not np.isfinite(out).all():
        raise CognitiveActionError(f"{name} must contain only finite values")
    if n is not None and out.size != n:
        raise CognitiveActionError(f"{name} must have length {n}")
    return out.copy()


def _matrix(value: Sequence[Sequence[float]] | np.ndarray, name: str, n: int | None = None) -> np.ndarray:
    out = np.asarray(value, dtype=float)
    if out.ndim != 2 or out.shape[0] != out.shape[1]:
        raise CognitiveActionError(f"{name} must be square")
    if n is not None and out.shape != (n, n):
        raise CognitiveActionError(f"{name} must have shape {(n, n)}")
    if not np.isfinite(out).all():
        raise CognitiveActionError(f"{name} must contain only finite values")
    return out.copy()


def _symmetric(value, name: str, n: int | None = None, tol: float = 1e-10) -> np.ndarray:
    out = _matrix(value, name, n)
    if not np.allclose(out, out.T, atol=tol, rtol=0.0):
        raise CognitiveActionError(f"{name} must be symmetric")
    return out


def _antisymmetric(value, name: str, n: int | None = None, tol: float = 1e-10) -> np.ndarray:
    out = _matrix(value, name, n)
    if not np.allclose(out, -out.T, atol=tol, rtol=0.0):
        raise CognitiveActionError(f"{name} must be antisymmetric")
    return out


def _positive_definite(value, name: str, n: int | None = None, tol: float = 1e-12) -> np.ndarray:
    out = _symmetric(value, name, n)
    if float(np.min(np.linalg.eigvalsh(out))) <= tol:
        raise CognitiveActionError(f"{name} must be positive definite")
    return out


def _positive_semidefinite(value, name: str, n: int | None = None, tol: float = 1e-12) -> np.ndarray:
    out = _symmetric(value, name, n)
    if float(np.min(np.linalg.eigvalsh(out))) < -tol:
        raise CognitiveActionError(f"{name} must be positive semidefinite")
    return out


@dataclass(frozen=True)
class QuadraticCognitiveAction:
    metric: np.ndarray
    connection_curvature: np.ndarray
    stiffness: np.ndarray
    damping: np.ndarray

    @property
    def dimension(self) -> int:
        return int(self.metric.shape[0])


def quadratic_action_model(
    metric,
    connection_curvature,
    stiffness,
    damping=None,
) -> QuadraticCognitiveAction:
    m = _positive_definite(metric, "metric")
    n = m.shape[0]
    g = _antisymmetric(connection_curvature, "connection_curvature", n)
    k = _symmetric(stiffness, "stiffness", n)
    d = np.zeros((n, n), dtype=float) if damping is None else _positive_semidefinite(damping, "damping", n)
    return QuadraticCognitiveAction(m, g, k, d)


def v012_collective_to_action(matrices: Any, *, damping=None) -> QuadraticCognitiveAction:
    try:
        mass = matrices.mass
        gyroscopic = matrices.gyroscopic
        stiffness = matrices.stiffness
    except AttributeError as exc:
        raise CognitiveActionError("matrices must expose mass, gyroscopic and stiffness") from exc
    return quadratic_action_model(mass, gyroscopic, stiffness, damping)


def quadratic_lagrangian(
    model: QuadraticCognitiveAction,
    state,
    velocity,
    *,
    potential_force=None,
    constraint_values=None,
    multipliers=None,
) -> float:
    n = model.dimension
    q = _vector(state, "state", n)
    v = _vector(velocity, "velocity", n)
    f = np.zeros(n, dtype=float) if potential_force is None else _vector(potential_force, "potential_force", n)
    kinetic = 0.5 * float(v @ model.metric @ v)
    connection = 0.5 * float(v @ model.connection_curvature @ q)
    potential = 0.5 * float(q @ model.stiffness @ q) - float(f @ q)
    out = kinetic + connection - potential
    if (constraint_values is None) != (multipliers is None):
        raise CognitiveActionError("constraint_values and multipliers must be supplied together")
    if constraint_values is not None:
        c = _vector(constraint_values, "constraint_values")
        lam = _vector(multipliers, "multipliers", c.size)
        out += float(lam @ c)
    return float(out)


def quadratic_energy(
    model: QuadraticCognitiveAction,
    state,
    velocity,
    *,
    potential_force=None,
) -> float:
    n = model.dimension
    q = _vector(state, "state", n)
    v = _vector(velocity, "velocity", n)
    f = np.zeros(n, dtype=float) if potential_force is None else _vector(potential_force, "potential_force", n)
    kinetic = 0.5 * float(v @ model.metric @ v)
    potential = 0.5 * float(q @ model.stiffness @ q) - float(f @ q)
    return kinetic + potential


def rayleigh_dissipation(model: QuadraticCognitiveAction, velocity) -> float:
    v = _vector(velocity, "velocity", model.dimension)
    return 0.5 * float(v @ model.damping @ v)


def euler_lagrange_residual(
    model: QuadraticCognitiveAction,
    state,
    velocity,
    acceleration,
    *,
    potential_force=None,
    external_force=None,
    constraint_jacobian=None,
    multipliers=None,
) -> np.ndarray:
    n = model.dimension
    q = _vector(state, "state", n)
    v = _vector(velocity, "velocity", n)
    a = _vector(acceleration, "acceleration", n)
    fpot = np.zeros(n) if potential_force is None else _vector(potential_force, "potential_force", n)
    qext = np.zeros(n) if external_force is None else _vector(external_force, "external_force", n)
    residual = model.metric @ a + model.connection_curvature @ v + model.stiffness @ q + model.damping @ v - fpot - qext
    if (constraint_jacobian is None) != (multipliers is None):
        raise CognitiveActionError("constraint_jacobian and multipliers must be supplied together")
    if constraint_jacobian is not None:
        j = np.asarray(constraint_jacobian, dtype=float)
        if j.ndim != 2 or j.shape[1] != n or not np.isfinite(j).all():
            raise CognitiveActionError(f"constraint_jacobian must have shape (m, {n})")
        lam = _vector(multipliers, "multipliers", j.shape[0])
        residual = residual - j.T @ lam
    return np.asarray(residual, dtype=float)


def energy_balance_rate(
    model: QuadraticCognitiveAction,
    velocity,
    *,
    external_force=None,
) -> float:
    v = _vector(velocity, "velocity", model.dimension)
    qext = np.zeros(model.dimension) if external_force is None else _vector(external_force, "external_force", model.dimension)
    return float(v @ qext - v @ model.damping @ v)


def trapezoidal_action(times, lagrangian_values) -> float:
    t = _vector(times, "times")
    l = _vector(lagrangian_values, "lagrangian_values", t.size)
    if t.size < 2:
        raise CognitiveActionError("at least two time samples are required")
    dt = np.diff(t)
    if np.any(dt <= 0.0):
        raise CognitiveActionError("times must be strictly increasing")
    return float(np.sum(0.5 * (l[:-1] + l[1:]) * dt))


def hybrid_action(continuous_action: float, jump_terms: Iterable[float] = ()) -> float:
    total = _finite_scalar(continuous_action, "continuous_action")
    for i, value in enumerate(jump_terms):
        total += _finite_scalar(value, f"jump_terms[{i}]")
    return total


def permission_projector(value, *, tolerance: float = 1e-10) -> np.ndarray:
    tol = _finite_scalar(tolerance, "tolerance")
    if tol <= 0.0:
        raise CognitiveActionError("tolerance must be positive")
    p = _symmetric(value, "permission_projector", tol=tol)
    if not np.allclose(p @ p, p, atol=tol, rtol=0.0):
        raise CognitiveActionError("permission_projector must be idempotent")
    return p


def project_velocity(projector, velocity) -> np.ndarray:
    p = permission_projector(projector)
    v = _vector(velocity, "velocity", p.shape[0])
    return p @ v


def permission_tangent_residual(projector, velocity) -> np.ndarray:
    p = permission_projector(projector)
    v = _vector(velocity, "velocity", p.shape[0])
    return (np.eye(p.shape[0]) - p) @ v


def holonomic_tangent_residual(constraint_jacobian, velocity) -> np.ndarray:
    v = _vector(velocity, "velocity")
    j = np.asarray(constraint_jacobian, dtype=float)
    if j.ndim != 2 or j.shape[1] != v.size or not np.isfinite(j).all():
        raise CognitiveActionError(f"constraint_jacobian must have shape (m, {v.size})")
    return j @ v


def _phase_couplings(value, n: int, tol: float = 1e-10) -> np.ndarray:
    k = _symmetric(value, "couplings", n, tol)
    if not np.allclose(np.diag(k), 0.0, atol=tol, rtol=0.0):
        raise CognitiveActionError("couplings diagonal must be zero")
    return k


def phase_potential(phases, couplings) -> float:
    theta = _vector(phases, "phases")
    k = _phase_couplings(couplings, theta.size)
    delta = theta[:, None] - theta[None, :]
    return -0.5 * float(np.sum(k * np.cos(delta)))


def phase_force(phases, couplings) -> np.ndarray:
    theta = _vector(phases, "phases")
    k = _phase_couplings(couplings, theta.size)
    delta = theta[:, None] - theta[None, :]
    return -np.sum(k * np.sin(delta), axis=1)


def inertial_phase_residual(
    phases,
    phase_velocity,
    phase_acceleration,
    *,
    inertia,
    damping,
    couplings,
    drive=None,
) -> np.ndarray:
    theta = _vector(phases, "phases")
    n = theta.size
    omega = _vector(phase_velocity, "phase_velocity", n)
    alpha = _vector(phase_acceleration, "phase_acceleration", n)
    inert = _vector(inertia, "inertia", n)
    damp = _vector(damping, "damping", n)
    if np.any(inert <= 0.0):
        raise CognitiveActionError("inertia entries must be positive")
    if np.any(damp < 0.0):
        raise CognitiveActionError("damping entries must be non-negative")
    drv = np.zeros(n) if drive is None else _vector(drive, "drive", n)
    force = phase_force(theta, couplings)
    return inert * alpha + damp * omega - drv - force


def overdamped_phase_velocity(phases, *, damping, couplings, drive=None) -> np.ndarray:
    theta = _vector(phases, "phases")
    n = theta.size
    damp = _vector(damping, "damping", n)
    if np.any(damp <= 0.0):
        raise CognitiveActionError("overdamped damping entries must be positive")
    drv = np.zeros(n) if drive is None else _vector(drive, "drive", n)
    return (drv + phase_force(theta, couplings)) / damp
