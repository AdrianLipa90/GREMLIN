from __future__ import annotations

from dataclasses import asdict, dataclass
import argparse
import ipaddress
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit
import zipfile

SCHEMA = "GREMLIN_CHATGPT_CLEAN_INSTALL_V1"
PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
PLUGIN_NAME = "gremlin"
PLUGIN_VERSION = "1.0.0"
REMOTE_TRANSPORT = "streamable-http"
REQUIRED_FILES = (
    "plugin.json",
    "mcp.json",
    "skills/gremlin/SKILL.md",
)

SKILL_TEXT = """---
name: gremlin
description: Use GREMLIN for auditable routing, specialist fanout, synthesis, diagnostics, and fail-closed research workflows through its MCP tools.
---

Use GREMLIN when the user asks to route, audit, decompose, test, synthesize, or inspect a complex task with the GREMLIN Bestiary.

1. Begin by calling `gremlin_status` when available. Treat an unavailable or blocked runtime as a blocker; do not invent a successful connection.
2. Prefer `gremlin_route` or `gremlin_auto_fanout` for automatic OCTOPUS routing. Use explicit fanout only when the desired specialist set is already known.
3. Preserve tool receipts, provenance, and candidate/authority distinctions. A candidate result is not canon or production authority.
4. Use `gremlin_collect` and `gremlin_synthesize` only after the required specialist work is complete.
5. For any write, mutation, external actuation, or authority-sensitive operation, obey the server's admission and confirmation gates and fail closed when a prerequisite is missing.
6. Report partial or blocked states explicitly instead of silently substituting a local-memory or prompt-only approximation.
"""


@dataclass(frozen=True)
class Gate:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class CleanInstallPlan:
    schema: str
    endpoint: str | None
    gates: tuple[Gate, ...]
    package_ready: bool
    blocker: str | None
    host_gate: Gate

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_endpoint(endpoint: str | None) -> str | None:
    if endpoint is None:
        return None
    value = str(endpoint).strip()
    return value or None


def _host_is_local_or_private(hostname: str) -> bool:
    host = hostname.strip().lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_unspecified)


def endpoint_gate(endpoint: str | None) -> Gate:
    value = _normalize_endpoint(endpoint)
    if value is None:
        return Gate("REMOTE_MCP", "FAIL", "REMOTE_ENDPOINT_REQUIRED")
    try:
        parsed = urlsplit(value)
    except ValueError:
        return Gate("REMOTE_MCP", "FAIL", "REMOTE_ENDPOINT_INVALID")
    if parsed.scheme.lower() != "https":
        return Gate("REMOTE_MCP", "FAIL", "REMOTE_ENDPOINT_MUST_USE_HTTPS")
    if parsed.username or parsed.password:
        return Gate("REMOTE_MCP", "FAIL", "REMOTE_ENDPOINT_MUST_NOT_EMBED_CREDENTIALS")
    if parsed.query:
        return Gate("REMOTE_MCP", "FAIL", "REMOTE_ENDPOINT_QUERY_NOT_ALLOWED")
    if not parsed.hostname:
        return Gate("REMOTE_MCP", "FAIL", "REMOTE_ENDPOINT_HOST_REQUIRED")
    if _host_is_local_or_private(parsed.hostname):
        return Gate("REMOTE_MCP", "FAIL", "REMOTE_ENDPOINT_NOT_REACHABLE_FROM_CLEAN_CHATGPT_ACCOUNT")
    if not (parsed.path == "/mcp" or parsed.path.endswith("/mcp")):
        return Gate("REMOTE_MCP", "FAIL", "REMOTE_ENDPOINT_PATH_MUST_END_IN_/mcp")
    if parsed.fragment:
        return Gate("REMOTE_MCP", "FAIL", "REMOTE_ENDPOINT_FRAGMENT_NOT_ALLOWED")
    return Gate("REMOTE_MCP", "PASS", "remote HTTPS Streamable HTTP MCP endpoint configured")


