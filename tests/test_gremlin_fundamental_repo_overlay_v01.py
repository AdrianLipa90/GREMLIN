import pytest

from tools.gremlin_fundamental_repo_overlay_v01 import (
    ClaimNode,
    analyze,
    apply_candidate_overlay,
    parse_graph,
)


def test_overlay_finds_cross_repo_edges_and_frontier_root():
    text = """
nodes:
- {claim_id: "A.ONE", repository: A, status: "CLOSED"}
- {claim_id: "A.TWO", repository: A, status: "OPEN"}
- {claim_id: "B.ONE", repository: B, status: "CANDIDATE_TARGET"}
edges:
- {from: "A.ONE", to: "A.TWO"}
- {from: "A.TWO", to: "B.ONE"}
"""
    nodes, edges = parse_graph(text)
    result = analyze(nodes, edges)
    assert result["node_count"] == 3
    assert result["edge_count"] == 2
    assert result["cross_repository_edge_counts"] == {"A->B": 1}
    assert result["frontier_count"] == 2
    roots = {row["claim_id"] for row in result["frontier_roots"]}
    assert roots == {"A.TWO"}
    assert result["high_impact_frontier"][0]["claim_id"] == "A.TWO"
    assert result["nontrivial_scc_count"] == 0


def test_closed_status_is_not_false_positive_frontier():
    text = """
nodes:
- {claim_id: "A.CLOSED", repository: A, status: "CLOSED"}
- {claim_id: "A.PASS", repository: A, status: "PASS_EXACT"}
edges:
- {from: "A.CLOSED", to: "A.PASS"}
"""
    nodes, edges = parse_graph(text)
    result = analyze(nodes, edges)
    assert result["frontier_count"] == 0
    assert result["frontier_root_count"] == 0


def test_candidate_overlay_is_additive_and_read_only():
    nodes = {
        "A.ONE": ClaimNode("A.ONE", "A", "CLOSED"),
        "B.ONE": ClaimNode("B.ONE", "B", "OPEN"),
    }
    edges = [("A.ONE", "B.ONE")]
    overlay = {
        "authority": "CANDIDATE_ONLY",
        "canon_allowed": False,
        "nodes": [
            {
                "claim_id": "CROSS.GLUE",
                "repository": "CROSS_STACK",
                "status": "CANDIDATE_META_CONTRACT / OPEN",
            }
        ],
        "edges": [
            {"from": "A.ONE", "to": "CROSS.GLUE"},
            {"from": "B.ONE", "to": "CROSS.GLUE"},
        ],
    }

    merged_nodes, merged_edges = apply_candidate_overlay(nodes, edges, overlay)
    assert set(nodes) == {"A.ONE", "B.ONE"}
    assert edges == [("A.ONE", "B.ONE")]
    assert "CROSS.GLUE" in merged_nodes
    assert ("B.ONE", "CROSS.GLUE") in merged_edges

    result = analyze(merged_nodes, merged_edges, candidate_overlay_applied=True)
    assert result["candidate_overlay_applied"] is True
    assert result["repository_node_counts"]["CROSS_STACK"] == 1
    assert result["nontrivial_scc_count"] == 0


def test_candidate_overlay_cannot_replace_canonical_claim():
    nodes = {"A.ONE": ClaimNode("A.ONE", "A", "CLOSED")}
    overlay = {
        "authority": "CANDIDATE_ONLY",
        "canon_allowed": False,
        "nodes": [
            {"claim_id": "A.ONE", "repository": "X", "status": "CANDIDATE"}
        ],
        "edges": [],
    }
    with pytest.raises(ValueError, match="cannot replace canonical claim"):
        apply_candidate_overlay(nodes, [], overlay)


def test_candidate_overlay_unknown_endpoint_fails_closed():
    nodes = {"A.ONE": ClaimNode("A.ONE", "A", "CLOSED")}
    overlay = {
        "authority": "CANDIDATE_ONLY",
        "canon_allowed": False,
        "nodes": [],
        "edges": [{"from": "A.ONE", "to": "MISSING"}],
    }
    with pytest.raises(ValueError, match="unknown endpoint"):
        apply_candidate_overlay(nodes, [], overlay)


def test_cycle_scan_detects_nontrivial_scc():
    nodes = {
        "A": ClaimNode("A", "A", "OPEN"),
        "B": ClaimNode("B", "B", "OPEN"),
    }
    result = analyze(nodes, [("A", "B"), ("B", "A")])
    assert result["nontrivial_scc_count"] == 1
    assert result["nontrivial_sccs"] == [["A", "B"]]
