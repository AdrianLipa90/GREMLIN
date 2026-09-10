from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import secrets
import time
from typing import Any, Callable, Mapping, Sequence
import urllib.parse

FERRET_SCHEMA = "GREMLIN_FERRET_WEB_ACTUATOR_V0_1"
FERRET_VERSION = "0.1.0"

_ALLOWED_ACTIONS = frozenset(
    {
        "navigate",
        "fill",
        "select",
        "check",
        "upload",
        "click",
        "wait_for",
        "snapshot",
    }
)


class FerretError(RuntimeError):
    pass


class FerretAuthorizationError(FerretError):
    pass


class FerretExecutionError(FerretError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _commit(domain: bytes, payload: Any) -> str:
    return hashlib.blake2b(domain + _canonical(payload), digest_size=32).hexdigest()


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _normalize_public_https_url(value: str) -> str:
    raw = str(value).strip()
    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme.lower() != "https":
        raise ValueError("FERRET accepts HTTPS targets only")
    if parsed.username or parsed.password:
        raise ValueError("userinfo in target URLs is blocked")
    if parsed.port not in (None, 443):
        raise ValueError("FERRET accepts HTTPS port 443 only")
    host = (parsed.hostname or "").strip().rstrip(".").lower()
    if not host:
        raise ValueError("target hostname is required")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("local targets are blocked")
    return urllib.parse.urlunsplit(("https", parsed.netloc, parsed.path or "/", parsed.query, ""))


def _normalize_step(step: Mapping[str, Any], index: int) -> dict[str, Any]:
    if not isinstance(step, Mapping):
        raise ValueError(f"step {index} must be a mapping")
    action = str(step.get("action", "")).strip().lower()
    if action not in _ALLOWED_ACTIONS:
        raise ValueError(f"step {index} has unsupported action: {action!r}")

    normalized: dict[str, Any] = {"action": action}
    selector = step.get("selector")
    if selector is not None:
        selector_text = str(selector).strip()
        if not selector_text:
            raise ValueError(f"step {index} selector cannot be blank")
        normalized["selector"] = selector_text

    if action == "navigate":
        normalized["url"] = _normalize_public_https_url(str(step.get("url", "")))
    elif action in {"fill", "select"}:
        if "selector" not in normalized:
            raise ValueError(f"step {index} requires selector")
        normalized["value"] = str(step.get("value", ""))
        if bool(step.get("secret", False)):
            normalized["secret"] = True
            normalized["value"] = "<REDACTED>"
    elif action == "check":
        if "selector" not in normalized:
            raise ValueError(f"step {index} requires selector")
        normalized["checked"] = bool(step.get("checked", True))
    elif action == "upload":
        if "selector" not in normalized:
            raise ValueError(f"step {index} requires selector")
        files = step.get("files")
        if not isinstance(files, Sequence) or isinstance(files, (str, bytes)) or not files:
            raise ValueError(f"step {index} upload requires a non-empty files list")
        normalized["files"] = [str(item) for item in files]
    elif action in {"click", "wait_for", "snapshot"}:
        if action != "snapshot" and "selector" not in normalized:
            raise ValueError(f"step {index} requires selector")
        if action == "snapshot":
            normalized["label"] = str(step.get("label", f"snapshot-{index}"))

    return normalized


def prepare_action(request: Mapping[str, Any]) -> dict[str, Any]:
    """Create an immutable, receipt-bound preview. This never touches the target website."""
    if not isinstance(request, Mapping):
        raise ValueError("request must be a mapping")

    target_url = _normalize_public_https_url(str(request.get("target_url", "")))
    intent = str(request.get("intent", "")).strip()
    if not intent:
        raise ValueError("intent is required")

    raw_steps = request.get("steps")
    if not isinstance(raw_steps, Sequence) or isinstance(raw_steps, (str, bytes)) or not raw_steps:
        raise ValueError("steps must be a non-empty list")
    if len(raw_steps) > 64:
        raise ValueError("FERRET v0.1 supports at most 64 steps")

    steps = [_normalize_step(step, index) for index, step in enumerate(raw_steps)]
    target_host = urllib.parse.urlsplit(target_url).hostname
    for step in steps:
        if step["action"] == "navigate":
            step_host = urllib.parse.urlsplit(step["url"]).hostname
            if step_host != target_host:
                raise ValueError("cross-origin navigation requires a separate FERRET action")

    core = {
        "schema": FERRET_SCHEMA,
        "version": FERRET_VERSION,
        "preview_id": secrets.token_hex(16),
        "created_unix_ns": time.time_ns(),
        "intent": intent,
        "target_url": target_url,
        "steps": steps,
        "requires_explicit_approval": True,
        "approval_scope": "EXACT_PREVIEW_COMMITMENT",
        "captcha_policy": "STOP_AND_HAND_CONTROL_TO_USER",
        "mfa_policy": "STOP_AND_HAND_CONTROL_TO_USER",
        "secret_logging": "REDACT",
        "authority": _authority(),
    }
    core["preview_commitment"] = _commit(b"GREMLIN-FERRET-PREVIEW/v0.1\0", core)
    return core


def authorize_action(
    preview: Mapping[str, Any],
    *,
    actor: str,
    approved: bool,
) -> dict[str, Any]:
    """Bind explicit caller approval to one exact preview commitment."""
    if not approved:
        raise FerretAuthorizationError("explicit approval is required")
    actor_name = str(actor).strip()
    if not actor_name:
        raise ValueError("actor is required")

    preview_dict = dict(preview)
    supplied = str(preview_dict.pop("preview_commitment", ""))
    expected = _commit(b"GREMLIN-FERRET-PREVIEW/v0.1\0", preview_dict)
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise FerretAuthorizationError("preview commitment mismatch")

    core = {
        "schema": "GREMLIN_FERRET_AUTHORIZATION_RECEIPT_V0_1",
        "authorization_id": secrets.token_hex(16),
        "authorized_unix_ns": time.time_ns(),
        "actor": actor_name,
        "preview_id": preview_dict["preview_id"],
        "preview_commitment": supplied,
        "scope": "EXACT_PREVIEW_ONLY",
        "single_use": True,
    }
    core["authorization_commitment"] = _commit(
        b"GREMLIN-FERRET-AUTHORIZATION/v0.1\0", core
    )
    return core


def verify_authorization(
    preview: Mapping[str, Any], authorization: Mapping[str, Any]
) -> None:
    preview_dict = dict(preview)
    preview_commitment = str(preview_dict.pop("preview_commitment", ""))
    expected_preview = _commit(b"GREMLIN-FERRET-PREVIEW/v0.1\0", preview_dict)
    if not preview_commitment or not secrets.compare_digest(preview_commitment, expected_preview):
        raise FerretAuthorizationError("preview commitment mismatch")

    auth_dict = dict(authorization)
    auth_commitment = str(auth_dict.pop("authorization_commitment", ""))
    expected_auth = _commit(b"GREMLIN-FERRET-AUTHORIZATION/v0.1\0", auth_dict)
    if not auth_commitment or not secrets.compare_digest(auth_commitment, expected_auth):
        raise FerretAuthorizationError("authorization commitment mismatch")
    if auth_dict.get("preview_id") != preview_dict.get("preview_id"):
        raise FerretAuthorizationError("authorization belongs to another preview")
    if auth_dict.get("preview_commitment") != preview_commitment:
        raise FerretAuthorizationError("authorization scope does not match preview")


@dataclass(frozen=True)
class FerretExecutionResult:
    status: str
    resolved_url: str
    evidence: Mapping[str, Any]


Executor = Callable[[Mapping[str, Any]], FerretExecutionResult]


def execute_authorized_action(
    preview: Mapping[str, Any],
    authorization: Mapping[str, Any],
    executor: Executor,
) -> dict[str, Any]:
    """Execute only after exact authorization; the concrete browser backend is injected."""
    verify_authorization(preview, authorization)
    if not callable(executor):
        raise TypeError("executor must be callable")

    started = time.time_ns()
    try:
        result = executor(preview)
    except Exception as exc:
        raise FerretExecutionError(f"FERRET backend failed: {type(exc).__name__}: {exc}") from exc
    if not isinstance(result, FerretExecutionResult):
        raise FerretExecutionError("FERRET backend returned an invalid result type")

    core = {
        "schema": "GREMLIN_FERRET_EXECUTION_RECEIPT_V0_1",
        "preview_id": preview["preview_id"],
        "preview_commitment": preview["preview_commitment"],
        "authorization_id": authorization["authorization_id"],
        "authorization_commitment": authorization["authorization_commitment"],
        "started_unix_ns": started,
        "finished_unix_ns": time.time_ns(),
        "status": str(result.status),
        "resolved_url": str(result.resolved_url),
        "evidence": dict(result.evidence),
        "authority": {
            "external_action_executed": True,
            "canon_allowed": False,
        },
    }
    core["execution_commitment"] = _commit(
        b"GREMLIN-FERRET-EXECUTION/v0.1\0", core
    )
    return core