def build_plan(endpoint: str | None) -> CleanInstallPlan:
    remote = endpoint_gate(endpoint)
    package_gates = (
        Gate("CLEAN_ACCOUNT", "PASS", "package requires no prior ChatGPT conversation, Memory, Library, NOEMA state, or local GREMLIN configuration"),
        Gate("PORTABLE_PLUGIN", "PASS", "package uses portable root plugin.json + mcp.json + bundled skill"),
        remote,
    )
    blocker = next((gate.detail for gate in package_gates if gate.status != "PASS"), None)
    host_gate = Gate(
        "CHATGPT_HOST_ADMISSION",
        "EXTERNAL_REQUIRED",
        "register/install the plugin in an eligible ChatGPT surface, run Scan Tools, review permissions, and verify GREMLIN tools are discovered",
    )
    return CleanInstallPlan(
        schema=SCHEMA,
        endpoint=_normalize_endpoint(endpoint),
        gates=package_gates,
        package_ready=blocker is None,
        blocker=blocker,
        host_gate=host_gate,
    )


def plugin_manifest() -> dict[str, Any]:
    return {
        "$schema": PLUGIN_SCHEMA,
        "name": PLUGIN_NAME,
        "version": PLUGIN_VERSION,
        "description": "GREMLIN auditable orchestration, research routing, synthesis, and diagnostics.",
        "author": {"name": "Adrian Lipa / Intention Lab"},
        "repository": "https://github.com/AdrianLipa90/GREMLIN",
        "license": "LicenseRef-CIEL-Research-NonCommercial-2.0",
        "keywords": ["gremlin", "orchestration", "research", "mcp", "phasenav"],
        "extensions": {
            "com.openai": {
                "interface": {
                    "displayName": "GREMLIN",
                    "shortDescription": "Auditable orchestration and specialist routing.",
                    "longDescription": "Use GREMLIN's MCP Bestiary for auditable routing, specialist fanout, synthesis, diagnostics, and fail-closed research workflows.",
                    "developerName": "Adrian Lipa / Intention Lab",
                    "category": "Productivity",
                    "capabilities": ["Read", "Write"],
                    "defaultPrompt": [
                        "Use GREMLIN to audit and route this task.",
                        "Use GREMLIN to decompose this problem and synthesize the specialist results."
                    ]
                }
            }
        }
    }


def mcp_manifest(endpoint: str) -> dict[str, Any]:
    gate = endpoint_gate(endpoint)
    if gate.status != "PASS":
        raise ValueError(gate.detail)
    return {
        "$schema": MCP_SCHEMA,
        "mcpServers": {
            "gremlin": {
                "type": REMOTE_TRANSPORT,
                "url": endpoint
            }
        }
    }


