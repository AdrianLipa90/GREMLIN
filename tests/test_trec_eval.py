import math

import pytest

from gremlin_mcp.trec_eval import (
    build_trec_run,
    evaluate_trec,
    parse_qrels,
    parse_trec_run,
    score_query,
)


def test_qrels_and_run_parsers_accept_standard_shapes():
    qrels = parse_qrels("q1 0 d1 1\nq1 0 d2 2\nq2 0 d9 1\n")
    assert qrels == {"q1": {"d1": 1.0, "d2": 2.0}, "q2": {"d9": 1.0}}

    run = parse_trec_run("q1 Q0 d2 1 9.0 GREMLIN\nq1 Q0 d1 2 8.0 GREMLIN\n")
    assert [row["docid"] for row in run["q1"]] == ["d2", "d1"]


def test_build_trec_run_deduplicates_rankings_and_assigns_monotonic_ranks():
    text = build_trec_run(
        {
            "q1": [
                {"docid": "d1", "score": 0.9},
                {"docid": "d1", "score": 0.8},
                ("d2", 0.7),
            ]
        },
        tag="GREMLIN-v01",
    )
    rows = parse_trec_run(text)["q1"]
    assert [(row["docid"], row["rank"]) for row in rows] == [("d1", 1), ("d2", 2)]
    assert all(row["tag"] == "GREMLIN-v01" for row in rows)


def test_recall_at_k_is_exact_on_small_fixture():
    ranking = [
        {"docid": "d1", "rank": 1, "score": 3.0},
        {"docid": "x", "rank": 2, "score": 2.0},
        {"docid": "d2", "rank": 3, "score": 1.0},
    ]
    score = score_query(ranking, {"d1": 1.0, "d2": 1.0, "d3": 1.0}, cutoffs=(1, 2, 3), ndcg_k=3)
    assert score["recall@1"] == pytest.approx(1 / 3)
    assert score["recall@2"] == pytest.approx(1 / 3)
    assert score["recall@3"] == pytest.approx(2 / 3)


def test_ndcg_uses_graded_relevance_and_log_discount():
    ranking = [
        {"docid": "d1", "rank": 1, "score": 3.0},
        {"docid": "d2", "rank": 2, "score": 2.0},
    ]
    qrels = {"d1": 1.0, "d2": 2.0}
    score = score_query(ranking, qrels, cutoffs=(2,), ndcg_k=2)
    actual = ((2**1 - 1) / math.log2(2)) + ((2**2 - 1) / math.log2(3))
    ideal = ((2**2 - 1) / math.log2(2)) + ((2**1 - 1) / math.log2(3))
    assert score["ndcg@2"] == pytest.approx(actual / ideal)
    assert 0.0 < score["ndcg@2"] < 1.0


def test_evaluate_trec_macro_averages_queries_in_qrels_including_missing_run_queries():
    qrels = "q1 0 d1 1\nq2 0 d2 1\n"
    run = "q1 Q0 d1 1 1.0 GREMLIN\n"
    result = evaluate_trec(run, qrels, cutoffs=(5,), ndcg_k=10)
    assert result["query_count"] == 2
    assert result["metrics"]["recall@5"] == pytest.approx(0.5)
    assert result["metrics"]["ndcg@10"] == pytest.approx(0.5)


def test_invalid_formats_fail_closed():
    with pytest.raises(ValueError):
        parse_qrels("q1 bad")
    with pytest.raises(ValueError):
        parse_trec_run("q1 Q0 d1 0 1.0 GREMLIN")
    with pytest.raises(ValueError):
        score_query([], {"d1": 1.0}, cutoffs=(0,), ndcg_k=10)
