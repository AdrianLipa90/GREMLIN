from __future__ import annotations

import copy

import pytest

from gremlin_mcp.ferret import (
    FerretAuthorizationError,
    FerretExecutionResult,
    authorize_action,
    execute_authorized_action,
    prepare_action,
    verify_authorization,
)


def _request() -> dict:
    return {
        "target_url": "https://example.com/complaints",
        "intent": "Submit a consumer complaint with evidence",
        "steps": [
            {"action": "navigate", "url": "https://example.com/complaints"},
            {"action": "fill", "selector": "#subject", "value": "Incorrect plan"},
            {"action": "fill", "selector": "#password", "value": "secret-value", "secret": True},
            {"action": "upload", "selector": "input[type=file]", "files": ["/tmp/evidence.png"]},
            {"action": "click", "selector": "button[type=submit]"},
            {"action": "snapshot", "label": "confirmation"},
        ],
    }


def test_prepare_is_receipt_bound_and_redacts_secret() -> None:
    preview = prepare_action(_request())
    assert preview["requires_explicit_approval"] is True
    assert preview["approval_scope"] == "EXACT_PREVIEW_COMMITMENT"
    assert preview["steps"][2]["value"] == "<REDACTED>"
    assert preview["steps"][2]["secret"] is True
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
