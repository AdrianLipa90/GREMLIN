from __future__ import annotations

import asyncio

from gremlin_mcp.core import PRODUCT_MCP_TOOLS, REFERENCE_MCP_TOOLS
from gremlin_mcp.tool_metadata import (
    CLASSIFIED_TOOLS,
    LOCAL_STATE_MUTATIONS,
    READ_ONLY_CLOSED,
    READ_ONLY_OPEN_WORLD,
    tool_annotations,
)


def test_annotation_registry_covers_every_declared_tool_exactly() -> None:
    declared = set(REFERENCE_MCP_TOOLS) | set(PRODUCT_MCP_TOOLS)
    assert CLASSIFIED_TOOLS == declared

    for name in READ_ONLY_CLOSED:
        annotation = tool_annotations(name)
        assert annotation.read_only_hint is True
        assert annotation.open_world_hint is False

    for name in READ_ONLY_OPEN_WORLD:
        annotation = tool_annotations(name)
        assert annotation.read_only_hint is True
        assert annotation.open_world_hint is True

    for name in LOCAL_STATE_MUTATIONS:
        annotation = tool_annotations(name)
        assert annotation.read_only_hint is False
        assert annotation.destructive_hint is False
        assert annotation.idempotent_hint is False
        assert annotation.open_world_hint is False


def test_reference_and_product_mcp_publish_annotations_for_all_tools() -> None:
    from mcp import Client
    from gremlin_mcp.product_server import mcp as product_mcp
    from gremlin_mcp.server import mcp as reference_mcp

    async def inspect(server, expected: set[str]) -> None:
        async with Client(server) as client:
            listed = await client.list_tools()
            by_name = {tool.name: tool for tool in listed.tools}
            assert set(by_name) == expected
            assert all(tool.annotations is not None for tool in by_name.values())

            assert by_name["gremlin_status"].annotations.read_only_hint is True
            assert by_name["gremlin_status"].annotations.open_world_hint is False
            assert by_name["gremlin_web_search"].annotations.read_only_hint is True
            assert by_name["gremlin_web_search"].annotations.open_world_hint is True
            assert by_name["gremlin_worker_enqueue"].annotations.read_only_hint is False
            assert by_name["gremlin_worker_enqueue"].annotations.destructive_hint is False

    async def exercise() -> None:
        await inspect(reference_mcp, set(REFERENCE_MCP_TOOLS))
        await inspect(product_mcp, set(PRODUCT_MCP_TOOLS))

    asyncio.run(exercise())
