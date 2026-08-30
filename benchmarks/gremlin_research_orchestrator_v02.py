from __future__ import annotations

import hashlib
import json
import statistics
import time
from typing import Any

from gremlin_mcp.pipeline import SPECIALISTS
from gremlin_mcp.research_planner_v02 import build_research_plan_v02

SCHEMA = "GREMLIN_RESEARCH_ORCHESTRATOR_BENCHMARK_V0_2"
VERSION = "0.2.0"

CASES = (
    ("evidence_only", "Review the evidence, sources, citations, provenance and methodology for quantum information geometry.", ("OWL",), ("ACQUIRE_EVIDENCE",)),
    ("relation_map", "Map the relation dependency graph and topology between entropy, information geometry and gravity.", ("OWL", "SPIDER"), ("ACQUIRE_EVIDENCE", "MAP_RELATIONS")),
    ("derivation", "Derive a candidate equation and mechanism relating information geometry to a gravitational coupling.", ("OWL", "MOLE"), ("ACQUIRE_EVIDENCE", "DERIVE_CANDIDATE")),
    ("adversarial_audit", "Audit the evidence for contradictions, errors, mismatches and falsification targets in this model.", ("OWL", "HOUND"), ("ACQUIRE_EVIDENCE", "ADVERSARIAL_CHECK")),
    ("relation_plus_derivation", "Map dependencies and graph relations, then derive a candidate mechanism and equation.", ("OWL", "SPIDER", "MOLE"), ("ACQUIRE_EVIDENCE", "MAP_RELATIONS", "DERIVE_CANDIDATE")),
    ("relation_plus_audit", "Build the dependency graph and audit contradictions, regressions and evidence quality.", ("OWL", "SPIDER", "HOUND"), ("ACQUIRE_EVIDENCE", "MAP_RELATIONS", "ADVERSARIAL_CHECK")),
    ("derive_plus_audit", "Derive the formula, then validate it against contradictions, errors and regression tests.", ("OWL", "MOLE", "HOUND"), ("ACQUIRE_EVIDENCE", "DERIVE_CANDIDATE", "ADVERSARIAL_CHECK")),
    ("full_research", "Audit evidence contradictions dependencies graph and derive the relation between Shannon entropy information geometry and quantum gravity.", ("OWL", "SPIDER", "MOLE", "HOUND"), ("ACQUIRE_EVIDENCE", "MAP_RELATIONS", "DERIVE_CANDIDATE", "ADVERSARIAL_CHECK")),
    ("memory_context", "Review prior memory, earlier history and previous archived results for this research question.", ("OWL", "RAVEN"), ("ACQUIRE_EVIDENCE", "MEMORY_CONTEXT")),
    ("enumeration", "Review evidence and enumerate candidate combinations, permutations and variants across the search space.", ("OWL", "ANT"), ("ACQUIRE_EVIDENCE", "ENUMERATE_VARIANTS")),
    ("deduplication", "Review evidence and identify duplicate, redundant, obsolete or overlapping candidate branches to prune.", ("OWL", "MANTIS"), ("ACQUIRE_EVIDENCE", "PRUNE_REDUNDANCY")),
    ("mixed_generalist", "Review sources, map graph dependencies, derive a mechanism, audit contradictions, enumerate variants and prune duplicates.", ("OWL", "SPIDER", "MOLE", "HOUND", "ANT", "MANTIS"), ("ACQUIRE_EVIDENCE", "MAP_RELATIONS", "DERIVE_CANDIDATE", "ADVERSARIAL_CHECK", "ENUMERATE_VARIANTS", "PRUNE_REDUNDANCY")),
)


def _metrics(selected, expected):
    s, e = set(selected), set(expected)
    tp, fp, fn = len(s & e), len(s - e), len(e - s)
    p = tp / len(s) if s else 0.0
    r = tp / len(e) if e else 1.0
    f1 = 0.0 if p + r == 0 else 2 * p * r / (p + r)
    return tp, fp, fn, p, r, f1, s == e


