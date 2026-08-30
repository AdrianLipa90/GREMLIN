from __future__ import annotations

from collections import Counter, defaultdict, deque
import hashlib
import json
import unicodedata
from typing import Any, Iterable, Mapping

from gremlin_mcp.relational_cases import CASES, OPERATOR_SIGNATURES, operator_signature

SCHEMA = "GREMLIN_RELATIONAL_ALGEBRA_V0_1"
VERSION = "0.1.0"
CASE_ORDER = tuple(CASES)

# Case frames remain n-ary hyperedges. Binary edges below are derived projections
# used only for traversal/composition. They never replace the source hyperedge.
PRIMARY_PROJECTIONS: dict[str, dict[str, Any]] = {
    "NAMES": {
        "source_case": "NOM",
        "target_case": "ACC",
        "predicate": "NAMES",
        "inverse_predicate": "NAMED_BY",
        "symmetric": False,
    },
    "DESCRIBES": {
        "source_case": "NOM",
        "target_case": "ACC",
        "predicate": "DESCRIBES",
        "inverse_predicate": "DESCRIBED_BY",
        "symmetric": False,
    },
    "SPEAKS_ABOUT": {
        "source_case": "NOM",
        "target_case": "LOC",
        "predicate": "SPEAKS_ABOUT",
        "inverse_predicate": "TOPIC_OF_SPEECH_BY",
        "symmetric": False,
    },
    "CONNECTED_WITH": {
        "source_case": "NOM",
        "target_case": "INS",
        "predicate": "CONNECTED_WITH",
        "inverse_predicate": "CONNECTED_WITH",
        "symmetric": True,
    },
    "BELONGS_TO": {
        "source_case": "NOM",
        "target_case": "GEN",
        "predicate": "BELONGS_TO",
        "inverse_predicate": "CONTAINS_MEMBER",
        "symmetric": False,
    },
    "GIVES": {
        "source_case": "NOM",
        "target_case": "DAT",
        "predicate": "GIVES_TO",
        "inverse_predicate": "RECEIVES_FROM",
        "symmetric": False,
    },
    "ADDRESSES": {
        "source_case": "NOM",
        "target_case": "VOC",
        "predicate": "ADDRESSES",
        "inverse_predicate": "ADDRESSED_BY",
        "symmetric": False,
    },
}

# NAMES also establishes a bounded name-binding candidate between the named
# entity and the assigned surface designation. This is not global identity.
SECONDARY_PROJECTIONS: dict[str, tuple[dict[str, Any], ...]] = {
    "NAMES": (
        {
            "source_case": "ACC",
            "target_case": "INS",
            "predicate": "HAS_ASSIGNED_NAME",
            "inverse_predicate": "ASSIGNED_NAME_OF",
            "symmetric": False,
            "relation_kind": "NAME_BINDING_CANDIDATE",
        },
    ),
}


