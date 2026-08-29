from __future__ import annotations

from typing import Any, Iterable, Mapping

from gremlin_mcp.store import SQLiteWorkerStore
from gremlin_mcp.workers import (
    WORKER_SCHEMA,
    LeaseRecord,
    TaskRecord,
    WorkerBroker,
    WorkerRecord,
    _commit,
    _normalize_id,
)


class PersistentWorkerBroker(WorkerBroker):
    """WorkerBroker with fail-closed SQLite WAL persistence.

    The scheduling/lease semantics remain those of ``WorkerBroker``. This class
    only makes worker registrations, tasks, candidate results and active leases
    survive a standalone MCP server restart.
    """

    def __init__(
        self,
        state_path: str,
        *,
        lease_seconds: int = 30,
        max_pending: int = 10_000,
    ) -> None:
        super().__init__(lease_seconds=lease_seconds, max_pending=max_pending)
        self._store = SQLiteWorkerStore(state_path)
        self._hydrate()

    def _hydrate(self) -> None:
        snapshot = self._store.load()
        try:
            self._workers = {
                worker_id: WorkerRecord(
                    worker_id=str(row["worker_id"]),
                    species=tuple(str(x) for x in row["species"]),
                    capabilities=tuple(str(x) for x in row["capabilities"]),
                    vector_width=int(row["vector_width"]),
                    max_batch=int(row["max_batch"]),
                    registered_ns=int(row["registered_ns"]),
                    last_seen_ns=int(row["last_seen_ns"]),
                )
                for worker_id, row in snapshot["workers"].items()
            }
            self._tasks = {
                task_id: TaskRecord(
                    task_id=str(row["task_id"]),
                    species=str(row["species"]),
                    payload=dict(row["payload"]),
                    task_commitment=str(row["task_commitment"]),
                    created_ns=int(row["created_ns"]),
                    state=str(row.get("state", "QUEUED")),
                    lease_id=row.get("lease_id"),
                    leased_to=row.get("leased_to"),
                    lease_expires_ns=(
                        None if row.get("lease_expires_ns") is None else int(row["lease_expires_ns"])
                    ),
                    result=row.get("result"),
                    result_commitment=row.get("result_commitment"),
                )
                for task_id, row in snapshot["tasks"].items()
            }
            self._leases = {
                lease_id: LeaseRecord(
                    lease_id=str(row["lease_id"]),
                    worker_id=str(row["worker_id"]),
                    species=str(row["species"]),
                    task_ids=tuple(str(x) for x in row["task_ids"]),
                    issued_ns=int(row["issued_ns"]),
                    expires_ns=int(row["expires_ns"]),
                )
                for lease_id, row in snapshot["leases"].items()
            }
            self._validate_hydrated_state()
            # Expired leases are safely returned to QUEUED on restart.
            import time

            self._reap_expired(time.time_ns())
        except Exception as exc:
            raise RuntimeError("GREMLIN SQLite worker state failed closed during hydration") from exc

    def _validate_hydrated_state(self) -> None:
        for key, worker in self._workers.items():
            if key != worker.worker_id:
                raise ValueError("worker store key mismatch")
        for key, task in self._tasks.items():
            if key != task.task_id:
                raise ValueError("task store key mismatch")
            expected = _commit(
                {
                    "schema": WORKER_SCHEMA,
                    "task_id": task.task_id,
                    "species": task.species,
                    "payload": task.payload,
                }
            )
            if expected != task.task_commitment:
                raise ValueError("persisted task commitment mismatch")
            if task.state not in {"QUEUED", "LEASED", "DONE"}:
                raise ValueError("persisted task state is invalid")
        for key, lease in self._leases.items():
            if key != lease.lease_id:
                raise ValueError("lease store key mismatch")
            worker = self._workers.get(lease.worker_id)
            if worker is None or lease.species not in worker.species:
                raise ValueError("persisted lease worker/species mismatch")
            for task_id in lease.task_ids:
                task = self._tasks.get(task_id)
                if task is None:
                    raise ValueError("persisted lease references missing task")
                if (
                    task.state != "LEASED"
                    or task.lease_id != lease.lease_id
                    or task.leased_to != lease.worker_id
                    or task.species != lease.species
                ):
                    raise ValueError("persisted lease/task lineage mismatch")

    @staticmethod
    def _worker_store_view(record: WorkerRecord) -> dict[str, Any]:
        return {
            "worker_id": record.worker_id,
            "species": list(record.species),
            "capabilities": list(record.capabilities),
            "vector_width": record.vector_width,
            "max_batch": record.max_batch,
            "registered_ns": record.registered_ns,
            "last_seen_ns": record.last_seen_ns,
        }

    @staticmethod
    def _task_store_view(record: TaskRecord) -> dict[str, Any]:
        return {
            "task_id": record.task_id,
            "species": record.species,
            "payload": record.payload,
            "task_commitment": record.task_commitment,
            "created_ns": record.created_ns,
            "state": record.state,
            "lease_id": record.lease_id,
            "leased_to": record.leased_to,
            "lease_expires_ns": record.lease_expires_ns,
            "result": record.result,
            "result_commitment": record.result_commitment,
        }

    @staticmethod
    def _lease_store_view(record: LeaseRecord) -> dict[str, Any]:
        return {
            "lease_id": record.lease_id,
            "worker_id": record.worker_id,
            "species": record.species,
            "task_ids": list(record.task_ids),
            "issued_ns": record.issued_ns,
            "expires_ns": record.expires_ns,
        }

    def register_worker(
        self,
        worker_id: str,
        species: Iterable[str],
        *,
        capabilities: Iterable[str] = (),
        vector_width: int = 8,
        max_batch: int = 128,
    ) -> dict[str, Any]:
        result = super().register_worker(
            worker_id,
            species,
            capabilities=capabilities,
            vector_width=vector_width,
            max_batch=max_batch,
        )
        wid = _normalize_id(worker_id, field="worker_id")
        self._store.save_worker(wid, self._worker_store_view(self._workers[wid]))
        return result

    def heartbeat(self, worker_id: str) -> dict[str, Any]:
        result = super().heartbeat(worker_id)
        wid = _normalize_id(worker_id, field="worker_id")
        self._store.save_worker(wid, self._worker_store_view(self._workers[wid]))
        return result

    def enqueue(
        self,
        species: str,
        payload: Mapping[str, Any],
        *,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        result = super().enqueue(species, payload, task_id=task_id)
        tid = str(result["task_id"])
        self._store.save_task(tid, self._task_store_view(self._tasks[tid]))
        return result

    def claim(
        self,
        worker_id: str,
        *,
        species: str | None = None,
        limit: int | None = None,
        lease_seconds: int | None = None,
    ) -> dict[str, Any]:
        result = super().claim(
            worker_id,
            species=species,
            limit=limit,
            lease_seconds=lease_seconds,
        )
        wid = _normalize_id(worker_id, field="worker_id")
        self._store.save_worker(wid, self._worker_store_view(self._workers[wid]))
        lease_id = result.get("lease_id")
        if lease_id:
            lease = self._leases[str(lease_id)]
            self._store.save_lease(lease.lease_id, self._lease_store_view(lease))
            for task_id in lease.task_ids:
                self._store.save_task(task_id, self._task_store_view(self._tasks[task_id]))
        return result

    def submit(
        self,
        worker_id: str,
        lease_id: str,
        results: Iterable[Mapping[str, Any]],
    ) -> dict[str, Any]:
        lid = _normalize_id(lease_id, field="lease_id")
        # Capture task ids before super() consumes the lease.
        lease = self._leases.get(lid)
        task_ids = tuple(lease.task_ids) if lease is not None else ()
        result = super().submit(worker_id, lease_id, results)
        wid = _normalize_id(worker_id, field="worker_id")
        self._store.save_worker(wid, self._worker_store_view(self._workers[wid]))
        for task_id in task_ids:
            self._store.save_task(task_id, self._task_store_view(self._tasks[task_id]))
        self._store.delete_lease(lid)
        return result

    def _reap_expired(self, now_ns: int) -> None:
        before = {lease_id: tuple(lease.task_ids) for lease_id, lease in self._leases.items()}
        super()._reap_expired(now_ns)
        if not hasattr(self, "_store"):
            return
        expired = set(before) - set(self._leases)
        for lease_id in expired:
            self._store.delete_lease(lease_id)
            for task_id in before[lease_id]:
                task = self._tasks.get(task_id)
                if task is not None:
                    self._store.save_task(task_id, self._task_store_view(task))

    def queue_status(self) -> dict[str, Any]:
        result = super().queue_status()
        result["state_persistence"] = "SQLITE_WAL_V0_3"
        result["store"] = self._store.stats()
        return result

    def close(self) -> None:
        self._store.close()
