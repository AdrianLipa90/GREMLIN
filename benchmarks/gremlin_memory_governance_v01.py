from __future__ import annotations

import hashlib
import json
import math
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping

from gremlin_mcp.constitutional_runtime import (
    build_runtime_action_binding,
    build_runtime_constitutional_packet,
)
from gremlin_mcp.ferret import (
    FerretAuthorizationError,
    FerretExecutionResult,
    InMemoryFerretExecutionLedger,
    authorize_action,
    execute_authorized_action,
    prepare_action,
)
from gremlin_mcp.hive_authority import HiveAuthorityRuntime
from gremlin_mcp.mathematical_constitution import (
    ETHICS_GATES,
    PASS,
    build_gate_receipt,
    evaluate_admission,
)
from gremlin_mcp.memory_anti_entropy import (
    apply_hive_delta,
    build_hive_inventory,
    build_hive_manifest,
    divergent_hive_buckets,
    export_hive_delta,
    plan_hive_delta,
)
from gremlin_mcp.memory_exchange import ingest_exchange_envelope
from gremlin_mcp.raphael import (
    ACCEPT,
    InMemoryMutationLedger,
    RaphaelExecutionError,
    authorize,
    execute,
    judge,
    observe,
)

SCHEMA = "GREMLIN_MEMORY_AND_GOVERNANCE_BENCHMARK_V0_1"
VERSION = "0.1.0"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _pctl(values: list[int], q: float) -> int:
    ordered = sorted(values)
    if not ordered:
        return 0
    index = min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))
    return int(ordered[index])


def _timing(values: list[int]) -> dict[str, Any]:
    return {
        "count": len(values),
        "median_ns": int(statistics.median(values)) if values else 0,
        "p95_ns": _pctl(values, 0.95),
        "p99_ns": _pctl(values, 0.99),
        "mean_ns": statistics.fmean(values) if values else 0.0,
        "min_ns": min(values) if values else 0,
        "max_ns": max(values) if values else 0,
    }


