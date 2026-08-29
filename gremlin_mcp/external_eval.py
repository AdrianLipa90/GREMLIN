from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable, Mapping

SCHEMA = "GREMLIN_EXTERNAL_RESEARCH_EVAL_V0_1"
VERSION = "0.1.0"
BROWSECOMP_PLUS_CONTRACT = "BROWSECOMP_PLUS_RUN_COMPAT_V0_1"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _docid(value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("document id must be non-empty")
    return text


def normalize_docids(values: Iterable[Any]) -> list[str]:
    return sorted({_docid(value) for value in values})


def extract_citation_docids(text: str) -> list[str]:
    """Extract numeric BrowseComp-Plus-style citations from [] or full-width 【】 groups."""
    source = str(text or "")
    found: set[str] = set()
    for match in re.findall(r"\[([^\[\]]+)\]", source):
        found.update(re.findall(r"\d+", match))
    for match in re.findall(r"【([^【】]+)】", source):
        found.update(re.findall(r"\d+", match))
    return sorted(found, key=lambda value: (len(value), value))


def set_metrics(selected: Iterable[Any], relevant: Iterable[Any]) -> dict[str, Any]:
    selected_ids = normalize_docids(selected)
    relevant_ids = normalize_docids(relevant)
    selected_set = set(selected_ids)
    relevant_set = set(relevant_ids)
    hits = sorted(selected_set & relevant_set)
    precision = len(hits) / len(selected_ids) if selected_ids else 0.0
    recall = len(hits) / len(relevant_ids) if relevant_ids else 0.0
    return {
        "selected_count": len(selected_ids),
        "relevant_count": len(relevant_ids),
        "hit_count": len(hits),
        "hits": hits,
        "precision": precision,
        "recall": recall,
    }


def build_browsecomp_plus_run(
    *,
    query_id: str,
    output_text: str,
    retrieved_docids: Iterable[Any],
    tool_call_counts: Mapping[str, int] | None = None,
    status: str = "completed",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    qid = str(query_id).strip()
    if not qid:
        raise ValueError("query_id must be non-empty")
    state = str(status).strip()
    if not state:
        raise ValueError("status must be non-empty")
    counts: dict[str, int] = {}
    for key, raw in dict(tool_call_counts or {}).items():
        value = int(raw)
        if value < 0:
            raise ValueError("tool call counts must be non-negative")
        counts[str(key)] = value

    core = {
        "query_id": qid,
        "tool_call_counts": dict(sorted(counts.items())),
        "status": state,
        "retrieved_docids": normalize_docids(retrieved_docids),
        "result": [{"type": "output_text", "output": str(output_text)}],
        "metadata": {
            "orchestrator": "GREMLIN",
            "external_eval_contract": BROWSECOMP_PLUS_CONTRACT,
            **dict(metadata or {}),
        },
    }
    core["metadata"]["run_commitment"] = _commit(
        b"GREMLIN-BROWSECOMP-PLUS-RUN/v0.1",
        {key: value for key, value in core.items() if key != "metadata"},
    )
    return core


def validate_browsecomp_plus_run(run: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    qid = str(run.get("query_id") or "").strip()
    if not qid:
        errors.append("MISSING_QUERY_ID")
    status = run.get("status")
    if not isinstance(status, str) or not status.strip():
        errors.append("MISSING_STATUS")
    counts = run.get("tool_call_counts")
    if not isinstance(counts, Mapping):
        errors.append("TOOL_CALL_COUNTS_NOT_OBJECT")
    else:
        for key, value in counts.items():
            if not isinstance(key, str) or not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append("INVALID_TOOL_CALL_COUNT")
                break
    retrieved = run.get("retrieved_docids")
    if not isinstance(retrieved, list) or any(not str(value).strip() for value in retrieved):
        errors.append("INVALID_RETRIEVED_DOCIDS")
    result = run.get("result")
    if not isinstance(result, list) or not result:
        errors.append("MISSING_RESULT")
    else:
        last = result[-1]
        if not isinstance(last, Mapping) or last.get("type") != "output_text" or not isinstance(last.get("output"), str):
            errors.append("INVALID_OUTPUT_TEXT")
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "contract": BROWSECOMP_PLUS_CONTRACT,
        "valid": not errors,
        "errors": errors,
    }


def score_browsecomp_plus_run(
    run: Mapping[str, Any],
    *,
    relevant_docids: Iterable[Any],
) -> dict[str, Any]:
    validation = validate_browsecomp_plus_run(run)
    if not validation["valid"]:
        raise ValueError(f"invalid BrowseComp-Plus run: {validation['errors']}")

    response = str(run["result"][-1]["output"])
    retrieved = normalize_docids(run.get("retrieved_docids") or [])
    cited = extract_citation_docids(response)
    relevant = normalize_docids(relevant_docids)
    retrieval = set_metrics(retrieved, relevant)
    citations = set_metrics(cited, relevant)
    tool_calls = {str(key): int(value) for key, value in dict(run["tool_call_counts"]).items()}
    total_tool_calls = sum(tool_calls.values())

    core = {
        "query_id": str(run["query_id"]),
        "completed": str(run["status"]) == "completed",
        "retrieval": retrieval,
        "citations": citations,
        "tool_call_counts": dict(sorted(tool_calls.items())),
        "total_tool_calls": total_tool_calls,
        "answer_correctness": None,
        "answer_correctness_status": "EXTERNAL_SEMANTIC_JUDGE_REQUIRED",
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "benchmark": "BrowseComp-Plus",
        **core,
        "score_commitment": _commit(b"GREMLIN-BROWSECOMP-PLUS-SCORE/v0.1", core),
        "scope_boundary": [
            "DETERMINISTIC_RETRIEVAL_AND_CITATION_METRICS_ONLY",
            "NO_LOCAL_SUBSTITUTE_FOR_OFFICIAL_SEMANTIC_ANSWER_JUDGE",
            "NO_BENCHMARK_DATA_VENDORED",
        ],
    }


def aggregate_browsecomp_plus(scores: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(scores)
    if not rows:
        raise ValueError("at least one score is required")
    for row in rows:
        if row.get("benchmark") != "BrowseComp-Plus":
            raise ValueError("mixed benchmark rows are not allowed")

    completed = sum(bool(row.get("completed")) for row in rows)
    retrieval_recall = sum(float(row["retrieval"]["recall"]) for row in rows) / len(rows)
    citation_precision = sum(float(row["citations"]["precision"]) for row in rows) / len(rows)
    citation_recall = sum(float(row["citations"]["recall"]) for row in rows) / len(rows)
    total_tool_calls = sum(int(row.get("total_tool_calls", 0)) for row in rows)
    core = {
        "query_count": len(rows),
        "completed_count": completed,
        "completion_rate": completed / len(rows),
        "mean_retrieval_recall": retrieval_recall,
        "mean_citation_precision": citation_precision,
        "mean_citation_recall": citation_recall,
        "total_tool_calls": total_tool_calls,
        "mean_tool_calls": total_tool_calls / len(rows),
        "answer_accuracy": None,
        "answer_accuracy_status": "EXTERNAL_SEMANTIC_JUDGE_REQUIRED",
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "benchmark": "BrowseComp-Plus",
        **core,
        "aggregate_commitment": _commit(b"GREMLIN-BROWSECOMP-PLUS-AGGREGATE/v0.1", core),
    }
