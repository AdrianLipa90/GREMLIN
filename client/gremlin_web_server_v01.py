from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from tools.gremlin_client_protocol_v01 import REQUEST_SCHEMA, run_client_request

WEB_SCHEMA = "GREMLIN_VISUAL_CLIENT_V0_1"
MAX_REQUEST_BYTES = 1024 * 1024
ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = Path(__file__).resolve().parent / "web"
EXAMPLE_REQUEST = ROOT / "examples" / "client_request_v01.json"

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}


class GremlinVisualClientError(ValueError):
    pass


def load_example_request() -> dict[str, Any]:
    value = json.loads(EXAMPLE_REQUEST.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GremlinVisualClientError("example request must be a JSON object")
    return value


def process_prototype_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise GremlinVisualClientError("request body must be a JSON object")
    if payload.get("schema") != REQUEST_SCHEMA:
        raise GremlinVisualClientError(f"request schema must be {REQUEST_SCHEMA}")
    response = run_client_request(payload)
    return {
        "ui_schema": WEB_SCHEMA,
        "authority": {
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        },
        "response": response,
    }


def health_payload() -> dict[str, Any]:
    return {
        "schema": WEB_SCHEMA,
        "status": "READY",
        "api": "/api/prototype",
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


class GremlinVisualClientHandler(BaseHTTPRequestHandler):
    server_version = "GREMLINVisualClient/0.1"

    def _send_bytes(self, status: int, content_type: str, data: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, status: int, value: Mapping[str, Any]) -> None:
        data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self._send_bytes(status, "application/json; charset=utf-8", data)

    def _send_error_json(self, status: int, message: str) -> None:
        self._send_json(status, {
            "ui_schema": WEB_SCHEMA,
            "status": "ERROR",
            "error": str(message),
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        })

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json(200, health_payload())
            return
        if path == "/api/example":
            try:
                self._send_json(200, load_example_request())
            except Exception as exc:
                self._send_error_json(500, exc)
            return

        static = STATIC_FILES.get(path)
        if static is None:
            self._send_error_json(404, "resource not found")
            return
        name, content_type = static
        target = WEB_ROOT / name
        try:
            data = target.read_bytes()
        except OSError as exc:
            self._send_error_json(500, exc)
            return
        self._send_bytes(200, content_type, data)

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
        path = urlparse(self.path).path
        if path != "/api/prototype":
            self._send_error_json(404, "resource not found")
            return

        raw_length = self.headers.get("Content-Length", "")
        try:
            length = int(raw_length)
        except ValueError:
            self._send_error_json(400, "valid Content-Length required")
            return
        if length < 1 or length > MAX_REQUEST_BYTES:
            self._send_error_json(413, "request body size outside visual-client bound")
            return

        try:
            body = self.rfile.read(length)
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise GremlinVisualClientError("request body must be a JSON object")
            result = process_prototype_request(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError, KeyError) as exc:
            self._send_error_json(400, exc)
            return
        except Exception as exc:
            self._send_error_json(500, exc)
            return
        self._send_json(200, result)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[gremlin-web] {self.address_string()} {format % args}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gremlin-web-v01",
        description="Serve the local GREMLIN visual research client.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host; defaults to loopback only")
    parser.add_argument("--port", default=8765, type=int, help="TCP port; defaults to 8765")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.port < 1 or args.port > 65535:
        raise SystemExit("port must be in 1..65535")
    server = ThreadingHTTPServer((args.host, args.port), GremlinVisualClientHandler)
    print(f"GREMLIN visual client: http://{args.host}:{args.port}")
    print("Authority boundary: prototype/reference validation only; no production admission.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
