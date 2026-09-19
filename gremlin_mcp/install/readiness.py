from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path
from typing import Any

from gremlin_mcp.product import ProductRuntime

from .integrations import gremlin_stdio_entry
from .license_activation import installed_license_status, resolve_public_key_path
from .mcp_probe import probe_product_mcp
from .paths import GremlinPaths
from .provider_integrations import list_providers


READINESS_SCHEMA = "GREMLIN_CUSTOMER_READINESS_V0_3"
_CONFIGURED_PROVIDER_STATES = frozenset({
    "CONNECTED",
    "REGISTERED",
    "REGISTERED_UNVERIFIED",
    "REGISTERED_RUNTIME_NOT_READY",
    "REGISTERED_RESTART_REQUIRED",
    "CONFIGURED_UNVERIFIED",
})
_UNVERIFIED_PROVIDER_STATES = _CONFIGURED_PROVIDER_STATES - {"CONNECTED"}
_INVALID_PROVIDER_STATES = frozenset({"CONFIG_INVALID"})


def _provider_rows(payload: Any) -> list[Mapping[str, Any]]:
    if not isinstance(payload, Mapping):
        raise RuntimeError("provider discovery returned a non-object payload")
    rows = payload.get("providers")
    if not isinstance(rows, list):
        raise RuntimeError("provider discovery payload must contain a providers list")
    normalized: list[Mapping[str, Any]] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise RuntimeError(f"provider discovery row {index} is not an object")
        provider_id = row.get("provider_id")
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise RuntimeError(f"provider discovery row {index} has invalid provider_id")
        provider_id = provider_id.strip()
        if provider_id in seen_ids:
            raise RuntimeError(f"provider discovery contains duplicate provider_id: {provider_id}")
        seen_ids.add(provider_id)

        detected = row.get("detected")
        connected = row.get("connected")
        if not isinstance(detected, bool):
            raise RuntimeError(f"provider discovery row {index} has non-boolean detected")
        if not isinstance(connected, bool):
            raise RuntimeError(f"provider discovery row {index} has non-boolean connected")
        status = row.get("connection_status")
        if not isinstance(status, str) or not status.strip():
            raise RuntimeError(f"provider discovery row {index} has invalid connection_status")
        status = status.strip()
        if connected and not detected:
            raise RuntimeError(f"provider discovery row {index} is connected but not detected")
        if connected != (status == "CONNECTED"):
            raise RuntimeError(
                f"provider discovery row {index} has inconsistent connected/connection_status state"
            )
        normalized.append(row)
    return normalized


def _runtime_command_available(command: str, platform: str) -> bool:
    executable = Path(command)
    if not executable.is_file():
        return False
    if platform == "windows":
        return True
    return os.access(executable, os.X_OK)


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
    provider_rows = _provider_rows(list_providers(paths))
    detected = [row for row in provider_rows if row.get("detected") is True]
    configured = [
        row for row in detected
        if row.get("connection_status") in _CONFIGURED_PROVIDER_STATES
    ]
    connected = [
        row
        for row in configured
        if row.get("connected") is True and row.get("connection_status") == "CONNECTED"
    ]
    unverified = [
        row
        for row in configured
        if row.get("connection_status") in _UNVERIFIED_PROVIDER_STATES
    ]
    invalid = [
        row
        for row in detected
        if row.get("connection_status") in _INVALID_PROVIDER_STATES
    ]

    entry = gremlin_stdio_entry(paths)
    command = entry.get("command") if isinstance(entry, Mapping) else None
    if not isinstance(command, str) or not command.strip():
        raise RuntimeError("GREMLIN stdio entry does not contain a valid command")
    command = command.strip()
    runtime_available = _runtime_command_available(command, paths.platform)

    handshake: dict[str, Any] = {
        "schema": "GREMLIN_MCP_RUNTIME_PROBE_V0_1",
        "status": "NOT_RUN",
        "transport": "stdio",
        "registry_exact": False,
        "detail": "product/license/runtime prerequisites are not satisfied",
    }
    if (
        license_state.get("status") == "ACTIVE"
        and product.get("status") == "LICENSED"
        and runtime_available
    ):
        raw_probe = probe_product_mcp(paths)
        if not isinstance(raw_probe, Mapping):
            raise RuntimeError("GREMLIN MCP runtime probe returned a non-object payload")
        handshake = dict(raw_probe)
        probe_status = handshake.get("status")
        if probe_status not in {"PASS", "FAIL"}:
            raise RuntimeError("GREMLIN MCP runtime probe returned an invalid status")

    actions: list[str] = []
    notices: list[str] = []
    if license_state.get("status") != "ACTIVE":
        actions.append("Activate your GREMLIN license")
    if product.get("status") != "LICENSED":
        reason = product.get("reason")
        if reason == "required client profile is missing":
            actions.append("Import the customer-specific GREMLIN profile supplied with this license")
        else:
            actions.append("Resolve the product entitlement configuration")
    if not runtime_available:
        actions.append("Repair the GREMLIN runtime installation")
    elif product.get("status") == "LICENSED" and handshake.get("status") != "PASS":
        actions.append("Repair or retry the GREMLIN MCP runtime handshake")

    if not detected:
        actions.append("Install or open a supported MCP-compatible AI client")
    elif not configured:
        if invalid:
            actions.append("Repair the invalid GREMLIN MCP configuration in one detected AI client")
        else:
            actions.append("Connect GREMLIN to one detected AI client")
    elif not connected:
        notices.append(
            "GREMLIN is configured in an AI client and the product MCP runtime is verified; "
            "the client has not independently reported a live GREMLIN session."
        )

    status = "READY" if not actions else "ACTION_REQUIRED"
    return {
        "schema": READINESS_SCHEMA,
        "status": status,
        "platform": paths.platform,
        "license": license_state,
        "product": product,
        "runtime": {
            "available": runtime_available,
            "command": command,
            "transport": "stdio",
            "handshake": handshake,
        },
        "providers": {
            "detected": len(detected),
            "configured": len(configured),
            "configured_ids": [row["provider_id"] for row in configured],
            # Backward-compatible field: connected means provider-reported live state only.
            "connected": len(connected),
            "connected_ids": [row["provider_id"] for row in connected],
            "live_connected": len(connected),
            "live_connected_ids": [row["provider_id"] for row in connected],
            "unverified": len(unverified),
            "unverified_ids": [row["provider_id"] for row in unverified],
            "invalid": len(invalid),
            "invalid_ids": [row["provider_id"] for row in invalid],
        },
        "profile": {
            "configured": profile_path.is_file(),
            "path": str(profile_path),
        },
        "notices": notices,
        "actions": actions,
    }

