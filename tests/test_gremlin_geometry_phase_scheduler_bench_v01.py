from tools.gremlin_geometry_phase_scheduler_bench_v01 import run_benchmark


def test_geometry_phase_scheduler_synthetic_benchmark_passes_without_token_claim():
    receipt = run_benchmark(items_per_topic=10)
    summary = receipt["summary"]
    assert receipt["verdict"] == "PASS_SYNTHETIC_GEOMETRY_SCHEDULING"
    assert summary["transition_reduction_vs_fifo_proxy"] > 0.20
    assert summary["lexical_overlap_gain"] > 0.05
    assert summary["topic_purity_gain"] > 0.20
    assert summary["actual_model_token_accounting"] is False
    assert summary["token_saving_claim"] is False
    assert summary["external_effects"] is False
    assert summary["canon_allowed"] is False
