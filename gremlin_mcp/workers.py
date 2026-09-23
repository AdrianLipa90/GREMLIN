from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from itertools import islice
import hashlib
import heapq
import json
from threading import RLock
import time
from typing import Any, Iterable, Mapping
import uuid

from gremlin_mcp.orchorbital_context import (
    BUNDLE_PAYLOAD_KEY,
    BUNDLE_REF_PAYLOAD_KEY,
    PACKET_PAYLOAD_KEY,
    apply_context_packet,
    bundle_context_packets,
    context_bundle_reference,
    reduce_context_packet,
)
from gremlin_mcp.memory_capabilities import (
    authorize_memory_requests,
    validate_task_authorization_bundle,
)

from tools.gremlin_bestiary_orbital_scheduler_v02 import PROFILES, service_omega
from tools.gremlin_bestiary_vector_species_v03 import lane_width
from tools.gremlin_geometry_context_pack_v01 import pack_context
from tools.gremlin_geometry_phase_scheduler_v01 import (
    MODE as GEOMETRY_SCHEDULER_MODE,
    NUMPY_DISTANCE_KERNEL_CANDIDATE,
    SCALAR_DISTANCE_KERNEL,
    SCHEDULER_SPECIES,
    choose_species,
    geometry_lane_width,
    queue_metrics,
    scheduler_manifest,
    select_batch,
    task_phase_state,
)

WORKER_SCHEMA = "GREMLIN_MCP_WORKER_ABI_V0_2"
WORKER_ABI_VERSION = "0.2.6"
COMMITMENT_DOMAIN = b"GREMLIN-MCP-WORKER-ABI/v0.2\x00"
TRANSPORT_COMMITMENT_DOMAIN = b"GREMLIN-MCP-WORKER-TRANSPORT/v0.2\x00"
MAX_IDENTIFIER_CHARS = 128
MAX_WORKER_VECTOR_WIDTH = 1024
MAX_WORKER_BATCH = 128
MAX_LEASE_SECONDS = 300
MAX_CONTEXT_FRAME_CACHE_KEYS = 4096
MAX_CONTEXT_INDEX_DEPTH = 8
MAX_CONTEXT_FAIRNESS_WINDOW = 32

MEMORY_REQUESTS_KEY = "_gremlin_memory_requests"
MEMORY_AUTHORIZATION_KEY = "_gremlin_memory_authorization"

# Capture/routing/root/actuation remain GREMLIN-core boundaries. All remaining
# Bestiary roles may participate in the geometry/phase/state worker scheduler.
WORKER_SPECIES = tuple(SCHEDULER_SPECIES)


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



def worker_transport_commitment(
    *,
    task_id: str,
    species: str,
    task_commitment: str,
    payload: Mapping[str, Any],
    bundle_commitment: str | None = None,
) -> str:
    """Bind one delivered transport projection to its canonical task."""

    tid = _normalize_id(task_id, field="task_id")
    if not isinstance(species, str):
        raise ValueError("species must be a string")
    name = species.strip().upper()
    if name not in WORKER_SPECIES:
        raise ValueError(f"unsupported worker species: {species!r}")
    commitment = _normalize_id(task_commitment, field="task_commitment")
    if len(commitment) != 64:
        raise ValueError("task_commitment must be a 64-character commitment")
    try:
        int(commitment, 16)
    except ValueError as exc:
        raise ValueError("task_commitment must be hexadecimal") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be a mapping")
    bundle = None
    if bundle_commitment is not None:
        bundle = _normalize_id(bundle_commitment, field="bundle_commitment")
        if len(bundle) != 64:
            raise ValueError("bundle_commitment must be a 64-character commitment")
        try:
            int(bundle, 16)
        except ValueError as exc:
            raise ValueError("bundle_commitment must be hexadecimal") from exc
    core = {
        "schema": WORKER_SCHEMA,
        "task_id": tid,
        "species": name,
        "task_commitment": commitment,
        "payload": dict(payload),
        "bundle_commitment": bundle,
    }
    return hashlib.blake2b(
        TRANSPORT_COMMITMENT_DOMAIN + _canonical(core),
        digest_size=32,
    ).hexdigest()


