from __future__ import annotations

from gremlin_mcp.paper_audit_eval import aggregate_issue_scores, score_issue_detection


def test_score_issue_detection_computes_precision_recall_and_f1() -> None:
    score = score_issue_detection(
        benchmark_id="fixture-1",
        detected_issue_ids=["A", "B", "X"],
        relevant_issue_ids=["A", "B", "C", "D"],
    )
    assert score["hit_count"] == 2
    assert score["false_positive_count"] == 1
    assert score["miss_count"] == 2
    assert score["precision"] == 2 / 3
    assert score["recall"] == 1 / 2
    assert 0.57 < score["f1"] < 0.58


def test_score_issue_detection_deduplicates_ids() -> None:
    score = score_issue_detection(
        benchmark_id="fixture-2",
        detected_issue_ids=["A", "A", "B"],
        relevant_issue_ids=["A", "B", "B"],
    )
    assert score["detected_count"] == 2
    assert score["relevant_count"] == 2
    assert score["precision"] == 1.0
    assert score["recall"] == 1.0
    assert score["f1"] == 1.0


def test_aggregate_issue_scores_requires_same_schema_and_reports_macro_metrics() -> None:
    a = score_issue_detection(benchmark_id="a", detected_issue_ids=["1"], relevant_issue_ids=["1", "2"])
    b = score_issue_detection(benchmark_id="b", detected_issue_ids=["x"], relevant_issue_ids=["x"])
    aggregate = aggregate_issue_scores([a, b])
    assert aggregate["benchmark_count"] == 2
    assert aggregate["macro_recall"] == 0.75
    assert aggregate["macro_precision"] == 1.0
    assert aggregate["authority"]["canon_allowed"] is False


def test_score_issue_detection_fails_closed_on_missing_ground_truth() -> None:
    score = score_issue_detection(benchmark_id="empty", detected_issue_ids=["A"], relevant_issue_ids=[])
    assert score["status"] == "NO_GROUND_TRUTH_FAIL_CLOSED"
    assert score["recall"] is None
    assert score["f1"] is None
