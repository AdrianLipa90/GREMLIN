from __future__ import annotations

import argparse
import ipaddress
import os
from typing import Any

from mcp.server import MCPServer

from gremlin_mcp import __version__
from gremlin_mcp.core import bestiary_manifest, plan_bestiary, run_prototype, species_profile, status
from gremlin_mcp.error_contract import mcp_error_boundary
from gremlin_mcp.tool_metadata import tool_annotations
from gremlin_mcp.tool_catalog import tool_description, tool_title
from gremlin_mcp.tool_types import (
    NonEmptyStringList,
    NonNegativeRouteCount,
    PlanVectorWidth,
    ProviderLimit,
    RequestId,
    ResearchMaxSources,
    RouteMaxSpecies,
    RouteMinScore,
    RouteRelativeCutoff,
    WebMaxBytes,
    WebTimeoutSeconds,
    WorkerClaimLimit,
    WorkerIdentifier,
    WorkerIdentifierList,
    WorkerLeaseSeconds,
    WorkerMaxBatch,
    WorkerVectorWidth,
)
from gremlin_mcp.guarded_research import execute_guarded_research
from gremlin_mcp.hound_research import execute_research_with_hound_provenance
from gremlin_mcp.pipeline import collect, enqueue_synthesis, fanout
from gremlin_mcp.product import ProductRuntime
from gremlin_mcp.relational_cases import extract_relations, operator_signature
from gremlin_mcp.relational_research import execute_relational_research
from gremlin_mcp.research_executor import execute_research
from gremlin_mcp.router import auto_fanout, route
from gremlin_mcp.web import build_research_plan, fetch_url, research, search_web
from gremlin_mcp.workers import WorkerBroker, broker as memory_broker

broker: WorkerBroker = memory_broker
product_runtime: ProductRuntime = ProductRuntime.unconfigured(require_license=True)

mcp = MCPServer(
    "GREMLIN-PRODUCT",
    title="GREMLIN AI Research Orchestrator",
    description="Licensed GREMLIN MCP product surface with signed entitlements and restrictive client profiles.",
    instructions=(
        "This MCP surface is entitlement-gated. Product status and license status are always introspectable. "
        "All operational tools fail closed when the configured license, feature entitlement, client profile, "
        "species policy, provider policy or licensed resource limit does not admit the request."
    ),
    version=__version__,
)


def configure_product(
    *,
    license_path: str | None = None,
    license_key: str | None = None,
    public_key_path: str | None = None,
    profile_path: str | None = None,
    require_license: bool = True,
) -> ProductRuntime:
    global product_runtime
    product_runtime = ProductRuntime.from_configuration(
        license_path=license_path,
        license_key=license_key,
        public_key_path=public_key_path,
        profile_path=profile_path,
        require_license=require_license,
    )
    return product_runtime


def configure_state(state_path: str | None) -> WorkerBroker:
    global broker
    if state_path is None or not str(state_path).strip():
        broker = memory_broker
        return broker
    product_runtime.authorize_feature("PERSISTENT_STATE")
    from gremlin_mcp.persistent_workers import PersistentWorkerBroker

    broker = PersistentWorkerBroker(str(state_path))
    return broker


def _assert_local_http_bind(host: str) -> None:
    """Keep v0.1 HTTP transport on loopback until authenticated remote MCP is implemented."""
    value = str(host or "").strip().casefold()
    if value == "localhost":
        return
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise RuntimeError("REMOTE_HTTP_AUTH_REQUIRED: v0.1 accepts only localhost/loopback bind addresses") from exc
    if not address.is_loopback:
        raise RuntimeError("REMOTE_HTTP_AUTH_REQUIRED: v0.1 accepts only localhost/loopback bind addresses")


def _providers(tool: str, providers: list[str] | None, *, max_sources: int) -> list[str]:
    selected = providers or ["crossref", "arxiv", "duckduckgo"]
    product_runtime.authorize(
        tool=tool,
        feature="INTERNET_RESEARCH",
        requested_sources=max_sources,
    )
    for provider in selected:
        product_runtime.authorize(tool=tool, provider=provider)
    return selected


