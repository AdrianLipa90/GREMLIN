from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import blake2b
import json
import math
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any, Iterable, Mapping

HIVE_SCHEMA = "GREMLIN_ORBITAL_HIVE_MEMORY_V0_1"
TWO_PI = 2.0 * math.pi
LOCK_GATES = (
    "evidence_ready",
    "dependencies_closed",
    "contradiction_audited",
    "provenance_complete",
    "phase_coherent",
)
VALID_STATES = {"OPEN", "ALIGNING", "DISPUTED", "QUARANTINED", "LOCKED"}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _digest(value: Any, *, person: bytes) -> str:
    return blake2b(_canonical(value).encode("utf-8"), digest_size=32, person=person[:16]).hexdigest()


def priority_orbit(priority: float, *, orbit_count: int = 36) -> tuple[int, float]:
    """Map priority [0,1] to concentric orbit index/radius.

    Higher priority occupies an inner orbit. Radius is 1..orbit_count.
    """
    p = float(priority)
    if not math.isfinite(p) or not 0.0 <= p <= 1.0:
        raise ValueError("priority must be finite in [0,1]")
    n = int(orbit_count)
    if n < 2:
        raise ValueError("orbit_count must be >= 2")
    index = min(n - 1, int(math.floor((1.0 - p) * n)))
    return index, float(index + 1)


def semantic_angle(semantic_key: str) -> float:
    """Deterministic reference addressing; not a claim about semantic truth."""
    key = str(semantic_key).strip()
    if not key:
        raise ValueError("semantic_key must be non-empty")
    raw = blake2b(key.encode("utf-8"), digest_size=8, person=b"GRMLN-SEM-ANG").digest()
    fraction = int.from_bytes(raw, "big") / float(1 << 64)
    return TWO_PI * fraction


def normalize_phase(phase: float) -> float:
    value = float(phase)
    if not math.isfinite(value):
        raise ValueError("phase must be finite")
    return value % TWO_PI


@dataclass(frozen=True)
class HiveCoordinate:
    orbit_index: int
    radius: float
    semantic_angle: float
    relation_phase: float

    def __post_init__(self) -> None:
        if self.orbit_index < 0:
            raise ValueError("orbit_index must be non-negative")
        if not math.isfinite(self.radius) or self.radius <= 0:
            raise ValueError("radius must be finite and positive")
        for value, label in (
            (self.semantic_angle, "semantic_angle"),
            (self.relation_phase, "relation_phase"),
        ):
            if not math.isfinite(value) or not 0.0 <= value < TWO_PI:
                raise ValueError(f"{label} must be finite in [0,2pi)")


@dataclass(frozen=True)
class ClosureGates:
    evidence_ready: bool = False
    dependencies_closed: bool = False
    contradiction_audited: bool = False
    provenance_complete: bool = False
    phase_coherent: bool = False

    @property
    def closed(self) -> bool:
        return all(bool(getattr(self, name)) for name in LOCK_GATES)

    @property
    def missing(self) -> tuple[str, ...]:
        return tuple(name for name in LOCK_GATES if not bool(getattr(self, name)))


@dataclass(frozen=True)
class HiveRecord:
    record_id: str
    subject_id: str
    version: int
    payload_hash: str
    payload: Mapping[str, Any]
    priority: float
    coordinate: HiveCoordinate
    semantic_key: str
    state: str
    gates: ClosureGates
    provenance: tuple[str, ...]
    dependencies: tuple[str, ...]
    contradictions: tuple[str, ...]
    parent_record_id: str | None = None
    seal_receipt: str | None = None
    authority: str = "SHARED_COGNITION_ONLY"

    def __post_init__(self) -> None:
        if self.state not in VALID_STATES:
            raise ValueError("invalid hive state")
        if self.version < 1:
            raise ValueError("version must be positive")
        if self.authority != "SHARED_COGNITION_ONLY":
            raise ValueError("Hive Memory cannot grant mutation authority")


