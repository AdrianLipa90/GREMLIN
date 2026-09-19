from __future__ import annotations

from functools import wraps
import json
import re
import secrets
from typing import Any, Callable, TypeVar, cast

from mcp.server.mcpserver.exceptions import ToolError

SCHEMA = "GREMLIN_MCP_ERROR_V0_1"
_CODE_RE = re.compile(r"^([A-Z][A-Z0-9_]*)(?::.*)?$", re.DOTALL)
F = TypeVar("F", bound=Callable[..., Any])


class GremlinMCPToolError(ToolError):
    """Expected MCP tool error carrying the GREMLIN machine-readable envelope."""


def _raw_code(message: str, default: str) -> tuple[str, str]:
    text = message.strip()
    match = _CODE_RE.match(text)
    if match:
        return match.group(1), text
    return default, text


def _user_action(code: str) -> str:
    if code == "LICENSE_REQUIRED":
        return "Activate a valid GREMLIN license in Control Center."
    if code == "PRODUCT_CONFIGURATION_ERROR":
        return "Open Control Center Diagnostics and repair the product/license/profile configuration."
    if code == "TOOL_NOT_ALLOWED_BY_PROFILE":
        return "Use a tool admitted by the active signed customer profile."
    if code == "SPECIES_NOT_ALLOWED_BY_PROFILE":
        return "Use a Bestiary species admitted by the active signed customer profile."
    if code == "PROVIDER_NOT_ALLOWED_BY_PROFILE":
        return "Use an internet provider admitted by the active signed customer profile."
    if code == "FEATURE_NOT_ENTITLED":
        return "Use an entitled feature or update the signed GREMLIN entitlement."
    if code in {"WORKER_LIMIT_EXCEEDED", "SOURCE_LIMIT_EXCEEDED"}:
        return "Reduce the requested resource count or use an entitlement with a higher limit."
    if code == "INTERNET_ACCESS_DISABLED_BY_PROFILE":
        return "Use an offline tool or a signed profile that explicitly permits internet research."
    if code == "CUSTOM_WORKERS_DISABLED_BY_PROFILE":
        return "Use built-in workers or a signed profile that explicitly permits custom workers."
    if code == "REMOTE_HTTP_AUTH_REQUIRED":
        return "Bind GREMLIN MCP to localhost/loopback or configure an authenticated remote transport."
    if code == "CROSS_ORIGIN_WORKSPACE_REQUEST":
        return "Use the local GREMLIN Workspace origin; cross-origin requests are not admitted."
    if code == "REQUEST_BODY_TOO_LARGE":
        return "Reduce the Workspace request body and retry."
    if code == "WORKSPACE_INTERNAL_ERROR":
        return "Open Control Center Diagnostics and export a sanitized support report before retrying."
    if code == "INVALID_REQUEST":
        return "Correct the tool arguments and retry."
    if code in {"TIMEOUT", "NETWORK_ERROR"}:
        return "Retry the operation; if it repeats, inspect provider/network diagnostics."
    if code == "IO_ERROR":
        return "Inspect the referenced local path, permissions and installation state."
    if code == "RUNTIME_ERROR":
        return "Open GREMLIN Diagnostics and inspect the exact runtime failure before retrying."
    return "Inspect the error detail and GREMLIN Diagnostics before retrying."


def error_envelope(exc: Exception, *, tool: str, request_id: str | None = None) -> dict[str, Any]:
    message = str(exc).strip() or type(exc).__name__
    if isinstance(request_id, str) and request_id.strip():
        correlation_id = request_id.strip()
        request_id_source = "caller"
    else:
        correlation_id = f"err-{secrets.token_hex(12)}"
        request_id_source = "generated"

    if isinstance(exc, PermissionError):
        code, detail = _raw_code(message, "AUTHORIZATION_DENIED")
        category = "AUTHORIZATION"
        retryable = False
    elif isinstance(exc, (ValueError, TypeError)):
        code, detail = _raw_code(message, "INVALID_REQUEST")
        category = "REQUEST"
        retryable = False
    elif isinstance(exc, TimeoutError):
        code, detail = _raw_code(message, "TIMEOUT")
        category = "TRANSIENT"
        retryable = True
    elif isinstance(exc, ConnectionError):
        code, detail = _raw_code(message, "NETWORK_ERROR")
        category = "TRANSIENT"
        retryable = True
    elif isinstance(exc, OSError):
        code, detail = _raw_code(message, "IO_ERROR")
        category = "RUNTIME"
        retryable = False
    elif isinstance(exc, RuntimeError):
        code, detail = _raw_code(message, "RUNTIME_ERROR")
        category = "RUNTIME"
        retryable = False
    else:
        code, detail = _raw_code(message, "INTERNAL_ERROR")
        category = "INTERNAL"
        retryable = False

    return {
        "schema": SCHEMA,
        "status": "ERROR",
        "tool": tool,
        "error_code": code,
        "detail_code": detail if detail else code,
        "category": category,
        "retryable": retryable,
        "user_action": _user_action(code),
        "request_id": correlation_id,
        "request_id_source": request_id_source,
        "exception_type": type(exc).__name__,
        "authority": {
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        },
    }


def serialize_error_envelope(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def mcp_error_boundary(tool: str) -> Callable[[F], F]:
    if not isinstance(tool, str) or not tool.strip():
        raise ValueError("tool must be a non-empty string")

    def decorate(fn: F) -> F:
        @wraps(fn)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except GremlinMCPToolError:
                raise
            except Exception as exc:
                raw_request_id = kwargs.get("request_id")
                request_id = raw_request_id if isinstance(raw_request_id, str) and raw_request_id.strip() else None
                payload = error_envelope(exc, tool=tool, request_id=request_id)
                raise GremlinMCPToolError(serialize_error_envelope(payload)) from exc

        return cast(F, wrapped)

    return decorate