def _strict_int(value: Any, *, field: str, minimum: int, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        if maximum is None:
            raise ValueError(f"{field} must be >= {minimum}")
        raise ValueError(f"{field} must be in {minimum}..{maximum}")
    return value


def _normalize_id(value: str, *, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    out = value.strip()
    if not out or len(out) > MAX_IDENTIFIER_CHARS:
        raise ValueError(f"{field} must contain 1..{MAX_IDENTIFIER_CHARS} characters")
    return out


def _normalize_species(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError("species must be an iterable of species names, not a string")
    try:
        raw_values = list(values)
    except TypeError as exc:
        raise ValueError("species must be iterable") from exc
    names: list[str] = []
    for raw in raw_values:
        if not isinstance(raw, str):
            raise ValueError("worker species names must be strings")
        name = raw.strip().upper()
        if name not in WORKER_SPECIES:
            raise ValueError(f"unsupported worker species: {raw!r}")
        if name not in names:
            names.append(name)
    if not names:
        raise ValueError("at least one worker species is required")
    return tuple(names)


def _validate_canonical_context_payload(payload: Mapping[str, Any]) -> None:
    """Admit only full, self-contained orbital context into canonical tasks."""

    if BUNDLE_PAYLOAD_KEY in payload or BUNDLE_REF_PAYLOAD_KEY in payload:
        raise ValueError(
            "orchorbital context bundle/reference keys are broker-owned transport fields"
        )
    packet = payload.get(PACKET_PAYLOAD_KEY)
    if packet is None:
        return
    if not isinstance(packet, Mapping):
        raise ValueError("orchorbital context packet must be an object")
    if packet.get("required_base_frame_commitment") is not None:
        raise ValueError("canonical task context packet must be self-contained")
    apply_context_packet(packet)


def _receiver_queue_locality(
    affinity_by_task: Mapping[str, Iterable[str]],
    known_frames: Iterable[str],
) -> float:
    known = set(known_frames)
    if not known:
        return 0.0
    scores: list[float] = []
    for values in affinity_by_task.values():
        signature = set(values)
        if not signature:
            continue
        scores.append(len(signature & known) / len(signature))
    return 0.0 if not scores else max(scores)


def _context_affinity_for_payload(
    payload: Mapping[str, Any],
) -> tuple[str, ...]:
    packet = payload.get(PACKET_PAYLOAD_KEY)
    if not isinstance(packet, Mapping):
        return ()
    frames = packet.get("frames")
    if not isinstance(frames, list):
        return ()
    commitments: list[str] = []
    for frame in frames:
        if not isinstance(frame, Mapping):
            continue
        commitment = frame.get("frame_commitment")
        if not isinstance(commitment, str) or len(commitment) != 64:
            continue
        try:
            int(commitment, 16)
        except ValueError:
            continue
        if commitment not in commitments:
            commitments.append(commitment)
    return tuple(commitments)


def _context_affinity_by_task(
    rows: Iterable[Mapping[str, Any]],
) -> dict[str, tuple[str, ...]]:
    """Extract privacy-safe context ancestry commitments for scheduler locality."""

    out: dict[str, tuple[str, ...]] = {}
    for row in rows:
        task_id = row.get("task_id")
        payload = row.get("payload")
        if not isinstance(task_id, str) or not isinstance(payload, Mapping):
            continue
        affinity = _context_affinity_for_payload(payload)
        if affinity:
            out[task_id] = affinity
    return out


def _normalize_context_frames(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError("known_context_frames must be an iterable of commitments")
    try:
        raw_values = list(values)
    except TypeError as exc:
        raise ValueError("known_context_frames must be iterable") from exc
    if len(raw_values) > MAX_CONTEXT_FRAME_CACHE_KEYS:
        raise ValueError(
            f"known_context_frames exceeds {MAX_CONTEXT_FRAME_CACHE_KEYS} commitments"
        )
    out: list[str] = []
    for index, raw in enumerate(raw_values):
        if not isinstance(raw, str) or len(raw) != 64:
            raise ValueError(
                f"known_context_frames[{index}] must be a 64-character hex commitment"
            )
        try:
            int(raw, 16)
        except ValueError as exc:
            raise ValueError(
                f"known_context_frames[{index}] must be hexadecimal"
            ) from exc
        if raw not in out:
            out.append(raw)
    return tuple(out)


def _normalize_capabilities(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError("capabilities must be an iterable of capability names, not a string")
    try:
        raw_values = list(values)
    except TypeError as exc:
        raise ValueError("capabilities must be iterable") from exc
    return tuple(sorted({_normalize_id(value, field="capability") for value in raw_values}))


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

    def __init__(
        self,
        *,
        lease_seconds: int = 30,
        max_pending: int = 10_000,
        vector_distance_shadow: bool = False,
    ) -> None:
        lease = _strict_int(lease_seconds, field="lease_seconds", minimum=1, maximum=300)
        pending = _strict_int(max_pending, field="max_pending", minimum=1)
        if not isinstance(vector_distance_shadow, bool):
            raise ValueError("vector_distance_shadow must be boolean")
        self._lease_seconds = lease
        self._max_pending = pending
        self._vector_distance_shadow = vector_distance_shadow
        self._workers: dict[str, WorkerRecord] = {}
        self._tasks: dict[str, TaskRecord] = {}
        self._leases: dict[str, LeaseRecord] = {}
        self._lease_expiry_heap: list[tuple[int, str]] = []
        self._queued_by_species: dict[str, dict[str, None]] = {
            name: {} for name in WORKER_SPECIES
        }
        self._task_context_affinity: dict[str, tuple[str, ...]] = {}
        self._queued_by_context_frame: dict[
            str, dict[str, dict[str, None]]
        ] = {name: {} for name in WORKER_SPECIES}
        self._task_phase_state: dict[str, Any] = {}
        self._unfinished_count = 0
        self._lock = RLock()

    def _index_task_metadata(self, task: TaskRecord) -> None:
        scheduler_row = self._scheduler_task_view(task)
        self._task_phase_state[task.task_id] = task_phase_state(scheduler_row)
        affinity = _context_affinity_for_payload(task.payload)
        if affinity:
            self._task_context_affinity[task.task_id] = affinity
        else:
            self._task_context_affinity.pop(task.task_id, None)

    def _context_index_keys(self, task_id: str) -> tuple[str, ...]:
        affinity = self._task_context_affinity.get(task_id, ())
        if not affinity:
            return ()
        return tuple(affinity[-MAX_CONTEXT_INDEX_DEPTH:])

    def _queue_index_add(self, task: TaskRecord) -> None:
        if task.state != "QUEUED":
            raise RuntimeError("only queued tasks may enter the queue index")
        bucket = self._queued_by_species.get(task.species)
        if bucket is None:
            raise RuntimeError("task species has no queue index")
        bucket[task.task_id] = None

        context_index = self._queued_by_context_frame.get(task.species)
        if context_index is None:
            raise RuntimeError("task species has no context queue index")
        for frame_commitment in self._context_index_keys(task.task_id):
            context_index.setdefault(frame_commitment, {})[task.task_id] = None

    def _queue_index_remove(self, task: TaskRecord) -> None:
        bucket = self._queued_by_species.get(task.species)
        if bucket is None:
            raise RuntimeError("task species has no queue index")
        bucket.pop(task.task_id, None)

        context_index = self._queued_by_context_frame.get(task.species)
        if context_index is None:
            raise RuntimeError("task species has no context queue index")
        for frame_commitment in self._context_index_keys(task.task_id):
            frame_bucket = context_index.get(frame_commitment)
            if frame_bucket is None:
                continue
            frame_bucket.pop(task.task_id, None)
            if not frame_bucket:
                context_index.pop(frame_commitment, None)

    def _rebuild_lease_heap(self) -> None:
        self._lease_expiry_heap = [
            (lease.expires_ns, lease_id)
            for lease_id, lease in self._leases.items()
        ]
        heapq.heapify(self._lease_expiry_heap)

    def _maybe_compact_lease_heap(self) -> None:
        threshold = max(64, 2 * len(self._leases) + 16)
        if len(self._lease_expiry_heap) > threshold:
            self._rebuild_lease_heap()

    def _rebuild_indexes(self) -> None:
        self._queued_by_species = {name: {} for name in WORKER_SPECIES}
        self._task_context_affinity = {}
        self._queued_by_context_frame = {
            name: {} for name in WORKER_SPECIES
        }
        self._task_phase_state = {}
        self._unfinished_count = 0
        for task in self._tasks.values():
            self._index_task_metadata(task)
            if task.state != "DONE":
                self._unfinished_count += 1
            if task.state == "QUEUED":
                self._queue_index_add(task)
        self._rebuild_lease_heap()

    def _queued_rows(self, species: str) -> list[dict[str, Any]]:
        bucket = self._queued_by_species.get(species)
        if bucket is None:
            raise RuntimeError("species has no queue index")
        rows: list[dict[str, Any]] = []
        for task_id in tuple(bucket):
            task = self._tasks.get(task_id)
            if task is None:
                raise RuntimeError("queue index references a missing task")
            if task.species != species or task.state != "QUEUED":
                raise RuntimeError("queue index/task state drift detected")
            self._validate_task_memory_authorization(task)
            rows.append(self._scheduler_task_view(task))
        return rows

    def _indexed_candidate_rows(
        self,
        species: str,
        known_frames: tuple[str, ...],
        *,
        requested_limit: int,
    ) -> tuple[list[dict[str, Any]], dict[str, object]]:
        """Return a bounded warm-context candidate set plus oldest fairness rows.

        This is activated only for an explicitly requested species. Cold-start
        and multi-species claims retain the complete species-queue semantics.
        """

        species_bucket = self._queued_by_species.get(species)
        context_index = self._queued_by_context_frame.get(species)
        if species_bucket is None or context_index is None:
            raise RuntimeError("species routing indexes are unavailable")
        queue_count = len(species_bucket)
        fallback = {
            "active": False,
            "hit": False,
            "species_queue_count": queue_count,
            "indexed_local_count": 0,
            "fairness_candidate_count": 0,
            "candidate_count": queue_count,
            "candidate_scan_reduction_proxy": 0.0,
            "selected_context_frame_commitment": None,
            "max_index_depth": MAX_CONTEXT_INDEX_DEPTH,
        }
        if not known_frames or queue_count <= 1:
            return self._queued_rows(species), fallback

        hits: list[tuple[int, str, dict[str, None]]] = []
        for frame_commitment in known_frames:
            frame_bucket = context_index.get(frame_commitment)
            if frame_bucket:
                hits.append((len(frame_bucket), frame_commitment, frame_bucket))
        if not hits:
            return self._queued_rows(species), fallback

        local_count, selected_frame, local_bucket = min(
            hits,
            key=lambda row: (row[0], row[1]),
        )
        local_ids = tuple(local_bucket)
        selected: dict[str, None] = {
            task_id: None for task_id in local_ids
        }

        fairness_limit = max(
            4,
            min(MAX_CONTEXT_FAIRNESS_WINDOW, requested_limit),
        )
        fairness_added = 0
        for task_id in islice(species_bucket, 0, queue_count):
            if task_id in selected:
                continue
            selected[task_id] = None
            fairness_added += 1
            if fairness_added >= fairness_limit:
                break

        rows: list[dict[str, Any]] = []
        for task_id in selected:
            task = self._tasks.get(task_id)
            if task is None:
                raise RuntimeError("context queue index references a missing task")
            if task.species != species or task.state != "QUEUED":
                raise RuntimeError("context queue index/task state drift detected")
            self._validate_task_memory_authorization(task)
            rows.append(self._scheduler_task_view(task))

        candidate_count = len(rows)
        reduction = (
            0.0
            if queue_count <= 0
            else 1.0 - candidate_count / queue_count
        )
        return rows, {
            "active": True,
            "hit": True,
            "species_queue_count": queue_count,
            "indexed_local_count": local_count,
            "fairness_candidate_count": fairness_added,
            "candidate_count": candidate_count,
            "candidate_scan_reduction_proxy": reduction,
            "selected_context_frame_commitment": selected_frame,
            "max_index_depth": MAX_CONTEXT_INDEX_DEPTH,
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
        wid = _normalize_id(worker_id, field="worker_id")
        names = _normalize_species(species)
        caps = _normalize_capabilities(capabilities)
        vw = _strict_int(vector_width, field="vector_width", minimum=1, maximum=MAX_WORKER_VECTOR_WIDTH)
        batch = _strict_int(max_batch, field="max_batch", minimum=1, maximum=MAX_WORKER_BATCH)
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
        if not isinstance(species, str):
            raise ValueError("species must be a string")
        name = species.strip().upper()
        if name not in WORKER_SPECIES:
            raise ValueError(f"unsupported worker species: {species!r}")
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be a mapping")
        body = deepcopy(dict(payload))
        if MEMORY_AUTHORIZATION_KEY in body:
            raise ValueError(
                f"{MEMORY_AUTHORIZATION_KEY} is broker-owned and cannot be supplied by callers"
            )
        tid = _normalize_id(task_id, field="task_id") if task_id is not None else uuid.uuid4().hex
        memory_requests = body.pop(MEMORY_REQUESTS_KEY, None)
        if memory_requests is not None:
            authorization = authorize_memory_requests(
                name,
                memory_requests,
                task_id=tid,
            )
            body[MEMORY_AUTHORIZATION_KEY] = authorization
        _validate_canonical_context_payload(body)
        _canonical(body)
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
            if self._unfinished_count >= self._max_pending:
                raise RuntimeError("GREMLIN worker queue is full")
            record = TaskRecord(tid, name, body, commitment, now)
            self._tasks[tid] = record
            self._index_task_metadata(record)
            self._queue_index_add(record)
            self._unfinished_count += 1
            return self._task_view(record, include_payload=True)

    def claim(
        self,
        worker_id: str,
        *,
        species: str | None = None,
        limit: int | None = None,
        lease_seconds: int | None = None,
        known_context_frames: Iterable[str] = (),
    ) -> dict[str, Any]:
        """Claim a bounded same-species batch by geometry, phase and task state.

        FIFO is retained only as a comparison proxy in the scheduler receipt.
        Operational selection is based on T^36 cluster coherence, task state,
        readiness/noise/urgency, and a cadence hint only as a secondary tie-break.
        """
        wid = _normalize_id(worker_id, field="worker_id")
        known_frames = _normalize_context_frames(known_context_frames)
        now = time.time_ns()
        with self._lock:
            self._reap_expired(now)
            worker = self._require_worker(wid)
            worker.last_seen_ns = now

            if species is None:
                candidate_names = tuple(worker.species)
            else:
                if not isinstance(species, str):
                    raise ValueError("species must be a string")
                requested = species.strip().upper()
                if requested not in worker.species:
                    raise ValueError("worker is not registered for requested species")
                candidate_names = (requested,)

            requested_limit = (
                worker.max_batch
                if limit is None
                else _strict_int(limit, field="limit", minimum=1)
            )
            queue_rows: dict[str, list[dict[str, Any]]] = {}
            candidate_scope: dict[str, dict[str, object]] = {}
            explicit_species = species is not None
            for name in candidate_names:
                if explicit_species and known_frames:
                    rows, scope = self._indexed_candidate_rows(
                        name,
                        known_frames,
                        requested_limit=requested_limit,
                    )
                else:
                    rows = self._queued_rows(name)
                    queue_count = len(self._queued_by_species[name])
                    scope = {
                        "active": False,
                        "hit": False,
                        "species_queue_count": queue_count,
                        "indexed_local_count": 0,
                        "fairness_candidate_count": 0,
                        "candidate_count": len(rows),
                        "candidate_scan_reduction_proxy": 0.0,
                        "selected_context_frame_commitment": None,
                        "max_index_depth": MAX_CONTEXT_INDEX_DEPTH,
                    }
                if rows:
                    queue_rows[name] = rows
                    candidate_scope[name] = scope

            cadence_hint = {
                name: service_omega(PROFILES[name])
                for name in candidate_names
                if name in PROFILES
            }
            affinity_by_species = {
                name: {
                    row["task_id"]: self._task_context_affinity[row["task_id"]]
                    for row in rows
                    if row["task_id"] in self._task_context_affinity
                }
                for name, rows in queue_rows.items()
            }
            receiver_locality_hint = {
                name: _receiver_queue_locality(
                    affinity_by_species.get(name, {}),
                    known_frames,
                )
                for name in queue_rows
            }
            selected_species, species_scheduler = choose_species(
                queue_rows,
                now_ns=now,
                cadence_hint=cadence_hint,
                locality_hint=(
                    receiver_locality_hint if known_frames else None
                ),
                precomputed_states=self._task_phase_state,
            )

            if selected_species is None:
                return {
                    "schema": WORKER_SCHEMA,
                    "worker_id": wid,
                    "lease_id": None,
                    "species": None,
                    "tasks": [],
                    "scheduler": species_scheduler,
                    "authority": _authority_state(),
                }

            rows = queue_rows[selected_species]
            species_metrics = species_scheduler.get("queues")
            if not isinstance(species_metrics, Mapping):
                raise RuntimeError("species scheduler metrics are unavailable")
            metrics = species_metrics.get(selected_species)
            if not isinstance(metrics, Mapping):
                raise RuntimeError(
                    "selected species metrics are unavailable from scheduler"
                )
            legacy_cap = (
                lane_width(selected_species, vector_width=worker.vector_width)
                if selected_species in PROFILES
                else min(128, max(1, worker.vector_width * 4))
            )
            lane = geometry_lane_width(
                vector_width=worker.vector_width,
                max_batch=worker.max_batch,
                cluster_coherence=float(metrics["cluster_coherence"]),
                legacy_cap=legacy_cap,
            )
            batch_limit = min(
                requested_limit,
                worker.max_batch,
                lane,
                int(metrics["eligible_count"]),
            )
            context_affinity = affinity_by_species[selected_species]
            centroid = metrics.get("centroid")
            if not isinstance(centroid, list):
                raise RuntimeError("selected species centroid is unavailable")
            selected_ids, batch_scheduler = select_batch(
                rows,
                limit=batch_limit,
                now_ns=now,
                affinity_by_task=context_affinity,
                receiver_known_affinity=known_frames,
                precomputed_states=self._task_phase_state,
                precomputed_centroid=centroid,
                distance_kernel=SCALAR_DISTANCE_KERNEL,
            )
            vector_shadow: dict[str, object] = {
                "enabled": self._vector_distance_shadow,
                "candidate_kernel": NUMPY_DISTANCE_KERNEL_CANDIDATE,
                "decision_kernel": SCALAR_DISTANCE_KERNEL,
                "selection_equivalent": None,
                "candidate_selected_task_ids": None,
            }
            if self._vector_distance_shadow:
                shadow_ids, shadow_receipt = select_batch(
                    rows,
                    limit=batch_limit,
                    now_ns=now,
                    affinity_by_task=context_affinity,
                    receiver_known_affinity=known_frames,
                    precomputed_states=self._task_phase_state,
                    precomputed_centroid=centroid,
                    distance_kernel=NUMPY_DISTANCE_KERNEL_CANDIDATE,
                )
                equivalent = shadow_ids == selected_ids
                vector_shadow = {
                    "enabled": True,
                    "candidate_kernel": NUMPY_DISTANCE_KERNEL_CANDIDATE,
                    "decision_kernel": SCALAR_DISTANCE_KERNEL,
                    "selection_equivalent": equivalent,
                    "candidate_selected_task_ids": list(shadow_ids),
                    "candidate_pairwise_state_distance_evaluations": (
                        shadow_receipt[
                            "greedy_pairwise_state_distance_evaluations"
                        ]
                    ),
                }
                if not equivalent:
                    raise RuntimeError(
                        "scalar/vector scheduler shadow selection mismatch"
                    )
            batch_scheduler["vector_distance_shadow"] = vector_shadow
            if not selected_ids:
                return {
                    "schema": WORKER_SCHEMA,
                    "worker_id": wid,
                    "lease_id": None,
                    "species": selected_species,
                    "tasks": [],
                    "scheduler": {
                        "mode": GEOMETRY_SCHEDULER_MODE,
                        "species_selection": species_scheduler,
                        "batch_selection": batch_scheduler,
                    },
                    "authority": _authority_state(),
                }

            chosen: list[TaskRecord] = []
            for task_id in selected_ids:
                task = self._tasks.get(task_id)
                if (
                    task is None
                    or task.species != selected_species
                    or task.state != "QUEUED"
                    or task_id not in self._queued_by_species[selected_species]
                ):
                    raise RuntimeError("scheduler selection is not present in queue index")
                chosen.append(task)
            batch_size = len(chosen)

            # Build and validate the receiver-specific transport view before
            # mutating any task or lease state. A malformed context packet must
            # never strand a task in LEASED state.
            transport_payloads: dict[str, dict[str, Any]] = {
                task.task_id: deepcopy(task.payload) for task in chosen
            }
            raw_context_packets: dict[str, Mapping[str, Any]] = {}
            for task in chosen:
                raw_packet = task.payload.get(PACKET_PAYLOAD_KEY)
                if raw_packet is None:
                    continue
                if not isinstance(raw_packet, Mapping):
                    raise RuntimeError("orchorbital context packet must be an object")
                raw_context_packets[task.task_id] = raw_packet

            cache_hits = 0
            original_context_bytes = 0
            transported_context_bytes = 0
            context_bundle: dict[str, object] | None = None
            known_set = set(known_frames)

            if len(raw_context_packets) >= 2:
                context_bundle = bundle_context_packets(
                    raw_context_packets,
                    receiver_known_frames=known_frames,
                )
                source_bytes = context_bundle.get("full_packet_bytes")
                bundle_bytes = context_bundle.get("bundle_bytes")
                if (
                    isinstance(source_bytes, bool)
                    or not isinstance(source_bytes, int)
                    or isinstance(bundle_bytes, bool)
                    or not isinstance(bundle_bytes, int)
                ):
                    raise RuntimeError("orchorbital context bundle byte accounting is invalid")
                original_context_bytes = source_bytes
                transported_context_bytes = bundle_bytes
                for task_id, raw_packet in raw_context_packets.items():
                    payload = transport_payloads[task_id]
                    payload.pop(PACKET_PAYLOAD_KEY, None)
                    reference = context_bundle_reference(context_bundle, task_id)
                    payload[BUNDLE_REF_PAYLOAD_KEY] = reference
                    transported_context_bytes += len(_canonical(reference))
                    target = raw_packet.get("target_frame_commitment")
                    raw_frames = raw_packet.get("frames")
                    if target in known_set or (
                        isinstance(raw_frames, list)
                        and any(
                            isinstance(frame, Mapping)
                            and frame.get("frame_commitment") in known_set
                            for frame in raw_frames
                        )
                    ):
                        cache_hits += 1
            else:
                for task_id, raw_packet in raw_context_packets.items():
                    reduced = reduce_context_packet(
                        raw_packet,
                        receiver_known_frames=known_frames,
                    )
                    source_bytes = raw_packet.get("packet_bytes")
                    reduced_bytes = reduced.get("packet_bytes")
                    if (
                        isinstance(source_bytes, bool)
                        or not isinstance(source_bytes, int)
                        or isinstance(reduced_bytes, bool)
                        or not isinstance(reduced_bytes, int)
                    ):
                        raise RuntimeError(
                            "orchorbital context packet byte accounting is invalid"
                        )
                    original_context_bytes += source_bytes
                    transported_context_bytes += reduced_bytes
                    if reduced.get("cache_hit_frame_commitment") is not None:
                        cache_hits += 1
                    transport_payloads[task_id][PACKET_PAYLOAD_KEY] = reduced

            transport_pack_rows = [
                {
                    "task_id": task.task_id,
                    "payload": transport_payloads[task.task_id],
                }
                for task in chosen
            ]
            context_pack = pack_context(transport_pack_rows)

            ttl = self._lease_seconds if lease_seconds is None else _strict_int(
                lease_seconds, field="lease_seconds", minimum=1, maximum=MAX_LEASE_SECONDS
            )
            lease_id = uuid.uuid4().hex
            expires = now + ttl * 1_000_000_000
            for task in chosen:
                self._queue_index_remove(task)
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
            heapq.heappush(self._lease_expiry_heap, (expires, lease_id))
            omega = service_omega(PROFILES[selected_species]) if selected_species in PROFILES else None
            task_views = [self._task_view(task, include_payload=True) for task in chosen]
            bundle_commitment = (
                None
                if context_bundle is None
                else context_bundle.get("bundle_commitment")
            )
            if bundle_commitment is not None and not isinstance(bundle_commitment, str):
                raise RuntimeError("orchorbital context bundle commitment is invalid")
            for task_view in task_views:
                task_id = task_view.get("task_id")
                if not isinstance(task_id, str) or task_id not in transport_payloads:
                    raise RuntimeError("worker task transport lineage is invalid")
                task_view["payload"] = deepcopy(transport_payloads[task_id])
                species_name = task_view.get("species")
                canonical_commitment = task_view.get("task_commitment")
                if not isinstance(species_name, str) or not isinstance(
                    canonical_commitment, str
                ):
                    raise RuntimeError("worker task transport metadata is invalid")
                task_view["transport_commitment"] = worker_transport_commitment(
                    task_id=task_id,
                    species=species_name,
                    task_commitment=canonical_commitment,
                    payload=task_view["payload"],
                    bundle_commitment=bundle_commitment,
                )
            return {
                "schema": WORKER_SCHEMA,
                "worker_id": wid,
                "lease_id": lease_id,
                "species": selected_species,
                "issued_ns": now,
                "expires_ns": expires,
                "lane_width": lane,
                "batch_size": batch_size,
                "omega": omega,
                "tasks": task_views,
                "context_pack": context_pack,
                BUNDLE_PAYLOAD_KEY: context_bundle,
                "orchorbital_context_transport": {
                    "known_frame_count": len(known_frames),
                    "packet_task_count": sum(
                        1
                        for task in task_views
                        if isinstance(task.get("payload"), Mapping)
                        and PACKET_PAYLOAD_KEY in task["payload"]
                    ),
                    "cache_hit_task_count": cache_hits,
                    "bundle_used": context_bundle is not None,
                    "bundle_unique_frame_count": (
                        0
                        if context_bundle is None
                        else int(context_bundle["unique_frame_count"])
                    ),
                    "full_packet_bytes": original_context_bytes,
                    "transport_packet_bytes": transported_context_bytes,
                    "byte_saving_fraction": (
                        0.0
                        if original_context_bytes <= 0
                        else 1.0 - transported_context_bytes / original_context_bytes
                    ),
                    "canonical_task_commitment_unchanged": True,
                    "token_saving_claim": False,
                },
                "scheduler": {
                    "mode": GEOMETRY_SCHEDULER_MODE,
                    "species_selection": species_scheduler,
                    "batch_selection": batch_scheduler,
                    "context_candidate_scope": candidate_scope.get(
                        selected_species,
                        {},
                    ),
                    "legacy_orbit_lane_cap": legacy_cap,
                    "geometry_lane_width": lane,
                    "fifo_primary": False,
                },
                "authority": _authority_state(),
            }

    def submit(self, worker_id: str, lease_id: str, results: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
        wid = _normalize_id(worker_id, field="worker_id")
        lid = _normalize_id(lease_id, field="lease_id")
        if isinstance(results, (str, bytes)):
            raise ValueError("results must be an iterable of mappings")
        try:
            rows = list(results)
        except TypeError as exc:
            raise ValueError("results must be iterable") from exc
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
                tid = _normalize_id(row.get("task_id"), field="task_id")  # type: ignore[arg-type]
                if tid in supplied:
                    raise ValueError("duplicate task result")
                supplied.add(tid)
                status = row.get("status", "CANDIDATE")
                if not isinstance(status, str) or status != "CANDIDATE":
                    raise ValueError("worker results must remain CANDIDATE")
                if "output" not in row:
                    raise ValueError("worker result requires output")
                output = deepcopy(row["output"])
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
                self._unfinished_count -= 1
                if self._unfinished_count < 0:
                    raise RuntimeError("unfinished task counter underflow")
            del self._leases[lid]
            self._maybe_compact_lease_heap()
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
                "lease_expiry_heap_entries": len(self._lease_expiry_heap),
                "lease_expiry_heap_indexed": True,
                "unfinished_task_count": self._unfinished_count,
                "queue_indexed": True,
                "precomputed_phase_state_cache": True,
                "precomputed_phase_state_count": len(self._task_phase_state),
                "vector_distance_shadow_enabled": self._vector_distance_shadow,
                "queued_index_counts": {
                    name: len(self._queued_by_species[name])
                    for name in WORKER_SPECIES
                },
                "context_ancestry_indexed": True,
                "context_index_max_depth": MAX_CONTEXT_INDEX_DEPTH,
                "context_index_bucket_counts": {
                    name: len(self._queued_by_context_frame[name])
                    for name in WORKER_SPECIES
                },
                "context_index_member_references": {
                    name: sum(
                        len(bucket)
                        for bucket in self._queued_by_context_frame[name].values()
                    )
                    for name in WORKER_SPECIES
                },
                "tasks": counts,
                "scheduler": scheduler_manifest(),
                "authority": _authority_state(),
            }

    @staticmethod
    def _validate_task_memory_authorization(task: TaskRecord) -> None:
        authorization = task.payload.get(MEMORY_AUTHORIZATION_KEY)
        if authorization is None:
            return
        validated = validate_task_authorization_bundle(authorization)
        if validated["beast"] != task.species:
            raise RuntimeError("task memory authorization beast/species mismatch")
        if validated["task_id"] != task.task_id:
            raise RuntimeError("task memory authorization task_id mismatch")

    def _require_worker(self, worker_id: str) -> WorkerRecord:
        worker = self._workers.get(worker_id)
        if worker is None:
            raise ValueError("unknown worker_id")
        return worker

    def _reap_expired(self, now_ns: int) -> None:
        if isinstance(now_ns, bool) or not isinstance(now_ns, int):
            raise ValueError("now_ns must be an integer")
        while self._lease_expiry_heap and self._lease_expiry_heap[0][0] <= now_ns:
            expires_ns, lid = heapq.heappop(self._lease_expiry_heap)
            lease = self._leases.get(lid)
            if lease is None:
                continue
            if lease.expires_ns != expires_ns:
                continue
            for tid in lease.task_ids:
                task = self._tasks.get(tid)
                if task is None:
                    raise RuntimeError("expired lease references a missing task")
                if (
                    task.state != "LEASED"
                    or task.lease_id != lid
                    or task.leased_to != lease.worker_id
                ):
                    raise RuntimeError("expired lease/task lineage is inconsistent")
            self._leases.pop(lid)
            for tid in lease.task_ids:
                task = self._tasks[tid]
                task.state = "QUEUED"
                task.lease_id = None
                task.leased_to = None
                task.lease_expires_ns = None
                self._queue_index_add(task)
        self._maybe_compact_lease_heap()

    @staticmethod
    def _scheduler_task_view(record: TaskRecord) -> dict[str, Any]:
        return {
            "task_id": record.task_id,
            "species": record.species,
            "payload": record.payload,
            "task_commitment": record.task_commitment,
            "created_ns": record.created_ns,
        }

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
            out["payload"] = deepcopy(record.payload)
        if include_result and record.state == "DONE":
            out["status"] = "CANDIDATE"
            out["result"] = deepcopy(record.result)
        return out


broker = WorkerBroker()
