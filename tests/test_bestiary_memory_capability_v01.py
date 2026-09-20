from __future__ import annotations

import copy

import pytest

from gremlin_mcp.bestiary_memory_capability import (
    ALL_PRINCIPALS,
    BESTIARY_PRINCIPALS,
    FORBIDDEN_MEMORY_OPERATIONS,
    POLICY,
    build_scope_token,
    evaluate_memory_access,
    memory_capability_manifest,
    principal_profile,
    require_memory_access,
    validate_scope_token,
)


def _token(
    principal: str,
    *,
    subject: str = "spectroscopy:ring-6",
    generation: str = "gen-001",
    operations: tuple[str, ...] = ("READ",),
    artifacts: tuple[str, ...] = ("*",),
    dependencies: tuple[str, ...] = (),
    governance: bool = False,
):
    return build_scope_token(
        principal=principal,
        task_id="task-memory-capability-test",
        subject_ids=[subject],
        generation_ids=[generation],
        operations=operations,
        artifact_types=artifacts,
        dependency_ids=dependencies,
        governance=governance,
    )


def _request(
    principal: str,
    *,
    layer: str,
    operation: str,
    artifact: str,
    token,
    visibility: str = "NONE",
    subject: str = "spectroscopy:ring-6",
    generation: str = "gen-001",
    dependency_id: str | None = None,
):
    return evaluate_memory_access(
        principal=principal,
        layer=layer,
        operation=operation,
        artifact_type=artifact,
        subject_id=subject,
        generation_id=generation,
        requested_visibility=visibility,
        token=token,
        dependency_id=dependency_id,
    )


def test_policy_covers_all_18_bestiary_species_plus_raphael() -> None:
    assert len(BESTIARY_PRINCIPALS) == 18
    assert len(ALL_PRINCIPALS) == 19
    assert set(POLICY) == set(ALL_PRINCIPALS)
    assert "RAPHAEL" in POLICY


def test_manifest_is_deterministic_deny_by_default_and_non_destructive() -> None:
    first = memory_capability_manifest()
    second = memory_capability_manifest()
    assert first == second
    assert first["default_policy"] == "DENY"
    assert len(first["manifest_sha256"]) == 64
    assert set(first["forbidden_memory_operations"]) == set(FORBIDDEN_MEMORY_OPERATIONS)
    assert {"DELETE", "OVERWRITE", "EDIT_IN_PLACE"} <= set(
        first["forbidden_memory_operations"]
    )


def test_every_write_like_rule_has_typed_artifacts() -> None:
    for principal, rules in POLICY.items():
        for rule in rules:
            write_like = [
                op
                for op in rule["operations"]
                if op.endswith("_APPEND") or op.endswith("_REQUEST") or op == "ACK"
            ]
            if write_like:
                assert rule["artifact_types"] != ["*"], (principal, rule)


def test_spider_reads_sources_and_writes_only_typed_graph_artifacts() -> None:
    token = _token(
        "SPIDER",
        operations=("READ", "COMPARE", "GRAPH_APPEND"),
        artifacts=("*", "RELATION_EDGE", "GRAPH_SNAPSHOT"),
    )
    read = _request(
        "SPIDER",
        layer="SEMANTIC",
        operation="READ",
        artifact="PHASENAV_MEMORY_CONSOLIDATED_SEMANTIC_V0_1",
        token=token,
        visibility="FULL",
    )
    graph = _request(
        "SPIDER",
        layer="RELATIONAL",
        operation="GRAPH_APPEND",
        artifact="RELATION_EDGE",
        token=token,
    )
    wrong = _request(
        "SPIDER",
        layer="RELATIONAL",
        operation="OBSERVE_APPEND",
        artifact="RAW_OBSERVATION",
        token=token,
    )

    assert read["decision"] == "ALLOW"
    assert graph["decision"] == "ALLOW"
    assert graph["rule_id"] == "SPI-REL-GRAPH"
    assert wrong["decision"] == "DENY"
    assert wrong["reason_code"] == "NO_MATCHING_TYPED_CAPABILITY_RULE"


