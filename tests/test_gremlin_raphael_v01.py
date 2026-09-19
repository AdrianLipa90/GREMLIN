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


GENERATION = "raphael-test-generation-001"


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


def _attestation(
    generation: str = GENERATION,
    *,
    identity_generation: str | None = None,
    domain_generation: str | None = None,
    authority_generation: str | None = None,
    authority_status: str = "VERIFIED",
) -> dict:
    return {
        "schema": "GREMLIN_TRIPLE_PULSE_ATTESTATION_V0_1",
        "generation": generation,
        "identity_receipt": {
            "generation": identity_generation or generation,
            "status": "VERIFIED",
        },
        "domain_receipt": {
            "generation": domain_generation or generation,
            "status": "VERIFIED",
        },
        "authority_receipt": {
            "generation": authority_generation or generation,
            "status": authority_status,
        },
    }


def _admission_probe(
    generation: str = GENERATION,
    *,
    tether_status: str = "ACTIVE",
):
    return lambda: {
        "tether_status": tether_status,
        "gremlin_attestation": _attestation(generation),
    }


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


def _authorization(decree, *, actor: str = "USER007", observed_target_sha: str = "a" * 40):
    return authorize(
        decree,
        actor=actor,
        approved=True,
        observed_target_sha=observed_target_sha,
        gate_receipt="operator-gate-receipt-001",
        tether_status="ACTIVE",
        gremlin_attestation=_attestation(),
    )


