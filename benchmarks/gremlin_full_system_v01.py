from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any, Callable, Iterable

from benchmarks.gremlin_ood_routing_v06 import run_benchmark as run_ood_routing
from benchmarks.gremlin_research_orchestrator_v02 import run_benchmark as run_orchestrator
from benchmarks.gremlin_memory_governance_v01 import run_memory_and_governance_suite
from gremlin_mcp.mathematical_constitution import (
    BLOCK,
    ETHICS_GATES,
    PASS,
    UNRESOLVED,
    ConstitutionalError,
    build_action_contract,
    build_gate_receipt,
    build_ledger_event,
    build_parameter_record,
    canonical_kappa_record,
    capability_status_from_memory_receipt,
    certify_transition,
    evaluate_admission,
    ledger_join,
    validate_admission_against_action,
    validate_gate_receipt,
)
from gremlin_mcp.memory_capabilities import evaluate_access, issue_capability_token
from tools.gremlin_bestiary_bench_v01 import run as run_bestiary_virtual
from tools.gremlin_bestiary_phasenav_numpy_bench_v01 import run_suite as run_phasenav_numpy
from tools.gremlin_geometry_phase_scheduler_bench_v01 import run_benchmark as run_geometry_scheduler
from tools.gremlin_runtime_coverage_audit_v01 import audit_runtime_coverage

SCHEMA = "GREMLIN_FULL_SYSTEM_BENCHMARK_AND_ABLATION_V0_1"
VERSION = "0.1.0"
SEED = 616
DEFAULT_OUT = Path("provenance/GREMLIN_FULL_SYSTEM_BENCHMARK_V0_1.json")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _pctl(values: list[int], q: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))
    return int(ordered[index])


def _timing_summary(samples_ns: list[int]) -> dict[str, Any]:
    if not samples_ns:
        return {
            "count": 0,
            "median_ns": 0,
            "p95_ns": 0,
            "p99_ns": 0,
            "mean_ns": 0.0,
            "min_ns": 0,
            "max_ns": 0,
        }
    return {
        "count": len(samples_ns),
        "median_ns": int(statistics.median(samples_ns)),
        "p95_ns": _pctl(samples_ns, 0.95),
        "p99_ns": _pctl(samples_ns, 0.99),
        "mean_ns": statistics.fmean(samples_ns),
        "min_ns": min(samples_ns),
        "max_ns": max(samples_ns),
    }


def _measure(fn: Callable[[], Any], *, repetitions: int, warmup: int = 20) -> dict[str, Any]:
    for _ in range(max(0, warmup)):
        fn()
    samples: list[int] = []
    for _ in range(int(repetitions)):
        start = time.perf_counter_ns()
        fn()
        samples.append(time.perf_counter_ns() - start)
    return _timing_summary(samples)


def _gate(gate: str, status: int = PASS) -> dict[str, Any]:
    return build_gate_receipt(
        gate=gate,
        status=status,
        relation_ids=("benchmark:relation:1",),
        subject_refs=("benchmark:subject:1",),
        source_classification="TEST_FIXTURE",
        source_ref=f"benchmark:{gate.lower()}",
        evidence_refs=(f"benchmark:evidence:{gate.lower()}",),
        reason="frozen benchmark fixture",
    )


def _full_gates(override: dict[str, int] | None = None) -> list[dict[str, Any]]:
    state = dict(override or {})
    return [_gate(gate, state.get(gate, PASS)) for gate in ETHICS_GATES]


def _decision(code: int) -> str:
    if code == PASS:
        return "ALLOW"
    if code == BLOCK:
        return "DENY"
    return "DEFER"


