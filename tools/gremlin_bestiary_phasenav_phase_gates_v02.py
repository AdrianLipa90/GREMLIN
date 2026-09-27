from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import cmath
import hashlib
import json
import math
from numbers import Real
from typing import Any, Mapping, Sequence

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore[assignment]

from gremlin_mcp.role_registry import BESTIARY_ROLE_NAMES

DIM = 36
ORTHOPLEX_DIM = 10
TAU = 2.0 * math.pi
SCHEMA = "GREMLIN_BESTIARY_PHASE_MEMORY_CARRIER_V0_2"
VERSION = "0.2.0"

REALIZATION_MODE = {
    "HUMMINGBIRD": "HYBRID",
    "OCTOPUS": "HYBRID",
    "SPIDER": "ANALOG_CORE_HYBRID_CONTROL",
    "RAVEN": "ANALOG_CORE_HYBRID_CONTROL",
    "HOUND": "ANALOG_CORE_HYBRID_CONTROL",
    "MOLE": "ANALOG_CORE_HYBRID_CONTROL",
    "OWL": "HYBRID",
    "ANT": "HYBRID",
    "MANTIS": "HYBRID",
    "FOX": "ANALOG_CORE_HYBRID_CONTROL",
    "BEAVER": "ANALOG_CORE_HYBRID_CONTROL",
    "BAT": "ANALOG_CORE_HYBRID_CONTROL",
    "CANARY": "ANALOG_CORE_HYBRID_CONTROL",
    "SERPENT": "ANALOG_CORE_HYBRID_CONTROL",
    "CHAMELEON": "HYBRID",
    "ELEPHANT": "HYBRID_MEMORY",
    "BEES": "HYBRID_COHERENCE",
    "BELZEBUB": "HYBRID",
    "FERRET": "HYBRID_AUTHORITY_BOUNDARY",
    "GREMLIN": "HYBRID",
}

# 36 pairwise-coprime modular channels. All moduli exceed the bounded
# role-address diameter, so the finite signature is injective on this role set.
ARPL_MODULI = (
    23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71,
    73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131,
    137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193,
)

# Candidate functional duals. This is an engineering binding, not a claim that
# the animal names possess an intrinsic mathematical polarity.
DUAL_PAIRS = (
    ("HUMMINGBIRD", "GREMLIN"),
    ("OCTOPUS", "FERRET"),
    ("SPIDER", "ELEPHANT"),
    ("RAVEN", "BEES"),
    ("HOUND", "BELZEBUB"),
    ("MOLE", "OWL"),
    ("ANT", "MANTIS"),
    ("FOX", "BEAVER"),
    ("BAT", "CANARY"),
    ("SERPENT", "CHAMELEON"),
)

SPECIES = tuple(sorted(BESTIARY_ROLE_NAMES))
if len(SPECIES) != 20:
    raise RuntimeError("v0.2 requires the canonical 20-role Bestiary")

_ROLE_BINDING: dict[str, tuple[int, int, int]] = {}
for axis, (positive, negative) in enumerate(DUAL_PAIRS, start=1):
    _ROLE_BINDING[positive] = (axis, +1, +axis)
    _ROLE_BINDING[negative] = (axis, -1, -axis)
if set(_ROLE_BINDING) != set(SPECIES):
    raise RuntimeError("orthoplex binding must cover the exact Bestiary")


class PhaseCarrierError(ValueError):
    pass


# Compatibility alias for live-binding code paths.
PhaseGateError = PhaseCarrierError


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PhaseCarrierError("value must be finite canonical JSON") from exc


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _wrap(value: float) -> float:
    return float(value) % TAU


def circular_delta(a: float, b: float) -> float:
    return (float(a) - float(b) + math.pi) % TAU - math.pi


def _theta36(values: Sequence[float]) -> tuple[float, ...]:
    if (
        isinstance(values, (str, bytes, Mapping))
        or not isinstance(values, Sequence)
        or len(values) != DIM
    ):
        raise PhaseCarrierError(f"phase state must contain exactly {DIM} coordinates")
    out: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise PhaseCarrierError("phase coordinates must be real numbers")
        coordinate = float(value)
        if not math.isfinite(coordinate) or not 0.0 <= coordinate < TAU:
            raise PhaseCarrierError("phase coordinates must be finite and lie in [0,2pi)")
        out.append(coordinate)
    return tuple(out)


