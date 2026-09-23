from __future__ import annotations

import pytest
from gremlin_mcp.semantic_graph_transformer import RELATION_CODES, SemanticGraphTransformer, compile_semantic_graph

def test_compile_is_deterministic_and_candidate_only() -> None:
    docs = ["Heat causes expansion. Expansion supports the pressure model."]
    a = compile_semantic_graph(docs); b = compile_semantic_graph(docs)
    assert a == b
    assert a["status"] == "PASS_CANDIDATE"
    assert len(a["graph_sha256"]) == 64
    assert a["claims"]["neural_transformer_trained"] is False
    assert a["claims"]["canon_allowed"] is False

def test_relation_triggers_are_typed() -> None:
    result = compile_semantic_graph([
        "Heat causes expansion.",
        "Expansion contradicts contraction.",
        "A rotor is a component of a motor.",
    ])
    codes = {row["relation"] for row in result["graph"]["relations"]}
    assert RELATION_CODES["CAUSES"] in codes
    assert RELATION_CODES["CONTRADICTS"] in codes
    assert RELATION_CODES["PART_OF"] in codes

def test_bounded_candidate_generation_beats_full_pairs_for_long_sentence() -> None:
    words = [f"concept{i}" for i in range(60)]
    result = compile_semantic_graph([" ".join(words) + "."], max_neighbors=4)
    metrics = result["metrics"]
    assert metrics["candidate_pairs"] < metrics["full_pair_baseline"]
    assert metrics["candidate_pair_ratio"] < 0.2

def test_repeated_relations_are_compressed_by_multiplicity() -> None:
    result = compile_semantic_graph(["alpha causes beta. " * 100])
    metrics = result["metrics"]
    assert metrics["raw_relation_occurrences"] > metrics["unique_relation_tokens"]
    assert metrics["repeated_edges_removed"] > 0
    assert metrics["relation_occurrence_compression_ratio"] < 0.1

def test_causal_cone_selects_subset() -> None:
    compiler = SemanticGraphTransformer(max_neighbors=2)
    graph = compiler.compile([
        "alpha causes beta. beta causes gamma. gamma causes delta. unrelated supports isolated."
    ])
    cone = compiler.causal_cone(graph, ["alpha"], depth=1)
    terms = {row["term"] for row in cone["nodes"]}
    assert "alpha" in terms
    assert cone["metrics"]["active_nodes"] < cone["metrics"]["full_nodes"]

def test_empty_and_bad_limits_fail_closed() -> None:
    with pytest.raises(ValueError): compile_semantic_graph([])
    with pytest.raises(ValueError): SemanticGraphTransformer(max_neighbors=0)
    with pytest.raises(ValueError): SemanticGraphTransformer(min_confidence=2.0)
