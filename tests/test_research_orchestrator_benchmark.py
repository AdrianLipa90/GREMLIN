from benchmarks.gremlin_research_orchestrator_v01 import CASES, run_benchmark


def test_benchmark_is_deterministic_at_semantic_level():
    first = run_benchmark(repetitions=120)
    second = run_benchmark(repetitions=120)
    assert first["case_count"] == second["case_count"] == len(CASES)
    assert [row["gremlin_route"] for row in first["cases"]] == [row["gremlin_route"] for row in second["cases"]]
    assert [row["actual_stages"] for row in first["cases"]] == [row["actual_stages"] for row in second["cases"]]
    # Timings are intentionally excluded from deterministic equality.


def test_broadcast_baseline_always_has_full_recall_but_lower_selectivity():
    result = run_benchmark(repetitions=120)
    assert result["broadcast_baseline"]["recall"] == 1.0
    assert result["broadcast_baseline"]["avg_dispatched_specialists"] == result["specialist_count"]
    assert result["gremlin"]["avg_dispatched_specialists"] <= result["broadcast_baseline"]["avg_dispatched_specialists"]


def test_benchmark_scope_does_not_misrepresent_external_products():
    result = run_benchmark(repetitions=120)
    assert "NOT_AN_ACTUAL_PERPLEXITY_SERVICE_BENCHMARK" in result["not_claimed"]
    assert "NOT_A_MODEL_ANSWER_QUALITY_BENCHMARK" in result["not_claimed"]
    assert "NOT_A_WEB_INDEX_QUALITY_BENCHMARK" in result["not_claimed"]
