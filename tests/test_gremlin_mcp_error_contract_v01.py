from __future__ import annotations

import asyncio
import json

from gremlin_mcp.error_contract import SCHEMA, error_envelope
from gremlin_mcp.product.gate import ProductAuthorizationError


def _result_text(result) -> str:
    return "\n".join(
        str(getattr(item, "text", ""))
        for item in getattr(result, "content", [])
        if getattr(item, "text", None) is not None
    )


def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    assert start >= 0 and end > start, text
    return json.loads(text[start : end + 1])


def test_authorization_error_envelope_is_actionable_and_fail_closed() -> None:
    payload = error_envelope(
        ProductAuthorizationError("LICENSE_REQUIRED"),
        tool="gremlin_route",
        request_id="req-1",
    )
    assert payload["schema"] == SCHEMA
    assert payload["status"] == "ERROR"
    assert payload["error_code"] == "LICENSE_REQUIRED"
    assert payload["category"] == "AUTHORIZATION"
    assert payload["retryable"] is False
    assert payload["request_id"] == "req-1"
    assert "Activate" in payload["user_action"]
    assert payload["authority"]["production_runtime_write"] is False
    assert payload["authority"]["execution_admitted"] is False
    assert payload["authority"]["canon_allowed"] is False


def test_reference_mcp_error_remains_protocol_error_with_machine_readable_body() -> None:
    from mcp import Client
    from gremlin_mcp.server import mcp

    async def exercise() -> None:
        async with Client(mcp) as client:
            result = await client.call_tool("gremlin_species", {"species": "NOT_A_GREMLIN_SPECIES"})
            assert result.is_error is True
            payload = _extract_json(_result_text(result))
            assert payload["schema"] == SCHEMA
            assert payload["tool"] == "gremlin_species"
            assert payload["error_code"] == "INVALID_REQUEST"
            assert payload["category"] == "REQUEST"
            assert payload["retryable"] is False
            assert payload["authority"]["execution_admitted"] is False

    asyncio.run(exercise())
