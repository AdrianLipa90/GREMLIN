from __future__ import annotations

import hashlib
import json

import pytest

from gremlin_mcp.constitutional_runtime import (
    RuntimeConstitutionalError,
    build_runtime_action_binding,
    build_runtime_constitutional_packet,
    require_constitutional_admission,
)
from gremlin_mcp.ferret import (
    FerretExecutionError,
    FerretExecutionResult,
    InMemoryFerretExecutionLedger,
    authorize_action,
    execute_authorized_action,
    prepare_action,
)
from gremlin_mcp.mathematical_constitution import (
    ETHICS_GATES,
    PASS,
    UNRESOLVED,
    build_gate_receipt,
    evaluate_admission,
)
from gremlin_mcp.memory_capabilities import evaluate_access, issue_capability_token
from gremlin_mcp.raphael import (
    ACCEPT,
    InMemoryMutationLedger,
    authorize,
    execute,
    judge,
    observe,
)


GENERATION = "robustness-generation-001"


def _gates(prefix: str) -> list[dict]:
    return [
        build_gate_receipt(
            gate=gate,
            status=PASS,
            relation_ids=(f"{prefix}:relation",),
            subject_refs=(f"{prefix}:subject",),
            source_classification="TEST_FIXTURE",
            source_ref=f"{prefix}:{gate.lower()}",
            evidence_refs=(f"{prefix}:evidence:{gate.lower()}",),
            reason="adversarial robustness fixture",
        )
        for gate in ETHICS_GATES
    ]


def _runtime_packet(
    *,
    endpoint: str,
    consequence_class: str,
    payload: dict,
    capability: int = PASS,
    authority: int = PASS,
    evidence: int = PASS,
) -> dict:
    binding = build_runtime_action_binding(
        endpoint=endpoint,
        consequence_class=consequence_class,
        request_payload=payload,
    )
    admission = evaluate_admission(
        action=binding["action_contract"],
        gate_receipts=_gates("robustness:runtime"),
        capability_status=capability,
        authority_status=authority,
        evidence_status=evidence,
    )
    return build_runtime_constitutional_packet(
        action_binding=binding,
        admission_receipt=admission,
    )


def _ferret_request() -> dict:
    return {
        "target_url": "https://example.com/submit",
        "intent": "robustness fixture",
        "steps": [
            {"action": "navigate", "url": "https://example.com/submit"},
            {"action": "click", "selector": "button[type=submit]"},
        ],
    }


def _ferret_packet(preview: dict, authorization: dict, *, authority: int = PASS) -> dict:
    payload = {
        "preview_id": preview["preview_id"],
        "preview_commitment": preview["preview_commitment"],
        "authorization_id": authorization["authorization_id"],
        "authorization_commitment": authorization["authorization_commitment"],
        "actor": authorization["actor"],
        "target_url": preview["target_url"],
    }
    return _runtime_packet(
        endpoint="ferret.execute_authorized_action",
        consequence_class="MUTATION",
        payload=payload,
        authority=authority,
    )


def _h(value: str) -> str:
    return hashlib.blake2b(value.encode("utf-8"), digest_size=32).hexdigest()


def _attestation(generation: str = GENERATION) -> dict:
    return {
        "schema": "GREMLIN_TRIPLE_PULSE_ATTESTATION_V0_1",
        "generation": generation,
        "identity_receipt": {"generation": generation, "status": "VERIFIED"},
        "domain_receipt": {"generation": generation, "status": "VERIFIED"},
        "authority_receipt": {"generation": generation, "status": "VERIFIED"},
    }


