from __future__ import annotations

import argparse
import ipaddress
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
from typing import Any, Mapping, Sequence, cast
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import webbrowser

from gremlin_mcp.core import bestiary_manifest, status as core_status
from gremlin_mcp.install.license_activation import resolve_public_key_path
from gremlin_mcp.install.paths import GremlinPaths, resolve_paths
from gremlin_mcp.product import ProductAuthorizationError, ProductRuntime
from tools.gremlin_client_protocol_v01 import REQUEST_SCHEMA, run_client_request

WORKSPACE_SCHEMA = "GREMLIN_WORKSPACE_V0_1"
MAX_REQUEST_BYTES = 1024 * 1024
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

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


def workspace_status_payload(runtime: ProductRuntime) -> dict[str, Any]:
    runtime.authorize(tool="gremlin_status")
    product = runtime.status()
    capabilities = core_status(surface="product")
    return {
        "schema": WORKSPACE_SCHEMA,
        "status": "READY",
        "product": product,
        "capabilities": {
            "surface": capabilities["surface"],
            "mode": capabilities["mode"],
            "tool_count": capabilities["tool_count"],
            "tool_groups": capabilities["tool_groups"],
            "capability_contract": capabilities["capability_contract"],
            "error_contract": capabilities["error_contract"],
        },
        "authority": _authority(),
    }


def workspace_bestiary_payload(runtime: ProductRuntime) -> dict[str, Any]:
    runtime.authorize(tool="gremlin_bestiary")
    manifest = bestiary_manifest()
    species = manifest.get("species")
    if not isinstance(species, list):
        raise GremlinWorkspaceError("GREMLIN Bestiary manifest is malformed")
    return {
        "schema": WORKSPACE_SCHEMA,
        "status": "READY",
        "topology": manifest.get("topology"),
        "species": species,
        "species_count": len(species),
        "authority": _authority(),
    }


def health_payload(runtime: ProductRuntime) -> dict[str, Any]:
    allowed, reason = _workspace_gate(runtime)
    product = runtime.status()
    return {
        "schema": WORKSPACE_SCHEMA,
        "status": "READY" if allowed else "BLOCKED",
        "reason": reason,
        "api": "/api/prototype",
        "product_status": product.get("status"),
        "authority": _authority(),
    }


def _probe_existing_workspace(host: str, port: int) -> bool:
    url = f"http://{host}:{port}/api/health"
    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=0.35) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read(32_768).decode("utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return (
        isinstance(payload, dict)
        and payload.get("schema") == WORKSPACE_SCHEMA
        and payload.get("status") == "READY"
    )


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

    already_running = _probe_existing_workspace(host, port)
    available = already_running or _port_available(host, port)
    return {
        "schema": WORKSPACE_SCHEMA,
        "status": "READY" if available else "BLOCKED",
        "reason": None if available else "WORKSPACE_PORT_UNAVAILABLE",
        "url": f"http://{host}:{port}",
        "already_running": already_running,
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
    ) -> None:
        super().__init__(server_address, GremlinWorkspaceHandler)
        self.web_root = web_root
        self.example_path = example_path
        self.runtime = runtime


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
            self._send_json(200, health_payload(self.workspace.runtime))
            return
        if path == "/api/status":
            try:
                self._send_json(200, workspace_status_payload(self.workspace.runtime))
            except ProductAuthorizationError as exc:
                self._send_error(403, str(exc))
            except Exception:
                self._send_error(500, "workspace status failed; inspect GREMLIN diagnostics")
            return
        if path == "/api/bestiary":
            try:
                self._send_json(200, workspace_bestiary_payload(self.workspace.runtime))
            except ProductAuthorizationError as exc:
                self._send_error(403, str(exc))
            except Exception:
                self._send_error(500, "workspace Bestiary failed; inspect GREMLIN diagnostics")
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

    def do_POST(self) -> None:  # noqa: N802
        if not self._same_origin():
            self._send_error(403, "cross-origin workspace requests are not allowed")
            return
        if urlparse(self.path).path != "/api/prototype":
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
    parser.add_argument("--check", action="store_true", help="validate assets, entitlement and loopback port then exit")
    parser.add_argument("--no-browser", action="store_true", help="serve without opening the default browser")
    parser.add_argument("--json", action="store_true", help="print startup/check result as JSON")
    return parser


def _emit(payload: Mapping[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"GREMLIN Workspace: {payload.get('status')} {payload.get('url')}")
        if payload.get("reason"):
            print(f"Reason: {payload['reason']}")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = resolve_paths(platform=args.platform)
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
    try:
        server = GremlinWorkspaceServer(
            (_assert_loopback(args.host), args.port),
            web_root=web_root,
            example_path=example_path,
            runtime=runtime,
        )
    except OSError as exc:
        payload = {
            **check,
            "status": "BLOCKED",
            "reason": f"workspace bind failed: {exc}",
        }
        _emit(payload, as_json=args.json)
        return 1

    started = {
        **check,
        "status": "READY",
        "already_running": False,
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
