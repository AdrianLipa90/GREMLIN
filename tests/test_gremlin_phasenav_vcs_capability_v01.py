from __future__ import annotations

import pytest

from gremlin_mcp.phasenav_vcs_capability import (
    branch_prepare,
    bundle_prepare,
    checkpoint_prepare,
    commit_prepare,
    execution_receipt_build,
    tag_prepare,
    test_receipt_bind,
    validate_preflight,
    writes_prepare,
)

HEAD0 = "1" * 40
HEAD1 = "2" * 40


def _action_packet() -> dict:
    return {
        "schema": "PHASENAV_ACTION_PACKET_V1",
        "action_id": "test-action-001",
        "intent": "exercise bounded VCS preparation",
    }


def _attestation(generation: str = "gen-001") -> dict:
    return {
        "schema": "GREMLIN_TRIPLE_PULSE_ATTESTATION_V0_1",
        "generation": generation,
        "identity_receipt": {"generation": generation, "status": "VERIFIED"},
        "domain_receipt": {"generation": generation, "status": "VERIFIED"},
        "authority_receipt": {"generation": generation, "status": "VERIFIED"},
    }


def _preflight() -> dict:
    return validate_preflight(
        action_packet=_action_packet(),
        gate_receipt="gate-receipt-001",
        tether_status="ACTIVE",
        gremlin_attestation=_attestation(),
        shell_used=False,
        copy_only=True,
    )


def _chain() -> tuple[dict, dict, dict, dict, dict, dict, dict, dict]:
    preflight = _preflight()
    checkpoint = checkpoint_prepare(
        preflight=preflight,
        repository="AdrianLipa90/CIEL-NOEMA-HTRI-CIELingo-Phasenav",
        base_ref="main",
        expected_head=HEAD0,
    )
    branch = branch_prepare(
        checkpoint=checkpoint,
        branch_name="candidate/test-vcs-capability-v01",
    )
    writes = writes_prepare(
        branch=branch,
        writes=[
            {
                "operation": "create",
                "path": "candidate_surface/example.txt",
                "content": "bounded candidate write\n",
            }
        ],
        copy_only=True,
    )
    commit = commit_prepare(prepared_writes=writes, message="candidate: test bounded write")
    tag = tag_prepare(checkpoint=checkpoint, tag_name="checkpoint/test-vcs-capability-v01")
    bundle = bundle_prepare(checkpoint=checkpoint, tag=tag, branch=branch)
    test_binding = test_receipt_bind(
        logical_step="bounded-vcs-test",
        evidence={"status": "PASS", "suite": "unit-fixture"},
    )
    return preflight, checkpoint, branch, writes, commit, tag, bundle, test_binding


def test_preflight_requires_active_tether() -> None:
    with pytest.raises(ValueError, match="tether_status must be ACTIVE"):
        validate_preflight(
            action_packet=_action_packet(),
            gate_receipt="gate-receipt-001",
            tether_status="INACTIVE",
            gremlin_attestation=_attestation(),
            shell_used=False,
            copy_only=True,
        )


def test_preflight_rejects_generation_mismatch() -> None:
    attestation = _attestation()
    attestation["authority_receipt"] = {"generation": "other", "status": "VERIFIED"}
    with pytest.raises(ValueError, match="generation mismatch"):
        validate_preflight(
            action_packet=_action_packet(),
            gate_receipt="gate-receipt-001",
            tether_status="ACTIVE",
            gremlin_attestation=attestation,
            shell_used=False,
            copy_only=True,
        )


def test_preflight_rejects_shell_and_non_copy_only() -> None:
    with pytest.raises(ValueError, match="shell_used must be false"):
        validate_preflight(
            action_packet=_action_packet(),
            gate_receipt="gate-receipt-001",
            tether_status="ACTIVE",
            gremlin_attestation=_attestation(),
            shell_used=True,
            copy_only=True,
        )
    with pytest.raises(ValueError, match="copy_only must be true"):
        validate_preflight(
            action_packet=_action_packet(),
            gate_receipt="gate-receipt-001",
            tether_status="ACTIVE",
            gremlin_attestation=_attestation(),
            shell_used=False,
            copy_only=False,
        )


def test_branch_prepare_rejects_main() -> None:
    checkpoint = checkpoint_prepare(
        preflight=_preflight(),
        repository="AdrianLipa90/example",
        base_ref="main",
        expected_head=HEAD0,
    )
    with pytest.raises(ValueError, match="main/master"):
        branch_prepare(checkpoint=checkpoint, branch_name="main")


def test_writes_prepare_is_create_only() -> None:
    checkpoint = checkpoint_prepare(
        preflight=_preflight(),
        repository="AdrianLipa90/example",
        base_ref="main",
        expected_head=HEAD0,
    )
    branch = branch_prepare(checkpoint=checkpoint, branch_name="candidate/example")
    with pytest.raises(ValueError, match="create operations only"):
        writes_prepare(
            branch=branch,
            writes=[{"operation": "delete", "path": "x", "content": ""}],
        )


def test_execution_receipt_requires_native_adapter_success_evidence() -> None:
    preflight, checkpoint, branch, writes, commit, tag, bundle, test_binding = _chain()
    with pytest.raises(ValueError, match="successful native execution"):
        execution_receipt_build(
            preflight=preflight,
            checkpoint=checkpoint,
            branch=branch,
            prepared_writes=writes,
            prepared_commit=commit,
            tag=tag,
            bundle=bundle,
            test_binding=test_binding,
            adapter_evidence={"status": "PENDING", "shell_used": False},
            before_head=HEAD0,
            after_head=HEAD1,
        )


def test_happy_path_builds_fail_closed_execution_receipt() -> None:
    preflight, checkpoint, branch, writes, commit, tag, bundle, test_binding = _chain()
    receipt = execution_receipt_build(
        preflight=preflight,
        checkpoint=checkpoint,
        branch=branch,
        prepared_writes=writes,
        prepared_commit=commit,
        tag=tag,
        bundle=bundle,
        test_binding=test_binding,
        adapter_evidence={
            "status": "VERIFIED",
            "shell_used": False,
            "adapter": "TEST_NATIVE_ADAPTER",
            "checkpoint_created": True,
            "tag_created": True,
            "bundle_created": True,
        },
        before_head=HEAD0,
        after_head=HEAD1,
    )
    assert receipt["schema"] == "PHASENAV_EXECUTION_RECEIPT_V1"
    assert receipt["status"] == "EXECUTED_NATIVE_ADAPTER_VERIFIED"
    assert receipt["shell_used"] is False
    assert receipt["canon_allowed"] is False
    assert receipt["production_runtime_write"] is False
    assert len(receipt["receipt_commitment"]) == 64