def _authorize_research_plan(
    tool: str,
    query: str,
    *,
    max_species: int,
    synthesis: bool,
    additional_species: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Preflight the exact deterministic research-plan species before network/work execution."""
    plan = build_research_plan(query, max_species=max_species)
    product_runtime.authorize(tool=tool, requested_workers=max_species)
    for species in plan.get("species_union") or []:
        product_runtime.authorize(tool=tool, species=str(species))
    for species in additional_species:
        product_runtime.authorize(tool=tool, species=species)
    if synthesis:
        product_runtime.authorize(tool=tool, species="BELZEBUB")
    return plan


@mcp.tool(
    title=tool_title("gremlin_product_status"),
    description=tool_description("gremlin_product_status"),
    annotations=tool_annotations("gremlin_product_status"),
)
@mcp_error_boundary("gremlin_product_status")
def gremlin_product_status() -> dict[str, Any]:
    """Return sanitized product/license/profile state without customer secrets."""
    out = product_runtime.status()
    out["worker_queue"] = broker.queue_status()
    return out


@mcp.tool(
    title=tool_title("gremlin_license_status"),
    description=tool_description("gremlin_license_status"),
    annotations=tool_annotations("gremlin_license_status"),
)
@mcp_error_boundary("gremlin_license_status")
def gremlin_license_status() -> dict[str, Any]:
    """Alias for the sanitized licensed-product state."""
    return product_runtime.status()


@mcp.tool(
    title=tool_title("gremlin_status"),
    description=tool_description("gremlin_status"),
    annotations=tool_annotations("gremlin_status"),
)
@mcp_error_boundary("gremlin_status")
def gremlin_status() -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_status")
    out = status(surface="product")
    out["product"] = product_runtime.status()
    out["worker_queue"] = broker.queue_status()
    return out


@mcp.tool(
    title=tool_title("gremlin_bestiary"),
    description=tool_description("gremlin_bestiary"),
    annotations=tool_annotations("gremlin_bestiary"),
)
@mcp_error_boundary("gremlin_bestiary")
def gremlin_bestiary() -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_bestiary")
    return bestiary_manifest()


@mcp.tool(
    title=tool_title("gremlin_species"),
    description=tool_description("gremlin_species"),
    annotations=tool_annotations("gremlin_species"),
)
@mcp_error_boundary("gremlin_species")
def gremlin_species(species: str) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_species", species=species)
    return species_profile(species)


@mcp.tool(
    title=tool_title("gremlin_plan"),
    description=tool_description("gremlin_plan"),
    annotations=tool_annotations("gremlin_plan"),
)
@mcp_error_boundary("gremlin_plan")
def gremlin_plan(route_counts: dict[str, NonNegativeRouteCount], vector_width: PlanVectorWidth = 8) -> dict[str, Any]:
    product_runtime.authorize(
        tool="gremlin_plan",
        feature="WORKER_ORCHESTRATION",
        requested_workers=sum(int(v) for v in route_counts.values()),
    )
    for species in route_counts:
        product_runtime.authorize(tool="gremlin_plan", species=species)
    return plan_bestiary(route_counts, vector_width=vector_width)


@mcp.tool(
    title=tool_title("gremlin_route"),
    description=tool_description("gremlin_route"),
    annotations=tool_annotations("gremlin_route"),
)
@mcp_error_boundary("gremlin_route")
def gremlin_route(
    payload: dict[str, Any],
    max_species: RouteMaxSpecies = 4,
    min_score: RouteMinScore = 2.0,
    relative_cutoff: RouteRelativeCutoff = 0.45,
) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_route", requested_workers=max_species)
    decision = route(payload, max_species=max_species, min_score=min_score, relative_cutoff=relative_cutoff)
    for species in decision.get("route_mask") or []:
        product_runtime.authorize(tool="gremlin_route", species=species)
    return decision


@mcp.tool(
    title=tool_title("gremlin_relation_parse"),
    description=tool_description("gremlin_relation_parse"),
    annotations=tool_annotations("gremlin_relation_parse"),
)
@mcp_error_boundary("gremlin_relation_parse")
def gremlin_relation_parse(text: str, language: str = "pl") -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_relation_parse")
    return extract_relations(text, language=language)


@mcp.tool(
    title=tool_title("gremlin_relation_signature"),
    description=tool_description("gremlin_relation_signature"),
    annotations=tool_annotations("gremlin_relation_signature"),
)
@mcp_error_boundary("gremlin_relation_signature")
def gremlin_relation_signature(operator: str) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_relation_signature")
    return operator_signature(operator)


@mcp.tool(
    title=tool_title("gremlin_web_fetch"),
    description=tool_description("gremlin_web_fetch"),
    annotations=tool_annotations("gremlin_web_fetch"),
)
@mcp_error_boundary("gremlin_web_fetch")
def gremlin_web_fetch(
    url: str,
    timeout_s: WebTimeoutSeconds = 10.0,
    max_bytes: WebMaxBytes = 1_000_000,
    max_chars: int = 120_000,
) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_web_fetch", feature="INTERNET_RESEARCH", requested_sources=1)
    return fetch_url(url, timeout_s=timeout_s, max_bytes=max_bytes, max_chars=max_chars)


@mcp.tool(
    title=tool_title("gremlin_web_search"),
    description=tool_description("gremlin_web_search"),
    annotations=tool_annotations("gremlin_web_search"),
)
@mcp_error_boundary("gremlin_web_search")
def gremlin_web_search(
    query: str,
    providers: list[str] | None = None,
    limit_per_provider: ProviderLimit = 6,
) -> dict[str, Any]:
    selected = _providers(
        "gremlin_web_search",
        providers,
        max_sources=max(1, len(providers or ["crossref", "arxiv", "duckduckgo"]) * int(limit_per_provider)),
    )
    return search_web(query, providers=selected, limit_per_provider=limit_per_provider)


@mcp.tool(
    title=tool_title("gremlin_research"),
    description=tool_description("gremlin_research"),
    annotations=tool_annotations("gremlin_research"),
)
@mcp_error_boundary("gremlin_research")
def gremlin_research(
    query: str,
    providers: list[str] | None = None,
    limit_per_provider: ProviderLimit = 6,
    max_species: int = 4,
) -> dict[str, Any]:
    _authorize_research_plan("gremlin_research", query, max_species=max_species, synthesis=False)
    selected = _providers(
        "gremlin_research",
        providers,
        max_sources=max(1, len(providers or ["crossref", "arxiv", "duckduckgo"]) * int(limit_per_provider)),
    )
    return research(query, providers=selected, limit_per_provider=limit_per_provider, max_species=max_species)


@mcp.tool(
    title=tool_title("gremlin_research_execute"),
    description=tool_description("gremlin_research_execute"),
    annotations=tool_annotations("gremlin_research_execute"),
)
@mcp_error_boundary("gremlin_research_execute")
def gremlin_research_execute(
    query: str,
    providers: list[str] | None = None,
    limit_per_provider: ProviderLimit = 6,
    max_species: int = 4,
    max_sources: ResearchMaxSources = 12,
) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_research_execute", feature="RESEARCH_EXECUTE")
    _authorize_research_plan("gremlin_research_execute", query, max_species=max_species, synthesis=True)
    selected = _providers("gremlin_research_execute", providers, max_sources=max_sources)
    return execute_research(
        query,
        providers=selected,
        limit_per_provider=limit_per_provider,
        max_species=max_species,
        max_sources=max_sources,
    )


@mcp.tool(
    title=tool_title("gremlin_research_hound_provenance"),
    description=tool_description("gremlin_research_hound_provenance"),
    annotations=tool_annotations("gremlin_research_hound_provenance"),
)
@mcp_error_boundary("gremlin_research_hound_provenance")
def gremlin_research_hound_provenance(
    query: str,
    providers: list[str] | None = None,
    limit_per_provider: ProviderLimit = 6,
    max_species: int = 4,
    max_sources: ResearchMaxSources = 12,
) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_research_hound_provenance", feature="RESEARCH_EXECUTE")
    _authorize_research_plan(
        "gremlin_research_hound_provenance",
        query,
        max_species=max_species,
        synthesis=True,
        additional_species=("HOUND",),
    )
    selected = _providers("gremlin_research_hound_provenance", providers, max_sources=max_sources)
    return execute_research_with_hound_provenance(
        query,
        providers=selected,
        limit_per_provider=limit_per_provider,
        max_species=max_species,
        max_sources=max_sources,
    )


@mcp.tool(
    title=tool_title("gremlin_research_guarded"),
    description=tool_description("gremlin_research_guarded"),
    annotations=tool_annotations("gremlin_research_guarded"),
)
@mcp_error_boundary("gremlin_research_guarded")
def gremlin_research_guarded(
    query: str,
    claim_id: str | None = None,
    claim_evidence: list[dict[str, Any]] | None = None,
    hound_receipt: dict[str, Any] | None = None,
    providers: list[str] | None = None,
    limit_per_provider: ProviderLimit = 6,
    max_species: int = 4,
    max_sources: ResearchMaxSources = 12,
) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_research_guarded", feature="RESEARCH_EXECUTE")
    product_runtime.authorize(tool="gremlin_research_guarded", feature="GUARDED_RESEARCH")
    _authorize_research_plan("gremlin_research_guarded", query, max_species=max_species, synthesis=True)
    selected = _providers("gremlin_research_guarded", providers, max_sources=max_sources)
    return execute_guarded_research(
        query,
        claim_id=claim_id,
        claim_evidence=claim_evidence,
        hound_receipt=hound_receipt,
        providers=selected,
        limit_per_provider=limit_per_provider,
        max_species=max_species,
        max_sources=max_sources,
    )


@mcp.tool(
    title=tool_title("gremlin_research_relational"),
    description=tool_description("gremlin_research_relational"),
    annotations=tool_annotations("gremlin_research_relational"),
)
@mcp_error_boundary("gremlin_research_relational")
def gremlin_research_relational(
    query: str,
    relation_text: str | None = None,
    language: str = "pl",
    providers: list[str] | None = None,
    limit_per_provider: ProviderLimit = 6,
    max_species: int = 4,
    max_sources: ResearchMaxSources = 12,
) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_research_relational", feature="RESEARCH_EXECUTE")
    product_runtime.authorize(tool="gremlin_research_relational", feature="RELATIONAL_RESEARCH")
    _authorize_research_plan(
        "gremlin_research_relational",
        query,
        max_species=max_species,
        synthesis=True,
        additional_species=("SPIDER", "MOLE", "HOUND"),
    )
    selected = _providers("gremlin_research_relational", providers, max_sources=max_sources)
    return execute_relational_research(
        query,
        relation_text=relation_text,
        language=language,
        providers=selected,
        limit_per_provider=limit_per_provider,
        max_species=max_species,
        max_sources=max_sources,
    )


@mcp.tool(
    title=tool_title("gremlin_auto_fanout"),
    description=tool_description("gremlin_auto_fanout"),
    annotations=tool_annotations("gremlin_auto_fanout"),
)
@mcp_error_boundary("gremlin_auto_fanout")
def gremlin_auto_fanout(
    payload: dict[str, Any],
    request_id: RequestId | None = None,
    max_species: RouteMaxSpecies = 4,
    min_score: RouteMinScore = 2.0,
    relative_cutoff: RouteRelativeCutoff = 0.45,
) -> dict[str, Any]:
    product_runtime.authorize(
        tool="gremlin_auto_fanout",
        feature="WORKER_ORCHESTRATION",
        requested_workers=max_species,
    )
    decision = route(payload, max_species=max_species, min_score=min_score, relative_cutoff=relative_cutoff)
    for species in decision.get("route_mask") or []:
        product_runtime.authorize(tool="gremlin_auto_fanout", species=species)
    return auto_fanout(
        broker,
        payload,
        request_id=request_id,
        max_species=max_species,
        min_score=min_score,
        relative_cutoff=relative_cutoff,
    )


@mcp.tool(
    title=tool_title("gremlin_fanout"),
    description=tool_description("gremlin_fanout"),
    annotations=tool_annotations("gremlin_fanout"),
)
@mcp_error_boundary("gremlin_fanout")
def gremlin_fanout(
    payload: dict[str, Any],
    species: list[str],
    request_id: RequestId | None = None,
) -> dict[str, Any]:
    product_runtime.authorize(
        tool="gremlin_fanout",
        feature="WORKER_ORCHESTRATION",
        requested_workers=len(species),
    )
    for name in species:
        product_runtime.authorize(tool="gremlin_fanout", species=name)
    return fanout(broker, payload, species, request_id=request_id)


@mcp.tool(
    title=tool_title("gremlin_collect"),
    description=tool_description("gremlin_collect"),
    annotations=tool_annotations("gremlin_collect"),
)
@mcp_error_boundary("gremlin_collect")
def gremlin_collect(task_ids: WorkerIdentifierList) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_collect", feature="WORKER_ORCHESTRATION")
    return collect(broker, task_ids)


@mcp.tool(
    title=tool_title("gremlin_synthesize"),
    description=tool_description("gremlin_synthesize"),
    annotations=tool_annotations("gremlin_synthesize"),
)
@mcp_error_boundary("gremlin_synthesize")
def gremlin_synthesize(specialist_task_ids: WorkerIdentifierList, request_id: RequestId | None = None) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_synthesize", feature="WORKER_ORCHESTRATION", species="BELZEBUB")
    return enqueue_synthesis(broker, specialist_task_ids, request_id=request_id)


@mcp.tool(
    title=tool_title("gremlin_prototype"),
    description=tool_description("gremlin_prototype"),
    annotations=tool_annotations("gremlin_prototype"),
)
@mcp_error_boundary("gremlin_prototype")
def gremlin_prototype(request: dict[str, Any]) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_prototype", feature="PROTOTYPE_PIPELINE")
    return run_prototype(request)


@mcp.tool(
    title=tool_title("gremlin_worker_register"),
    description=tool_description("gremlin_worker_register"),
    annotations=tool_annotations("gremlin_worker_register"),
)
@mcp_error_boundary("gremlin_worker_register")
def gremlin_worker_register(
    worker_id: WorkerIdentifier,
    species: NonEmptyStringList,
    capabilities: list[str] | None = None,
    vector_width: WorkerVectorWidth = 8,
    max_batch: WorkerMaxBatch = 128,
) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_worker_register", feature="CUSTOM_WORKERS", requested_workers=1)
    for name in species:
        product_runtime.authorize(tool="gremlin_worker_register", species=name)
    return broker.register_worker(
        worker_id,
        species,
        capabilities=capabilities or (),
        vector_width=vector_width,
        max_batch=max_batch,
    )


@mcp.tool(
    title=tool_title("gremlin_worker_heartbeat"),
    description=tool_description("gremlin_worker_heartbeat"),
    annotations=tool_annotations("gremlin_worker_heartbeat"),
)
@mcp_error_boundary("gremlin_worker_heartbeat")
def gremlin_worker_heartbeat(worker_id: WorkerIdentifier) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_worker_heartbeat", feature="CUSTOM_WORKERS")
    return broker.heartbeat(worker_id)


@mcp.tool(
    title=tool_title("gremlin_worker_list"),
    description=tool_description("gremlin_worker_list"),
    annotations=tool_annotations("gremlin_worker_list"),
)
@mcp_error_boundary("gremlin_worker_list")
def gremlin_worker_list() -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_worker_list", feature="CUSTOM_WORKERS")
    return broker.list_workers()


@mcp.tool(
    title=tool_title("gremlin_worker_enqueue"),
    description=tool_description("gremlin_worker_enqueue"),
    annotations=tool_annotations("gremlin_worker_enqueue"),
)
@mcp_error_boundary("gremlin_worker_enqueue")
def gremlin_worker_enqueue(species: str, payload: dict[str, Any], task_id: WorkerIdentifier | None = None) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_worker_enqueue", feature="CUSTOM_WORKERS", species=species)
    return broker.enqueue(species, payload, task_id=task_id)


@mcp.tool(
    title=tool_title("gremlin_worker_claim"),
    description=tool_description("gremlin_worker_claim"),
    annotations=tool_annotations("gremlin_worker_claim"),
)
@mcp_error_boundary("gremlin_worker_claim")
def gremlin_worker_claim(
    worker_id: WorkerIdentifier,
    species: str | None = None,
    limit: WorkerClaimLimit | None = None,
    lease_seconds: WorkerLeaseSeconds | None = None,
) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_worker_claim", feature="CUSTOM_WORKERS", species=species)
    return broker.claim(worker_id, species=species, limit=limit, lease_seconds=lease_seconds)


@mcp.tool(
    title=tool_title("gremlin_worker_submit"),
    description=tool_description("gremlin_worker_submit"),
    annotations=tool_annotations("gremlin_worker_submit"),
)
@mcp_error_boundary("gremlin_worker_submit")
def gremlin_worker_submit(worker_id: WorkerIdentifier, lease_id: WorkerIdentifier, results: list[dict[str, Any]]) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_worker_submit", feature="CUSTOM_WORKERS")
    return broker.submit(worker_id, lease_id, results)


@mcp.tool(
    title=tool_title("gremlin_worker_result"),
    description=tool_description("gremlin_worker_result"),
    annotations=tool_annotations("gremlin_worker_result"),
)
@mcp_error_boundary("gremlin_worker_result")
def gremlin_worker_result(task_id: WorkerIdentifier) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_worker_result", feature="CUSTOM_WORKERS")
    return broker.task_result(task_id)


@mcp.tool(
    title=tool_title("gremlin_worker_queue"),
    description=tool_description("gremlin_worker_queue"),
    annotations=tool_annotations("gremlin_worker_queue"),
)
@mcp_error_boundary("gremlin_worker_queue")
def gremlin_worker_queue() -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_worker_queue", feature="CUSTOM_WORKERS")
    return broker.queue_status()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Licensed GREMLIN AI Research Orchestrator MCP server")
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8766, type=int)
    parser.add_argument("--path", default="/mcp")
    parser.add_argument("--license-path", default=os.environ.get("GREMLIN_LICENSE_PATH"))
    parser.add_argument("--license-key", default=os.environ.get("GREMLIN_LICENSE_KEY"))
    parser.add_argument("--public-key", default=os.environ.get("GREMLIN_LICENSE_PUBLIC_KEY"))
    parser.add_argument("--client-profile", default=os.environ.get("GREMLIN_CLIENT_PROFILE"))
    parser.add_argument("--state-path", default=os.environ.get("GREMLIN_MCP_STATE_PATH"))
    parser.add_argument(
        "--allow-unlicensed-research",
        action="store_true",
        help="disable product entitlement enforcement only for explicit non-commercial research mode",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    configure_product(
        license_path=args.license_path,
        license_key=args.license_key,
        public_key_path=args.public_key,
        profile_path=args.client_profile,
        require_license=not args.allow_unlicensed_research,
    )
    if args.transport == "stdio":
        product_runtime.authorize_feature("MCP_STDIO")
    else:
        product_runtime.authorize_feature("MCP_HTTP")
        _assert_local_http_bind(args.host)
    configure_state(args.state_path)
    if args.transport == "stdio":
        mcp.run("stdio")
        return
    mcp.run(
        "streamable-http",
        host=args.host,
        port=args.port,
        streamable_http_path=args.path,
        json_response=True,
    )


if __name__ == "__main__":
    main()
