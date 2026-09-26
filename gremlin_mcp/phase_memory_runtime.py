from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from threading import RLock
from typing import Any, Iterable, Mapping, Sequence

from gremlin_mcp.role_registry import BESTIARY_ROLE_NAMES

SCHEMA = "GREMLIN_PHASE_MEMORY_RUNTIME_V0_1"
VERSION = "0.1.0"
MAX_BIAS = 0.12


class PhaseMemoryError(ValueError):
    pass


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
        raise PhaseMemoryError("memory state must be finite canonical JSON") from exc


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _role(value: str) -> str:
    name = str(value).strip().upper()
    if name not in BESTIARY_ROLE_NAMES:
        raise PhaseMemoryError(f"unknown Bestiary role: {value!r}")
    return name


def empty_memory_state() -> dict[str, Any]:
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "sequence": 0,
        "last_role": None,
        "visit_counts": {},
        "transition_counts": {},
        "parent_commitment": None,
    }
    return {**core, "commitment": _sha(core)}


def validate_memory_state(state: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(state, Mapping):
        raise PhaseMemoryError("memory state must be a mapping")
    row = deepcopy(dict(state))
    if row.get("schema") != SCHEMA or row.get("version") != VERSION:
        raise PhaseMemoryError("unsupported phase-memory state")
    sequence = row.get("sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise PhaseMemoryError("memory sequence must be a non-negative integer")
    last_role = row.get("last_role")
    if last_role is not None:
        last_role = _role(str(last_role))
    visits = row.get("visit_counts")
    transitions = row.get("transition_counts")
    if not isinstance(visits, Mapping) or not isinstance(transitions, Mapping):
        raise PhaseMemoryError("memory counts must be mappings")
    normalized_visits: dict[str, int] = {}
    for raw_role, raw_count in visits.items():
        name = _role(str(raw_role))
        if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count < 0:
            raise PhaseMemoryError("visit counts must be non-negative integers")
        if raw_count:
            normalized_visits[name] = raw_count
    normalized_transitions: dict[str, int] = {}
    for raw_edge, raw_count in transitions.items():
        if not isinstance(raw_edge, str) or "->" not in raw_edge:
            raise PhaseMemoryError("transition keys must use SOURCE->TARGET")
        source, target = raw_edge.split("->", 1)
        key = f"{_role(source)}->{_role(target)}"
        if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count < 0:
            raise PhaseMemoryError("transition counts must be non-negative integers")
        if raw_count:
            normalized_transitions[key] = raw_count
    parent = row.get("parent_commitment")
    if parent is not None and (not isinstance(parent, str) or len(parent) != 64):
        raise PhaseMemoryError("parent commitment must be a SHA-256 hex string")
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "sequence": sequence,
        "last_role": last_role,
        "visit_counts": dict(sorted(normalized_visits.items())),
        "transition_counts": dict(sorted(normalized_transitions.items())),
        "parent_commitment": parent,
    }
    commitment = row.get("commitment")
    if commitment != _sha(core):
        raise PhaseMemoryError("memory commitment mismatch")
    return {**core, "commitment": commitment}


def update_memory_state(
    state: Mapping[str, Any],
    route: Sequence[str],
) -> dict[str, Any]:
    current = validate_memory_state(state)
    names = tuple(_role(name) for name in route)
    if not names:
        return current
    visits = dict(current["visit_counts"])
    transitions = dict(current["transition_counts"])
    previous = current["last_role"]
    for name in names:
        visits[name] = visits.get(name, 0) + 1
        if previous is not None:
            key = f"{previous}->{name}"
            transitions[key] = transitions.get(key, 0) + 1
        previous = name
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "sequence": int(current["sequence"]) + 1,
        "last_role": previous,
        "visit_counts": dict(sorted(visits.items())),
        "transition_counts": dict(sorted(transitions.items())),
        "parent_commitment": current["commitment"],
    }
    return {**core, "commitment": _sha(core)}