def test_raven_can_index_memory_but_cannot_write_graph_edges() -> None:
    token = _token(
        "RAVEN",
        operations=("READ", "INDEX_APPEND", "GRAPH_APPEND"),
        artifacts=("*", "MEMORY_INDEX", "RELATION_EDGE"),
    )
    index = _request(
        "RAVEN",
        layer="SEMANTIC",
        operation="INDEX_APPEND",
        artifact="MEMORY_INDEX",
        token=token,
    )
    graph = _request(
        "RAVEN",
        layer="RELATIONAL",
        operation="GRAPH_APPEND",
        artifact="RELATION_EDGE",
        token=token,
    )
    assert index["decision"] == "ALLOW"
    assert graph["decision"] == "DENY"


def test_hound_can_flag_and_request_quarantine_but_cannot_quarantine_directly() -> None:
    token = _token(
        "HOUND",
        operations=("FLAG_APPEND", "QUARANTINE_REQUEST", "QUARANTINE"),
        artifacts=("CONTRADICTION", "QUARANTINE_REQUEST"),
    )
    flag = _request(
        "HOUND",
        layer="RELATIONAL",
        operation="FLAG_APPEND",
        artifact="CONTRADICTION",
        token=token,
    )
    request = _request(
        "HOUND",
        layer="RELATIONAL",
        operation="QUARANTINE_REQUEST",
        artifact="QUARANTINE_REQUEST",
        token=token,
    )
    direct = _request(
        "HOUND",
        layer="RELATIONAL",
        operation="QUARANTINE",
        artifact="QUARANTINE_REQUEST",
        token=token,
    )
    assert flag["decision"] == "ALLOW"
    assert request["decision"] == "ALLOW"
    assert direct["decision"] == "DENY"


def test_mantis_can_request_supersession_without_deleting_source() -> None:
    token = _token(
        "MANTIS",
        operations=("SUPERSEDE_REQUEST", "DELETE"),
        artifacts=("SUPERSEDE_REQUEST",),
    )
    supersede = _request(
        "MANTIS",
        layer="RELATIONAL",
        operation="SUPERSEDE_REQUEST",
        artifact="SUPERSEDE_REQUEST",
        token=token,
    )
    delete = _request(
        "MANTIS",
        layer="RELATIONAL",
        operation="DELETE",
        artifact="SUPERSEDE_REQUEST",
        token=token,
    )
    assert supersede["decision"] == "ALLOW"
    assert delete["decision"] == "DENY"
    assert delete["reason_code"] == "GLOBAL_DESTRUCTIVE_MEMORY_OPERATION_DENIED"


@pytest.mark.parametrize("principal", ALL_PRINCIPALS)
@pytest.mark.parametrize("operation", ["DELETE", "OVERWRITE", "EDIT_IN_PLACE"])
def test_destructive_shared_memory_operations_are_denied_for_every_principal(
    principal: str,
    operation: str,
) -> None:
    token = _token(
        principal,
        operations=(operation,),
        artifacts=("*",),
        governance=(principal == "RAPHAEL"),
    )
    receipt = _request(
        principal,
        layer="RELATIONAL",
        operation=operation,
        artifact="ANY_MEMORY",
        token=token,
    )
    assert receipt["decision"] == "DENY"
    assert receipt["reason_code"] == "GLOBAL_DESTRUCTIVE_MEMORY_OPERATION_DENIED"


def test_ant_compare_is_feature_view_not_full_payload() -> None:
    token = _token(
        "ANT",
        operations=("COMPARE",),
        artifacts=("*",),
    )
    feature = _request(
        "ANT",
        layer="SEMANTIC",
        operation="COMPARE",
        artifact="SEMANTIC_STATE",
        token=token,
        visibility="FEATURE_VIEW",
    )
    full = _request(
        "ANT",
        layer="SEMANTIC",
        operation="COMPARE",
        artifact="SEMANTIC_STATE",
        token=token,
        visibility="FULL",
    )
    assert feature["decision"] == "ALLOW"
    assert feature["visibility"] == "FEATURE_VIEW"
    assert full["decision"] == "DENY"
    assert full["reason_code"] == "REQUESTED_VISIBILITY_EXCEEDS_RULE"


