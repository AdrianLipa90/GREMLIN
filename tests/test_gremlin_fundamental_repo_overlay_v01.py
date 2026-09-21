from tools.gremlin_fundamental_repo_overlay_v01 import analyze, parse_graph


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
