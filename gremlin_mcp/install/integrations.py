from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import ntpath
import os
from pathlib import Path
import posixpath
import re
import tempfile
from typing import Any, Mapping

from .paths import GremlinPaths


INTEGRATION_SCHEMA = "GREMLIN_MCP_INTEGRATION_RECEIPT_V0_1"
_CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
_SERVER_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")


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


def _client_id(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("client_id must be a string")
    candidate = value.strip()
    if candidate in {".", ".."} or not _CLIENT_ID_RE.fullmatch(candidate):
        raise ValueError("client_id must be a safe identifier matching [A-Za-z0-9][A-Za-z0-9._-]{0,95}")
    return candidate


def _server_name(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("server_name must be a string")
    candidate = value.strip()
    if candidate in {".", ".."} or not _SERVER_NAME_RE.fullmatch(candidate):
        raise ValueError("server_name must be a safe identifier matching [A-Za-z0-9][A-Za-z0-9._-]{0,95}")
    return candidate


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_object_no_duplicates(raw: bytes, path: Path) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"MCP client config is not valid UTF-8 JSON: {path}: {exc}") from exc

    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise ValueError(f"MCP client config contains duplicate JSON key: {key}")
            out[key] = value
        return out

    try:
        value = json.loads(text, object_pairs_hook=hook)
    except ValueError as exc:
        if str(exc).startswith("MCP client config contains duplicate JSON key"):
            raise
        if isinstance(exc, json.JSONDecodeError):
            raise ValueError(f"MCP client config is not valid UTF-8 JSON: {path}: {exc}") from exc
        raise
    if not isinstance(value, dict):
        raise ValueError("MCP client config root must be a JSON object")
    return value


def _load(path: Path) -> tuple[dict[str, Any], bytes | None]:
    if not path.exists():
        return {}, None
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"unable to read MCP client config: {path}: {exc}") from exc
    return _json_object_no_duplicates(raw, path), raw


def _current_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise RuntimeError(f"unable to re-read MCP client config before replacement: {path}: {exc}") from exc


def _assert_unchanged(path: Path, expected_before: bytes | None) -> None:
    current = _current_bytes(path)
    if current != expected_before:
        raise RuntimeError("MCP client config changed during integration update; refusing to overwrite newer bytes")


def _atomic_json_write(
    path: Path,
    value: Mapping[str, Any],
    *,
    original_mode: int | None,
    expected_before: bytes | None,
) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = (
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("MCP client configuration update must be finite JSON") from exc

    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp = Path(temp_name)
    fd_open = True
    try:
        if original_mode is not None and os.name != "nt":
            os.fchmod(fd, original_mode)
        handle = os.fdopen(fd, "wb")
        fd_open = False
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if original_mode is not None and os.name == "nt":
            os.chmod(temp, original_mode)

        staged, staged_raw = _load(temp)
        if staged_raw != payload or staged != dict(value):
            raise RuntimeError("staged MCP client configuration verification mismatch")

        _assert_unchanged(path, expected_before)
        os.replace(temp, path)
    finally:
        if fd_open:
            os.close(fd)
        if temp.exists():
            temp.unlink()
    return payload


def _restore_pre_update_state(
    path: Path,
    *,
    before: bytes | None,
    written: bytes,
    original_mode: int | None,
) -> None:
    """Restore the exact pre-update bytes without overwriting a concurrent writer."""
    _assert_unchanged(path, written)
    if before is None:
        path.unlink()
        if path.exists():
            raise RuntimeError("failed to remove newly-created MCP config during rollback")
        return

    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".rollback", dir=str(path.parent))
    temp = Path(temp_name)
    fd_open = True
    try:
        if original_mode is not None and os.name != "nt":
            os.fchmod(fd, original_mode)
        handle = os.fdopen(fd, "wb")
        fd_open = False
        with handle:
            handle.write(before)
            handle.flush()
            os.fsync(handle.fileno())
        if original_mode is not None and os.name == "nt":
            os.chmod(temp, original_mode)
        _assert_unchanged(path, written)
        os.replace(temp, path)
    finally:
        if fd_open:
            os.close(fd)
        if temp.exists():
            temp.unlink()

    if _current_bytes(path) != before:
        raise RuntimeError("MCP config rollback verification failed")


def _verify_or_rollback(
    path: Path,
    *,
    before: bytes | None,
    written: bytes,
    original_mode: int | None,
    verifier,
    operation: str,
) -> None:
    try:
        verifier()
    except BaseException as exc:
        try:
            _restore_pre_update_state(
                path,
                before=before,
                written=written,
                original_mode=original_mode,
            )
        except BaseException as rollback_exc:
            raise RuntimeError(
                f"MCP integration {operation} verification failed and automatic rollback failed or was unsafe: {rollback_exc}"
            ) from exc
        raise RuntimeError(
            f"MCP integration {operation} verification failed; pre-update state restored"
        ) from exc


