from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from benchmarks.gremlin_memory_governance_v01 import run_memory_and_governance_suite
from benchmarks.gremlin_ood_routing_v06 import run_benchmark as run_ood_routing
from benchmarks.gremlin_research_orchestrator_v02 import run_benchmark as run_orchestrator
from gremlin_mcp.constitutional_runtime import (
    build_runtime_action_binding,
    build_runtime_constitutional_packet,
    require_constitutional_admission,
)
from gremlin_mcp.mathematical_constitution import (
    BLOCK,
    ETHICS_GATES,
    PASS,
    UNRESOLVED,
    ConstitutionalError,
    build_action_contract,
    build_gate_receipt,
    build_ledger_event,
    canonical_kappa_record,
    capability_status_from_memory_receipt,
    certify_transition,
    evaluate_admission,
    ledger_join,
)
from gremlin_mcp.memory_capabilities import evaluate_access, issue_capability_token
from tools.gremlin_bestiary_bench_v01 import run as run_bestiary_virtual
from tools.gremlin_bestiary_phasenav_numpy_bench_v01 import run_suite as run_phasenav_numpy
from tools.gremlin_geometry_phase_scheduler_bench_v01 import run_benchmark as run_geometry_scheduler
from tools.gremlin_runtime_constitutional_proof_v01 import (
    audit_runtime_constitutional_coverage,
)

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


def _full_gates(override: Mapping[str, int] | None = None) -> list[dict[str, Any]]:
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
    for case in cases:
        values = [case[channel] for channel in channels]
        full_scalar = min(values)
        rows.append(
            {
                "case_id": case["case_id"],
                "channel_state": {channel: case[channel] for channel in channels},
                "full_scalar": full_scalar,
                "full_decision": _decision(full_scalar),
            }
        )
        for omitted in channels:
            kept = [case[channel] for channel in channels if channel != omitted]
            scalar = min(kept)
            false_allow = full_scalar != PASS and scalar == PASS
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
        "all_pass_is_allow": rows[0]["full_decision"] == "ALLOW",
        "every_nonpass_case_not_allow": all(
            row["full_decision"] != "ALLOW" for row in rows[1:]
        ),
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
        "pass": all(exact.values()),
        "thresholds_used": False,
    }


def _base_mutation_action() -> dict[str, Any]:
    return build_action_contract(
        action_id="benchmark:mutation",
        consequence_class="MUTATION",
    )