class OrbitalHiveMemory:
    """Append-only semantic/orbital/phase memory with fail-closed latching."""

    def __init__(self, *, orbit_count: int = 36) -> None:
        self.orbit_count = int(orbit_count)
        if self.orbit_count < 2:
            raise ValueError("orbit_count must be >= 2")
        self._records: dict[str, HiveRecord] = {}
        self._heads: dict[str, str] = {}

    def _record_id(self, body: Mapping[str, Any]) -> str:
        return "hive:" + _digest(body, person=b"GRMLN-HIVE-REC")

    def place(
        self,
        *,
        subject_id: str,
        payload: Mapping[str, Any],
        priority: float,
        semantic_key: str,
        relation_phase: float,
        provenance: Iterable[str] = (),
        dependencies: Iterable[str] = (),
        gates: ClosureGates | None = None,
    ) -> HiveRecord:
        subject = str(subject_id).strip()
        if not subject:
            raise ValueError("subject_id must be non-empty")
        payload_dict = dict(payload)
        p_hash = _digest(payload_dict, person=b"GRMLN-HIVE-PAY")
        index, radius = priority_orbit(priority, orbit_count=self.orbit_count)
        coordinate = HiveCoordinate(index, radius, semantic_angle(semantic_key), normalize_phase(relation_phase))
        prev_id = self._heads.get(subject)
        version = 1 if prev_id is None else self._records[prev_id].version + 1
        g = gates or ClosureGates()
        prov = tuple(sorted({str(x) for x in provenance if str(x)}))
        deps = tuple(sorted({str(x) for x in dependencies if str(x)}))
        body = {
            "schema": HIVE_SCHEMA,
            "subject_id": subject,
            "version": version,
            "payload_hash": p_hash,
            "priority": float(priority),
            "coordinate": asdict(coordinate),
            "semantic_key": str(semantic_key),
            "state": "ALIGNING" if any(asdict(g).values()) else "OPEN",
            "gates": asdict(g),
            "provenance": prov,
            "dependencies": deps,
            "contradictions": (),
            "parent_record_id": prev_id,
            "authority": "SHARED_COGNITION_ONLY",
        }
        rec = HiveRecord(
            record_id=self._record_id(body),
            payload=payload_dict,
            seal_receipt=None,
            **{k: v for k, v in body.items() if k not in {"schema", "coordinate", "gates"}},
            coordinate=coordinate,
            gates=g,
        )
        self._append(rec)
        return rec

    def _append(self, record: HiveRecord) -> None:
        if record.record_id in self._records:
            raise RuntimeError("duplicate hive record")
        self._records[record.record_id] = record
        self._heads[record.subject_id] = record.record_id

    def head(self, subject_id: str) -> HiveRecord:
        record_id = self._heads[str(subject_id)]
        return self._records[record_id]

    def update_gates(self, subject_id: str, **changes: bool) -> HiveRecord:
        unknown = set(changes) - set(LOCK_GATES)
        if unknown:
            raise KeyError(f"unknown closure gates: {sorted(unknown)}")
        current = self.head(subject_id)
        if current.state == "LOCKED":
            raise RuntimeError("locked records are immutable; fork the subject instead")
        g = replace(current.gates, **{k: bool(v) for k, v in changes.items()})
        return self.place(
            subject_id=current.subject_id,
            payload=current.payload,
            priority=current.priority,
            semantic_key=current.semantic_key,
            relation_phase=current.coordinate.relation_phase,
            provenance=current.provenance,
            dependencies=current.dependencies,
            gates=g,
        )

    def dispute(self, subject_id: str, contradiction_ref: str) -> HiveRecord:
        current = self.head(subject_id)
        ref = str(contradiction_ref).strip()
        if not ref:
            raise ValueError("contradiction_ref must be non-empty")
        gates = replace(current.gates, contradiction_audited=False)
        body = {
            "schema": HIVE_SCHEMA,
            "subject_id": current.subject_id,
            "version": current.version + 1,
            "payload_hash": current.payload_hash,
            "priority": current.priority,
            "coordinate": asdict(current.coordinate),
            "semantic_key": current.semantic_key,
            "state": "DISPUTED",
            "gates": asdict(gates),
            "provenance": current.provenance,
            "dependencies": current.dependencies,
            "contradictions": tuple(sorted(set(current.contradictions + (ref,)))),
            "parent_record_id": current.record_id,
            "authority": current.authority,
        }
        rec = HiveRecord(
            record_id=self._record_id(body),
            payload=current.payload,
            seal_receipt=None,
            coordinate=current.coordinate,
            gates=gates,
            **{k: v for k, v in body.items() if k not in {"schema", "coordinate", "gates"}},
        )
        self._append(rec)
        return rec

    def latch(self, subject_id: str) -> HiveRecord:
        current = self.head(subject_id)
        if current.state in {"DISPUTED", "QUARANTINED"}:
            raise RuntimeError("disputed/quarantined information cannot latch")
        if not current.gates.closed:
            raise RuntimeError("closure gates incomplete: " + ",".join(current.gates.missing))
        seal_body = {
            "schema": HIVE_SCHEMA,
            "record_id": current.record_id,
            "payload_hash": current.payload_hash,
            "coordinate": asdict(current.coordinate),
            "provenance": current.provenance,
            "dependencies": current.dependencies,
            "gates": asdict(current.gates),
            "authority": current.authority,
        }
        receipt = "latch:" + _digest(seal_body, person=b"GRMLN-HIVE-LCH")
        body = {
            "schema": HIVE_SCHEMA,
            "subject_id": current.subject_id,
            "version": current.version + 1,
            "payload_hash": current.payload_hash,
            "priority": current.priority,
            "coordinate": asdict(current.coordinate),
            "semantic_key": current.semantic_key,
            "state": "LOCKED",
            "gates": asdict(current.gates),
            "provenance": current.provenance,
            "dependencies": current.dependencies,
            "contradictions": current.contradictions,
            "parent_record_id": current.record_id,
            "authority": current.authority,
            "seal_receipt": receipt,
        }
        rec = HiveRecord(
            record_id=self._record_id(body),
            payload=current.payload,
            coordinate=current.coordinate,
            gates=current.gates,
            **{k: v for k, v in body.items() if k not in {"schema", "coordinate", "gates"}},
        )
        self._append(rec)
        return rec

    def flat_ring_table(self) -> tuple[HiveRecord, ...]:
        """Return current heads sorted inner->outer, then angle, then phase."""
        records = [self._records[rid] for rid in self._heads.values()]
        return tuple(sorted(records, key=lambda r: (
            r.coordinate.radius,
            r.coordinate.semantic_angle,
            r.coordinate.relation_phase,
            r.subject_id,
        )))

    def history(self, subject_id: str) -> tuple[HiveRecord, ...]:
        current = self.head(subject_id)
        out = [current]
        while current.parent_record_id is not None:
            current = self._records[current.parent_record_id]
            out.append(current)
        return tuple(reversed(out))


