from __future__ import annotations

import json

import pytest

from gremlin_mcp.owl_runtime_audit import OwlRuntimeAuditor, owl_runtime_boundary


def test_success_receipts_are_hash_chained_and_stats_are_online(tmp_path) -> None:
    path = tmp_path / "owl.jsonl"
    auditor = OwlRuntimeAuditor(path)

    first = auditor.begin("tool.alpha", (1,), {"species": "OWL"})
    r1 = auditor.finish_success(first, {"tool_calls": 2, "result": "ok"})
    second = auditor.begin("tool.alpha", (2,), {})
    r2 = auditor.finish_success(second, {"tool_calls": 4, "result": "ok"})

    assert r1["sequence"] == 1
    assert r2["sequence"] == 2
    assert r2["previous_record_hash"] == r1["record_hash"]

    stats = auditor.snapshot()["tools"]["tool.alpha"]
    assert stats["calls"] == 2
    assert stats["successes"] == 2
    assert stats["errors"] == 0
    assert stats["observable"]["tool_calls"]["mean"] == 3.0


def test_raw_payload_is_not_persisted(tmp_path) -> None:
    path = tmp_path / "owl.jsonl"
    auditor = OwlRuntimeAuditor(path)
    sensitive_value = "payload-value-not-for-ledger"

    span = auditor.begin("tool.secret", (), {"payload": {"value": sensitive_value}})
    auditor.finish_success(span, {"answer": sensitive_value})

    text = path.read_text(encoding="utf-8")
    assert sensitive_value not in text
    assert "call_commitment" in text
    assert "output_commitment" in text


def test_error_receipt_updates_error_statistics(tmp_path) -> None:
    auditor = OwlRuntimeAuditor(tmp_path / "owl.jsonl")
    span = auditor.begin("tool.beta", (), {})
    receipt = auditor.finish_error(span, ValueError("bad"), "INVALID_REQUEST")

    assert receipt["status"] == "ERROR"
    assert receipt["error_code"] == "INVALID_REQUEST"
    stats = auditor.snapshot()["tools"]["tool.beta"]
    assert stats["errors"] == 1
    assert stats["error_rate"] == 1.0


def test_restart_replays_and_verifies_ledger(tmp_path) -> None:
    path = tmp_path / "owl.jsonl"
    first = OwlRuntimeAuditor(path)
    for value in range(3):
        span = first.begin("tool.gamma", (value,), {})
        first.finish_success(span, {"result": value})

    second = OwlRuntimeAuditor(path)
    snapshot = second.snapshot()
    assert snapshot["status"] == "PASS"
    assert snapshot["event_count"] == 3
    assert snapshot["record_count"] == 3
    assert snapshot["tools"]["tool.gamma"]["calls"] == 3


def test_tampered_ledger_is_reported_degraded(tmp_path) -> None:
    path = tmp_path / "owl.jsonl"
    auditor = OwlRuntimeAuditor(path)
    span = auditor.begin("tool.delta", (), {})
    auditor.finish_success(span, {"ok": True})

    record = json.loads(path.read_text(encoding="utf-8").strip())
    record["duration_ns"] += 1
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    replay = OwlRuntimeAuditor(path)
    snapshot = replay.snapshot()
    assert snapshot["status"] == "DEGRADED"
    assert "hash mismatch" in snapshot["last_error"]


def test_error_rate_emits_candidate_without_auto_apply(tmp_path) -> None:
    auditor = OwlRuntimeAuditor(tmp_path / "owl.jsonl")
    for index in range(20):
        span = auditor.begin("tool.epsilon", (index,), {})
        if index < 3:
            auditor.finish_error(span, RuntimeError("boom"), "RUNTIME_ERROR")
        else:
            auditor.finish_success(span, {"ok": True})

    candidates = auditor.snapshot()["recent_candidates"]
    assert len(candidates) == 1
    assert candidates[0]["kind"] == "ERROR_RATE"
    assert candidates[0]["status"] == "CANDIDATE_ONLY"
    assert candidates[0]["auto_apply"] is False
    assert candidates[0]["authority"]["mutation_allowed"] is False


def test_boundary_preserves_return_and_exception_semantics(monkeypatch, tmp_path) -> None:
    import gremlin_mcp.owl_runtime_audit as owl

    monkeypatch.setattr(owl, "GLOBAL_OWL_AUDITOR", OwlRuntimeAuditor(tmp_path / "owl.jsonl"))

    @owl_runtime_boundary
    def good(value: int) -> int:
        return value + 1

    @owl_runtime_boundary
    def bad() -> None:
        raise KeyError("expected")

    assert good(4) == 5
    with pytest.raises(KeyError, match="expected"):
        bad()

    snapshot = owl.audit_status()
    assert snapshot["tools"]["good"]["successes"] == 1
    assert snapshot["tools"]["bad"]["errors"] == 1
