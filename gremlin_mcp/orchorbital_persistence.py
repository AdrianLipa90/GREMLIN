from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any, Mapping

from gremlin_mcp.orchorbital_context import OrbitalContextStore
from gremlin_mcp.orchorbital_executor import OrchorbitalExecutor
from gremlin_mcp.orchorbital_fabric import OrchorbitalFabric
from gremlin_mcp.orchorbital_local import LocalAdapterRegistry

SCHEMA = "GREMLIN_ORCHORBITAL_RUNTIME_CHECKPOINT_V0_1"
STORE_SCHEMA = "GREMLIN_ORCHORBITAL_RUNTIME_SQLITE_WAL_V0_1"
CHECKPOINT_DOMAIN = b"GREMLIN-ORCHORBITAL-RUNTIME-CHECKPOINT/v0.1\x00"


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
        raise ValueError("runtime checkpoint must be finite JSON data") from exc


def _strict_execution_id(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("execution_id must be a string")
    out = value.strip()
    if not out or len(out) > 128:
        raise ValueError("execution_id must contain 1..128 characters")
    return out


def _strict_commitment(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field} must be a 64-character commitment")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{field} must be hexadecimal") from exc
    return value


def build_runtime_checkpoint(
    executor: OrchorbitalExecutor,
) -> dict[str, object]:
    """Capture one cross-layer restart checkpoint at a stable topology point.

    WorkerBroker state is deliberately external. PersistentWorkerBroker owns
    queue/task/result/lease durability; this envelope owns the dynamic fabric,
    immutable context lineage and executor-local semantic results.
    """

    if not isinstance(executor, OrchorbitalExecutor):
        raise ValueError("executor must be an OrchorbitalExecutor")

    topology_before = executor.fabric.topology_commitment()
    fabric_checkpoint = executor.fabric.checkpoint_state()

    context_checkpoint: dict[str, object] | None = None
    if executor.context_store is not None:
        context_checkpoint = executor.context_store.checkpoint_state()

    executor_checkpoint = executor.checkpoint_state()
    topology_after = executor.fabric.topology_commitment()
    if topology_after != topology_before:
        raise RuntimeError("orchorbital topology changed during runtime checkpoint capture")

    fabric_commitment = _strict_commitment(
        fabric_checkpoint.get("checkpoint_commitment"),
        "fabric checkpoint commitment",
    )
    executor_commitment = _strict_commitment(
        executor_checkpoint.get("checkpoint_commitment"),
        "executor checkpoint commitment",
    )
    context_commitment: str | None = None
    if context_checkpoint is not None:
        context_commitment = _strict_commitment(
            context_checkpoint.get("checkpoint_commitment"),
            "context checkpoint commitment",
        )

    if fabric_checkpoint.get("topology_commitment") != topology_before:
        raise RuntimeError("fabric checkpoint topology commitment drift")
    if executor_checkpoint.get("fabric_topology_commitment") != topology_before:
        raise RuntimeError("executor checkpoint topology commitment drift")
    if executor_checkpoint.get("context_checkpoint_commitment") != context_commitment:
        raise RuntimeError("executor/context checkpoint commitment drift")

    core: dict[str, object] = {
        "schema": SCHEMA,
        "execution_id": executor.execution_id,
        "fabric_topology_commitment": topology_before,
        "fabric_checkpoint_commitment": fabric_commitment,
        "context_checkpoint_commitment": context_commitment,
        "executor_checkpoint_commitment": executor_commitment,
        "fabric": fabric_checkpoint,
        "context": context_checkpoint,
        "executor": executor_checkpoint,
        "worker_broker_state_included": False,
        "worker_broker_state_required_external": True,
        "sensitive_runtime_state": True,
        "canon_allowed": False,
    }
    return {
        **core,
        "checkpoint_commitment": hashlib.blake2b(
            CHECKPOINT_DOMAIN + _canonical(core),
            digest_size=32,
        ).hexdigest(),
    }


