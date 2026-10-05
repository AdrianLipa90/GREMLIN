from __future__ import annotations

import json
from pathlib import Path

import pytest

from gremlin_mcp.pnv_native_admission import (
    PNVNativeAdmissionError,
    admit_tool_call,
    admission_facts,
    native_admission_manifest,
)


def _live(root: Path, *, tether: str = "ACTIVE", domain: str = "ACTIVE", authority: str = "VERIFIED", mismatch: bool = False) -> None:
    generation = "gen-native-001"
    (root / "session").mkdir(parents=True)
    (root / "gremlin").mkdir(parents=True)
    (root / "session/tether_guard_latest.json").write_text(
        json.dumps(
            {
                "schema": "NOEMA_TETHER_GUARD_LATEST_V1",
                "status": tether,
                "tether_status": tether,
                "failures": [],
            }
        ),
        encoding="utf-8",
    )
    (root / "gremlin/triple_pulse_attestation.json").write_text(
        json.dumps(
            {
                "schema": "GREMLIN_TRIPLE_PULSE_ATTESTATION_V0_1",
                "generation": generation,
                "identity_receipt": {"generation": generation, "status": "VERIFIED"},
                "domain_receipt": {"generation": "other" if mismatch else generation, "status": domain},
                "authority_receipt": {"generation": generation, "status": authority},
            }
        ),
        encoding="utf-8",
    )


def test_manifest_is_pnv_authoritative() -> None:
    manifest = native_admission_manifest()
    assert manifest["mode"] == "PNV_NATIVE_POLICY_PYTHON_TRANSPORT_ONLY"
    assert manifest["key_mutations"] == "REVIEW_REQUIRED"
    assert manifest["main_mutation_auto"] is False
    assert len(manifest["pnv_sha256"]) == 64


def test_read_only_call_passes_with_live_same_generation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _live(tmp_path)
    monkeypatch.setenv("GREMLIN_NOEMA_RUNTIME_ROOT", str(tmp_path))
    receipt = admit_tool_call("gremlin_status", (), {})
    assert receipt["status"] == "PASS"
    assert receipt["mutation_tier"] == "READ_ONLY"
    assert receipt["triple_pulse_same_generation"] is True


def test_local_state_mutation_is_low_risk_auto(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _live(tmp_path)
    monkeypatch.setenv("GREMLIN_NOEMA_RUNTIME_ROOT", str(tmp_path))
    facts = admission_facts("gremlin_worker_enqueue")
    assert facts["tier"] == "LOW_RISK_AUTO"
    receipt = admit_tool_call("gremlin_worker_enqueue", (), {})
    assert receipt["status"] == "PASS"
    assert receipt["local_state_write"] is True
    assert receipt["production_runtime_write"] is False
    assert receipt["canon_allowed"] is False


def test_unknown_or_key_mutation_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _live(tmp_path)
    monkeypatch.setenv("GREMLIN_NOEMA_RUNTIME_ROOT", str(tmp_path))
    with pytest.raises(PNVNativeAdmissionError):
        admit_tool_call("gremlin_git_merge_main", (), {})


def test_inactive_tether_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _live(tmp_path, tether="FAIL")
    monkeypatch.setenv("GREMLIN_NOEMA_RUNTIME_ROOT", str(tmp_path))
    with pytest.raises(PNVNativeAdmissionError):
        admit_tool_call("gremlin_status", (), {})


def test_cross_generation_triple_pulse_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _live(tmp_path, mismatch=True)
    monkeypatch.setenv("GREMLIN_NOEMA_RUNTIME_ROOT", str(tmp_path))
    with pytest.raises(PNVNativeAdmissionError):
        admit_tool_call("gremlin_status", (), {})
