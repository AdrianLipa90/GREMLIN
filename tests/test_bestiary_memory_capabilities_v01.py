from __future__ import annotations

import copy

import pytest

from gremlin_mcp.memory_capabilities import (
    DESTRUCTIVE_OPERATIONS,
    PRIVATE_LAYER,
    POLICY,
    authorize_memory_requests,
    beast_capabilities,
    evaluate_access,
    issue_capability_token,
    policy_manifest,
    validate_access_receipt,
    validate_capability_token,
)


def _token(
    *,
    beast: str,
    layer: str,
    operation: str,
    artifact_type: str,
    subject_scope: str = "spectroscopy:ring-6",
    generation_scope: str = "gen-001",
    task_scope: str = "task-001",
):
    return issue_capability_token(
        beast=beast,
        layer=layer,
        operation=operation,
        artifact_type=artifact_type,
        subject_scope=subject_scope,
        generation_scope=generation_scope,
        task_scope=task_scope,
    )


def _decision(token: dict, **overrides):
    kwargs = {
        "beast": token["beast"],
        "layer": token["layer"],
        "operation": token["operation"],
        "artifact_type": token["artifact_type"],
        "subject_id": "spectroscopy:ring-6",
        "generation_id": "gen-001",
        "task_id": "task-001",
        "token": token,
    }
    kwargs.update(overrides)
    return evaluate_access(**kwargs)


def test_policy_is_deny_by_default_and_has_all_bestiary_principals() -> None:
    manifest = policy_manifest()
    assert manifest["default"] == "DENY"
    assert set(POLICY) == {
        "HUMMINGBIRD", "OCTOPUS", "SPIDER", "RAVEN", "HOUND", "MOLE",
        "OWL", "ANT", "MANTIS", "FOX", "BEAVER", "BAT", "CANARY",
        "SERPENT", "CHAMELEON", "BELZEBUB", "FERRET", "GREMLIN", "RAPHAEL",
    }
    assert manifest["invariants"]["delete_allowed"] is False
    assert manifest["invariants"]["overwrite_allowed"] is False
    assert manifest["invariants"]["in_place_edit_allowed"] is False
    assert manifest["invariants"]["spider_graph_write_is_typed"] is True
    assert len(manifest["policy_sha256"]) == 64


def test_spider_can_write_graphs_but_not_arbitrary_relational_memory() -> None:
    token = _token(
        beast="SPIDER",
        layer="RELATIONAL",
        operation="GRAPH_APPEND",
        artifact_type="GRAPH_SNAPSHOT",
    )
    receipt = _decision(token)
    assert receipt["decision"] == "ALLOW"
    assert receipt["reason_code"] == "POLICY_AND_SCOPE_MATCH"

    with pytest.raises(PermissionError):
        _token(
            beast="SPIDER",
            layer="RELATIONAL",
            operation="OBSERVE_APPEND",
            artifact_type="RAW_OBSERVATION",
        )


def test_spider_edge_write_and_node_link_are_typed() -> None:
    for operation, artifact in (
        ("EDGE_APPEND", "RELATION_EDGE"),
        ("NODE_LINK", "DEPENDENCY_LINK"),
    ):
        token = _token(
            beast="SPIDER",
            layer="RELATIONAL",
            operation=operation,
            artifact_type=artifact,
        )
        assert _decision(token)["decision"] == "ALLOW"

    with pytest.raises(PermissionError):
        _token(
            beast="SPIDER",
            layer="RELATIONAL",
            operation="EDGE_APPEND",
            artifact_type="CONTRADICTION",
        )


def test_raven_can_build_memory_indices_but_not_graph_snapshots() -> None:
    token = _token(
        beast="RAVEN",
        layer="SEMANTIC",
        operation="DERIVE",
        artifact_type="MEMORY_INDEX",
    )
    assert _decision(token)["decision"] == "ALLOW"

    with pytest.raises(PermissionError):
        _token(
            beast="RAVEN",
            layer="RELATIONAL",
            operation="GRAPH_APPEND",
            artifact_type="GRAPH_SNAPSHOT",
        )


