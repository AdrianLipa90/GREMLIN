from __future__ import annotations

from dataclasses import asdict, dataclass
import argparse
import json
import os
import shutil
from typing import Any, Callable, Mapping, Sequence

from . import chatgpt_clean_install as remote
from . import openai_tunnel as tunnel

SCHEMA = "GREMLIN_CHATGPT_INSTALL_PREFLIGHT_V1"


@dataclass(frozen=True)
class Route:
    name: str
    status: str
    blocker: str | None
    detail: str
    plan: dict[str, Any]


@dataclass(frozen=True)
class Preflight:
    schema: str
    status: str
    selected_route: str | None
    routes: tuple[Route, ...]
    host_gate: dict[str, str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _remote_route(endpoint: str | None) -> Route:
    plan = remote.build_plan(endpoint)
    return Route(
        name="REMOTE_HTTPS_MCP",
        status="PACKAGE_READY" if plan.package_ready else "BLOCKED",
        blocker=plan.blocker,
        detail=(
            "portable plugin package can be built for this endpoint"
            if plan.package_ready
            else "remote HTTPS MCP path is not ready"
        ),
        plan=plan.as_dict(),
    )


def _tunnel_route(
    *,
    env: Mapping[str, str],
    which: Callable[[str], str | None],
) -> Route:
    plan = tunnel.build_plan(env=env, which=which)
    failed = [gate for gate in plan.gates if gate.status != "PASS"]
    blocker = failed[0].detail if failed else None
    return Route(
        name="SECURE_MCP_TUNNEL",
        status="PREREQUISITES_READY" if plan.ready else "BLOCKED",
        blocker=blocker,
        detail=(
            "tunnel-client prerequisites are present; init + doctor still required"
            if plan.ready
            else "Secure MCP Tunnel prerequisites are incomplete"
        ),
        plan=plan.as_dict(),
    )


def build_preflight(
    *,
    endpoint: str | None = None,
    env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> Preflight:
    environ = os.environ if env is None else env
    routes = (
        _remote_route(endpoint),
        _tunnel_route(env=environ, which=which),
    )

    selected: str | None = None
    status = "BLOCKED"
    if routes[0].status == "PACKAGE_READY":
        selected = routes[0].name
        status = "PACKAGE_READY"
    elif routes[1].status == "PREREQUISITES_READY":
        selected = routes[1].name
        status = "TUNNEL_PREREQUISITES_READY"

    return Preflight(
        schema=SCHEMA,
        status=status,
        selected_route=selected,
        routes=routes,
        host_gate={
            "name": "CHATGPT_HOST_ADMISSION",
            "status": "EXTERNAL_REQUIRED",
            "detail": "ChatGPT registration, authentication/permissions, tool scan, and a live GREMLIN tool call must still pass",
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Diagnose clean-account ChatGPT installation paths for GREMLIN"
    )
    parser.add_argument("--endpoint", help="optional remote HTTPS GREMLIN MCP endpoint ending in /mcp")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_preflight(endpoint=args.endpoint)
    payload = result.as_dict()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(result.status)
        for route in result.routes:
            suffix = f": {route.blocker}" if route.blocker else ""
            print(f"{route.status} {route.name}{suffix}")
        print("EXTERNAL_REQUIRED CHATGPT_HOST_ADMISSION")
    return 0 if result.status != "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