def test_octopus_global_route_view_is_metadata_only() -> None:
    token = build_scope_token(
        principal="OCTOPUS",
        task_id="routing",
        subject_ids=["*"],
        generation_ids=["*"],
        operations=["READ", "ROUTE"],
        artifact_types=["*"],
    )
    metadata = _request(
        "OCTOPUS",
        layer="SEMANTIC",
        operation="READ",
        artifact="ANY_SEMANTIC",
        token=token,
        visibility="METADATA",
        subject="unrelated-subject",
        generation="unrelated-generation",
    )
    full = _request(
        "OCTOPUS",
        layer="SEMANTIC",
        operation="READ",
        artifact="ANY_SEMANTIC",
        token=token,
        visibility="FULL",
        subject="unrelated-subject",
        generation="unrelated-generation",
    )
    assert metadata["decision"] == "ALLOW"
    assert full["decision"] == "DENY"
    assert full["reason_code"] == "GLOBAL_SCOPE_LIMITED_TO_METADATA"


def test_task_scoped_payload_read_rejects_wildcard_subject_or_generation() -> None:
    token = build_scope_token(
        principal="SPIDER",
        task_id="bad-wildcard",
        subject_ids=["*"],
        generation_ids=["*"],
        operations=["READ"],
        artifact_types=["*"],
    )
    receipt = _request(
        "SPIDER",
        layer="SEMANTIC",
        operation="READ",
        artifact="SEMANTIC_STATE",
        token=token,
        visibility="FULL",
    )
    assert receipt["decision"] == "DENY"
    assert receipt["reason_code"] == "WILDCARD_FORBIDDEN_FOR_PAYLOAD_SCOPE"


def test_subject_generation_and_dependency_scope_fail_closed() -> None:
    token = _token(
        "SPIDER",
        operations=("READ",),
        artifacts=("*",),
        dependencies=("dep:allowed",),
    )
    wrong_subject = _request(
        "SPIDER",
        layer="SEMANTIC",
        operation="READ",
        artifact="SEMANTIC_STATE",
        token=token,
        visibility="FULL",
        subject="other",
    )
    wrong_generation = _request(
        "SPIDER",
        layer="SEMANTIC",
        operation="READ",
        artifact="SEMANTIC_STATE",
        token=token,
        visibility="FULL",
        generation="other",
    )
    wrong_dependency = _request(
        "SPIDER",
        layer="SEMANTIC",
        operation="READ",
        artifact="SEMANTIC_STATE",
        token=token,
        visibility="FULL",
        dependency_id="dep:denied",
    )
    assert wrong_subject["decision"] == "DENY"
    assert wrong_generation["decision"] == "DENY"
    assert wrong_dependency["decision"] == "DENY"
    assert wrong_dependency["reason_code"] == "DEPENDENCY_OUTSIDE_SCOPE_TOKEN"


def test_shared_memory_requires_scope_token() -> None:
    receipt = _request(
        "RAVEN",
        layer="SEMANTIC",
        operation="READ",
        artifact="MEMORY_INDEX",
        token=None,
        visibility="FULL",
    )
    assert receipt["decision"] == "DENY"
    assert receipt["reason_code"] == "SHARED_MEMORY_SCOPE_TOKEN_REQUIRED"


def test_ferret_is_explicit_grant_and_metadata_only() -> None:
    token = _token(
        "FERRET",
        operations=("READ", "ACTUATION_RECEIPT_APPEND"),
        artifacts=("*", "ACTUATION_RECEIPT"),
    )
    metadata = _request(
        "FERRET",
        layer="RELATIONAL",
        operation="READ",
        artifact="AUTHORITY_STATE",
        token=token,
        visibility="METADATA",
    )
    full = _request(
        "FERRET",
        layer="RELATIONAL",
        operation="READ",
        artifact="AUTHORITY_STATE",
        token=token,
        visibility="FULL",
    )
    receipt = _request(
        "FERRET",
        layer="RELATIONAL",
        operation="ACTUATION_RECEIPT_APPEND",
        artifact="ACTUATION_RECEIPT",
        token=token,
    )
    assert metadata["decision"] == "ALLOW"
    assert full["decision"] == "DENY"
    assert receipt["decision"] == "ALLOW"


