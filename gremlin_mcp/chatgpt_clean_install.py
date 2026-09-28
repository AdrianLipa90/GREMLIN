from __future__ import annotations

from dataclasses import asdict, dataclass
import argparse
import json
import os
from ipaddress import ip_address
import shutil
from typing import Callable, Mapping, Sequence
from urllib.parse import urlparse

from . import openai_tunnel


SCHEMA = "GREMLIN_CHATGPT_CLEAN_INSTALL_V1"
VERSION = "1.0.0"

_TRUE = {"1", "true", "yes", "on", "enabled", "pass"}
_FALSE = {"0", "false", "no", "off", "disabled", "fail"}


@dataclass(frozen=True)
class Gate:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class CleanInstallPlan:
    schema: str
    version: str
    status: str
    transport: str | None
    remote_mcp_url: str | None
    capability_mode: str
    gates: tuple[Gate, ...]
    next_action: str | None
    assumptions: dict[str, bool]
    tunnel: dict[str, object] | None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _env_text(env: Mapping[str, str], name: str) -> str | None:
    raw = env.get(name)
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError(f"{name} must be a string")
    text = raw.strip()
    return text or None


def _optional_bool(env: Mapping[str, str], name: str) -> bool | None:
    text = _env_text(env, name)
    if text is None:
        return None
    normalized = text.lower()
    if normalized in _TRUE:
        return True
    if normalized in _FALSE:
        return False
    raise ValueError(f"{name} must be one of: true/false, yes/no, on/off, 1/0")


def _normalize_surface(value: str | None) -> str:
    text = (value or "unknown").strip().lower()
    aliases = {
        "browser": "web",
        "chatgpt-web": "web",
        "android": "mobile",
        "ios": "mobile",
        "app": "mobile",
    }
    return aliases.get(text, text)


def _normalize_scan(value: str | None) -> str:
    text = (value or "NOT_RUN").strip().upper().replace("-", "_")
    aliases = {"READY": "PASS", "SUCCESS": "PASS", "ERROR": "FAIL"}
    text = aliases.get(text, text)
    if text not in {"PASS", "FAIL", "NOT_RUN"}:
        raise ValueError("tool scan status must be PASS, FAIL, or NOT_RUN")
    return text


def _normalize_capability(value: str | None) -> str:
    text = (value or "unknown").strip().lower()
    aliases = {"read-only": "read", "readonly": "read", "write": "full"}
    text = aliases.get(text, text)
    if text not in {"unknown", "read", "full"}:
        raise ValueError("capability mode must be unknown, read, or full")
    return text


def validate_remote_mcp_url(value: str | None) -> tuple[bool, str]:
    if not value:
        return False, "set GREMLIN_CHATGPT_REMOTE_MCP_URL to the deployed HTTPS /mcp endpoint"
    try:
        parsed = urlparse(value)
    except ValueError as exc:
        return False, f"invalid MCP URL: {exc}"
    if parsed.scheme.lower() != "https":
        return False, "remote MCP endpoint must use HTTPS"
    if not parsed.hostname:
        return False, "remote MCP endpoint must include a hostname"
    if parsed.username or parsed.password:
        return False, "credentials must not be embedded in the MCP URL"
    if parsed.query or parsed.fragment:
        return False, "MCP URL must not contain query parameters or fragments"
    path = parsed.path.rstrip("/")
    if not path.endswith("/mcp"):
        return False, "remote MCP endpoint path must end in /mcp"

    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"}:
        return False, "ChatGPT cannot connect directly to localhost; deploy remotely or use Secure MCP Tunnel"
    try:
        addr = ip_address(host)
    except ValueError:
        addr = None
    if addr is not None and (addr.is_loopback or addr.is_private or addr.is_link_local):
        return False, "ChatGPT cannot connect directly to a private/loopback IP; deploy remotely or use Secure MCP Tunnel"
    return True, "remote HTTPS MCP endpoint is structurally valid"


def _first_blocker(gates: Sequence[Gate]) -> Gate | None:
    return next((gate for gate in gates if gate.status != "PASS"), None)


def _next_action(blocker: Gate | None, transport: str | None) -> str | None:
    if blocker is None:
        return None
    actions = {
        "SURFACE": "Open ChatGPT on the web; custom MCP/plugin setup is not admitted from the mobile surface.",
        "DEVELOPER_MODE": "Enable ChatGPT developer mode for this account/workspace before registering GREMLIN.",
        "TRANSPORT": (
            "Provide a deployed HTTPS /mcp endpoint with GREMLIN_CHATGPT_REMOTE_MCP_URL, "
            "or configure Secure MCP Tunnel with tunnel-client, a tunnel_id, and CONTROL_PLANE_API_KEY."
        ),
        "APP_REGISTRATION": (
            "Create the GREMLIN app/plugin in ChatGPT developer mode using the admitted MCP transport, "
            "then set GREMLIN_CHATGPT_APP_CREATED=true."
        ),
        "TOOL_SCAN": (
            "Run ChatGPT Scan Tools for GREMLIN. Set GREMLIN_CHATGPT_TOOL_SCAN_STATUS=PASS only after the scan succeeds."
        ),
        "CAPABILITY_MODE": "Record the actual ChatGPT capability exposed to this account as read or full.",
    }
    action = actions.get(blocker.name, blocker.detail)
    if blocker.name == "APP_REGISTRATION" and transport == "secure-tunnel":
        action += " Use the Secure MCP Tunnel-backed GREMLIN endpoint/profile for registration."
    return action


