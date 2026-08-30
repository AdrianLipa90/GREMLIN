from __future__ import annotations

from collections import defaultdict
import math
from typing import Any, Iterable, Mapping


def parse_qrels(text: str) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = defaultdict(dict)
    for line_no, raw in enumerate(str(text).splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 4:
            raise ValueError(f"invalid qrel line {line_no}: expected 4 columns")
        qid, _, docid, relevance_raw = parts
        try:
            relevance = float(relevance_raw)
        except ValueError as exc:
            raise ValueError(f"invalid qrel relevance at line {line_no}") from exc
        out[qid][docid] = relevance
    return {qid: dict(rows) for qid, rows in out.items()}


def parse_trec_run(text: str) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line_no, raw in enumerate(str(text).splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 6:
            raise ValueError(f"invalid TREC run line {line_no}: expected 6 columns")
        qid, _, docid, rank_raw, score_raw, tag = parts
        try:
            rank = int(rank_raw)
            score = float(score_raw)
        except ValueError as exc:
            raise ValueError(f"invalid rank/score at line {line_no}") from exc
        if rank < 1:
            raise ValueError(f"invalid rank at line {line_no}")
        out[qid].append({"docid": docid, "rank": rank, "score": score, "tag": tag})
    for rows in out.values():
        rows.sort(key=lambda row: (row["rank"], -row["score"], row["docid"]))
    return {qid: rows for qid, rows in out.items()}


def build_trec_run(
    rankings: Mapping[str, Iterable[Mapping[str, Any] | tuple[str, float] | str]],
    *,
    tag: str = "GREMLIN",
) -> str:
    safe_tag = str(tag).strip().replace(" ", "_") or "GREMLIN"
    lines: list[str] = []
    for qid in sorted(str(key) for key in rankings):
        seen: set[str] = set()
        rank = 0
        for item in rankings[qid]:
            if isinstance(item, Mapping):
                docid = str(item.get("docid") or "").strip()
                score = float(item.get("score", 0.0))
            elif isinstance(item, tuple):
                docid = str(item[0]).strip()
                score = float(item[1])
            else:
                docid = str(item).strip()
                score = 0.0
            if not docid or docid in seen:
                continue
            seen.add(docid)
            rank += 1
            lines.append(f"{qid} Q0 {docid} {rank} {score:.12g} {safe_tag}")
    return "\n".join(lines) + ("\n" if lines else "")


def _gain(rel: float) -> float:
    return (2.0 ** max(0.0, rel)) - 1.0


def _dcg(relevances: Iterable[float]) -> float:
    total = 0.0
    for index, rel in enumerate(relevances, start=1):
        total += _gain(float(rel)) / math.log2(index + 1.0)
    return total


def score_query(
    ranking: Iterable[Mapping[str, Any]],
    qrels: Mapping[str, float],
    *,
    cutoffs: Iterable[int] = (5, 100, 1000),
    ndcg_k: int = 10,
) -> dict[str, Any]:
    rows = list(ranking)
    relevant = {docid for docid, rel in qrels.items() if float(rel) > 0.0}
    result: dict[str, Any] = {"relevant_count": len(relevant)}
    for k in cutoffs:
        kk = int(k)
        if kk < 1:
            raise ValueError("cutoffs must be positive")
        retrieved = {str(row["docid"]) for row in rows[:kk]}
        result[f"recall@{kk}"] = (len(retrieved & relevant) / len(relevant)) if relevant else 0.0

    actual = [float(qrels.get(str(row["docid"]), 0.0)) for row in rows[: int(ndcg_k)]]
    ideal = sorted((float(value) for value in qrels.values()), reverse=True)[: int(ndcg_k)]
    ideal_dcg = _dcg(ideal)
    result[f"ndcg@{int(ndcg_k)}"] = (_dcg(actual) / ideal_dcg) if ideal_dcg > 0.0 else 0.0
    return result


def evaluate_trec(
    run_text: str,
    qrel_text: str,
    *,
    cutoffs: Iterable[int] = (5, 100, 1000),
    ndcg_k: int = 10,
) -> dict[str, Any]:
    run = parse_trec_run(run_text)
    qrels = parse_qrels(qrel_text)
    qids = sorted(qrels)
    if not qids:
        raise ValueError("qrels contain no queries")
    per_query = {
        qid: score_query(run.get(qid, []), qrels[qid], cutoffs=cutoffs, ndcg_k=ndcg_k)
        for qid in qids
    }
    metrics: dict[str, float] = {}
    keys = [f"recall@{int(k)}" for k in cutoffs] + [f"ndcg@{int(ndcg_k)}"]
    for key in keys:
        metrics[key] = sum(float(per_query[qid][key]) for qid in qids) / len(qids)
    return {
        "query_count": len(qids),
        "metrics": metrics,
        "per_query": per_query,
        "scope": "DEPENDENCY_FREE_REFERENCE_SCORER_VALIDATE_AGAINST_PYSERINI_BEFORE_LEADERBOARD_USE",
    }
