from __future__ import annotations

from dataclasses import dataclass, field, asdict, is_dataclass
from functools import wraps
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import threading
import time
import warnings
from typing import Any, Callable, Mapping, TypeVar, cast

SCHEMA = "GREMLIN_OWL_RUNTIME_AUDIT_V0_1"
VERSION = "0.1.0"
EVENT_SCHEMA = "GREMLIN_OWL_USE_RECEIPT_V0_1"
CANDIDATE_SCHEMA = "GREMLIN_OWL_IMPROVEMENT_CANDIDATE_V0_1"
ZERO_HASH = "0" * 64
F = TypeVar("F", bound=Callable[..., Any])

_OBSERVABLE_KEYS = {
    "retry_count", "retries", "tool_calls", "memory_reads", "memory_writes",
    "tokens_in", "tokens_out", "input_tokens", "output_tokens",
    "latency_ms", "duration_ms",
}


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
    if is_dataclass(value) and not isinstance(value, type):
        return _normalize(asdict(value), depth + 1)
    if isinstance(value, Mapping):
        return {str(k): _normalize(v, depth + 1) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if isinstance(value, (list, tuple)):
        return [_normalize(v, depth + 1) for v in value]
    if isinstance(value, (set, frozenset)):
        values = [_normalize(v, depth + 1) for v in value]
        return sorted(values, key=lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False))
    return {"type": type(value).__name__, "repr_digest": _digest(repr(value).encode("utf-8", "replace"))}


def commitment(value: Any) -> str:
    payload = json.dumps(
        _normalize(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return _digest(payload)


def _canonical(record: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(record), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _observable_metrics(value: Any, depth: int = 0) -> dict[str, float]:
    if depth > 4 or not isinstance(value, Mapping):
        return {}
    out: dict[str, float] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key)
        if key in _OBSERVABLE_KEYS:
            number = _number(raw_value)
            if number is not None:
                out[key] = number
        if key in {"metrics", "telemetry", "usage", "statistics", "stats"} and isinstance(raw_value, Mapping):
            for nested_key, nested_value in _observable_metrics(raw_value, depth + 1).items():
                out.setdefault(nested_key, nested_value)
    return out


@dataclass
class OnlineStat:
    count: int = 0
    mean: float = 0.0
    m2: float = 0.0
    minimum: float | None = None
    maximum: float | None = None
    ewma: float | None = None

    def update(self, value: float, alpha: float = 0.2) -> None:
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        self.m2 += delta * (value - self.mean)
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)
        self.ewma = value if self.ewma is None else alpha * value + (1.0 - alpha) * self.ewma

    @property
    def stddev(self) -> float:
        variance = self.m2 / (self.count - 1) if self.count > 1 else 0.0
        return math.sqrt(max(0.0, variance))

    def snapshot(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "mean": self.mean,
            "stddev": self.stddev,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "ewma": self.ewma,
        }


@dataclass
class ToolStats:
    calls: int = 0
    successes: int = 0
    errors: int = 0
    latency_ns: OnlineStat = field(default_factory=OnlineStat)
    observable: dict[str, OnlineStat] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "successes": self.successes,
            "errors": self.errors,
            "error_rate": self.errors / self.calls if self.calls else 0.0,
            "latency_ns": self.latency_ns.snapshot(),
            "observable": {k: v.snapshot() for k, v in sorted(self.observable.items())},
        }


@dataclass(frozen=True)
class AuditSpan:
    trace_id: str
    tool: str
    started_unix_ns: int
    call_commitment: str
    labels: dict[str, str]