def restore_runtime_checkpoint(
    checkpoint: Mapping[str, Any],
    *,
    broker: Any,
    local_adapters: LocalAdapterRegistry | None = None,
) -> OrchorbitalExecutor:
    """Restore fabric -> context -> executor and verify cross-layer commitments."""

    if not isinstance(checkpoint, Mapping):
        raise ValueError("runtime checkpoint must be a mapping")
    if checkpoint.get("schema") != SCHEMA:
        raise ValueError("invalid runtime checkpoint schema")
    supplied = _strict_commitment(
        checkpoint.get("checkpoint_commitment"),
        "runtime checkpoint commitment",
    )
    core = {
        key: deepcopy(value)
        for key, value in checkpoint.items()
        if key != "checkpoint_commitment"
    }
    expected = hashlib.blake2b(
        CHECKPOINT_DOMAIN + _canonical(core),
        digest_size=32,
    ).hexdigest()
    if supplied != expected:
        raise ValueError("runtime checkpoint commitment mismatch")

    execution_id = _strict_execution_id(core.get("execution_id"))
    raw_fabric = core.get("fabric")
    raw_context = core.get("context")
    raw_executor = core.get("executor")
    if not isinstance(raw_fabric, Mapping):
        raise ValueError("runtime fabric checkpoint must be an object")
    if raw_context is not None and not isinstance(raw_context, Mapping):
        raise ValueError("runtime context checkpoint must be an object or null")
    if not isinstance(raw_executor, Mapping):
        raise ValueError("runtime executor checkpoint must be an object")

    fabric_commitment = _strict_commitment(
        core.get("fabric_checkpoint_commitment"),
        "fabric checkpoint commitment",
    )
    if raw_fabric.get("checkpoint_commitment") != fabric_commitment:
        raise ValueError("runtime/fabric checkpoint commitment mismatch")

    executor_commitment = _strict_commitment(
        core.get("executor_checkpoint_commitment"),
        "executor checkpoint commitment",
    )
    if raw_executor.get("checkpoint_commitment") != executor_commitment:
        raise ValueError("runtime/executor checkpoint commitment mismatch")

    context_commitment_raw = core.get("context_checkpoint_commitment")
    if context_commitment_raw is None:
        if raw_context is not None:
            raise ValueError("runtime context presence/commitment mismatch")
        context_commitment = None
    else:
        context_commitment = _strict_commitment(
            context_commitment_raw,
            "context checkpoint commitment",
        )
        if raw_context is None or raw_context.get("checkpoint_commitment") != context_commitment:
            raise ValueError("runtime/context checkpoint commitment mismatch")

    fabric = OrchorbitalFabric.from_checkpoint(raw_fabric)
    topology = fabric.topology_commitment()
    claimed_topology = _strict_commitment(
        core.get("fabric_topology_commitment"),
        "fabric_topology_commitment",
    )
    if topology != claimed_topology:
        raise ValueError("runtime restored topology commitment mismatch")

    context_store: OrbitalContextStore | None = None
    if raw_context is not None:
        context_store = OrbitalContextStore.from_checkpoint(
            fabric,
            raw_context,
        )
        if (
            context_store.checkpoint_state().get("checkpoint_commitment")
            != context_commitment
        ):
            raise ValueError("runtime restored context commitment mismatch")

    restored = OrchorbitalExecutor.from_checkpoint(
        raw_executor,
        fabric=fabric,
        broker=broker,
        context_store=context_store,
        local_adapters=local_adapters,
    )
    if restored.execution_id != execution_id:
        raise ValueError("runtime restored execution_id mismatch")
    if restored.fabric.topology_commitment() != claimed_topology:
        raise ValueError("runtime restored executor topology mismatch")
    return restored


