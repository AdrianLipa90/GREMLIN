from __future__ import annotations

from pathlib import Path
from typing import Any

from gremlin_mcp.product import ProductRuntime

from .integrations import gremlin_stdio_entry
from .license_activation import installed_license_status, resolve_public_key_path
from .paths import GremlinPaths
from .provider_integrations import list_providers


READINESS_SCHEMA = "GREMLIN_CUSTOMER_READINESS_V0_1"


def evaluate_readiness(paths: GremlinPaths) -> dict[str, Any]:
    license_state = installed_license_status(paths)
    public_key = resolve_public_key_path(paths)
    profile_path = Path(paths.client_profile_file)

    runtime = ProductRuntime.from_paths(
        license_path=paths.license_file if Path(paths.license_file).is_file() else None,
        public_key_path=str(public_key) if public_key.is_file() else None,
        # Always pass the canonical path. ProductRuntime decides whether a missing
        # profile is optional or mandatory from signed license metadata.
        profile_path=str(profile_path),
        require_license=True,
    )
    product = runtime.status()
    providers = list_providers(paths)
    provider_rows = list(providers.get("providers") or [])
    detected = [row for row in provider_rows if bool(row.get("detected"))]
    connected = [row for row in provider_rows if bool(row.get("connected"))]

    entry = gremlin_stdio_entry(paths)
    executable = Path(str(entry["command"]))
    runtime_available = executable.is_file()

    actions: list[str] = []
    if license_state.get("status") != "ACTIVE":
        actions.append("Activate your GREMLIN license")
    if product.get("status") != "LICENSED":
        reason = str(product.get("reason") or "").strip()
        if reason == "required client profile is missing":
            actions.append("Import the customer-specific GREMLIN profile supplied with this license")
        else:
            actions.append("Resolve the product entitlement configuration")
    if not runtime_available:
        actions.append("Repair the GREMLIN runtime installation")
    if not detected:
        actions.append("Install or open a supported MCP-compatible AI client")
    elif not connected:
        actions.append("Connect GREMLIN to one detected AI client")

    status = "READY" if not actions else "ACTION_REQUIRED"
    return {
        "schema": READINESS_SCHEMA,
        "status": status,
        "platform": paths.platform,
        "license": license_state,
        "product": product,
        "runtime": {
            "available": runtime_available,
            "command": str(entry["command"]),
            "transport": "stdio",
        },
        "providers": {
            "detected": len(detected),
            "connected": len(connected),
            "connected_ids": [str(row.get("provider_id")) for row in connected],
        },
        "profile": {
            "configured": profile_path.is_file(),
            "path": str(profile_path),
        },
        "actions": actions,
    }
