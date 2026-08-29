from __future__ import annotations

import argparse
import os
from typing import Any

from mcp.server import MCPServer

from gremlin_mcp import __version__
from gremlin_mcp.core import (
    bestiary_manifest,
    plan_bestiary,
    run_prototype,
    species_profile,
    status,
)
from gremlin_mcp.pipeline import collect, enqueue_synthesis, fanout
from gremlin_mcp.router import auto_fanout, route
from gremlin_mcp.web import fetch_url, research, search_web
from gremlin_mcp.workers import WorkerBroker, broker as memory_broker

broker: WorkerBroker = memory_broker

mcp = MCPServer(
    "GREMLIN",
    title="GREMLIN Bestiary",
    description="Standalone research MCP adapter for GREMLIN Bestiary semantic routing, scheduling, internet evidence acquisition, external animal workers and reference execution.",
    instructions=(
        "GREMLIN MCP is a research/candidate interface. Use gremlin_bestiary to inspect "
        "the animal topology, gremlin_species for one role, gremlin_plan to build a "
        "mass-orbit/vector lane plan, gremlin_route for an auditable OCTOPUS semantic route, "
        "gremlin_web_search for bounded internet evidence acquisition, gremlin_web_fetch for "
        "a receipt-bearing HTTPS document fetch, gremlin_research for route + multi-provider "
        "evidence acquisition, gremlin_auto_fanout to route and queue confident specialist work, "
        "gremlin_fanout for an explicit caller-supplied route, gremlin_collect to inspect "
        "specialist completion, gremlin_synthesize to queue BELZEBUB after all supplied specialists "
        "finish, and gremlin_prototype for the existing fail-closed reference prototype pipeline. "
        "Internet access is HTTPS-only, blocks local/private/link-local/reserved targets, validates "
        "redirects and bounds response size. External backends can register as animal workers, "
        "claim bounded same-species batches, and submit CANDIDATE results. MCP calls never grant "
        "production execution or canon authority."
    ),
    version=__version__,
)


def configure_state(state_path: str | None) -> WorkerBroker:
    """Select process-memory or durable SQLite-WAL worker coordination."""
    global broker
    if state_path is None or not str(state_path).strip():
        broker = memory_broker
        return broker
    from gremlin_mcp.persistent_workers import PersistentWorkerBroker

    broker = PersistentWorkerBroker(str(state_path))
    return broker


