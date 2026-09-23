from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
import cmath
import json
import math
from typing import Mapping, Sequence

SCHEMA = "GREMLIN_HOLOGRAPHIC_ORBITAL_MEMORY_V0_1"
VERSION = "0.1.0"
DIM = 36
ROWS = 6
COLS = 6
TWO_PI = 2.0 * math.pi
SQRT3 = math.sqrt(3.0)

AUTHORITY = {
    "ledger_mutation": False,
    "canon_allowed": False,
    "execution_authority": False,
    "derived_index_only": True,
    "rebuildable_from_ledger": True,
}


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _digest(value: object, *, person: bytes) -> str:
    return blake2b(_canonical(value).encode("utf-8"), digest_size=32, person=person[:16]).hexdigest()


def normalize_phase(value: float) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise ValueError("phase must be finite")
    return x % TWO_PI


def validate_cell(values: Sequence[float]) -> tuple[float, ...]:
    if len(values) != DIM:
        raise ValueError("holographic memory cell must contain exactly 36 phases")
    return tuple(normalize_phase(v) for v in values)


def reshape_cell(values: Sequence[float]) -> tuple[tuple[float, ...], ...]:
    cell = validate_cell(values)
    return tuple(tuple(cell[a * COLS + k] for k in range(COLS)) for a in range(ROWS))


def circular_delta(left: float, right: float) -> float:
    return math.atan2(math.sin(left - right), math.cos(left - right))


def phase_rms_distance(left: Sequence[float], right: Sequence[float]) -> float:
    a = validate_cell(left)
    b = validate_cell(right)
    return math.sqrt(sum(circular_delta(x, y) ** 2 for x, y in zip(a, b)) / DIM)


def moire_overlap(left: Sequence[float], right: Sequence[float]) -> float:
    """Normalized coherent overlap of two 36D phase memories in [0,1]."""
    a = validate_cell(left)
    b = validate_cell(right)
    z = sum(cmath.exp(1j * circular_delta(x, y)) for x, y in zip(a, b)) / DIM
    return abs(z)


def apply_phase_carrier(
    cell: Sequence[float],
    carrier_36d: Sequence[float],
    *,
    gain: float = 1.0,
) -> tuple[float, ...]:
    """Reversible PhaseNav/QHTRI-style phase transport for a derived cell.

    The carrier is explicit caller-owned runtime context. This function does
    not claim physical QHTRI execution and does not persist the transported cell.
    """
    base = validate_cell(cell)
    if len(carrier_36d) != DIM:
        raise ValueError("carrier_36d must contain exactly 36 finite values")
    carrier = tuple(float(x) for x in carrier_36d)
    if any(not math.isfinite(x) for x in carrier):
        raise ValueError("carrier_36d must contain exactly 36 finite values")
    g = float(gain)
    if not math.isfinite(g):
        raise ValueError("gain must be finite")
    return tuple(normalize_phase(p + g * c) for p, c in zip(base, carrier))


def _validated_weights(count: int, weights: Sequence[float] | None) -> tuple[float, ...]:
    if count < 1:
        raise ValueError("at least one memory cell is required")
    if weights is None:
        return tuple(1.0 for _ in range(count))
    if len(weights) != count:
        raise ValueError("weights length mismatch")
    out = tuple(float(w) for w in weights)
    if any((not math.isfinite(w)) or w < 0.0 for w in out):
        raise ValueError("weights must be finite and non-negative")
    if not any(w > 0.0 for w in out):
        raise ValueError("at least one weight must be positive")
    return out


@dataclass(frozen=True)
class HolographicProjection:
    phase_36d: tuple[float, ...]
    amplitude_36d: tuple[float, ...]
    global_coherence: float
    source_count: int
    projection_commitment: str
    authority: Mapping[str, bool]


@dataclass(frozen=True)
class HolographicAddress:
    orbit_index: int
    hex_q: int
    hex_r: int
    orientation_sector: int
    coherence: float

    @property
    def key(self) -> tuple[int, int, int]:
        return self.orbit_index, self.hex_q, self.hex_r