def package_files(endpoint: str) -> dict[str, bytes]:
    return {
        "plugin.json": (json.dumps(plugin_manifest(), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        "mcp.json": (json.dumps(mcp_manifest(endpoint), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        "skills/gremlin/SKILL.md": SKILL_TEXT.encode("utf-8")
    }


def build_zip(endpoint: str, output: str | Path) -> dict[str, Any]:
    plan = build_plan(endpoint)
    if not plan.package_ready:
        raise ValueError(plan.blocker or "CLEAN_INSTALL_BLOCKED")
    target = Path(output)
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing artifact: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    files = package_files(endpoint)
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(files):
            zf.writestr(name, files[name])
    inspected = inspect_zip(target)
    if inspected["status"] != "PASS":
        target.unlink(missing_ok=True)
        raise RuntimeError(f"generated plugin failed self-inspection: {inspected}")
    return {
        "schema": SCHEMA,
        "status": "PACKAGE_READY",
        "artifact": str(target),
        "endpoint": endpoint,
        "files": sorted(files),
        "inspection": inspected,
        "host_gate": asdict(plan.host_gate),
        "next_required_gate": "CHATGPT_HOST_ADMISSION"
    }


def _load_json_bytes(raw: bytes, name: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"{name}: invalid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{name}: top level must be an object")
    return value


def inspect_zip(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    failures: list[str] = []
    endpoint: str | None = None
    try:
        with zipfile.ZipFile(target, "r") as zf:
            names = zf.namelist()
            if len(names) != len(set(names)):
                failures.append("DUPLICATE_ARCHIVE_PATH")
            for name in names:
                pure = PurePosixPath(name)
                if pure.is_absolute() or ".." in pure.parts:
                    failures.append(f"UNSAFE_ARCHIVE_PATH:{name}")
            for required in REQUIRED_FILES:
                if required not in names:
                    failures.append(f"MISSING:{required}")
            for unexpected in sorted(set(names) - set(REQUIRED_FILES)):
                failures.append(f"UNEXPECTED:{unexpected}")
            if not failures:
                plugin = _load_json_bytes(zf.read("plugin.json"), "plugin.json")
                mcp = _load_json_bytes(zf.read("mcp.json"), "mcp.json")
                if plugin.get("$schema") != PLUGIN_SCHEMA:
                    failures.append("PLUGIN_SCHEMA_MISMATCH")
                if plugin.get("name") != PLUGIN_NAME:
                    failures.append("PLUGIN_NAME_MISMATCH")
                if mcp.get("$schema") != MCP_SCHEMA:
                    failures.append("MCP_SCHEMA_MISMATCH")
                servers = mcp.get("mcpServers")
                if not isinstance(servers, Mapping):
                    failures.append("MCP_SERVERS_MISSING")
                else:
                    server = servers.get("gremlin")
                    if not isinstance(server, Mapping):
                        failures.append("GREMLIN_MCP_SERVER_MISSING")
                    else:
                        endpoint_value = server.get("url")
                        endpoint = endpoint_value if isinstance(endpoint_value, str) else None
                        gate = endpoint_gate(endpoint)
                        if gate.status != "PASS":
                            failures.append(gate.detail)
                        if server.get("type") != REMOTE_TRANSPORT:
                            failures.append("MCP_TRANSPORT_MUST_BE_STREAMABLE_HTTP")
                skill = zf.read("skills/gremlin/SKILL.md").decode("utf-8")
                if not re.search(r"(?m)^name:\s*gremlin\s*$", skill):
                    failures.append("SKILL_NAME_MISSING")
                if "/dev/shm" in skill or "localhost" in skill.lower():
                    failures.append("SKILL_CONTAINS_LOCAL_ACCOUNT_DEPENDENCY")
    except (OSError, zipfile.BadZipFile, ValueError, UnicodeDecodeError) as exc:
        failures.append(f"ARCHIVE_INVALID:{type(exc).__name__}")
    return {
        "schema": SCHEMA,
        "status": "PASS" if not failures else "FAIL",
        "artifact": str(target),
        "endpoint": endpoint,
        "failures": failures
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan, build, or inspect a clean-account GREMLIN ChatGPT plugin package")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--inspect", metavar="ZIP")
    parser.add_argument("--endpoint", help="remote HTTPS GREMLIN MCP endpoint ending in /mcp")
    parser.add_argument("--output", default="GREMLIN-ChatGPT-Plugin-v1.zip")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args()
    if args.inspect:
        payload = inspect_zip(args.inspect)
        code = 0 if payload["status"] == "PASS" else 2
    else:
        plan = build_plan(args.endpoint)
        if args.plan:
            payload = {
                "schema": SCHEMA,
                "status": "PACKAGE_READY" if plan.package_ready else "BLOCKED",
                "plan": plan.as_dict()
            }
            code = 0 if plan.package_ready else 2
        elif not plan.package_ready:
            payload = {"schema": SCHEMA, "status": "BLOCKED", "plan": plan.as_dict()}
            code = 2
        else:
            payload = build_zip(plan.endpoint or "", args.output)
            code = 0
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(payload["status"])
        if payload["status"] == "BLOCKED":
            print(payload["plan"]["blocker"])
        elif payload["status"] == "PACKAGE_READY":
            print(payload.get("artifact", ""))
            print("NEXT_REQUIRED_GATE: CHATGPT_HOST_ADMISSION")
        else:
            print(payload.get("artifact", ""))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