def run_benchmark(repetitions: int = 8000) -> dict[str, Any]:
    rows = []
    gtp = gfp = gfn = btp = bfp = bfn = 0
    gtasks = btasks = exact = stage_exact = 0
    for case_id, query, expected_species, expected_stages in CASES:
        plan = build_research_plan_v02(query)
        selected = plan["species_union"]
        actual_stages = tuple(x["stage_id"] for x in plan["stages"])
        m = _metrics(selected, expected_species)
        bm = _metrics(SPECIALISTS, expected_species)
        gtp += m[0]; gfp += m[1]; gfn += m[2]
        btp += bm[0]; bfp += bm[1]; bfn += bm[2]
        gtasks += len(selected); btasks += len(SPECIALISTS)
        exact += int(m[6]); stage_exact += int(actual_stages == expected_stages)
        rows.append({"case_id": case_id, "expected_species": list(expected_species), "gremlin_species_union": selected, "expected_stages": list(expected_stages), "actual_stages": list(actual_stages), "exact": m[6], "stage_exact": actual_stages == expected_stages, "plan_commitment": plan["plan_commitment"], "all_stage_routes_match_targets": plan["all_stage_routes_match_targets"]})

    def agg(tp, fp, fn):
        p = tp/(tp+fp) if tp+fp else 1.0; r = tp/(tp+fn) if tp+fn else 1.0
        return {"precision": p, "recall": r, "f1": 0.0 if p+r == 0 else 2*p*r/(p+r)}

    route_ns=[]; broadcast_ns=[]
    for i in range(int(repetitions)):
        q=CASES[i%len(CASES)][1]
        t=time.perf_counter_ns(); build_research_plan_v02(q); route_ns.append(time.perf_counter_ns()-t)
        t=time.perf_counter_ns(); tuple(SPECIALISTS); broadcast_ns.append(time.perf_counter_ns()-t)
    rs=sorted(route_ns); bs=sorted(broadcast_ns)
    g=agg(gtp,gfp,gfn); b=agg(btp,bfp,bfn)
    g_eff=gtp/gtasks; b_eff=btp/btasks
    out={
      "schema":SCHEMA,"version":VERSION,"case_count":len(CASES),"specialist_count":len(SPECIALISTS),"repetitions":int(repetitions),
      "benchmark_scope":"FULL_STAGED_PLAN_SPECIES_UNION_VS_SEVEN_SPECIALIST_BROADCAST_BASELINE",
      "historical_predecessor":"V0_1_FAILED_RECALL_GATE_BECAUSE_IT_MEASURED_ACQUISITION_ROUTE_AND_EXPOSED_MISSING_ANT_MANTIS_STAGES",
      "not_claimed":["NOT_AN_ACTUAL_PERPLEXITY_SERVICE_BENCHMARK","NOT_A_MODEL_ANSWER_QUALITY_BENCHMARK","NOT_A_WEB_INDEX_QUALITY_BENCHMARK"],
      "gremlin":{**g,"exact_route_rate":exact/len(CASES),"stage_exact_rate":stage_exact/len(CASES),"avg_dispatched_specialists":gtasks/len(CASES),"total_dispatched_specialists":gtasks,"useful_task_efficiency":g_eff,"plan_latency_ns":{"median":int(statistics.median(rs)),"p95":int(rs[min(len(rs)-1,int(len(rs)*.95))]),"p99":int(rs[min(len(rs)-1,int(len(rs)*.99))]),"mean":statistics.fmean(rs)}},
      "broadcast_baseline":{**b,"avg_dispatched_specialists":btasks/len(CASES),"total_dispatched_specialists":btasks,"useful_task_efficiency":b_eff,"route_latency_ns":{"median":int(statistics.median(bs)),"p95":int(bs[min(len(bs)-1,int(len(bs)*.95))]),"p99":int(bs[min(len(bs)-1,int(len(bs)*.99))]),"mean":statistics.fmean(bs)}},
      "comparison":{"fanout_reduction_fraction":1-gtasks/btasks,"fanout_reduction_percent":100*(1-gtasks/btasks),"useful_task_efficiency_ratio":g_eff/b_eff if b_eff else None,"control_plane_latency_ratio_vs_constant_broadcast":statistics.median(rs)/max(1,statistics.median(bs))},
      "cases":rows,
    }
    out["benchmark_commitment"]=hashlib.blake2b(b"GREMLIN-RESEARCH-ORCH-BENCH-v0.2\0"+json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode(),digest_size=32).hexdigest()
    return out


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser(); p.add_argument("--repetitions",type=int,default=8000); p.add_argument("--out",required=True); a=p.parse_args()
    r=run_benchmark(a.repetitions); Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(r,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8"); print(json.dumps(r,ensure_ascii=False,sort_keys=True))
