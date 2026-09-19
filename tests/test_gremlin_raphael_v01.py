from __future__ import annotations

import copy
import hashlib

import pytest

from gremlin_mcp.raphael import (
    ACCEPT,
    DEFER,
    InMemoryMutationLedger,
    RaphaelAuthorizationError,
    RaphaelExecutionError,
    RaphaelWisdomError,
    angelic_manifest,
    authorize,
    cancel_decree,
    execute,
    judge,
    observe,
)


def _h(value: str) -> str:
    return hashlib.blake2b(value.encode("utf-8"), digest_size=32).hexdigest()


def _evidence(statuses=None):
    statuses = statuses or {"GREMLIN": "PASS", "OWL": "PASS", "HOUND": "PASS"}
    return [
        {
            "producer": producer,
            "status": status,
            "receipt_commitment": _h(producer),
        }
        for producer, status in statuses.items()
    ]


def _observation():
    return observe(
        objective="Bind RAPHAEL v0.1 without widening canon authority",
        target_repository="AdrianLipa90/GREMLIN",
        target_branch="feat/raphael-wisdom-mutation-v01",
        target_sha="a" * 40,
        operations=[
            {
                "operation": "UPDATE_FILE",
                "path": "gremlin_mcp/core.py",
                "expected_blob_sha": "b" * 40,
                "content": "updated",
            }
        ],
        evidence_receipts=_evidence(),
    )


def _decree():
    observation = _observation()
    decision = judge(
        observation,
        decision=ACCEPT,
        rationale_codes=["EVIDENCE_CLOSED", "EXACT_SCOPE_BOUND"],
        required_tests=["pytest:raphael"],
        postconditions=["authority.canon_allowed=false"],
    )
    return decision["decree"]


class FakeBackend:
    def __init__(self):
        self.sha = "a" * 40
        self.applied = []
        self.rolled_back = False
        self.bad_receipt = False

    def current_state(self):
        return {"target_sha": self.sha}

    def prepare(self, decree):
        return {"target_sha": self.sha, "operation_count": len(decree["operations"])}

    def apply_operation(self, operation):
        self.applied.append(dict(operation))
        self.sha = "c" * 40
        return {
            "operation_commitment": (
                "0" * 64 if self.bad_receipt else operation["operation_commitment"]
            ),
            "status": "APPLIED",
        }

    def rollback(self, rollback_state, applied_results):
        self.rolled_back = True
        self.sha = rollback_state["target_sha"]
        return {"status": "ROLLED_BACK", "count": len(applied_results)}


def test_raphael_is_angelic_function_not_bestiary_species():
    manifest = angelic_manifest()
    assert manifest["name"] == "RAPHAEL"
    assert manifest["title"] == "Lord of Wisdom"
    assert manifest["class"] == "ANGELIC_FUNCTION"
    assert manifest["bestiary_species"] is False
    assert manifest["epistemic"] == "CHYBA"
    assert manifest["authority"] == {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "mutation_authorized": False,
    }


def test_eye_binds_exact_target_scope_and_required_wisdom_receipts():
    observation = _observation()
    assert observation["phase"] == "EYE"
    assert observation["evidence_ready"] is True
    assert observation["allowed_paths"] == ["gremlin_mcp/core.py"]
    assert len(observation["scope_commitment"]) == 64
    assert len(observation["observation_commitment"]) == 64


def test_unknown_or_blocking_evidence_fails_closed():
    observation = observe(
        objective="test",
        target_repository="AdrianLipa90/GREMLIN",
        target_branch="x",
        target_sha="a" * 40,
        operations=[{"operation": "CREATE_FILE", "path": "x.txt", "content": "x"}],
        evidence_receipts=_evidence(
            {"GREMLIN": "PASS", "OWL": "PASS", "HOUND": "UNRESOLVED"}
        ),
    )
    assert observation["evidence_ready"] is False
    assert "HOUND:UNRESOLVED" in observation["blocking_evidence"]
    with pytest.raises(RaphaelWisdomError, match="ACCEPT is forbidden"):
        judge(observation, decision=ACCEPT, rationale_codes=["SHOULD_NOT_PASS"])

    deferred = judge(
        observation,
        decision=DEFER,
        rationale_codes=["HOUND_UNRESOLVED"],
    )
    assert deferred["decision"] == "DEFER"
    assert "decree" not in deferred


def test_decree_is_commitment_bound_and_keeps_global_authority_closed():
    decree = _decree()
    assert decree["scope_immutable_after_first_write"] is True
    assert decree["requires_external_authorization"] is True
    assert decree["single_use"] is True
    assert decree["authority"]["mutation_authorized"] is False
    assert decree["authority"]["canon_allowed"] is False