class FakeBackend:
    def __init__(self):
        self.sha = "a" * 40
        self.applied = []
        self.rolled_back = False
        self.bad_receipt = False
        self.nonfinite_receipt = False
        self.bad_reservation_scope = False

    def current_state(self):
        return {"target_sha": self.sha}

    def prepare(self, decree):
        return {
            "status": "PREPARED",
            "target_sha": self.sha,
            "scope_commitment": (
                "0" * 64
                if self.bad_reservation_scope
                else decree["scope_commitment"]
            ),
            "reservation_id": "reservation-001",
            "rollback_state": {"target_sha": self.sha},
        }

    def apply_operation(self, operation):
        self.applied.append(dict(operation))
        self.sha = "c" * 40
        return {
            "operation_commitment": (
                "0" * 64 if self.bad_receipt else operation["operation_commitment"]
            ),
            "status": "APPLIED",
            **({"diagnostic": float("nan")} if self.nonfinite_receipt else {}),
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


def test_operation_schema_is_exact_and_update_requires_blob_binding():
    with pytest.raises(ValueError, match="exact field mismatch"):
        observe(
            objective="reject silent operation fields",
            target_repository="AdrianLipa90/GREMLIN",
            target_branch="feat/test",
            target_sha="a" * 40,
            operations=[{
                "operation": "CREATE_FILE",
                "path": "x.txt",
                "content": "x",
                "force": True,
            }],
            evidence_receipts=_evidence(),
        )

    with pytest.raises(ValueError, match="exact field mismatch"):
        observe(
            objective="require exact update source",
            target_repository="AdrianLipa90/GREMLIN",
            target_branch="feat/test",
            target_sha="a" * 40,
            operations=[{
                "operation": "UPDATE_FILE",
                "path": "x.txt",
                "content": "x",
            }],
            evidence_receipts=_evidence(),
        )


def test_accept_requires_real_post_audit_gates():
    observation = _observation()
    with pytest.raises(RaphaelWisdomError, match="at least one decree-bound test"):
        judge(
            observation,
            decision=ACCEPT,
            rationale_codes=["EVIDENCE_CLOSED"],
            postconditions=["authority.canon_allowed=false"],
        )
    with pytest.raises(
        RaphaelWisdomError, match="at least one decree-bound postcondition"
    ):
        judge(
            observation,
            decision=ACCEPT,
            rationale_codes=["EVIDENCE_CLOSED"],
            required_tests=["pytest:raphael"],
        )


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


def test_authorization_binds_target_active_tether_and_same_generation_triple_pulse():
    decree = _decree()
    auth = _authorization(decree)
    assert auth["authority"]["mutation_authorized"] is True
    assert auth["authority"]["canon_allowed"] is False
    assert auth["scope_commitment"] == decree["scope_commitment"]
    assert auth["tether_status"] == "ACTIVE"
    assert auth["generation"] == GENERATION
    assert len(auth["gremlin_attestation_commitment"]) == 64

    with pytest.raises(RaphaelAuthorizationError, match="STATE_DRIFT"):
        _authorization(decree, observed_target_sha="f" * 40)

    with pytest.raises(RaphaelAuthorizationError, match="tether_status must be ACTIVE"):
        authorize(
            decree,
            actor="USER007",
            approved=True,
            observed_target_sha="a" * 40,
            gate_receipt="operator-gate-receipt-001",
            tether_status="INACTIVE",
            gremlin_attestation=_attestation(),
        )

    with pytest.raises(RaphaelAuthorizationError, match="generation mismatch"):
        authorize(
            decree,
            actor="USER007",
            approved=True,
            observed_target_sha="a" * 40,
            gate_receipt="operator-gate-receipt-001",
            tether_status="ACTIVE",
            gremlin_attestation=_attestation(authority_generation="other-generation"),
        )


def test_hand_executes_exact_scope_then_expires_mutation_authority():
    decree = _decree()
    auth = _authorization(decree)
    backend = FakeBackend()
    receipt = execute(
        decree,
        auth,
        backend=backend,
        ledger=InMemoryMutationLedger(),
        admission_probe=_admission_probe(),
        test_runner=lambda name: name == "pytest:raphael",
        postcondition_checker=lambda condition: condition
        == "authority.canon_allowed=false",
    )
    assert receipt["status"] == "PASS"
    assert receipt["before_target_sha"] == "a" * 40
    assert receipt["after_target_sha"] == "c" * 40
    assert len(receipt["reservation_commitment"]) == 64
    assert receipt["mutation_authority_expired"] is True
    assert receipt["authority"]["mutation_authorized"] is False
    assert receipt["authority"]["canon_allowed"] is False
    assert backend.rolled_back is False


def test_live_admission_generation_drift_aborts_and_burns_authorization():
    decree = _decree()
    auth = _authorization(decree)
    backend = FakeBackend()
    ledger = InMemoryMutationLedger()
    with pytest.raises(RaphaelExecutionError, match="LIVE_ADMISSION_FAILED") as caught:
        execute(
            decree,
            auth,
            backend=backend,
            ledger=ledger,
            admission_probe=_admission_probe("other-generation"),
            test_runner=lambda _: True,
            postcondition_checker=lambda _: True,
        )
    assert caught.value.receipt["status"] == "ABORTED"
    assert caught.value.receipt["failure_code"] == "LIVE_ADMISSION_FAILED"
    assert caught.value.receipt["mutation_started"] is False

    with pytest.raises(RaphaelAuthorizationError, match="already consumed"):
        execute(
            decree,
            auth,
            backend=backend,
            ledger=ledger,
            admission_probe=_admission_probe(),
            test_runner=lambda _: True,
            postcondition_checker=lambda _: True,
        )


def test_state_drift_before_hand_is_fail_loud_and_burns_stale_authorization():
    decree = _decree()
    auth = _authorization(decree)
    backend = FakeBackend()
    backend.sha = "d" * 40
    ledger = InMemoryMutationLedger()
    with pytest.raises(RaphaelExecutionError, match="STATE_DRIFT") as caught:
        execute(
            decree,
            auth,
            backend=backend,
            ledger=ledger,
            admission_probe=_admission_probe(),
            test_runner=lambda _: True,
            postcondition_checker=lambda _: True,
        )
    assert caught.value.receipt["status"] == "ABORTED"
    assert caught.value.receipt["failure_code"] == "STATE_DRIFT"
    assert caught.value.receipt["mutation_started"] is False
    assert caught.value.receipt["mutation_authority_expired"] is True

    backend.sha = "a" * 40
    with pytest.raises(RaphaelAuthorizationError, match="already consumed"):
        execute(
            decree,
            auth,
            backend=backend,
            ledger=ledger,
            admission_probe=_admission_probe(),
            test_runner=lambda _: True,
            postcondition_checker=lambda _: True,
        )


def test_invalid_reservation_scope_quarantines_without_mutation():
    decree = _decree()
    auth = _authorization(decree)
    backend = FakeBackend()
    backend.bad_reservation_scope = True
    with pytest.raises(RaphaelExecutionError) as caught:
        execute(
            decree,
            auth,
            backend=backend,
            ledger=InMemoryMutationLedger(),
            admission_probe=_admission_probe(),
            test_runner=lambda _: True,
            postcondition_checker=lambda _: True,
        )
    assert caught.value.receipt["status"] == "QUARANTINED"
    assert caught.value.receipt["failure_code"] == "RESERVATION_RECEIPT_INVALID"
    assert caught.value.receipt["mutation_started"] is False
    assert backend.applied == []


def test_bad_operation_receipt_rolls_back():
    decree = _decree()
    auth = _authorization(decree)
    backend = FakeBackend()
    backend.bad_receipt = True
    with pytest.raises(RaphaelExecutionError) as caught:
        execute(
            decree,
            auth,
            backend=backend,
            ledger=InMemoryMutationLedger(),
            admission_probe=_admission_probe(),
            test_runner=lambda _: True,
            postcondition_checker=lambda _: True,
        )
    assert caught.value.receipt["failure_code"] == "OPERATION_RECEIPT_MISMATCH"
    assert caught.value.receipt["status"] == "ROLLED_BACK"
    assert backend.rolled_back is True


def test_nonfinite_backend_receipt_rolls_back_before_lineage_commit():
    decree = _decree()
    auth = _authorization(decree)
    backend = FakeBackend()
    backend.nonfinite_receipt = True
    with pytest.raises(RaphaelExecutionError) as caught:
        execute(
            decree,
            auth,
            backend=backend,
            ledger=InMemoryMutationLedger(),
            admission_probe=_admission_probe(),
            test_runner=lambda _: True,
            postcondition_checker=lambda _: True,
        )
    assert caught.value.receipt["failure_code"] == "MALFORMED_MUTATION_RESULT"
    assert caught.value.receipt["status"] == "ROLLED_BACK"
    assert backend.rolled_back is True


def test_failed_post_audit_rolls_back_and_emits_committed_failure_receipt():
    decree = _decree()
    auth = _authorization(decree)
    backend = FakeBackend()
    with pytest.raises(RaphaelExecutionError) as caught:
        execute(
            decree,
            auth,
            backend=backend,
            ledger=InMemoryMutationLedger(),
            admission_probe=_admission_probe(),
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
        _authorization(tampered)


def test_cancelled_decree_cannot_execute():
    decree = _decree()
    auth = _authorization(decree)
    ledger = InMemoryMutationLedger()
    cancellation = cancel_decree(decree, reason_codes=["NEW_EVIDENCE"], ledger=ledger)
    assert cancellation["status"] == "CANCELLED_BEFORE_MUTATION"
    with pytest.raises(RaphaelAuthorizationError, match="cancelled"):
        execute(
            decree,
            auth,
            backend=FakeBackend(),
            ledger=ledger,
            admission_probe=_admission_probe(),
            test_runner=lambda _: True,
            postcondition_checker=lambda _: True,
        )


def test_decree_and_authorization_are_single_use():
    decree = _decree()
    auth = _authorization(decree)
    ledger = InMemoryMutationLedger()
    first = execute(
        decree,
        auth,
        backend=FakeBackend(),
        ledger=ledger,
        admission_probe=_admission_probe(),
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
            admission_probe=_admission_probe(),
            test_runner=lambda _: True,
            postcondition_checker=lambda _: True,
        )


def test_target_sha_accepts_only_exact_sha1_or_sha256_lengths():
    with pytest.raises(ValueError, match="exactly 40 or 64"):
        observe(
            objective="reject malformed state digest",
            target_repository="AdrianLipa90/GREMLIN",
            target_branch="feat/test",
            target_sha="a" * 41,
            operations=[{"operation": "CREATE_FILE", "path": "x.txt", "content": "x"}],
            evidence_receipts=_evidence(),
        )


def test_required_wisdom_quorum_cannot_be_weakened_by_caller():
    with pytest.raises(
        RaphaelWisdomError, match="cannot remove mandatory wisdom producers"
    ):
        observe(
            objective="attempt quorum downgrade",
            target_repository="AdrianLipa90/GREMLIN",
            target_branch="feat/test",
            target_sha="a" * 40,
            operations=[{"operation": "CREATE_FILE", "path": "x.txt", "content": "x"}],
            evidence_receipts=[],
            required_producers=[],
        )


def test_string_fail_is_not_truthy_test_pass():
    decree = _decree()
    auth = _authorization(decree)
    backend = FakeBackend()
    with pytest.raises(RaphaelExecutionError) as caught:
        execute(
            decree,
            auth,
            backend=backend,
            ledger=InMemoryMutationLedger(),
            admission_probe=_admission_probe(),
            test_runner=lambda _: "FAIL",
            postcondition_checker=lambda _: True,
        )
    assert caught.value.receipt["failure_code"] == "MALFORMED_TEST_RESULT"
    assert caught.value.receipt["status"] == "ROLLED_BACK"
    assert backend.rolled_back is True


def test_consumed_decree_cannot_be_cancelled_after_mutation():
    decree = _decree()
    auth = _authorization(decree)
    ledger = InMemoryMutationLedger()
    receipt = execute(
        decree,
        auth,
        backend=FakeBackend(),
        ledger=ledger,
        admission_probe=_admission_probe(),
        test_runner=lambda _: True,
        postcondition_checker=lambda _: True,
    )
    assert receipt["status"] == "PASS"
    with pytest.raises(RaphaelAuthorizationError, match="already consumed"):
        cancel_decree(decree, reason_codes=["TOO_LATE"], ledger=ledger)


def test_raphael_cannot_self_authorize():
    decree = _decree()
    with pytest.raises(RaphaelAuthorizationError, match="cannot self-authorize"):
        authorize(
            decree,
            actor="RAPHAEL",
            approved=True,
            observed_target_sha="a" * 40,
            gate_receipt="operator-gate-receipt-001",
            tether_status="ACTIVE",
            gremlin_attestation=_attestation(),
        )