def _admit(
    action: Mapping[str, Any],
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

    def record(
        case_id: str,
        expected: str,
        observed: str,
        passed: bool,
        detail: str = "",
    ) -> None:
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
    record("all_required_inputs_valid", "ALLOW", allow["decision"], allow["decision"] == "ALLOW")

    missing = [gate for gate in _full_gates() if gate["gate"] != "LIFE_PROTECTION"]
    receipt = _admit(action, gates=missing)
    record("missing_required_ethics_gate", "DEFER", receipt["decision"], receipt["decision"] == "DEFER")

    receipt = _admit(action, gates=_full_gates(override={"NO_GO": BLOCK}))
    record("no_go_hit", "DENY", receipt["decision"], receipt["decision"] == "DENY")

    receipt = _admit(action, capability=BLOCK)
    record("capability_deny", "DENY", receipt["decision"], receipt["decision"] == "DENY")

    receipt = _admit(action, authority=UNRESOLVED)
    record("authority_unresolved", "DEFER", receipt["decision"], receipt["decision"] == "DEFER")

    kappa = canonical_kappa_record()
    action_with_kappa = build_action_contract(
        action_id="benchmark:kappa-mutation",
        consequence_class="MUTATION",
        parameter_ids=(kappa["parameter_sha256"],),
    )
    receipt = _admit(action_with_kappa, parameters=(kappa,))
    record("canonical_but_unbound_kappa", "DEFER", receipt["decision"], receipt["decision"] == "DEFER")

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
    forged = dict(access)
    forged["decision"] = "DENY"
    try:
        capability_status_from_memory_receipt(forged)
    except ConstitutionalError:
        record("forged_capability_receipt", "REJECT", "REJECT", True)
    else:
        record("forged_capability_receipt", "REJECT", "ACCEPT", False)

    gate = _gate("NO_GO")
    forged_gate = dict(gate)
    forged_gate["status"] = BLOCK
    from gremlin_mcp.mathematical_constitution import validate_gate_receipt

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

    runtime_payload = {
        "subject_id": "benchmark:runtime",
        "operation": "APPEND_ONLY_TEST",
        "value": 1,
    }
    runtime_binding = build_runtime_action_binding(
        endpoint="benchmark.runtime.guard",
        consequence_class="APPEND_ONLY",
        request_payload=runtime_payload,
    )
    runtime_admission = evaluate_admission(
        action=runtime_binding["action_contract"],
        gate_receipts=gates,
        capability_status=PASS,
        authority_status=PASS,
        evidence_status=PASS,
    )
    runtime_packet = build_runtime_constitutional_packet(
        action_binding=runtime_binding,
        admission_receipt=runtime_admission,
    )

    def runtime_guard_call() -> None:
        receipt = require_constitutional_admission(
            endpoint="benchmark.runtime.guard",
            consequence_class="APPEND_ONLY",
            request_payload=runtime_payload,
            constitutional_packet=runtime_packet,
            expected_capability_status=PASS,
            expected_authority_status=PASS,
            expected_evidence_status=PASS,
        )
        if receipt["status"] != "ADMITTED":
            raise RuntimeError("runtime constitutional guard benchmark drift")

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
        "runtime_request_guard": _measure(runtime_guard_call, repetitions=repetitions),
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
    return {
        "research_orchestrator_v0_2": run_orchestrator(
            repetitions=orchestrator_repetitions
        ),
        "ood_routing_v0_6": run_ood_routing(),
        "bestiary_virtual_topology_v0_1": run_bestiary_virtual(
            count=bestiary_items,
            seed=SEED,
        ),
        "geometry_phase_scheduler_v0_1": run_geometry_scheduler(
            items_per_topic=18
        ),
        "phasenav_numpy_v0_1": run_phasenav_numpy(
            n=phasenav_batch,
            repeats=3,
        ),
    }


def _semantic_regression_summary(existing: Mapping[str, Any]) -> dict[str, Any]:
    orchestrator = existing["research_orchestrator_v0_2"]
    ood = existing["ood_routing_v0_6"]
    bestiary = existing["bestiary_virtual_topology_v0_1"]
    scheduler = existing["geometry_phase_scheduler_v0_1"]
    phasenav = existing["phasenav_numpy_v0_1"]

    ood_semantic = ood["semantic"]
    scheduler_summary = scheduler["summary"]
    phasenav_summary = phasenav["summary"]

    exact_or_natural = {
        "orchestrator_precision_exact_1": {
            "pass": orchestrator["gremlin"]["precision"] == 1.0,
            "provenance": "EXACT_FROZEN_FIXTURE",
        },
        "orchestrator_recall_exact_1": {
            "pass": orchestrator["gremlin"]["recall"] == 1.0,
            "provenance": "EXACT_FROZEN_FIXTURE",
        },
        "orchestrator_stage_exact_rate_1": {
            "pass": orchestrator["gremlin"]["stage_exact_rate"] == 1.0,
            "provenance": "EXACT_FROZEN_FIXTURE",
        },
        "ood_false_positives_eq_0": {
            "pass": ood_semantic["fp"] == 0,
            "provenance": "EXACT_LABELED_FIXTURE",
        },
        "ood_false_negatives_eq_0": {
            "pass": ood_semantic["fn"] == 0,
            "provenance": "EXACT_LABELED_FIXTURE",
        },
        "ood_exact_rate_eq_1": {
            "pass": ood_semantic["exact_rate"] == 1.0,
            "provenance": "EXACT_LABELED_FIXTURE",
        },
        "ood_ambiguity_false_additions_eq_0": {
            "pass": ood["ambiguity_false_additions"] == 0,
            "provenance": "EXACT_NEGATIVE_FIXTURE",
        },
        "ood_fanout_not_worse_than_broadcast": {
            "pass": ood["fanout"]["reduction_fraction"] >= 0.0,
            "provenance": "NATURAL_BASELINE_ZERO",
        },
        "bestiary_virtual_not_slower_than_serial": {
            "pass": bestiary["throughput_speedup"] >= 1.0,
            "provenance": "NATURAL_BASELINE_RATIO_ONE",
        },
        "scheduler_transition_not_worse_than_fifo": {
            "pass": scheduler_summary["transition_reduction_vs_fifo_proxy"] >= 0.0,
            "provenance": "NATURAL_BASELINE_ZERO",
        },
        "scheduler_noise_not_worse_than_fifo": {
            "pass": scheduler_summary["noise_reduction_vs_fifo_proxy"] >= 0.0,
            "provenance": "NATURAL_BASELINE_ZERO",
        },
        "scheduler_lexical_overlap_not_worse_than_fifo": {
            "pass": scheduler_summary["lexical_overlap_gain"] >= 0.0,
            "provenance": "NATURAL_BASELINE_ZERO",
        },
        "scheduler_topic_purity_not_worse_than_fifo": {
            "pass": scheduler_summary["topic_purity_gain"] >= 0.0,
            "provenance": "NATURAL_BASELINE_ZERO",
        },
        "scheduler_context_pack_not_worse_than_fifo": {
            "pass": scheduler_summary["context_pack_advantage_vs_fifo_proxy"] >= 0.0,
            "provenance": "NATURAL_BASELINE_ZERO",
        },
    }

    legacy_only = {
        "ood_legacy_threshold_gate": {
            "value": bool(ood["all_gates_pass"]),
            "provenance": "LEGACY_MAGIC_THRESHOLDS_REPORT_ONLY",
            "controls_readiness": False,
        },
        "bestiary_legacy_10x_candidate": {
            "value": bool(bestiary["candidate"]),
            "threshold": bestiary["candidate_threshold"],
            "provenance": "LEGACY_MAGIC_THRESHOLD_REPORT_ONLY",
            "controls_readiness": False,
        },
        "scheduler_legacy_threshold_verdict": {
            "value": scheduler["verdict"],
            "provenance": "LEGACY_MAGIC_THRESHOLDS_REPORT_ONLY",
            "controls_readiness": False,
        },
        "phasenav_legacy_1e_12_equivalence": {
            "value": bool(phasenav_summary["all_species_scalar_vector_equivalent_1e_12"]),
            "provenance": "LEGACY_NUMERIC_TOLERANCE_REPORT_ONLY",
            "controls_readiness": False,
        },
    }

    open_numeric = {
        "phasenav_scalar_vector_max_torus_error": {
            "value": phasenav_summary["max_scalar_vector_torus_error"],
            "status": "MEASURE_ONLY_UNTIL_ROUNDOFF_BOUND_DERIVED",
            "controls_readiness": False,
        },
        "phasenav_roundoff_bound": {
            "status": "OPEN",
            "requirement": (
                "derive an implementation-specific floating-point error bound "
                "before promoting scalar/vector tolerance to a theorem gate"
            ),
            "controls_readiness": False,
        },
    }

    return {
        "gate_policy": {
            "allowed_gate_provenance": [
                "EXACT_FROZEN_FIXTURE",
                "EXACT_LABELED_FIXTURE",
                "EXACT_NEGATIVE_FIXTURE",
                "NATURAL_BASELINE_ZERO",
                "NATURAL_BASELINE_RATIO_ONE",
            ],
            "legacy_magic_thresholds_control_readiness": False,
            "unproven_numeric_tolerances_control_readiness": False,
        },
        "readiness_gates": exact_or_natural,
        "legacy_report_only": legacy_only,
        "open_numeric_bindings": open_numeric,
        "semantic_regression_pass": all(
            bool(row["pass"]) for row in exact_or_natural.values()
        ),
    }

def _environment() -> dict[str, Any]:
    return {
        "python": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "perf_counter": "time.perf_counter_ns",
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
    runtime_coverage = audit_runtime_constitutional_coverage()
    microbench = run_constitution_microbench(microbench_repetitions)
    ledger_scaling = run_ledger_scaling()
    memory_governance = run_memory_and_governance_suite()
    existing = run_existing_benchmarks(
        orchestrator_repetitions=orchestrator_repetitions,
        bestiary_items=bestiary_items,
        phasenav_batch=phasenav_batch,
    )
    semantic = _semantic_regression_summary(existing)

    invariant_pass = bool(ablation["pass"] and faults["pass"])
    state_governance_pass = bool(
        memory_governance["summary"]["all_exact_invariants_pass"]
    )
    runtime_complete = bool(runtime_coverage["summary"]["coverage_complete"])
    semantic_regression = bool(semantic["semantic_regression_pass"])

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
        "environment": _environment(),
        "workload": {
            "orchestrator_repetitions": orchestrator_repetitions,
            "microbench_repetitions": microbench_repetitions,
            "bestiary_items": bestiary_items,
            "phasenav_batch": phasenav_batch,
            "ledger_sizes": [1, 10, 100, 1000, 5000],
            "memory_convergence_sizes": [10, 100, 500],
            "durable_hive_sizes": [10, 100, 500],
            "raphael_repetitions_per_lane": 100,
            "ferret_repetitions": 100,
        },
        "scope": [
            "CONSTITUTION_NON_BYPASS_ABLATION",
            "FAULT_INJECTION",
            "DECLARED_RUNTIME_CONSTITUTIONAL_COVERAGE",
            "CONTROL_PLANE_LATENCY",
            "LEDGER_SCALING",
            "MEMORY_ANTI_ENTROPY_CONVERGENCE",
            "DURABLE_HIVE_SCALING",
            "RAPHAEL_SUCCESS_AND_ROLLBACK",
            "FERRET_SINGLE_USE_ACTUATION",
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
            "NOT_REGISTRY_EXHAUSTIVENESS_PROOF",
        ],
        "preregistered_exact_invariants": {
            "full_constitution_nonpass_never_allows": True,
            "each_single_channel_ablation_exposes_false_allow": True,
            "fault_injection_all_expected_outcomes_exact": True,
            "runtime_coverage_complete_requires_every_declared_surface_guarded": True,
            "memory_convergence_exact": True,
            "durable_hive_recovery_exact": True,
            "raphael_success_and_rollback_exact": True,
            "ferret_single_use_exact": True,
            "legacy_magic_thresholds_do_not_control_readiness": True,
            "numeric_tolerance_requires_derived_error_bound": True,
            "new_latency_thresholds_added": False,
        },
        "constitution_ablation": ablation,
        "fault_injection": faults,
        "runtime_coverage": runtime_coverage,
        "microbench": microbench,
        "ledger_scaling": ledger_scaling,
        "memory_and_governance": memory_governance,
        "existing_benchmarks": existing,
        "semantic_regression_summary": semantic,
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
