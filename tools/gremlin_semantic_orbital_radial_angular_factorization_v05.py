from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence

KAPPA = math.log(2.0) / (24.0 * math.pi)
L3, L4, L5 = 7, 2, 5
ALPHA_M = 1.0 / ((L3 * L4) ** 2 - L3**2 - L4 * L5 + L4**2 * KAPPA)
L_RATIO = L4 / L3
DELTA7 = 2.0 * math.pi / 7.0
THEORY_MASS_STEP = KAPPA * ALPHA_M


class RadialAngularAuditError(ValueError):
    pass


def _finite(x: float, name: str) -> float:
    y = float(x)
    if not math.isfinite(y):
        raise RadialAngularAuditError(f"{name} must be finite")
    return y


def wrap_pi(x: float) -> float:
    return (_finite(x, "phase") + math.pi) % (2.0 * math.pi) - math.pi


def semantic_mass_unrounded(phase_index: int, order_parameter_R: float) -> float:
    if isinstance(phase_index, bool) or not isinstance(phase_index, int) or phase_index < 1:
        raise RadialAngularAuditError("phase_index must be a positive integer")
    R = _finite(order_parameter_R, "order_parameter_R")
    if R < 0.0:
        raise RadialAngularAuditError("order_parameter_R must be non-negative")
    return KAPPA * (1.0 + ALPHA_M * phase_index) + L_RATIO * R


def constant_R_step() -> float:
    return THEORY_MASS_STEP


def pearson(x: Sequence[float], y: Sequence[float]) -> float:
    if len(x) != len(y) or len(x) < 2:
        raise RadialAngularAuditError("equal sequences with at least two values required")
    xs = [_finite(v, "x") for v in x]
    ys = [_finite(v, "y") for v in y]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    dx = [v - mx for v in xs]
    dy = [v - my for v in ys]
    den = math.sqrt(sum(v * v for v in dx) * sum(v * v for v in dy))
    if den == 0.0:
        raise RadialAngularAuditError("correlation undefined for constant input")
    return sum(a * b for a, b in zip(dx, dy)) / den


def linear_residuals(y: Sequence[float], x: Sequence[float]) -> tuple[float, float, tuple[float, ...]]:
    if len(x) != len(y) or len(x) < 2:
        raise RadialAngularAuditError("equal sequences with at least two values required")
    xs = [_finite(v, "x") for v in x]
    ys = [_finite(v, "y") for v in y]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    denom = sum((v - mx) ** 2 for v in xs)
    if denom == 0.0:
        raise RadialAngularAuditError("linear fit requires nonconstant x")
    slope = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / denom
    intercept = my - slope * mx
    residuals = tuple(b - (intercept + slope * a) for a, b in zip(xs, ys))
    return intercept, slope, residuals


def partial_c7_coefficient(masses: Sequence[float], phase_indices: Sequence[float], c7_indices: Sequence[float]) -> float:
    _, _, mass_resid = linear_residuals(masses, phase_indices)
    _, _, c7_resid = linear_residuals(c7_indices, phase_indices)
    denom = sum(v * v for v in c7_resid)
    if denom == 0.0:
        raise RadialAngularAuditError("C7 residual has zero variance")
    return sum(a * b for a, b in zip(mass_resid, c7_resid)) / denom


def classify_c7(reference: Sequence[float], vector: Sequence[float]) -> tuple[int, float]:
    if len(reference) != 36 or len(vector) != 36:
        raise RadialAngularAuditError("C7 classifier requires two 36D phase vectors")
    deltas = [wrap_pi(float(b) - float(a)) for a, b in zip(reference, vector)]
    shift = math.atan2(sum(math.sin(v) for v in deltas), sum(math.cos(v) for v in deltas))
    candidates = [(abs(wrap_pi(shift + n * DELTA7)), n) for n in range(7)]
    _, n = min(candidates)
    residual = wrap_pi(shift + n * DELTA7)
    return n, residual


@dataclass(frozen=True)
class FactorizationSummary:
    mass_vs_phase_index_corr: float
    mass_vs_c7_corr: float
    c7_coefficient_after_phase_index: float


def summarize(masses: Sequence[float], phase_indices: Sequence[float], c7_indices: Sequence[float]) -> FactorizationSummary:
    return FactorizationSummary(
        mass_vs_phase_index_corr=pearson(masses, phase_indices),
        mass_vs_c7_corr=pearson(masses, c7_indices),
        c7_coefficient_after_phase_index=partial_c7_coefficient(masses, phase_indices, c7_indices),
    )