def role_binding(species: str) -> dict[str, int | str]:
    if not isinstance(species, str):
        raise PhaseCarrierError("Bestiary role must be a string")
    name = species.strip().upper()
    if name not in _ROLE_BINDING:
        raise PhaseCarrierError(f"unknown Bestiary role: {species!r}")
    axis, orientation, address = _ROLE_BINDING[name]
    partner = next(
        other
        for left, right in DUAL_PAIRS
        for current, other in ((left, right), (right, left))
        if current == name
    )
    return {
        "species": name,
        "axis": axis,
        "orientation": orientation,
        "address": address,
        "dual": partner,
    }


def orthoplex_vector(species: str) -> tuple[int, ...]:
    row = role_binding(species)
    out = [0] * ORTHOPLEX_DIM
    out[int(row["axis"]) - 1] = int(row["orientation"])
    return tuple(out)


def phase_signature(address: int) -> tuple[float, ...]:
    if isinstance(address, bool) or not isinstance(address, int):
        raise PhaseCarrierError("ARPL address must be an integer")
    return tuple(TAU * ((address % modulus) / modulus) for modulus in ARPL_MODULI)


@lru_cache(maxsize=None)
def role_phase_carrier(species: str) -> tuple[float, ...]:
    return phase_signature(int(role_binding(species)["address"]))


def relative_phase_signature(source: str, target: str) -> tuple[float, ...]:
    left = int(role_binding(source)["address"])
    right = int(role_binding(target)["address"])
    return phase_signature(right - left)


def phase_difference_law_residual(source: str, target: str) -> float:
    """Numerical rendering of ARPL OP-D029 on all 36 modular channels."""
    left = role_phase_carrier(source)
    right = role_phase_carrier(target)
    relative = relative_phase_signature(source, target)
    return max(
        abs(circular_delta(circular_delta(y, x), r))
        for x, y, r in zip(left, right, relative)
    )


def torus_distance(left: Sequence[float], right: Sequence[float]) -> float:
    a, b = _theta36(left), _theta36(right)
    return math.sqrt(sum(circular_delta(x, y) ** 2 for x, y in zip(a, b)))


def phase_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    a, b = _theta36(left), _theta36(right)
    z = sum(cmath.exp(1j * circular_delta(x, y)) for x, y in zip(a, b)) / DIM
    return 0.5 * (1.0 + z.real)


@dataclass(frozen=True)
class PhaseState36:
    theta: tuple[float, ...]

    def __init__(self, theta: Sequence[float]) -> None:
        object.__setattr__(self, "theta", _theta36(theta))

    @property
    def state_id(self) -> str:
        payload = {
            "schema": "GREMLIN_PHASENAV_T36_STATE_V0_2",
            "space": "T^36",
            "theta": list(self.theta),
        }
        return f"gremlin:t36:v02:sha256:{_sha(payload)}"


