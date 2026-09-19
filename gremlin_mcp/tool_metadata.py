from __future__ import annotations

from mcp.types import ToolAnnotations

READ_ONLY_CLOSED = frozenset({
    "gremlin_product_status",
    "gremlin_license_status",
    "gremlin_status",
    "gremlin_bestiary",
    "gremlin_species",
    "gremlin_plan",
    "gremlin_route",
    "gremlin_relation_parse",
    "gremlin_relation_signature",
    "gremlin_collect",
    "gremlin_prototype",
    "gremlin_phasenav_status",
    "gremlin_phasenav_reference_sweep",
    "gremlin_phasenav_threeway",
    "gremlin_phasenav_analog_invariants",
    "gremlin_phasenav_live_replay",
    "gremlin_worker_list",
    "gremlin_worker_result",
    "gremlin_worker_queue",
})

READ_ONLY_OPEN_WORLD = frozenset({
    "gremlin_web_fetch",
    "gremlin_web_search",
    "gremlin_research",
    "gremlin_research_execute",
    "gremlin_research_hound_provenance",
    "gremlin_research_guarded",
    "gremlin_research_relational",
})

LOCAL_STATE_MUTATIONS = frozenset({
    "gremlin_auto_fanout",
    "gremlin_fanout",
    "gremlin_synthesize",
    "gremlin_worker_register",
    "gremlin_worker_heartbeat",
    "gremlin_worker_enqueue",
    "gremlin_worker_claim",
    "gremlin_worker_submit",
})

CLASSIFIED_TOOLS = READ_ONLY_CLOSED | READ_ONLY_OPEN_WORLD | LOCAL_STATE_MUTATIONS


def tool_annotations(tool: str) -> ToolAnnotations:
    if not isinstance(tool, str) or not tool.strip():
        raise ValueError("tool must be a non-empty string")
    name = tool.strip()
    if name in READ_ONLY_CLOSED:
        return ToolAnnotations(read_only_hint=True, open_world_hint=False)
    if name in READ_ONLY_OPEN_WORLD:
        return ToolAnnotations(read_only_hint=True, open_world_hint=True)
    if name in LOCAL_STATE_MUTATIONS:
        return ToolAnnotations(
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=False,
        )
    raise ValueError(f"unclassified MCP tool annotations: {name}")
