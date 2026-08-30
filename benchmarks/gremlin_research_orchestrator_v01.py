from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import statistics
import time
from typing import Any, Iterable

from gremlin_mcp.pipeline import SPECIALISTS
from gremlin_mcp.router import route
from gremlin_mcp.web import build_research_plan

SCHEMA = "GREMLIN_RESEARCH_ORCHESTRATOR_BENCHMARK_V0_1"
VERSION = "0.1.0"


@dataclass(frozen=True)
class Case:
    case_id: str
    query: str
    expected_species: tuple[str, ...]
    expected_stages: tuple[str, ...]


CASES: tuple[Case, ...] = (
    Case(
        "evidence_only",
        "Review the evidence, sources, citations, provenance and methodology for quantum information geometry.",
        ("OWL",),
        ("ACQUIRE_EVIDENCE",),
    ),
    Case(
        "relation_map",
        "Map the relation dependency graph and topology between entropy, information geometry and gravity.",
        ("OWL", "SPIDER"),
        ("ACQUIRE_EVIDENCE", "MAP_RELATIONS"),
    ),
    Case(
        "derivation",
        "Derive a candidate equation and mechanism relating information geometry to a gravitational coupling.",
        ("OWL", "MOLE"),
        ("ACQUIRE_EVIDENCE", "DERIVE_CANDIDATE"),
    ),
    Case(
        "adversarial_audit",
        "Audit the evidence for contradictions, errors, mismatches and falsification targets in this model.",
        ("OWL", "HOUND"),
        ("ACQUIRE_EVIDENCE", "ADVERSARIAL_CHECK"),
    ),
    Case(
        "relation_plus_derivation",
        "Map dependencies and graph relations, then derive a candidate mechanism and equation.",
        ("OWL", "SPIDER", "MOLE"),
        ("ACQUIRE_EVIDENCE", "MAP_RELATIONS", "DERIVE_CANDIDATE"),
    ),
    Case(
        "relation_plus_audit",
        "Build the dependency graph and audit contradictions, regressions and evidence quality.",
        ("OWL", "SPIDER", "HOUND"),
        ("ACQUIRE_EVIDENCE", "MAP_RELATIONS", "ADVERSARIAL_CHECK"),
    ),
    Case(
        "derive_plus_audit",
        "Derive the formula, then validate it against contradictions, errors and regression tests.",
        ("OWL", "MOLE", "HOUND"),
        ("ACQUIRE_EVIDENCE", "DERIVE_CANDIDATE", "ADVERSARIAL_CHECK"),
    ),
    Case(
        "full_research",
        "Audit evidence contradictions dependencies graph and derive the relation between Shannon entropy information geometry and quantum gravity.",
        ("OWL", "SPIDER", "MOLE", "HOUND"),
        ("ACQUIRE_EVIDENCE", "MAP_RELATIONS", "DERIVE_CANDIDATE", "ADVERSARIAL_CHECK"),
    ),
    Case(
        "memory_context",
        "Review prior memory, earlier history and previous archived results for this research question.",
        ("OWL", "RAVEN"),
        ("ACQUIRE_EVIDENCE",),
    ),
    Case(
        "enumeration",
        "Review evidence and enumerate candidate combinations, permutations and variants across the search space.",
        ("OWL", "ANT"),
        ("ACQUIRE_EVIDENCE",),
    ),
    Case(
        "deduplication",
        "Review evidence and identify duplicate, redundant, obsolete or overlapping candidate branches to prune.",
        ("OWL", "MANTIS"),
        ("ACQUIRE_EVIDENCE",),
    ),
    Case(
        "mixed_generalist",
        "Review sources, map graph dependencies, derive a mechanism, audit contradictions, enumerate variants and prune duplicates.",
        ("OWL", "SPIDER", "MOLE", "HOUND", "ANT", "MANTIS"),
        ("ACQUIRE_EVIDENCE", "MAP_RELATIONS", "DERIVE_CANDIDATE", "ADVERSARIAL_CHECK"),
    ),
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _commit(value: Any) -> str:
    return hashlib.blake2b(b"GREMLIN-RESEARCH-ORCH-BENCH/v0.1\0" + _canonical(value), digest_size=32).hexdigest()


def _route_for_query(query: str, *, max_species: int = 7) -> dict[str, Any]:
    payload = {
        "query": query,
        "task": "internet research source review evidence provenance",
        "evidence": {"requested": True, "provenance_required": True},
    }
    return route(payload, max_species=max_species)


def _metrics(selected: Iterable[str], expected: Iterable[str]) -> dict[str, float | int | bool]:
    selected_set = set(selected)
    expected_set = set(expected)
    tp = len(selected_set & expected_set)
    fp = len(selected_set - expected_set)
    fn = len(expected_set - selected_set)
    precision = tp / len(selected_set) if selected_set else (1.0 if not expected_set else 0.0)
    recall = tp / len(expected_set) if expected_set else 1.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "exact": selected_set == expected_set,
    }


