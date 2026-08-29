from gremlin_mcp.relational_algebra import (
    audit_relation_set,
    build_graph,
    compare_edges,
    compose_all,
    find_paths,
    invert_edge,
    project_relation,
    to_hyperedge,
)
from gremlin_mcp.relational_cases import bind_relation


def _bind(operator, *rows):
    return bind_relation(operator, rows, evidence="TEST")


def test_hyperedge_semantic_commitment_is_binding_order_independent():
    a = _bind(
        "CONNECTED_WITH",
        {"case": "NOM", "entity": "Zosia"},
        {"case": "INS", "entity": "Adrian"},
    )
    b = _bind(
        "CONNECTED_WITH",
        {"case": "INS", "entity": "Adrian"},
        {"case": "NOM", "entity": "Zosia"},
    )
    assert a["relation_commitment"] != b["relation_commitment"]
    assert to_hyperedge(a)["semantic_frame_commitment"] == to_hyperedge(b)["semantic_frame_commitment"]


def test_connected_with_projection_is_symmetric_at_semantic_identity_level():
    forward = project_relation(
        _bind(
            "CONNECTED_WITH",
            {"case": "NOM", "entity": "Zosia"},
            {"case": "INS", "entity": "Adrian"},
        )
    )["edges"][0]
    reverse_surface = project_relation(
        _bind(
            "CONNECTED_WITH",
            {"case": "NOM", "entity": "Adrian"},
            {"case": "INS", "entity": "Zosia"},
        )
    )["edges"][0]
    assert forward["semantic_edge_commitment"] == reverse_surface["semantic_edge_commitment"]
    assert compare_edges(forward, reverse_surface)["comparison"] == "SEMANTICALLY_EQUIVALENT_PROJECTION"


def test_belongs_to_inverts_without_rewriting_source_hyperedge():
    relation = _bind(
        "BELONGS_TO",
        {"case": "NOM", "entity": "moduł"},
        {"case": "GEN", "entity": "system"},
    )
    projection = project_relation(relation)
    edge = projection["edges"][0]
    inverse = invert_edge(edge)
    assert edge["predicate"] == "BELONGS_TO"
    assert edge["source"] == "moduł"
    assert edge["target"] == "system"
    assert inverse["predicate"] == "CONTAINS_MEMBER"
    assert inverse["source"] == "system"
    assert inverse["target"] == "moduł"
    assert projection["hyperedge"]["operator"] == "BELONGS_TO"


def test_names_keeps_nary_frame_and_emits_bounded_name_binding_projection():
    relation = _bind(
        "NAMES",
        {"case": "NOM", "entity": "Adrian"},
        {"case": "ACC", "entity": "assistant"},
        {"case": "INS", "entity": "Zosia"},
    )
    projection = project_relation(relation)
    assert len(projection["hyperedge"]["bindings"]) == 3
    by_predicate = {edge["predicate"]: edge for edge in projection["edges"]}
    assert by_predicate["NAMES"]["source"] == "Adrian"
    assert by_predicate["NAMES"]["target"] == "assistant"
    assert by_predicate["HAS_ASSIGNED_NAME"]["source"] == "assistant"
    assert by_predicate["HAS_ASSIGNED_NAME"]["target"] == "Zosia"
    assert by_predicate["HAS_ASSIGNED_NAME"]["relation_kind"] == "NAME_BINDING_CANDIDATE"


def test_gives_remains_three_port_hyperedge_while_binary_projection_keeps_object_as_qualifier():
    relation = _bind(
        "GIVES",
        {"case": "NOM", "entity": "Adrian"},
        {"case": "DAT", "entity": "Zosi"},
        {"case": "ACC", "entity": "książkę"},
    )
    projection = project_relation(relation)
    edge = projection["edges"][0]
    assert projection["hyperedge"]["complete"] is True
    assert edge["predicate"] == "GIVES_TO"
    assert edge["source"] == "Adrian"
    assert edge["target"] == "Zosi"
    assert edge["qualifiers"] == [
        {
            "case": "ACC",
            "entity": "książkę",
            "entity_key": "książkę",
            "operator_role": "transferred_object",
        }
    ]


