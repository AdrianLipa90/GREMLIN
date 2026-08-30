from __future__ import annotations

import asyncio

from gremlin_mcp.core import bestiary_manifest, plan_bestiary, species_profile, status


def test_standalone_status_is_fail_closed() -> None:
    s = status()
    assert s["standalone"] is True
    assert s["noema_required"] is False
    assert s["authority"] == {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def test_bestiary_manifest_contains_full_topology() -> None:
    manifest = bestiary_manifest()
    names = {item["name"] for item in manifest["species"]}
    assert {
        "HUMMINGBIRD",
        "OCTOPUS",
        "SPIDER",
        "RAVEN",
        "HOUND",
        "MOLE",
        "OWL",
        "ANT",
        "MANTIS",
        "BELZEBUB",
        "GREMLIN",
    } <= names
    assert species_profile("belzebub")["scheduler_profile"]["mass"] == 2.60
    assert species_profile("octopus")["scheduler_profile"] is None


def test_vector_lane_plan_is_deterministic_and_compressed() -> None:
    counts = {
        "SPIDER": 64,
        "RAVEN": 64,
        "HOUND": 64,
        "MOLE": 64,
        "OWL": 64,
        "ANT": 64,
        "MANTIS": 64,
        "BELZEBUB": 64,
    }
    a = plan_bestiary(counts, vector_width=8)
    b = plan_bestiary(counts, vector_width=8)
    assert a == b
    assert a["dispatch_compression"] > 1.0
    assert all(item["lane_width"] > 0 for item in a["plan"])


def test_mcp_in_process_handshake_and_status_tool() -> None:
    from mcp import Client
    from gremlin_mcp.server import mcp

    async def exercise() -> None:
        async with Client(mcp) as client:
            listed = await client.list_tools()
            names = {tool.name for tool in listed.tools}
            assert {
                "gremlin_status",
                "gremlin_bestiary",
                "gremlin_species",
                "gremlin_plan",
                "gremlin_relation_parse",
                "gremlin_relation_signature",
                "gremlin_research_relational",
                "gremlin_prototype",
            } <= names
            result = await client.call_tool("gremlin_status", {})
            assert result.is_error is False

    asyncio.run(exercise())
