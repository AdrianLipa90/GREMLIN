from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

DEFAULT = Path("benchmarks/GREMLIN_EXTERNAL_EVIDENCE_REGISTRY_V0_2.json")


def build_stats(registry: dict) -> dict:
    rows = {r["id"]: r for r in registry["observations"]}
    lg = rows["obs:agent-harness:langgraph"]
    framework = {}
    for key in ("langgraph", "crewai", "autogen"):
        row = rows[f"obs:agent-harness:{key}"]
        framework[row["framework"]] = {
            "median_latency_ratio_vs_langgraph": row["median_latency_s"] / lg["median_latency_s"],
            "p95_latency_ratio_vs_langgraph": row["p95_latency_s"] / lg["p95_latency_s"],
            "cost_ratio_vs_langgraph": row["cost_per_1000_usd"] / lg["cost_per_1000_usd"],
            "token_overhead_ratio_vs_langgraph": row["token_overhead_pct"] / lg["token_overhead_pct"],
        }

    prism = rows["obs:beyond-prompts:prism"]["held_out_lift_percentage_points"]
    swarms = rows["obs:swarms:graphworkflow"]
    return {
        "schema": "GREMLIN_EXTERNAL_EVIDENCE_QUASISTATS_V0_2",
        "status": "PASS_DERIVED_DESCRIPTORS",
        "canon_allowed": False,
        "claim_boundary": "Ratios stay inside one source/methodology. Cross-source metrics are not combined into a winner score.",
        "agent_harness_normalized_to_langgraph": framework,
        "prism_unweighted_mean_held_out_lift_pp": mean(prism.values()),
        "swarms_reported_noop_systems_envelope": {
            "steady_state_geomean_speedup_x": swarms["steady_state_geomean_speedup_x"],
            "chain_200_speedup_x": swarms["chain_200_speedup_x"],
            "shallow_wide_speedup_min_x": swarms["shallow_wide_speedup_range_x"][0],
            "shallow_wide_speedup_max_x": swarms["shallow_wide_speedup_range_x"][1],
            "compile_speedup_min_x": swarms["compile_speedup_range_x"][0],
            "compile_speedup_max_x": swarms["compile_speedup_range_x"][1],
            "cold_path_speedup_x": swarms["cold_path_speedup_x"],
        },
        "gremlin_comparison_status": {
            "same_model_quality": "HARNESS_READY_MODEL_NOT_RUN",
            "systems_overhead": "DESIGNED_NOT_EXECUTED",
            "external_tau2": "ADAPTER_NOT_YET_EXECUTED",
        },
    }


if __name__ == "__main__":
    r = json.loads(DEFAULT.read_text(encoding="utf-8"))
    print(json.dumps(build_stats(r), indent=2, sort_keys=True))