def test_hound_flags_and_quarantine_requests_but_cannot_overwrite() -> None:
    token = _token(
        beast="HOUND",
        layer="RELATIONAL",
        operation="QUARANTINE_REQUEST",
        artifact_type="QUARANTINE_PROPOSAL",
    )
    assert _decision(token)["decision"] == "ALLOW"

    for operation in DESTRUCTIVE_OPERATIONS:
        receipt = evaluate_access(
            beast="HOUND",
            layer="RELATIONAL",
            operation=operation,
            artifact_type="CONTRADICTION",
            subject_id="spectroscopy:ring-6",
            generation_id="gen-001",
            task_id="task-001",
            token=None,
        )
        assert receipt["decision"] == "DENY"
        assert receipt["reason_code"] == "DESTRUCTIVE_OPERATION_FORBIDDEN"


def test_mantis_requests_supersession_without_in_place_edit() -> None:
    token = _token(
        beast="MANTIS",
        layer="SEMANTIC",
        operation="SUPERSEDE_REQUEST",
        artifact_type="SUPERSEDE_PROPOSAL",
    )
    assert _decision(token)["decision"] == "ALLOW"

    receipt = evaluate_access(
        beast="MANTIS",
        layer="SEMANTIC",
        operation="IN_PLACE_EDIT",
        artifact_type="SUPERSEDE_PROPOSAL",
        subject_id="spectroscopy:ring-6",
        generation_id="gen-001",
        task_id="task-001",
        token=None,
    )
    assert receipt["decision"] == "DENY"


def test_scope_token_prevents_cross_subject_cross_generation_and_cross_task_use() -> None:
    token = _token(
        beast="SPIDER",
        layer="RELATIONAL",
        operation="GRAPH_APPEND",
        artifact_type="GRAPH_SNAPSHOT",
    )
    assert _decision(token)["decision"] == "ALLOW"
    assert _decision(token, subject_id="other")["reason_code"] == "TOKEN_SUBJECT_SCOPE_MISMATCH"
    assert _decision(token, generation_id="gen-002")["reason_code"] == "TOKEN_GENERATION_SCOPE_MISMATCH"
    assert _decision(token, task_id="task-002")["reason_code"] == "TOKEN_TASK_SCOPE_MISMATCH"


def test_subject_scoped_grant_cannot_issue_wildcard_subject_token() -> None:
    with pytest.raises(PermissionError, match="scope"):
        _token(
            beast="SPIDER",
            layer="RELATIONAL",
            operation="GRAPH_APPEND",
            artifact_type="GRAPH_SNAPSHOT",
            subject_scope="*",
        )


def test_metadata_only_grant_does_not_become_payload_access() -> None:
    metadata_token = _token(
        beast="RAVEN",
        layer="ARCHIVAL",
        operation="READ_METADATA",
        artifact_type="AUDIT_RECEIPT",
        subject_scope="*",
        generation_scope="*",
        task_scope="*",
    )
    assert _decision(
        metadata_token,
        subject_id="anything",
        generation_id="anything",
        task_id="anything",
    )["decision"] == "ALLOW"

    with pytest.raises(PermissionError):
        _token(
            beast="RAVEN",
            layer="ARCHIVAL",
            operation="READ_PAYLOAD",
            artifact_type="AUDIT_RECEIPT",
        )


def test_private_scratch_is_local_task_scoped_and_not_synchronized() -> None:
    token = _token(
        beast="MOLE",
        layer=PRIVATE_LAYER,
        operation="DERIVE",
        artifact_type="DERIVATION",
        subject_scope="*",
        generation_scope="*",
        task_scope="task-local",
    )
    receipt = evaluate_access(
        beast="MOLE",
        layer=PRIVATE_LAYER,
        operation="DERIVE",
        artifact_type="DERIVATION",
        subject_id="anything",
        generation_id="anything",
        task_id="task-local",
        token=token,
    )
    assert receipt["decision"] == "ALLOW"
    manifest = policy_manifest()
    assert manifest["private_scratch_policy"]["synchronized"] is False
    assert manifest["private_scratch_policy"]["source_of_truth"] is False