class DurableOrchorbitalRuntime:
    """Small durability façade around executor + runtime checkpoint store.

    It does not own WorkerBroker persistence. A PersistentWorkerBroker should be
    used separately when queue/task/lease/result durability is required.
    """

    def __init__(
        self,
        executor: OrchorbitalExecutor,
        store: "SQLiteOrchorbitalRuntimeStore",
    ) -> None:
        if not isinstance(executor, OrchorbitalExecutor):
            raise ValueError("executor must be an OrchorbitalExecutor")
        if not isinstance(store, SQLiteOrchorbitalRuntimeStore):
            raise ValueError("store must be a SQLiteOrchorbitalRuntimeStore")
        self.executor = executor
        self.store = store

    @property
    def execution_id(self) -> str:
        return self.executor.execution_id

    def checkpoint(self) -> dict[str, object]:
        return self.store.save(self.executor)

    def orchestration_step(
        self,
        payload_overrides: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> dict[str, object]:
        """Advance once, then durably checkpoint the resulting runtime state."""

        step = self.executor.orchestration_step(payload_overrides)
        checkpoint = self.store.save(self.executor)
        return {
            "schema": SCHEMA,
            "execution_id": self.execution_id,
            "step": step,
            "checkpoint": checkpoint,
            "checkpoint_after_step": True,
            "worker_broker_state_included": False,
            "canon_allowed": False,
        }

    @classmethod
    def restore(
        cls,
        store: "SQLiteOrchorbitalRuntimeStore",
        execution_id: str,
        *,
        broker: Any,
    ) -> "DurableOrchorbitalRuntime":
        if not isinstance(store, SQLiteOrchorbitalRuntimeStore):
            raise ValueError("store must be a SQLiteOrchorbitalRuntimeStore")
        executor = store.restore(execution_id, broker=broker)
        return cls(executor, store)


class SQLiteOrchorbitalRuntimeStore:
    """Durable single-row-per-execution store for orchorbital runtime state."""

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
                    CREATE TABLE IF NOT EXISTS runtime_checkpoints (
                        execution_id TEXT PRIMARY KEY,
                        checkpoint_commitment TEXT NOT NULL,
                        data_json TEXT NOT NULL
                    );
                    """
                )
                row = self._connection.execute(
                    "SELECT value FROM meta WHERE key = 'schema'"
                ).fetchone()
                if row is None:
                    count = int(
                        self._connection.execute(
                            "SELECT COUNT(*) FROM runtime_checkpoints"
                        ).fetchone()[0]
                    )
                    if count:
                        raise RuntimeError(
                            "orchorbital runtime store has state without schema metadata"
                        )
                    self._connection.execute(
                        "INSERT INTO meta(key, value) VALUES('schema', ?)",
                        (STORE_SCHEMA,),
                    )
                elif row[0] != STORE_SCHEMA:
                    raise RuntimeError(
                        f"incompatible orchorbital runtime store schema: {row[0]!r}"
                    )
        except Exception:
            self._connection.close()
            raise

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def save(self, executor: OrchorbitalExecutor) -> dict[str, object]:
        checkpoint = build_runtime_checkpoint(executor)
        execution_id = _strict_execution_id(checkpoint.get("execution_id"))
        commitment = _strict_commitment(
            checkpoint.get("checkpoint_commitment"),
            "runtime checkpoint commitment",
        )
        payload = _canonical(checkpoint).decode("utf-8")
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                self._connection.execute(
                    """
                    INSERT INTO runtime_checkpoints(
                        execution_id,
                        checkpoint_commitment,
                        data_json
                    ) VALUES(?, ?, ?)
                    ON CONFLICT(execution_id) DO UPDATE SET
                        checkpoint_commitment=excluded.checkpoint_commitment,
                        data_json=excluded.data_json
                    """,
                    (execution_id, commitment, payload),
                )
                row = self._connection.execute(
                    """
                    SELECT checkpoint_commitment, data_json
                    FROM runtime_checkpoints
                    WHERE execution_id = ?
                    """,
                    (execution_id,),
                ).fetchone()
                if row is None or row[0] != commitment or row[1] != payload:
                    raise RuntimeError("orchorbital runtime checkpoint readback mismatch")
                self._connection.execute("COMMIT")
            except Exception:
                self._connection.execute("ROLLBACK")
                raise
        return {
            "schema": STORE_SCHEMA,
            "execution_id": execution_id,
            "checkpoint_commitment": commitment,
            "fabric_topology_commitment": checkpoint[
                "fabric_topology_commitment"
            ],
            "journal_mode": self.journal_mode(),
            "canon_allowed": False,
        }

    def load_checkpoint(self, execution_id: str) -> dict[str, Any]:
        eid = _strict_execution_id(execution_id)
        with self._lock:
            schema_row = self._connection.execute(
                "SELECT value FROM meta WHERE key = 'schema'"
            ).fetchone()
            if schema_row is None or schema_row[0] != STORE_SCHEMA:
                raise RuntimeError("orchorbital runtime store schema changed")
            row = self._connection.execute(
                """
                SELECT checkpoint_commitment, data_json
                FROM runtime_checkpoints
                WHERE execution_id = ?
                """,
                (eid,),
            ).fetchone()
        if row is None:
            raise ValueError(f"unknown runtime execution_id: {eid}")
        commitment, payload = row
        if not isinstance(commitment, str) or not isinstance(payload, str):
            raise RuntimeError("corrupt orchorbital runtime store row")
        value = json.loads(payload)
        if not isinstance(value, dict):
            raise RuntimeError("corrupt orchorbital runtime checkpoint JSON")
        if value.get("checkpoint_commitment") != commitment:
            raise RuntimeError("stored runtime checkpoint commitment column mismatch")
        # Full envelope verification, without requiring a broker yet.
        supplied = _strict_commitment(
            value.get("checkpoint_commitment"),
            "runtime checkpoint commitment",
        )
        core = {
            key: deepcopy(raw)
            for key, raw in value.items()
            if key != "checkpoint_commitment"
        }
        expected = hashlib.blake2b(
            CHECKPOINT_DOMAIN + _canonical(core),
            digest_size=32,
        ).hexdigest()
        if supplied != expected:
            raise RuntimeError("stored runtime checkpoint commitment mismatch")
        return value

    def restore(
        self,
        execution_id: str,
        *,
        broker: Any,
        local_adapters: LocalAdapterRegistry | None = None,
    ) -> OrchorbitalExecutor:
        return restore_runtime_checkpoint(
            self.load_checkpoint(execution_id),
            broker=broker,
            local_adapters=local_adapters,
        )

    def journal_mode(self) -> str:
        with self._lock:
            row = self._connection.execute("PRAGMA journal_mode").fetchone()
        if row is None or not isinstance(row[0], str):
            raise RuntimeError("SQLite returned invalid journal mode")
        return row[0].upper()

    def stats(self) -> dict[str, object]:
        with self._lock:
            count = int(
                self._connection.execute(
                    "SELECT COUNT(*) FROM runtime_checkpoints"
                ).fetchone()[0]
            )
        return {
            "schema": STORE_SCHEMA,
            "journal_mode": self.journal_mode(),
            "checkpoint_count": count,
            "worker_broker_state_included": False,
            "canon_allowed": False,
        }


__all__ = [
    "CHECKPOINT_DOMAIN",
    "DurableOrchorbitalRuntime",
    "SCHEMA",
    "STORE_SCHEMA",
    "SQLiteOrchorbitalRuntimeStore",
    "build_runtime_checkpoint",
    "restore_runtime_checkpoint",
]
