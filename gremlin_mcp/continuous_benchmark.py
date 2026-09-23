from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, asdict, is_dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import threading
import time
import warnings
from typing import Any, Iterator, Mapping

SCHEMA = "GREMLIN_CONTINUOUS_BENCHMARK_V0_1"
EVENT_SCHEMA = "GREMLIN_CONTINUOUS_BENCHMARK_EVENT_V0_1"
VERSION = "0.1.0"
ZERO_HASH = "0" * 64

_CURRENT_PROMPT_ID: ContextVar[str | None] = ContextVar(
    "gremlin_continuous_benchmark_prompt_id", default=None
)


def _digest(data: bytes) -> str:
    return hashlib.blake2b(data, digest_size=32).hexdigest()


def _normalize(value: Any, depth: int = 0) -> Any:
    if depth > 8:
        return {"type": type(value).__name__, "truncated": True}
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else {"nonfinite": repr(value)}
    if isinstance(value, bytes):
        return {"bytes_digest": _digest(value), "length": len(value)}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {
            str(k): _normalize(v, depth + 1)
            for k, v in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_normalize(v, depth + 1) for v in value]
    if isinstance(value, (set, frozenset)):
        rows = [_normalize(v, depth + 1) for v in value]
        return sorted(rows, key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False))
    if is_dataclass(value) and not isinstance(value, type):
        return _normalize(asdict(value), depth + 1)
    return {
        "type": type(value).__name__,
        "repr_digest": _digest(repr(value).encode("utf-8", "replace")),
    }


def _canonical(value: Any) -> bytes:
    return json.dumps(
        _normalize(value),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def commitment(value: Any) -> str:
    return _digest(_canonical(value))


def _metric_map(metrics: Mapping[str, Any] | None) -> dict[str, float]:
    if metrics is None:
        return {}
    out: dict[str, float] = {}
    for raw_key, raw_value in metrics.items():
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            continue
        value = float(raw_value)
        if math.isfinite(value):
            out[str(raw_key)] = value
    return out


def _labels(value: Mapping[str, Any] | None) -> dict[str, str]:
    if value is None:
        return {}
    out: dict[str, str] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key).strip()
        text = str(raw_value).strip()
        if key and text:
            out[key[:96]] = text[:192]
    return out


@dataclass(frozen=True)
class PromptSpan:
    prompt_id: str
    started_unix_ns: int
    prompt_commitment: str
    generation: str | None
    source: str
    labels: dict[str, str]


@dataclass
class OnlineStat:
    count: int = 0
    total: float = 0.0
    minimum: float | None = None
    maximum: float | None = None

    def update(self, value: float) -> None:
        self.count += 1
        self.total += value
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)

    @property
    def mean(self) -> float:
        return self.total / self.count if self.count else 0.0

    def snapshot(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "mean": self.mean,
            "minimum": self.minimum,
            "maximum": self.maximum,
        }