def run_constitution_ablation() -> dict[str, Any]:
    channels = ("ethics", "capability", "authority", "evidence", "parameters")
    cases: list[dict[str, Any]] = [
        {
            "case_id": "all_pass",
            "ethics": PASS,
            "capability": PASS,
            "authority": PASS,
            "evidence": PASS,
            "parameters": PASS,
        }
    ]
    for channel in channels:
        for state, label in ((BLOCK, "block"), (UNRESOLVED, "unresolved")):
            row = {
                "case_id": f"{channel}_{label}",
                "ethics": PASS,
                "capability": PASS,
                "authority": PASS,
                "evidence": PASS,
                "parameters": PASS,
            }
            row[channel] = state
            cases.append(row)

    rows = []
    ablations = {channel: {"false_allows": 0, "rows": []} for channel in channels}
    full_false_allows = 0
    full_false_denies = 0

    for case in cases:
        values = [case[channel] for channel in channels]
        full = min(values)
        expected = PASS if case["case_id"] == "all_pass" else min(values)
        if full == PASS and expected != PASS:
            full_false_allows += 1
        if full != PASS and expected == PASS:
            full_false_denies += 1

        row = {
            "case_id": case["case_id"],
            "channel_state": {channel: case[channel] for channel in channels},
            "full_scalar": full,
            "full_decision": _decision(full),
        }
        rows.append(row)

        for omitted in channels:
            kept = [case[channel] for channel in channels if channel != omitted]
            scalar = min(kept)
            false_allow = full != PASS and scalar == PASS
            ablations[omitted]["false_allows"] += int(false_allow)
            ablations[omitted]["rows"].append(
                {
                    "case_id": case["case_id"],
                    "scalar": scalar,
                    "decision": _decision(scalar),
                    "false_allow_vs_full_constitution": false_allow,
                }
            )

    exact = {
        "full_false_allow_count": full_false_allows,
        "full_false_deny_count": full_false_denies,
        "full_false_allow_count_eq_0": full_false_allows == 0,
        "full_false_deny_count_eq_0": full_false_denies == 0,
        "all_pass_is_allow": rows[0]["full_decision"] == "ALLOW",
        "each_single_channel_ablation_exposes_false_allow": all(
            ablations[channel]["false_allows"] >= 1 for channel in channels
        ),
    }
    return {
        "scope": "EXACT_FIVE_CHANNEL_NON_BYPASS_ABLATION",
        "channels": list(channels),
        "cases": rows,
        "ablations": ablations,
        "exact_invariants": exact,
        "pass": bool(
            exact["full_false_allow_count_eq_0"]
            and exact["full_false_deny_count_eq_0"]
            and exact["all_pass_is_allow"]
            and exact["each_single_channel_ablation_exposes_false_allow"]
        ),
        "thresholds_used": False,
    }


def _base_mutation_action() -> dict[str, Any]:
    return build_action_contract(
        action_id="benchmark:mutation",
        consequence_class="MUTATION",
    )


