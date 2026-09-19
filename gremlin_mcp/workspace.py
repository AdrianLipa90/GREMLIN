from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hmac
import ipaddress
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import socket
import threading
import time
from typing import Any, Mapping, Sequence, cast
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import webbrowser

from gremlin_mcp.core import bestiary_manifest, status as core_status
from gremlin_mcp.install.license_activation import resolve_public_key_path
from gremlin_mcp.install.paths import GremlinPaths, resolve_paths
from gremlin_mcp.product import ProductAuthorizationError, ProductRuntime
from tools.gremlin_client_protocol_v01 import REQUEST_SCHEMA, run_client_request

WORKSPACE_SCHEMA = "GREMLIN_WORKSPACE_V0_1"
SYSTEM_SCHEMA = "GREMLIN_WORKSPACE_SYSTEM_V0_1"
INSTANCE_SCHEMA = "GREMLIN_WORKSPACE_INSTANCE_V0_1"
MAX_REQUEST_BYTES = 1024 * 1024
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
STOP_WAIT_SECONDS = 3.0

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}


class GremlinWorkspaceError(RuntimeError):
    pass


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _assert_loopback(host: str) -> str:
    if not isinstance(host, str) or not host.strip():
        raise GremlinWorkspaceError("workspace host must be a non-empty string")
    value = host.strip()
    if value.casefold() == "localhost":
        return value
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise GremlinWorkspaceError("GREMLIN Workspace accepts only localhost/loopback bind addresses") from exc
    if not address.is_loopback:
        raise GremlinWorkspaceError("GREMLIN Workspace accepts only localhost/loopback bind addresses")
    return value


def _runtime(paths: GremlinPaths) -> ProductRuntime:
    public_key = resolve_public_key_path(paths)
    profile = Path(paths.client_profile_file)
    return ProductRuntime.from_paths(
        license_path=paths.license_file if Path(paths.license_file).is_file() else None,
        public_key_path=str(public_key) if public_key.is_file() else None,
        profile_path=str(profile),
        require_license=True,
    )


def _workspace_gate(runtime: ProductRuntime) -> tuple[bool, str | None]:
    status = runtime.status()
    if status.get("status") != "LICENSED":
        reason = status.get("reason")
        return False, str(reason or status.get("status") or "PRODUCT_NOT_LICENSED")
    try:
        runtime.authorize(tool="gremlin_prototype", feature="PROTOTYPE_PIPELINE")
    except ProductAuthorizationError as exc:
        return False, str(exc)
    return True, None


def _source_assets() -> tuple[Path, Path] | None:
    root = Path(__file__).resolve().parents[1]
    web_root = root / "client" / "web"
    example = root / "examples" / "client_request_v01.json"
    if all((web_root / name).is_file() for name, _ in STATIC_FILES.values()) and example.is_file():
        return web_root, example
    return None


def resolve_workspace_assets(paths: GremlinPaths) -> tuple[Path, Path, str]:
    installed = Path(paths.shared_data_root) / "workspace"
    installed_example = installed / "example-request.json"
    if all((installed / name).is_file() for name, _ in STATIC_FILES.values()) and installed_example.is_file():
        return installed, installed_example, "INSTALLED_RESOURCES"

    source = _source_assets()
    if source is not None:
        return source[0], source[1], "SOURCE_CHECKOUT"

    raise GremlinWorkspaceError(
        f"GREMLIN Workspace assets are missing from {installed}; repair or reinstall GREMLIN"
    )


