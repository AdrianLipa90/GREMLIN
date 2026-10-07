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


def _live(
    root: Path,
    *,
    tether: str = "ACTIVE",
    domain: str = "ACTIVE",
    authority: str = "VERIFIED",
    mismatch: bool = False,
) -> None:
    generation = "gen-native-001"
    (root / "session").mkdir(parents=True)
    (root / "gremlin").mkdir(parents=True)
    (root / "system_sync").mkdir(parents=True)
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
    (root / "system_sync/CURRENT.json").write_text(
        json.dumps(
            {
                "schema": "NOEMA_SYSTEM_SYNC_CURRENT_V1",
                "status": "ALIGNED_CANDIDATE",
                "generation": generation,
                "canon_allowed": False,
                "sync_sha256": "a" * 64,
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
                "domain_receipt": {
                    "generation": "other" if mismatch else generation,
                    "status": domain,
                },
                "authority_receipt": {"generation": generation, "status": authority},
            }
        ),
        encoding="utf-8",
    )


def test_manifest_splits_source_work_from_live_production() -> None:
    manifest = native_admission_manifest()
    assert manifest["mode"] == "PNV_NATIVE_SPLIT_AUTHORITY_PYTHON_TRANSPORT_ONLY"
    assert manifest["authority_model"] == "SOURCE_WORK_VS_LIVE_PRODUCTION"
    assert manifest["source_work"]["live_tether_required"] is False
    assert manifest["source_work"]["global_action_denial"] is False
    assert manifest["live_production"]["live_tether_required"] is True
    assert manifest["key_mutations"] == "REVIEW_REQUIRED"
    assert len(manifest["live_pnv_sha256"]) == 64
    assert len(manifest["source_work_pnv_sha256"]) == 64


def test_read_only_call_passes_without_live_tether(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GREMLIN_NOEMA_RUNTIME_ROOT", str(tmp_path))
    receipt = admit_tool_call("gremlin_status", (), {})
    assert receipt["status"] == "PASS"
    assert receipt["authority_lane"] == "SOURCE_WORK"
    assert receipt["source_work_authority"] == "ACTIVE"
    assert receipt["live_production_authority"] == "NOT_GRANTED"
    assert receipt["mutation_tier"] == "READ_ONLY"
    assert receipt["tether_required"] is False
    assert receipt["tether_status"] == "NOT_REQUIRED"
    assert receipt["global_action_denial"] is False


def test_local_state_mutation_is_source_work_without_live_tether(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GREMLIN_NOEMA_RUNTIME_ROOT", str(tmp_path))
    facts = admission_facts("gremlin_worker_enqueue")
    assert facts["tier"] == "LOW_RISK_AUTO"
    receipt = admit_tool_call("gremlin_worker_enqueue", (), {})
    assert receipt["status"] == "PASS"
    assert receipt["authority_lane"] == "SOURCE_WORK"
    assert receipt["local_state_write"] is True
    assert receipt["tether_required"] is False
    assert receipt["production_effect_admitted_by_request"] is False
    assert receipt["canon_promotion_admitted_by_request"] is False


def test_read_only_call_is_not_revoked_by_inactive_live_tether(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _live(tmp_path, tether="FAIL")
    monkeypatch.setenv("GREMLIN_NOEMA_RUNTIME_ROOT", str(tmp_path))
    receipt = admit_tool_call("gremlin_status", (), {})
    assert receipt["status"] == "PASS"
    assert receipt["authority_lane"] == "SOURCE_WORK"
    assert receipt["tether_status"] == "NOT_REQUIRED"


def test_unknown_or_key_mutation_still_requires_live_guard(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GREMLIN_NOEMA_RUNTIME_ROOT", str(tmp_path))
    with pytest.raises(PNVNativeAdmissionError, match="PNV_NATIVE_TETHER_GUARD_UNAVAILABLE"):
        admit_tool_call("gremlin_git_merge_main", (), {})


def test_key_mutation_fails_with_inactive_tether(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _live(tmp_path, tether="FAIL")
    monkeypatch.setenv("GREMLIN_NOEMA_RUNTIME_ROOT", str(tmp_path))
    with pytest.raises(PNVNativeAdmissionError):
        admit_tool_call("gremlin_git_merge_main", (), {})


def test_key_mutation_fails_on_cross_generation_triple_pulse(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _live(tmp_path, mismatch=True)
    monkeypatch.setenv("GREMLIN_NOEMA_RUNTIME_ROOT", str(tmp_path))
    with pytest.raises(PNVNativeAdmissionError):
        admit_tool_call("gremlin_git_merge_main", (), {})


def test_key_mutation_fails_when_system_sync_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _live(tmp_path)
    (tmp_path / "system_sync/CURRENT.json").unlink()
    monkeypatch.setenv("GREMLIN_NOEMA_RUNTIME_ROOT", str(tmp_path))
    with pytest.raises(PNVNativeAdmissionError):
        admit_tool_call("gremlin_git_merge_main", (), {})
