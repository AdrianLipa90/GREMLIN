from __future__ import annotations

import asyncio

from gremlin_mcp.router import ROUTER_SCHEMA, auto_fanout, route
from gremlin_mcp.workers import WorkerBroker


def test_octopus_routes_dependency_graph_to_spider() -> None:
    decision = route(
        {
            "problem": "Map the dependency graph and relation topology between these nodes",
            "graph": {"nodes": ["A", "B"], "edges": [["A", "B"]]},
        },
        max_species=2,
    )
    assert decision["schema"] == ROUTER_SCHEMA
    assert decision["status"] == "ROUTE_READY"
    assert decision["route_mask"][0] == "SPIDER"
    spider = next(row for row in decision["scores"] if row["species"] == "SPIDER")
    assert spider["score"] > 0
    assert spider["evidence"]
    assert decision["authority"]["canon_allowed"] is False


def test_octopus_can_route_to_multiple_specialists() -> None:
    decision = route(
        {
            "query": "Audit evidence and provenance for this dependency graph and find contradictions",
            "sources": ["paper-a", "paper-b"],
            "dependencies": ["A->B"],
            "errors": ["claim mismatch"],
        },
        max_species=4,
        relative_cutoff=0.25,
    )
    mask = set(decision["route_mask"])
    assert {"OWL", "SPIDER", "HOUND"} <= mask


def test_octopus_polish_stem_cues_are_normalized() -> None:
    decision = route({"query": "Wyprowadz rownanie i dowod, potem oblicz parametry"})
    assert decision["route_mask"][0] == "MOLE"


def test_octopus_no_evidence_fails_closed_without_queueing() -> None:
    broker = WorkerBroker()
    result = auto_fanout(broker, {"text": "hello world"}, request_id="no-route")
    assert result["status"] == "NO_CONFIDENT_ROUTE_NOT_QUEUED"
    assert result["route_mask"] == []
    assert result["tasks"] == []
    queue = broker.queue_status()
    assert sum(states["QUEUED"] for states in queue["tasks"].values()) == 0


def test_octopus_route_commitment_is_deterministic() -> None:
    payload = {"query": "find duplicate redundant branches and prune them", "duplicates": ["a", "a"]}
    a = route(payload)
    b = route(payload)
    assert a["route_mask"] == b["route_mask"]
    assert a["route_commitment"] == b["route_commitment"]
    assert a["route_mask"][0] == "MANTIS"


def test_auto_fanout_binds_route_commitment_into_worker_task_lineage() -> None:
    broker = WorkerBroker()
    result = auto_fanout(
        broker,
        {"query": "inspect the equation and derive the formula"},
        request_id="auto-mole",
        max_species=1,
    )
    assert result["status"] == "AUTO_FANOUT_QUEUED"
    assert result["route_mask"] == ["MOLE"]
    fanout = result["fanout"]
    assert fanout["route_context"]["route_commitment"] == result["route_commitment"]
    task = broker.claim(
        broker.register_worker("mole-router-test", ["MOLE"])["worker_id"],
        species="MOLE",
        limit=1,
    )["tasks"][0]
    assert task["payload"]["route_context"]["route_commitment"] == result["route_commitment"]
    assert task["payload"]["route_context"]["route_mask"] == ["MOLE"]


def test_mcp_discovery_exposes_octopus_tools() -> None:
    from mcp import Client
    from gremlin_mcp.server import mcp

    async def exercise() -> None:
        async with Client(mcp) as client:
            listed = await client.list_tools()
            names = {tool.name for tool in listed.tools}
            assert {"gremlin_route", "gremlin_auto_fanout"} <= names
            routed = await client.call_tool(
                "gremlin_route",
                {"payload": {"query": "audit evidence provenance and citations"}},
            )
            assert routed.is_error is False

    asyncio.run(exercise())
