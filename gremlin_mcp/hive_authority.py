from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any, Iterable, Mapping

from .orbital_hive_memory import ClosureGates, HIVE_SCHEMA, HiveRecord, OrbitalHiveMemory, normalize_phase

AUTHORITY_SCHEMA = "GREMLIN_HIVE_AUTHORITY_RUNTIME_V0_2"


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


class HiveAuthorityRuntime:
    """One fail-closed authority surface for GREMLIN Hive working memory.

    With a SQLite path configured, every operation rehydrates under a SQLite
    BEGIN IMMEDIATE transaction before mutation. This prevents two GREMLIN MCP
    processes from independently advancing the same subject head. Without a
    path, the runtime is process-resident and protected by an RLock.

    The authority here is only authority over Hive lineage ordering. It never
    grants repository, publication, production-execution or canon authority.
    """

    def __init__(self, state_path: str | Path | None = None, *, orbit_count: int = 36) -> None:
        self.orbit_count = int(orbit_count)
        self._lock = RLock()
        self._memory = OrbitalHiveMemory(orbit_count=self.orbit_count)
        self._path: Path | None = None
        self._db: sqlite3.Connection | None = None
        if state_path is not None and str(state_path).strip():
            self._path = Path(state_path).expanduser().resolve()
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(
                str(self._path),
                timeout=5.0,
                isolation_level=None,
                check_same_thread=False,
            )
            with self._lock:
                self._db.execute("PRAGMA journal_mode=WAL")
                self._db.execute("PRAGMA synchronous=FULL")
                self._db.execute("PRAGMA foreign_keys=ON")
                self._db.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS hive_records (
                        ordinal INTEGER PRIMARY KEY AUTOINCREMENT,
                        record_id TEXT UNIQUE NOT NULL,
                        subject_id TEXT NOT NULL,
                        data_json TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS hive_subject_idx
                        ON hive_records(subject_id, ordinal);
                    CREATE TABLE IF NOT EXISTS hive_heads (
                        subject_id TEXT PRIMARY KEY,
                        record_id TEXT UNIQUE NOT NULL
                    );
                    """
                )
                self._repair_heads_locked()

    @property
    def persistent(self) -> bool:
        return self._db is not None

    @property
    def state_path(self) -> str | None:
        return None if self._path is None else str(self._path)

    def close(self) -> None:
        with self._lock:
            if self._db is not None:
                self._db.close()
                self._db = None

    def _rows_locked(self, subject_id: str | None = None) -> tuple[dict[str, Any], ...]:
        if self._db is None:
            raise RuntimeError("durable Hive store is not configured")
        if subject_id is None:
            rows = self._db.execute(
                "SELECT data_json FROM hive_records ORDER BY ordinal"
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT data_json FROM hive_records WHERE subject_id=? ORDER BY ordinal",
                (str(subject_id),),
            ).fetchall()
        return tuple(json.loads(row[0]) for row in rows)

    def _hydrate_locked(self) -> OrbitalHiveMemory:
        if self._db is None:
            return self._memory
        hive = OrbitalHiveMemory(orbit_count=self.orbit_count)
        for row in self._rows_locked():
            hive.import_record(row)
        return hive

    def _repair_heads_locked(self) -> None:
        """Rebuild heads from append-only lineage; fail closed on corrupt forks."""
        if self._db is None:
            return
        hive = OrbitalHiveMemory(orbit_count=self.orbit_count)
        children: dict[str, list[str]] = {}
        rows = self._rows_locked()
        for row in rows:
            parent = row.get("parent_record_id")
            if parent is not None:
                children.setdefault(str(parent), []).append(str(row["record_id"]))
            hive.import_record(row)
        forks = {parent: ids for parent, ids in children.items() if len(ids) > 1}
        if forks:
            raise RuntimeError(f"forked persisted hive lineage: {forks}")
        self._db.execute("DELETE FROM hive_heads")
        for record in hive.flat_ring_table():
            self._db.execute(
                "INSERT INTO hive_heads(subject_id, record_id) VALUES(?, ?)",
                (record.subject_id, record.record_id),
            )

    def _persist_locked(self, record: HiveRecord) -> None:
        if self._db is None:
            return
        parent = record.parent_record_id
        current = self._db.execute(
            "SELECT record_id FROM hive_heads WHERE subject_id=?",
            (record.subject_id,),
        ).fetchone()
        current_id = None if current is None else str(current[0])
        if current_id != parent:
            raise RuntimeError(
                "Hive head changed during mutation; refusing stale append"
            )
        self._db.execute(
            "INSERT INTO hive_records(record_id, subject_id, data_json) VALUES(?,?,?)",
            (record.record_id, record.subject_id, _json(asdict(record))),
        )
        self._db.execute(
            "INSERT INTO hive_heads(subject_id, record_id) VALUES(?, ?) "
            "ON CONFLICT(subject_id) DO UPDATE SET record_id=excluded.record_id",
            (record.subject_id, record.record_id),
        )

    def _mutate(self, operation: str, *args: Any, **kwargs: Any) -> HiveRecord:
        with self._lock:
            if self._db is None:
                hive = self._memory
                method = getattr(hive, operation)
                return method(*args, **kwargs)
            self._db.execute("BEGIN IMMEDIATE")
            try:
                hive = self._hydrate_locked()
                method = getattr(hive, operation)
                record: HiveRecord = method(*args, **kwargs)
                self._persist_locked(record)
                self._db.execute("COMMIT")
                return record
            except Exception:
                self._db.execute("ROLLBACK")
                raise

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
        return self._mutate(
            "place",
            subject_id=subject_id,
            payload=payload,
            priority=priority,
            semantic_key=semantic_key,
            relation_phase=relation_phase,
            provenance=provenance,
            dependencies=dependencies,
            gates=gates,
        )

    def place_idempotent(
        self,
        *,
        subject_id: str,
        payload: Mapping[str, Any],
        priority: float,
        semantic_key: str,
        relation_phase: float,
        provenance: Iterable[str] = (),
        dependencies: Iterable[str] = (),
    ) -> tuple[HiveRecord, bool]:
        """Atomically place one immutable observation or return its existing head.

        This operation is intended for deterministic component ingestion. The read
        and conditional append share the same process lock and, for durable state,
        the same BEGIN IMMEDIATE transaction. A reused subject with different
        content/address/provenance/dependencies fails closed rather than creating an
        implicit new semantic version.
        """
        subject = str(subject_id).strip()
        if not subject:
            raise ValueError("subject_id must be non-empty")
        payload_dict = dict(payload)
        priority_value = float(priority)
        semantic_value = str(semantic_key)
        phase_value = normalize_phase(relation_phase)
        provenance_value = tuple(sorted({str(x) for x in provenance if str(x)}))
        dependencies_value = tuple(sorted({str(x) for x in dependencies if str(x)}))

        def matches(current: HiveRecord) -> bool:
            return (
                dict(current.payload) == payload_dict
                and abs(float(current.priority) - priority_value) <= 1e-12
                and current.semantic_key == semantic_value
                and abs(float(current.coordinate.relation_phase) - phase_value) <= 1e-12
                and current.provenance == provenance_value
                and current.dependencies == dependencies_value
            )

        def resolve(hive: OrbitalHiveMemory) -> tuple[HiveRecord, bool]:
            try:
                current = hive.head(subject)
            except KeyError:
                current = None
            if current is not None:
                if matches(current):
                    return current, False
                raise RuntimeError(
                    "same Hive subject already exists with different content or lineage metadata; "
                    "refuse implicit overwrite"
                )
            record = hive.place(
                subject_id=subject,
                payload=payload_dict,
                priority=priority_value,
                semantic_key=semantic_value,
                relation_phase=phase_value,
                provenance=provenance_value,
                dependencies=dependencies_value,
            )
            return record, True

        with self._lock:
            if self._db is None:
                return resolve(self._memory)
            self._db.execute("BEGIN IMMEDIATE")
            try:
                hive = self._hydrate_locked()
                record, created = resolve(hive)
                if created:
                    self._persist_locked(record)
                self._db.execute("COMMIT")
                return record, created
            except Exception:
                self._db.execute("ROLLBACK")
                raise

    def update_gates(self, subject_id: str, **changes: bool) -> HiveRecord:
        return self._mutate("update_gates", subject_id, **changes)

    def dispute(self, subject_id: str, contradiction_ref: str) -> HiveRecord:
        return self._mutate("dispute", subject_id, contradiction_ref)

    def latch(self, subject_id: str) -> HiveRecord:
        return self._mutate("latch", subject_id)

    def _read_hive(self) -> OrbitalHiveMemory:
        with self._lock:
            return self._hydrate_locked()

    def head(self, subject_id: str) -> HiveRecord:
        return self._read_hive().head(subject_id)

    def table(self) -> tuple[HiveRecord, ...]:
        return self._read_hive().flat_ring_table()

    def history(self, subject_id: str) -> tuple[HiveRecord, ...]:
        return self._read_hive().history(subject_id)

    def persisted(self, subject_id: str | None = None) -> tuple[dict[str, Any], ...]:
        with self._lock:
            if self._db is None:
                return tuple(asdict(record) for record in (
                    self._memory.history(subject_id) if subject_id is not None else self._memory.flat_ring_table()
                ))
            return self._rows_locked(subject_id)

    def status(self) -> dict[str, Any]:
        table = self.table()
        return {
            "schema": AUTHORITY_SCHEMA,
            "hive_schema": HIVE_SCHEMA,
            "status": "AVAILABLE",
            "orbit_count": self.orbit_count,
            "head_count": len(table),
            "persistence": "SQLITE_WAL_SINGLE_AUTHORITY" if self.persistent else "PROCESS_RESIDENT",
            "state_path": self.state_path,
            "authority": "SHARED_COGNITION_ONLY",
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        }


__all__ = ["AUTHORITY_SCHEMA", "HiveAuthorityRuntime"]