def _authority() -> dict[str, bool]:
    return {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _entity_key(value: Any) -> str:
    # Surface-form normalization only. No lemma, morphology, pronoun resolution,
    # ontology identity or cross-language equivalence is inferred here.
    text = unicodedata.normalize("NFC", str(value).strip())
    return " ".join(text.split()).casefold()


def _case_rank(case: str) -> int:
    try:
        return CASE_ORDER.index(case)
    except ValueError:
        return len(CASE_ORDER)


def to_hyperedge(relation: Mapping[str, Any]) -> dict[str, Any]:
    operator = str(relation.get("operator") or "").strip().upper()
    if operator not in OPERATOR_SIGNATURES:
        raise ValueError(f"unknown relational operator: {operator!r}")
    signature = operator_signature(operator)
    raw_bindings = relation.get("bindings")
    if not isinstance(raw_bindings, list):
        raise ValueError("relation requires bindings list")

    seen: set[str] = set()
    bindings: list[dict[str, Any]] = []
    for raw in raw_bindings:
        if not isinstance(raw, Mapping):
            raise ValueError("binding must be an object")
        case = str(raw.get("case") or "").strip().upper()
        if case not in CASES:
            raise ValueError(f"unknown grammatical case: {case!r}")
        if case in seen:
            raise ValueError(f"duplicate case binding for {case}")
        entity = str(raw.get("entity") or "").strip()
        if not entity:
            raise ValueError("binding entity must be non-empty")
        seen.add(case)
        confidence = float(raw.get("confidence", 1.0))
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        bindings.append(
            {
                "case": case,
                "entity": entity,
                "entity_key": _entity_key(entity),
                "operator_role": str(raw.get("operator_role") or signature["roles"].get(case) or ""),
                "evidence": str(raw.get("evidence") or "UNSPECIFIED"),
                "confidence": confidence,
            }
        )
    bindings.sort(key=lambda row: (_case_rank(row["case"]), row["entity_key"], row["operator_role"]))

    required = list(signature["required"])
    missing = [case for case in required if case not in seen]
    allowed = set(required) | set(signature["optional"])
    extra = sorted(case for case in seen if case not in allowed)
    if extra:
        raise ValueError(f"cases not admitted by {operator}: {extra}")

    semantic_core = {
        "operator": operator,
        "ports": [
            {
                "case": row["case"],
                "entity_key": row["entity_key"],
                "operator_role": row["operator_role"],
            }
            for row in bindings
        ],
    }
    evidence_core = {
        "operator": operator,
        "ports": bindings,
        "source_relation_commitment": relation.get("relation_commitment"),
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "kind": "CASE_TYPED_RELATIONAL_HYPEREDGE",
        "operator": operator,
        "bindings": bindings,
        "required_cases": required,
        "optional_cases": list(signature["optional"]),
        "missing_required_cases": missing,
        "complete": not missing,
        "surface_resolution": "SURFACE_FORM_ONLY_NO_LEMMA_OR_COREFERENCE",
        "source_relation_commitment": relation.get("relation_commitment"),
        "semantic_frame_commitment": _commit(b"GREMLIN-RELATIONAL-HYPEREDGE-SEMANTIC/v0.1", semantic_core),
        "evidence_frame_commitment": _commit(b"GREMLIN-RELATIONAL-HYPEREDGE-EVIDENCE/v0.1", evidence_core),
        "epistemic_status": "CASE_TYPED_RELATION_CANDIDATE",
        "authority": _authority(),
    }


def _binding_map(hyperedge: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(row["case"]): row for row in hyperedge.get("bindings", [])}


def _edge_commitments(core: Mapping[str, Any], *, symmetric: bool) -> tuple[str, str]:
    source_key = str(core["source_key"])
    target_key = str(core["target_key"])
    semantic_source, semantic_target = source_key, target_key
    if symmetric and target_key < source_key:
        semantic_source, semantic_target = target_key, source_key
    semantic = {
        "predicate": core["predicate"],
        "source_key": semantic_source,
        "target_key": semantic_target,
        "qualifiers": core.get("qualifiers", []),
        "symmetric": symmetric,
    }
    traversal = {
        "predicate": core["predicate"],
        "source_key": source_key,
        "target_key": target_key,
        "qualifiers": core.get("qualifiers", []),
        "symmetric": symmetric,
    }
    return (
        _commit(b"GREMLIN-RELATIONAL-EDGE-SEMANTIC/v0.1", semantic),
        _commit(b"GREMLIN-RELATIONAL-EDGE-TRAVERSAL/v0.1", traversal),
    )


def _project_one(hyperedge: Mapping[str, Any], spec: Mapping[str, Any]) -> dict[str, Any] | None:
    ports = _binding_map(hyperedge)
    source_case = str(spec["source_case"])
    target_case = str(spec["target_case"])
    source = ports.get(source_case)
    target = ports.get(target_case)
    if source is None or target is None:
        return None
    qualifier_rows = []
    for case, row in ports.items():
        if case in {source_case, target_case}:
            continue
        qualifier_rows.append(
            {
                "case": case,
                "entity": row["entity"],
                "entity_key": row["entity_key"],
                "operator_role": row["operator_role"],
            }
        )
    qualifier_rows.sort(key=lambda row: (_case_rank(row["case"]), row["entity_key"]))
    confidence = min([float(source.get("confidence", 1.0)), float(target.get("confidence", 1.0))] + [float(row.get("confidence", 1.0)) for row in ports.values()])
    core = {
        "predicate": str(spec["predicate"]),
        "inverse_predicate": str(spec["inverse_predicate"]),
        "source": source["entity"],
        "source_key": source["entity_key"],
        "source_case": source_case,
        "source_role": source["operator_role"],
        "target": target["entity"],
        "target_key": target["entity_key"],
        "target_case": target_case,
        "target_role": target["operator_role"],
        "qualifiers": qualifier_rows,
        "symmetric": bool(spec.get("symmetric", False)),
        "relation_kind": str(spec.get("relation_kind") or "PRIMARY_CASE_PROJECTION"),
        "confidence": confidence,
        "parent_hyperedge_commitment": hyperedge["semantic_frame_commitment"],
        "parent_operator": hyperedge["operator"],
    }
    semantic_commitment, traversal_commitment = _edge_commitments(core, symmetric=core["symmetric"])
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "kind": "RELATIONAL_EDGE_PROJECTION",
        **core,
        "semantic_edge_commitment": semantic_commitment,
        "traversal_commitment": traversal_commitment,
        "epistemic_status": "DERIVED_FROM_CASE_TYPED_HYPEREDGE",
        "authority": _authority(),
    }


