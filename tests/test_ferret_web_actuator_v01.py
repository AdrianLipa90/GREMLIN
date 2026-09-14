from __future__ import annotations

import copy

import pytest

from gremlin_mcp.ferret import (
    FerretAuthorizationError,
    FerretExecutionResult,
    FerretHandoffError,
    authorize_action,
    complete_human_handoff,
    detect_human_gate,
    execute_authorized_action,
    prepare_action,
    prepare_human_handoff,
    verify_authorization,
    verify_handoff_resume,
)


def _request() -> dict:
    return {
        "target_url": "https://example.com/complaints",
        "intent": "Submit a consumer complaint with evidence",
        "steps": [
            {"action": "navigate", "url": "https://example.com/complaints"},
            {"action": "fill", "selector": "#subject", "value": "Incorrect plan"},
            {"action": "fill", "selector": "#password", "secret": True, "secret_ref": "complaint-password"},
            {"action": "upload", "selector": "input[type=file]", "files": ["/tmp/evidence.png"]},
            {"action": "click", "selector": "button[type=submit]"},
            {"action": "snapshot", "label": "confirmation"},
        ],
    }


def _captcha_observation() -> dict:
    return {
        "resolved_url": "https://example.com/complaints",
        "title": "Additional security check",
        "body_text": "Additional security check is required. I am human.",
        "frames": [
            {
                "name": "main-iframe",
                "url": "https://example.com/complaints",
                "text": "Additional security check is required",
            },
            {
                "name": "hcaptcha",
                "url": "https://newassets.hcaptcha.com/captcha/v1/123/static/hcaptcha.html",
                "text": "I am human",
            },
        ],
        "fields": [
            {"tag": "textarea", "name": "h-captcha-response"},
            {"tag": "textarea", "name": "g-recaptcha-response"},
        ],
    }


def test_prepare_is_receipt_bound_and_redacts_secret() -> None:
    preview = prepare_action(_request())
    assert preview["requires_explicit_approval"] is True
    assert preview["approval_scope"] == "EXACT_PREVIEW_COMMITMENT"
    assert preview["steps"][2]["value"] == "<REDACTED>"
    assert preview["steps"][2]["secret"] is True
    assert preview["steps"][2]["secret_ref"] == "complaint-password"
    assert len(preview["preview_commitment"]) == 64


def test_authorization_is_exact_preview_scoped() -> None:
    preview = prepare_action(_request())
    authorization = authorize_action(preview, actor="USER007", approved=True)
    verify_authorization(preview, authorization)

    tampered = copy.deepcopy(preview)
    tampered["steps"][1]["value"] = "different"
    with pytest.raises(FerretAuthorizationError):
        verify_authorization(tampered, authorization)


def test_rejects_missing_explicit_approval() -> None:
    preview = prepare_action(_request())
    with pytest.raises(FerretAuthorizationError):
        authorize_action(preview, actor="USER007", approved=False)


def test_rejects_cross_origin_navigation() -> None:
    request = _request()
    request["steps"][0] = {"action": "navigate", "url": "https://other.example/complaints"}
    with pytest.raises(ValueError, match="cross-origin"):
        prepare_action(request)


def test_execution_receipt_binds_preview_and_authorization() -> None:
    preview = prepare_action(_request())
    authorization = authorize_action(preview, actor="USER007", approved=True)

    def executor(_preview):
        return FerretExecutionResult(
            status="SUBMITTED",
            resolved_url="https://example.com/complaints/confirmation",
            evidence={"case_id": "CASE-123", "screenshot_sha256": "a" * 64},
        )

    receipt = execute_authorized_action(preview, authorization, executor)
    assert receipt["status"] == "SUBMITTED"
    assert receipt["preview_commitment"] == preview["preview_commitment"]
    assert receipt["authorization_commitment"] == authorization["authorization_commitment"]
    assert receipt["evidence"]["case_id"] == "CASE-123"
    assert len(receipt["execution_commitment"]) == 64


def test_detect_human_gate_finds_hcaptcha_without_solving_it() -> None:
    gate = detect_human_gate(_captcha_observation())
    assert gate is not None
    assert gate["gate_kind"] == "CAPTCHA"
    assert "HCAPTCHA" in gate["providers"]
    assert gate["policy"] == "HUMAN_HANDOFF_REQUIRED"
    assert gate["automated_solution_attempted"] is False


def test_handoff_binds_exact_preview_gate_and_origin() -> None:
    preview = prepare_action(_request())
    gate = detect_human_gate(_captcha_observation())
    assert gate is not None

    handoff = prepare_human_handoff(
        preview,
        gate,
        resolved_url="https://example.com/complaints",
    )
    assert handoff["status"] == "USER_ACTION_REQUIRED"
    assert handoff["preview_commitment"] == preview["preview_commitment"]
    assert handoff["target_origin"] == "https://example.com"
    assert handoff["automated_gate_solution_allowed"] is False
    assert len(handoff["handoff_commitment"]) == 64


def test_resume_requires_human_completion_and_same_origin() -> None:
    preview = prepare_action(_request())
    gate = detect_human_gate(_captcha_observation())
    assert gate is not None
    handoff = prepare_human_handoff(
        preview,
        gate,
        resolved_url="https://example.com/complaints",
    )

    with pytest.raises(FerretHandoffError, match="human completion"):
        complete_human_handoff(
            handoff,
            actor="USER007",
            completed=False,
            resolved_url="https://example.com/complaints",
            storage_state_sha256="a" * 64,
        )

    with pytest.raises(FerretHandoffError, match="origin"):
        complete_human_handoff(
            handoff,
            actor="USER007",
            completed=True,
            resolved_url="https://other.example/complaints",
            storage_state_sha256="a" * 64,
        )


def test_resume_receipt_binds_private_browser_state_by_hash_only() -> None:
    preview = prepare_action(_request())
    gate = detect_human_gate(_captcha_observation())
    assert gate is not None
    handoff = prepare_human_handoff(
        preview,
        gate,
        resolved_url="https://example.com/complaints",
    )
    resume = complete_human_handoff(
        handoff,
        actor="USER007",
        completed=True,
        resolved_url="https://example.com/complaints?challenge=complete",
        storage_state_sha256="b" * 64,
    )

    verify_handoff_resume(handoff, resume)
    assert resume["status"] == "READY_TO_RESUME"
    assert resume["storage_state_sha256"] == "b" * 64
    assert "cookies" not in resume
    assert len(resume["resume_commitment"]) == 64

    tampered = copy.deepcopy(resume)
    tampered["storage_state_sha256"] = "c" * 64
    with pytest.raises(FerretHandoffError):
        verify_handoff_resume(handoff, tampered)