def test_authorization_binds_exact_decree_and_exact_target_state():
    decree = _decree()
    auth = authorize(
        decree,
        actor="USER007",
        approved=True,
        observed_target_sha="a" * 40,
    )
    assert auth["authority"]["mutation_authorized"] is True
    assert auth["authority"]["canon_allowed"] is False
    assert auth["scope_commitment"] == decree["scope_commitment"]

    with pytest.raises(RaphaelAuthorizationError, match="STATE_DRIFT"):
        authorize(
            decree,
            actor="USER007",
            approved=True,
            observed_target_sha="f" * 40,
        )


def test_hand_executes_exact_scope_then_expires_mutation_authority():
    decree = _decree()
    auth = authorize(decree, actor="USER007", approved=True, observed_target_sha="a" * 40)
    backend = FakeBackend()
    receipt = execute(
        decree,
        auth,
        backend=backend,
        ledger=InMemoryMutationLedger(),
        test_runner=lambda name: name == "pytest:raphael",
        postcondition_checker=lambda condition: condition == "authority.canon_allowed=false",
    )
    assert receipt["status"] == "PASS"
    assert receipt["before_target_sha"] == "a" * 40
    assert receipt["after_target_sha"] == "c" * 40
    assert receipt["mutation_authority_expired"] is True
    assert receipt["authority"]["mutation_authorized"] is False
    assert receipt["authority"]["canon_allowed"] is False
    assert backend.rolled_back is False


def test_state_drift_before_hand_is_fail_loud():
    decree = _decree()
    auth = authorize(decree, actor="USER007", approved=True, observed_target_sha="a" * 40)
    backend = FakeBackend()
    backend.sha = "d" * 40
    with pytest.raises(RaphaelExecutionError, match="STATE_DRIFT"):
        execute(
            decree,
            auth,
            backend=backend,
            ledger=InMemoryMutationLedger(),
            test_runner=lambda _: True,
            postcondition_checker=lambda _: True,
        )


def test_bad_operation_receipt_rolls_back():
    decree = _decree()
    auth = authorize(decree, actor="USER007", approved=True, observed_target_sha="a" * 40)
    backend = FakeBackend()
    backend.bad_receipt = True
    with pytest.raises(RaphaelExecutionError) as caught:
        execute(
            decree,
            auth,
            backend=backend,
            ledger=InMemoryMutationLedger(),
            test_runner=lambda _: True,
            postcondition_checker=lambda _: True,
        )
    assert caught.value.receipt["failure_code"] == "OPERATION_RECEIPT_MISMATCH"
    assert caught.value.receipt["status"] == "ROLLED_BACK"
    assert backend.rolled_back is True


def test_failed_post_audit_rolls_back_and_emits_committed_failure_receipt():
    decree = _decree()
    auth = authorize(decree, actor="USER007", approved=True, observed_target_sha="a" * 40)
    backend = FakeBackend()
    with pytest.raises(RaphaelExecutionError) as caught:
        execute(
            decree,
            auth,
            backend=backend,
            ledger=InMemoryMutationLedger(),
            test_runner=lambda _: False,
            postcondition_checker=lambda _: True,
        )
    receipt = caught.value.receipt
    assert receipt["status"] == "ROLLED_BACK"
    assert receipt["failure_code"] == "TEST_FAILURE"
    assert receipt["rollback"]["status"] == "ROLLED_BACK"
    assert receipt["mutation_authority_expired"] is True
    assert len(receipt["receipt_commitment"]) == 64
    assert backend.rolled_back is True


def test_tampered_decree_is_rejected_before_mutation():
    decree = _decree()
    tampered = copy.deepcopy(decree)
    tampered["allowed_paths"].append("undeclared.py")
    with pytest.raises(ValueError, match="decree_commitment mismatch"):
        authorize(
            tampered,
            actor="USER007",
            approved=True,
            observed_target_sha="a" * 40,
        )


def test_cancelled_decree_cannot_execute():
    decree = _decree()
    auth = authorize(decree, actor="USER007", approved=True, observed_target_sha="a" * 40)
    ledger = InMemoryMutationLedger()
    cancellation = cancel_decree(decree, reason_codes=["NEW_EVIDENCE"], ledger=ledger)
    assert cancellation["status"] == "CANCELLED_BEFORE_MUTATION"
    with pytest.raises(RaphaelAuthorizationError, match="cancelled"):
        execute(
            decree,
            auth,
            backend=FakeBackend(),
            ledger=ledger,
            test_runner=lambda _: True,
            postcondition_checker=lambda _: True,
        )


def test_decree_and_authorization_are_single_use():
    decree = _decree()
    auth = authorize(decree, actor="USER007", approved=True, observed_target_sha="a" * 40)
    ledger = InMemoryMutationLedger()
    first = execute(
        decree,
        auth,
        backend=FakeBackend(),
        ledger=ledger,
        test_runner=lambda _: True,
        postcondition_checker=lambda _: True,
    )
    assert first["status"] == "PASS"
    with pytest.raises(RaphaelAuthorizationError, match="already consumed"):
        execute(
            decree,
            auth,
            backend=FakeBackend(),
            ledger=ledger,
            test_runner=lambda _: True,
            postcondition_checker=lambda _: True,
        )