def project_relation(relation: Mapping[str, Any]) -> dict[str, Any]:
    hyperedge = to_hyperedge(relation)
    operator = hyperedge["operator"]
    specs: list[Mapping[str, Any]] = []
    primary = PRIMARY_PROJECTIONS.get(operator)
    if primary:
        specs.append(primary)
    specs.extend(SECONDARY_PROJECTIONS.get(operator, ()))
    edges = [edge for spec in specs if (edge := _project_one(hyperedge, spec)) is not None]
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "hyperedge": hyperedge,
        "edges": edges,
        "edge_count": len(edges),
        "projection_status": "PROJECTED" if edges else "NO_BINARY_PROJECTION_AVAILABLE",
        "authority": _authority(),
    }


def invert_edge(edge: Mapping[str, Any]) -> dict[str, Any]:
    predicate = str(edge.get("predicate") or "")
    inverse_predicate = str(edge.get("inverse_predicate") or "")
    if not predicate or not inverse_predicate:
        raise ValueError("edge requires predicate and inverse_predicate")
    core = {
        "predicate": predicate if bool(edge.get("symmetric")) else inverse_predicate,
        "inverse_predicate": inverse_predicate if bool(edge.get("symmetric")) else predicate,
        "source": edge["target"],
        "source_key": edge["target_key"],
        "source_case": edge.get("target_case"),
        "source_role": edge.get("target_role"),
        "target": edge["source"],
        "target_key": edge["source_key"],
        "target_case": edge.get("source_case"),
        "target_role": edge.get("source_role"),
        "qualifiers": list(edge.get("qualifiers") or []),
        "symmetric": bool(edge.get("symmetric")),
        "relation_kind": "INVERSE_DERIVED_PROJECTION",
        "confidence": float(edge.get("confidence", 1.0)),
        "parent_hyperedge_commitment": edge.get("parent_hyperedge_commitment"),
        "parent_operator": edge.get("parent_operator"),
    }
    semantic_commitment, traversal_commitment = _edge_commitments(core, symmetric=core["symmetric"])
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "kind": "RELATIONAL_EDGE_PROJECTION",
        **core,
        "semantic_edge_commitment": semantic_commitment,
        "traversal_commitment": traversal_commitment,
        "inverse_of_traversal_commitment": edge.get("traversal_commitment"),
        "epistemic_status": "INVERSE_PROJECTION_CANDIDATE",
        "authority": _authority(),
    }


def _expand_edges(edges: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in edges:
        edge = dict(raw)
        for candidate in (edge, invert_edge(edge)):
            key = str(candidate["traversal_commitment"])
            if key in seen:
                continue
            seen.add(key)
            expanded.append(candidate)
    return expanded


def compare_edges(first: Mapping[str, Any], second: Mapping[str, Any]) -> dict[str, Any]:
    a = dict(first)
    b = dict(second)
    if a.get("semantic_edge_commitment") == b.get("semantic_edge_commitment"):
        relation = "SEMANTICALLY_EQUIVALENT_PROJECTION"
    elif invert_edge(a).get("traversal_commitment") == b.get("traversal_commitment"):
        relation = "INVERSE_EQUIVALENT_PROJECTION"
    else:
        a_nodes = {str(a.get("source_key")), str(a.get("target_key"))}
        b_nodes = {str(b.get("source_key")), str(b.get("target_key"))}
        shared = sorted((a_nodes & b_nodes) - {"None"})
        relation = "SHARED_ENTITY" if shared else "DISJOINT"
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "comparison": relation,
        "shared_entity_keys": sorted(({str(a.get("source_key")), str(a.get("target_key"))} & {str(b.get("source_key")), str(b.get("target_key"))}) - {"None"}),
        "semantic_conflict": False,
        "semantic_conflict_reason": "NO_OPERATOR_EXCLUSIVITY_RULE_APPLIED",
        "authority": _authority(),
    }