def transition_affinity(
    state: Mapping[str, Any],
    source_roles: Iterable[str],
    target_role: str,
) -> float:
    current = validate_memory_state(state)
    target = _role(target_role)
    sources = tuple(dict.fromkeys(_role(source) for source in source_roles))
    if not sources:
        if current["last_role"] is None:
            return 0.0
        sources = (str(current["last_role"]),)
    counts = current["transition_counts"]
    values: list[float] = []
    for source in sources:
        outgoing = [
            (edge, int(count))
            for edge, count in counts.items()
            if edge.startswith(f"{source}->")
        ]
        total = sum(count for _, count in outgoing)
        if total <= 0:
            values.append(0.0)
            continue
        direct = int(counts.get(f"{source}->{target}", 0))
        values.append(direct / total)
    return 0.0 if not values else sum(values) / len(values)


def memory_bias_scores(
    base_scores: Mapping[str, float],
    state: Mapping[str, Any],
    *,
    source_roles: Iterable[str] = (),
    max_bias: float = MAX_BIAS,
) -> dict[str, float]:
    if not isinstance(base_scores, Mapping):
        raise PhaseMemoryError("base_scores must be a mapping")
    strength = float(max_bias)
    if not math.isfinite(strength) or not 0.0 <= strength <= 0.5:
        raise PhaseMemoryError("max_bias must be finite and in [0,0.5]")
    normalized: dict[str, float] = {}
    for raw_role, raw_score in base_scores.items():
        name = _role(str(raw_role))
        score = float(raw_score)
        if not math.isfinite(score):
            raise PhaseMemoryError("base scores must be finite")
        normalized[name] = score
    sources = tuple(source_roles)
    return {
        name: score + strength * transition_affinity(state, sources, name)
        for name, score in normalized.items()
    }


def memory_order(
    species: Sequence[str],
    base_scores: Mapping[str, float],
    state: Mapping[str, Any],
    *,
    source_roles: Iterable[str] = (),
    max_bias: float = MAX_BIAS,
) -> tuple[list[str], dict[str, float]]:
    names = tuple(dict.fromkeys(_role(name) for name in species))
    scored = memory_bias_scores(
        {name: float(base_scores.get(name, 0.0)) for name in names},
        state,
        source_roles=source_roles,
        max_bias=max_bias,
    )
    return (
        sorted(names, key=lambda name: (-scored[name], name)),
        scored,
    )


def memory_manifest() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "source_law": {
            "repository": "AdrianLipa90/Memory-Ontology",
            "artifact": "formalism/memory-law-v0.1.md",
            "law": "persistent history-dependent modification of transition structure",
        },
        "history_encoding": "VISIT_AND_DIRECTED_TRANSITION_COUNTS",
        "persistence": "PROCESS_RESIDENT_SERIALIZABLE_CHAINED_STATE",
        "causal_effect": "BOUNDED_FUTURE_ROUTE_SCORE_BIAS",
        "max_bias": MAX_BIAS,
        "automatic_external_effects": False,
        "production_runtime_write": False,
        "canon_allowed": False,
    }


class PhaseMemoryRuntime:
    """Thread-safe process-resident memory kernel.

    The state is serializable and commitment-chained. Persistence beyond process
    lifetime is an adapter responsibility; no hidden disk write occurs here.
    """

    def __init__(self, state: Mapping[str, Any] | None = None) -> None:
        self._lock = RLock()
        self._state = (
            empty_memory_state()
            if state is None
            else validate_memory_state(state)
        )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._state)

    def observe(self, route: Sequence[str]) -> dict[str, Any]:
        with self._lock:
            self._state = update_memory_state(self._state, route)
            return deepcopy(self._state)

    def order(
        self,
        species: Sequence[str],
        base_scores: Mapping[str, float],
        *,
        source_roles: Iterable[str] = (),
        max_bias: float = MAX_BIAS,
    ) -> tuple[list[str], dict[str, float]]:
        with self._lock:
            return memory_order(
                species,
                base_scores,
                self._state,
                source_roles=source_roles,
                max_bias=max_bias,
            )


__all__ = [
    "SCHEMA",
    "VERSION",
    "MAX_BIAS",
    "PhaseMemoryError",
    "empty_memory_state",
    "validate_memory_state",
    "update_memory_state",
    "transition_affinity",
    "memory_bias_scores",
    "memory_order",
    "memory_manifest",
    "PhaseMemoryRuntime",
]
