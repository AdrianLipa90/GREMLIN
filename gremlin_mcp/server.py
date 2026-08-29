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
from gremlin_mcp.workers import WorkerBroker, broker as memory_broker

broker: WorkerBroker = memory_broker

mcp = MCPServer(
    "GREMLIN",
    title="GREMLIN Bestiary",
    description="Standalone research MCP adapter for GREMLIN Bestiary scheduling, external animal workers and reference execution.",
    instructions=(
        "GREMLIN MCP is a research/candidate interface. Use gremlin_bestiary to inspect "
        "the animal topology, gremlin_species for one role, gremlin_plan to build a "
        "mass-orbit/vector lane plan, gremlin_fanout to queue an explicit specialist route, "
        "gremlin_collect to inspect specialist completion, gremlin_synthesize to queue BELZEBUB "
        "after all supplied specialists finish, and gremlin_prototype for the existing fail-closed "
        "reference prototype pipeline. External backends can register as animal workers, claim "
        "bounded same-species batches, and submit CANDIDATE results. MCP calls never grant "
        "production execution or canon authority."
    ),
    version=__version__,
)


def configure_state(state_path: str | None) -> WorkerBroker:
    """Select process-memory or durable SQLite-WAL worker coordination.

    Passing ``None`` keeps the in-process broker used by embedded MCP hosts and
    tests. A path creates a fresh persistent broker and makes all worker tools
    share that durable state.
    """
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
def gremlin_fanout(
    payload: dict[str, Any],
    species: list[str],
    request_id: str | None = None,
) -> dict[str, Any]:
    """Queue one payload to an explicit specialist route mask.

    This does not pretend to be an implicit semantic OCTOPUS decision: the
    caller supplies the route mask and GREMLIN supplies lineage and queueing.
    """
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