class ContinuousBenchmarkLedger:
    """Append-only prompt/runtime benchmark ledger.

    The ledger persists commitments and bounded metrics only. Raw prompts,
    model outputs and specialist payloads are not written by this layer.
    """

    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        self._lock = threading.RLock()
        self._path = self._resolve_path(path)
        self._fsync = os.environ.get(
            "GREMLIN_CONTINUOUS_BENCHMARK_FSYNC", ""
        ).strip().casefold() in {"1", "true", "yes", "on"}
        self._sequence = 0
        self._previous_hash = ZERO_HASH
        self._health = "PASS"
        self._last_error: str | None = None
        self._open: dict[str, dict[str, Any]] = {}
        self._prompts_opened = 0
        self._prompts_closed = 0
        self._known_success = 0
        self._successes = 0
        self._routes = 0
        self._no_confident_routes = 0
        self._validations = 0
        self._validation_passes = 0
        self._ablations = 0
        self._fanout = OnlineStat()
        self._duration_ms = OnlineStat()
        self._corrections = OnlineStat()
        self._retries = OnlineStat()
        self._regressions = OnlineStat()
        self._generation_counts: dict[str, int] = {}
        self._load_existing()

    @staticmethod
    def _resolve_path(path: str | os.PathLike[str] | None) -> Path | None:
        if path is not None:
            raw = str(path).strip()
            return None if raw == ":memory:" else Path(raw).expanduser()
        configured = os.environ.get("GREMLIN_CONTINUOUS_BENCHMARK_PATH", "").strip()
        if configured:
            return None if configured == ":memory:" else Path(configured).expanduser()
        try:
            from gremlin_mcp.install.paths import resolve_paths
            return Path(resolve_paths().logs_dir) / "continuous-prompt-benchmark-v01.jsonl"
        except Exception:
            return Path.home() / ".gremlin" / "logs" / "continuous-prompt-benchmark-v01.jsonl"

    @property
    def path(self) -> Path | None:
        return self._path

    def mark_degraded(self, exc: BaseException) -> None:
        with self._lock:
            self._health = "DEGRADED"
            self._last_error = f"{type(exc).__name__}: {exc}"

    def _load_existing(self) -> None:
        if self._path is None or not self._path.exists():
            return
        previous = ZERO_HASH
        sequence = 0
        try:
            with self._path.open("r", encoding="utf-8") as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line:
                        continue
                    record = json.loads(line)
                    if record.get("sequence") != sequence + 1:
                        raise ValueError("continuous benchmark sequence discontinuity")
                    if record.get("previous_record_hash") != previous:
                        raise ValueError("continuous benchmark hash-chain discontinuity")
                    body = dict(record)
                    actual_hash = body.pop("record_hash", None)
                    if actual_hash != _digest(_canonical(body)):
                        raise ValueError("continuous benchmark record hash mismatch")
                    sequence += 1
                    previous = str(actual_hash)
                    self._replay(record)
            self._sequence = sequence
            self._previous_hash = previous
        except Exception as exc:
            self.mark_degraded(exc)

    def _append(self, record: Mapping[str, Any]) -> dict[str, Any]:
        if self._health != "PASS":
            raise RuntimeError(
                "CONTINUOUS_BENCHMARK_DEGRADED: append refused until ledger integrity is repaired"
            )
        body = dict(record)
        body["schema"] = EVENT_SCHEMA
        body["sequence"] = self._sequence + 1
        body["previous_record_hash"] = self._previous_hash
        body["record_hash"] = _digest(_canonical(body))
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        body,
                        sort_keys=True,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
                handle.flush()
                if self._fsync:
                    os.fsync(handle.fileno())
        self._sequence = int(body["sequence"])
        self._previous_hash = str(body["record_hash"])
        self._replay(body)
        return body

    def _replay(self, record: Mapping[str, Any]) -> None:
        event = str(record.get("event_type") or "")
        prompt_id = str(record.get("prompt_id") or "")
        generation = record.get("generation")
        if isinstance(generation, str) and generation:
            self._generation_counts[generation] = self._generation_counts.get(generation, 0) + 1

        if event == "PROMPT_OPEN":
            self._prompts_opened += 1
            if prompt_id:
                self._open[prompt_id] = {
                    "started_unix_ns": int(record.get("created_unix_ns") or 0),
                    "prompt_commitment": record.get("prompt_commitment"),
                    "generation": record.get("generation"),
                }
        elif event == "OCTOPUS_ROUTE":
            self._routes += 1
            fanout = record.get("fanout_count")
            if isinstance(fanout, int) and fanout >= 0:
                self._fanout.update(float(fanout))
            if record.get("route_status") in {
                "NO_CONFIDENT_ROUTE",
                "NO_CONFIDENT_ROUTE_NOT_QUEUED",
            }:
                self._no_confident_routes += 1
        elif event == "VALIDATION":
            self._validations += 1
            if record.get("validation_status") == "PASS":
                self._validation_passes += 1
            metrics = record.get("metrics")
            if isinstance(metrics, Mapping):
                for key, stat in (
                    ("correction_count", self._corrections),
                    ("retry_count", self._retries),
                    ("regression_count", self._regressions),
                ):
                    value = metrics.get(key)
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        stat.update(float(value))
        elif event == "PROMPT_CLOSE":
            self._prompts_closed += 1
            success = record.get("success")
            if isinstance(success, bool):
                self._known_success += 1
                if success:
                    self._successes += 1
            duration_ms = record.get("duration_ms")
            if isinstance(duration_ms, (int, float)) and not isinstance(duration_ms, bool):
                self._duration_ms.update(float(duration_ms))
            self._open.pop(prompt_id, None)
        elif event == "ABLATION":
            self._ablations += 1

    def begin_prompt(
        self,
        prompt: Any,
        *,
        generation: str | None = None,
        labels: Mapping[str, Any] | None = None,
        source: str = "EXPLICIT",
    ) -> PromptSpan:
        source_name = str(source).strip() or "EXPLICIT"
        now = time.time_ns()
        span = PromptSpan(
            prompt_id=f"prompt-{secrets.token_hex(12)}",
            started_unix_ns=now,
            prompt_commitment=commitment(prompt),
            generation=(
                str(generation).strip()
                if generation is not None and str(generation).strip()
                else os.environ.get("GREMLIN_GENERATION")
                or os.environ.get("NOEMA_GENERATION")
                or None
            ),
            source=source_name,
            labels=_labels(labels),
        )
        with self._lock:
            self._append(
                {
                    "event_type": "PROMPT_OPEN",
                    "created_unix_ns": now,
                    "prompt_id": span.prompt_id,
                    "prompt_commitment": span.prompt_commitment,
                    "generation": span.generation,
                    "source": span.source,
                    "labels": dict(span.labels),
                    "privacy": {
                        "raw_prompt_persisted": False,
                        "raw_output_persisted": False,
                    },
                    "authority": {
                        "observes_only": True,
                        "mutation_allowed": False,
                        "canon_allowed": False,
                    },
                }
            )
        return span

    def record_route(
        self,
        prompt_id: str,
        decision: Mapping[str, Any],
        *,
        generation: str | None = None,
    ) -> dict[str, Any]:
        route_mask = [str(value) for value in decision.get("route_mask") or []]
        ranked = []
        for row in decision.get("scores") or []:
            if isinstance(row, Mapping):
                score = row.get("score")
                if isinstance(score, (int, float)) and not isinstance(score, bool):
                    ranked.append(
                        {"species": str(row.get("species") or ""), "score": float(score)}
                    )
        prompt_key = str(prompt_id)
        inherited_generation = generation
        if inherited_generation is None:
            inherited_generation = self._open.get(prompt_key, {}).get("generation")
        record = {
            "event_type": "OCTOPUS_ROUTE",
            "created_unix_ns": time.time_ns(),
            "prompt_id": prompt_key,
            "generation": inherited_generation,
            "route_status": str(decision.get("status") or ""),
            "route_mask": route_mask,
            "fanout_count": len(route_mask),
            "route_commitment": decision.get("route_commitment"),
            "threshold": decision.get("threshold"),
            "ranked_scores": ranked,
            "authority": {
                "observes_only": True,
                "mutation_allowed": False,
                "canon_allowed": False,
            },
        }
        with self._lock:
            return self._append(record)

    def record_stage(
        self,
        prompt_id: str,
        *,
        stage: str,
        status: str,
        species: str | None = None,
        result: Any = None,
        metrics: Mapping[str, Any] | None = None,
        generation: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            return self._append(
                {
                    "event_type": "STAGE",
                    "created_unix_ns": time.time_ns(),
                    "prompt_id": str(prompt_id),
                    "generation": generation,
                    "stage": str(stage),
                    "status": str(status),
                    "species": str(species) if species is not None else None,
                    "result_commitment": commitment(result) if result is not None else None,
                    "metrics": _metric_map(metrics),
                    "authority": {
                        "observes_only": True,
                        "mutation_allowed": False,
                        "canon_allowed": False,
                    },
                }
            )

    def record_validation(
        self,
        prompt_id: str,
        *,
        status: str,
        validators: tuple[str, ...] | list[str] = (),
        correction_count: int = 0,
        retry_count: int = 0,
        regression_count: int = 0,
        provenance_complete: bool | None = None,
        evidence: Any = None,
        generation: str | None = None,
    ) -> dict[str, Any]:
        metrics = {
            "correction_count": int(correction_count),
            "retry_count": int(retry_count),
            "regression_count": int(regression_count),
        }
        with self._lock:
            return self._append(
                {
                    "event_type": "VALIDATION",
                    "created_unix_ns": time.time_ns(),
                    "prompt_id": str(prompt_id),
                    "generation": generation,
                    "validation_status": str(status),
                    "validators": [str(value) for value in validators],
                    "provenance_complete": provenance_complete,
                    "evidence_commitment": commitment(evidence) if evidence is not None else None,
                    "metrics": metrics,
                    "authority": {
                        "observes_only": True,
                        "mutation_allowed": False,
                        "canon_allowed": False,
                    },
                }
            )

    def finish_prompt(
        self,
        prompt_id: str,
        *,
        status: str,
        success: bool | None,
        outcome: Any = None,
        metrics: Mapping[str, Any] | None = None,
        generation: str | None = None,
    ) -> dict[str, Any]:
        now = time.time_ns()
        opened = self._open.get(str(prompt_id))
        started = int(opened.get("started_unix_ns") or now) if opened else now
        duration_ms = max(0.0, (now - started) / 1_000_000.0)
        with self._lock:
            return self._append(
                {
                    "event_type": "PROMPT_CLOSE",
                    "created_unix_ns": now,
                    "prompt_id": str(prompt_id),
                    "generation": generation,
                    "status": str(status),
                    "success": success,
                    "duration_ms": duration_ms,
                    "outcome_commitment": commitment(outcome) if outcome is not None else None,
                    "metrics": _metric_map(metrics),
                    "authority": {
                        "observes_only": True,
                        "mutation_allowed": False,
                        "canon_allowed": False,
                    },
                }
            )

    def record_ablation(
        self,
        prompt_id: str,
        *,
        ablation: str,
        baseline_metrics: Mapping[str, Any],
        ablated_metrics: Mapping[str, Any],
        method: str,
        exact_same_task: bool,
        generation: str | None = None,
    ) -> dict[str, Any]:
        baseline = _metric_map(baseline_metrics)
        ablated = _metric_map(ablated_metrics)
        deltas = {
            key: ablated[key] - baseline[key]
            for key in sorted(set(baseline) & set(ablated))
        }
        with self._lock:
            return self._append(
                {
                    "event_type": "ABLATION",
                    "created_unix_ns": time.time_ns(),
                    "prompt_id": str(prompt_id),
                    "generation": generation,
                    "ablation": str(ablation),
                    "method": str(method),
                    "exact_same_task": bool(exact_same_task),
                    "baseline_metrics": baseline,
                    "ablated_metrics": ablated,
                    "delta_ablated_minus_baseline": deltas,
                    "authority": {
                        "observes_only": True,
                        "mutation_allowed": False,
                        "canon_allowed": False,
                    },
                }
            )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            success_rate = (
                self._successes / self._known_success if self._known_success else None
            )
            validation_rate = (
                self._validation_passes / self._validations if self._validations else None
            )
            return {
                "schema": SCHEMA,
                "version": VERSION,
                "status": self._health,
                "last_error": self._last_error,
                "ledger_path": str(self._path) if self._path is not None else None,
                "persistent": self._path is not None,
                "record_count": self._sequence,
                "head_hash": self._previous_hash,
                "open_prompt_count": len(self._open),
                "prompts": {
                    "opened": self._prompts_opened,
                    "closed": self._prompts_closed,
                    "known_success": self._known_success,
                    "successes": self._successes,
                    "success_rate": success_rate,
                    "duration_ms": self._duration_ms.snapshot(),
                },
                "routing": {
                    "routes": self._routes,
                    "no_confident_routes": self._no_confident_routes,
                    "fanout_count": self._fanout.snapshot(),
                },
                "validation": {
                    "events": self._validations,
                    "passes": self._validation_passes,
                    "pass_rate": validation_rate,
                    "correction_count": self._corrections.snapshot(),
                    "retry_count": self._retries.snapshot(),
                    "regression_count": self._regressions.snapshot(),
                },
                "ablations": self._ablations,
                "generation_event_counts": dict(sorted(self._generation_counts.items())),
                "policy": {
                    "raw_prompt_persisted": False,
                    "raw_output_persisted": False,
                    "append_only": True,
                    "hash_chained": True,
                    "observational_only": True,
                    "unknown_metrics_not_inferred": True,
                },
                "authority": {
                    "production_runtime_write": False,
                    "execution_admitted": False,
                    "canon_allowed": False,
                },
            }


GLOBAL_CONTINUOUS_BENCHMARK = ContinuousBenchmarkLedger()


def configure_continuous_benchmark(
    path: str | os.PathLike[str] | None,
) -> ContinuousBenchmarkLedger:
    global GLOBAL_CONTINUOUS_BENCHMARK
    GLOBAL_CONTINUOUS_BENCHMARK = ContinuousBenchmarkLedger(path)
    return GLOBAL_CONTINUOUS_BENCHMARK


def benchmark_status() -> dict[str, Any]:
    return GLOBAL_CONTINUOUS_BENCHMARK.snapshot()


def current_prompt_id() -> str | None:
    return _CURRENT_PROMPT_ID.get()


@contextmanager
def prompt_benchmark_scope(
    prompt: Any,
    *,
    generation: str | None = None,
    labels: Mapping[str, Any] | None = None,
    source: str = "EXPLICIT",
) -> Iterator[PromptSpan]:
    span = GLOBAL_CONTINUOUS_BENCHMARK.begin_prompt(
        prompt,
        generation=generation,
        labels=labels,
        source=source,
    )
    token = _CURRENT_PROMPT_ID.set(span.prompt_id)
    try:
        yield span
    except Exception as exc:
        GLOBAL_CONTINUOUS_BENCHMARK.finish_prompt(
            span.prompt_id,
            status="ERROR",
            success=False,
            outcome={"exception_type": type(exc).__name__},
            generation=span.generation,
        )
        raise
    else:
        if span.prompt_id in GLOBAL_CONTINUOUS_BENCHMARK._open:
            GLOBAL_CONTINUOUS_BENCHMARK.finish_prompt(
                span.prompt_id,
                status="SCOPE_COMPLETE",
                success=None,
                generation=span.generation,
            )
    finally:
        _CURRENT_PROMPT_ID.reset(token)


def record_octopus_route(
    payload: Mapping[str, Any],
    decision: Mapping[str, Any],
    *,
    generation: str | None = None,
) -> str | None:
    """Record every OCTOPUS route without changing routing semantics.

    If a host opened a full prompt scope, the route attaches to it. Otherwise a
    short implicit route-only span is created so route telemetry is still
    continuous for every call that actually crosses OCTOPUS.
    """

    try:
        prompt_id = current_prompt_id()
        if prompt_id is not None:
            GLOBAL_CONTINUOUS_BENCHMARK.record_route(
                prompt_id, decision, generation=generation
            )
            return prompt_id

        span = GLOBAL_CONTINUOUS_BENCHMARK.begin_prompt(
            payload,
            generation=generation,
            labels={"scope": "route_only"},
            source="IMPLICIT_OCTOPUS_ROUTE",
        )
        GLOBAL_CONTINUOUS_BENCHMARK.record_route(
            span.prompt_id, decision, generation=span.generation
        )
        GLOBAL_CONTINUOUS_BENCHMARK.finish_prompt(
            span.prompt_id,
            status="ROUTE_ONLY",
            success=None,
            metrics={"fanout_count": len(decision.get("route_mask") or [])},
            generation=span.generation,
        )
        return span.prompt_id
    except Exception as exc:
        GLOBAL_CONTINUOUS_BENCHMARK.mark_degraded(exc)
        warnings.warn(
            f"continuous benchmark degraded: {type(exc).__name__}: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )
        return None


__all__ = [
    "EVENT_SCHEMA",
    "SCHEMA",
    "VERSION",
    "ContinuousBenchmarkLedger",
    "PromptSpan",
    "benchmark_status",
    "commitment",
    "configure_continuous_benchmark",
    "current_prompt_id",
    "prompt_benchmark_scope",
    "record_octopus_route",
]
