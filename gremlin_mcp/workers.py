from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from threading import RLock
import time
from typing import Any, Iterable, Mapping
import uuid

from tools.gremlin_bestiary_orbital_scheduler_v02 import PROFILES, service_omega
from tools.gremlin_bestiary_vector_species_v03 import lane_width

WORKER_SCHEMA = "GREMLIN_MCP_WORKER_ABI_V0_2"
WORKER_ABI_VERSION = "0.2.0"
COMMITMENT_DOMAIN = b"GREMLIN-MCP-WORKER-ABI/v0.2\x00"

# Capture and routing remain GREMLIN-core stages. Scheduler-backed specialist and
# synthesis roles may be supplied by external MCP workers.
WORKER_SPECIES = tuple(name for name in PROFILES if name != "HUMMINGBIRD")


def _authority_state() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


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
        raise ValueError("value must be finite JSON data") from exc


def _commit(value: Any) -> str:
    return hashlib.blake2b(COMMITMENT_DOMAIN + _canonical(value), digest_size=32).hexdigest()


def _normalize_id(value: str, *, field: str) -> str:
    out = str(value).strip()
    if not out or len(out) > 128:
        raise ValueError(f"{field} must contain 1..128 characters")
    return out


def _normalize_species(values: Iterable[str]) -> tuple[str, ...]:
    names: list[str] = []
    for raw in values:
        name = str(raw).strip().upper()
        if name not in WORKER_SPECIES:
            raise ValueError(f"unsupported worker species: {raw!r}")
        if name not in names:
            names.append(name)
    if not names:
        raise ValueError("at least one worker species is required")
    return tuple(names)


@dataclass
class WorkerRecord:
    worker_id: str
    species: tuple[str, ...]
    capabilities: tuple[str, ...]
    vector_width: int
    max_batch: int
    registered_ns: int
    last_seen_ns: int


@dataclass
class TaskRecord:
    task_id: str
    species: str
    payload: dict[str, Any]
    task_commitment: str
    created_ns: int
    state: str = "QUEUED"
    lease_id: str | None = None
    leased_to: str | None = None
    lease_expires_ns: int | None = None
    result: Any = None
    result_commitment: str | None = None


@dataclass
class LeaseRecord:
    lease_id: str
    worker_id: str
    species: str
    task_ids: tuple[str, ...]
    issued_ns: int
    expires_ns: int


