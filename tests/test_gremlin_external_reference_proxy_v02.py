from __future__ import annotations

import json
from pathlib import Path

from tools.gremlin_external_reference_proxy_v02 import build_proxy, piecewise_linear

ROOT = Path(__file__).resolve().parents[1]


def _result() -> dict:
    graph = json.loads((ROOT / "benchmarks" / "GREMLIN_EXTERNAL_BENCHMARK_GRAPH_V0_1.json").read_text(encoding="utf-8"))
    return build_proxy(graph)


def test_proxy_preserves_claim_boundary_and_authority() -> None:
    result = _result()
    assert result["status"] == "PASS_SYNTHETIC_REFERENCE_ONLY"
    assert result["canon_allowed"] is False
    assert result["synthetic_assumptions"]["quality_prediction"] is False
    assert result["synthetic_assumptions"]["competitor_runtime_emulation"] is False


def test_threshold_alignment_starts_at_three_total_domains() -> None:
    result = _result()
    assert result["summary"]["first_sgt_use_domain_count_under_proxy"] == 3
    assert result["summary"]["first_external_sharp_drop_total_domain_count"] == 3
    assert result["summary"]["first_threshold_alignment_total_domain_count"] == 3
    assert result["summary"]["first_threshold_alignment_synthetic_sentences"] == 330


def test_small_context_negative_result_is_preserved() -> None:
    rows = {r["total_domains"]: r for r in _result()["rows"]}
    assert rows[1]["gremlin_sgt_fixture_interpolated_context_reduction_pct"] < 0
    assert rows[1]["gremlin_sgt_gate_candidate"] == "BYPASS_SGT"
    assert rows[2]["gremlin_sgt_fixture_interpolated_context_reduction_pct"] < 0
    assert rows[2]["gremlin_sgt_gate_candidate"] == "BYPASS_SGT"


def test_large_input_interpolation_is_clamped_not_extrapolated() -> None:
    assert piecewise_linear(10_000) == 65.89


def test_tau_reliability_is_reference_not_gremlin_score() -> None:
    result = _result()
    tau = result["external_reference_facts"]["tau_bench_reliability"]
    assert tau["gpt4o_retail_pass1_pct_reference"] == 65.2
    assert tau["gpt4o_retail_pass8_pct_upper_bound"] == 25.0
    assert tau["reliability_drop_lower_bound_pct"] > 60.0
    assert "gremlin_pass" not in json.dumps(result).lower()
