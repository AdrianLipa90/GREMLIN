from __future__ import annotations

import copy

import pytest

from gremlin_mcp.constitutional_runtime import (
    RuntimeConstitutionalError,
    build_runtime_action_binding,
    build_runtime_constitutional_packet,
)
from gremlin_mcp.mathematical_constitution import (
    ETHICS_GATES,
    PASS,
    build_gate_receipt,
    evaluate_admission,
)
from gremlin_mcp.ferret import (
    FerretAuthorizationError,
    FerretExecutionResult,
    FerretHandoffError,
    InMemoryFerretExecutionLedger,
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


def _constitutional_packet(preview: dict, authorization: dict) -> dict:
    payload = {
        "preview_id": preview["preview_id"],
        "preview_commitment": preview["preview_commitment"],
        "authorization_id": authorization["authorization_id"],
        "authorization_commitment": authorization["authorization_commitment"],
        "actor": authorization["actor"],
        "target_url": preview["target_url"],
    }
    binding = build_runtime_action_binding(
        endpoint="ferret.execute_authorized_action",
        consequence_class="MUTATION",
        request_payload=payload,
    )
    gates = [
        build_gate_receipt(
            gate=gate,
            status=PASS,
            relation_ids=("ferret:test:relation",),
            subject_refs=("ferret:test:subject",),
            source_classification="TEST_FIXTURE",
            source_ref=f"ferret:test:{gate.lower()}",
            evidence_refs=(f"ferret:test:evidence:{gate.lower()}",),
            reason="FERRET constitutional test fixture",
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

    receipt = execute_authorized_action(
        preview,
        authorization,
        executor,
        ledger=InMemoryFerretExecutionLedger(),
        constitutional_packet=_constitutional_packet(preview, authorization),
    )
    assert receipt["status"] == "SUBMITTED"
    assert receipt["preview_commitment"] == preview["preview_commitment"]
    assert receipt["authorization_commitment"] == authorization["authorization_commitment"]
    assert receipt["authorization_consumed"] is True
    assert receipt["single_use"] is True
    assert receipt["approved_origin"] == "https://example.com"
    assert receipt["resolved_origin"] == "https://example.com"
    assert receipt["origin_confined"] is True
    assert receipt["evidence"]["case_id"] == "CASE-123"
    assert len(receipt["execution_commitment"]) == 64


def test_cross_origin_execution_result_fails_closed_and_burns_authorization() -> None:
    preview = prepare_action(_request())
    authorization = authorize_action(preview, actor="USER007", approved=True)
    ledger = InMemoryFerretExecutionLedger()

    def escaped_executor(_preview):
        return FerretExecutionResult(
            status="SUBMITTED",
            resolved_url="https://other.example/confirmation",
            evidence={"redirect": True},
        )

    with pytest.raises(FerretExecutionError, match="approved origin"):
        execute_authorized_action(
            preview,
            authorization,
            escaped_executor,
            ledger=ledger,
            constitutional_packet=_constitutional_packet(preview, authorization),
        )

    def safe_executor(_preview):
        return FerretExecutionResult(
            status="SUBMITTED",
            resolved_url="https://example.com/confirmation",
            evidence={},
        )

    with pytest.raises(FerretAuthorizationError, match="already consumed"):
        execute_authorized_action(
            preview,
            authorization,
            safe_executor,
            ledger=ledger,
            constitutional_packet=_constitutional_packet(preview, authorization),
        )


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


def test_ferret_authorization_is_single_use() -> None:
    preview = prepare_action(_request())
    authorization = authorize_action(preview, actor="USER007", approved=True)
    assert authorization["single_use"] is True
    assert authorization["replay_protection"] == "FERRET_EXECUTION_LEDGER_REQUIRED"

    def executor(_preview):
        return FerretExecutionResult(
            status="SUBMITTED",
            resolved_url="https://example.com/complaints/confirmation",
            evidence={"case_id": "CASE-ONE"},
        )

    ledger = InMemoryFerretExecutionLedger()
    packet = _constitutional_packet(preview, authorization)
    first = execute_authorized_action(
        preview,
        authorization,
        executor,
        ledger=ledger,
        constitutional_packet=packet,
    )
    assert first["status"] == "SUBMITTED"

    with pytest.raises(FerretAuthorizationError, match="already consumed"):
        execute_authorized_action(
            preview,
            authorization,
            executor,
            ledger=ledger,
            constitutional_packet=packet,
        )


def test_ferret_missing_constitution_does_not_consume_authorization() -> None:
    preview = prepare_action(_request())
    authorization = authorize_action(preview, actor="USER007", approved=True)
    ledger = InMemoryFerretExecutionLedger()

    def executor(_preview):
        return FerretExecutionResult(
            status="SUBMITTED",
            resolved_url="https://example.com/complaints/confirmation",
            evidence={"case_id": "CASE-TWO"},
        )

    with pytest.raises(PermissionError, match="constitutional_packet"):
        execute_authorized_action(
            preview,
            authorization,
            executor,
            ledger=ledger,
        )

    receipt = execute_authorized_action(
        preview,
        authorization,
        executor,
        ledger=ledger,
        constitutional_packet=_constitutional_packet(preview, authorization),
    )
    assert receipt["status"] == "SUBMITTED"


def test_execution_without_constitutional_packet_fails_before_executor() -> None:
    preview = prepare_action(_request())
    authorization = authorize_action(preview, actor="USER007", approved=True)
    called = {"value": False}

    def executor(_preview):
        called["value"] = True
        return FerretExecutionResult(
            status="SHOULD_NOT_RUN",
            resolved_url="https://example.com/complaints",
            evidence={},
        )

    with pytest.raises(RuntimeConstitutionalError):
        execute_authorized_action(
            preview,
            authorization,
            executor,
            ledger=InMemoryFerretExecutionLedger(),
        )
    assert called["value"] is False


def test_constitutional_packet_cannot_be_replayed_on_another_preview() -> None:
    preview_a = prepare_action(_request())
    authorization_a = authorize_action(preview_a, actor="USER007", approved=True)
    packet_a = _constitutional_packet(preview_a, authorization_a)

    preview_b = prepare_action(_request())
    authorization_b = authorize_action(preview_b, actor="USER007", approved=True)

    def executor(_preview):
        return FerretExecutionResult(
            status="SHOULD_NOT_RUN",
            resolved_url="https://example.com/complaints",
            evidence={},
        )

    with pytest.raises(RuntimeConstitutionalError, match="exact runtime request"):
        execute_authorized_action(
            preview_b,
            authorization_b,
            executor,
            ledger=InMemoryFerretExecutionLedger(),
            constitutional_packet=packet_a,
        )


def test_ferret_rejects_rehashed_authorization_with_weakened_single_use_contract() -> None:
    preview = prepare_action(_request())
    authorization = authorize_action(preview, actor="USER007", approved=True)
    weakened = copy.deepcopy(authorization)
    weakened.pop("authorization_commitment")
    weakened["single_use"] = False
    weakened["replay_protection"] = "CALLER_LEDGER_REQUIRED"

    import hashlib
    import json

    raw = json.dumps(
        weakened,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    weakened["authorization_commitment"] = hashlib.blake2b(
        b"GREMLIN-FERRET-AUTHORIZATION/v0.1\0" + raw,
        digest_size=32,
    ).hexdigest()

    with pytest.raises(FerretAuthorizationError, match="single-use"):
        verify_authorization(preview, weakened)