class WorkerBroker:
    """Fail-closed pull broker for external GREMLIN animal workers.

    Workers never receive a callback URL and GREMLIN never initiates network
    requests. A backend registers through MCP, claims a bounded same-species
    batch, computes locally, then submits candidate results against the lease.
    """

    def __init__(self, *, lease_seconds: int = 30, max_pending: int = 10_000) -> None:
        lease = int(lease_seconds)
        pending = int(max_pending)
        if lease <= 0 or lease > 300:
            raise ValueError("lease_seconds must be in 1..300")
        if pending <= 0:
            raise ValueError("max_pending must be positive")
        self._lease_seconds = lease
        self._max_pending = pending
        self._workers: dict[str, WorkerRecord] = {}
        self._tasks: dict[str, TaskRecord] = {}
        self._leases: dict[str, LeaseRecord] = {}
        self._lock = RLock()

    def register_worker(
        self,
        worker_id: str,
        species: Iterable[str],
        *,
        capabilities: Iterable[str] = (),
        vector_width: int = 8,
        max_batch: int = 128,
    ) -> dict[str, Any]:
        wid = _normalize_id(worker_id, field="worker_id")
        names = _normalize_species(species)
        caps = tuple(sorted({_normalize_id(c, field="capability") for c in capabilities}))
        vw = int(vector_width)
        batch = int(max_batch)
        if vw <= 0 or vw > 1024:
            raise ValueError("vector_width must be in 1..1024")
        if batch <= 0 or batch > 128:
            raise ValueError("max_batch must be in 1..128")
        now = time.time_ns()
        with self._lock:
            old = self._workers.get(wid)
            registered = old.registered_ns if old is not None else now
            record = WorkerRecord(wid, names, caps, vw, batch, registered, now)
            self._workers[wid] = record
        return self._worker_view(record)

    def heartbeat(self, worker_id: str) -> dict[str, Any]:
        wid = _normalize_id(worker_id, field="worker_id")
        with self._lock:
            record = self._require_worker(wid)
            record.last_seen_ns = time.time_ns()
            return self._worker_view(record)

    def list_workers(self) -> dict[str, Any]:
        with self._lock:
            workers = [self._worker_view(self._workers[k]) for k in sorted(self._workers)]
        return {
            "schema": WORKER_SCHEMA,
            "workers": workers,
            "worker_count": len(workers),
            "authority": _authority_state(),
        }

    def enqueue(self, species: str, payload: Mapping[str, Any], *, task_id: str | None = None) -> dict[str, Any]:
        name = str(species).strip().upper()
        if name not in WORKER_SPECIES:
            raise ValueError(f"unsupported worker species: {species!r}")
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be a mapping")
        body = dict(payload)
        _canonical(body)
        tid = _normalize_id(task_id, field="task_id") if task_id is not None else uuid.uuid4().hex
        now = time.time_ns()
        core = {
            "schema": WORKER_SCHEMA,
            "task_id": tid,
            "species": name,
            "payload": body,
        }
        commitment = _commit(core)
        with self._lock:
            self._reap_expired(now)
            old = self._tasks.get(tid)
            if old is not None:
                if old.task_commitment != commitment:
                    raise ValueError("task_id already exists with different content")
                return self._task_view(old, include_payload=True)
            unfinished = sum(task.state != "DONE" for task in self._tasks.values())
            if unfinished >= self._max_pending:
                raise RuntimeError("GREMLIN worker queue is full")
            record = TaskRecord(tid, name, body, commitment, now)
            self._tasks[tid] = record
            return self._task_view(record, include_payload=True)

    def claim(
        self,
        worker_id: str,
        *,
        species: str | None = None,
        limit: int | None = None,
        lease_seconds: int | None = None,
    ) -> dict[str, Any]:
        wid = _normalize_id(worker_id, field="worker_id")
        now = time.time_ns()
        with self._lock:
            self._reap_expired(now)
            worker = self._require_worker(wid)
            worker.last_seen_ns = now
            if species is None:
                candidates = tuple(
                    sorted(worker.species, key=lambda name: (-service_omega(PROFILES[name]), name))
                )
            else:
                requested = str(species).strip().upper()
                if requested not in worker.species:
                    raise ValueError("worker is not registered for requested species")
                candidates = (requested,)

            selected_species: str | None = None
            pending: list[TaskRecord] = []
            for name in candidates:
                rows = [
                    task
                    for task in self._tasks.values()
                    if task.species == name and task.state == "QUEUED"
                ]
                if rows:
                    selected_species = name
                    pending = sorted(rows, key=lambda task: (task.created_ns, task.task_id))
                    break

            if selected_species is None:
                return {
                    "schema": WORKER_SCHEMA,
                    "worker_id": wid,
                    "lease_id": None,
                    "species": None,
                    "tasks": [],
                    "authority": _authority_state(),
                }

            lane = lane_width(selected_species, vector_width=worker.vector_width)
            requested_limit = worker.max_batch if limit is None else int(limit)
            if requested_limit <= 0:
                raise ValueError("limit must be positive")
            batch_size = min(requested_limit, worker.max_batch, lane, len(pending))
            ttl = self._lease_seconds if lease_seconds is None else int(lease_seconds)
            if ttl <= 0 or ttl > 300:
                raise ValueError("lease_seconds must be in 1..300")
            lease_id = uuid.uuid4().hex
            expires = now + ttl * 1_000_000_000
            chosen = pending[:batch_size]
            for task in chosen:
                task.state = "LEASED"
                task.lease_id = lease_id
                task.leased_to = wid
                task.lease_expires_ns = expires
            lease = LeaseRecord(
                lease_id,
                wid,
                selected_species,
                tuple(task.task_id for task in chosen),
                now,
                expires,
            )
            self._leases[lease_id] = lease
            return {
                "schema": WORKER_SCHEMA,
                "worker_id": wid,
                "lease_id": lease_id,
                "species": selected_species,
                "issued_ns": now,
                "expires_ns": expires,
                "lane_width": lane,
                "batch_size": batch_size,
                "omega": service_omega(PROFILES[selected_species]),
                "tasks": [self._task_view(task, include_payload=True) for task in chosen],
                "authority": _authority_state(),
            }

    def submit(self, worker_id: str, lease_id: str, results: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
        wid = _normalize_id(worker_id, field="worker_id")
        lid = _normalize_id(lease_id, field="lease_id")
        rows = list(results)
        now = time.time_ns()
        with self._lock:
            self._reap_expired(now)
            self._require_worker(wid)
            lease = self._leases.get(lid)
            if lease is None:
                raise ValueError("unknown or expired lease")
            if lease.worker_id != wid:
                raise ValueError("lease belongs to another worker")
            expected = set(lease.task_ids)
            supplied: set[str] = set()
            normalized: list[tuple[str, Any]] = []
            for row in rows:
                if not isinstance(row, Mapping):
                    raise ValueError("each result must be a mapping")
                tid = _normalize_id(str(row.get("task_id", "")), field="task_id")
                if tid in supplied:
                    raise ValueError("duplicate task result")
                supplied.add(tid)
                if row.get("status", "CANDIDATE") != "CANDIDATE":
                    raise ValueError("worker results must remain CANDIDATE")
                if "output" not in row:
                    raise ValueError("worker result requires output")
                output = row["output"]
                _canonical(output)
                normalized.append((tid, output))
            if supplied != expected:
                raise ValueError("lease submission must cover the exact claimed task set")

            receipt_core = {
                "schema": WORKER_SCHEMA,
                "worker_id": wid,
                "lease_id": lid,
                "species": lease.species,
                "task_ids": list(lease.task_ids),
                "submitted_ns": now,
                "status": "CANDIDATE",
            }
            receipt_commitment = _commit(receipt_core)
            by_id = dict(normalized)
            for tid in lease.task_ids:
                task = self._tasks[tid]
                output = by_id[tid]
                task.result = output
                task.result_commitment = _commit(
                    {
                        "task_commitment": task.task_commitment,
                        "worker_id": wid,
                        "output": output,
                        "status": "CANDIDATE",
                    }
                )
                task.state = "DONE"
                task.lease_id = None
                task.leased_to = None
                task.lease_expires_ns = None
            del self._leases[lid]
            self._workers[wid].last_seen_ns = now
            return {
                **receipt_core,
                "receipt_commitment": receipt_commitment,
                "result_commitments": {
                    tid: self._tasks[tid].result_commitment for tid in lease.task_ids
                },
                "authority": _authority_state(),
            }

    def task_result(self, task_id: str) -> dict[str, Any]:
        tid = _normalize_id(task_id, field="task_id")
        now = time.time_ns()
        with self._lock:
            self._reap_expired(now)
            task = self._tasks.get(tid)
            if task is None:
                raise ValueError("unknown task_id")
            return self._task_view(task, include_payload=False, include_result=True)

    def queue_status(self) -> dict[str, Any]:
        now = time.time_ns()
        with self._lock:
            self._reap_expired(now)
            counts: dict[str, dict[str, int]] = {
                name: {"QUEUED": 0, "LEASED": 0, "DONE": 0} for name in WORKER_SPECIES
            }
            for task in self._tasks.values():
                counts[task.species][task.state] += 1
            return {
                "schema": WORKER_SCHEMA,
                "state_persistence": "PROCESS_MEMORY_V0_2",
                "registered_workers": len(self._workers),
                "active_leases": len(self._leases),
                "tasks": counts,
                "authority": _authority_state(),
            }

    def _require_worker(self, worker_id: str) -> WorkerRecord:
        worker = self._workers.get(worker_id)
        if worker is None:
            raise ValueError("unknown worker_id")
        return worker

    def _reap_expired(self, now_ns: int) -> None:
        expired = [lid for lid, lease in self._leases.items() if lease.expires_ns <= now_ns]
        for lid in expired:
            lease = self._leases.pop(lid)
            for tid in lease.task_ids:
                task = self._tasks.get(tid)
                if task is None or task.state != "LEASED" or task.lease_id != lid:
                    continue
                task.state = "QUEUED"
                task.lease_id = None
                task.leased_to = None
                task.lease_expires_ns = None

    @staticmethod
    def _worker_view(record: WorkerRecord) -> dict[str, Any]:
        return {
            "schema": WORKER_SCHEMA,
            **asdict(record),
            "authority": _authority_state(),
        }

    @staticmethod
    def _task_view(
        record: TaskRecord,
        *,
        include_payload: bool,
        include_result: bool = False,
    ) -> dict[str, Any]:
        out: dict[str, Any] = {
            "schema": WORKER_SCHEMA,
            "task_id": record.task_id,
            "species": record.species,
            "task_commitment": record.task_commitment,
            "created_ns": record.created_ns,
            "state": record.state,
            "lease_id": record.lease_id,
            "leased_to": record.leased_to,
            "lease_expires_ns": record.lease_expires_ns,
            "result_commitment": record.result_commitment,
            "authority": _authority_state(),
        }
        if include_payload:
            out["payload"] = record.payload
        if include_result and record.state == "DONE":
            out["status"] = "CANDIDATE"
            out["result"] = record.result
        return out


broker = WorkerBroker()
