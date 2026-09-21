"""GREMLIN fundamental-repository dependency overlay v0.1.

Dependency-free parser/auditor for the canonical FPDG one-line YAML node/edge
records. The tool is intentionally read-only: it maps repository topology,
cross-repository seams, and high-impact unresolved frontier roots. It does not
promote claims or infer physical truth from graph connectivity.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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


def analyze(nodes: dict[str, ClaimNode], edges: Iterable[tuple[str, str]]) -> dict[str, object]:
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

    frontier_roots = [
        row for row in frontier if not row["frontier_parents"]
    ]

    represented_repositories = sorted(repo_counts)
    return {
        "schema": "GREMLIN_FUNDAMENTAL_REPO_OVERLAY_V0_1",
        "authority": "CANDIDATE_AUDIT_ONLY",
        "promotion_allowed": False,
        "node_count": len(nodes),
        "edge_count": len(edge_list),
        "repository_node_counts": dict(sorted(repo_counts.items())),
        "cross_repository_edge_counts": dict(sorted(cross_counts.items())),
        "cross_repository_edges": cross_edges,
        "frontier_count": len(frontier),
        "frontier_root_count": len(frontier_roots),
        "frontier_roots": frontier_roots,
        "high_impact_frontier": frontier[:20],
        "represented_repositories": represented_repositories,
        "interpretation_firewall": {
            "graph_connectivity_is_not_proof": True,
            "conditional_or_open_nodes_are_not_promoted": True,
            "missing_repository_is_an_integration_gap_not_a_mathematical_refutation": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("graph", type=Path, help="Path to FPDG dependency_graph.yaml")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    nodes, edges = parse_graph(args.graph.read_text(encoding="utf-8"))
    result = analyze(nodes, edges)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
