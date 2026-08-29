from __future__ import annotations

import argparse
import json
from pathlib import Path

from gremlin_mcp.relational_algebra import audit_relation_set, build_graph, compose_all, find_paths
from gremlin_mcp.relational_cases import bind_relation


def _r(operator: str, *bindings: dict) -> dict:
    return bind_relation(operator, bindings, evidence="RELATIONAL_ALGEBRA_PROBE")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    relations = [
        _r(
            "NAMES",
            {"case": "NOM", "entity": "Adrian"},
            {"case": "ACC", "entity": "assistant"},
            {"case": "INS", "entity": "Zosia"},
        ),
        _r(
            "CONNECTED_WITH",
            {"case": "NOM", "entity": "Zosia"},
            {"case": "INS", "entity": "Adrian"},
        ),
        _r(
            "BELONGS_TO",
            {"case": "NOM", "entity": "moduł"},
            {"case": "GEN", "entity": "system"},
        ),
        _r(
            "CONNECTED_WITH",
            {"case": "NOM", "entity": "system"},
            {"case": "INS", "entity": "NOEMA"},
        ),
        _r(
            "DESCRIBES",
            {"case": "NOM", "entity": "teoria"},
            {"case": "ACC", "entity": "geometria"},
        ),
        _r(
            "CONNECTED_WITH",
            {"case": "NOM", "entity": "geometria"},
            {"case": "INS", "entity": "informacja"},
        ),
    ]

    graph = build_graph(relations)
    composed = compose_all(relations)
    module_path = find_paths(relations, source="moduł", target="NOEMA", max_depth=2)
    theory_path = find_paths(relations, source="teoria", target="informacja", max_depth=2)
    audit = audit_relation_set(relations)

    name_edges = [edge for edge in graph["projected_edges"] if edge["predicate"] == "HAS_ASSIGNED_NAME"]
    checks = {
        "hyperedges_preserved": graph["hyperedge_count"] == len(relations),
        "name_binding_present": any(edge["source_key"] == "assistant" and edge["target_key"] == "zosia" for edge in name_edges),
        "module_path_present": any(path["operator_sequence"] == ["BELONGS_TO", "CONNECTED_WITH"] for path in module_path["paths"]),
        "theory_path_present": any(path["operator_sequence"] == ["DESCRIBES", "CONNECTED_WITH"] for path in theory_path["paths"]),
        "composition_candidates_present": composed["path_count"] > 0,
        "no_semantic_conflict_invented": audit["semantic_conflicts"] == [],
        "fail_closed_authority": graph["authority"] == {
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        },
    }
    receipt = {
        "schema": "GREMLIN_RELATIONAL_ALGEBRA_PROBE_V0_1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "graph_commitment": graph["graph_commitment"],
        "hyperedge_count": graph["hyperedge_count"],
        "projected_edge_count": graph["projected_edge_count"],
        "traversal_edge_count": graph["traversal_edge_count"],
        "composition_path_count": composed["path_count"],
        "module_to_noema_paths": module_path["paths"],
        "theory_to_information_paths": theory_path["paths"],
        "name_binding_candidates": audit["name_binding_candidates"],
        "semantic_conflict_status": audit["semantic_conflict_status"],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    if receipt["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
