from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "benchmarks" / "GREMLIN_EXTERNAL_BENCHMARK_GRAPH_V0_1.json"
OUT = ROOT / "benchmarks" / "GREMLIN_EXTERNAL_REFERENCE_PROXY_V0_2.json"

DOMAIN_TOTALS = (1, 2, 3, 4, 7)
SENTENCES_PER_DOMAIN_PROXY = 110
DISTRACTOR_TOOLS_PER_DOMAIN = 19
SGT_ANCHORS = ((110, -17.262), (550, 31.665), (1100, 65.89))
SGT_BREAK_EVEN_SENTENCES = 265.237
GREMLIN_DISPATCH_REDUCTION_REFERENCE_PCT = 50.0
GREMLIN_RESEARCH_ORCHESTRATOR_FANOUT_REDUCTION_PCT = 61.9
TAU_RETAIL_PASS1_PCT = 65.2
TAU_RETAIL_PASS8_UPPER_BOUND_PCT = 25.0


def piecewise_linear(x: float, anchors: tuple[tuple[float, float], ...] = SGT_ANCHORS) -> float:
    """Interpolate only inside measured anchors; clamp above the largest anchor."""
    if x <= anchors[0][0]:
        return anchors[0][1]
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * ((x - x0) / (x1 - x0))
    return anchors[-1][1]


