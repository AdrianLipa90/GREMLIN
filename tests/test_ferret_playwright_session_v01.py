from __future__ import annotations

import json
from pathlib import Path

import pytest

from gremlin_mcp.ferret import (
    complete_human_handoff,
    detect_human_gate,
    prepare_action,
    prepare_human_handoff,
)
from gremlin_mcp.ferret_playwright import (
    FerretBrowserSessionError,
    persist_storage_state,
    verify_storage_state_for_resume,
    wait_for_human_gate_clear,
)


class FakeContext:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def storage_state(self, *, path: str) -> dict:
        Path(path).write_text(json.dumps(self.payload, sort_keys=True), encoding="utf-8")
        return self.payload


class FakePage:
    def __init__(self) -> None:
        self.waits: list[int] = []

    def wait_for_timeout(self, ms: int) -> None:
        self.waits.append(ms)


def _preview() -> dict:
    return prepare_action(
        {
            "target_url": "https://example.com/complaints",
            "intent": "Prepare complaint after human verification",
            "steps": [
                {"action": "navigate", "url": "https://example.com/complaints"},
                {"action": "snapshot", "label": "post-gate"},
            ],
        }
    )


def _gate() -> dict:
    gate = detect_human_gate(
        {
            "resolved_url": "https://example.com/complaints",
            "title": "Security check",
            "body_text": "Please verify you are human",
            "frames": [
                {
                    "name": "hcaptcha",
                    "url": "https://newassets.hcaptcha.com/captcha/v1/abc/static/hcaptcha.html",
                    "text": "I am human",
                }
            ],
            "fields": [{"name": "h-captcha-response"}],
        }
    )
    assert gate is not None
    return gate


def test_storage_state_is_persisted_private_and_hashed(tmp_path: Path) -> None:
    context = FakeContext(
        {
            "cookies": [{"name": "session", "value": "secret-cookie"}],
            "origins": [],
        }
    )
    path = tmp_path / "ferret-state.json"
    receipt = persist_storage_state(context, path)

    assert path.exists()
    assert len(receipt["sha256"]) == 64
    assert receipt["bytes"] == path.stat().st_size
    assert receipt["secret_material_returned"] is False
    assert "secret-cookie" not in json.dumps(receipt)
    assert path.stat().st_mode & 0o777 == 0o600


def test_resume_verification_accepts_exact_private_state(tmp_path: Path) -> None:
    preview = _preview()
    handoff = prepare_human_handoff(
        preview,
        _gate(),
        resolved_url="https://example.com/complaints",
    )
    path = tmp_path / "state.json"
    state_receipt = persist_storage_state(FakeContext({"cookies": [], "origins": []}), path)
    resume = complete_human_handoff(
        handoff,
        actor="USER007",
        completed=True,
        resolved_url="https://example.com/complaints?verified=1",
        storage_state_sha256=state_receipt["sha256"],
    )

    verified = verify_storage_state_for_resume(handoff, resume, path)
    assert verified["status"] == "VERIFIED"
    assert verified["storage_state_sha256"] == state_receipt["sha256"]


def test_resume_verification_rejects_changed_state(tmp_path: Path) -> None:
    preview = _preview()
    handoff = prepare_human_handoff(
        preview,
        _gate(),
        resolved_url="https://example.com/complaints",
    )
    path = tmp_path / "state.json"
    state_receipt = persist_storage_state(FakeContext({"cookies": [], "origins": []}), path)
    resume = complete_human_handoff(
        handoff,
        actor="USER007",
        completed=True,
        resolved_url="https://example.com/complaints",
        storage_state_sha256=state_receipt["sha256"],
    )
    path.write_text('{"cookies":[{"name":"tampered"}]}', encoding="utf-8")

    with pytest.raises(FerretBrowserSessionError, match="hash mismatch"):
        verify_storage_state_for_resume(handoff, resume, path)


def test_wait_for_human_gate_clear_only_observes() -> None:
    page = FakePage()
    sequence = iter(
        [
            {"body_text": "hcaptcha verify you are human", "fields": [{"name": "h-captcha-response"}]},
            {"body_text": "hcaptcha verify you are human", "fields": [{"name": "h-captcha-response"}]},
            {"body_text": "Complaint form", "fields": [{"name": "message"}]},
        ]
    )

    def observe(_page):
        return next(sequence)

    result = wait_for_human_gate_clear(
        page,
        observe=observe,
        timeout_s=1.0,
        poll_ms=1,
    )
    assert result["status"] == "HUMAN_GATE_CLEARED"
    assert result["automated_solution_attempted"] is False
    assert page.waits == [1, 1]


def test_wait_for_human_gate_clear_times_out_fail_closed() -> None:
    page = FakePage()

    def observe(_page):
        return {"body_text": "hcaptcha verify you are human", "fields": [{"name": "h-captcha-response"}]}

    with pytest.raises(FerretBrowserSessionError, match="timed out"):
        wait_for_human_gate_clear(
            page,
            observe=observe,
            timeout_s=0.001,
            poll_ms=1,
        )