def _raphael_decree() -> dict:
    evidence = [
        {"producer": producer, "status": "PASS", "receipt_commitment": _h(producer)}
        for producer in ("GREMLIN", "OWL", "HOUND")
    ]
    observation = observe(
        objective="adversarial robustness exact-scope fixture",
        target_repository="AdrianLipa90/GREMLIN",
        target_branch="test/adversarial-robustness-v01-20260920",
        target_sha="a" * 40,
        operations=[
            {
                "operation": "UPDATE_FILE",
                "path": "gremlin_mcp/core.py",
                "expected_blob_sha": "b" * 40,
                "content": "updated",
            }
        ],
        evidence_receipts=evidence,
    )
    return judge(
        observation,
        decision=ACCEPT,
        rationale_codes=["EVIDENCE_CLOSED", "EXACT_SCOPE_BOUND"],
        required_tests=["pytest:robustness"],
        postconditions=["authority.canon_allowed=false"],
    )["decree"]


def _raphael_authorization(decree: dict, actor: str) -> dict:
    return authorize(
        decree,
        actor=actor,
        approved=True,
        observed_target_sha="a" * 40,
        gate_receipt=f"operator-gate-{actor}",
        tether_status="ACTIVE",
        gremlin_attestation=_attestation(),
    )


def _raphael_packet(decree: dict, authorization: dict) -> dict:
    payload = {
        "decree_commitment": decree["decree_commitment"],
        "authorization_commitment": authorization["authorization_commitment"],
        "target_repository": decree["target_repository"],
        "target_branch": decree["target_branch"],
        "target_sha": decree["target_sha"],
        "scope_commitment": decree["scope_commitment"],
        "actor": authorization["actor"],
        "gate_receipt": authorization["gate_receipt"],
        "generation": authorization["generation"],
        "gremlin_attestation_commitment": authorization["gremlin_attestation_commitment"],
    }
    return _runtime_packet(
        endpoint="raphael.execute",
        consequence_class="MUTATION",
        payload=payload,
    )


class _Backend:
    def __init__(self) -> None:
        self.sha = "a" * 40
        self.applied: list[dict] = []

    def current_state(self) -> dict:
        return {"target_sha": self.sha}

    def prepare(self, decree: dict) -> dict:
        return {
            "status": "PREPARED",
            "target_sha": self.sha,
            "scope_commitment": decree["scope_commitment"],
            "reservation_id": "robustness-reservation",
            "rollback_state": {"target_sha": self.sha},
        }

    def apply_operation(self, operation: dict) -> dict:
        self.applied.append(dict(operation))
        self.sha = "c" * 40
        return {
            "operation_commitment": operation["operation_commitment"],
            "status": "APPLIED",
        }

    def rollback(self, rollback_state: dict, applied_results: list[dict]) -> dict:
        self.sha = rollback_state["target_sha"]
        return {"status": "ROLLED_BACK", "count": len(applied_results)}


def test_runtime_rejects_nonfinite_request_payload() -> None:
    with pytest.raises(RuntimeConstitutionalError, match="finite JSON"):
        build_runtime_action_binding(
            endpoint="gremlin_hive_place",
            consequence_class="APPEND_ONLY",
            request_payload={"priority": float("nan")},
        )


def test_runtime_rejects_boolean_expected_status() -> None:
    payload = {"subject_id": "robustness"}
    packet = _runtime_packet(
        endpoint="gremlin_hive_place",
        consequence_class="APPEND_ONLY",
        payload=payload,
    )
    with pytest.raises(RuntimeConstitutionalError, match="must be one of"):
        require_constitutional_admission(
            endpoint="gremlin_hive_place",
            consequence_class="APPEND_ONLY",
            request_payload=payload,
            constitutional_packet=packet,
            expected_authority_status=True,
        )


def test_memory_token_cannot_cross_principal_even_when_operation_matches() -> None:
    token = issue_capability_token(
        beast="RAVEN",
        layer="SEMANTIC",
        operation="READ_METADATA",
        artifact_type="MEMORY_INDEX",
        subject_scope="subject-a",
        generation_scope="gen-a",
        task_scope="task-a",
    )
    receipt = evaluate_access(
        beast="OWL",
        layer="SEMANTIC",
        operation="READ_METADATA",
        artifact_type="MEMORY_INDEX",
        subject_id="subject-a",
        generation_id="gen-a",
        task_id="task-a",
        token=token,
    )
    assert receipt["decision"] == "DENY"
    assert receipt["reason_code"] == "TOKEN_BEAST_MISMATCH"