def build_proxy(graph: dict[str, Any]) -> dict[str, Any]:
    adk = next(x for x in graph["observations"] if x["id"] == "obs:google-adk2:illustrative")
    adk_token_reduction = 100.0 * (adk["vanilla_tokens_per_run"] - adk["workflow_tokens_per_run"]) / adk["vanilla_tokens_per_run"]
    adk_latency_reduction = 100.0 * (adk["vanilla_latency_s"] - adk["workflow_latency_s"]) / adk["vanilla_latency_s"]

    rows: list[dict[str, Any]] = []
    for domains in DOMAIN_TOTALS:
        distractors = domains - 1
        sentences = domains * SENTENCES_PER_DOMAIN_PROXY
        sgt_reduction = piecewise_linear(sentences)
        rows.append({
            "total_domains": domains,
            "distractor_domains": distractors,
            "synthetic_sentences": sentences,
            "distractor_tool_exposure_baseline": distractors * DISTRACTOR_TOOLS_PER_DOMAIN,
            "normalized_monolithic_domain_context_units": float(domains),
            "normalized_ideal_selective_domain_context_units": 1.0,
            "ideal_structural_domain_context_avoidance_pct": 100.0 * (1.0 - 1.0 / domains),
            "gremlin_sgt_fixture_interpolated_context_reduction_pct": sgt_reduction,
            "gremlin_sgt_gate_candidate": "USE_SGT" if sentences >= SGT_BREAK_EVEN_SENTENCES else "BYPASS_SGT",
            "langchain_same_model_sharp_drop_regime": distractors >= 2,
            "synthetic_alignment": bool(distractors >= 2 and sentences >= SGT_BREAK_EVEN_SENTENCES),
            "claim_boundary": "Structural/proxy row only; no model answer-quality value is predicted.",
        })

    aligned = [r for r in rows if r["synthetic_alignment"]]
    return {
        "schema": "GREMLIN_EXTERNAL_REFERENCE_PROXY_V0_2",
        "status": "PASS_SYNTHETIC_REFERENCE_ONLY",
        "canon_allowed": False,
        "claim_boundary": "Not a competitor execution benchmark and not a same-model answer-quality A/B. It maps published external stress regimes onto GREMLIN internal control-plane measurements using explicit synthetic assumptions.",
        "external_reference_facts": {
            "langchain_same_model_multi_agent": {
                "model": "gpt-4o",
                "dataset": "modified tau-bench retail, first 100 test examples",
                "distractor_environments_added": 6,
                "tools_per_distractor_environment": DISTRACTOR_TOOLS_PER_DOMAIN,
                "reported_pattern": "single-agent baseline falls sharply with two or more distractor domains; swarm/supervisor token cost remains flatter as distractors grow",
                "source": "https://www.langchain.com/blog/benchmarking-multi-agent-architectures",
            },
            "tau_bench_reliability": {
                "gpt4o_retail_pass1_pct_reference": TAU_RETAIL_PASS1_PCT,
                "gpt4o_retail_pass8_pct_upper_bound": TAU_RETAIL_PASS8_UPPER_BOUND_PCT,
                "pass8_retention_vs_pass1_upper_bound_pct": 100.0 * TAU_RETAIL_PASS8_UPPER_BOUND_PCT / TAU_RETAIL_PASS1_PCT,
                "reliability_drop_lower_bound_pct": 100.0 * (1.0 - TAU_RETAIL_PASS8_UPPER_BOUND_PCT / TAU_RETAIL_PASS1_PCT),
                "source": "https://sierra.ai/uk/blog/benchmarking-ai-agents",
            },
            "google_adk2_illustrative": {
                "token_reduction_pct": adk_token_reduction,
                "latency_reduction_pct": adk_latency_reduction,
                "vendor_marks_as_illustrative": True,
                "source": "https://developers.googleblog.com/why-we-built-adk-20/",
            },
        },
        "gremlin_internal_references": {
            "sgt_fixture_break_even_sentences": SGT_BREAK_EVEN_SENTENCES,
            "sgt_live_dispatch_reduction_pct": GREMLIN_DISPATCH_REDUCTION_REFERENCE_PCT,
            "research_orchestrator_fanout_reduction_pct": GREMLIN_RESEARCH_ORCHESTRATOR_FANOUT_REDUCTION_PCT,
            "sgt_anchor_points": [{"sentences": x, "context_reduction_pct": y} for x, y in SGT_ANCHORS],
        },
        "synthetic_assumptions": {
            "sentences_per_domain_proxy": SENTENCES_PER_DOMAIN_PROXY,
            "distractor_tools_per_domain": DISTRACTOR_TOOLS_PER_DOMAIN,
            "above_1100_sentence_sgt_behavior": "CLAMP_TO_LAST_MEASURED_ANCHOR",
            "quality_prediction": False,
            "competitor_runtime_emulation": False,
        },
        "rows": rows,
        "summary": {
            "first_sgt_use_domain_count_under_proxy": next(r["total_domains"] for r in rows if r["gremlin_sgt_gate_candidate"] == "USE_SGT"),
            "first_external_sharp_drop_total_domain_count": next(r["total_domains"] for r in rows if r["langchain_same_model_sharp_drop_regime"]),
            "first_threshold_alignment_total_domain_count": aligned[0]["total_domains"] if aligned else None,
            "first_threshold_alignment_synthetic_sentences": aligned[0]["synthetic_sentences"] if aligned else None,
            "mean_interpolated_sgt_context_reduction_pct_for_aligned_rows": mean(r["gremlin_sgt_fixture_interpolated_context_reduction_pct"] for r in aligned) if aligned else None,
            "verdict": "PASS_THRESHOLD_ALIGNMENT_HYPOTHESIS_NOT_QUALITY_PROOF",
        },
        "next_gate": {
            "name": "GREMLIN_EXTERNAL_SAME_MODEL_AB_V0_3",
            "required": [
                "Run one identical foundation model in monolithic, supervisor/swarm reference, and GREMLIN selective-cone conditions.",
                "Use the same tau-bench-style tasks, policy text, tools, retry budget and model temperature.",
                "Measure pass^1 and pass^k, exact final state, prompt/completion tokens, model/tool calls, median/p95 wall-clock latency and failure recovery.",
                "Do not reuse this proxy as a quality score.",
            ],
        },
    }


def main() -> dict[str, Any]:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    result = build_proxy(graph)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    result = main()
    print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))
