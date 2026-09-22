"""GREMLIN fundamental-repository dependency overlay v0.1.

Dependency-free parser/auditor for the canonical FPDG one-line YAML node/edge
records. An optional candidate overlay may be supplied for GREMLIN-only second
passes. Candidate overlay data never mutates the source graph and never
promotes a claim.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

NODE_RE = re.compile(
    r'claim_id:\s*"(?P<id>[^"]+)".*?repository:\s*(?P<repo>[^,}]+).*?status:\s*"(?P<status>[^"]+)"'
)
EDGE_RE = re.compile(r'from:\s*"(?P<from>[^"]+)".*?to:\s*"(?P<to>[^"]+)"')

FRONTIER_TOKENS = (
    "OPEN",
    "FRONTIER",
    "CANDIDATE",
    "CONDITIONAL",
    "NEXT",
    "INPUT",
    "TARGET",
    "PENDING",
    "REQUIRED",
    "ACTIVE_RECONCILIATION",
    "SOURCE_BINDING",
    "UNFIXED",
    "SCALE_SOLVE",
    "DOWNSTREAM_TARGET",
    "JOINT_TARGET",
)


@dataclass(frozen=True)
class ClaimNode:
    claim_id: str
    repository: str
    status: str


def parse_graph(text: str) -> tuple[dict[str, ClaimNode], list[tuple[str, str]]]:
    nodes: dict[str, ClaimNode] = {}
    edges: list[tuple[str, str]] = []
    for line in text.splitlines():
        node_match = NODE_RE.search(line)
        if node_match:
            node = ClaimNode(
                claim_id=node_match.group("id"),
                repository=node_match.group("repo").strip(),
                status=node_match.group("status").strip(),
            )
            nodes[node.claim_id] = node
        edge_match = EDGE_RE.search(line)
        if edge_match:
            edges.append((edge_match.group("from"), edge_match.group("to")))
    return nodes, edges


def apply_candidate_overlay(
    nodes: Mapping[str, ClaimNode],
    edges: Iterable[tuple[str, str]],
    overlay: Mapping[str, object],
) -> tuple[dict[str, ClaimNode], list[tuple[str, str]]]:
    """Return a copy of the graph with a non-canonical candidate overlay.

    Overlay nodes must be new claim IDs. This prevents a GREMLIN candidate from
    silently replacing a canonical claim. Every overlay edge endpoint must
    exist after candidate nodes are added.
    """

    if overlay.get("authority") != "CANDIDATE_ONLY":
        raise ValueError("candidate overlay must declare authority=CANDIDATE_ONLY")
    if overlay.get("canon_allowed") is not False:
        raise ValueError("candidate overlay must declare canon_allowed=false")

    merged_nodes = dict(nodes)
    merged_edges = list(edges)

    raw_nodes = overlay.get("nodes", [])
    raw_edges = overlay.get("edges", [])
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        raise ValueError("candidate overlay nodes and edges must be arrays")

    for raw in raw_nodes:
        if not isinstance(raw, Mapping):
            raise ValueError("candidate node must be an object")
        claim_id = str(raw.get("claim_id", "")).strip()
        repository = str(raw.get("repository", "")).strip()
        status = str(raw.get("status", "")).strip()
        if not claim_id or not repository or not status:
            raise ValueError("candidate node requires claim_id, repository and status")
        if claim_id in merged_nodes:
            raise ValueError(f"candidate overlay cannot replace canonical claim: {claim_id}")
        merged_nodes[claim_id] = ClaimNode(claim_id, repository, status)

    known = set(merged_nodes)
    for raw in raw_edges:
        if not isinstance(raw, Mapping):
            raise ValueError("candidate edge must be an object")
        source = str(raw.get("from", "")).strip()
        target = str(raw.get("to", "")).strip()
        if source not in known or target not in known:
            raise ValueError(f"candidate edge has unknown endpoint: {source} -> {target}")
        edge = (source, target)
        if edge not in merged_edges:
            merged_edges.append(edge)

    return merged_nodes, merged_edges


def is_frontier(status: str) -> bool:
    upper = status.upper()
    return any(token in upper for token in FRONTIER_TOKENS)


def descendants(start: str, adjacency: dict[str, list[str]]) -> set[str]:
    seen: set[str] = set()
    stack = [start]
    while stack:
        current = stack.pop()
        for nxt in adjacency.get(current, []):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def nontrivial_sccs(
    nodes: Mapping[str, ClaimNode],
    adjacency: Mapping[str, list[str]],
) -> list[list[str]]:
    """Tarjan SCC scan; only cycles/components of size > 1 are returned."""

    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    components: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for nxt in adjacency.get(node, []):
            if nxt not in indices:
                visit(nxt)
                lowlinks[node] = min(lowlinks[node], lowlinks[nxt])
            elif nxt in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[nxt])

        if lowlinks[node] == indices[node]:
            component: list[str] = []
            while True:
                current = stack.pop()
                on_stack.remove(current)
                component.append(current)
                if current == node:
                    break
            if len(component) > 1:
                components.append(sorted(component))

    for node in nodes:
        if node not in indices:
            visit(node)
    return sorted(components, key=lambda component: (-len(component), component))


def analyze(
    nodes: dict[str, ClaimNode],
    edges: Iterable[tuple[str, str]],
    *,
    candidate_overlay_applied: bool = False,
) -> dict[str, object]:
    edge_list = list(edges)
    adjacency: dict[str, list[str]] = defaultdict(list)
    incoming: dict[str, list[str]] = defaultdict(list)
    repo_counts: dict[str, int] = defaultdict(int)
    cross_counts: dict[str, int] = defaultdict(int)
    cross_edges: list[dict[str, str]] = []

    for node in nodes.values():
        repo_counts[node.repository] += 1

    for source, target in edge_list:
        adjacency[source].append(target)
        incoming[target].append(source)
        source_repo = nodes.get(source, ClaimNode(source, "UNKNOWN", "")).repository
        target_repo = nodes.get(target, ClaimNode(target, "UNKNOWN", "")).repository
        if source_repo != target_repo:
            cross_counts[f"{source_repo}->{target_repo}"] += 1
            cross_edges.append(
                {
                    "from": source,
                    "to": target,
                    "from_repository": source_repo,
                    "to_repository": target_repo,
                }
            )

    frontier_ids = {node.claim_id for node in nodes.values() if is_frontier(node.status)}
    frontier = []
    for claim_id in frontier_ids:
        node = nodes[claim_id]
        frontier.append(
            {
                "claim_id": claim_id,
                "repository": node.repository,
                "status": node.status,
                "downstream_count": len(descendants(claim_id, adjacency)),
                "frontier_parents": sorted(
                    parent for parent in incoming.get(claim_id, []) if parent in frontier_ids
                ),
                "parents": sorted(incoming.get(claim_id, [])),
            }
        )
    frontier.sort(key=lambda row: (-row["downstream_count"], row["claim_id"]))
    frontier_roots = [row for row in frontier if not row["frontier_parents"]]
    cycles = nontrivial_sccs(nodes, adjacency)

    return {
        "schema": "GREMLIN_FUNDAMENTAL_REPO_OVERLAY_V0_1",
        "authority": "CANDIDATE_AUDIT_ONLY",
        "promotion_allowed": False,
        "candidate_overlay_applied": candidate_overlay_applied,
        "node_count": len(nodes),
        "edge_count": len(edge_list),
        "repository_node_counts": dict(sorted(repo_counts.items())),
        "cross_repository_edge_counts": dict(sorted(cross_counts.items())),
        "cross_repository_edges": cross_edges,
        "frontier_count": len(frontier),
        "frontier_root_count": len(frontier_roots),
        "frontier_roots": frontier_roots,
        "high_impact_frontier": frontier[:20],
        "nontrivial_scc_count": len(cycles),
        "nontrivial_sccs": cycles,
        "represented_repositories": sorted(repo_counts),
        "interpretation_firewall": {
            "graph_connectivity_is_not_proof": True,
            "conditional_or_open_nodes_are_not_promoted": True,
            "missing_repository_is_an_integration_gap_not_a_mathematical_refutation": True,
            "candidate_overlay_is_not_canon": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("graph", type=Path, help="Path to FPDG dependency_graph.yaml")
    parser.add_argument(
        "--candidate-overlay",
        type=Path,
        help="Optional GREMLIN-only candidate overlay JSON; never mutates FPDG",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    nodes, edges = parse_graph(args.graph.read_text(encoding="utf-8"))
    overlay_applied = False
    if args.candidate_overlay:
        overlay = json.loads(args.candidate_overlay.read_text(encoding="utf-8"))
        nodes, edges = apply_candidate_overlay(nodes, edges, overlay)
        overlay_applied = True

    result = analyze(nodes, edges, candidate_overlay_applied=overlay_applied)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
