from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Any, Iterable, Mapping, Sequence

from gremlin_mcp.role_registry import CONTROL_PLANE_SPECIES, DYNAMIC_WORKLOAD_SPECIES
from tools.gremlin_bestiary_phasenav_phase_gates_v01 import DIM, TAU, PhaseGate36, SPECIES

SCHEMA = "GREMLIN_GEOMETRY_PHASE_STATE_SCHEDULER_V0_1"
MODE = "GEOMETRY_PHASE_STATE_CLUSTERED_V0_1"
SCHEDULER_KEY = "_gremlin_scheduler"
DERIVED_PHASE_DOMAIN = b"GREMLIN-GEOMETRY-PHASE-SCHEDULER/v0.1\x00"
TOKEN_RE = re.compile(r"[A-Za-z0-9_./:+-]+", re.UNICODE)
CONTEXT_AFFINITY_WEIGHT = 0.08
RECEIVER_CACHE_AFFINITY_WEIGHT = 0.06
RECEIVER_SPECIES_AFFINITY_WEIGHT = 0.04

# Control-plane classification comes from the canonical 20-role registry.
CORE_ONLY_SPECIES = CONTROL_PLANE_SPECIES
SCHEDULER_SPECIES = tuple(sorted(DYNAMIC_WORKLOAD_SPECIES))
PHASENAV_CARRIER_SPECIES = frozenset(SPECIES)


class GeometryPhaseSchedulerError(ValueError):
    pass


@dataclass(frozen=True)
class TaskPhaseState:
    task_id: str
    species: str
    phase36: tuple[float, ...]
    phase_source: str
    readiness: float
    temperature: float
    urgency: float
    noise: float
    token_estimate: int
    created_ns: int
    task_commitment: str


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
        raise GeometryPhaseSchedulerError("scheduler payload must be finite JSON data") from exc