def test_ferret_constitution_cannot_cross_authorization_on_same_preview() -> None:
    preview = prepare_action(_ferret_request())
    auth_a = authorize_action(preview, actor="USER-A", approved=True)
    auth_b = authorize_action(preview, actor="USER-B", approved=True)
    packet_a = _ferret_packet(preview, auth_a)
    called = {"value": False}

    def executor(_preview: dict) -> FerretExecutionResult:
        called["value"] = True
        return FerretExecutionResult(
            status="SUBMITTED",
            resolved_url="https://example.com/confirmation",
            evidence={},
        )

    with pytest.raises(RuntimeConstitutionalError, match="exact runtime request"):
        execute_authorized_action(
            preview,
            auth_b,
            executor,
            ledger=InMemoryFerretExecutionLedger(),
            constitutional_packet=packet_a,
        )
    assert called["value"] is False


def test_ferret_authority_downgrade_fails_without_burning_authorization() -> None:
    preview = prepare_action(_ferret_request())
    authorization = authorize_action(preview, actor="USER007", approved=True)
    ledger = InMemoryFerretExecutionLedger()
    called = {"count": 0}

    def executor(_preview: dict) -> FerretExecutionResult:
        called["count"] += 1
        return FerretExecutionResult(
            status="SUBMITTED",
            resolved_url="https://example.com/confirmation",
            evidence={"case": "robustness"},
        )

    with pytest.raises(RuntimeConstitutionalError):
        execute_authorized_action(
            preview,
            authorization,
            executor,
            ledger=ledger,
            constitutional_packet=_ferret_packet(
                preview,
                authorization,
                authority=UNRESOLVED,
            ),
        )
    assert called["count"] == 0

    receipt = execute_authorized_action(
        preview,
        authorization,
        executor,
        ledger=ledger,
        constitutional_packet=_ferret_packet(preview, authorization),
    )
    assert receipt["status"] == "SUBMITTED"
    assert called["count"] == 1


def test_ferret_execution_cannot_escape_approved_origin_via_redirect_result() -> None:
    preview = prepare_action(_ferret_request())
    authorization = authorize_action(preview, actor="USER007", approved=True)

    def executor(_preview: dict) -> FerretExecutionResult:
        return FerretExecutionResult(
            status="SUBMITTED",
            resolved_url="https://other.example/confirmation",
            evidence={"redirect": True},
        )

    with pytest.raises(FerretExecutionError, match="origin"):
        execute_authorized_action(
            preview,
            authorization,
            executor,
            ledger=InMemoryFerretExecutionLedger(),
            constitutional_packet=_ferret_packet(preview, authorization),
        )


def test_raphael_constitution_cannot_cross_authorization_and_does_not_burn_valid_one() -> None:
    decree = _raphael_decree()
    auth_a = _raphael_authorization(decree, "USER-A")
    auth_b = _raphael_authorization(decree, "USER-B")
    ledger = InMemoryMutationLedger()
    backend = _Backend()

    with pytest.raises(RuntimeConstitutionalError, match="exact runtime request"):
        execute(
            decree,
            auth_b,
            backend=backend,
            ledger=ledger,
            admission_probe=lambda: {
                "tether_status": "ACTIVE",
                "gremlin_attestation": _attestation(),
            },
            constitutional_packet=_raphael_packet(decree, auth_a),
            test_runner=lambda _: True,
            postcondition_checker=lambda _: True,
        )
    assert backend.applied == []

    receipt = execute(
        decree,
        auth_b,
        backend=backend,
        ledger=ledger,
        admission_probe=lambda: {
            "tether_status": "ACTIVE",
            "gremlin_attestation": _attestation(),
        },
        constitutional_packet=_raphael_packet(decree, auth_b),
        test_runner=lambda _: True,
        postcondition_checker=lambda _: True,
    )
    assert receipt["status"] == "PASS"
    assert len(backend.applied) == 1