def test_unknown_beast_and_unknown_artifact_are_denied() -> None:
    receipt = evaluate_access(
        beast="UNKNOWN",
        layer="SEMANTIC",
        operation="READ_METADATA",
        artifact_type="MEMORY_INDEX",
        subject_id="s",
        generation_id="g",
        task_id="t",
        token=None,
    )
    assert receipt["decision"] == "DENY"
    assert receipt["reason_code"] == "NO_MATCHING_GRANT"

    receipt = evaluate_access(
        beast="RAVEN",
        layer="SEMANTIC",
        operation="READ_METADATA",
        artifact_type="UNREGISTERED_ARTIFACT",
        subject_id="s",
        generation_id="g",
        task_id="t",
        token=None,
    )
    assert receipt["decision"] == "DENY"


def test_matching_policy_without_token_is_still_denied() -> None:
    receipt = evaluate_access(
        beast="SPIDER",
        layer="RELATIONAL",
        operation="GRAPH_APPEND",
        artifact_type="GRAPH_SNAPSHOT",
        subject_id="spectroscopy:ring-6",
        generation_id="gen-001",
        task_id="task-001",
        token=None,
    )
    assert receipt["decision"] == "DENY"
    assert receipt["reason_code"] == "SCOPED_TOKEN_REQUIRED"
    assert receipt["claims"]["deny_by_default"] is True


def test_token_tamper_fails_closed() -> None:
    token = _token(
        beast="SPIDER",
        layer="RELATIONAL",
        operation="GRAPH_APPEND",
        artifact_type="GRAPH_SNAPSHOT",
    )
    assert validate_capability_token(token)["token_id"] == token["token_id"]

    bad = copy.deepcopy(token)
    bad["artifact_type"] = "RELATION_EDGE"
    with pytest.raises(ValueError, match="commitment"):
        validate_capability_token(bad)

    bad = copy.deepcopy(token)
    bad["claims"]["overwrite_authority"] = True
    with pytest.raises(ValueError, match="claim"):
        validate_capability_token(bad)


def test_receipts_are_deterministic_and_commit_policy() -> None:
    token = _token(
        beast="OWL",
        layer="SEMANTIC",
        operation="AUDIT",
        artifact_type="AUDIT_RECEIPT",
        subject_scope="*",
        generation_scope="*",
        task_scope="task-audit",
    )
    first = _decision(
        token,
        subject_id="any-subject",
        generation_id="any-generation",
        task_id="task-audit",
    )
    second = _decision(
        token,
        subject_id="any-subject",
        generation_id="any-generation",
        task_id="task-audit",
    )
    assert first == second
    assert first["receipt_id"].startswith("bmr:")
    assert first["policy_sha256"] == policy_manifest()["policy_sha256"]
    assert first["claims"]["decision_is_auditable"] is True
    assert first["claims"]["difference_detection_grants_disclosure"] is False


def test_gremlin_is_not_memory_superuser() -> None:
    with pytest.raises(PermissionError):
        _token(
            beast="GREMLIN",
            layer="RELATIONAL",
            operation="GRAPH_APPEND",
            artifact_type="GRAPH_SNAPSHOT",
        )

    token = _token(
        beast="GREMLIN",
        layer="RELATIONAL",
        operation="DERIVE",
        artifact_type="AGGREGATE_CANDIDATE",
        subject_scope="*",
        generation_scope="*",
        task_scope="task-agg",
    )
    assert _decision(
        token,
        subject_id="s",
        generation_id="g",
        task_id="task-agg",
    )["decision"] == "ALLOW"


def test_raphael_governance_does_not_gain_delete_or_overwrite() -> None:
    capabilities = beast_capabilities("RAPHAEL")
    assert capabilities["default"] == "DENY"

    token = _token(
        beast="RAPHAEL",
        layer="RELATIONAL",
        operation="GOVERNANCE_REVIEW",
        artifact_type="GOVERNANCE_DECISION",
        subject_scope="*",
        generation_scope="*",
        task_scope="governance-001",
    )
    assert _decision(
        token,
        subject_id="s",
        generation_id="g",
        task_id="governance-001",
    )["decision"] == "ALLOW"

    for operation in ("DELETE", "OVERWRITE", "IN_PLACE_EDIT"):
        receipt = evaluate_access(
            beast="RAPHAEL",
            layer="RELATIONAL",
            operation=operation,
            artifact_type="GOVERNANCE_DECISION",
            subject_id="s",
            generation_id="g",
            task_id="governance-001",
            token=None,
        )
        assert receipt["decision"] == "DENY"
        assert receipt["reason_code"] == "DESTRUCTIVE_OPERATION_FORBIDDEN"