def test_two_hop_composition_preserves_operator_sequence_instead_of_inventing_predicate():
    relations = [
        _bind(
            "BELONGS_TO",
            {"case": "NOM", "entity": "moduł"},
            {"case": "GEN", "entity": "system"},
        ),
        _bind(
            "CONNECTED_WITH",
            {"case": "NOM", "entity": "system"},
            {"case": "INS", "entity": "NOEMA"},
        ),
    ]
    result = compose_all(relations)
    matching = [
        path for path in result["paths"]
        if path["source_key"] == "moduł" and path["target_key"] == "noema"
    ]
    assert matching
    assert matching[0]["operator_sequence"] == ["BELONGS_TO", "CONNECTED_WITH"]
    assert matching[0]["epistemic_status"] == "COMPOSED_PROJECTION_CANDIDATE_NOT_COLLAPSED_TO_NEW_PREDICATE"


def test_find_paths_uses_inverse_semantics_for_traversal():
    relations = [
        _bind(
            "BELONGS_TO",
            {"case": "NOM", "entity": "moduł"},
            {"case": "GEN", "entity": "system"},
        ),
        _bind(
            "CONNECTED_WITH",
            {"case": "NOM", "entity": "system"},
            {"case": "INS", "entity": "NOEMA"},
        ),
    ]
    result = find_paths(relations, source="NOEMA", target="moduł", max_depth=2)
    assert result["path_count"] >= 1
    assert any(path["operator_sequence"] == ["CONNECTED_WITH", "CONTAINS_MEMBER"] for path in result["paths"])
    assert result["epistemic_boundary"] == "PATH_EXISTENCE_DOES_NOT_IMPLY_TRANSITIVE_SEMANTIC_EQUIVALENCE"


def test_graph_keeps_hyperedges_separate_from_binary_projections():
    relations = [
        _bind(
            "NAMES",
            {"case": "NOM", "entity": "Adrian"},
            {"case": "ACC", "entity": "assistant"},
            {"case": "INS", "entity": "Zosia"},
        ),
        _bind(
            "CONNECTED_WITH",
            {"case": "NOM", "entity": "Zosia"},
            {"case": "INS", "entity": "Adrian"},
        ),
    ]
    graph = build_graph(relations)
    assert graph["hyperedge_count"] == 2
    assert graph["projected_edge_count"] == 3
    assert graph["kind"] == "RELATIONAL_HYPERGRAPH_WITH_BINARY_PROJECTIONS"


def test_audit_reports_unresolved_discourse_entities_without_calling_them_semantic_conflicts():
    relations = [
        _bind(
            "NAMES",
            {"case": "NOM", "entity": "@speaker", "confidence": 0.98},
            {"case": "ACC", "entity": "cię", "confidence": 0.88},
            {"case": "INS", "entity": "Zosią", "confidence": 0.88},
        )
    ]
    audit = audit_relation_set(relations)
    assert audit["status"] == "STRUCTURAL_ISSUES_PRESENT"
    assert audit["unresolved_surface_entities"] == ["@speaker"]
    assert audit["semantic_conflicts"] == []
    assert audit["semantic_conflict_status"] == "NOT_INFERRED_WITHOUT_OPERATOR_EXCLUSIVITY_OR_DOMAIN_RULES"


def test_path_search_rejects_unbounded_depth():
    relation = _bind(
        "CONNECTED_WITH",
        {"case": "NOM", "entity": "A"},
        {"case": "INS", "entity": "B"},
    )
    try:
        find_paths([relation], source="A", target="B", max_depth=99)
    except ValueError as exc:
        assert "max_depth" in str(exc)
    else:
        raise AssertionError("expected fail-closed max_depth validation")
