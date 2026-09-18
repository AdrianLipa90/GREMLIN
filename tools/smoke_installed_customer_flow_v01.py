from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
from typing import Any


def run_json(
    command: list[str],
    *,
    stdin_text: str | None = None,
    allowed_codes: set[int] | None = None,
) -> dict[str, Any]:
    allowed = {0} if allowed_codes is None else allowed_codes
    result = subprocess.run(
        command,
        input=stdin_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode not in allowed:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"command did not return JSON: {' '.join(command)}\nstdout: {result.stdout}\nstderr: {result.stderr}"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"command returned non-object JSON: {' '.join(command)}")
    return payload


def customer_home(platform: str) -> Path:
    key = "USERPROFILE" if platform == "windows" else "HOME"
    value = str(os.environ.get(key) or "").strip()
    if not value:
        raise RuntimeError(f"{key} is required for installed customer smoke")
    return Path(value)


def smoke(*, ctl: Path, platform: str, license_key: str) -> dict[str, Any]:
    if not ctl.is_file():
        raise RuntimeError(f"installed gremlinctl is missing: {ctl}")
    key = license_key.strip()
    if not key.startswith("GRM1-"):
        raise RuntimeError("customer smoke license is not a GRM1 key")

    home = customer_home(platform)
    cursor_config = home / ".cursor" / "mcp.json"
    cursor_config.parent.mkdir(parents=True, exist_ok=True)
    original = cursor_config.read_bytes() if cursor_config.exists() else None
    sentinel = {
        "mcpServers": {
            "customer-existing-server": {
                "command": "customer-existing-command",
                "args": ["--untouched"],
            }
        },
        "customerSetting": {"must_survive": True},
    }

    try:
        cursor_config.write_text(json.dumps(sentinel, indent=2) + "\n", encoding="utf-8")

        activation = run_json(
            [str(ctl), "license", "activate", "--stdin", "--platform", platform, "--json"],
            stdin_text=key,
        )
        if activation.get("status") != "ACTIVE":
            raise RuntimeError(f"license activation did not become ACTIVE: {activation}")

        license_status = run_json([str(ctl), "license", "status", "--platform", platform, "--json"])
        if license_status.get("status") != "ACTIVE":
            raise RuntimeError(f"installed license status is not ACTIVE: {license_status}")

        profile_status = run_json([str(ctl), "profile", "status", "--platform", platform, "--json"])
        if profile_status.get("status") != "NOT_CONFIGURED":
            raise RuntimeError(
                "release smoke entitlement must allow startup before an optional customer profile is delivered"
            )

        providers_before = run_json(
            [str(ctl), "integrations", "providers", "--platform", platform, "--json"]
        )
        provider_ids = {str(item.get("provider_id")) for item in providers_before.get("providers", [])}
        required = {"codex", "opencode", "claude-code", "gemini", "cursor", "vscode", "windsurf"}
        if platform == "windows":
            required.add("claude-desktop")
        if not required.issubset(provider_ids):
            raise RuntimeError(f"provider matrix missing: {sorted(required - provider_ids)}")
        if platform == "linux" and "claude-desktop" in provider_ids:
            raise RuntimeError("Linux provider matrix contains Windows-only Claude Desktop")

        connected = run_json(
            [str(ctl), "integrations", "connect", "cursor", "--platform", platform, "--json"]
        )
        if connected.get("status") != "CONFIGURED_UNVERIFIED":
            raise RuntimeError(
                "Cursor JSON integration must configure without claiming live connectivity: "
                f"{connected}"
            )

        # JSON-config providers intentionally do not claim a live MCP session from
        # configuration presence alone. The CLI therefore returns exit code 1 for
        # the unverified test state while still emitting the structured receipt.
        tested = run_json(
            [str(ctl), "integrations", "test", "cursor", "--platform", platform, "--json"],
            allowed_codes={1},
        )
        if tested.get("status") != "REGISTERED_UNVERIFIED":
            raise RuntimeError(
                "Cursor registration test must remain fail-loud until the real client "
                f"proves a live MCP runtime: {tested}"
            )

        merged = json.loads(cursor_config.read_text(encoding="utf-8"))
        if merged.get("customerSetting") != {"must_survive": True}:
            raise RuntimeError("GREMLIN modified unrelated customer config")
        servers = merged.get("mcpServers") or {}
        if "customer-existing-server" not in servers or "gremlin" not in servers:
            raise RuntimeError("MCP merge lost the existing server or failed to add GREMLIN")

        ready = run_json([str(ctl), "ready", "--platform", platform, "--json"])
        if ready.get("status") != "ACTION_REQUIRED":
            raise RuntimeError(
                "readiness must stay ACTION_REQUIRED until a real client verifies "
                f"the live MCP session: {ready}"
            )
        if (ready.get("product") or {}).get("status") != "LICENSED":
            raise RuntimeError("readiness lost the LICENSED product state")
        if not bool((ready.get("runtime") or {}).get("available")):
            raise RuntimeError("readiness did not detect the installed runtime")
        providers = ready.get("providers") or {}
        connected_ids = set(providers.get("connected_ids") or [])
        unverified_ids = set(providers.get("unverified_ids") or [])
        if "cursor" in connected_ids:
            raise RuntimeError("readiness falsely promoted Cursor configuration to CONNECTED")
        if "cursor" not in unverified_ids:
            raise RuntimeError("readiness did not retain Cursor as registered/unverified")
        actions = set(ready.get("actions") or [])
        expected_action = "Verify a live GREMLIN MCP connection in one detected AI client"
        if expected_action not in actions:
            raise RuntimeError(f"readiness did not request live MCP verification: {ready}")

        disconnected = run_json(
            [str(ctl), "integrations", "disconnect", "cursor", "--platform", platform, "--json"]
        )
        if disconnected.get("status") != "DISCONNECTED":
            raise RuntimeError(f"Cursor disconnect failed: {disconnected}")

        after = json.loads(cursor_config.read_text(encoding="utf-8"))
        if after.get("customerSetting") != {"must_survive": True}:
            raise RuntimeError("Disconnect modified unrelated customer config")
        after_servers = after.get("mcpServers") or {}
        if "customer-existing-server" not in after_servers or "gremlin" in after_servers:
            raise RuntimeError("Disconnect did not preserve existing MCP servers cleanly")

        return {
            "schema": "GREMLIN_INSTALLED_CUSTOMER_SMOKE_V0_1",
            "status": "PASS",
            "platform": platform,
            "license_id": activation.get("license_id"),
            "provider": "cursor",
            "provider_connect_status": "CONFIGURED_UNVERIFIED",
            "provider_test_status": "REGISTERED_UNVERIFIED",
            "readiness_status_before_disconnect": "ACTION_REQUIRED",
            "live_connection_claim": False,
            "existing_config_preserved": True,
        }
    finally:
        if original is None:
            try:
                cursor_config.unlink()
            except FileNotFoundError:
                pass
        else:
            cursor_config.write_bytes(original)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke the installed GREMLIN customer activation and MCP flow")
    parser.add_argument("--ctl", required=True, type=Path)
    parser.add_argument("--platform", required=True, choices=("windows", "linux"))
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--license-key-file", type=Path)
    source.add_argument("--license-key-env", help="environment variable containing the GRM1 key; only the variable name appears in process arguments")
    args = parser.parse_args()
    if args.license_key_file is not None:
        key = args.license_key_file.read_text(encoding="utf-8")
    else:
        key = str(os.environ.get(args.license_key_env) or "")
        if not key:
            raise SystemExit(f"license key environment variable is empty: {args.license_key_env}")
    print(json.dumps(smoke(ctl=args.ctl, platform=args.platform, license_key=key), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