@dataclass(frozen=True)
class HolographicRetrieval:
    record_id: str
    score: float
    phase_distance: float
    address: HolographicAddress
    candidate_count: int
    total_records: int
    comparison_reduction: float
    rings_scanned: int
    full_scan_fallback: bool


def project_hologram(
    cells: Sequence[Sequence[float]],
    *,
    weights: Sequence[float] | None = None,
    relation_phases: Sequence[float] | None = None,
) -> HolographicProjection:
    """Interfere memory cells coordinate-wise without changing source records."""
    normalized = tuple(validate_cell(cell) for cell in cells)
    w = _validated_weights(len(normalized), weights)
    if relation_phases is None:
        rp = tuple(0.0 for _ in normalized)
    else:
        if len(relation_phases) != len(normalized):
            raise ValueError("relation_phases length mismatch")
        rp = tuple(normalize_phase(x) for x in relation_phases)

    total_weight = sum(w)
    phases: list[float] = []
    amplitudes: list[float] = []
    for j in range(DIM):
        z = sum(w_i * cmath.exp(1j * (cell[j] + rel)) for cell, w_i, rel in zip(normalized, w, rp))
        phases.append(normalize_phase(cmath.phase(z)) if abs(z) > 1e-15 else 0.0)
        amplitudes.append(abs(z) / total_weight)
    global_coherence = sum(amplitudes) / DIM
    body = {
        "schema": SCHEMA,
        "phase_36d": phases,
        "amplitude_36d": amplitudes,
        "global_coherence": global_coherence,
        "source_count": len(normalized),
        "weights": w,
        "relation_phases": rp,
    }
    return HolographicProjection(
        phase_36d=tuple(phases),
        amplitude_36d=tuple(amplitudes),
        global_coherence=global_coherence,
        source_count=len(normalized),
        projection_commitment="holo:" + _digest(body, person=b"GRMLN-HOLO-PROJ"),
        authority=dict(AUTHORITY),
    )


def kuramoto_potential(cells: Sequence[Sequence[float]], weights: Sequence[float] | None = None) -> float:
    normalized = tuple(validate_cell(cell) for cell in cells)
    w = _validated_weights(len(normalized), weights)
    total = 0.0
    for i in range(len(normalized)):
        for j in range(i + 1, len(normalized)):
            wij = w[i] * w[j]
            total -= wij * sum(
                math.cos(circular_delta(normalized[i][k], normalized[j][k]))
                for k in range(DIM)
            ) / DIM
    return total


def kuramoto_relax(
    cells: Sequence[Sequence[float]],
    *,
    weights: Sequence[float] | None = None,
    coupling: float = 1.0,
    dt: float = 0.05,
    steps: int = 1,
) -> tuple[tuple[float, ...], ...]:
    """Bounded overdamped Kuramoto relaxation over working-memory copies."""
    state = [list(validate_cell(cell)) for cell in cells]
    w = _validated_weights(len(state), weights)
    K = float(coupling)
    h = float(dt)
    n_steps = int(steps)
    if not math.isfinite(K) or K < 0.0:
        raise ValueError("coupling must be finite and non-negative")
    if not math.isfinite(h) or h <= 0.0 or h > 0.25:
        raise ValueError("dt must be finite in (0,0.25]")
    if n_steps < 0 or n_steps > 10000:
        raise ValueError("steps must be in [0,10000]")

    norm_w = sum(w)
    for _ in range(n_steps):
        previous = [row[:] for row in state]
        for i in range(len(state)):
            for k in range(DIM):
                force = sum(
                    w[j] * math.sin(previous[j][k] - previous[i][k])
                    for j in range(len(previous))
                    if j != i
                ) / norm_w
                state[i][k] = normalize_phase(previous[i][k] + h * K * force)
    return tuple(tuple(row) for row in state)


