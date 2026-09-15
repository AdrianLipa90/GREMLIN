from __future__ import annotations

from dataclasses import asdict, dataclass
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from typing import Callable, Mapping, Sequence

SCHEMA = "GREMLIN_OPENAI_SECURE_MCP_TUNNEL_V0_1"
VERSION = "0.1.0"
DEFAULT_PROFILE = "gremlin-chatgpt"
TUNNEL_ID_RE = re.compile(r"^tunnel_[A-Za-z0-9_-]{8,}$")


@dataclass(frozen=True)
class Gate:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class TunnelPlan:
    schema: str
    version: str
    profile: str
    tunnel_id: str | None
    tunnel_client: str | None
    mcp_command: str
    gates: tuple[Gate, ...]
    ready: bool
    state_paths: dict[str, str]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _default_mcp_command() -> str:
    # Avoid relying on a shell-installed console script. The module invocation
    # works from an editable install and from an installed wheel.
    exe = shlex.quote(sys.executable)
    return f"{exe} -m gremlin_mcp.server_with_hive --transport stdio"


def _default_state_paths(env: Mapping[str, str]) -> dict[str, str]:
    home = Path(str(env.get("HOME") or env.get("USERPROFILE") or ".")).expanduser()
    root = home / ".local" / "state" / "gremlin"
    return {
        "GREMLIN_MCP_STATE_PATH": str(env.get("GREMLIN_MCP_STATE_PATH") or root / "worker.sqlite3"),
        "GREMLIN_HIVE_STATE_PATH": str(env.get("GREMLIN_HIVE_STATE_PATH") or root / "hive.sqlite3"),
    }


def build_plan(
    *,
    env: Mapping[str, str] | None = None,
    profile: str = DEFAULT_PROFILE,
    mcp_command: str | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> TunnelPlan:
    environ = os.environ if env is None else env
    profile = str(profile).strip()
    if not profile:
        raise ValueError("profile must be non-empty")
    command = str(mcp_command or _default_mcp_command()).strip()
    if not command:
        raise ValueError("mcp_command must be non-empty")

    tunnel_client = which("tunnel-client")
    tunnel_id_raw = str(environ.get("GREMLIN_OPENAI_TUNNEL_ID") or environ.get("OPENAI_TUNNEL_ID") or "").strip()
    tunnel_id = tunnel_id_raw or None
    runtime_key = str(environ.get("CONTROL_PLANE_API_KEY") or "").strip()
    states = _default_state_paths(environ)

    gates: list[Gate] = []
    gates.append(Gate(
        "IDENTITY",
        "PASS" if tunnel_client else "FAIL",
        "tunnel-client executable resolved" if tunnel_client else "tunnel-client executable not found",
    ))
    gates.append(Gate(
        "TUNNEL_ID",
        "PASS" if tunnel_id and TUNNEL_ID_RE.fullmatch(tunnel_id) else "FAIL",
        "tunnel id present and structurally valid" if tunnel_id and TUNNEL_ID_RE.fullmatch(tunnel_id)
        else "set GREMLIN_OPENAI_TUNNEL_ID to a valid tunnel_... identifier",
    ))
    gates.append(Gate(
        "RUNTIME_KEY",
        "PASS" if runtime_key else "FAIL",
        "control-plane runtime key present (value not emitted)" if runtime_key
        else "CONTROL_PLANE_API_KEY is not set",
    ))
    gates.append(Gate(
        "MCP_STDIO",
        "PASS",
        "private GREMLIN MCP is configured for stdio; no public listener required",
    ))
    gates.append(Gate(
        "PERSISTENCE",
        "PASS",
        "durable worker and Hive SQLite paths are configured",
    ))

    ready = all(g.status == "PASS" for g in gates)
    return TunnelPlan(
        schema=SCHEMA,
        version=VERSION,
        profile=profile,
        tunnel_id=tunnel_id,
        tunnel_client=tunnel_client,
        mcp_command=command,
        gates=tuple(gates),
        ready=ready,
        state_paths=states,
    )


def init_command(plan: TunnelPlan) -> list[str]:
    if not plan.tunnel_client or not plan.tunnel_id:
        raise RuntimeError("IDENTITY/TUNNEL_ID gates must pass before init")
    return [
        plan.tunnel_client,
        "init",
        "--sample",
        "sample_mcp_stdio_local",
        "--profile",
        plan.profile,
        "--tunnel-id",
        plan.tunnel_id,
        "--mcp-command",
        plan.mcp_command,
    ]


def doctor_command(plan: TunnelPlan) -> list[str]:
    if not plan.tunnel_client:
        raise RuntimeError("IDENTITY gate must pass before doctor")
    return [plan.tunnel_client, "doctor", "--profile", plan.profile, "--explain"]


def run_command(plan: TunnelPlan) -> list[str]:
    if not plan.tunnel_client:
        raise RuntimeError("IDENTITY gate must pass before run")
    return [plan.tunnel_client, "run", "--profile", plan.profile]


def _child_env(plan: TunnelPlan, source: Mapping[str, str] | None = None) -> dict[str, str]:
    out = dict(os.environ if source is None else source)
    out.update(plan.state_paths)
    return out


def _run(
    command: Sequence[str],
    *,
    env: Mapping[str, str],
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> subprocess.CompletedProcess[str]:
    return runner(
        list(command),
        env=dict(env),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def setup_and_doctor(
    plan: TunnelPlan,
    *,
    env: Mapping[str, str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    if not plan.ready:
        return {"schema": SCHEMA, "status": "BLOCKED", "plan": plan.as_dict(), "steps": []}
    child_env = _child_env(plan, env)
    steps: list[dict[str, object]] = []
    for name, command in (("init", init_command(plan)), ("doctor", doctor_command(plan))):
        result = _run(command, env=child_env, runner=runner)
        steps.append({
            "name": name,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        })
        if result.returncode != 0:
            return {"schema": SCHEMA, "status": "FAIL", "plan": plan.as_dict(), "steps": steps}
    return {"schema": SCHEMA, "status": "READY", "plan": plan.as_dict(), "steps": steps}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fail-closed GREMLIN Secure MCP Tunnel bootstrap")
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--mcp-command", default=None)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--setup", action="store_true", help="initialize profile and run tunnel-client doctor")
    mode.add_argument("--run", action="store_true", help="run the already initialized tunnel profile")
    parser.add_argument("--json", action="store_true", help="emit machine-readable gate/receipt output")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    plan = build_plan(profile=args.profile, mcp_command=args.mcp_command)
    if args.setup:
        payload = setup_and_doctor(plan)
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(payload["status"])
            for gate in plan.gates:
                print(f"{gate.status} {gate.name}: {gate.detail}")
        raise SystemExit(0 if payload["status"] == "READY" else 2)
    if args.run:
        if not plan.ready:
            if args.json:
                print(json.dumps({"schema": SCHEMA, "status": "BLOCKED", "plan": plan.as_dict()}, indent=2, sort_keys=True))
            else:
                for gate in plan.gates:
                    print(f"{gate.status} {gate.name}: {gate.detail}")
            raise SystemExit(2)
        command = run_command(plan)
        os.execvpe(command[0], command, _child_env(plan))

    payload = {"schema": SCHEMA, "status": "READY" if plan.ready else "BLOCKED", "plan": plan.as_dict()}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for gate in plan.gates:
            print(f"{gate.status} {gate.name}: {gate.detail}")
        print("READY" if plan.ready else "BLOCKED")
    raise SystemExit(0 if plan.ready else 2)


if __name__ == "__main__":
    main()
