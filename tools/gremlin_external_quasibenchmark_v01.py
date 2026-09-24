from __future__ import annotations
import json
from pathlib import Path
from statistics import mean

DEFAULT = Path("benchmarks/GREMLIN_EXTERNAL_BENCHMARK_GRAPH_V0_1.json")

def pct_reduction(before: float, after: float) -> float:
    return 100.0 * (before - after) / before

def build_quasistats(graph: dict) -> dict:
    obs = {row["id"]: row for row in graph["observations"]}
    g110, g550, g1100 = (obs["obs:gremlin:110"], obs["obs:gremlin:550"], obs["obs:gremlin:1100"])
    # Fixture-specific linear interpolation only: not a universal threshold.
    y0, y1 = g110["context_reduction_pct"], g550["context_reduction_pct"]
    x0, x1 = g110["input_sentences"], g550["input_sentences"]
    crossover = x0 + (0.0 - y0) * (x1 - x0) / (y1 - y0)

    adk = obs["obs:google-adk2:illustrative"]
    mag = [
        obs["obs:magentic-one:gaia"]["value"],
        obs["obs:magentic-one:assistantbench"]["value"],
        obs["obs:magentic-one:webarena"]["value"],
    ]
    task5_ids = [
        "obs:aimultiple:task5:autogen",
        "obs:aimultiple:task5:langgraph",
        "obs:aimultiple:task5:langchain",
    ]
    task5 = [obs[i] for i in task5_ids]
    ref = task5[0]
    normalized = {
        row["framework"].split(":")[-1]: {
            "token_ratio": row["prompt_tokens"] / ref["prompt_tokens"],
            "latency_ratio": row["median_latency_s"] / ref["median_latency_s"],
        }
        for row in task5
    }
    return {
        "schema": "GREMLIN_EXTERNAL_QUASISTATS_V0_1",
        "claim_boundary": "Derived descriptors only; cross-source metrics are not an overall ranking.",
        "GREMLIN_fixture_linear_context_break_even_sentences": crossover,
        "GREMLIN_large_context_mean_context_reduction_pct": mean([
            g550["context_reduction_pct"], g1100["context_reduction_pct"]
        ]),
        "GREMLIN_mean_route_latency_reduction_pct_across_3_sizes": mean([
            g110["latency_reduction_pct"], g550["latency_reduction_pct"], g1100["latency_reduction_pct"]
        ]),
        "GREMLIN_dispatch_reduction_pct_all_3_sizes": mean([
            g110["dispatch_reduction_pct"], g550["dispatch_reduction_pct"], g1100["dispatch_reduction_pct"]
        ]),
        "MagenticOne_unweighted_mean_reported_completion_pct": mean(mag),
        "Google_ADK2_illustrative_token_reduction_pct": pct_reduction(
            adk["vanilla_tokens_per_run"], adk["workflow_tokens_per_run"]
        ),
        "Google_ADK2_illustrative_latency_reduction_pct": pct_reduction(
            adk["vanilla_latency_s"], adk["workflow_latency_s"]
        ),
        "AIMultiple_Task5_normalized_to_AutoGen": normalized,
    }

def main() -> None:
    graph = json.loads(DEFAULT.read_text(encoding="utf-8"))
    print(json.dumps(build_quasistats(graph), indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
