from gremlin_mcp.external_eval import (
    aggregate_browsecomp_plus,
    build_browsecomp_plus_run,
    extract_citation_docids,
    score_browsecomp_plus_run,
    validate_browsecomp_plus_run,
)


def test_build_run_matches_required_browsecomp_plus_shape():
    run = build_browsecomp_plus_run(
        query_id="q1",
        output_text="Answer [101] and support 【202, 303】.",
        retrieved_docids=[303, "101", "202", "101"],
        tool_call_counts={"search": 3, "fetch": 2},
        metadata={"planner": "v0.2"},
    )
    assert run["query_id"] == "q1"
    assert run["status"] == "completed"
    assert run["retrieved_docids"] == ["101", "202", "303"]
    assert run["result"] == [{"type": "output_text", "output": "Answer [101] and support 【202, 303】."}]
    assert validate_browsecomp_plus_run(run)["valid"] is True


def test_citation_parser_supports_ascii_and_fullwidth_groups():
    assert extract_citation_docids("A [12] B [7, 9] C 【13】 D 【21, 22】") == ["7", "9", "12", "13", "21", "22"]


def test_score_computes_retrieval_and_citation_metrics_without_faking_answer_grade():
    run = build_browsecomp_plus_run(
        query_id="q2",
        output_text="Final answer supported by [11, 12].",
        retrieved_docids=["11", "12", "13", "99"],
        tool_call_counts={"search": 2, "fetch": 4},
    )
    score = score_browsecomp_plus_run(run, relevant_docids=["11", "12", "13", "14"])
    assert score["retrieval"]["recall"] == 0.75
    assert score["retrieval"]["precision"] == 0.75
    assert score["citations"]["precision"] == 1.0
    assert score["citations"]["recall"] == 0.5
    assert score["total_tool_calls"] == 6
    assert score["answer_correctness"] is None
    assert score["answer_correctness_status"] == "EXTERNAL_SEMANTIC_JUDGE_REQUIRED"


def test_invalid_run_fails_closed():
    invalid = {
        "query_id": "",
        "tool_call_counts": {"search": -1},
        "status": "completed",
        "retrieved_docids": [],
        "result": [],
    }
    validation = validate_browsecomp_plus_run(invalid)
    assert validation["valid"] is False
    assert "MISSING_QUERY_ID" in validation["errors"]
    assert "INVALID_TOOL_CALL_COUNT" in validation["errors"]
    assert "MISSING_RESULT" in validation["errors"]


def test_aggregate_preserves_external_judge_boundary():
    run1 = build_browsecomp_plus_run(
        query_id="q1",
        output_text="A [1]",
        retrieved_docids=[1, 2],
        tool_call_counts={"search": 1},
    )
    run2 = build_browsecomp_plus_run(
        query_id="q2",
        output_text="B [3]",
        retrieved_docids=[3],
        tool_call_counts={"search": 2},
    )
    scores = [
        score_browsecomp_plus_run(run1, relevant_docids=[1, 2]),
        score_browsecomp_plus_run(run2, relevant_docids=[3, 4]),
    ]
    agg = aggregate_browsecomp_plus(scores)
    assert agg["query_count"] == 2
    assert agg["completion_rate"] == 1.0
    assert agg["mean_retrieval_recall"] == 0.75
    assert agg["mean_citation_precision"] == 1.0
    assert agg["mean_citation_recall"] == 0.5
    assert agg["mean_tool_calls"] == 1.5
    assert agg["answer_accuracy"] is None
    assert agg["answer_accuracy_status"] == "EXTERNAL_SEMANTIC_JUDGE_REQUIRED"