def _write_backup(path: Path, data: bytes, *, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, mode if os.name != "nt" else 0o600)
    fd_open = True
    try:
        handle = os.fdopen(fd, "wb")
        fd_open = False
        with handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if os.name == "nt":
            os.chmod(path, mode)
    except BaseException as exc:
        try:
            path.unlink(missing_ok=True)
        except OSError as cleanup_exc:
            raise RuntimeError(
                f"MCP config backup write failed and partial backup cleanup also failed: {cleanup_exc}"
            ) from exc
        raise
    finally:
        if fd_open:
            os.close(fd)


def gremlin_stdio_entry(paths: GremlinPaths) -> dict[str, Any]:
    if paths.platform == "windows":
        executable = ntpath.join(paths.install_root, "gremlin-product-mcp.exe")
        public_key = ntpath.join(paths.shared_data_root, "issuer-public.pem")
    else:
        executable = "/usr/bin/gremlin-product-mcp"
        public_key = posixpath.join(paths.shared_data_root, "issuer-public.pem")
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
    safe_server = _server_name(server_name)
    config, raw = _load(target)
    servers = config.get("mcpServers")
    if servers is not None and not isinstance(servers, dict):
        raise ValueError("mcpServers must be a JSON object when present")
    return {
        "schema": "GREMLIN_MCP_INTEGRATION_INSPECT_V0_1",
        "config_path": str(target),
        "exists": target.exists(),
        "sha256": _sha256(raw) if raw is not None else None,
        "server_name": safe_server,
        "gremlin_present": isinstance(servers, dict) and safe_server in servers,
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
    safe_client = _client_id(client_id)
    safe_server = _server_name(server_name)
    if not isinstance(entry, Mapping):
        raise ValueError("MCP server entry must be an object")
    normalized_entry = dict(entry)
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
    original_mode = (path.stat().st_mode & 0o777) if before is not None else None
    if before is not None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_dir = Path(backup_root) / safe_client
        backup_path = backup_dir / f"{path.name}.{stamp}.{before_sha[:12]}.bak"
        _write_backup(backup_path, before, mode=original_mode if original_mode is not None else 0o600)

    servers[safe_server] = normalized_entry
    after = _atomic_json_write(
        path,
        config,
        original_mode=original_mode,
        expected_before=before,
    )

    def verify_install() -> None:
        installed, reread = _load(path)
        installed_servers = installed.get("mcpServers")
        if not isinstance(installed_servers, dict) or installed_servers.get(safe_server) != normalized_entry:
            raise RuntimeError("installed MCP entry does not match requested entry")
        if reread != after:
            raise RuntimeError("MCP client config bytes changed immediately after atomic replacement")

    _verify_or_rollback(
        path,
        before=before,
        written=after,
        original_mode=original_mode,
        verifier=verify_install,
        operation="installation",
    )
    return IntegrationReceipt(
        schema=INTEGRATION_SCHEMA,
        status="INSTALLED",
        client_id=safe_client,
        config_path=str(path),
        backup_path=str(backup_path) if backup_path else None,
        before_sha256=before_sha,
        after_sha256=_sha256(after),
        server_name=safe_server,
    )


def remove_json_mcp(
    *,
    client_id: str,
    config_path: str | Path,
    backup_root: str | Path,
    server_name: str = "gremlin",
) -> IntegrationReceipt:
    safe_client = _client_id(client_id)
    safe_server = _server_name(server_name)
    path = Path(config_path)
    config, before = _load(path)
    if before is None:
        raise ValueError("MCP client config does not exist")
    servers = config.get("mcpServers")
    if not isinstance(servers, dict):
        raise ValueError("mcpServers must be a JSON object")
    if safe_server not in servers:
        raise ValueError(f"MCP server entry is not installed: {safe_server}")

    before_sha = _sha256(before)
    mode = path.stat().st_mode & 0o777
    backup_dir = Path(backup_root) / safe_client
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = backup_dir / f"{path.name}.{stamp}.{before_sha[:12]}.bak"
    _write_backup(backup_path, before, mode=mode)

    del servers[safe_server]
    after = _atomic_json_write(
        path,
        config,
        original_mode=mode,
        expected_before=before,
    )

    def verify_remove() -> None:
        reread, reread_raw = _load(path)
        reread_servers = reread.get("mcpServers")
        if not isinstance(reread_servers, dict) or safe_server in reread_servers:
            raise RuntimeError("removed MCP entry is still present after replacement")
        if reread_raw != after:
            raise RuntimeError("MCP client config bytes changed immediately after atomic replacement")

    _verify_or_rollback(
        path,
        before=before,
        written=after,
        original_mode=mode,
        verifier=verify_remove,
        operation="removal",
    )
    return IntegrationReceipt(
        schema=INTEGRATION_SCHEMA,
        status="REMOVED",
        client_id=safe_client,
        config_path=str(path),
        backup_path=str(backup_path),
        before_sha256=before_sha,
        after_sha256=_sha256(after),
        server_name=safe_server,
    )