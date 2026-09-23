from __future__ import annotations

import json

import pytest

from gremlin_mcp.continuous_benchmark import (
    ContinuousBenchmarkLedger,
    configure_continuous_benchmark,
    prompt_benchmark_scope,
)
from gremlin_mcp.router import route


def test_octopus_route_is_logged_without_persisting_raw_prompt(tmp_path) -> None:
    path = tmp_path / "continuous.jsonl"
    ledger = configure_continuous_benchmark(path)
    secret = "RAW_PROMPT_SENTINEL_DO_NOT_PERSIST_9f17"
    decision = route({"query": f"audit evidence provenance {secret}"})

    assert decision["route_mask"]
    text = path.read_text(encoding="utf-8")
    assert secret not in text

    rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    assert [row["event_type"] for row in rows] == [
        "PROMPT_OPEN",
        "OCTOPUS_ROUTE",
        "PROMPT_CLOSE",
    ]
    assert rows[0]["source"] == "IMPLICIT_OCTOPUS_ROUTE"
    assert rows[1]["route_commitment"] == decision["route_commitment"]
    assert rows[1]["route_mask"] == decision["route_mask"]
    assert rows[2]["status"] == "ROUTE_ONLY"

    status = ledger.snapshot()
    assert status["prompts"]["opened"] == 1
    assert status["prompts"]["closed"] == 1
    assert status["routing"]["routes"] == 1
    assert status["policy"]["raw_prompt_persisted"] is False
    configure_continuous_benchmark(":memory:")


def test_explicit_prompt_scope_links_route_validation_and_close(tmp_path) -> None:
    path = tmp_path / "continuous.jsonl"
    ledger = configure_continuous_benchmark(path)

    with prompt_benchmark_scope(
        {"query": "map dependency graph then validate evidence"},
        generation="generation-test-1",
        labels={"task_class": "repository_audit"},
    ) as span:
        decision = route(
            {
                "query": "map dependency graph and audit evidence",
                "dependencies": ["A->B"],
                "sources": ["fixture"],
            },
            max_species=4,
            relative_cutoff=0.25,
        )
        ledger.record_validation(
            span.prompt_id,
            status="PASS",
            validators=("HOUND", "OWL"),
            correction_count=1,
            retry_count=2,
            regression_count=0,
            provenance_complete=True,
            evidence={"fixture": "validated"},
            generation=span.generation,
        )
        ledger.finish_prompt(
            span.prompt_id,
            status="PASS",
            success=True,
            outcome={"result": "validated"},
            metrics={"tool_calls": 5},
            generation=span.generation,
        )

    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    prompt_ids = {row["prompt_id"] for row in rows}
    assert prompt_ids == {span.prompt_id}
    assert [row["event_type"] for row in rows] == [
        "PROMPT_OPEN",
        "OCTOPUS_ROUTE",
        "VALIDATION",
        "PROMPT_CLOSE",
    ]
    assert rows[1]["route_commitment"] == decision["route_commitment"]

    status = ledger.snapshot()
    assert status["prompts"]["success_rate"] == 1.0
    assert status["validation"]["pass_rate"] == 1.0
    assert status["validation"]["correction_count"]["mean"] == 1.0
    assert status["validation"]["retry_count"]["mean"] == 2.0
    assert status["generation_event_counts"]["generation-test-1"] == 4
    configure_continuous_benchmark(":memory:")


def test_ablation_records_only_measured_numeric_delta(tmp_path) -> None:
    ledger = configure_continuous_benchmark(tmp_path / "continuous.jsonl")
    span = ledger.begin_prompt({"query": "same task"}, generation="g")
    receipt = ledger.record_ablation(
        span.prompt_id,
        ablation="WITHOUT_GREMLIN",
        baseline_metrics={
            "success": 1,
            "tool_calls": 8,
            "label": "not numeric",
        },
        ablated_metrics={
            "success": 0,
            "tool_calls": 13,
            "label": "also ignored",
        },
        method="REPLAY_SAME_FROZEN_TASK",
        exact_same_task=True,
        generation="g",
    )
    assert receipt["delta_ablated_minus_baseline"] == {
        "success": -1.0,
        "tool_calls": 5.0,
    }
    assert receipt["exact_same_task"] is True
    assert ledger.snapshot()["ablations"] == 1
    configure_continuous_benchmark(":memory:")


def test_hash_chain_tamper_degrades_and_refuses_append(tmp_path) -> None:
    path = tmp_path / "continuous.jsonl"
    ledger = ContinuousBenchmarkLedger(path)
    span = ledger.begin_prompt({"query": "audit"})
    ledger.finish_prompt(span.prompt_id, status="PASS", success=True)

    rows = path.read_text(encoding="utf-8").splitlines()
    first = json.loads(rows[0])
    first["source"] = "TAMPERED"
    rows[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    damaged = ContinuousBenchmarkLedger(path)
    assert damaged.snapshot()["status"] == "DEGRADED"
    with pytest.raises(RuntimeError, match="CONTINUOUS_BENCHMARK_DEGRADED"):
        damaged.begin_prompt({"query": "must fail"})


def test_route_result_is_semantically_unchanged_by_benchmark_hook(tmp_path) -> None:
    configure_continuous_benchmark(tmp_path / "continuous.jsonl")
    payload = {"query": "derive equation and verify contradiction"}
    a = route(payload)
    b = route(payload)
    assert a["route_commitment"] == b["route_commitment"]
    assert a["route_mask"] == b["route_mask"]
    assert "benchmark" not in a
    configure_continuous_benchmark(":memory:")
