from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping

from .paths import GremlinPaths


INTEGRATION_SCHEMA = "GREMLIN_MCP_INTEGRATION_RECEIPT_V0_1"


@dataclass(frozen=True)
class IntegrationReceipt:
    schema: str
    status: str
    client_id: str
    config_path: str
    backup_path: str | None
    before_sha256: str | None
    after_sha256: str
    server_name: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load(path: Path) -> tuple[dict[str, Any], bytes | None]:
    if not path.exists():
        return {}, None
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"MCP client config is not valid UTF-8 JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("MCP client config root must be a JSON object")
    return value, raw


def _atomic_json_write(path: Path, value: Mapping[str, Any], *, original_mode: int | None) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if original_mode is not None:
            os.chmod(temp, original_mode)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()
    return payload


def gremlin_stdio_entry(paths: GremlinPaths) -> dict[str, Any]:
    executable = (
        os.path.join(paths.install_root, "gremlin-product-mcp.exe")
        if paths.platform == "windows"
        else "/usr/bin/gremlin-product-mcp"
    )
    public_key = os.path.join(paths.shared_data_root, "issuer-public.pem")
    return {
        "command": executable,
        "args": ["--transport", "stdio"],
        "env": {
            "GREMLIN_LICENSE_PATH": paths.license_file,
            "GREMLIN_LICENSE_PUBLIC_KEY": public_key,
            "GREMLIN_CLIENT_PROFILE": paths.client_profile_file,
            "GREMLIN_MCP_STATE_PATH": paths.state_db,
        },
    }


def inspect_json_mcp(path: str | Path, *, server_name: str = "gremlin") -> dict[str, Any]:
    target = Path(path)
    config, raw = _load(target)
    servers = config.get("mcpServers")
    if servers is not None and not isinstance(servers, dict):
        raise ValueError("mcpServers must be a JSON object when present")
    return {
        "schema": "GREMLIN_MCP_INTEGRATION_INSPECT_V0_1",
        "config_path": str(target),
        "exists": target.exists(),
        "sha256": _sha256(raw) if raw is not None else None,
        "server_name": server_name,
        "gremlin_present": bool(isinstance(servers, dict) and server_name in servers),
        "server_count": len(servers or {}),
    }


def install_json_mcp(
    *,
    client_id: str,
    config_path: str | Path,
    entry: Mapping[str, Any],
    backup_root: str | Path,
    server_name: str = "gremlin",
) -> IntegrationReceipt:
    path = Path(config_path)
    config, before = _load(path)
    servers = config.get("mcpServers")
    if servers is None:
        servers = {}
        config["mcpServers"] = servers
    if not isinstance(servers, dict):
        raise ValueError("mcpServers must be a JSON object")

    backup_path: Path | None = None
    before_sha = _sha256(before) if before is not None else None
    original_mode = (path.stat().st_mode & 0o777) if path.exists() else None
    if before is not None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_dir = Path(backup_root) / client_id
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{path.name}.{stamp}.{before_sha[:12]}.bak"
        backup_path.write_bytes(before)
        if original_mode is not None:
            os.chmod(backup_path, original_mode)

    servers[server_name] = dict(entry)
    after = _atomic_json_write(path, config, original_mode=original_mode)
    # Reread and validate the exact installed object after replacement.
    installed, reread = _load(path)
    installed_servers = installed.get("mcpServers")
    if not isinstance(installed_servers, dict) or installed_servers.get(server_name) != dict(entry):
        if backup_path is not None:
            shutil.copy2(backup_path, path)
        raise RuntimeError("MCP integration verification failed; original configuration restored when available")
    return IntegrationReceipt(
        schema=INTEGRATION_SCHEMA,
        status="INSTALLED",
        client_id=client_id,
        config_path=str(path),
        backup_path=str(backup_path) if backup_path else None,
        before_sha256=before_sha,
        after_sha256=_sha256(reread if reread is not None else after),
        server_name=server_name,
    )


def remove_json_mcp(
    *,
    client_id: str,
    config_path: str | Path,
    backup_root: str | Path,
    server_name: str = "gremlin",
) -> IntegrationReceipt:
    path = Path(config_path)
    config, before = _load(path)
    if before is None:
        raise ValueError("MCP client config does not exist")
    servers = config.get("mcpServers")
    if not isinstance(servers, dict):
        raise ValueError("mcpServers must be a JSON object")

    before_sha = _sha256(before)
    mode = path.stat().st_mode & 0o777
    backup_dir = Path(backup_root) / client_id
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = backup_dir / f"{path.name}.{stamp}.{before_sha[:12]}.bak"
    backup_path.write_bytes(before)
    os.chmod(backup_path, mode)

    servers.pop(server_name, None)
    after = _atomic_json_write(path, config, original_mode=mode)
    reread, reread_raw = _load(path)
    reread_servers = reread.get("mcpServers")
    if not isinstance(reread_servers, dict) or server_name in reread_servers:
        shutil.copy2(backup_path, path)
        raise RuntimeError("MCP integration removal verification failed; original configuration restored")
    return IntegrationReceipt(
        schema=INTEGRATION_SCHEMA,
        status="REMOVED",
        client_id=client_id,
        config_path=str(path),
        backup_path=str(backup_path),
        before_sha256=before_sha,
        after_sha256=_sha256(reread_raw if reread_raw is not None else after),
        server_name=server_name,
    )
