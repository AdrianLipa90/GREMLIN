from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

SCHEMA = "GREMLIN_PAPER_AUDIT_EVAL_V0_1"
VERSION = "0.1.0"


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _ids(values: Iterable[Any]) -> list[str]:
    rows = {str(value).strip() for value in values if str(value).strip()}
    return sorted(rows)


def score_issue_detection(
    *,
    benchmark_id: str,
    detected_issue_ids: Iterable[Any],
    relevant_issue_ids: Iterable[Any],
) -> dict[str, Any]:
    bid = str(benchmark_id).strip()
    if not bid:
        raise ValueError("benchmark_id must be non-empty")

    detected = _ids(detected_issue_ids)
    relevant = _ids(relevant_issue_ids)
    detected_set = set(detected)
    relevant_set = set(relevant)
    hits = sorted(detected_set & relevant_set)
    false_positives = sorted(detected_set - relevant_set)
    misses = sorted(relevant_set - detected_set)

    if not relevant:
        core = {
            "schema": SCHEMA,
            "version": VERSION,
            "benchmark_id": bid,
            "status": "NO_GROUND_TRUTH_FAIL_CLOSED",
            "detected_issue_ids": detected,
            "relevant_issue_ids": relevant,
            "hits": [],
            "false_positives": false_positives,
            "misses": [],
            "detected_count": len(detected),
            "relevant_count": 0,
            "hit_count": 0,
            "false_positive_count": len(false_positives),
            "miss_count": 0,
            "precision": None,
            "recall": None,
            "f1": None,
            "authority": _authority(),
        }
        core["score_commitment"] = _commit(b"GREMLIN-PAPER-AUDIT-SCORE/v0.1", core)
        return core

    precision = len(hits) / len(detected) if detected else 0.0
    recall = len(hits) / len(relevant)
    f1 = 2.0 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "benchmark_id": bid,
        "status": "SCORED",
        "detected_issue_ids": detected,
        "relevant_issue_ids": relevant,
        "hits": hits,
        "false_positives": false_positives,
        "misses": misses,
        "detected_count": len(detected),
        "relevant_count": len(relevant),
        "hit_count": len(hits),
        "false_positive_count": len(false_positives),
        "miss_count": len(misses),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "authority": _authority(),
    }
    core["score_commitment"] = _commit(b"GREMLIN-PAPER-AUDIT-SCORE/v0.1", core)
    return core


def aggregate_issue_scores(scores: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(scores)
    if not rows:
        raise ValueError("at least one score is required")
    if any(row.get("schema") != SCHEMA for row in rows):
        raise ValueError("mixed or invalid paper-audit score schema")
    scored = [row for row in rows if row.get("status") == "SCORED"]
    if not scored:
        core = {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "NO_SCORED_BENCHMARKS_FAIL_CLOSED",
            "benchmark_count": len(rows),
            "scored_benchmark_count": 0,
            "macro_precision": None,
            "macro_recall": None,
            "macro_f1": None,
            "authority": _authority(),
        }
        core["aggregate_commitment"] = _commit(b"GREMLIN-PAPER-AUDIT-AGGREGATE/v0.1", core)
        return core

    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "SCORED",
        "benchmark_count": len(rows),
        "scored_benchmark_count": len(scored),
        "macro_precision": sum(float(row["precision"]) for row in scored) / len(scored),
        "macro_recall": sum(float(row["recall"]) for row in scored) / len(scored),
        "macro_f1": sum(float(row["f1"]) for row in scored) / len(scored),
        "authority": _authority(),
    }
    core["aggregate_commitment"] = _commit(b"GREMLIN-PAPER-AUDIT-AGGREGATE/v0.1", core)
    return core
