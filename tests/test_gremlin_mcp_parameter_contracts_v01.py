from __future__ import annotations

import asyncio


def _input_schema(tool) -> dict:
    raw = tool.model_dump(by_alias=True, exclude_none=True)
    schema = raw.get("inputSchema")
    assert isinstance(schema, dict), (tool.name, raw)
    return schema


def _property(tool, name: str) -> dict:
    schema = _input_schema(tool)
    properties = schema.get("properties")
    assert isinstance(properties, dict)
    value = properties.get(name)
    assert isinstance(value, dict), (tool.name, name, schema)
    return value


def test_mcp_json_schema_exposes_existing_runtime_bounds() -> None:
    from mcp import Client
    from gremlin_mcp.server import mcp

    async def exercise() -> None:
        async with Client(mcp) as client:
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}

        route = tools["gremlin_route"]
        max_species = _property(route, "max_species")
        assert max_species["minimum"] == 1
        assert max_species["maximum"] == 7
        assert _property(route, "min_score")["exclusiveMinimum"] == 0.0
        cutoff = _property(route, "relative_cutoff")
        assert cutoff["exclusiveMinimum"] == 0.0
        assert cutoff["maximum"] == 1.0

        fetch = tools["gremlin_web_fetch"]
        timeout = _property(fetch, "timeout_s")
        assert timeout["minimum"] == 0.1
        assert timeout["maximum"] == 60.0
        max_bytes = _property(fetch, "max_bytes")
        assert max_bytes["minimum"] == 1
        assert max_bytes["maximum"] == 8_000_000

        search = tools["gremlin_web_search"]
        per_provider = _property(search, "limit_per_provider")
        assert per_provider["minimum"] == 1
        assert per_provider["maximum"] == 25

        execute = tools["gremlin_research_execute"]
        max_sources = _property(execute, "max_sources")
        assert max_sources["minimum"] == 1
        assert max_sources["maximum"] == 50

        plan = tools["gremlin_plan"]
        assert _property(plan, "vector_width")["minimum"] == 1
        route_counts = _property(plan, "route_counts")
        values = route_counts.get("additionalProperties")
        assert isinstance(values, dict)
        assert values["minimum"] == 0

        register = tools["gremlin_worker_register"]
        worker_id = _property(register, "worker_id")
        assert worker_id["minLength"] == 1
        assert worker_id["maxLength"] == 128
        species = _property(register, "species")
        assert species["minItems"] == 1
        vector_width = _property(register, "vector_width")
        assert vector_width["minimum"] == 1
        assert vector_width["maximum"] == 1024
        max_batch = _property(register, "max_batch")
        assert max_batch["minimum"] == 1
        assert max_batch["maximum"] == 128

        claim = tools["gremlin_worker_claim"]
        limit = _property(claim, "limit")
        # Optional Annotated scalar is represented through anyOf.
        limit_variants = limit.get("anyOf")
        if isinstance(limit_variants, list):
            numeric = next(row for row in limit_variants if row.get("type") == "integer")
        else:
            numeric = limit
        assert numeric["minimum"] == 1
        lease = _property(claim, "lease_seconds")
        lease_variants = lease.get("anyOf")
        if isinstance(lease_variants, list):
            lease_numeric = next(row for row in lease_variants if row.get("type") == "integer")
        else:
            lease_numeric = lease
        assert lease_numeric["minimum"] == 1
        assert lease_numeric["maximum"] == 300

        collect = tools["gremlin_collect"]
        task_ids = _property(collect, "task_ids")
        assert task_ids["minItems"] == 1
        assert task_ids["items"]["minLength"] == 1
        assert task_ids["items"]["maxLength"] == 128

    asyncio.run(exercise())


def test_product_and_reference_parameter_schemas_remain_exact() -> None:
    from mcp import Client
    from gremlin_mcp.product_server import mcp as product_mcp
    from gremlin_mcp.server import mcp as reference_mcp

    async def exercise() -> None:
        async with Client(reference_mcp) as client:
            reference = {tool.name: tool for tool in (await client.list_tools()).tools}
        async with Client(product_mcp) as client:
            product = {tool.name: tool for tool in (await client.list_tools()).tools}

        shared = set(reference) & set(product)
        assert len(shared) == 27
        for name in sorted(shared):
            assert _input_schema(reference[name]) == _input_schema(product[name]), name

    asyncio.run(exercise())
