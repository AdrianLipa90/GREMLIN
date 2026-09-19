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
        "FOX",
        "BEAVER",
        "BAT",
        "CANARY",
        "SERPENT",
        "CHAMELEON",
        "BELZEBUB",
        "FERRET",
        "GREMLIN",
    } <= names
    assert species_profile("belzebub")["scheduler_profile"]["mass"] == 2.60
    assert species_profile("octopus")["scheduler_profile"] is None
    ferret = species_profile("ferret")
    assert ferret["stage"] == "actuation"
    assert ferret["scheduler_profile"] is None


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
            declared_status = status()
            declared = set(declared_status["tools"])
            grouped = {
                tool
                for tools in declared_status["tool_groups"].values()
                for tool in tools
            }
            assert names == declared
            assert grouped == declared
            assert declared_status["tool_count"] == len(names) == 32
            assert {
                "gremlin_status",
                "gremlin_bestiary",
                "gremlin_species",
                "gremlin_plan",
                "gremlin_relation_parse",
                "gremlin_relation_signature",
                "gremlin_research_hound_provenance",
                "gremlin_research_guarded",
                "gremlin_research_relational",
                "gremlin_prototype",
                "gremlin_phasenav_status",
                "gremlin_phasenav_reference_sweep",
                "gremlin_phasenav_threeway",
                "gremlin_phasenav_analog_invariants",
                "gremlin_phasenav_live_replay",
            } <= names
            result = await client.call_tool("gremlin_status", {})
            assert result.is_error is False

    asyncio.run(exercise())

def test_standalone_phasenav_runtime_import_surface_is_complete() -> None:
    from gremlin_mcp.phasenav_runtime import analog_invariants, reference_sweep, status, threeway

    s = status()
    assert s["standalone"] is True
    assert s["live_noema_required_for_core"] is False
    assert s["species_count"] == 18
    assert set(s["species"]) >= {"FOX", "BEAVER", "BAT", "CANARY", "SERPENT", "CHAMELEON"}
    assert s["vector_backend_available"] is True

    sweep = reference_sweep()
    assert sweep["species_count"] == 18
    assert sweep["external_effects"] is False
    assert sweep["canon_allowed"] is False

    tri = threeway(batch_size=4, horizon=0.2, coarse_steps=4, fine_steps=16, rk4_substeps=64)
    assert tri["summary"]["species_count"] == 18
    assert tri["summary"]["all_species_pass"] is True
    assert tri["summary"]["physical_analog_claim"] is False

    inv = analog_invariants()
    assert inv["summary"]["all_analog_core_specialist_invariants_pass"] is True
    assert inv["summary"]["passed"] == 9