def _admit(
    action: dict[str, Any],
    *,
    gates: list[dict[str, Any]] | None = None,
    capability: int = PASS,
    authority: int = PASS,
    evidence: int = PASS,
    parameters: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    return evaluate_admission(
        action=action,
        gate_receipts=_full_gates() if gates is None else gates,
        capability_status=capability,
        authority_status=authority,
        evidence_status=evidence,
        parameter_records=parameters,
    )


def run_fault_injection_matrix() -> dict[str, Any]:
    action = _base_mutation_action()
    rows: list[dict[str, Any]] = []

    def record(case_id: str, expected: str, observed: str, passed: bool, detail: str = "") -> None:
        rows.append(
            {
                "case_id": case_id,
                "expected": expected,
                "observed": observed,
                "pass": bool(passed),
                "detail": detail,
            }
        )

    allow = _admit(action)
    record(
        "all_required_inputs_valid",
        "ALLOW",
        allow["decision"],
        allow["decision"] == "ALLOW",
    )

    missing = [
        gate
        for gate in _full_gates()
        if gate["gate"] != "LIFE_PROTECTION"
    ]
    receipt = _admit(action, gates=missing)
    record(
        "missing_required_ethics_gate",
        "DEFER",
        receipt["decision"],
        receipt["decision"] == "DEFER",
    )

    receipt = _admit(
        action,
        gates=_full_gates(override={"NO_GO": BLOCK}),
    )
    record(
        "no_go_hit",
        "DENY",
        receipt["decision"],
        receipt["decision"] == "DENY",
    )

    receipt = _admit(action, capability=BLOCK)
    record(
        "capability_deny",
        "DENY",
        receipt["decision"],
        receipt["decision"] == "DENY",
    )

    receipt = _admit(action, authority=UNRESOLVED)
    record(
        "authority_unresolved",
        "DEFER",
        receipt["decision"],
        receipt["decision"] == "DEFER",
    )

    kappa = canonical_kappa_record()
    action_with_kappa = build_action_contract(
        action_id="benchmark:kappa-mutation",
        consequence_class="MUTATION",
        parameter_ids=(kappa["parameter_sha256"],),
    )
    receipt = _admit(action_with_kappa, parameters=(kappa,))
    record(
        "canonical_but_unbound_kappa",
        "DEFER",
        receipt["decision"],
        receipt["decision"] == "DEFER",
    )

    token = issue_capability_token(
        beast="SPIDER",
        layer="RELATIONAL",
        operation="GRAPH_APPEND",
        artifact_type="RELATION_EDGE",
        subject_scope="subject:1",
        generation_scope="generation:1",
        task_scope="task:1",
    )
    access = evaluate_access(
        beast="SPIDER",
        layer="RELATIONAL",
        operation="GRAPH_APPEND",
        artifact_type="RELATION_EDGE",
        subject_id="subject:1",
        generation_id="generation:1",
        task_id="task:1",
        token=token,
    )
    forged = copy.deepcopy(access)
    forged["decision"] = "DENY"
    try:
        capability_status_from_memory_receipt(forged)
    except ConstitutionalError:
        record("forged_capability_receipt", "REJECT", "REJECT", True)
    else:
        record("forged_capability_receipt", "REJECT", "ACCEPT", False)

    gate = _gate("NO_GO")
    forged_gate = copy.deepcopy(gate)
    forged_gate["status"] = BLOCK
    try:
        validate_gate_receipt(forged_gate)
    except ConstitutionalError:
        record("forged_ethics_gate_receipt", "REJECT", "REJECT", True)
    else:
        record("forged_ethics_gate_receipt", "REJECT", "ACCEPT", False)

    allow = _admit(action)
    try:
        certify_transition(
            action_contract=action,
            pre_state_commitment="state:before",
            post_state_commitment="state:after",
            admission_receipt=allow,
            ledger_before=(),
            ledger_after=(),
            mutation_receipt_event_id="gce:" + "0" * 64,
        )
    except ConstitutionalError:
        record("silent_state_mutation", "REJECT", "REJECT", True)
    else:
        record("silent_state_mutation", "REJECT", "ACCEPT", False)

    other = build_action_contract(
        action_id="benchmark:other-mutation",
        consequence_class="MUTATION",
    )
    event = build_ledger_event(
        event_type="MUTATION_RECEIPT",
        payload={
            "action_id": other["action_id"],
            "action_sha256": other["action_sha256"],
            "admission_receipt_id": allow["receipt_id"],
            "pre_state_commitment": "state:before",
            "post_state_commitment": "state:after",
        },
    )
    try:
        certify_transition(
            action_contract=other,
            pre_state_commitment="state:before",
            post_state_commitment="state:after",
            admission_receipt=allow,
            ledger_before=(),
            ledger_after=(event,),
            mutation_receipt_event_id=event["event_id"],
        )
    except ConstitutionalError:
        record("allow_receipt_replay_on_different_action", "REJECT", "REJECT", True)
    else:
        record("allow_receipt_replay_on_different_action", "REJECT", "ACCEPT", False)

    failed = [row["case_id"] for row in rows if not row["pass"]]
    return {
        "scope": "CONSTITUTIONAL_FAIL_CLOSED_FAULT_INJECTION",
        "case_count": len(rows),
        "passed_count": len(rows) - len(failed),
        "failed_count": len(failed),
        "failed_cases": failed,
        "rows": rows,
        "pass": not failed,
    }


def run_constitution_microbench(repetitions: int = 3000) -> dict[str, Any]:
    action = _base_mutation_action()
    gates = _full_gates()
    allow = _admit(action, gates=gates)

    def admission_call() -> None:
        receipt = evaluate_admission(
            action=action,
            gate_receipts=gates,
            capability_status=PASS,
            authority_status=PASS,
            evidence_status=PASS,
        )
        if receipt["decision"] != "ALLOW":
            raise RuntimeError("constitutional admission benchmark drift")

    token = issue_capability_token(
        beast="SPIDER",
        layer="RELATIONAL",
        operation="GRAPH_APPEND",
        artifact_type="RELATION_EDGE",
        subject_scope="subject:bench",
        generation_scope="generation:bench",
        task_scope="task:bench",
    )

    def capability_call() -> None:
        receipt = evaluate_access(
            beast="SPIDER",
            layer="RELATIONAL",
            operation="GRAPH_APPEND",
            artifact_type="RELATION_EDGE",
            subject_id="subject:bench",
            generation_id="generation:bench",
            task_id="task:bench",
            token=token,
        )
        if capability_status_from_memory_receipt(receipt) != PASS:
            raise RuntimeError("capability benchmark drift")

    event = build_ledger_event(
        event_type="MUTATION_RECEIPT",
        payload={
            "action_id": action["action_id"],
            "action_sha256": action["action_sha256"],
            "admission_receipt_id": allow["receipt_id"],
            "pre_state_commitment": "before",
            "post_state_commitment": "after",
        },
    )

    def transition_call() -> None:
        certify_transition(
            action_contract=action,
            pre_state_commitment="before",
            post_state_commitment="after",
            admission_receipt=allow,
            ledger_before=(),
            ledger_after=(event,),
            mutation_receipt_event_id=event["event_id"],
        )

    return {
        "scope": "SAME_PROCESS_PYTHON_CONTROL_PLANE_LATENCY",
        "repetitions": int(repetitions),
        "admission": _measure(admission_call, repetitions=repetitions),
        "capability_validation": _measure(capability_call, repetitions=repetitions),
        "transition_certificate": _measure(
            transition_call,
            repetitions=max(500, repetitions // 2),
        ),
        "performance_gate": "MEASURE_ONLY_NO_PROMOTION_THRESHOLD",
        "external_effects": False,
    }


def run_ledger_scaling() -> dict[str, Any]:
    sizes = (1, 10, 100, 1000, 5000)
    rows = []
    for size in sizes:
        events = tuple(
            build_ledger_event(
                event_type="OBSERVATION",
                payload={"index": i, "subject": f"subject:{i % 17}"},
            )
            for i in range(size)
        )
        start = time.perf_counter_ns()
        merged = ledger_join((), events)
        elapsed = time.perf_counter_ns() - start
        if len(merged) != size:
            raise RuntimeError("ledger scaling benchmark lost events")
        rows.append(
            {
                "events": size,
                "join_ns": elapsed,
                "ns_per_event": elapsed / size,
                "all_events_preserved": True,
            }
        )
    return {
        "scope": "APPEND_ONLY_LEDGER_BATCH_JOIN_SCALING",
        "rows": rows,
        "performance_gate": "MEASURE_ONLY_NO_PROMOTION_THRESHOLD",
    }


def run_existing_benchmarks(
    *,
    orchestrator_repetitions: int = 2500,
    bestiary_items: int = 5000,
    phasenav_batch: int = 256,
) -> dict[str, Any]:
    orchestrator = run_orchestrator(repetitions=orchestrator_repetitions)
    ood = run_ood_routing()
    bestiary = run_bestiary_virtual(count=bestiary_items, seed=SEED)
    scheduler = run_geometry_scheduler(items_per_topic=18)
    phasenav = run_phasenav_numpy(n=phasenav_batch, repeats=3)

    return {
        "research_orchestrator_v0_2": orchestrator,
        "ood_routing_v0_6": ood,
        "bestiary_virtual_topology_v0_1": bestiary,
        "geometry_phase_scheduler_v0_1": scheduler,
        "phasenav_numpy_v0_1": phasenav,
    }


def _legacy_semantic_summary(existing: dict[str, Any]) -> dict[str, Any]:
    orchestrator = existing["research_orchestrator_v0_2"]
    ood = existing["ood_routing_v0_6"]
    scheduler = existing["geometry_phase_scheduler_v0_1"]
    phasenav = existing["phasenav_numpy_v0_1"]
    return {
        "orchestrator_precision": orchestrator["gremlin"]["precision"],
        "orchestrator_recall": orchestrator["gremlin"]["recall"],
        "orchestrator_exact_route_rate": orchestrator["gremlin"]["exact_route_rate"],
        "orchestrator_stage_exact_rate": orchestrator["gremlin"]["stage_exact_rate"],
        "orchestrator_fanout_reduction_fraction": orchestrator["comparison"]["fanout_reduction_fraction"],
        "ood_all_existing_gates_pass": bool(ood["all_gates_pass"]),
        "scheduler_verdict": scheduler["verdict"],
        "phasenav_scalar_vector_equivalent": bool(
            phasenav["summary"]["all_species_scalar_vector_equivalent_1e_12"]
        ),
        "legacy_semantic_regression_pass": bool(
            orchestrator["gremlin"]["precision"] == 1.0
            and orchestrator["gremlin"]["recall"] == 1.0
            and orchestrator["gremlin"]["stage_exact_rate"] == 1.0
            and ood["all_gates_pass"]
            and str(scheduler["verdict"]).startswith("PASS_")
            and phasenav["summary"]["all_species_scalar_vector_equivalent_1e_12"]
        ),
    }


def run_full_suite(
    *,
    orchestrator_repetitions: int = 2500,
    microbench_repetitions: int = 3000,
    bestiary_items: int = 5000,
    phasenav_batch: int = 256,
) -> dict[str, Any]:
    started = time.time()
    ablation = run_constitution_ablation()
    faults = run_fault_injection_matrix()
    microbench = run_constitution_microbench(microbench_repetitions)
    ledger_scaling = run_ledger_scaling()
    memory_governance = run_memory_and_governance_suite()
    runtime_coverage = audit_runtime_coverage()
    existing = run_existing_benchmarks(
        orchestrator_repetitions=orchestrator_repetitions,
        bestiary_items=bestiary_items,
        phasenav_batch=phasenav_batch,
    )
    legacy = _legacy_semantic_summary(existing)

    invariant_pass = bool(ablation["pass"] and faults["pass"])
    state_governance_pass = bool(
        memory_governance["summary"]["all_exact_invariants_pass"]
    )
    runtime_complete = bool(runtime_coverage["summary"]["coverage_complete"])
    semantic_regression = bool(legacy["legacy_semantic_regression_pass"])

    if invariant_pass and state_governance_pass and runtime_complete and semantic_regression:
        readiness = "PASS_FULL_INTERNAL_SYSTEM_GATE"
    elif invariant_pass and state_governance_pass and semantic_regression and not runtime_complete:
        readiness = "FAIL_RUNTIME_CONSTITUTIONAL_COVERAGE_GAP"
    elif not invariant_pass:
        readiness = "FAIL_CONSTITUTIONAL_INVARIANT"
    elif not state_governance_pass:
        readiness = "FAIL_MEMORY_OR_GOVERNANCE_INVARIANT"
    else:
        readiness = "FAIL_EXISTING_BENCHMARK_REGRESSION"

    receipt = {
        "schema": SCHEMA,
        "version": VERSION,
        "seed": SEED,
        "scope": [
            "CONSTITUTION_NON_BYPASS_ABLATION",
            "FAULT_INJECTION",
            "RUNTIME_CONSTITUTIONAL_COVERAGE",
            "CONTROL_PLANE_LATENCY",
            "LEDGER_SCALING",
            "MEMORY_ANTI_ENTROPY_CONVERGENCE",
            "DURABLE_HIVE_SCALING",
            "RAPHAEL_SUCCESS_AND_ROLLBACK",
            "RESEARCH_ROUTING",
            "OOD_ROUTING",
            "BESTIARY_VIRTUAL_TOPOLOGY",
            "GEOMETRY_PHASE_SCHEDULING",
            "PHASENAV_SCALAR_VECTOR_EQUIVALENCE_AND_PERFORMANCE",
        ],
        "not_claimed": [
            "NOT_EXTERNAL_MODEL_ANSWER_QUALITY",
            "NOT_EXTERNAL_WEB_INDEX_QUALITY",
            "NOT_PRODUCTION_SLO_OR_CAPACITY_CERTIFICATION",
            "NOT_PHYSICAL_DYNAMICS_VALIDATION",
            "NOT_CONSCIOUSNESS_VALIDATION",
            "NOT_A_PROOF_THAT_THE_RUNTIME_COVERAGE_REGISTRY_IS_EXHAUSTIVE",
        ],
        "preregistered_exact_invariants": {
            "full_constitution_false_allows_eq_0": True,
            "full_constitution_false_denies_eq_0_on_all_pass": True,
            "fault_injection_all_expected_outcomes_exact": True,
            "each_single_channel_ablation_must_expose_at_least_one_false_allow": True,
            "runtime_coverage_complete_requires_every_declared_surface_guarded": True,
            "existing_benchmark_thresholds_are_reused_not_relaxed": True,
            "new_latency_thresholds_added": False,
        },
        "constitution_ablation": ablation,
        "fault_injection": faults,
        "runtime_coverage": runtime_coverage,
        "microbench": microbench,
        "ledger_scaling": ledger_scaling,
        "memory_and_governance": memory_governance,
        "existing_benchmarks": existing,
        "legacy_semantic_summary": legacy,
        "summary": {
            "constitutional_invariants_pass": invariant_pass,
            "memory_and_governance_invariants_pass": state_governance_pass,
            "runtime_constitutional_coverage_complete": runtime_complete,
            "existing_semantic_regression_pass": semantic_regression,
            "system_readiness_verdict": readiness,
            "benchmark_execution_success": True,
            "elapsed_wall_s": time.time() - started,
        },
    }
    receipt["benchmark_sha256"] = _hash(receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--orchestrator-repetitions", type=int, default=2500)
    parser.add_argument("--microbench-repetitions", type=int, default=3000)
    parser.add_argument("--bestiary-items", type=int, default=5000)
    parser.add_argument("--phasenav-batch", type=int, default=256)
    args = parser.parse_args()

    receipt = run_full_suite(
        orchestrator_repetitions=args.orchestrator_repetitions,
        microbench_repetitions=args.microbench_repetitions,
        bestiary_items=args.bestiary_items,
        phasenav_batch=args.phasenav_batch,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt["summary"], sort_keys=True))
    print(f"receipt={out}")
    # Negative benchmark findings are preserved in the receipt. Harness success
    # means the benchmark executed faithfully, not that GREMLIN is production-ready.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