def _unit(value: Any, field: str, *, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GeometryPhaseSchedulerError(f"{field} must be a finite number in [0,1]")
    out = float(value)
    if not math.isfinite(out) or not (0.0 <= out <= 1.0):
        raise GeometryPhaseSchedulerError(f"{field} must be in [0,1]")
    return out


def _phase36(value: Any) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != DIM:
        raise GeometryPhaseSchedulerError(f"phase36 must contain exactly {DIM} values")
    out = tuple(float(x) for x in value)
    if not all(math.isfinite(x) and 0.0 <= x < TAU for x in out):
        raise GeometryPhaseSchedulerError("phase36 must contain finite values in [0,2pi)")
    return out


def _payload_core(payload: Mapping[str, Any]) -> dict[str, Any]:
    # Scheduler hints are committed by the worker task envelope, but are excluded
    # from the fallback content geometry so tuning metadata cannot rewrite meaning.
    return {str(k): v for k, v in payload.items() if str(k) != SCHEDULER_KEY}


def _byte_entropy(raw: bytes) -> float:
    if not raw:
        return 0.0
    counts = [0] * 256
    for b in raw:
        counts[b] += 1
    n = len(raw)
    h = 0.0
    for c in counts:
        if c:
            p = c / n
            h -= p * math.log2(p)
    return min(1.0, max(0.0, h / 8.0))


def _tokenize(raw: bytes) -> tuple[str, ...]:
    text = raw.decode("utf-8", errors="replace").casefold()
    tokens = tuple(TOKEN_RE.findall(text))
    if tokens:
        return tokens
    digest = hashlib.blake2b(DERIVED_PHASE_DOMAIN + raw, digest_size=16).hexdigest()
    return (digest,)


def _token_phase(token: str, axis: int) -> float:
    digest = hashlib.blake2b(
        DERIVED_PHASE_DOMAIN + axis.to_bytes(2, "big") + token.encode("utf-8"),
        digest_size=8,
    ).digest()
    u = int.from_bytes(digest, "big") / float(1 << 64)
    return TAU * u


def derived_phase36(payload: Mapping[str, Any]) -> tuple[float, ...]:
    """Locality-oriented deterministic phase fingerprint.

    Shared canonical payload tokens contribute the same phasors, so related
    payloads tend to occupy closer regions of T^36 than unrelated payloads.
    This is a scheduling fingerprint, not a semantic truth claim.
    """
    raw = _canonical(_payload_core(payload))
    tokens = _tokenize(raw)
    # Frequency damping prevents one repeated token from completely dominating.
    freq: dict[str, int] = {}
    for token in tokens:
        freq[token] = freq.get(token, 0) + 1
    weighted = tuple((token, 1.0 / math.sqrt(freq[token])) for token in tokens)

    phases: list[float] = []
    for axis in range(DIM):
        c = 0.0
        s = 0.0
        for token, weight in weighted:
            angle = _token_phase(token, axis)
            c += weight * math.cos(angle)
            s += weight * math.sin(angle)
        if abs(c) + abs(s) <= 1e-15:
            angle = _token_phase(hashlib.blake2b(raw, digest_size=16).hexdigest(), axis)
        else:
            angle = math.atan2(s, c) % TAU
        phases.append(angle)
    return tuple(phases)


def circular_delta(a: float, b: float) -> float:
    return (float(a) - float(b) + math.pi) % TAU - math.pi


def phase_distance(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != DIM or len(right) != DIM:
        raise GeometryPhaseSchedulerError("phase distance requires two 36D states")
    rms = math.sqrt(sum(circular_delta(a, b) ** 2 for a, b in zip(left, right)) / DIM)
    return min(1.0, rms / math.pi)


def phase_centroid(states: Sequence[TaskPhaseState]) -> tuple[float, ...]:
    if not states:
        raise GeometryPhaseSchedulerError("phase centroid requires at least one state")
    out: list[float] = []
    for axis in range(DIM):
        c = sum(math.cos(s.phase36[axis]) for s in states)
        q = sum(math.sin(s.phase36[axis]) for s in states)
        if abs(c) + abs(q) <= 1e-15:
            # Deterministic fallback to the lexicographically first task.
            ref = min(states, key=lambda x: (x.task_commitment, x.task_id))
            out.append(ref.phase36[axis])
        else:
            out.append(math.atan2(q, c) % TAU)
    return tuple(out)


def state_distance(left: TaskPhaseState, right: TaskPhaseState) -> float:
    geometry = phase_distance(left.phase36, right.phase36)
    temperature = abs(left.temperature - right.temperature)
    readiness = abs(left.readiness - right.readiness)
    return min(1.0, 0.76 * geometry + 0.14 * temperature + 0.10 * readiness)


def _task_state(row: Mapping[str, Any]) -> TaskPhaseState:
    task_id = row.get("task_id")
    species = row.get("species")
    payload = row.get("payload")
    commitment = row.get("task_commitment")
    created_ns = row.get("created_ns")
    if not isinstance(task_id, str) or not task_id:
        raise GeometryPhaseSchedulerError("scheduler task requires task_id")
    if not isinstance(species, str) or species not in SCHEDULER_SPECIES:
        raise GeometryPhaseSchedulerError("scheduler task has unsupported species")
    if not isinstance(payload, Mapping):
        raise GeometryPhaseSchedulerError("scheduler task payload must be an object")
    if not isinstance(commitment, str) or not commitment:
        raise GeometryPhaseSchedulerError("scheduler task requires task_commitment")
    if isinstance(created_ns, bool) or not isinstance(created_ns, int) or created_ns < 0:
        raise GeometryPhaseSchedulerError("scheduler task requires non-negative created_ns")

    raw_meta = payload.get(SCHEDULER_KEY)
    if raw_meta is None:
        meta: Mapping[str, Any] = {}
    elif isinstance(raw_meta, Mapping):
        meta = raw_meta
    else:
        raise GeometryPhaseSchedulerError(f"{SCHEDULER_KEY} must be an object")

    explicit_phase = meta.get("phase36")
    if explicit_phase is None:
        phase = derived_phase36(payload)
        source = "DERIVED_STRUCTURAL_TEXT_PHASE_V0_1"
    else:
        phase = _phase36(explicit_phase)
        source = "EXPLICIT_T36"

    raw_core = _canonical(_payload_core(payload))
    estimated_tokens = max(1, math.ceil(len(raw_core) / 4.0))
    explicit_noise = meta.get("noise")
    noise = _unit(explicit_noise, "noise", default=_byte_entropy(raw_core))

    ready = meta.get("ready", True)
    if not isinstance(ready, bool):
        raise GeometryPhaseSchedulerError("ready must be boolean")
    readiness = _unit(meta.get("readiness"), "readiness", default=1.0 if ready else 0.0)
    if not ready:
        readiness = 0.0

    return TaskPhaseState(
        task_id=task_id,
        species=species,
        phase36=phase,
        phase_source=source,
        readiness=readiness,
        temperature=_unit(meta.get("temperature"), "temperature", default=0.5),
        urgency=_unit(meta.get("urgency"), "urgency", default=0.0),
        noise=noise,
        token_estimate=estimated_tokens,
        created_ns=created_ns,
        task_commitment=commitment,
    )


def task_phase_state(row: Mapping[str, Any]) -> TaskPhaseState:
    return _task_state(row)


def _states_for_rows(
    rows: Sequence[Mapping[str, Any]],
    precomputed_states: Mapping[str, TaskPhaseState] | None = None,
) -> list[TaskPhaseState]:
    if precomputed_states is None:
        return [_task_state(row) for row in rows]
    if not isinstance(precomputed_states, Mapping):
        raise GeometryPhaseSchedulerError("precomputed_states must be a mapping")

    states: list[TaskPhaseState] = []
    for row in rows:
        task_id = row.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise GeometryPhaseSchedulerError("scheduler task requires task_id")
        state = precomputed_states.get(task_id)
        if not isinstance(state, TaskPhaseState):
            raise GeometryPhaseSchedulerError(
                f"precomputed state is unavailable for task: {task_id}"
            )
        if (
            row.get("species") != state.species
            or row.get("task_commitment") != state.task_commitment
            or row.get("created_ns") != state.created_ns
        ):
            raise GeometryPhaseSchedulerError(
                f"precomputed state lineage mismatch for task: {task_id}"
            )
        states.append(state)
    return states


def _age_boost(state: TaskPhaseState, now_ns: int) -> float:
    if now_ns < state.created_ns:
        return 0.0
    age_s = (now_ns - state.created_ns) / 1_000_000_000.0
    # Starvation firewall only; it cannot turn the scheduler back into FIFO.
    return min(0.12, max(0.0, (age_s - 300.0) / 3600.0 * 0.12))


def _anchor_resonance(state: TaskPhaseState) -> float:
    # Explicit PhaseNav states are allowed to use the species carrier as a real
    # scheduling coordinate. Fallback content fingerprints remain anchor-neutral.
    if state.phase_source != "EXPLICIT_T36":
        return 0.5
    # ELEPHANT/BEES are valid dynamic Bestiary roles but do not yet have
    # validated PhaseNav species carriers. Keep their anchor contribution
    # neutral rather than inventing a carrier.
    if state.species not in PHASENAV_CARRIER_SPECIES:
        return 0.5
    anchor = PhaseGate36(state.species).phase_bias
    return 1.0 - phase_distance(state.phase36, anchor)


def task_priority(state: TaskPhaseState, centroid: Sequence[float], *, now_ns: int) -> float:
    cluster = 1.0 - phase_distance(state.phase36, centroid)
    info = 1.0 - state.noise
    anchor = _anchor_resonance(state)
    return (
        0.40 * cluster
        + 0.18 * info
        + 0.16 * state.readiness
        + 0.11 * state.urgency
        + 0.05 * anchor
        + 0.10 * _age_boost(state, now_ns)
    )


def queue_metrics(
    rows: Sequence[Mapping[str, Any]],
    *,
    now_ns: int,
    precomputed_states: Mapping[str, TaskPhaseState] | None = None,
) -> dict[str, Any]:
    if not rows:
        raise GeometryPhaseSchedulerError("queue metrics require at least one task")
    states = _states_for_rows(rows, precomputed_states)
    eligible = [s for s in states if s.readiness > 0.0]
    if not eligible:
        return {
            "eligible": False,
            "task_count": len(states),
            "eligible_count": 0,
            "queue_score": -1.0,
            "cluster_coherence": 0.0,
            "mean_noise": 1.0,
            "mean_readiness": 0.0,
            "max_urgency": max((s.urgency for s in states), default=0.0),
            "explicit_phase_fraction": sum(s.phase_source == "EXPLICIT_T36" for s in states) / len(states),
        }

    centroid = phase_centroid(eligible)
    distances = [phase_distance(s.phase36, centroid) for s in eligible]
    coherence = 1.0 - sum(distances) / len(distances)
    mean_noise = sum(s.noise for s in eligible) / len(eligible)
    mean_readiness = sum(s.readiness for s in eligible) / len(eligible)
    max_urgency = max(s.urgency for s in eligible)
    backlog = min(1.0, math.log1p(len(eligible)) / math.log(129.0))
    explicit_fraction = sum(s.phase_source == "EXPLICIT_T36" for s in eligible) / len(eligible)
    overdue = max(_age_boost(s, now_ns) for s in eligible)
    score = (
        0.42 * coherence
        + 0.20 * (1.0 - mean_noise)
        + 0.14 * mean_readiness
        + 0.10 * max_urgency
        + 0.07 * backlog
        + 0.04 * explicit_fraction
        + 0.03 * overdue
    )
    return {
        "eligible": True,
        "task_count": len(states),
        "eligible_count": len(eligible),
        "queue_score": score,
        "cluster_coherence": coherence,
        "mean_noise": mean_noise,
        "mean_readiness": mean_readiness,
        "max_urgency": max_urgency,
        "explicit_phase_fraction": explicit_fraction,
        "centroid": list(centroid),
    }


def choose_species(
    queues: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    now_ns: int,
    cadence_hint: Mapping[str, float] | None = None,
    locality_hint: Mapping[str, float] | None = None,
    precomputed_states: Mapping[str, TaskPhaseState] | None = None,
) -> tuple[str | None, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    candidates: list[tuple[float, float, str]] = []
    for species, rows in queues.items():
        if species not in SCHEDULER_SPECIES or not rows:
            continue
        m = queue_metrics(
            rows,
            now_ns=now_ns,
            precomputed_states=precomputed_states,
        )
        metrics[species] = m
        if not m["eligible"]:
            continue
        cadence = 0.0 if cadence_hint is None else float(cadence_hint.get(species, 0.0))
        if not math.isfinite(cadence) or cadence < 0.0:
            raise GeometryPhaseSchedulerError("cadence hints must be finite and non-negative")
        locality = 0.0 if locality_hint is None else float(locality_hint.get(species, 0.0))
        if not math.isfinite(locality) or not (0.0 <= locality <= 1.0):
            raise GeometryPhaseSchedulerError("locality hints must be finite and in [0,1]")
        # Receiver locality is a bounded additive bias. Cadence remains a
        # deterministic secondary hint after geometry/state + locality.
        effective = float(m["queue_score"]) + RECEIVER_SPECIES_AFFINITY_WEIGHT * locality
        m["receiver_locality_hint"] = locality
        m["effective_queue_score"] = effective
        candidates.append((effective, cadence, species))
    if not candidates:
        return None, {"schema": SCHEMA, "mode": MODE, "queues": metrics, "selected_species": None}
    selected = max(candidates, key=lambda row: (row[0], row[1], row[2]))[2]
    return selected, {
        "schema": SCHEMA,
        "mode": MODE,
        "queues": metrics,
        "selected_species": selected,
        "selection_basis": (
            "GEOMETRY_PHASE_STATE_PLUS_RECEIVER_LOCALITY_THEN_CADENCE"
            if locality_hint
            else "GEOMETRY_PHASE_STATE_THEN_CADENCE_TIEBREAK"
        ),
        "receiver_species_affinity_weight": (
            RECEIVER_SPECIES_AFFINITY_WEIGHT if locality_hint else 0.0
        ),
    }


def geometry_lane_width(
    *,
    vector_width: int,
    max_batch: int,
    cluster_coherence: float,
    legacy_cap: int | None = None,
) -> int:
    vw = int(vector_width)
    mb = int(max_batch)
    if vw <= 0 or mb <= 0:
        raise GeometryPhaseSchedulerError("vector_width and max_batch must be positive")
    coherence = float(cluster_coherence)
    if not math.isfinite(coherence) or not (0.0 <= coherence <= 1.0):
        raise GeometryPhaseSchedulerError("cluster_coherence must be in [0,1]")
    cap = mb if legacy_cap is None else min(mb, int(legacy_cap))
    if cap <= 0:
        raise GeometryPhaseSchedulerError("lane cap must be positive")
    # Coherent queues may use wider vector batches; noisy queues contract.
    width = round(vw * (0.50 + 1.50 * coherence))
    return max(1, min(cap, int(width)))


def _transition_cost(states: Sequence[TaskPhaseState]) -> float:
    if len(states) < 2:
        return 0.0
    return sum(state_distance(a, b) for a, b in zip(states, states[1:]))


def _noise_cost(states: Sequence[TaskPhaseState]) -> float:
    if not states:
        return 0.0
    intrinsic = sum(s.noise for s in states) / len(states)
    transition = _transition_cost(states) / max(1, len(states) - 1)
    return 0.60 * intrinsic + 0.40 * transition



def _normalize_affinity(
    affinity_by_task: Mapping[str, Iterable[str]] | None,
    eligible_ids: set[str],
) -> dict[str, frozenset[str]]:
    if affinity_by_task is None:
        return {}
    if not isinstance(affinity_by_task, Mapping):
        raise GeometryPhaseSchedulerError("affinity_by_task must be a mapping")
    out: dict[str, frozenset[str]] = {}
    for task_id, values in affinity_by_task.items():
        if task_id not in eligible_ids:
            continue
        if isinstance(values, (str, bytes, Mapping)) or not isinstance(values, Iterable):
            raise GeometryPhaseSchedulerError("task affinity must be an iterable")
        normalized = frozenset(str(value) for value in values if str(value))
        out[task_id] = normalized
    return out


def _context_affinity(
    task_id: str,
    chosen_ids: Sequence[str],
    affinity: Mapping[str, frozenset[str]],
) -> float:
    candidate = affinity.get(task_id, frozenset())
    if not candidate or not chosen_ids:
        return 0.0
    active: set[str] = set()
    for chosen_id in chosen_ids:
        active.update(affinity.get(chosen_id, frozenset()))
    if not active:
        return 0.0
    overlap = len(candidate & active)
    scale = min(len(candidate), len(active))
    return 0.0 if scale <= 0 else overlap / scale


def select_batch(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int,
    now_ns: int,
    affinity_by_task: Mapping[str, Iterable[str]] | None = None,
    receiver_known_affinity: Iterable[str] | None = None,
    precomputed_states: Mapping[str, TaskPhaseState] | None = None,
    precomputed_centroid: Sequence[float] | None = None,
) -> tuple[list[str], dict[str, Any]]:
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise GeometryPhaseSchedulerError("limit must be a positive integer")
    states = _states_for_rows(rows, precomputed_states)
    eligible = [s for s in states if s.readiness > 0.0]
    if not eligible:
        return [], {
            "schema": SCHEMA,
            "mode": MODE,
            "selected_task_ids": [],
            "reason": "NO_READY_GEOMETRIC_STATE",
        }

    if precomputed_centroid is None:
        centroid = phase_centroid(eligible)
    else:
        centroid = _phase36(list(precomputed_centroid))
    priority = {s.task_id: task_priority(s, centroid, now_ns=now_ns) for s in eligible}
    affinity = _normalize_affinity(
        affinity_by_task,
        {state.task_id for state in eligible},
    )
    affinity_active = any(affinity.values())
    if receiver_known_affinity is None:
        receiver_known = frozenset()
    else:
        if isinstance(receiver_known_affinity, (str, bytes, Mapping)) or not isinstance(
            receiver_known_affinity, Iterable
        ):
            raise GeometryPhaseSchedulerError(
                "receiver_known_affinity must be an iterable"
            )
        receiver_known = frozenset(
            str(value) for value in receiver_known_affinity if str(value)
        )

    receiver_affinity_active = bool(receiver_known) and affinity_active
    receiver_scores: dict[str, float] = {}
    if receiver_affinity_active:
        for task_id, signature in affinity.items():
            if signature:
                receiver_scores[task_id] = (
                    len(signature & receiver_known) / len(signature)
                )

    def receiver_score(task_id: str) -> float:
        return receiver_scores.get(task_id, 0.0)
    seed = max(
        eligible,
        key=lambda s: (
            priority[s.task_id]
            + (
                RECEIVER_CACHE_AFFINITY_WEIGHT * receiver_score(s.task_id)
                if receiver_affinity_active
                else 0.0
            ),
            -s.noise,
            s.urgency,
            s.task_commitment,
            s.task_id,
        ),
    )
    chosen = [seed]
    remaining = {s.task_id: s for s in eligible if s.task_id != seed.task_id}
    greedy_pairwise_distance_evaluations = 0

    while remaining and len(chosen) < limit:
        current = chosen[-1]
        active_affinity: set[str] = set()
        if affinity_active:
            for selected_state in chosen:
                active_affinity.update(
                    affinity.get(selected_state.task_id, frozenset())
                )

        def active_context_affinity(task_id: str) -> float:
            candidate = affinity.get(task_id, frozenset())
            if not candidate or not active_affinity:
                return 0.0
            overlap = len(candidate & active_affinity)
            scale = min(len(candidate), len(active_affinity))
            return 0.0 if scale <= 0 else overlap / scale

        def candidate_score(state: TaskPhaseState) -> float:
            nonlocal greedy_pairwise_distance_evaluations
            greedy_pairwise_distance_evaluations += 1
            return (
                0.58 * (1.0 - state_distance(current, state))
                + 0.25 * priority[state.task_id]
                + 0.10 * (1.0 - state.noise)
                + 0.07 * state.urgency
                + (
                    CONTEXT_AFFINITY_WEIGHT
                    * active_context_affinity(state.task_id)
                    if affinity_active
                    else 0.0
                )
                + (
                    RECEIVER_CACHE_AFFINITY_WEIGHT
                    * receiver_score(state.task_id)
                    if receiver_affinity_active
                    else 0.0
                )
            )

        next_state = max(
            remaining.values(),
            key=lambda state: (
                candidate_score(state),
                state.task_commitment,
                state.task_id,
            ),
        )
        chosen.append(next_state)
        del remaining[next_state.task_id]

    fifo = sorted(eligible, key=lambda s: (s.created_ns, s.task_id))[: len(chosen)]
    selected_transition = _transition_cost(chosen)
    fifo_transition = _transition_cost(fifo)
    selected_noise = _noise_cost(chosen)
    fifo_noise = _noise_cost(fifo)
    phase_sources: dict[str, int] = {}
    for state in chosen:
        phase_sources[state.phase_source] = phase_sources.get(state.phase_source, 0) + 1

    selected_affinities = [
        _context_affinity(
            chosen[index].task_id,
            [state.task_id for state in chosen[:index]],
            affinity,
        )
        for index in range(1, len(chosen))
    ]
    receipt = {
        "schema": SCHEMA,
        "mode": MODE,
        "selected_task_ids": [s.task_id for s in chosen],
        "fifo_task_ids_proxy": [s.task_id for s in fifo],
        "phase_sources": phase_sources,
        "context_affinity_active": affinity_active,
        "context_affinity_weight": (
            CONTEXT_AFFINITY_WEIGHT if affinity_active else 0.0
        ),
        "mean_context_affinity": (
            0.0
            if not selected_affinities
            else sum(selected_affinities) / len(selected_affinities)
        ),
        "receiver_cache_affinity_active": receiver_affinity_active,
        "receiver_cache_affinity_weight": (
            RECEIVER_CACHE_AFFINITY_WEIGHT if receiver_affinity_active else 0.0
        ),
        "mean_receiver_cache_affinity": (
            0.0
            if not chosen
            else sum(receiver_score(state.task_id) for state in chosen) / len(chosen)
        ),
        "mean_priority": sum(priority[s.task_id] for s in chosen) / len(chosen),
        "transition_cost_selected": selected_transition,
        "transition_cost_fifo_proxy": fifo_transition,
        "transition_reduction_vs_fifo_proxy": (
            0.0 if fifo_transition <= 1e-15 else 1.0 - selected_transition / fifo_transition
        ),
        "noise_cost_selected": selected_noise,
        "noise_cost_fifo_proxy": fifo_noise,
        "noise_reduction_vs_fifo_proxy": (
            0.0 if fifo_noise <= 1e-15 else 1.0 - selected_noise / fifo_noise
        ),
        "estimated_payload_tokens": sum(s.token_estimate for s in chosen),
        "greedy_pairwise_state_distance_evaluations": (
            greedy_pairwise_distance_evaluations
        ),
        "greedy_phase_axis_evaluations_proxy": (
            greedy_pairwise_distance_evaluations * DIM
        ),
        "distance_kernel": "SCALAR_EXACT_V0_1",
        "active_context_affinity_union_reused": True,
        "receiver_cache_affinity_precomputed": receiver_affinity_active,
        "ready_count": len(eligible),
        "queued_count": len(states),
        "fifo_used_for_selection": False,
        "precomputed_state_cache_used": precomputed_states is not None,
        "precomputed_centroid_used": precomputed_centroid is not None,
        "authority": {
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        },
    }
    return [s.task_id for s in chosen], receipt


def scheduler_manifest() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "mode": MODE,
        "dimension": DIM,
        "space": "T^36",
        "species": list(SCHEDULER_SPECIES),
        "core_only_species": sorted(CORE_ONLY_SPECIES),
        "queue_selection": "GEOMETRY_PHASE_STATE_CLUSTER_COHERENCE",
        "batch_selection": "GREEDY_PHASE_STATE_NEAREST_NEIGHBOR",
        "fifo_primary": False,
        "fifo_proxy_only": True,
        "explicit_phase_supported": True,
        "dynamic_workload_species": list(SCHEDULER_SPECIES),
        "validated_phasenav_carrier_species": sorted(
            PHASENAV_CARRIER_SPECIES & frozenset(SCHEDULER_SPECIES)
        ),
        "anchor_neutral_dynamic_species": sorted(
            frozenset(SCHEDULER_SPECIES) - PHASENAV_CARRIER_SPECIES
        ),
        "derived_phase": "LOCALITY_ORIENTED_STRUCTURAL_TEXT_PHASE_V0_1",
        "token_saving_claim": False,
        "noise_reduction_metric": "PROXY_UNTIL_END_TO_END_TOKEN_BENCHMARK",
        "external_effects": False,
        "canon_allowed": False,
    }