class SQLiteHiveStore:
    """Append-only durable receipt store for Hive Memory records."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._db = sqlite3.connect(str(self.path), timeout=5.0, isolation_level=None, check_same_thread=False)
        with self._lock:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.executescript("""
            CREATE TABLE IF NOT EXISTS hive_records (
                ordinal INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT UNIQUE NOT NULL,
                subject_id TEXT NOT NULL,
                data_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS hive_subject_idx ON hive_records(subject_id, ordinal);
            """)

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def append(self, record: HiveRecord) -> None:
        data = asdict(record)
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                self._db.execute(
                    "INSERT INTO hive_records(record_id, subject_id, data_json) VALUES(?,?,?)",
                    (record.record_id, record.subject_id, _canonical(data)),
                )
                self._db.execute("COMMIT")
            except Exception:
                self._db.execute("ROLLBACK")
                raise

    def rows(self, subject_id: str | None = None) -> tuple[dict[str, Any], ...]:
        with self._lock:
            if subject_id is None:
                rows = self._db.execute("SELECT data_json FROM hive_records ORDER BY ordinal").fetchall()
            else:
                rows = self._db.execute(
                    "SELECT data_json FROM hive_records WHERE subject_id=? ORDER BY ordinal",
                    (str(subject_id),),
                ).fetchall()
        return tuple(json.loads(row[0]) for row in rows)
