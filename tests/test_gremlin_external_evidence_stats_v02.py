from __future__ import annotations

import json
from pathlib import Path

from tools.gremlin_external_evidence_stats_v02 import build_stats

ROOT = Path(__file__).resolve().parents[1]
REG = json.loads(
    (ROOT / "benchmarks" / "GREMLIN_EXTERNAL_EVIDENCE_REGISTRY_V0_2.json").read_text(
        encoding="utf-8"
    )
)


def test_ratios_are_within_single_source_only() -> None:
    out = build_stats(REG)
    assert out["status"] == "PASS_DERIVED_DESCRIPTORS"
    assert out["canon_allowed"] is False
    n = out["agent_harness_normalized_to_langgraph"]
    assert n["LangGraph"]["median_latency_ratio_vs_langgraph"] == 1.0
    assert 1.30 < n["CrewAI"]["median_latency_ratio_vs_langgraph"] < 1.31
    assert 1.60 < n["AutoGen"]["median_latency_ratio_vs_langgraph"] < 1.62


def test_fixed_model_harness_lift_is_descriptor_not_gremlin_score() -> None:
    out = build_stats(REG)
    assert 13.0 < out["prism_unweighted_mean_held_out_lift_pp"] < 13.1
    assert "gremlin_score" not in json.dumps(out).lower()


def test_systems_overhead_remains_not_executed() -> None:
    out = build_stats(REG)
    assert out["gremlin_comparison_status"]["systems_overhead"] == "DESIGNED_NOT_EXECUTED"
