from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any, Mapping

STORE_SCHEMA = "GREMLIN_MCP_SQLITE_WAL_V0_3"


def _json(value: Mapping[str, Any]) -> str:
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
            self._connection.execute(
                "INSERT INTO meta(key, value) VALUES('schema', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (STORE_SCHEMA,),
            )

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _upsert(self, table: str, key_name: str, key: str, value: Mapping[str, Any]) -> None:
        if table not in {"workers", "tasks", "leases"}:
            raise ValueError("unsupported store table")
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                self._connection.execute(
                    f"INSERT INTO {table}({key_name}, data_json) VALUES(?, ?) "
                    f"ON CONFLICT({key_name}) DO UPDATE SET data_json=excluded.data_json",
                    (str(key), _json(value)),
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
        with self._lock:
            self._connection.execute("DELETE FROM leases WHERE lease_id = ?", (str(lease_id),))

    def _load_table(self, table: str, key_name: str) -> dict[str, dict[str, Any]]:
        if table not in {"workers", "tasks", "leases"}:
            raise ValueError("unsupported store table")
        with self._lock:
            rows = self._connection.execute(
                f"SELECT {key_name}, data_json FROM {table} ORDER BY {key_name}"
            ).fetchall()
        out: dict[str, dict[str, Any]] = {}
        for key, payload in rows:
            value = json.loads(payload)
            if not isinstance(value, dict):
                raise RuntimeError("corrupt GREMLIN worker store row")
            out[str(key)] = value
        return out

    def load(self) -> dict[str, dict[str, dict[str, Any]]]:
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
            journal = str(self._connection.execute("PRAGMA journal_mode").fetchone()[0]).upper()
        return {
            "schema": STORE_SCHEMA,
            "journal_mode": journal,
            **counts,
        }