def _row_phasors(cell: Sequence[float]) -> tuple[complex, ...]:
    rows = reshape_cell(cell)
    return tuple(sum(cmath.exp(1j * p) for p in row) / COLS for row in rows)


def _global_coherence(cell: Sequence[float]) -> float:
    normalized = validate_cell(cell)
    return abs(sum(cmath.exp(1j * p) for p in normalized) / DIM)


def _hex_round(qf: float, rf: float) -> tuple[int, int]:
    xf = qf
    zf = rf
    yf = -xf - zf
    rx, ry, rz = round(xf), round(yf), round(zf)
    dx, dy, dz = abs(rx - xf), abs(ry - yf), abs(rz - zf)
    if dx > dy and dx > dz:
        rx = -ry - rz
    elif dy > dz:
        ry = -rx - rz
    else:
        rz = -rx - ry
    return int(rx), int(rz)


def holographic_address(
    cell: Sequence[float],
    *,
    orbit_count: int = 9,
    hex_scale: float = 16.0,
) -> HolographicAddress:
    """Map a 6x6 memory cell onto an orbital shell and hexagonal BEES patch."""
    n_orbits = int(orbit_count)
    scale = float(hex_scale)
    if n_orbits < 2:
        raise ValueError("orbit_count must be >= 2")
    if not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("hex_scale must be finite and positive")
    rows = _row_phasors(cell)
    h1 = sum(rows[a] * cmath.exp(1j * TWO_PI * a / ROWS) for a in range(ROWS)) / ROWS
    h2 = sum(rows[a] * cmath.exp(1j * 2.0 * TWO_PI * a / ROWS) for a in range(ROWS)) / ROWS
    z = h1 + 0.5 * h2
    x, y = scale * z.real, scale * z.imag
    qf = (2.0 / 3.0) * x
    rf = (-x / 3.0) + (SQRT3 * y / 3.0)
    q, r = _hex_round(qf, rf)
    coherence = _global_coherence(cell)
    orbit = min(n_orbits - 1, int(math.floor((1.0 - coherence) * n_orbits)))
    orientation = int(math.floor((normalize_phase(cmath.phase(h1)) / TWO_PI) * 6.0)) % 6
    return HolographicAddress(orbit, q, r, orientation, coherence)


def _hex_ring(q: int, r: int, radius: int) -> tuple[tuple[int, int], ...]:
    if radius < 0:
        raise ValueError("radius must be non-negative")
    if radius == 0:
        return ((q, r),)
    directions = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))
    cq = q + directions[4][0] * radius
    cr = r + directions[4][1] * radius
    out: list[tuple[int, int]] = []
    for direction in directions:
        for _ in range(radius):
            out.append((cq, cr))
            cq += direction[0]
            cr += direction[1]
    return tuple(out)


