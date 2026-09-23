from __future__ import annotations

import pytest

from gremlin_mcp.semantic_graph_transformer import compile_semantic_graph
from gremlin_mcp.semantic_graph_bestiary import ROLE_REQUESTS, build_bestiary_handoff


def _fake_authorizer(task_id: str):
    def authorize(role, requests):
        return {
            "schema": "BESTIARY_MEMORY_TASK_AUTHORIZATION_V0_1",
            "beast": role,
            "task_id": task_id,
            "requests": requests,
            "canon_allowed": False,
            "claims": {"all_requests_allowed": True},
        }
    return authorize


def test_stage_order_and_capability_shapes() -> None:
    graph = compile_semantic_graph(["alpha causes beta. beta depends on gamma."])
    out = build_bestiary_handoff(graph, subject_id="sgt:test", generation_id="gen-001", task_id="task-001")
    assert out["stage_order"] == ["SPIDER", "ELEPHANT", "BEES"]
    assert out["canon_allowed"] is False
    assert out["execution_semantics"]["automatic_hive_mutation"] is False
    assert len(out["handoff_sha256"]) == 64
    assert {s["role"] for s in out["stages"]} == set(ROLE_REQUESTS)


def test_exact_existing_policy_artifacts_are_used() -> None:
    graph = compile_semantic_graph(["alpha causes beta."])
    out = build_bestiary_handoff(graph, subject_id="s", generation_id="g", task_id="t")
    by_role = {x["role"]: x for x in out["stages"]}
    assert {x["artifact_type"] for x in by_role["SPIDER"]["requests"]} == {"GRAPH_SNAPSHOT", "RELATION_EDGE", "DEPENDENCY_LINK"}
    assert {x["artifact_type"] for x in by_role["ELEPHANT"]["requests"]} == {"MEMORY_ORBIT", "CONSOLIDATION_RECEIPT", "REPLAY_PLAN"}
    assert {x["artifact_type"] for x in by_role["BEES"]["requests"]} == {"COHERENCE_FINDING", "ANTI_ENTROPY_DELTA", "RECONCILE_PROPOSAL"}


def test_authorization_callback_is_role_and_task_bound() -> None:
    graph = compile_semantic_graph(["alpha causes beta."])
    out = build_bestiary_handoff(graph, subject_id="s", generation_id="g", task_id="t", authorize=_fake_authorizer("t"))
    assert all(stage["authorization"] is not None for stage in out["stages"])


def test_bad_authorization_fails_closed() -> None:
    graph = compile_semantic_graph(["alpha causes beta."])
    def bad(role, requests):
        return {"beast":"WRONG", "task_id":"t", "canon_allowed":False}
    with pytest.raises(PermissionError):
        build_bestiary_handoff(graph, subject_id="s", generation_id="g", task_id="t", authorize=bad)