def compose_edges(first: Mapping[str, Any], second: Mapping[str, Any], *, allow_loops: bool = False) -> dict[str, Any]:
    paths: list[dict[str, Any]] = []
    seen: set[str] = set()
    for left in _expand_edges([first]):
        for right in _expand_edges([second]):
            if left["target_key"] != right["source_key"]:
                continue
            if not allow_loops and left["source_key"] == right["target_key"]:
                continue
            core = {
                "source": left["source"],
                "source_key": left["source_key"],
                "via": left["target"],
                "via_key": left["target_key"],
                "target": right["target"],
                "target_key": right["target_key"],
                "operator_sequence": [left["predicate"], right["predicate"]],
                "traversal_commitments": [left["traversal_commitment"], right["traversal_commitment"]],
                "parent_hyperedge_commitments": [left.get("parent_hyperedge_commitment"), right.get("parent_hyperedge_commitment")],
                "confidence": min(float(left.get("confidence", 1.0)), float(right.get("confidence", 1.0))),
            }
            commitment = _commit(b"GREMLIN-RELATIONAL-PATH/v0.1", core)
            if commitment in seen:
                continue
            seen.add(commitment)
            paths.append(
                {
                    "schema": SCHEMA,
                    "version": VERSION,
                    "kind": "RELATIONAL_PATH_CANDIDATE",
                    **core,
                    "depth": 2,
                    "path_commitment": commitment,
                    "epistemic_status": "COMPOSED_PROJECTION_CANDIDATE_NOT_COLLAPSED_TO_NEW_PREDICATE",
                    "authority": _authority(),
                }
            )
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "paths": paths,
        "path_count": len(paths),
        "authority": _authority(),
    }


def build_graph(relations: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    hyperedges: list[dict[str, Any]] = []
    projected: list[dict[str, Any]] = []
    edge_seen: set[str] = set()
    for relation in relations:
        projection = project_relation(relation)
        hyperedges.append(projection["hyperedge"])
        for edge in projection["edges"]:
            key = str(edge["semantic_edge_commitment"])
            if key in edge_seen:
                continue
            edge_seen.add(key)
            projected.append(edge)
    traversal_edges = _expand_edges(projected)
    node_surfaces: dict[str, set[str]] = defaultdict(set)
    for edge in traversal_edges:
        node_surfaces[str(edge["source_key"])].add(str(edge["source"]))
        node_surfaces[str(edge["target_key"])].add(str(edge["target"]))
    nodes = [
        {"entity_key": key, "surface_forms": sorted(values)}
        for key, values in sorted(node_surfaces.items())
    ]
    graph_core = {
        "hyperedge_commitments": sorted(row["semantic_frame_commitment"] for row in hyperedges),
        "edge_commitments": sorted(row["semantic_edge_commitment"] for row in projected),
        "node_keys": [row["entity_key"] for row in nodes],
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "kind": "RELATIONAL_HYPERGRAPH_WITH_BINARY_PROJECTIONS",
        "hyperedges": hyperedges,
        "projected_edges": projected,
        "traversal_edges": traversal_edges,
        "nodes": nodes,
        "hyperedge_count": len(hyperedges),
        "projected_edge_count": len(projected),
        "traversal_edge_count": len(traversal_edges),
        "graph_commitment": _commit(b"GREMLIN-RELATIONAL-GRAPH/v0.1", graph_core),
        "authority": _authority(),
    }


def find_paths(
    relations: Iterable[Mapping[str, Any]],
    *,
    source: str,
    target: str,
    max_depth: int = 3,
    max_paths: int = 32,
) -> dict[str, Any]:
    if not 1 <= int(max_depth) <= 6:
        raise ValueError("max_depth must be in [1, 6]")
    if not 1 <= int(max_paths) <= 256:
        raise ValueError("max_paths must be in [1, 256]")
    source_key = _entity_key(source)
    target_key = _entity_key(target)
    if not source_key or not target_key:
        raise ValueError("source and target must be non-empty")
    graph = build_graph(relations)
    adjacency: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for edge in graph["traversal_edges"]:
        adjacency[str(edge["source_key"])].append(edge)
    for rows in adjacency.values():
        rows.sort(key=lambda edge: (str(edge["predicate"]), str(edge["target_key"]), str(edge["traversal_commitment"])))

    queue: deque[tuple[str, list[str], list[Mapping[str, Any]]]] = deque([(source_key, [source_key], [])])
    paths: list[dict[str, Any]] = []
    while queue and len(paths) < max_paths:
        node, visited_nodes, traversed = queue.popleft()
        if len(traversed) >= max_depth:
            continue
        for edge in adjacency.get(node, []):
            next_key = str(edge["target_key"])
            if next_key in visited_nodes:
                continue
            new_edges = traversed + [edge]
            new_nodes = visited_nodes + [next_key]
            if next_key == target_key:
                core = {
                    "source_key": source_key,
                    "target_key": target_key,
                    "node_keys": new_nodes,
                    "operator_sequence": [str(row["predicate"]) for row in new_edges],
                    "traversal_commitments": [str(row["traversal_commitment"]) for row in new_edges],
                    "confidence": min(float(row.get("confidence", 1.0)) for row in new_edges),
                }
                paths.append(
                    {
                        "schema": SCHEMA,
                        "version": VERSION,
                        "kind": "RELATIONAL_PATH_CANDIDATE",
                        **core,
                        "depth": len(new_edges),
                        "path_commitment": _commit(b"GREMLIN-RELATIONAL-PATH/v0.1", core),
                        "epistemic_status": "GRAPH_PATH_CANDIDATE_NO_TRANSITIVE_SEMANTIC_CLAIM",
                        "authority": _authority(),
                    }
                )
            elif len(new_edges) < max_depth:
                queue.append((next_key, new_nodes, new_edges))
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "source": source,
        "target": target,
        "source_key": source_key,
        "target_key": target_key,
        "paths": paths,
        "path_count": len(paths),
        "max_depth": max_depth,
        "graph_commitment": graph["graph_commitment"],
        "epistemic_boundary": "PATH_EXISTENCE_DOES_NOT_IMPLY_TRANSITIVE_SEMANTIC_EQUIVALENCE",
        "authority": _authority(),
    }