def test_raphael_governance_reads_metadata_not_full_payload_and_cannot_delete_memory() -> None:
    token = build_scope_token(
        principal="RAPHAEL",
        task_id="governance",
        subject_ids=["*"],
        generation_ids=["*"],
        operations=["READ", "AUDIT", "GOVERNANCE_APPEND", "DELETE"],
        artifact_types=["*", "MEMORY_GOVERNANCE_RECEIPT"],
        governance=True,
    )
    metadata = _request(
        "RAPHAEL",
        layer="SEMANTIC",
        operation="AUDIT",
        artifact="SEMANTIC_STATE",
        token=token,
        visibility="METADATA",
        subject="any",
        generation="any",
    )
    full = _request(
        "RAPHAEL",
        layer="SEMANTIC",
        operation="READ",
        artifact="SEMANTIC_STATE",
        token=token,
        visibility="FULL",
        subject="any",
        generation="any",
    )
    decree = _request(
        "RAPHAEL",
        layer="RELATIONAL",
        operation="GOVERNANCE_APPEND",
        artifact="MEMORY_GOVERNANCE_RECEIPT",
        token=token,
        subject="any",
        generation="any",
    )
    delete = _request(
        "RAPHAEL",
        layer="RELATIONAL",
        operation="DELETE",
        artifact="MEMORY_GOVERNANCE_RECEIPT",
        token=token,
        subject="any",
        generation="any",
    )
    assert metadata["decision"] == "ALLOW"
    assert full["decision"] == "DENY"
    assert decree["decision"] == "ALLOW"
    assert delete["decision"] == "DENY"


def test_invalid_or_tampered_token_is_denied_and_receipted() -> None:
    token = _token("RAVEN", operations=("READ",), artifacts=("*",))
    tampered = copy.deepcopy(token)
    tampered["subject_ids"] = ["other"]

    with pytest.raises(ValueError, match="commitment"):
        validate_scope_token(tampered)

    receipt = _request(
        "RAVEN",
        layer="SEMANTIC",
        operation="READ",
        artifact="SEMANTIC_STATE",
        token=tampered,
        visibility="FULL",
    )
    assert receipt["decision"] == "DENY"
    assert receipt["reason_code"] == "INVALID_SCOPE_TOKEN"
    assert len(receipt["receipt_sha256"]) == 64


def test_receipts_are_deterministic_and_require_helper_raises_on_deny() -> None:
    token = _token("RAVEN", operations=("READ",), artifacts=("*",))
    first = _request(
        "RAVEN",
        layer="SEMANTIC",
        operation="READ",
        artifact="SEMANTIC_STATE",
        token=token,
        visibility="FULL",
    )
    second = _request(
        "RAVEN",
        layer="SEMANTIC",
        operation="READ",
        artifact="SEMANTIC_STATE",
        token=token,
        visibility="FULL",
    )
    assert first == second
    assert first["decision"] == "ALLOW"

    with pytest.raises(PermissionError, match="memory access denied"):
        require_memory_access(
            principal="RAVEN",
            layer="RELATIONAL",
            operation="GRAPH_APPEND",
            artifact_type="RELATION_EDGE",
            subject_id="spectroscopy:ring-6",
            generation_id="gen-001",
            token=token,
        )


def test_private_scratch_is_local_only_and_not_source_of_truth() -> None:
    profile = principal_profile("SPIDER")
    assert profile["private_scratch"]["source_of_truth"] is False
    assert profile["private_scratch"]["synchronized"] is False

    receipt = evaluate_memory_access(
        principal="SPIDER",
        layer="PRIVATE_SCRATCH",
        operation="READ",
        artifact_type="LOCAL_GRAPH_DRAFT",
        subject_id="spectroscopy:ring-6",
        generation_id="gen-001",
        requested_visibility="FULL",
        token=None,
    )
    # No shared policy rule exists for private scratch: scratch is deliberately
    # outside shared memory SoT and is described, not granted by shared ACL.
    assert receipt["decision"] == "DENY"