def _constitutional_packet(
    *,
    endpoint: str,
    consequence_class: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    binding = build_runtime_action_binding(
        endpoint=endpoint,
        consequence_class=consequence_class,
        request_payload=payload,
    )
    gates = [
        build_gate_receipt(
            gate=gate,
            status=PASS,
            relation_ids=("benchmark:relation",),
            subject_refs=("benchmark:subject",),
            source_classification="TEST_FIXTURE",
            source_ref=f"benchmark:{gate.lower()}",
            evidence_refs=(f"benchmark:evidence:{gate.lower()}",),
            reason="frozen benchmark fixture",
        )
        for gate in ETHICS_GATES
    ]
    admission = evaluate_admission(
        action=binding["action_contract"],
        gate_receipts=gates,
        capability_status=PASS,
        authority_status=PASS,
        evidence_status=PASS,
    )
    return build_runtime_constitutional_packet(
        action_binding=binding,
        admission_receipt=admission,
    )


def _exchange_packet(subject: str, *, sequence: int = 0) -> dict[str, Any]:
    payload = {"kind": "OBSERVATION", "subject": subject, "value": sequence}
    payload_sha = _sha(payload)
    route = (0.2 + sequence * 1e-6, -0.05)
    core = {
        "schema": "PHASENAV_MEMORY_INFORMATION_EXCHANGE_V0_1",
        "version": "0.1.0",
        "subject_id": subject,
        "producer_id": "PHASENAV",
        "generation_id": "benchmark-gen-001",
        "sequence": sequence,
        "source_layer": "SEMANTIC",
        "target_layer": "RELATIONAL",
        "payload_sha256": payload_sha,
        "parent_envelope_ids": [],
        "provenance": ["benchmark:memory"],
        "dependencies": [f"model:{subject}"],
        "route_edge_potentials": list(route),
        "hop_count": 0,
        "hop_limit": 8,
        "epistemic": "CHYBA",
        "authority": "SHARED_COGNITION_ONLY",
        "canon_allowed": False,
    }
    theta = math.fsum(route)
    return {
        **core,
        "envelope_id": "px:" + _sha(core),
        "payload": payload,
        "transport": {
            "real": math.cos(theta),
            "imag": math.sin(theta),
            "phase": math.atan2(math.sin(theta), math.cos(theta)),
            "modulus": 1.0,
        },
        "claims": {
            "content_addressed_payload": True,
            "causal_lineage": True,
            "computational_u1_route_phase": True,
            "producer_identity_authenticated": False,
            "physical_nonlocal_signalling": False,
            "physical_channel_identified": False,
            "canon_promoted": False,
        },
    }


def _sync(sender: HiveAuthorityRuntime, receiver: HiveAuthorityRuntime) -> dict[str, Any]:
    sender_inventory = build_hive_inventory(sender, node_id="HIVE-A")
    receiver_inventory = build_hive_inventory(receiver, node_id="HIVE-B")
    prefixes = divergent_hive_buckets(sender_inventory, receiver_inventory)
    sender_manifest = build_hive_manifest(sender, node_id="HIVE-A", prefixes=prefixes)
    receiver_manifest = build_hive_manifest(receiver, node_id="HIVE-B", prefixes=prefixes)
    plan = plan_hive_delta(
        sender_inventory,
        receiver_inventory,
        sender_manifest,
        receiver_manifest,
    )
    delta = export_hive_delta(sender, plan)
    return {
        "sender_inventory": sender_inventory,
        "receiver_inventory": receiver_inventory,
        "prefixes": prefixes,
        "plan": plan,
        "delta": delta,
    }


def run_memory_convergence_benchmark(
    *,
    sizes: tuple[int, ...] = (10, 100, 500),
) -> dict[str, Any]:
    rows = []
    for size in sizes:
        sender = HiveAuthorityRuntime()
        receiver = HiveAuthorityRuntime()
        packets = [_exchange_packet(f"subject:{i:05d}", sequence=i) for i in range(size)]

        ingest_sender_ns = []
        for packet in packets:
            start = time.perf_counter_ns()
            ingest_exchange_envelope(sender, packet)
            ingest_sender_ns.append(time.perf_counter_ns() - start)

        shared = size // 2
        for packet in packets[:shared]:
            ingest_exchange_envelope(receiver, packet)

        start = time.perf_counter_ns()
        sync = _sync(sender, receiver)
        plan_export_ns = time.perf_counter_ns() - start
        delta = sync["delta"]
        expected_missing = size - shared
        transfer_count = len(delta["transfers"])

        start = time.perf_counter_ns()
        apply_hive_delta(receiver, delta, receiver_node_id="HIVE-B")
        apply_ns = time.perf_counter_ns() - start

        after_sender = build_hive_inventory(sender, node_id="HIVE-A")
        after_receiver = build_hive_inventory(receiver, node_id="HIVE-B")
        divergent_after = divergent_hive_buckets(after_sender, after_receiver)

        full_payload_bytes = sum(len(_canonical(packet)) for packet in packets)
        delta_bytes = len(_canonical(delta))
        rows.append(
            {
                "sender_items": size,
                "receiver_initial_items": shared,
                "expected_missing_items": expected_missing,
                "delta_transfer_count": transfer_count,
                "delta_exactly_missing_only": transfer_count == expected_missing,
                "divergent_bucket_count_before": len(sync["prefixes"]),
                "divergent_bucket_count_after": len(divergent_after),
                "converged": len(divergent_after) == 0,
                "sender_ingest_latency": _timing(ingest_sender_ns),
                "plan_and_export_ns": plan_export_ns,
                "apply_delta_ns": apply_ns,
                "full_packet_bytes_proxy": full_payload_bytes,
                "delta_bytes": delta_bytes,
                "delta_to_full_bytes_ratio": (
                    0.0 if full_payload_bytes == 0 else delta_bytes / full_payload_bytes
                ),
            }
        )
        sender.close()
        receiver.close()

    exact = {
        "all_delta_transfers_equal_missing_set": all(
            row["delta_exactly_missing_only"] for row in rows
        ),
        "all_receivers_converge": all(row["converged"] for row in rows),
    }
    return {
        "scope": "IN_PROCESS_EXCHANGE_MEMORY_ANTI_ENTROPY_CONVERGENCE",
        "rows": rows,
        "exact_invariants": exact,
        "performance_gate": "MEASURE_ONLY_NO_PROMOTION_THRESHOLD",
        "pass": all(exact.values()),
    }


def run_durable_hive_benchmark(
    *,
    sizes: tuple[int, ...] = (10, 100, 500),
) -> dict[str, Any]:
    rows = []
    for size in sizes:
        with tempfile.TemporaryDirectory(prefix="gremlin-hive-bench-") as td:
            path = Path(td) / "hive.sqlite3"
            runtime = HiveAuthorityRuntime(path)
            write_ns = []
            for i in range(size):
                start = time.perf_counter_ns()
                runtime.place_idempotent(
                    subject_id=f"durable:{i:05d}",
                    payload={"kind": "BENCH", "index": i},
                    priority=0.5,
                    semantic_key="benchmark/durable",
                    relation_phase=(i * 0.017) % (2.0 * math.pi),
                    provenance=("benchmark:durable",),
                    dependencies=(),
                )
                write_ns.append(time.perf_counter_ns() - start)

            start = time.perf_counter_ns()
            table = runtime.table()
            read_all_ns = time.perf_counter_ns() - start
            runtime.close()

            reopen_start = time.perf_counter_ns()
            reopened = HiveAuthorityRuntime(path)
            reopen_ns = time.perf_counter_ns() - reopen_start
            recovered = reopened.table()
            status = reopened.status()
            reopened.close()

            rows.append(
                {
                    "records": size,
                    "write_latency": _timing(write_ns),
                    "read_all_ns": read_all_ns,
                    "reopen_and_repair_ns": reopen_ns,
                    "recovered_record_count": len(recovered),
                    "all_records_recovered": len(recovered) == size,
                    "initial_record_count": len(table),
                    "persistence_mode": status["persistence"],
                }
            )

    exact = {
        "all_records_recovered": all(row["all_records_recovered"] for row in rows),
        "all_modes_sqlite_wal": all(
            row["persistence_mode"] == "SQLITE_WAL_SINGLE_AUTHORITY" for row in rows
        ),
    }
    return {
        "scope": "SQLITE_WAL_DURABLE_HIVE_SCALING_AND_REOPEN",
        "rows": rows,
        "exact_invariants": exact,
        "performance_gate": "MEASURE_ONLY_NO_PROMOTION_THRESHOLD",
        "pass": all(exact.values()),
    }


RAPHAEL_GENERATION = "raphael-benchmark-generation-001"


def _raphael_hash(value: str) -> str:
    return hashlib.blake2b(value.encode("utf-8"), digest_size=32).hexdigest()


def _raphael_evidence() -> list[dict[str, Any]]:
    return [
        {"producer": p, "status": "PASS", "receipt_commitment": _raphael_hash(p)}
        for p in ("GREMLIN", "OWL", "HOUND")
    ]


def _raphael_attestation(generation: str = RAPHAEL_GENERATION) -> dict[str, Any]:
    return {
        "schema": "GREMLIN_TRIPLE_PULSE_ATTESTATION_V0_1",
        "generation": generation,
        "identity_receipt": {"generation": generation, "status": "VERIFIED"},
        "domain_receipt": {"generation": generation, "status": "VERIFIED"},
        "authority_receipt": {"generation": generation, "status": "VERIFIED"},
    }


def _raphael_probe():
    return lambda: {
        "tether_status": "ACTIVE",
        "gremlin_attestation": _raphael_attestation(),
    }


def _raphael_decree_and_auth(index: int):
    observation = observe(
        objective=f"benchmark RAPHAEL mutation {index}",
        target_repository="AdrianLipa90/GREMLIN",
        target_branch="benchmark/raphael",
        target_sha="a" * 40,
        operations=[
            {
                "operation": "UPDATE_FILE",
                "path": "gremlin_mcp/core.py",
                "expected_blob_sha": "b" * 40,
                "content": f"updated-{index}",
            }
        ],
        evidence_receipts=_raphael_evidence(),
    )
    decision = judge(
        observation,
        decision=ACCEPT,
        rationale_codes=["EVIDENCE_CLOSED", "EXACT_SCOPE_BOUND"],
        required_tests=["pytest:raphael-benchmark"],
        postconditions=["authority.canon_allowed=false"],
    )
    decree = decision["decree"]
    auth = authorize(
        decree,
        actor="USER007",
        approved=True,
        observed_target_sha="a" * 40,
        gate_receipt=f"benchmark-operator-gate-{index}",
        tether_status="ACTIVE",
        gremlin_attestation=_raphael_attestation(),
    )
    return decree, auth


def _raphael_packet(decree: Mapping[str, Any], auth: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        "decree_commitment": decree["decree_commitment"],
        "authorization_commitment": auth["authorization_commitment"],
        "target_repository": decree["target_repository"],
        "target_branch": decree["target_branch"],
        "target_sha": decree["target_sha"],
        "scope_commitment": decree["scope_commitment"],
        "actor": auth["actor"],
        "gate_receipt": auth["gate_receipt"],
        "generation": auth["generation"],
        "gremlin_attestation_commitment": auth["gremlin_attestation_commitment"],
    }
    return _constitutional_packet(
        endpoint="raphael.execute",
        consequence_class="MUTATION",
        payload=payload,
    )


class _RaphaelBackend:
    def __init__(self, *, bad_receipt: bool = False) -> None:
        self.sha = "a" * 40
        self.bad_receipt = bad_receipt
        self.rolled_back = False

    def current_state(self):
        return {"target_sha": self.sha}

    def prepare(self, decree):
        return {
            "status": "PREPARED",
            "target_sha": self.sha,
            "scope_commitment": decree["scope_commitment"],
            "reservation_id": "benchmark-reservation",
            "rollback_state": {"target_sha": self.sha},
        }

    def apply_operation(self, operation):
        self.sha = "c" * 40
        return {
            "operation_commitment": (
                "0" * 64 if self.bad_receipt else operation["operation_commitment"]
            ),
            "status": "APPLIED",
        }

    def rollback(self, rollback_state, applied_results):
        self.rolled_back = True
        self.sha = rollback_state["target_sha"]
        return {"status": "ROLLED_BACK", "count": len(applied_results)}


def run_raphael_governance_benchmark(*, repetitions: int = 100) -> dict[str, Any]:
    success_ns: list[int] = []
    rollback_ns: list[int] = []
    success_count = 0
    rollback_count = 0

    for i in range(repetitions):
        decree, auth = _raphael_decree_and_auth(i)
        backend = _RaphaelBackend()
        start = time.perf_counter_ns()
        receipt = execute(
            decree,
            auth,
            backend=backend,
            ledger=InMemoryMutationLedger(),
            admission_probe=_raphael_probe(),
            constitutional_packet=_raphael_packet(decree, auth),
            test_runner=lambda name: name == "pytest:raphael-benchmark",
            postcondition_checker=lambda c: c == "authority.canon_allowed=false",
        )
        success_ns.append(time.perf_counter_ns() - start)
        success_count += int(
            receipt["status"] == "PASS"
            and receipt["mutation_authority_expired"] is True
            and backend.rolled_back is False
        )

    for i in range(repetitions):
        decree, auth = _raphael_decree_and_auth(100000 + i)
        backend = _RaphaelBackend(bad_receipt=True)
        start = time.perf_counter_ns()
        try:
            execute(
                decree,
                auth,
                backend=backend,
                ledger=InMemoryMutationLedger(),
                admission_probe=_raphael_probe(),
                constitutional_packet=_raphael_packet(decree, auth),
                test_runner=lambda _: True,
                postcondition_checker=lambda _: True,
            )
        except RaphaelExecutionError as exc:
            rollback_ns.append(time.perf_counter_ns() - start)
            rollback_count += int(
                exc.receipt["status"] == "ROLLED_BACK"
                and exc.receipt["failure_code"] == "OPERATION_RECEIPT_MISMATCH"
                and exc.receipt["mutation_authority_expired"] is True
                and backend.rolled_back is True
                and backend.sha == "a" * 40
            )
        else:
            rollback_ns.append(time.perf_counter_ns() - start)

    exact = {
        "all_successes_expire_authority": success_count == repetitions,
        "all_bad_operation_receipts_rollback": rollback_count == repetitions,
    }
    return {
        "scope": "IN_PROCESS_RAPHAEL_SUCCESS_AND_ROLLBACK_GOVERNANCE",
        "repetitions_per_lane": repetitions,
        "success_lane": {
            "exact_success_count": success_count,
            "expected_count": repetitions,
            "latency": _timing(success_ns),
        },
        "rollback_lane": {
            "exact_rollback_count": rollback_count,
            "expected_count": repetitions,
            "latency": _timing(rollback_ns),
        },
        "exact_invariants": exact,
        "performance_gate": "MEASURE_ONLY_NO_PROMOTION_THRESHOLD",
        "pass": all(exact.values()),
    }


def _ferret_request() -> dict[str, Any]:
    return {
        "target_url": "https://example.com/benchmark",
        "intent": "benchmark controlled actuator",
        "steps": [
            {"action": "navigate", "url": "https://example.com/benchmark"},
            {"action": "snapshot", "label": "benchmark"},
        ],
    }


def _ferret_packet(preview: Mapping[str, Any], auth: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        "preview_id": preview["preview_id"],
        "preview_commitment": preview["preview_commitment"],
        "authorization_id": auth["authorization_id"],
        "authorization_commitment": auth["authorization_commitment"],
        "actor": auth["actor"],
        "target_url": preview["target_url"],
    }
    return _constitutional_packet(
        endpoint="ferret.execute_authorized_action",
        consequence_class="MUTATION",
        payload=payload,
    )


def run_ferret_governance_benchmark(*, repetitions: int = 100) -> dict[str, Any]:
    success_ns: list[int] = []
    replay_ns: list[int] = []
    success_count = 0
    replay_block_count = 0

    for _ in range(repetitions):
        preview = prepare_action(_ferret_request())
        auth = authorize_action(preview, actor="USER007", approved=True)
        packet = _ferret_packet(preview, auth)
        ledger = InMemoryFerretExecutionLedger()

        def executor(_preview):
            return FerretExecutionResult(
                status="SUBMITTED",
                resolved_url="https://example.com/benchmark/confirmation",
                evidence={"benchmark": True},
            )

        start = time.perf_counter_ns()
        receipt = execute_authorized_action(
            preview,
            auth,
            executor,
            ledger=ledger,
            constitutional_packet=packet,
        )
        success_ns.append(time.perf_counter_ns() - start)
        success_count += int(
            receipt["status"] == "SUBMITTED"
            and receipt["authorization_consumed"] is True
        )

        start = time.perf_counter_ns()
        try:
            execute_authorized_action(
                preview,
                auth,
                executor,
                ledger=ledger,
                constitutional_packet=packet,
            )
        except FerretAuthorizationError:
            replay_ns.append(time.perf_counter_ns() - start)
            replay_block_count += 1
        else:
            replay_ns.append(time.perf_counter_ns() - start)

    exact = {
        "all_valid_actions_execute_once": success_count == repetitions,
        "all_authorization_replays_blocked": replay_block_count == repetitions,
    }
    return {
        "scope": "IN_PROCESS_FERRET_CONSTITUTIONAL_SINGLE_USE_ACTUATION",
        "repetitions": repetitions,
        "success_lane": {
            "exact_success_count": success_count,
            "latency": _timing(success_ns),
        },
        "replay_lane": {
            "exact_replay_block_count": replay_block_count,
            "latency": _timing(replay_ns),
        },
        "exact_invariants": exact,
        "performance_gate": "MEASURE_ONLY_NO_PROMOTION_THRESHOLD",
        "pass": all(exact.values()),
    }


def run_memory_and_governance_suite() -> dict[str, Any]:
    memory = run_memory_convergence_benchmark()
    durable = run_durable_hive_benchmark()
    raphael = run_raphael_governance_benchmark()
    ferret = run_ferret_governance_benchmark()
    exact_pass = bool(
        memory["pass"] and durable["pass"] and raphael["pass"] and ferret["pass"]
    )
    receipt = {
        "schema": SCHEMA,
        "version": VERSION,
        "memory_convergence": memory,
        "durable_hive": durable,
        "raphael_governance": raphael,
        "ferret_governance": ferret,
        "summary": {
            "memory_convergence_pass": memory["pass"],
            "durable_hive_pass": durable["pass"],
            "raphael_governance_pass": raphael["pass"],
            "ferret_governance_pass": ferret["pass"],
            "all_exact_invariants_pass": exact_pass,
        },
    }
    receipt["receipt_sha256"] = _sha(receipt)
    return receipt


if __name__ == "__main__":
    print(json.dumps(run_memory_and_governance_suite(), indent=2, sort_keys=True))