def compose_all(relations: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    graph = build_graph(relations)
    edges = graph["projected_edges"]
    paths: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, left in enumerate(edges):
        for j, right in enumerate(edges):
            if i == j:
                continue
            for path in compose_edges(left, right)["paths"]:
                commitment = str(path["path_commitment"])
                if commitment in seen:
                    continue
                seen.add(commitment)
                paths.append(path)
    paths.sort(key=lambda row: (str(row["source_key"]), str(row["target_key"]), row["operator_sequence"]))
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "paths": paths,
        "path_count": len(paths),
        "graph_commitment": graph["graph_commitment"],
        "authority": _authority(),
    }


def audit_relation_set(relations: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    graph = build_graph(relations)
    frame_counts = Counter(row["semantic_frame_commitment"] for row in graph["hyperedges"])
    duplicate_frames = sorted(key for key, count in frame_counts.items() if count > 1)
    incomplete = [row["semantic_frame_commitment"] for row in graph["hyperedges"] if not row["complete"]]
    unresolved = sorted(
        {
            binding["entity"]
            for row in graph["hyperedges"]
            for binding in row["bindings"]
            if str(binding["entity"]).startswith("@")
        }
    )
    low_confidence = [
        {
            "hyperedge_commitment": row["semantic_frame_commitment"],
            "case": binding["case"],
            "entity": binding["entity"],
            "confidence": binding["confidence"],
        }
        for row in graph["hyperedges"]
        for binding in row["bindings"]
        if float(binding["confidence"]) < 0.75
    ]
    name_bindings = [
        edge
        for edge in graph["projected_edges"]
        if edge["predicate"] == "HAS_ASSIGNED_NAME"
    ]
    issues = bool(duplicate_frames or incomplete or unresolved or low_confidence)
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "STRUCTURAL_ISSUES_PRESENT" if issues else "STRUCTURALLY_CLEAN",
        "duplicate_semantic_frames": duplicate_frames,
        "incomplete_hyperedges": incomplete,
        "unresolved_surface_entities": unresolved,
        "low_confidence_bindings": low_confidence,
        "name_binding_candidates": name_bindings,
        "semantic_conflicts": [],
        "semantic_conflict_status": "NOT_INFERRED_WITHOUT_OPERATOR_EXCLUSIVITY_OR_DOMAIN_RULES",
        "graph_commitment": graph["graph_commitment"],
        "authority": _authority(),
    }


def run_algebra(
    operation: str,
    relations: Iterable[Mapping[str, Any]],
    *,
    source: str | None = None,
    target: str | None = None,
    max_depth: int = 3,
) -> dict[str, Any]:
    op = str(operation).strip().lower()
    rows = list(relations)
    if op == "graph":
        return build_graph(rows)
    if op == "compose":
        return compose_all(rows)
    if op == "audit":
        return audit_relation_set(rows)
    if op == "paths":
        if source is None or target is None:
            raise ValueError("paths operation requires source and target")
        return find_paths(rows, source=source, target=target, max_depth=max_depth)
    raise ValueError("operation must be one of: graph, compose, audit, paths")
