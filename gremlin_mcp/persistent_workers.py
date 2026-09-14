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
    _normalize_species,
    _strict_int,
)


def _stored_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"persisted {field} must be an object")
    return value


def _stored_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"persisted {field} must be a list")
    return value


def _stored_optional_id(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _normalize_id(value, field=field)  # type: ignore[arg-type]


def _stored_commitment(value: Any, field: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"persisted {field} must be a 64-character hex commitment")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"persisted {field} must be hexadecimal") from exc
    return value


def _stored_capabilities(value: Any) -> tuple[str, ...]:
    rows = _stored_list(value, "worker.capabilities")
    return tuple(_normalize_id(item, field="capability") for item in rows)  # type: ignore[arg-type]


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
            workers = _stored_mapping(snapshot.get("workers"), "workers table")
            tasks = _stored_mapping(snapshot.get("tasks"), "tasks table")
            leases = _stored_mapping(snapshot.get("leases"), "leases table")

            self._workers = {}
            for worker_key, raw_row in workers.items():
                key = _normalize_id(worker_key, field="worker store key")  # type: ignore[arg-type]
                row = _stored_mapping(raw_row, f"worker[{key}]")
                worker_id = _normalize_id(row.get("worker_id"), field="worker_id")  # type: ignore[arg-type]
                species_rows = _stored_list(row.get("species"), f"worker[{key}].species")
                species = _normalize_species(species_rows)
                record = WorkerRecord(
                    worker_id=worker_id,
                    species=species,
                    capabilities=_stored_capabilities(row.get("capabilities")),
                    vector_width=_strict_int(row.get("vector_width"), field="vector_width", minimum=1, maximum=1024),
                    max_batch=_strict_int(row.get("max_batch"), field="max_batch", minimum=1, maximum=128),
                    registered_ns=_strict_int(row.get("registered_ns"), field="registered_ns", minimum=0),
                    last_seen_ns=_strict_int(row.get("last_seen_ns"), field="last_seen_ns", minimum=0),
                )
                self._workers[key] = record

            self._tasks = {}
            for task_key, raw_row in tasks.items():
                key = _normalize_id(task_key, field="task store key")  # type: ignore[arg-type]
                row = _stored_mapping(raw_row, f"task[{key}]")
                task_id = _normalize_id(row.get("task_id"), field="task_id")  # type: ignore[arg-type]
                raw_species = row.get("species")
                if not isinstance(raw_species, str):
                    raise ValueError("persisted task species must be a string")
                species = _normalize_species([raw_species])[0]
                payload = dict(_stored_mapping(row.get("payload"), f"task[{key}].payload"))
                _commit(payload)  # also proves finite JSON serializability
                state = row.get("state", "QUEUED")
                if not isinstance(state, str) or state not in {"QUEUED", "LEASED", "DONE"}:
                    raise ValueError("persisted task state is invalid")
                lease_expires = row.get("lease_expires_ns")
                record = TaskRecord(
                    task_id=task_id,
                    species=species,
                    payload=payload,
                    task_commitment=str(_stored_commitment(row.get("task_commitment"), "task_commitment")),
                    created_ns=_strict_int(row.get("created_ns"), field="created_ns", minimum=0),
                    state=state,
                    lease_id=_stored_optional_id(row.get("lease_id"), "lease_id"),
                    leased_to=_stored_optional_id(row.get("leased_to"), "leased_to"),
                    lease_expires_ns=(
                        None
                        if lease_expires is None
                        else _strict_int(lease_expires, field="lease_expires_ns", minimum=0)
                    ),
                    result=row.get("result"),
                    result_commitment=_stored_commitment(
                        row.get("result_commitment"), "result_commitment", optional=True
                    ),
                )
                self._tasks[key] = record

            self._leases = {}
            for lease_key, raw_row in leases.items():
                key = _normalize_id(lease_key, field="lease store key")  # type: ignore[arg-type]
                row = _stored_mapping(raw_row, f"lease[{key}]")
                raw_species = row.get("species")
                if not isinstance(raw_species, str):
                    raise ValueError("persisted lease species must be a string")
                task_ids = tuple(
                    _normalize_id(item, field="task_id")  # type: ignore[arg-type]
                    for item in _stored_list(row.get("task_ids"), f"lease[{key}].task_ids")
                )
                if not task_ids:
                    raise ValueError("persisted lease must reference at least one task")
                record = LeaseRecord(
                    lease_id=_normalize_id(row.get("lease_id"), field="lease_id"),  # type: ignore[arg-type]
                    worker_id=_normalize_id(row.get("worker_id"), field="worker_id"),  # type: ignore[arg-type]
                    species=_normalize_species([raw_species])[0],
                    task_ids=task_ids,
                    issued_ns=_strict_int(row.get("issued_ns"), field="issued_ns", minimum=0),
                    expires_ns=_strict_int(row.get("expires_ns"), field="expires_ns", minimum=0),
                )
                self._leases[key] = record

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
            if worker.last_seen_ns < worker.registered_ns:
                raise ValueError("persisted worker last_seen_ns predates registration")
        leased_task_ids: set[str] = set()
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
            if task.state == "QUEUED":
                if task.lease_id is not None or task.leased_to is not None or task.lease_expires_ns is not None:
                    raise ValueError("queued persisted task contains lease lineage")
                if task.result_commitment is not None:
                    raise ValueError("queued persisted task contains result commitment")
            elif task.state == "LEASED":
                if task.lease_id is None or task.leased_to is None or task.lease_expires_ns is None:
                    raise ValueError("leased persisted task is missing lease lineage")
                if task.result_commitment is not None:
                    raise ValueError("leased persisted task contains result commitment")
                leased_task_ids.add(task.task_id)
            elif task.state == "DONE":
                if task.lease_id is not None or task.leased_to is not None or task.lease_expires_ns is not None:
                    raise ValueError("completed persisted task still contains lease lineage")
                if task.result_commitment is None:
                    raise ValueError("completed persisted task is missing result commitment")
            else:
                raise ValueError("persisted task state is invalid")
        lease_task_ids: set[str] = set()
        for key, lease in self._leases.items():
            if key != lease.lease_id:
                raise ValueError("lease store key mismatch")
            if lease.expires_ns <= lease.issued_ns:
                raise ValueError("persisted lease expiry must follow issuance")
            worker = self._workers.get(lease.worker_id)
            if worker is None or lease.species not in worker.species:
                raise ValueError("persisted lease worker/species mismatch")
            for task_id in lease.task_ids:
                if task_id in lease_task_ids:
                    raise ValueError("persisted task appears in multiple leases")
                lease_task_ids.add(task_id)
                task = self._tasks.get(task_id)
                if task is None:
                    raise ValueError("persisted lease references missing task")
                if (
                    task.state != "LEASED"
                    or task.lease_id != lease.lease_id
                    or task.leased_to != lease.worker_id
                    or task.species != lease.species
                    or task.lease_expires_ns != lease.expires_ns
                ):
                    raise ValueError("persisted lease/task lineage mismatch")
        if leased_task_ids != lease_task_ids:
            raise ValueError("persisted leased task set does not match active leases")

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
        tid = _normalize_id(result.get("task_id"), field="task_id")  # type: ignore[arg-type]
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
        if lease_id is not None:
            lid = _normalize_id(lease_id, field="lease_id")  # type: ignore[arg-type]
            lease = self._leases[lid]
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
                if task is None:
                    raise RuntimeError("expired persisted lease task disappeared during reap")
                self._store.save_task(task_id, self._task_store_view(task))

    def queue_status(self) -> dict[str, Any]:
        result = super().queue_status()
        result["state_persistence"] = "SQLITE_WAL_V0_3"
        result["store"] = self._store.stats()
        return result

    def close(self) -> None:
        self._store.close()