def load_example_request(example_path: Path) -> dict[str, Any]:
    value = json.loads(example_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GremlinWorkspaceError("workspace example request must be a JSON object")
    if value.get("schema") != REQUEST_SCHEMA:
        raise GremlinWorkspaceError("workspace example request schema mismatch")
    return value


def process_prototype_request(payload: Mapping[str, Any], runtime: ProductRuntime) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("request body must be a JSON object")
    if payload.get("schema") != REQUEST_SCHEMA:
        raise ValueError(f"request schema must be {REQUEST_SCHEMA}")
    runtime.authorize(tool="gremlin_prototype", feature="PROTOTYPE_PIPELINE")
    response = run_client_request(payload)
    return {
        "ui_schema": WORKSPACE_SCHEMA,
        "authority": _authority(),
        "response": response,
    }


def health_payload(runtime: ProductRuntime, *, instance_id: str | None = None) -> dict[str, Any]:
    allowed, reason = _workspace_gate(runtime)
    product = runtime.status()
    return {
        "schema": WORKSPACE_SCHEMA,
        "status": "READY" if allowed else "BLOCKED",
        "reason": reason,
        "api": "/api/prototype",
        "instance_id": instance_id,
        "product_status": product.get("status"),
        "authority": _authority(),
    }


def system_payload(
    runtime: ProductRuntime | None = None,
    *,
    surface: str = "product",
) -> dict[str, Any]:
    if surface not in {"product", "reference"}:
        raise ValueError("workspace system surface must be product or reference")
    if surface == "product":
        if runtime is None:
            raise ValueError("product workspace system payload requires ProductRuntime")
        product = runtime.status()
        license_info = product.get("license")
        profile = product.get("profile")
    else:
        product = {
            "status": "UNLICENSED_RESEARCH",
            "reason": "DEVELOPMENT_REFERENCE_SURFACE",
            "license": None,
            "profile": None,
        }
        license_info = None
        profile = None

    mcp = core_status(surface=surface)
    bestiary = bestiary_manifest()

    safe_license = {
        "edition": license_info.get("edition") if isinstance(license_info, Mapping) else None,
        "expires_at": license_info.get("expires_at") if isinstance(license_info, Mapping) else None,
        "features": list(license_info.get("features") or []) if isinstance(license_info, Mapping) else [],
        "limits": dict(license_info.get("limits") or {}) if isinstance(license_info, Mapping) else {},
    }
    safe_profile = {
        "configured": isinstance(profile, Mapping),
        "label": profile.get("label") if isinstance(profile, Mapping) else None,
    }
    species = []
    for row in bestiary.get("species", []):
        if not isinstance(row, Mapping):
            raise GremlinWorkspaceError("Bestiary manifest contains a non-object species row")
        name = row.get("name")
        stage = row.get("stage")
        role = row.get("role")
        if not all(isinstance(value, str) and value for value in (name, stage, role)):
            raise GremlinWorkspaceError("Bestiary manifest species row is incomplete")
        species.append({"name": name, "stage": stage, "role": role})

    return {
        "schema": SYSTEM_SCHEMA,
        "surface": surface,
        "product": {
            "status": product.get("status"),
            "reason": product.get("reason"),
            "license": safe_license,
            "profile": safe_profile,
        },
        "mcp": {
            "version": mcp.get("version"),
            "tool_count": mcp.get("tool_count"),
            "tool_groups": mcp.get("tool_groups"),
            "capability_contract": mcp.get("capability_contract"),
            "error_contract": mcp.get("error_contract"),
        },
        "bestiary": {
            "species_count": len(species),
            "topology": list(bestiary.get("topology") or []),
            "species": species,
        },
        "authority": _authority(),
    }


def _instance_path(paths: GremlinPaths) -> Path:
    return Path(paths.state_dir) / "workspace-instance.json"


def _write_private_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(temporary, flags, 0o600)
    open_fd = True
    try:
        if os.name != "nt":
            os.fchmod(fd, 0o600)
        handle = os.fdopen(fd, "w", encoding="utf-8")
        open_fd = False
        with handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            path.chmod(0o600)
    except BaseException:
        try:
            temporary.unlink(missing_ok=True)
        finally:
            if open_fd:
                os.close(fd)
        raise


def _validate_instance_state(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise GremlinWorkspaceError("workspace instance state must be a JSON object")
    state = dict(value)
    if state.get("schema") != INSTANCE_SCHEMA:
        raise GremlinWorkspaceError("workspace instance state schema mismatch")
    instance_id = state.get("instance_id")
    token = state.get("shutdown_token")
    host = state.get("host")
    port = state.get("port")
    if not isinstance(instance_id, str) or len(instance_id) < 16:
        raise GremlinWorkspaceError("workspace instance state has invalid instance_id")
    if not isinstance(token, str) or len(token) < 32:
        raise GremlinWorkspaceError("workspace instance state has invalid shutdown token")
    if not isinstance(host, str):
        raise GremlinWorkspaceError("workspace instance state has invalid host")
    _assert_loopback(host)
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise GremlinWorkspaceError("workspace instance state has invalid port")
    return state


def _read_instance_state(paths: GremlinPaths) -> dict[str, Any] | None:
    target = _instance_path(paths)
    if not target.exists():
        return None
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GremlinWorkspaceError(f"workspace instance state is unreadable: {exc}") from exc
    return _validate_instance_state(value)


def _remove_instance_state(paths: GremlinPaths, *, expected_instance_id: str | None = None) -> None:
    target = _instance_path(paths)
    if not target.exists():
        return
    if expected_instance_id is not None:
        current = _read_instance_state(paths)
        if current is None or current.get("instance_id") != expected_instance_id:
            return
    target.unlink(missing_ok=True)


def _probe_health(host: str, port: int, *, timeout: float = 0.35) -> dict[str, Any] | None:
    url = f"http://{host}:{port}/api/health"
    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return None
            payload = json.loads(response.read(32_768).decode("utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("schema") != WORKSPACE_SCHEMA:
        return None
    return payload


def _probe_existing_workspace(host: str, port: int) -> bool:
    payload = _probe_health(host, port)
    return payload is not None and payload.get("status") == "READY"


def _port_available(host: str, port: int) -> bool:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
    except OSError:
        return False
    finally:
        sock.close()
    return True


def workspace_status(
    paths: GremlinPaths,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> dict[str, Any]:
    host = _assert_loopback(host)
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise GremlinWorkspaceError("workspace port must be an integer in 1..65535")

    state = _read_instance_state(paths)
    if state is None:
        health = _probe_health(host, port)
        if health is not None:
            return {
                "schema": WORKSPACE_SCHEMA,
                "status": "RUNNING_UNMANAGED",
                "url": f"http://{host}:{port}",
                "instance_id": health.get("instance_id"),
                "can_stop": False,
                "authority": _authority(),
            }
        return {
            "schema": WORKSPACE_SCHEMA,
            "status": "NOT_RUNNING",
            "url": f"http://{host}:{port}",
            "instance_id": None,
            "can_stop": False,
            "authority": _authority(),
        }

    state_host = str(state["host"])
    state_port = int(state["port"])
    health = _probe_health(state_host, state_port)
    if (
        health is not None
        and health.get("status") == "READY"
        and health.get("instance_id") == state.get("instance_id")
    ):
        return {
            "schema": WORKSPACE_SCHEMA,
            "status": "RUNNING",
            "url": state["url"],
            "instance_id": state["instance_id"],
            "pid": state.get("pid"),
            "started_at": state.get("started_at"),
            "can_stop": True,
            "authority": _authority(),
        }

    return {
        "schema": WORKSPACE_SCHEMA,
        "status": "STALE",
        "url": state["url"],
        "instance_id": state["instance_id"],
        "pid": state.get("pid"),
        "can_stop": False,
        "authority": _authority(),
    }


def workspace_stop(paths: GremlinPaths, *, timeout: float = STOP_WAIT_SECONDS) -> dict[str, Any]:
    state = _read_instance_state(paths)
    if state is None:
        return {
            "schema": WORKSPACE_SCHEMA,
            "status": "NOT_RUNNING",
            "can_stop": False,
            "authority": _authority(),
        }

    health = _probe_health(str(state["host"]), int(state["port"]), timeout=0.25)
    if health is None or health.get("instance_id") != state.get("instance_id"):
        _remove_instance_state(paths, expected_instance_id=str(state["instance_id"]))
        return {
            "schema": WORKSPACE_SCHEMA,
            "status": "STALE_CLEARED",
            "instance_id": state["instance_id"],
            "can_stop": False,
            "authority": _authority(),
        }

    url = str(state["url"]).rstrip("/")
    request = Request(
        f"{url}/api/shutdown",
        data=b"{}",
        method="POST",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {state['shutdown_token']}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=1.0) as response:
            payload = json.loads(response.read(32_768).decode("utf-8"))
    except HTTPError as exc:
        raise GremlinWorkspaceError(f"workspace stop was rejected with HTTP {exc.code}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise GremlinWorkspaceError(f"workspace stop request failed: {exc}") from exc

    if not isinstance(payload, Mapping) or payload.get("status") != "STOPPING":
        raise GremlinWorkspaceError("workspace stop returned an invalid receipt")

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _probe_health(str(state["host"]), int(state["port"]), timeout=0.2) is None:
            _remove_instance_state(paths, expected_instance_id=str(state["instance_id"]))
            return {
                "schema": WORKSPACE_SCHEMA,
                "status": "STOPPED",
                "instance_id": state["instance_id"],
                "can_stop": False,
                "authority": _authority(),
            }
        time.sleep(0.05)

    raise GremlinWorkspaceError("workspace did not stop within the bounded shutdown window")


def workspace_check(
    *,
    paths: GremlinPaths,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> dict[str, Any]:
    host = _assert_loopback(host)
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise GremlinWorkspaceError("workspace port must be an integer in 1..65535")

    try:
        web_root, example_path, asset_mode = resolve_workspace_assets(paths)
    except GremlinWorkspaceError as exc:
        return {
            "schema": WORKSPACE_SCHEMA,
            "status": "BLOCKED",
            "reason": str(exc),
            "url": f"http://{host}:{port}",
            "assets": {"ready": False},
            "authority": _authority(),
        }

    runtime = _runtime(paths)
    allowed, reason = _workspace_gate(runtime)
    if not allowed:
        return {
            "schema": WORKSPACE_SCHEMA,
            "status": "BLOCKED",
            "reason": reason,
            "url": f"http://{host}:{port}",
            "assets": {
                "ready": True,
                "mode": asset_mode,
                "static_file_count": len(STATIC_FILES),
                "example_ready": example_path.is_file(),
            },
            "product_status": runtime.status().get("status"),
            "authority": _authority(),
        }

    lifecycle = workspace_status(paths, host=host, port=port)
    already_running = lifecycle.get("status") in {"RUNNING", "RUNNING_UNMANAGED"}
    if lifecycle.get("status") == "STALE" and _port_available(host, port):
        _remove_instance_state(paths, expected_instance_id=str(lifecycle.get("instance_id") or ""))
        lifecycle = workspace_status(paths, host=host, port=port)

    available = already_running or _port_available(host, port)
    return {
        "schema": WORKSPACE_SCHEMA,
        "status": "READY" if available else "BLOCKED",
        "reason": None if available else "WORKSPACE_PORT_UNAVAILABLE",
        "url": f"http://{host}:{port}",
        "already_running": already_running,
        "lifecycle_status": lifecycle.get("status"),
        "port_available": available if not already_running else False,
        "assets": {
            "ready": True,
            "mode": asset_mode,
            "static_file_count": len(STATIC_FILES),
            "example_ready": example_path.is_file(),
            "web_root": str(web_root),
        },
        "product_status": runtime.status().get("status"),
        "authority": _authority(),
    }


class GremlinWorkspaceServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        web_root: Path,
        example_path: Path,
        runtime: ProductRuntime,
        instance_id: str,
        shutdown_token: str,
    ) -> None:
        super().__init__(server_address, GremlinWorkspaceHandler)
        self.web_root = web_root
        self.example_path = example_path
        self.runtime = runtime
        self.instance_id = instance_id
        self.shutdown_token = shutdown_token


class GremlinWorkspaceHandler(BaseHTTPRequestHandler):
    server_version = "GREMLINWorkspace/0.1"

    @property
    def workspace(self) -> GremlinWorkspaceServer:
        return cast(GremlinWorkspaceServer, self.server)

    def _send_bytes(self, status: int, content_type: str, data: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; base-uri 'none'; "
            "frame-ancestors 'none'; form-action 'none'",
        )
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, status: int, value: Mapping[str, Any]) -> None:
        data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self._send_bytes(status, "application/json; charset=utf-8", data)

    def _send_error(self, status: int, message: str) -> None:
        self._send_json(status, {
            "schema": WORKSPACE_SCHEMA,
            "status": "ERROR",
            "error": message,
            "authority": _authority(),
        })

    def _same_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        host, port = self.workspace.server_address[:2]
        allowed = {
            f"http://{host}:{port}",
            f"http://localhost:{port}",
        }
        return origin.rstrip("/") in allowed

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json(
                200,
                health_payload(self.workspace.runtime, instance_id=self.workspace.instance_id),
            )
            return
        if path == "/api/system":
            try:
                self._send_json(200, system_payload(self.workspace.runtime))
            except (ValueError, TypeError, GremlinWorkspaceError) as exc:
                self._send_error(500, str(exc))
            return
        if path == "/api/example":
            try:
                self._send_json(200, load_example_request(self.workspace.example_path))
            except (OSError, ValueError, json.JSONDecodeError, GremlinWorkspaceError) as exc:
                self._send_error(500, str(exc))
            return

        static = STATIC_FILES.get(path)
        if static is None:
            self._send_error(404, "resource not found")
            return
        name, content_type = static
        target = self.workspace.web_root / name
        try:
            data = target.read_bytes()
        except OSError as exc:
            self._send_error(500, str(exc))
            return
        self._send_bytes(200, content_type, data)

    def _shutdown_authorized(self) -> bool:
        header = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not header.startswith(prefix):
            return False
        supplied = header[len(prefix):]
        return hmac.compare_digest(supplied, self.workspace.shutdown_token)

    def do_POST(self) -> None:  # noqa: N802
        if not self._same_origin():
            self._send_error(403, "cross-origin workspace requests are not allowed")
            return

        path = urlparse(self.path).path
        if path == "/api/shutdown":
            if not self._shutdown_authorized():
                self._send_error(403, "workspace shutdown authorization failed")
                return
            self._send_json(200, {
                "schema": WORKSPACE_SCHEMA,
                "status": "STOPPING",
                "instance_id": self.workspace.instance_id,
                "authority": _authority(),
            })
            threading.Thread(target=self.workspace.shutdown, daemon=True).start()
            return

        if path != "/api/prototype":
            self._send_error(404, "resource not found")
            return
        content_type = self.headers.get("Content-Type", "")
        if not content_type.casefold().startswith("application/json"):
            self._send_error(415, "application/json request body required")
            return
        raw_length = self.headers.get("Content-Length", "")
        try:
            length = int(raw_length)
        except ValueError:
            self._send_error(400, "valid Content-Length required")
            return
        if length < 1 or length > MAX_REQUEST_BYTES:
            self._send_error(413, "request body size outside workspace bound")
            return

        try:
            body = self.rfile.read(length)
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            result = process_prototype_request(payload, self.workspace.runtime)
        except ProductAuthorizationError as exc:
            self._send_error(403, str(exc))
            return
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError, KeyError) as exc:
            self._send_error(400, str(exc))
            return
        except Exception:
            self._send_error(500, "workspace prototype execution failed; inspect GREMLIN diagnostics")
            return
        self._send_json(200, result)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[gremlin-workspace] {self.address_string()} {format % args}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serve the licensed local GREMLIN Workspace")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    parser.add_argument("--platform", choices=("windows", "linux"))
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--check", action="store_true", help="validate assets, entitlement and loopback port then exit")
    actions.add_argument("--status", action="store_true", help="report the managed Workspace lifecycle state then exit")
    actions.add_argument("--stop", action="store_true", help="stop the managed Workspace instance then exit")
    parser.add_argument("--no-browser", action="store_true", help="serve without opening the default browser")
    parser.add_argument("--json", action="store_true", help="print startup/check result as JSON")
    return parser


def _emit(payload: Mapping[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"GREMLIN Workspace: {payload.get('status')} {payload.get('url', '')}".rstrip())
        if payload.get("reason"):
            print(f"Reason: {payload['reason']}")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = resolve_paths(platform=args.platform)

    if args.status:
        status = workspace_status(paths, host=args.host, port=args.port)
        _emit(status, as_json=args.json)
        return 0
    if args.stop:
        try:
            stopped = workspace_stop(paths)
        except GremlinWorkspaceError as exc:
            _emit(
                {
                    "schema": WORKSPACE_SCHEMA,
                    "status": "ERROR",
                    "reason": str(exc),
                    "authority": _authority(),
                },
                as_json=args.json,
            )
            return 1
        _emit(stopped, as_json=args.json)
        return 0

    check = workspace_check(paths=paths, host=args.host, port=args.port)
    if args.check:
        _emit(check, as_json=args.json)
        return 0 if check["status"] == "READY" else 1
    if check["status"] != "READY":
        _emit(check, as_json=args.json)
        return 1

    url = str(check["url"])
    if check.get("already_running") is True:
        if not args.no_browser:
            webbrowser.open(url, new=2)
        _emit(check, as_json=args.json)
        return 0

    web_root, example_path, _ = resolve_workspace_assets(paths)
    runtime = _runtime(paths)
    instance_id = secrets.token_hex(16)
    shutdown_token = secrets.token_urlsafe(32)
    try:
        server = GremlinWorkspaceServer(
            (_assert_loopback(args.host), args.port),
            web_root=web_root,
            example_path=example_path,
            runtime=runtime,
            instance_id=instance_id,
            shutdown_token=shutdown_token,
        )
    except OSError as exc:
        payload = {
            **check,
            "status": "BLOCKED",
            "reason": f"workspace bind failed: {exc}",
        }
        _emit(payload, as_json=args.json)
        return 1

    state = {
        "schema": INSTANCE_SCHEMA,
        "instance_id": instance_id,
        "shutdown_token": shutdown_token,
        "pid": os.getpid(),
        "host": args.host,
        "port": args.port,
        "url": url,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        _write_private_json(_instance_path(paths), state)
    except Exception as exc:
        server.server_close()
        _emit(
            {
                **check,
                "status": "BLOCKED",
                "reason": f"workspace instance state could not be persisted: {exc}",
            },
            as_json=args.json,
        )
        return 1

    started = {
        **check,
        "status": "READY",
        "already_running": False,
        "instance_id": instance_id,
    }
    _emit(started, as_json=args.json)
    if not args.no_browser:
        webbrowser.open(url, new=2)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        _remove_instance_state(paths, expected_instance_id=instance_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