@mcp.tool()
def gremlin_status() -> dict[str, Any]:
    """Return MCP mode, capabilities, topology and fail-closed authority state."""
    result = status()
    result["worker_queue"] = broker.queue_status()
    result["internet_research"] = {
        "status": "AVAILABLE",
        "mode": "HTTPS_ONLY_FAIL_CLOSED",
        "providers": ["crossref", "arxiv", "duckduckgo"],
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
    return result


@mcp.tool()
def gremlin_bestiary() -> dict[str, Any]:
    """List GREMLIN animals, their roles, scheduler mass/orbit and cadence data."""
    return bestiary_manifest()


@mcp.tool()
def gremlin_species(species: str) -> dict[str, Any]:
    """Inspect one GREMLIN animal by name, for example SPIDER, OWL or BELZEBUB."""
    return species_profile(species)


@mcp.tool()
def gremlin_plan(route_counts: dict[str, int], vector_width: int = 8) -> dict[str, Any]:
    """Build a deterministic mass-orbit/vector-lane execution plan for routed work."""
    return plan_bestiary(route_counts, vector_width=vector_width)


@mcp.tool()
def gremlin_route(
    payload: dict[str, Any],
    max_species: int = 4,
    min_score: float = 2.0,
    relative_cutoff: float = 0.45,
) -> dict[str, Any]:
    """Ask OCTOPUS for an auditable deterministic semantic specialist route mask."""
    return route(
        payload,
        max_species=max_species,
        min_score=min_score,
        relative_cutoff=relative_cutoff,
    )


@mcp.tool()
def gremlin_web_fetch(
    url: str,
    timeout_s: float = 10.0,
    max_bytes: int = 1_000_000,
    max_chars: int = 120_000,
) -> dict[str, Any]:
    """Fetch one public HTTPS text/JSON/XML resource with SSRF firewall and provenance receipt."""
    return fetch_url(
        url,
        timeout_s=timeout_s,
        max_bytes=max_bytes,
        max_chars=max_chars,
    )


@mcp.tool()
def gremlin_web_search(
    query: str,
    providers: list[str] | None = None,
    limit_per_provider: int = 6,
) -> dict[str, Any]:
    """Search bounded public internet providers and return deduplicated candidate evidence."""
    return search_web(
        query,
        providers=providers or ["crossref", "arxiv", "duckduckgo"],
        limit_per_provider=limit_per_provider,
    )


@mcp.tool()
def gremlin_research(
    query: str,
    providers: list[str] | None = None,
    limit_per_provider: int = 6,
    max_species: int = 4,
) -> dict[str, Any]:
    """Run OCTOPUS routing plus bounded internet evidence acquisition for a research query."""
    return research(
        query,
        providers=providers or ["crossref", "arxiv", "duckduckgo"],
        limit_per_provider=limit_per_provider,
        max_species=max_species,
    )


@mcp.tool()
def gremlin_auto_fanout(
    payload: dict[str, Any],
    request_id: str | None = None,
    max_species: int = 4,
    min_score: float = 2.0,
    relative_cutoff: float = 0.45,
) -> dict[str, Any]:
    """Route with OCTOPUS and queue work only when positive semantic evidence is present."""
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
    """Queue one payload to an explicit caller-supplied specialist route mask."""
    return fanout(broker, payload, species, request_id=request_id)


@mcp.tool()
def gremlin_collect(task_ids: list[str]) -> dict[str, Any]:
    """Collect current states and CANDIDATE outputs for a specialist fanout."""
    return collect(broker, task_ids)


@mcp.tool()
def gremlin_synthesize(
    specialist_task_ids: list[str],
    request_id: str | None = None,
) -> dict[str, Any]:
    """Queue BELZEBUB synthesis after every supplied specialist task is DONE."""
    return enqueue_synthesis(broker, specialist_task_ids, request_id=request_id)


@mcp.tool()
def gremlin_prototype(request: dict[str, Any]) -> dict[str, Any]:
    """Run GREMLIN's existing reference candidate -> PhaseNav IR -> prototype -> test pipeline."""
    return run_prototype(request)


@mcp.tool()
def gremlin_worker_register(
    worker_id: str,
    species: list[str],
    capabilities: list[str] | None = None,
    vector_width: int = 8,
    max_batch: int = 128,
) -> dict[str, Any]:
    """Register or refresh an external backend as one or more GREMLIN animal workers."""
    return broker.register_worker(
        worker_id,
        species,
        capabilities=capabilities or (),
        vector_width=vector_width,
        max_batch=max_batch,
    )


@mcp.tool()
def gremlin_worker_heartbeat(worker_id: str) -> dict[str, Any]:
    """Refresh a registered GREMLIN worker heartbeat."""
    return broker.heartbeat(worker_id)


@mcp.tool()
def gremlin_worker_list() -> dict[str, Any]:
    """List currently registered external GREMLIN animal workers."""
    return broker.list_workers()


@mcp.tool()
def gremlin_worker_enqueue(
    species: str,
    payload: dict[str, Any],
    task_id: str | None = None,
) -> dict[str, Any]:
    """Queue one JSON task for a scheduler-backed GREMLIN animal worker."""
    return broker.enqueue(species, payload, task_id=task_id)


@mcp.tool()
def gremlin_worker_claim(
    worker_id: str,
    species: str | None = None,
    limit: int | None = None,
    lease_seconds: int | None = None,
) -> dict[str, Any]:
    """Claim one bounded same-species batch using GREMLIN orbit/vector lane limits."""
    return broker.claim(
        worker_id,
        species=species,
        limit=limit,
        lease_seconds=lease_seconds,
    )


@mcp.tool()
def gremlin_worker_submit(
    worker_id: str,
    lease_id: str,
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Submit exact lease results; the MCP envelope remains CANDIDATE and fail-closed."""
    return broker.submit(worker_id, lease_id, results)


@mcp.tool()
def gremlin_worker_result(task_id: str) -> dict[str, Any]:
    """Read current state or candidate output for one GREMLIN worker task."""
    return broker.task_result(task_id)


@mcp.tool()
def gremlin_worker_queue() -> dict[str, Any]:
    """Return per-species queue counts, active leases and persistence scope."""
    return broker.queue_status()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GREMLIN Bestiary MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host")
    parser.add_argument("--port", default=8766, type=int, help="HTTP bind port")
    parser.add_argument("--path", default="/mcp", help="Streamable HTTP MCP path")
    parser.add_argument(
        "--state-path",
        default=os.environ.get("GREMLIN_MCP_STATE_PATH"),
        help=(
            "optional SQLite worker-state path; also read from GREMLIN_MCP_STATE_PATH. "
            "Without it the standalone worker broker is process-resident."
        ),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
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
