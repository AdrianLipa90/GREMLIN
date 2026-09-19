from __future__ import annotations

import asyncio

from gremlin_mcp.core import PRODUCT_MCP_TOOLS, REFERENCE_MCP_TOOLS, status
from gremlin_mcp.tool_catalog import TOOL_DESCRIPTIONS, catalog_manifest, tool_description, tool_title


PRODUCT_ONLY = {
    "gremlin_product_status",
    "gremlin_license_status",
}

REFERENCE_ONLY = {
    "gremlin_phasenav_status",
    "gremlin_phasenav_reference_sweep",
    "gremlin_phasenav_threeway",
    "gremlin_phasenav_analog_invariants",
    "gremlin_phasenav_live_replay",
}


def _tool_contract(tool) -> dict:
    raw = tool.model_dump(by_alias=True, exclude_none=True)
    return {
        "title": raw.get("title"),
        "description": raw.get("description"),
        "inputSchema": raw.get("inputSchema"),
        "outputSchema": raw.get("outputSchema"),
        "annotations": raw.get("annotations"),
    }


def test_tool_catalog_covers_every_declared_tool_exactly() -> None:
    declared = set(REFERENCE_MCP_TOOLS) | set(PRODUCT_MCP_TOOLS)
    assert len(declared) == 34
    assert set(TOOL_DESCRIPTIONS) == declared

    manifest = catalog_manifest()
    assert manifest["tool_count"] == 34
    assert set(manifest["tools"]) == declared

    for name in sorted(declared):
        title = tool_title(name)
        description = tool_description(name)
        assert title.startswith("GREMLIN · ")
        assert len(title) > len("GREMLIN · ")
        assert description.strip()
        assert manifest["tools"][name] == {
            "title": title,
            "description": description,
        }


def test_declared_surface_difference_is_exact_and_intentional() -> None:
    reference = set(REFERENCE_MCP_TOOLS)
    product = set(PRODUCT_MCP_TOOLS)
    shared = reference & product

    assert len(reference) == 32
    assert len(product) == 29
    assert len(shared) == 27
    assert product - reference == PRODUCT_ONLY
    assert reference - product == REFERENCE_ONLY


def test_shared_reference_product_tool_contracts_are_exact() -> None:
    from mcp import Client
    from gremlin_mcp.product_server import mcp as product_mcp
    from gremlin_mcp.server import mcp as reference_mcp

    async def exercise() -> None:
        async with Client(reference_mcp) as client:
            reference = {
                tool.name: tool
                for tool in (await client.list_tools()).tools
            }
        async with Client(product_mcp) as client:
            product = {
                tool.name: tool
                for tool in (await client.list_tools()).tools
            }

        assert set(reference) == set(REFERENCE_MCP_TOOLS)
        assert set(product) == set(PRODUCT_MCP_TOOLS)

        shared = set(reference) & set(product)
        assert len(shared) == 27
        for name in sorted(shared):
            expected = {
                "title": tool_title(name),
                "description": tool_description(name),
            }
            assert reference[name].title == expected["title"], name
            assert reference[name].description == expected["description"], name
            assert product[name].title == expected["title"], name
            assert product[name].description == expected["description"], name
            assert _tool_contract(reference[name]) == _tool_contract(product[name]), name

    asyncio.run(exercise())


def test_status_publishes_exact_correlation_error_contract() -> None:
    for surface in ("reference", "product"):
        contract = status(surface=surface)["error_contract"]
        assert contract["schema"] == "GREMLIN_MCP_ERROR_V0_1"
        assert contract["protocol_semantics"] == "MCP_TOOL_ERROR_IS_ERROR_TRUE"
        assert contract["request_id_policy"] == "CALLER_OR_GENERATED_NONEMPTY"
        assert contract["fields"] == [
            "error_code",
            "detail_code",
            "category",
            "retryable",
            "user_action",
            "request_id",
            "request_id_source",
        ]