class OwlRuntimeAuditor:
    """Append-only, non-actuating runtime evidence layer for OWL."""

    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        self._lock = threading.RLock()
        self._path = self._resolve_path(path)
        self._fsync = os.environ.get("GREMLIN_OWL_AUDIT_FSYNC", "").strip().casefold() in {"1", "true", "yes", "on"}
        self._sequence = 0
        self._previous_hash = ZERO_HASH
        self._events = 0
        self._tool_stats: dict[str, ToolStats] = {}
        self._candidate_keys: set[str] = set()
        self._recent_candidates: list[dict[str, Any]] = []
        self._health = "PASS"
        self._last_error: str | None = None
        self._load_existing()

    @staticmethod
    def _resolve_path(path: str | os.PathLike[str] | None) -> Path | None:
        if path is not None:
            raw = str(path).strip()
            return None if raw == ":memory:" else Path(raw).expanduser()
        configured = os.environ.get("GREMLIN_OWL_AUDIT_PATH", "").strip()
        if configured:
            return None if configured == ":memory:" else Path(configured).expanduser()
        try:
            from gremlin_mcp.install.paths import resolve_paths
            return Path(resolve_paths().logs_dir) / "owl-runtime-audit-v01.jsonl"
        except Exception:
            return Path.home() / ".gremlin" / "logs" / "owl-runtime-audit-v01.jsonl"

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
                        raise ValueError("OWL ledger sequence discontinuity")
                    if record.get("previous_record_hash") != previous:
                        raise ValueError("OWL ledger hash-chain discontinuity")
                    body = dict(record)
                    actual_hash = body.pop("record_hash", None)
                    if actual_hash != _digest(_canonical(body)):
                        raise ValueError("OWL ledger record hash mismatch")
                    sequence += 1
                    previous = str(actual_hash)
                    self._replay(record)
            self._sequence = sequence
            self._previous_hash = previous
        except Exception as exc:
            self.mark_degraded(exc)

    def _replay(self, record: Mapping[str, Any]) -> None:
        if record.get("record_type") == "USE_RECEIPT":
            self._apply_event(record)
        elif record.get("record_type") == "IMPROVEMENT_CANDIDATE":
            key = str(record.get("candidate_key", ""))
            if key:
                self._candidate_keys.add(key)
            self._recent_candidates.append(dict(record))
            self._recent_candidates = self._recent_candidates[-100:]

    def begin(self, tool: str, args: tuple[Any, ...], kwargs: Mapping[str, Any]) -> AuditSpan:
        name = str(tool).strip()
        if not name:
            raise ValueError("OWL audit tool name must be non-empty")
        labels: dict[str, str] = {}
        for key in ("species", "operation", "surface", "tier"):
            value = kwargs.get(key)
            if isinstance(value, (str, int)) and str(value).strip():
                labels[key] = str(value).strip()[:96]
        return AuditSpan(
            trace_id=f"owl-{secrets.token_hex(12)}",
            tool=name,
            started_unix_ns=time.time_ns(),
            call_commitment=commitment({"args": args, "kwargs": kwargs}),
            labels=labels,
        )

    def finish_success(self, span: AuditSpan, result: Any) -> dict[str, Any]:
        return self._finish(span, "PASS", result, None, None)

    def finish_error(self, span: AuditSpan, exc: BaseException, error_code: str | None = None) -> dict[str, Any]:
        return self._finish(
            span,
            "ERROR",
            None,
            str(error_code).strip() if error_code else type(exc).__name__,
            type(exc).__name__,
        )

    def _finish(
        self,
        span: AuditSpan,
        status: str,
        result: Any,
        error_code: str | None,
        exception_type: str | None,
    ) -> dict[str, Any]:
        finished = time.time_ns()
        record = {
            "schema": EVENT_SCHEMA,
            "record_type": "USE_RECEIPT",
            "trace_id": span.trace_id,
            "tool": span.tool,
            "started_unix_ns": span.started_unix_ns,
            "finished_unix_ns": finished,
            "duration_ns": max(0, finished - span.started_unix_ns),
            "status": status,
            "call_commitment": span.call_commitment,
            "output_commitment": commitment(result) if status == "PASS" else None,
            "error_code": error_code,
            "exception_type": exception_type,
            "observable_metrics": _observable_metrics(result) if status == "PASS" else {},
            "labels": dict(span.labels),
            "runtime_context": {
                "build_id": os.environ.get("GREMLIN_BUILD_ID") or None,
                "config_hash": os.environ.get("GREMLIN_CONFIG_HASH") or None,
                "hypercrystal_version": os.environ.get("GREMLIN_HYPERCRYSTAL_VERSION") or None,
            },
            "authority": {"observes_only": True, "mutation_allowed": False, "canon_allowed": False},
        }
        with self._lock:
            stored = self._append(record)
            self._apply_event(stored)
            self._maybe_candidates(span.tool)
            return dict(stored)

    def _append(self, record: Mapping[str, Any]) -> dict[str, Any]:
        body = dict(record)
        body["sequence"] = self._sequence + 1
        body["previous_record_hash"] = self._previous_hash
        body["record_hash"] = _digest(_canonical(body))
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")
                handle.flush()
                if self._fsync:
                    os.fsync(handle.fileno())
        self._sequence = int(body["sequence"])
        self._previous_hash = str(body["record_hash"])
        return body

    def _apply_event(self, record: Mapping[str, Any]) -> None:
        tool = str(record["tool"])
        stats = self._tool_stats.setdefault(tool, ToolStats())
        stats.calls += 1
        self._events += 1
        if record.get("status") == "PASS":
            stats.successes += 1
        else:
            stats.errors += 1
        duration = _number(record.get("duration_ns"))
        if duration is not None:
            stats.latency_ns.update(duration)
        metrics = record.get("observable_metrics")
        if isinstance(metrics, Mapping):
            for raw_name, raw_value in metrics.items():
                number = _number(raw_value)
                if number is not None:
                    stats.observable.setdefault(str(raw_name), OnlineStat()).update(number)

    def _emit_candidate(
        self,
        tool: str,
        kind: str,
        finding: str,
        evidence: Mapping[str, Any],
        proposal: str,
    ) -> None:
        key = f"{tool}:{kind}"
        if key in self._candidate_keys:
            return
        candidate = {
            "schema": CANDIDATE_SCHEMA,
            "record_type": "IMPROVEMENT_CANDIDATE",
            "candidate_key": key,
            "tool": tool,
            "kind": kind,
            "finding": finding,
            "evidence": dict(evidence),
            "proposal": proposal,
            "status": "CANDIDATE_ONLY",
            "auto_apply": False,
            "authority": {"observes_only": True, "mutation_allowed": False, "canon_allowed": False},
        }
        stored = self._append(candidate)
        self._candidate_keys.add(key)
        self._recent_candidates.append(stored)
        self._recent_candidates = self._recent_candidates[-100:]

    def _maybe_candidates(self, tool: str) -> None:
        stats = self._tool_stats[tool]
        if stats.calls >= 20 and stats.errors >= 3:
            rate = stats.errors / stats.calls
            if rate >= 0.05:
                self._emit_candidate(
                    tool,
                    "ERROR_RATE",
                    "Observed error rate crossed the deterministic OWL v0.1 review threshold.",
                    {"calls": stats.calls, "errors": stats.errors, "error_rate": rate},
                    "Route this tool to HOUND for failure clustering and test-target generation.",
                )
        if stats.calls >= 30 and stats.latency_ns.ewma is not None:
            mean = stats.latency_ns.mean
            stddev = stats.latency_ns.stddev
            threshold = mean + max(2.0 * stddev, 0.25 * mean)
            if stats.latency_ns.ewma > threshold:
                self._emit_candidate(
                    tool,
                    "LATENCY_REGRESSION",
                    "Recent EWMA latency exceeded the deterministic OWL v0.1 historical threshold.",
                    {
                        "calls": stats.calls,
                        "mean_latency_ns": mean,
                        "stddev_latency_ns": stddev,
                        "ewma_latency_ns": stats.latency_ns.ewma,
                        "threshold_ns": threshold,
                    },
                    "Run an exact-config before/after benchmark and inspect routing depth before changing runtime policy.",
                )
        retry = stats.observable.get("retry_count") or stats.observable.get("retries")
        if retry is not None and retry.count >= 20 and retry.mean >= 0.5:
            self._emit_candidate(
                tool,
                "RETRY_BURDEN",
                "Observed retries are persistently non-trivial.",
                {"samples": retry.count, "mean_retries": retry.mean},
                "Route retry traces to HOUND and compare failing route/configuration classes.",
            )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "schema": SCHEMA,
                "version": VERSION,
                "status": self._health,
                "last_error": self._last_error,
                "ledger_path": str(self._path) if self._path is not None else None,
                "persistent": self._path is not None,
                "record_count": self._sequence,
                "event_count": self._events,
                "head_hash": self._previous_hash,
                "tools": {k: v.snapshot() for k, v in sorted(self._tool_stats.items())},
                "recent_candidates": [dict(v) for v in self._recent_candidates[-20:]],
                "policy": {
                    "raw_payload_persisted": False,
                    "append_only": True,
                    "hash_chained": True,
                    "candidate_auto_apply": False,
                    "observes_only": True,
                },
                "authority": {
                    "production_runtime_write": False,
                    "execution_admitted": False,
                    "canon_allowed": False,
                },
            }