def run_benchmark(*, repetitions: int = 4000) -> dict[str, Any]:
    reps = int(repetitions)
    if not 100 <= reps <= 100_000:
        raise ValueError("repetitions must be in 100..100000")

    rows: list[dict[str, Any]] = []
    gremlin_total_tasks = 0
    broadcast_total_tasks = 0
    gremlin_tp = gremlin_fp = gremlin_fn = 0
    broadcast_tp = broadcast_fp = broadcast_fn = 0
    exact_count = 0
    stage_exact_count = 0

    # Record stable semantic outcomes once per case.
    for case in CASES:
        decision = _route_for_query(case.query, max_species=len(SPECIALISTS))
        selected = list(decision["route_mask"])
        expected = list(case.expected_species)
        gremlin = _metrics(selected, expected)
        broadcast = _metrics(SPECIALISTS, expected)
        plan = build_research_plan(case.query, max_species=len(SPECIALISTS))
        actual_stages = tuple(stage["stage_id"] for stage in plan["stages"])
        expected_stages = tuple(case.expected_stages)

        gremlin_total_tasks += len(selected)
        broadcast_total_tasks += len(SPECIALISTS)
        gremlin_tp += int(gremlin["tp"])
        gremlin_fp += int(gremlin["fp"])
        gremlin_fn += int(gremlin["fn"])
        broadcast_tp += int(broadcast["tp"])
        broadcast_fp += int(broadcast["fp"])
        broadcast_fn += int(broadcast["fn"])
        exact_count += int(bool(gremlin["exact"]))
        stage_exact_count += int(actual_stages == expected_stages)

        rows.append(
            {
                "case_id": case.case_id,
                "query": case.query,
                "expected_species": expected,
                "gremlin_route": selected,
                "broadcast_route": list(SPECIALISTS),
                "gremlin": gremlin,
                "broadcast": broadcast,
                "expected_stages": list(expected_stages),
                "actual_stages": list(actual_stages),
                "stage_exact": actual_stages == expected_stages,
                "route_commitment": decision["route_commitment"],
                "plan_commitment": plan["plan_commitment"],
            }
        )

    # Microbenchmark only the routing/control-plane decision. Query set is cycled
    # to avoid benchmarking one hot string. Broadcast baseline is constant route
    # construction, not a pretend external framework implementation.
    route_latencies_ns: list[int] = []
    broadcast_latencies_ns: list[int] = []
    for index in range(reps):
        case = CASES[index % len(CASES)]
        start = time.perf_counter_ns()
        _route_for_query(case.query, max_species=len(SPECIALISTS))
        route_latencies_ns.append(time.perf_counter_ns() - start)

        start = time.perf_counter_ns()
        tuple(SPECIALISTS)
        broadcast_latencies_ns.append(time.perf_counter_ns() - start)

    def aggregate(tp: int, fp: int, fn: int) -> dict[str, float]:
        precision = tp / (tp + fp) if tp + fp else 1.0
        recall = tp / (tp + fn) if tp + fn else 1.0
        f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
        return {"precision": precision, "recall": recall, "f1": f1}

    gremlin_quality = aggregate(gremlin_tp, gremlin_fp, gremlin_fn)
    broadcast_quality = aggregate(broadcast_tp, broadcast_fp, broadcast_fn)
    fanout_reduction = 1.0 - (gremlin_total_tasks / broadcast_total_tasks)
    useful_efficiency = gremlin_tp / gremlin_total_tasks if gremlin_total_tasks else 0.0
    broadcast_efficiency = broadcast_tp / broadcast_total_tasks if broadcast_total_tasks else 0.0

    route_sorted = sorted(route_latencies_ns)
    broadcast_sorted = sorted(broadcast_latencies_ns)

    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "benchmark_scope": "DETERMINISTIC_CONTROL_PLANE_SELECTIVE_ROUTING_VS_SEVEN_SPECIALIST_BROADCAST_BASELINE",
        "not_claimed": [
            "NOT_AN_ACTUAL_PERPLEXITY_SERVICE_BENCHMARK",
            "NOT_A_MODEL_ANSWER_QUALITY_BENCHMARK",
            "NOT_A_WEB_INDEX_QUALITY_BENCHMARK",
        ],
        "case_count": len(CASES),
        "repetitions": reps,
        "specialist_count": len(SPECIALISTS),
        "gremlin": {
            **gremlin_quality,
            "exact_route_rate": exact_count / len(CASES),
            "stage_exact_rate": stage_exact_count / len(CASES),
            "total_dispatched_specialists": gremlin_total_tasks,
            "avg_dispatched_specialists": gremlin_total_tasks / len(CASES),
            "useful_task_efficiency": useful_efficiency,
            "route_latency_ns": {
                "median": int(statistics.median(route_sorted)),
                "p95": int(route_sorted[min(len(route_sorted) - 1, int(len(route_sorted) * 0.95))]),
                "p99": int(route_sorted[min(len(route_sorted) - 1, int(len(route_sorted) * 0.99))]),
                "mean": statistics.fmean(route_sorted),
            },
        },
        "broadcast_baseline": {
            **broadcast_quality,
            "exact_route_rate": sum(set(SPECIALISTS) == set(case.expected_species) for case in CASES) / len(CASES),
            "total_dispatched_specialists": broadcast_total_tasks,
            "avg_dispatched_specialists": broadcast_total_tasks / len(CASES),
            "useful_task_efficiency": broadcast_efficiency,
            "route_latency_ns": {
                "median": int(statistics.median(broadcast_sorted)),
                "p95": int(broadcast_sorted[min(len(broadcast_sorted) - 1, int(len(broadcast_sorted) * 0.95))]),
                "p99": int(broadcast_sorted[min(len(broadcast_sorted) - 1, int(len(broadcast_sorted) * 0.99))]),
                "mean": statistics.fmean(broadcast_sorted),
            },
        },
        "comparison": {
            "fanout_reduction_fraction": fanout_reduction,
            "fanout_reduction_percent": fanout_reduction * 100.0,
            "useful_task_efficiency_ratio": useful_efficiency / broadcast_efficiency if broadcast_efficiency else None,
            "control_plane_latency_ratio_vs_constant_broadcast": statistics.median(route_sorted) / max(1, statistics.median(broadcast_sorted)),
        },
        "cases": rows,
    }
    result["benchmark_commitment"] = _commit(result)
    return result


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=4000)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    receipt = run_benchmark(repetitions=args.repetitions)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
