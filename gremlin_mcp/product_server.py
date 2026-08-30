from __future__ import annotations

import argparse
import ipaddress
import os
from typing import Any

from mcp.server import MCPServer

from gremlin_mcp import __version__
from gremlin_mcp.core import bestiary_manifest, plan_bestiary, run_prototype, species_profile, status
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


@mcp.tool()
def gremlin_product_status() -> dict[str, Any]:
    """Return sanitized product/license/profile state without customer secrets."""
    out = product_runtime.status()
    out["worker_queue"] = broker.queue_status()
    return out


@mcp.tool()
def gremlin_license_status() -> dict[str, Any]:
    """Alias for the sanitized licensed-product state."""
    return product_runtime.status()


@mcp.tool()
def gremlin_status() -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_status")
    out = status()
    out["product"] = product_runtime.status()
    out["worker_queue"] = broker.queue_status()
    return out


@mcp.tool()
def gremlin_bestiary() -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_bestiary")
    return bestiary_manifest()


@mcp.tool()
def gremlin_species(species: str) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_species", species=species)
    return species_profile(species)


@mcp.tool()
def gremlin_plan(route_counts: dict[str, int], vector_width: int = 8) -> dict[str, Any]:
    product_runtime.authorize(
        tool="gremlin_plan",
        feature="WORKER_ORCHESTRATION",
        requested_workers=sum(int(v) for v in route_counts.values()),
    )
    for species in route_counts:
        product_runtime.authorize(tool="gremlin_plan", species=species)
    return plan_bestiary(route_counts, vector_width=vector_width)


@mcp.tool()
def gremlin_route(
    payload: dict[str, Any],
    max_species: int = 4,
    min_score: float = 2.0,
    relative_cutoff: float = 0.45,
) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_route", requested_workers=max_species)
    decision = route(payload, max_species=max_species, min_score=min_score, relative_cutoff=relative_cutoff)
    for species in decision.get("route_mask") or []:
        product_runtime.authorize(tool="gremlin_route", species=species)
    return decision


@mcp.tool()
def gremlin_relation_parse(text: str, language: str = "pl") -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_relation_parse")
    return extract_relations(text, language=language)


@mcp.tool()
def gremlin_relation_signature(operator: str) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_relation_signature")
    return operator_signature(operator)


@mcp.tool()
def gremlin_web_fetch(
    url: str,
    timeout_s: float = 10.0,
    max_bytes: int = 1_000_000,
    max_chars: int = 120_000,
) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_web_fetch", feature="INTERNET_RESEARCH", requested_sources=1)
    return fetch_url(url, timeout_s=timeout_s, max_bytes=max_bytes, max_chars=max_chars)


@mcp.tool()
def gremlin_web_search(
    query: str,
    providers: list[str] | None = None,
    limit_per_provider: int = 6,
) -> dict[str, Any]:
    selected = _providers(
        "gremlin_web_search",
        providers,
        max_sources=max(1, len(providers or ["crossref", "arxiv", "duckduckgo"]) * int(limit_per_provider)),
    )
    return search_web(query, providers=selected, limit_per_provider=limit_per_provider)


@mcp.tool()
def gremlin_research(
    query: str,
    providers: list[str] | None = None,
    limit_per_provider: int = 6,
    max_species: int = 4,
) -> dict[str, Any]:
    _authorize_research_plan("gremlin_research", query, max_species=max_species, synthesis=False)
    selected = _providers(
        "gremlin_research",
        providers,
        max_sources=max(1, len(providers or ["crossref", "arxiv", "duckduckgo"]) * int(limit_per_provider)),
    )
    return research(query, providers=selected, limit_per_provider=limit_per_provider, max_species=max_species)


@mcp.tool()
def gremlin_research_execute(
    query: str,
    providers: list[str] | None = None,
    limit_per_provider: int = 6,
    max_species: int = 4,
    max_sources: int = 12,
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


@mcp.tool()
def gremlin_research_hound_provenance(
    query: str,
    providers: list[str] | None = None,
    limit_per_provider: int = 6,
    max_species: int = 4,
    max_sources: int = 12,
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


@mcp.tool()
def gremlin_research_guarded(
    query: str,
    claim_id: str | None = None,
    claim_evidence: list[dict[str, Any]] | None = None,
    hound_receipt: dict[str, Any] | None = None,
    providers: list[str] | None = None,
    limit_per_provider: int = 6,
    max_species: int = 4,
    max_sources: int = 12,
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


@mcp.tool()
def gremlin_research_relational(
    query: str,
    relation_text: str | None = None,
    language: str = "pl",
    providers: list[str] | None = None,
    limit_per_provider: int = 6,
    max_species: int = 4,
    max_sources: int = 12,
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


@mcp.tool()
def gremlin_auto_fanout(
    payload: dict[str, Any],
    request_id: str | None = None,
    max_species: int = 4,
    min_score: float = 2.0,
    relative_cutoff: float = 0.45,
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


@mcp.tool()
def gremlin_fanout(
    payload: dict[str, Any],
    species: list[str],
    request_id: str | None = None,
) -> dict[str, Any]:
    product_runtime.authorize(
        tool="gremlin_fanout",
        feature="WORKER_ORCHESTRATION",
        requested_workers=len(species),
    )
    for name in species:
        product_runtime.authorize(tool="gremlin_fanout", species=name)
    return fanout(broker, payload, species, request_id=request_id)


@mcp.tool()
def gremlin_collect(task_ids: list[str]) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_collect", feature="WORKER_ORCHESTRATION")
    return collect(broker, task_ids)


@mcp.tool()
def gremlin_synthesize(specialist_task_ids: list[str], request_id: str | None = None) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_synthesize", feature="WORKER_ORCHESTRATION", species="BELZEBUB")
    return enqueue_synthesis(broker, specialist_task_ids, request_id=request_id)


@mcp.tool()
def gremlin_prototype(request: dict[str, Any]) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_prototype", feature="PROTOTYPE_PIPELINE")
    return run_prototype(request)


@mcp.tool()
def gremlin_worker_register(
    worker_id: str,
    species: list[str],
    capabilities: list[str] | None = None,
    vector_width: int = 8,
    max_batch: int = 128,
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


@mcp.tool()
def gremlin_worker_heartbeat(worker_id: str) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_worker_heartbeat", feature="CUSTOM_WORKERS")
    return broker.heartbeat(worker_id)


@mcp.tool()
def gremlin_worker_list() -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_worker_list", feature="CUSTOM_WORKERS")
    return broker.list_workers()


@mcp.tool()
def gremlin_worker_enqueue(species: str, payload: dict[str, Any], task_id: str | None = None) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_worker_enqueue", feature="CUSTOM_WORKERS", species=species)
    return broker.enqueue(species, payload, task_id=task_id)


@mcp.tool()
def gremlin_worker_claim(
    worker_id: str,
    species: str | None = None,
    limit: int | None = None,
    lease_seconds: int | None = None,
) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_worker_claim", feature="CUSTOM_WORKERS", species=species)
    return broker.claim(worker_id, species=species, limit=limit, lease_seconds=lease_seconds)


@mcp.tool()
def gremlin_worker_submit(worker_id: str, lease_id: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_worker_submit", feature="CUSTOM_WORKERS")
    return broker.submit(worker_id, lease_id, results)


@mcp.tool()
def gremlin_worker_result(task_id: str) -> dict[str, Any]:
    product_runtime.authorize(tool="gremlin_worker_result", feature="CUSTOM_WORKERS")
    return broker.task_result(task_id)


@mcp.tool()
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