@dataclass(frozen=True)
class PhaseGate36:
    species: str
    phase_bias: tuple[float, ...]
    drive_gain: float = 0.30
    neighbor_coupling: float = 0.12
    harmonic_gain: float = 0.04
    dt: float = 0.20

    def __init__(
        self,
        species: str,
        phase_bias: Sequence[float] | None = None,
        drive_gain: float = 0.30,
        neighbor_coupling: float = 0.12,
        harmonic_gain: float = 0.04,
        dt: float = 0.20,
    ) -> None:
        if not isinstance(species, str):
            raise PhaseCarrierError("species must be a string")
        name = species.strip().upper()
        if name not in SPECIES:
            raise PhaseCarrierError(f"unknown species: {species!r}")
        raw_gains = (drive_gain, neighbor_coupling, harmonic_gain, dt)
        if any(isinstance(value, bool) or not isinstance(value, Real) for value in raw_gains):
            raise PhaseCarrierError("phase-gate coefficients must be real numbers")
        drive = float(drive_gain)
        coupling = float(neighbor_coupling)
        harmonic = float(harmonic_gain)
        step_dt = float(dt)
        gains = (drive, coupling, harmonic, step_dt)
        if not all(math.isfinite(value) for value in gains):
            raise PhaseCarrierError("phase-gate coefficients must be finite")
        if drive < 0 or coupling < 0 or harmonic < 0 or step_dt <= 0:
            raise PhaseCarrierError("invalid phase-gate coefficients")
        object.__setattr__(self, "species", name)
        object.__setattr__(
            self,
            "phase_bias",
            _theta36(role_phase_carrier(name) if phase_bias is None else phase_bias),
        )
        object.__setattr__(self, "drive_gain", drive)
        object.__setattr__(self, "neighbor_coupling", coupling)
        object.__setattr__(self, "harmonic_gain", harmonic)
        object.__setattr__(self, "dt", step_dt)

    def step(
        self,
        state: PhaseState36,
        target: Sequence[float] | None = None,
    ) -> PhaseState36:
        if not isinstance(state, PhaseState36):
            raise PhaseCarrierError("PhaseState36 required")
        bias = self.phase_bias if target is None else _theta36(target)
        theta = state.theta
        out: list[float] = []
        for i in range(DIM):
            drive = self.drive_gain * math.sin(circular_delta(bias[i], theta[i]))
            coupling = 0.5 * self.neighbor_coupling * (
                math.sin(circular_delta(theta[(i - 1) % DIM], theta[i]))
                + math.sin(circular_delta(theta[(i + 1) % DIM], theta[i]))
            )
            harmonic = self.harmonic_gain * math.sin(
                2.0 * circular_delta(bias[i], theta[i])
            )
            out.append(_wrap(theta[i] + self.dt * (drive + coupling + harmonic)))
        return PhaseState36(out)

    def step_batch_vectorized(
        self,
        states: Sequence[PhaseState36],
        target: Sequence[float] | None = None,
    ) -> tuple[PhaseState36, ...]:
        if np is None:
            raise PhaseCarrierError("NumPy is required for vectorized phase execution")
        if (
            isinstance(states, (str, bytes, Mapping))
            or not isinstance(states, Sequence)
        ):
            raise PhaseCarrierError("states must be a sequence of PhaseState36 values")
        if not states:
            return ()
        if not all(isinstance(state, PhaseState36) for state in states):
            raise PhaseCarrierError("PhaseState36 inputs required")
        theta = np.asarray([state.theta for state in states], dtype=np.float64)
        bias = np.asarray(
            self.phase_bias if target is None else _theta36(target),
            dtype=np.float64,
        )
        delta = (bias[None, :] - theta + math.pi) % TAU - math.pi
        left = (np.roll(theta, 1, axis=1) - theta + math.pi) % TAU - math.pi
        right = (np.roll(theta, -1, axis=1) - theta + math.pi) % TAU - math.pi
        out = np.mod(
            theta
            + self.dt
            * (
                self.drive_gain * np.sin(delta)
                + 0.5 * self.neighbor_coupling * (np.sin(left) + np.sin(right))
                + self.harmonic_gain * np.sin(2.0 * delta)
            ),
            TAU,
        )
        return tuple(PhaseState36(row.tolist()) for row in out)


def route_phase_order(
    phase36: Sequence[float],
    candidates: Sequence[str],
) -> tuple[list[str], dict[str, float]]:
    state = PhaseState36(phase36)
    if (
        isinstance(candidates, (str, bytes, Mapping))
        or not isinstance(candidates, Sequence)
    ):
        raise PhaseCarrierError("candidates must be a sequence of role strings")
    unique: list[str] = []
    for raw in candidates:
        if not isinstance(raw, str):
            raise PhaseCarrierError("route species must be strings")
        name = raw.strip().upper()
        if name not in SPECIES:
            raise PhaseCarrierError(f"unknown route species: {raw!r}")
        if name not in unique:
            unique.append(name)
    scored = [
        (phase_similarity(state.theta, role_phase_carrier(name)), name)
        for name in unique
    ]
    scored.sort(key=lambda row: (-row[0], row[1]))
    return [name for _, name in scored], {name: score for score, name in scored}


def octopus_route(
    state: PhaseState36,
    candidates: Sequence[str],
    *,
    max_species: int = 4,
    min_score: float = 0.15,
) -> dict[str, Any]:
    if not isinstance(state, PhaseState36):
        raise PhaseCarrierError("PhaseState36 required")
    if isinstance(max_species, bool) or not isinstance(max_species, int) or max_species < 1:
        raise PhaseCarrierError("max_species must be a positive integer")
    if isinstance(min_score, bool) or not isinstance(min_score, Real):
        raise PhaseCarrierError("min_score must be a real number")
    score_floor = float(min_score)
    if not math.isfinite(score_floor) or score_floor < 0.0:
        raise PhaseCarrierError("min_score must be finite and non-negative")
    ordered, scores = route_phase_order(state.theta, candidates)
    admitted = [
        name for name in ordered if scores[name] >= score_floor
    ][:max_species]
    return {
        "schema": "GREMLIN_PHASENAV_ROUTE_V0_2",
        "status": "PASS_CANDIDATE",
        "data": {
            "routes": [
                {"species": name, "score": scores[name]}
                for name in admitted
            ]
        },
        "canon_allowed": False,
        "external_effects": False,
    }