def test_task_authorization_bundle_issues_exact_tokens_and_receipts() -> None:
    bundle = authorize_memory_requests(
        "SPIDER",
        [
            {
                "layer": "SEMANTIC",
                "operation": "READ_PAYLOAD",
                "artifact_type": "MEMORY_INDEX",
                "subject_id": "spectroscopy:ring-6",
                "generation_id": "gen-001",
            },
            {
                "layer": "RELATIONAL",
                "operation": "GRAPH_APPEND",
                "artifact_type": "GRAPH_SNAPSHOT",
                "subject_id": "spectroscopy:ring-6",
                "generation_id": "gen-001",
            },
        ],
        task_id="task-spider-graph",
    )

    assert bundle["schema"] == "BESTIARY_MEMORY_TASK_AUTHORIZATION_V0_1"
    assert bundle["beast"] == "SPIDER"
    assert bundle["task_id"] == "task-spider-graph"
    assert len(bundle["tokens"]) == 2
    assert len(bundle["receipts"]) == 2
    assert bundle["token_ids"] == [row["token_id"] for row in bundle["tokens"]]
    assert bundle["receipt_ids"] == [row["receipt_id"] for row in bundle["receipts"]]
    assert all(row["task_scope"] == "task-spider-graph" for row in bundle["tokens"])
    assert all(row["decision"] == "ALLOW" for row in bundle["receipts"])
    assert all(validate_access_receipt(row)["decision"] == "ALLOW" for row in bundle["receipts"])
    assert bundle["claims"]["all_requests_allowed"] is True
    assert bundle["claims"]["delete_authority"] is False
    assert bundle["claims"]["overwrite_authority"] is False


def test_task_authorization_fails_whole_bundle_on_one_forbidden_request() -> None:
    with pytest.raises(PermissionError):
        authorize_memory_requests(
            "SPIDER",
            [
                {
                    "layer": "RELATIONAL",
                    "operation": "GRAPH_APPEND",
                    "artifact_type": "GRAPH_SNAPSHOT",
                    "subject_id": "spectroscopy:ring-6",
                    "generation_id": "gen-001",
                },
                {
                    "layer": "RELATIONAL",
                    "operation": "OBSERVE_APPEND",
                    "artifact_type": "RAW_OBSERVATION",
                    "subject_id": "spectroscopy:ring-6",
                    "generation_id": "gen-001",
                },
            ],
            task_id="task-atomic-deny",
        )


def test_task_authorization_cannot_reuse_token_for_another_task() -> None:
    bundle = authorize_memory_requests(
        "RAVEN",
        [
            {
                "layer": "SEMANTIC",
                "operation": "DERIVE",
                "artifact_type": "MEMORY_INDEX",
                "subject_id": "subject-a",
                "generation_id": "gen-a",
            }
        ],
        task_id="task-a",
    )
    token = bundle["tokens"][0]
    denied = evaluate_access(
        beast="RAVEN",
        layer="SEMANTIC",
        operation="DERIVE",
        artifact_type="MEMORY_INDEX",
        subject_id="subject-a",
        generation_id="gen-a",
        task_id="task-b",
        token=token,
    )
    assert denied["decision"] == "DENY"
    assert denied["reason_code"] == "TOKEN_TASK_SCOPE_MISMATCH"


def test_access_receipt_tamper_fails_closed() -> None:
    token = _token(
        beast="SPIDER",
        layer="RELATIONAL",
        operation="GRAPH_APPEND",
        artifact_type="GRAPH_SNAPSHOT",
    )
    receipt = _decision(token)
    assert validate_access_receipt(receipt)["receipt_id"] == receipt["receipt_id"]

    bad = copy.deepcopy(receipt)
    bad["decision"] = "DENY"
    with pytest.raises(ValueError, match="commitment"):
        validate_access_receipt(bad)

    bad = copy.deepcopy(receipt)
    bad["claims"]["delete_authority"] = True
    with pytest.raises(ValueError, match="claim"):
        validate_access_receipt(bad)