class HolographicOrbitalIndex:
    """Rebuildable orbital/hex prefilter over immutable 36D memory cells."""

    def __init__(self, *, orbit_count: int = 9, hex_scale: float = 16.0) -> None:
        self.orbit_count = int(orbit_count)
        self.hex_scale = float(hex_scale)
        if self.orbit_count < 2:
            raise ValueError("orbit_count must be >= 2")
        if not math.isfinite(self.hex_scale) or self.hex_scale <= 0.0:
            raise ValueError("hex_scale must be finite and positive")
        self._vectors: dict[str, tuple[float, ...]] = {}
        self._addresses: dict[str, HolographicAddress] = {}
        self._buckets: dict[tuple[int, int, int], list[str]] = {}

    def add(self, record_id: str, cell: Sequence[float]) -> HolographicAddress:
        rid = str(record_id).strip()
        if not rid:
            raise ValueError("record_id must be non-empty")
        if rid in self._vectors:
            raise RuntimeError("duplicate holographic record id")
        vector = validate_cell(cell)
        addr = holographic_address(vector, orbit_count=self.orbit_count, hex_scale=self.hex_scale)
        self._vectors[rid] = vector
        self._addresses[rid] = addr
        self._buckets.setdefault(addr.key, []).append(rid)
        return addr

    @classmethod
    def remap(
        cls,
        records: Mapping[str, Sequence[float]],
        *,
        orbit_count: int = 9,
        hex_scale: float = 16.0,
    ) -> "HolographicOrbitalIndex":
        index = cls(orbit_count=orbit_count, hex_scale=hex_scale)
        for record_id in sorted(records):
            index.add(record_id, records[record_id])
        return index

    @property
    def size(self) -> int:
        return len(self._vectors)

    def mapping_commitment(self) -> str:
        body = {
            "schema": SCHEMA,
            "orbit_count": self.orbit_count,
            "hex_scale": self.hex_scale,
            "mapping": [
                {
                    "record_id": rid,
                    "address": {
                        "orbit_index": self._addresses[rid].orbit_index,
                        "hex_q": self._addresses[rid].hex_q,
                        "hex_r": self._addresses[rid].hex_r,
                        "orientation_sector": self._addresses[rid].orientation_sector,
                    },
                }
                for rid in sorted(self._vectors)
            ],
        }
        return "map:" + _digest(body, person=b"GRMLN-HOLO-MAP")

    def query_candidates(
        self,
        query: Sequence[float],
        *,
        min_candidates: int = 12,
        max_hex_ring: int = 3,
        orbit_radius: int = 1,
    ) -> tuple[tuple[str, ...], HolographicAddress, int]:
        if self.size == 0:
            return (), holographic_address(
                query,
                orbit_count=self.orbit_count,
                hex_scale=self.hex_scale,
            ), 0
        target = holographic_address(
            query,
            orbit_count=self.orbit_count,
            hex_scale=self.hex_scale,
        )
        wanted = max(1, int(min_candidates))
        max_ring = max(0, int(max_hex_ring))
        o_radius = max(0, int(orbit_radius))
        seen: dict[str, None] = {}
        used_ring = 0
        for ring in range(max_ring + 1):
            used_ring = ring
            for orbit in range(
                max(0, target.orbit_index - o_radius),
                min(self.orbit_count - 1, target.orbit_index + o_radius) + 1,
            ):
                for q, r in _hex_ring(target.hex_q, target.hex_r, ring):
                    for rid in self._buckets.get((orbit, q, r), ()):
                        seen.setdefault(rid, None)
            if len(seen) >= wanted:
                break
        return tuple(seen), target, used_ring

    def retrieve(
        self,
        query: Sequence[float],
        *,
        min_candidates: int = 12,
        max_hex_ring: int = 3,
        orbit_radius: int = 1,
        full_scan_if_empty: bool = True,
    ) -> HolographicRetrieval:
        if self.size == 0:
            raise LookupError("cannot retrieve from empty holographic index")
        query_cell = validate_cell(query)
        candidates, target, rings = self.query_candidates(
            query_cell,
            min_candidates=min_candidates,
            max_hex_ring=max_hex_ring,
            orbit_radius=orbit_radius,
        )
        fallback = False
        if not candidates:
            if not full_scan_if_empty:
                raise LookupError("no candidates in requested orbital/hex neighborhood")
            candidates = tuple(sorted(self._vectors))
            fallback = True

        def key(rid: str) -> tuple[float, float, str]:
            vector = self._vectors[rid]
            return (
                -moire_overlap(query_cell, vector),
                phase_rms_distance(query_cell, vector),
                rid,
            )

        best = min(candidates, key=key)
        score = moire_overlap(query_cell, self._vectors[best])
        distance = phase_rms_distance(query_cell, self._vectors[best])
        count = len(candidates)
        return HolographicRetrieval(
            record_id=best,
            score=score,
            phase_distance=distance,
            address=target,
            candidate_count=count,
            total_records=self.size,
            comparison_reduction=(self.size / count) if count else math.inf,
            rings_scanned=rings,
            full_scan_fallback=fallback,
        )