def binding_manifest() -> dict[str, Any]:
    rows = []
    for name in SPECIES:
        bind = role_binding(name)
        rows.append(
            {
                **bind,
                "orthoplex_vector": list(orthoplex_vector(name)),
                "phase36_sha256": _sha(list(role_phase_carrier(name))),
            }
        )
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "space": "T^36",
        "dimension": DIM,
        "role_geometry": "CANDIDATE_10_ORTHOPLEX",
        "orthoplex_dimension": ORTHOPLEX_DIM,
        "species_count": len(SPECIES),
        "species": rows,
        "phase_law_source": {
            "repository": "AdrianLipa90/On-Primes",
            "branch": "feat/arithmetic-relational-phase-law-v0.1",
            "artifact": "proofs/ARITHMETIC_RELATIONAL_PHASE_LAW_V0_1.md",
            "claims": ["OP-D029", "OP-D030", "OP-D031", "OP-D035"],
        },
        "moduli": list(ARPL_MODULI),
        "semantic_axis_assignment": False,
        "physical_analog_claim": False,
        "canon_allowed": False,
    }


def run_full_bestiary_reference_sweep(*, steps: int = 12) -> dict[str, Any]:
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
        raise PhaseCarrierError("steps must be a positive integer")
    base = PhaseState36([_wrap(0.10 + 0.017 * i) for i in range(DIM)])
    rows = []
    for name in SPECIES:
        gate = PhaseGate36(name, drive_gain=0.75, neighbor_coupling=0.02, harmonic_gain=0.08, dt=0.20)
        before = torus_distance(base.theta, gate.phase_bias)
        current = base
        for _ in range(steps):
            current = gate.step(current)
        after = torus_distance(current.theta, gate.phase_bias)
        rows.append(
            {
                "species": name,
                "before_distance": before,
                "after_distance": after,
                "distance_reduced": after < before,
                "carrier_sha256": _sha(list(gate.phase_bias)),
            }
        )

    law_residual = max(
        phase_difference_law_residual(left, right)
        for left in SPECIES
        for right in SPECIES
    )
    orthoplex_ok = all(
        tuple(-x for x in orthoplex_vector(left)) == orthoplex_vector(right)
        for left, right in DUAL_PAIRS
    )
    unique_carriers = len({row["carrier_sha256"] for row in rows}) == len(SPECIES)
    passed = (
        all(row["distance_reduced"] for row in rows)
        and unique_carriers
        and orthoplex_ok
        and law_residual <= 1e-12
    )
    return {
        "schema": "GREMLIN_BESTIARY_PHASE_MEMORY_REFERENCE_SWEEP_V0_2",
        "status": "PASS" if passed else "FAIL",
        "species_count": len(SPECIES),
        "all_species_distance_reduced": all(row["distance_reduced"] for row in rows),
        "all_species_carriers_unique": unique_carriers,
        "orthoplex_duals_exact": orthoplex_ok,
        "max_arpl_phase_law_residual": law_residual,
        "results": rows,
        "external_effects": False,
        "canon_allowed": False,
        "physical_analog_claim": False,
    }


def phase_gate_vectorization_manifest() -> dict[str, Any]:
    return {
        "schema": "GREMLIN_BESTIARY_PHASENAV_VECTOR_GATE_MANIFEST_V0_2",
        "dimension": DIM,
        "space": "T^36",
        "species_count": len(SPECIES),
        "numpy_available": np is not None,
        "vectorized_batch_realization": np is not None,
        "role_carrier_binding": "ARPL_36_CHANNEL_V0_2",
        "role_geometry": "CANDIDATE_10_ORTHOPLEX",
        "physical_analog_claim": False,
        "canon_allowed": False,
    }


__all__ = [
    "DIM",
    "ORTHOPLEX_DIM",
    "TAU",
    "ARPL_MODULI",
    "DUAL_PAIRS",
    "SPECIES",
    "REALIZATION_MODE",
    "PhaseCarrierError",
    "PhaseGateError",
    "PhaseState36",
    "PhaseGate36",
    "role_binding",
    "orthoplex_vector",
    "phase_signature",
    "role_phase_carrier",
    "relative_phase_signature",
    "phase_difference_law_residual",
    "torus_distance",
    "phase_similarity",
    "route_phase_order",
    "octopus_route",
    "binding_manifest",
    "run_full_bestiary_reference_sweep",
    "phase_gate_vectorization_manifest",
]
