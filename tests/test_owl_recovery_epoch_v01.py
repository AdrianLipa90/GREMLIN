"""Regression tests for explicit OWL audit ledger recovery.

A damaged ledger must remain byte-for-byte unchanged. The recovery epoch has
a distinct journal path, a source hash witness, and a fresh verifiable chain.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from gremlin_mcp.owl_runtime_audit import OwlRuntimeAuditor


def test_recovery_preserves_original_and_creates_new_verified_epoch(tmp_path):
    original = tmp_path / "owl.jsonl"
    writer = OwlRuntimeAuditor(original)
    span = writer.begin("tool.before", (), {})
    writer.finish_success(span, {"ok": True})

    record = json.loads(original.read_text(encoding="utf-8"))
    record["duration_ns"] += 1
    original.write_text(json.dumps(record) + "\n", encoding="utf-8")
    damaged_bytes = original.read_bytes()

    corrupted = OwlRuntimeAuditor(original)
    assert corrupted.snapshot()["status"] == "DEGRADED"
    recovered = corrupted.start_recovery_epoch()

    assert original.read_bytes() == damaged_bytes
    assert corrupted.snapshot()["status"] == "DEGRADED"
    assert recovered.path != original
    assert recovered.snapshot()["status"] == "PASS"

    marker = json.loads(recovered.path.read_text(encoding="utf-8").splitlines()[0])
    assert marker["record_type"] == "AUDIT_RECOVERY_EPOCH"
    assert marker["source_ledger_sha256"] == hashlib.sha256(damaged_bytes).hexdigest()
    assert marker["historical_continuity_verified"] is False
    assert marker["original_ledger_preserved"] is True

    span = recovered.begin("tool.after", (), {})
    recovered.finish_success(span, {"ok": True})
    restart = OwlRuntimeAuditor(recovered.path)
    assert restart.snapshot()["status"] == "PASS"
    assert restart.snapshot()["record_count"] == 2
    assert restart.snapshot()["event_count"] == 1
    assert original.read_bytes() == damaged_bytes



def test_global_recovery_restores_observation_without_mutating_source(monkeypatch, tmp_path):
    import gremlin_mcp.owl_runtime_audit as owl

    original = tmp_path / "owl.jsonl"
    early = OwlRuntimeAuditor(original)
    early.finish_success(early.begin("early", (), {}), {"ok": True})
    payload = json.loads(original.read_text(encoding="utf-8"))
    payload["status"] = "ERROR"
    original.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    damaged = original.read_bytes()

    monkeypatch.setattr(owl, "GLOBAL_OWL_AUDITOR", OwlRuntimeAuditor(original))
    assert owl.audit_status()["status"] == "DEGRADED"
    witness = owl.recover_global_owl_audit()
    assert witness["status"] == "RECOVERED"
    assert witness["source_ledger_health"] == "DEGRADED"
    assert witness["historical_continuity_verified"] is False
    assert original.read_bytes() == damaged

    span = owl.begin_use("after_recovery", (), {})
    assert owl.finish_use_success(span, {"ok": True})["sequence"] == 2
    new = OwlRuntimeAuditor(witness["recovery_ledger"])
    assert new.snapshot()["status"] == "PASS"
    assert new.snapshot()["record_count"] == 2
    assert new.snapshot()["event_count"] == 1
    assert original.read_bytes() == damaged



def test_healthy_ledger_cannot_be_recovered(tmp_path):
    healthy = OwlRuntimeAuditor(tmp_path / "owl.jsonl")
    with pytest.raises(RuntimeError, match="OWL_AUDIT_RECOVERY_REQUIRES_DEGRADED"):
        healthy.start_recovery_epoch()


def test_wrapper_replays_receipt_into_new_epoch_without_rerunning_tool(monkeypatch, tmp_path):
    import gremlin_mcp.owl_runtime_audit as owl

    source = tmp_path / "owl.jsonl"
    original = OwlRuntimeAuditor(source)
    original.finish_success(original.begin("original", (), {}), {"ok": True})
    corrupted = json.loads(source.read_text(encoding="utf-8"))
    corrupted["duration_ns"] += 19
    source.write_text(json.dumps(corrupted) + "\n", encoding="utf-8")
    original_bytes = source.read_bytes()
    monkeypatch.setattr(owl, "GLOBAL_OWL_AUDITOR", OwlRuntimeAuditor(source))
    calls = []

    @owl.owl_runtime_boundary
    def once():
        calls.append("once")
        return "worked"

    with pytest.warns(RuntimeWarning, match="Historical continuity remains UNVERIFIED"):
        assert once() == "worked"
    assert calls == ["once"]
    assert source.read_bytes() == original_bytes
    current = owl.GLOBAL_OWL_AUDITOR
    assert current.path != source
    assert owl.audit_status()["status"] == "PASS"
    replay = OwlRuntimeAuditor(current.path)
    assert replay.snapshot()["status"] == "PASS"
    assert replay.snapshot()["record_count"] == 2
    assert replay.snapshot()["event_count"] == 1


def test_wrapper_recovers_error_receipt_and_preserves_original(monkeypatch, tmp_path):
    import gremlin_mcp.owl_runtime_audit as owl

    source = tmp_path / "owl.jsonl"
    original = OwlRuntimeAuditor(source)
    original.finish_success(original.begin("before", (), {}), {"ok": True})
    record = json.loads(source.read_text(encoding="utf-8"))
    record["duration_ns"] += 5
    source.write_text(json.dumps(record) + "\n", encoding="utf-8")
    original_bytes = source.read_bytes()
    monkeypatch.setattr(owl, "GLOBAL_OWL_AUDITOR", OwlRuntimeAuditor(source))

    span = owl.begin_use("error_after_recovery", (), {})
    with pytest.warns(RuntimeWarning, match="Historical continuity remains UNVERIFIED"):
        receipt = owl.finish_use_error(span, ValueError("bad request"), "INVALID_REQUEST")
    assert receipt is not None
    assert receipt["status"] == "ERROR"
    assert receipt["sequence"] == 2
    assert source.read_bytes() == original_bytes
    assert owl.audit_status()["tools"]["error_after_recovery"]["errors"] == 1