GLOBAL_OWL_AUDITOR = OwlRuntimeAuditor()


def _warn(exc: BaseException) -> None:
    GLOBAL_OWL_AUDITOR.mark_degraded(exc)
    warnings.warn(
        f"OWL runtime audit degraded: {type(exc).__name__}: {exc}",
        RuntimeWarning,
        stacklevel=3,
    )


def begin_use(tool: str, args: tuple[Any, ...], kwargs: Mapping[str, Any]) -> AuditSpan | None:
    try:
        return GLOBAL_OWL_AUDITOR.begin(tool, args, kwargs)
    except Exception as exc:
        _warn(exc)
        return None


def finish_use_success(span: AuditSpan | None, result: Any) -> dict[str, Any] | None:
    if span is None:
        return None
    try:
        return GLOBAL_OWL_AUDITOR.finish_success(span, result)
    except Exception as exc:
        _warn(exc)
        return None


def finish_use_error(
    span: AuditSpan | None,
    exc: BaseException,
    error_code: str | None = None,
) -> dict[str, Any] | None:
    if span is None:
        return None
    try:
        return GLOBAL_OWL_AUDITOR.finish_error(span, exc, error_code)
    except Exception as audit_exc:
        _warn(audit_exc)
        return None


def audit_status() -> dict[str, Any]:
    return GLOBAL_OWL_AUDITOR.snapshot()


def owl_runtime_boundary(fn: F) -> F:
    @wraps(fn)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        span = begin_use(fn.__name__, args, kwargs)
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:
            finish_use_error(span, exc)
            raise
        finish_use_success(span, result)
        return result
    return cast(F, wrapped)
