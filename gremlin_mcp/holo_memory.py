from __future__ import annotations

from dataclasses import dataclass, asdict
import cmath
import hashlib
import json
import math
from typing import Any, Iterable, Mapping, Sequence

DIM = 36
ROWS = 6
COLS = 6
SCHEMA = "GREMLIN_HOLO_MEMORY_V0_1"
TWO_PI = 2.0 * math.pi
AUTHORITY = {
    "source_of_truth": False,
    "ledger_mutation": False,
    "canon_allowed": False,
    "derived_index_only": True,
}


class HoloMemoryError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _commit(value: Any, *, person: bytes = b"GRMLN-HOLO-V01") -> str:
    return hashlib.blake2b(
        _canonical(value),
        digest_size=32,
        person=person[:16],
    ).hexdigest()


def _phase_packet(
    packet: Mapping[str, Any],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    phase = packet.get("phase36")
    amp = packet.get("amplitude36")
    if not isinstance(phase, Sequence) or len(phase) != DIM:
        raise HoloMemoryError("packet requires exact phase36")
    if not isinstance(amp, Sequence) or len(amp) != DIM:
        raise HoloMemoryError("packet requires exact amplitude36")
    p = tuple(float(x) for x in phase)
    a = tuple(float(x) for x in amp)
    if not all(math.isfinite(x) for x in p + a):
        raise HoloMemoryError("phase/amplitude must be finite")
    if any(x < 0.0 for x in a):
        raise HoloMemoryError("amplitudes must be non-negative")
    return p, a


def circular_delta(a: float, b: float) -> float:
    return (float(a) - float(b) + math.pi) % TWO_PI - math.pi


def weighted_phase_coherence(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> float:
    lp, la = _phase_packet(left)
    rp, ra = _phase_packet(right)
    weights = [math.sqrt(x * y) for x, y in zip(la, ra)]
    den = sum(weights)
    if den <= 1e-15:
        return 0.0
    z = sum(
        w * cmath.exp(1j * circular_delta(x, y))
        for x, y, w in zip(lp, rp, weights)
    ) / den
    return float(abs(z))


def moire_cross_term(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> float:
    """Normalized coherent cross term in [-1, 1]. Evidence, never truth."""
    lp, la = _phase_packet(left)
    rp, ra = _phase_packet(right)
    num = sum(
        2.0 * math.sqrt(xa * ya) * math.cos(circular_delta(xp, yp))
        for xp, yp, xa, ya in zip(lp, rp, la, ra)
    )
    den = sum(xa + ya for xa, ya in zip(la, ra))
    if den <= 1e-15:
        return 0.0
    return max(-1.0, min(1.0, float(num / den)))


def _row_complex(packet: Mapping[str, Any], row: int) -> complex:
    phase, amp = _phase_packet(packet)
    start = row * COLS
    return (
        sum(
            amp[i] * cmath.exp(1j * phase[i])
            for i in range(start, start + COLS)
        )
        / COLS
    )


def hex_embedding(
    packet: Mapping[str, Any],
    *,
    scale: float = 9.0,
) -> tuple[int, int]:
    """Map six 6D projection rows to one deterministic axial hex coordinate."""
    if not math.isfinite(scale) or scale <= 0:
        raise HoloMemoryError("scale must be finite and positive")
    z = 0j
    for row in range(ROWS):
        z += _row_complex(packet, row) * cmath.exp(
            1j * row * math.pi / 3.0
        )
    x = scale * z.real
    y = scale * z.imag
    rf = 2.0 * y / math.sqrt(3.0)
    qf = x - rf / 2.0
    return cube_round_axial(qf, rf)


def cube_round_axial(qf: float, rf: float) -> tuple[int, int]:
    xf, zf = qf, rf
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


def hex_distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    aq, ar = a
    bq, br = b
    ax, az, ay = aq, ar, -aq - ar
    bx, bz, by = bq, br, -bq - br
    return max(abs(ax - bx), abs(ay - by), abs(az - bz))


def hex_neighborhood(
    center: tuple[int, int],
    radius: int,
) -> tuple[tuple[int, int], ...]:
    if radius < 0:
        raise HoloMemoryError("radius must be >= 0")
    cq, cr = center
    out: list[tuple[int, int]] = []
    for dq in range(-radius, radius + 1):
        lo = max(-radius, -dq - radius)
        hi = min(radius, -dq + radius)
        for dr in range(lo, hi + 1):
            out.append((cq + dq, cr + dr))
    return tuple(out)


@dataclass(frozen=True)
class HoloCell:
    memory_id: str
    ledger_record_id: str
    phase36: tuple[float, ...]
    amplitude36: tuple[float, ...]
    hex_q: int
    hex_r: int
    priority_orbit_index: int
    semantic_orbit_id: str | None
    priority: float
    semantic_commitment: str
    source_commitment: str


class HoloMemoryIndex:
    """Regenerable holographic/hexagonal index over authoritative memory."""

    def __init__(self, *, hex_scale: float = 9.0) -> None:
        self.hex_scale = float(hex_scale)
        self._cells: dict[str, HoloCell] = {}
        self._packets: dict[str, dict[str, Any]] = {}
        self._hex: dict[tuple[int, int], list[str]] = {}

    @property
    def count(self) -> int:
        return len(self._cells)

    def add(
        self,
        *,
        memory_id: str,
        ledger_record_id: str,
        packet: Mapping[str, Any],
        priority_orbit_index: int = 0,
        semantic_orbit_id: str | None = None,
        priority: float = 0.5,
    ) -> HoloCell:
        mid = str(memory_id).strip()
        rid = str(ledger_record_id).strip()
        if not mid or not rid:
            raise HoloMemoryError(
                "memory_id and ledger_record_id are required"
            )
        if mid in self._cells:
            raise HoloMemoryError("duplicate memory_id")
        p, a = _phase_packet(packet)
        if priority_orbit_index < 0:
            raise HoloMemoryError("priority_orbit_index must be >=0")
        semantic_id = (
            None
            if semantic_orbit_id is None
            else str(semantic_orbit_id).strip()
        )
        if semantic_orbit_id is not None and not semantic_id:
            raise HoloMemoryError(
                "semantic_orbit_id must be non-empty when supplied"
            )
        pr = float(priority)
        if not math.isfinite(pr) or not 0.0 <= pr <= 1.0:
            raise HoloMemoryError("priority must be in [0,1]")
        coord = hex_embedding(packet, scale=self.hex_scale)
        sem = str(
            packet.get("semantic_commitment")
            or _commit(
                {"phase36": p, "amplitude36": a},
                person=b"GRMLN-HOLO-SEM",
            )
        )
        src = _commit(
            {
                "memory_id": mid,
                "ledger_record_id": rid,
                "semantic_commitment": sem,
                "phase36": p,
                "amplitude36": a,
                "priority_orbit_index": int(priority_orbit_index),
                "semantic_orbit_id": semantic_id,
            },
            person=b"GRMLN-HOLO-SRC",
        )
        cell = HoloCell(
            mid,
            rid,
            p,
            a,
            coord[0],
            coord[1],
            int(priority_orbit_index),
            semantic_id,
            pr,
            sem,
            src,
        )
        self._cells[mid] = cell
        self._packets[mid] = {
            **dict(packet),
            "phase36": list(p),
            "amplitude36": list(a),
        }
        self._hex.setdefault(coord, []).append(mid)
        self._hex[coord].sort()
        return cell

    def rebuild(self, rows: Iterable[Mapping[str, Any]]) -> str:
        self._cells.clear()
        self._packets.clear()
        self._hex.clear()
        normalized = []
        for row in rows:
            cell = self.add(
                memory_id=str(row["memory_id"]),
                ledger_record_id=str(row["ledger_record_id"]),
                packet=row["packet"],
                priority_orbit_index=int(
                    row.get(
                        "priority_orbit_index",
                        row.get("orbit_index", 0),
                    )
                ),
                semantic_orbit_id=row.get("semantic_orbit_id"),
                priority=float(row.get("priority", 0.5)),
            )
            normalized.append(asdict(cell))
        return _commit(normalized, person=b"GRMLN-HOLO-RBLD")

    def snapshot_commitment(self) -> str:
        return _commit(
            [asdict(self._cells[k]) for k in sorted(self._cells)],
            person=b"GRMLN-HOLO-IDX",
        )

    def shortlist(
        self,
        cue: Mapping[str, Any],
        *,
        patch_radius: int = 1,
        semantic_orbit_ids: Sequence[str] | None = None,
        priority_orbit_radius: int | None = None,
        priority_orbit_index: int = 0,
    ) -> tuple[str, ...]:
        center = hex_embedding(cue, scale=self.hex_scale)
        ids: list[str] = []
        for coord in hex_neighborhood(center, patch_radius):
            ids.extend(self._hex.get(coord, ()))
        if semantic_orbit_ids is not None:
            allowed = {
                str(x).strip()
                for x in semantic_orbit_ids
                if str(x).strip()
            }
            if not allowed:
                raise HoloMemoryError(
                    "semantic_orbit_ids must contain a non-empty id"
                )
            ids = [
                mid
                for mid in ids
                if self._cells[mid].semantic_orbit_id in allowed
            ]
        if priority_orbit_radius is not None:
            ids = [
                mid
                for mid in ids
                if abs(
                    self._cells[mid].priority_orbit_index
                    - int(priority_orbit_index)
                )
                <= int(priority_orbit_radius)
            ]
        return tuple(dict.fromkeys(sorted(ids)))

    def retrieve(
        self,
        cue: Mapping[str, Any],
        *,
        patch_radius: int = 1,
        semantic_orbit_ids: Sequence[str] | None = None,
        priority_orbit_radius: int | None = None,
        priority_orbit_index: int = 0,
        fallback_full: bool = True,
    ) -> dict[str, Any]:
        shortlist = list(
            self.shortlist(
                cue,
                patch_radius=patch_radius,
                semantic_orbit_ids=semantic_orbit_ids,
                priority_orbit_radius=priority_orbit_radius,
                priority_orbit_index=priority_orbit_index,
            )
        )
        fallback_used = False
        if not shortlist and fallback_full:
            shortlist = sorted(self._cells)
            fallback_used = True
        ranked = []
        for mid in shortlist:
            phase_score = weighted_phase_coherence(
                cue, self._packets[mid]
            )
            moire = moire_cross_term(cue, self._packets[mid])
            score = 0.75 * phase_score + 0.25 * ((moire + 1.0) / 2.0)
            ranked.append(
                {
                    "memory_id": mid,
                    "score": float(score),
                    "phase_coherence36": phase_score,
                    "moire_cross_term": moire,
                }
            )
        ranked.sort(key=lambda x: (-x["score"], x["memory_id"]))
        return {
            "schema": "GREMLIN_HOLO_MEMORY_RETRIEVAL_V0_1",
            "status": "MATCH" if ranked else "NO_CANDIDATE",
            "picked": ranked[0]["memory_id"] if ranked else None,
            "ranked": ranked,
            "evaluated": len(ranked),
            "total": len(self._cells),
            "fraction_evaluated": (
                0.0 if not self._cells else len(ranked) / len(self._cells)
            ),
            "fallback_full": fallback_used,
            "authority": dict(AUTHORITY),
        }

    def retrieve_reference(
        self,
        cue: Mapping[str, Any],
        *,
        patch_radius: int = 1,
        semantic_orbit_ids: Sequence[str] | None = None,
        priority_orbit_radius: int | None = None,
        priority_orbit_index: int = 0,
        fallback_full: bool = True,
    ) -> dict[str, Any]:
        """Shortlist holographically, then preserve GREMLIN semantic scorer."""
        from .relational_memory_encoder import memory_similarity

        shortlist = list(
            self.shortlist(
                cue,
                patch_radius=patch_radius,
                semantic_orbit_ids=semantic_orbit_ids,
                priority_orbit_radius=priority_orbit_radius,
                priority_orbit_index=priority_orbit_index,
            )
        )
        fallback_used = False
        if not shortlist and fallback_full:
            shortlist = sorted(self._cells)
            fallback_used = True
        ranked = []
        for mid in shortlist:
            sim = memory_similarity(cue, self._packets[mid])
            ranked.append({"memory_id": mid, **sim})
        ranked.sort(
            key=lambda x: (-float(x["score"]), x["memory_id"])
        )
        return {
            "schema": "GREMLIN_HOLO_MEMORY_REFERENCE_RETRIEVAL_V0_1",
            "status": "MATCH" if ranked else "NO_CANDIDATE",
            "picked": ranked[0]["memory_id"] if ranked else None,
            "ranked": ranked,
            "evaluated": len(ranked),
            "total": len(self._cells),
            "fraction_evaluated": (
                0.0 if not self._cells else len(ranked) / len(self._cells)
            ),
            "fallback_full": fallback_used,
            "scorer": "GREMLIN_RELATIONAL_MEMORY_SIMILARITY_V0_1",
            "authority": dict(AUTHORITY),
        }

    def patch_moire(
        self,
        memory_ids: Sequence[str],
    ) -> dict[str, Any]:
        ids = [str(x) for x in memory_ids]
        if len(ids) < 2:
            raise HoloMemoryError(
                "patch_moire needs at least two memories"
            )
        if any(mid not in self._cells for mid in ids):
            raise HoloMemoryError("unknown memory id")
        pairs = []
        for i, left in enumerate(ids):
            for right in ids[i + 1 :]:
                value = moire_cross_term(
                    self._packets[left], self._packets[right]
                )
                pairs.append(
                    {
                        "left": left,
                        "right": right,
                        "cross_term": value,
                    }
                )
        mean = sum(p["cross_term"] for p in pairs) / len(pairs)
        return {
            "schema": "GREMLIN_HOLO_MEMORY_MOIRE_PATCH_V0_1",
            "status": "CANDIDATE_ONLY",
            "memory_ids": ids,
            "mean_cross_term": float(mean),
            "pairs": pairs,
            "ledger_mutation": False,
            "authority": dict(AUTHORITY),
        }


def remap_hive_record(
    record: Any,
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a non-mutating Holo row from HiveRecord-like input."""
    def get(name: str, default: Any = None) -> Any:
        if isinstance(record, Mapping):
            return record.get(name, default)
        return getattr(record, name, default)

    coordinate = get("coordinate")
    if isinstance(coordinate, Mapping):
        orbit_index = int(coordinate.get("orbit_index", 0))
    else:
        orbit_index = (
            int(getattr(coordinate, "orbit_index", 0))
            if coordinate is not None
            else 0
        )
    rid = str(get("record_id", "")).strip()
    subject = str(get("subject_id", "")).strip()
    if not rid or not subject:
        raise HoloMemoryError(
            "Hive record requires record_id and subject_id"
        )
    return {
        "memory_id": subject,
        "ledger_record_id": rid,
        "packet": dict(packet),
        "priority_orbit_index": orbit_index,
        "semantic_orbit_id": None,
        "priority": float(get("priority", 0.5)),
    }


def kuramoto_step(
    phases: Sequence[float],
    edges: Sequence[tuple[int, int, float]],
    *,
    dt: float = 0.05,
    damping: float = 1.0,
) -> tuple[float, ...]:
    n = len(phases)
    if n == 0:
        return ()
    p = [float(x) for x in phases]
    if not all(math.isfinite(x) for x in p):
        raise HoloMemoryError("phases must be finite")
    if (
        not math.isfinite(dt)
        or dt <= 0
        or not math.isfinite(damping)
        or damping <= 0
    ):
        raise HoloMemoryError("dt/damping must be positive finite")
    force = [0.0] * n
    for i, j, k in edges:
        if not (0 <= i < n and 0 <= j < n) or i == j:
            raise HoloMemoryError("invalid edge")
        kk = float(k)
        if not math.isfinite(kk):
            raise HoloMemoryError("coupling must be finite")
        s = kk * math.sin(p[j] - p[i])
        force[i] += s
        force[j] -= s
    return tuple(
        (p[i] + dt * force[i] / damping) % TWO_PI
        for i in range(n)
    )


def order_parameter(phases: Sequence[float]) -> float:
    if not phases:
        return 0.0
    z = sum(cmath.exp(1j * float(x)) for x in phases) / len(phases)
    return float(abs(z))


def settle_hex_patch(
    phases: Sequence[float],
    coords: Sequence[tuple[int, int]],
    *,
    coupling: float = 0.5,
    dt: float = 0.05,
    steps: int = 64,
) -> dict[str, Any]:
    if len(phases) != len(coords):
        raise HoloMemoryError("phases/coords length mismatch")
    edges = []
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            if hex_distance(coords[i], coords[j]) == 1:
                edges.append((i, j, float(coupling)))
    state = tuple(float(x) % TWO_PI for x in phases)
    before = order_parameter(state)
    for _ in range(int(steps)):
        state = kuramoto_step(state, edges, dt=dt)
    after = order_parameter(state)
    return {
        "schema": "GREMLIN_HOLO_MEMORY_KURAMOTO_PATCH_V0_1",
        "before": before,
        "after": after,
        "phases": state,
        "edge_count": len(edges),
        "authority": dict(AUTHORITY),
    }