def build_plan(
    *,
    env: Mapping[str, str] | None = None,
    surface: str | None = None,
    developer_mode: bool | None = None,
    remote_mcp_url: str | None = None,
    app_created: bool | None = None,
    tool_scan_status: str | None = None,
    transport: str = "auto",
    capability_mode: str | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> CleanInstallPlan:
    environ = os.environ if env is None else env

    resolved_surface = _normalize_surface(surface or _env_text(environ, "GREMLIN_CHATGPT_SURFACE"))
    resolved_developer_mode = developer_mode
    if resolved_developer_mode is None:
        resolved_developer_mode = _optional_bool(environ, "GREMLIN_CHATGPT_DEVELOPER_MODE")

    resolved_remote = remote_mcp_url or _env_text(environ, "GREMLIN_CHATGPT_REMOTE_MCP_URL")

    resolved_app_created = app_created
    if resolved_app_created is None:
        resolved_app_created = _optional_bool(environ, "GREMLIN_CHATGPT_APP_CREATED")

    resolved_scan = _normalize_scan(
        tool_scan_status or _env_text(environ, "GREMLIN_CHATGPT_TOOL_SCAN_STATUS")
    )
    resolved_capability = _normalize_capability(
        capability_mode or _env_text(environ, "GREMLIN_CHATGPT_CAPABILITY_MODE")
    )

    requested_transport = transport.strip().lower()
    if requested_transport not in {"auto", "remote", "secure-tunnel"}:
        raise ValueError("transport must be auto, remote, or secure-tunnel")

    remote_ok, remote_detail = validate_remote_mcp_url(resolved_remote)
    tunnel_plan = openai_tunnel.build_plan(env=environ, which=which)

    if requested_transport == "remote":
        selected_transport = "remote" if remote_ok else None
    elif requested_transport == "secure-tunnel":
        selected_transport = "secure-tunnel" if tunnel_plan.ready else None
    else:
        if remote_ok:
            selected_transport = "remote"
        elif tunnel_plan.ready:
            selected_transport = "secure-tunnel"
        else:
            selected_transport = None

    if selected_transport == "remote":
        transport_detail = remote_detail
    elif selected_transport == "secure-tunnel":
        transport_detail = "Secure MCP Tunnel admission gates passed"
    else:
        tunnel_failures = [g.name for g in tunnel_plan.gates if g.status != "PASS"]
        transport_detail = (
            f"remote={remote_detail}; secure-tunnel blocked by {','.join(tunnel_failures) or 'UNKNOWN'}"
        )

    gates = (
        Gate(
            "SURFACE",
            "PASS" if resolved_surface == "web" else "FAIL",
            "ChatGPT web surface confirmed" if resolved_surface == "web"
            else f"surface={resolved_surface}; clean MCP/plugin onboarding requires ChatGPT web",
        ),
        Gate(
            "DEVELOPER_MODE",
            "PASS" if resolved_developer_mode is True else "FAIL",
            "developer mode explicitly confirmed" if resolved_developer_mode is True
            else "developer mode is not explicitly confirmed for this account/workspace",
        ),
        Gate(
            "TRANSPORT",
            "PASS" if selected_transport else "FAIL",
            transport_detail,
        ),
        Gate(
            "APP_REGISTRATION",
            "PASS" if resolved_app_created is True else "FAIL",
            "GREMLIN app/plugin creation explicitly confirmed" if resolved_app_created is True
            else "GREMLIN app/plugin creation has not been confirmed",
        ),
        Gate(
            "TOOL_SCAN",
            "PASS" if resolved_scan == "PASS" else "FAIL",
            "ChatGPT tool scan explicitly passed" if resolved_scan == "PASS"
            else f"tool scan status={resolved_scan}",
        ),
        Gate(
            "CAPABILITY_MODE",
            "PASS" if resolved_capability in {"read", "full"} else "FAIL",
            f"account capability recorded as {resolved_capability}" if resolved_capability != "unknown"
            else "record the actual account capability as read or full; do not infer it from prior accounts",
        ),
    )
    blocker = _first_blocker(gates)
    status = "READY" if blocker is None else f"BLOCKED:{blocker.name}"

    tunnel_summary = tunnel_plan.as_dict()
    return CleanInstallPlan(
        schema=SCHEMA,
        version=VERSION,
        status=status,
        transport=selected_transport,
        remote_mcp_url=resolved_remote if selected_transport == "remote" else None,
        capability_mode=resolved_capability,
        gates=gates,
        next_action=_next_action(blocker, selected_transport),
        assumptions={
            "requires_prior_chat_history": False,
            "requires_chatgpt_memory": False,
            "requires_noema_library": False,
            "requires_existing_gremlin_account_state": False,
            "requires_successful_tool_scan_for_ready": True,
        },
        tunnel=tunnel_summary,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail-closed GREMLIN clean-account bootstrap for ChatGPT"
    )
    parser.add_argument("--surface", choices=("web", "mobile", "unknown"))
    parser.add_argument("--developer-mode", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--remote-mcp-url")
    parser.add_argument("--app-created", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--tool-scan-status", choices=("PASS", "FAIL", "NOT_RUN"))
    parser.add_argument("--transport", choices=("auto", "remote", "secure-tunnel"), default="auto")
    parser.add_argument("--capability-mode", choices=("unknown", "read", "full"))
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = build_plan(
        surface=args.surface,
        developer_mode=args.developer_mode,
        remote_mcp_url=args.remote_mcp_url,
        app_created=args.app_created,
        tool_scan_status=args.tool_scan_status,
        transport=args.transport,
        capability_mode=args.capability_mode,
    )
    payload = plan.as_dict()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(plan.status)
        for gate in plan.gates:
            print(f"{gate.status} {gate.name}: {gate.detail}")
        if plan.next_action:
            print(f"NEXT: {plan.next_action}")
    return 0 if plan.status == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
