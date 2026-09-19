from __future__ import annotations

from typing import Final

SCHEMA: Final = "GREMLIN_MCP_TOOL_CATALOG_V0_1"

TOOL_DESCRIPTIONS: dict[str, str] = {
    "gremlin_product_status": "Return sanitized product/license/profile state without customer secrets.",
    "gremlin_license_status": "Alias for the sanitized licensed-product state.",
    "gremlin_status": "Return MCP mode, capabilities, topology and fail-closed authority state.",
    "gremlin_bestiary": "List GREMLIN animals, their roles, scheduler mass/orbit and cadence data.",
    "gremlin_species": "Inspect one GREMLIN animal by name, for example SPIDER, OWL or BELZEBUB.",
    "gremlin_plan": "Build a deterministic mass-orbit/vector-lane execution plan for routed work.",
    "gremlin_route": "Ask OCTOPUS for an auditable deterministic semantic specialist route mask.",
    "gremlin_relation_parse": "Parse bounded Polish relation frames into grammatical case ports and operator-local roles.",
    "gremlin_relation_signature": "Return required/optional grammatical ports and operator-local roles for a relation operator.",
    "gremlin_web_fetch": "Fetch one public HTTPS text/JSON/XML resource with SSRF firewall and provenance receipt.",
    "gremlin_web_search": "Search bounded public internet providers and return deduplicated candidate evidence.",
    "gremlin_research": "Run OCTOPUS routing plus bounded internet evidence acquisition for a research query.",
    "gremlin_research_execute": "Acquire internet evidence, execute staged Bestiary reference workers and synthesize a candidate.",
    "gremlin_research_hound_provenance": "Execute research and bind HOUND duplicate/version auditing to canonical source-family provenance.",
    "gremlin_research_guarded": "Execute research and quarantine synthesis when explicit typed claim evidence conflicts.",
    "gremlin_research_relational": "Execute internet research and propagate case-typed relation frames into Bestiary synthesis.",
    "gremlin_auto_fanout": "Route with OCTOPUS and queue work only when positive semantic evidence is present.",
    "gremlin_fanout": "Queue one payload to an explicit caller-supplied specialist route mask.",
    "gremlin_collect": "Collect current states and CANDIDATE outputs for a specialist fanout.",
    "gremlin_synthesize": "Queue BELZEBUB synthesis after every supplied specialist task is DONE.",
    "gremlin_prototype": "Run GREMLIN's existing reference candidate -> PhaseNav IR -> prototype -> test pipeline.",
    "gremlin_phasenav_status": "Return the standalone 36D PhaseNav Bestiary runtime/import surface.",
    "gremlin_phasenav_reference_sweep": "Run all current Bestiary species through the standalone reference phase layer.",
    "gremlin_phasenav_threeway": "Compare scalar, NumPy-vector and continuous T^36 realizations.",
    "gremlin_phasenav_analog_invariants": "Run specialist invariants for all current analog-core Bestiary candidates.",
    "gremlin_phasenav_live_replay": "Replay all species against an explicit live PhaseNav surface; no fallback.",
    "gremlin_worker_register": "Register or refresh an external backend as one or more GREMLIN animal workers.",
    "gremlin_worker_heartbeat": "Refresh a registered GREMLIN worker heartbeat.",
    "gremlin_worker_list": "List currently registered external GREMLIN animal workers.",
    "gremlin_worker_enqueue": "Queue one JSON task for a scheduler-backed GREMLIN animal worker.",
    "gremlin_worker_claim": "Claim one bounded same-species batch using GREMLIN orbit/vector lane limits.",
    "gremlin_worker_submit": "Submit exact lease results; the MCP envelope remains CANDIDATE and fail-closed.",
    "gremlin_worker_result": "Read current state or candidate output for one GREMLIN worker task.",
    "gremlin_worker_queue": "Return per-species queue counts, active leases and persistence scope.",
}

_TOKEN_CASE = {
    "mcp": "MCP",
    "phasenav": "PhaseNav",
    "web": "Web",
}


def tool_description(tool: str) -> str:
    if not isinstance(tool, str) or not tool.strip():
        raise ValueError("tool must be a non-empty string")
    name = tool.strip()
    try:
        return TOOL_DESCRIPTIONS[name]
    except KeyError as exc:
        raise ValueError(f"unclassified MCP tool description: {name}") from exc


def tool_title(tool: str) -> str:
    if tool not in TOOL_DESCRIPTIONS:
        raise ValueError(f"unclassified MCP tool title: {tool}")
    stem = tool.removeprefix("gremlin_")
    words = [
        _TOKEN_CASE.get(token, token.replace("-", " ").title())
        for token in stem.split("_")
    ]
    return "GREMLIN · " + " ".join(words)


def catalog_manifest() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "tool_count": len(TOOL_DESCRIPTIONS),
        "tools": {
            name: {
                "title": tool_title(name),
                "description": description,
            }
            for name, description in sorted(TOOL_DESCRIPTIONS.items())
        },
    }
