from __future__ import annotations

from gremlin_mcp.hive_authority import HiveAuthorityRuntime
from gremlin_mcp.memory_capabilities import authorize_memory_requests
from gremlin_mcp.memory_exchange import ingest_exchange_envelope, validate_exchange_envelope
from gremlin_mcp.semantic_graph_bestiary import build_bestiary_handoff, build_hive_exchange_candidate
from gremlin_mcp.semantic_graph_transformer import compile_semantic_graph


def test_sgt_uses_actual_bestiary_capability_policy() -> None:
    compiled = compile_semantic_graph(["alpha causes beta. beta depends on gamma."])
    task_id = "sgt-policy-integration"
    out = build_bestiary_handoff(
        compiled,
        subject_id="sgt:alpha",
        generation_id="gen-001",
        task_id=task_id,
        authorize=lambda role, requests: authorize_memory_requests(role, requests, task_id=task_id),
    )
    assert [stage["role"] for stage in out["stages"]] == ["SPIDER", "ELEPHANT", "BEES"]
    assert all(stage["authorization"]["claims"]["all_requests_allowed"] for stage in out["stages"])
    assert all(stage["authorization"]["canon_allowed"] is False for stage in out["stages"])


def test_sgt_exchange_packet_roundtrips_through_actual_hive_protocol() -> None:
    compiled = compile_semantic_graph(["alpha causes beta. beta supports gamma."])
    packet = build_hive_exchange_candidate(compiled, subject_id="sgt:alpha", generation_id="gen-001")
    normalized = validate_exchange_envelope(packet)
    assert normalized["payload_sha256"] == packet["payload_sha256"]
    runtime = HiveAuthorityRuntime()
    try:
        result = ingest_exchange_envelope(runtime, packet)
        assert result["status"] == "INGESTED"
        assert result["automatic_latch"] is False
        assert result["canon_allowed"] is False
        assert result["hive_subject_id"].startswith("exchange:px:")
    finally:
        runtime.close()
