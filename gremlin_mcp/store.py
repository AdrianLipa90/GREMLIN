from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any, Mapping

STORE_SCHEMA = "GREMLIN_MCP_SQLITE_WAL_V0_3"


def _strict_key(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _json(value: Mapping[str, Any]) -> str:
    if not isinstance(value, Mapping):
        raise ValueError("worker store value must be an object")
    return json.dumps(
        dict(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


class SQLiteWorkerStore:
    """Small durable store for the standalone Worker ABI.

    SQLite is used in WAL mode so the MCP server keeps a single durable local
    authority for worker/task/lease coordination without requiring NOEMA.
    Payloads remain canonical JSON; GREMLIN commitments are computed in the
    broker before persistence.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(
            str(self.path),
            timeout=5.0,
            isolation_level=None,
            check_same_thread=False,
        )
        try:
            with self._lock:
                self._connection.execute("PRAGMA journal_mode=WAL")
                self._connection.execute("PRAGMA synchronous=FULL")
                self._connection.execute("PRAGMA foreign_keys=ON")
                self._connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS workers (
                        worker_id TEXT PRIMARY KEY,
                        data_json TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY,
                        data_json TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS leases (
                        lease_id TEXT PRIMARY KEY,
                        data_json TEXT NOT NULL
                    );
                    """
                )
                schema_row = self._connection.execute(
                    "SELECT value FROM meta WHERE key = 'schema'"
                ).fetchone()
                if schema_row is None:
                    persisted_rows = sum(
                        int(self._connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                        for table in ("workers", "tasks", "leases")
                    )
                    if persisted_rows:
                        raise RuntimeError(
                            "GREMLIN worker store contains persisted state without schema metadata"
                        )
                    self._connection.execute(
                        "INSERT INTO meta(key, value) VALUES('schema', ?)",
                        (STORE_SCHEMA,),
                    )
                else:
                    schema = schema_row[0]
                    if not isinstance(schema, str) or schema != STORE_SCHEMA:
                        raise RuntimeError(
                            f"incompatible GREMLIN worker store schema: {schema!r}; expected {STORE_SCHEMA}"
                        )
        except Exception:
            self._connection.close()
            raise

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _upsert(self, table: str, key_name: str, key: str, value: Mapping[str, Any]) -> None:
        if table not in {"workers", "tasks", "leases"}:
            raise ValueError("unsupported store table")
        safe_key = _strict_key(key, key_name)
        payload = _json(value)
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                self._connection.execute(
                    f"INSERT INTO {table}({key_name}, data_json) VALUES(?, ?) "
                    f"ON CONFLICT({key_name}) DO UPDATE SET data_json=excluded.data_json",
                    (safe_key, payload),
                )
                self._connection.execute("COMMIT")
            except Exception:
                self._connection.execute("ROLLBACK")
                raise

    def save_worker(self, worker_id: str, value: Mapping[str, Any]) -> None:
        self._upsert("workers", "worker_id", worker_id, value)

    def save_task(self, task_id: str, value: Mapping[str, Any]) -> None:
        self._upsert("tasks", "task_id", task_id, value)

    def save_lease(self, lease_id: str, value: Mapping[str, Any]) -> None:
        self._upsert("leases", "lease_id", lease_id, value)

    def delete_lease(self, lease_id: str) -> None:
        safe_lease_id = _strict_key(lease_id, "lease_id")
        with self._lock:
            self._connection.execute("DELETE FROM leases WHERE lease_id = ?", (safe_lease_id,))

    def _load_table(self, table: str, key_name: str) -> dict[str, dict[str, Any]]:
        if table not in {"workers", "tasks", "leases"}:
            raise ValueError("unsupported store table")
        with self._lock:
            rows = self._connection.execute(
                f"SELECT {key_name}, data_json FROM {table} ORDER BY {key_name}"
            ).fetchall()
        out: dict[str, dict[str, Any]] = {}
        for key, payload in rows:
            safe_key = _strict_key(key, key_name)
            if not isinstance(payload, str):
                raise RuntimeError("corrupt GREMLIN worker store JSON payload type")
            value = json.loads(payload)
            if not isinstance(value, dict):
                raise RuntimeError("corrupt GREMLIN worker store row")
            out[safe_key] = value
        return out

    def load(self) -> dict[str, dict[str, dict[str, Any]]]:
        with self._lock:
            schema_row = self._connection.execute(
                "SELECT value FROM meta WHERE key = 'schema'"
            ).fetchone()
        if schema_row is None or schema_row[0] != STORE_SCHEMA:
            raise RuntimeError("GREMLIN worker store schema changed after initialization")
        return {
            "workers": self._load_table("workers", "worker_id"),
            "tasks": self._load_table("tasks", "task_id"),
            "leases": self._load_table("leases", "lease_id"),
        }

    def stats(self) -> dict[str, Any]:
        with self._lock:
            counts = {
                table: int(self._connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in ("workers", "tasks", "leases")
            }
            journal = self._connection.execute("PRAGMA journal_mode").fetchone()[0]
        if not isinstance(journal, str):
            raise RuntimeError("SQLite returned a non-text journal mode")
        return {
            "schema": STORE_SCHEMA,
            "journal_mode": journal.upper(),
            **counts,
        }
