from __future__ import annotations

from dataclasses import dataclass
import hashlib
import ipaddress
import json
import re
import secrets
import socket
import time
from typing import Any, Callable, Mapping, Sequence
import urllib.parse

FERRET_SCHEMA = "GREMLIN_FERRET_WEB_ACTUATOR_V0_1"
FERRET_VERSION = "0.1.1"

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
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_LOCAL_HOST_SUFFIXES = (".local", ".localhost", ".internal", ".lan", ".home", ".corp")


class FerretError(RuntimeError):
    pass


class FerretAuthorizationError(FerretError):
    pass


class FerretExecutionError(FerretError):
    pass


class FerretHandoffError(FerretError):
    pass


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("FERRET data must be finite JSON") from exc


def _commit(domain: bytes, payload: Any) -> str:
    return hashlib.blake2b(domain + _canonical(payload), digest_size=32).hexdigest()


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _strict_text(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not allow_empty and not text:
        raise ValueError(f"{field} must be non-empty")
    return text


def _strict_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field} must be boolean")
    return value


def _strict_commitment(value: Any, field: str) -> str:
    text = _strict_text(value, field).lower()
    if not _HEX64.fullmatch(text):
        raise ValueError(f"{field} must be a lowercase SHA-256/BLAKE2b-256 hex digest")
    return text


def _ensure_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address, field: str) -> None:
    if not ip.is_global:
        raise ValueError(f"{field} resolves to a non-public address: {ip}")


def _normalize_public_https_url(value: str) -> str:
    raw = _strict_text(value, "URL")
    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme.lower() != "https":
        raise ValueError("FERRET accepts HTTPS targets only")
    if parsed.username or parsed.password:
        raise ValueError("userinfo in target URLs is blocked")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("target URL contains an invalid port") from exc
    if port not in (None, 443):
        raise ValueError("FERRET accepts HTTPS port 443 only")
    host = (parsed.hostname or "").strip().rstrip(".").lower()
    if not host:
        raise ValueError("target hostname is required")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(_LOCAL_HOST_SUFFIXES):
        raise ValueError("local targets are blocked")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        _ensure_public_ip(literal, "target URL")
    netloc = f"[{host}]" if ":" in host else host
    return urllib.parse.urlunsplit(("https", netloc, parsed.path or "/", parsed.query, ""))


def validate_public_network_url(value: str) -> str:
    """Resolve an HTTPS target at the transport edge and reject every non-public address.

    Preview creation remains deterministic and network-free. Browser execution calls this helper
    immediately before network access, which also closes private-IP literals and DNS rebinding into
    private, loopback, link-local, reserved, multicast or otherwise non-global ranges.
    """
    normalized = _normalize_public_https_url(value)
    host = urllib.parse.urlsplit(normalized).hostname
    if host is None:
        raise ValueError("target hostname is required")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        _ensure_public_ip(literal, "target URL")
        return normalized
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"DNS resolution failed for target host {host!r}") from exc
    if not infos:
        raise ValueError(f"DNS returned no addresses for target host {host!r}")
    seen: set[str] = set()
    for info in infos:
        raw_address = info[4][0]
        if raw_address in seen:
            continue
        seen.add(raw_address)
        try:
            resolved = ipaddress.ip_address(raw_address)
        except ValueError as exc:
            raise ValueError(f"DNS returned an invalid address for {host!r}") from exc
        _ensure_public_ip(resolved, f"target host {host!r}")
    return normalized


def _origin(value: str) -> str:
    parsed = urllib.parse.urlsplit(_normalize_public_https_url(value))
    host = parsed.hostname
    if host is None:
        raise ValueError("target hostname is required")
    return f"https://[{host}]" if ":" in host else f"https://{host}"


def _normalize_step(step: Mapping[str, Any], index: int) -> dict[str, Any]:
    if not isinstance(step, Mapping):
        raise ValueError(f"step {index} must be a mapping")
    action = _strict_text(step.get("action"), f"step {index} action").lower()
    if action not in _ALLOWED_ACTIONS:
        raise ValueError(f"step {index} has unsupported action: {action!r}")

    normalized: dict[str, Any] = {"action": action}
    selector = step.get("selector")
    if selector is not None:
        normalized["selector"] = _strict_text(selector, f"step {index} selector")

    if action == "navigate":
        normalized["url"] = _normalize_public_https_url(
            _strict_text(step.get("url"), f"step {index} url")
        )
    elif action in {"fill", "select"}:
        if "selector" not in normalized:
            raise ValueError(f"step {index} requires selector")
        secret_raw = step.get("secret", False)
        secret = _strict_bool(secret_raw, f"step {index} secret")
        if secret:
            if "value" in step and step.get("value") not in (None, "<REDACTED>"):
                raise ValueError(
                    f"step {index} secret values must not be embedded; use secret_ref"
                )
            normalized["secret"] = True
            normalized["secret_ref"] = _strict_text(
                step.get("secret_ref"), f"step {index} secret_ref"
            )
            normalized["value"] = "<REDACTED>"
        else:
            normalized["value"] = _strict_text(
                step.get("value", ""), f"step {index} value", allow_empty=True
            )
    elif action == "check":
        if "selector" not in normalized:
            raise ValueError(f"step {index} requires selector")
        normalized["checked"] = _strict_bool(
            step.get("checked", True), f"step {index} checked"
        )
    elif action == "upload":
        if "selector" not in normalized:
            raise ValueError(f"step {index} requires selector")
        files = step.get("files")
        if not isinstance(files, (list, tuple)) or not files:
            raise ValueError(f"step {index} upload requires a non-empty files list")
        normalized_files: list[str] = []
        for file_index, item in enumerate(files):
            normalized_files.append(
                _strict_text(item, f"step {index} files[{file_index}]")
            )
        normalized["files"] = normalized_files
    elif action in {"click", "wait_for", "snapshot"}:
        if action != "snapshot" and "selector" not in normalized:
            raise ValueError(f"step {index} requires selector")
        if action == "snapshot":
            normalized["label"] = _strict_text(
                step.get("label", f"snapshot-{index}"), f"step {index} label"
            )

    return normalized


def _verify_preview(preview: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    if not isinstance(preview, Mapping):
        raise FerretAuthorizationError("preview must be a mapping")
    preview_dict = dict(preview)
    try:
        supplied = _strict_commitment(
            preview_dict.pop("preview_commitment", None), "preview_commitment"
        )
    except ValueError as exc:
        raise FerretAuthorizationError(str(exc)) from exc
    expected = _commit(b"GREMLIN-FERRET-PREVIEW/v0.1\0", preview_dict)
    if not secrets.compare_digest(supplied, expected):
        raise FerretAuthorizationError("preview commitment mismatch")
    return preview_dict, supplied


def prepare_action(request: Mapping[str, Any]) -> dict[str, Any]:
    """Create an immutable, receipt-bound preview. This never touches the target website."""
    if not isinstance(request, Mapping):
        raise ValueError("request must be a mapping")

    target_url = _normalize_public_https_url(
        _strict_text(request.get("target_url"), "target_url")
    )
    intent = _strict_text(request.get("intent"), "intent")

    raw_steps = request.get("steps")
    if not isinstance(raw_steps, (list, tuple)) or not raw_steps:
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
        "secret_value_policy": "REFERENCE_ONLY",
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
    approved_value = _strict_bool(approved, "approved")
    if not approved_value:
        raise FerretAuthorizationError("explicit approval is required")
    actor_name = _strict_text(actor, "actor")

    preview_dict, supplied = _verify_preview(preview)
    core = {
        "schema": "GREMLIN_FERRET_AUTHORIZATION_RECEIPT_V0_1",
        "authorization_id": secrets.token_hex(16),
        "authorized_unix_ns": time.time_ns(),
        "actor": actor_name,
        "preview_id": preview_dict["preview_id"],
        "preview_commitment": supplied,
        "scope": "EXACT_PREVIEW_ONLY",
        "single_use": False,
        "replay_protection": "CALLER_LEDGER_REQUIRED",
    }
    core["authorization_commitment"] = _commit(
        b"GREMLIN-FERRET-AUTHORIZATION/v0.1\0", core
    )
    return core


def verify_authorization(
    preview: Mapping[str, Any], authorization: Mapping[str, Any]
) -> None:
    preview_dict, preview_commitment = _verify_preview(preview)
    if not isinstance(authorization, Mapping):
        raise FerretAuthorizationError("authorization must be a mapping")

    auth_dict = dict(authorization)
    try:
        auth_commitment = _strict_commitment(
            auth_dict.pop("authorization_commitment", None), "authorization_commitment"
        )
    except ValueError as exc:
        raise FerretAuthorizationError(str(exc)) from exc
    expected_auth = _commit(b"GREMLIN-FERRET-AUTHORIZATION/v0.1\0", auth_dict)
    if not secrets.compare_digest(auth_commitment, expected_auth):
        raise FerretAuthorizationError("authorization commitment mismatch")
    if auth_dict.get("preview_id") != preview_dict.get("preview_id"):
        raise FerretAuthorizationError("authorization belongs to another preview")
    if auth_dict.get("preview_commitment") != preview_commitment:
        raise FerretAuthorizationError("authorization scope does not match preview")


def _append_optional_text(values: list[str], value: Any, field: str) -> None:
    if value is None:
        return
    values.append(_strict_text(value, field, allow_empty=True))


def detect_human_gate(observation: Mapping[str, Any]) -> dict[str, Any] | None:
    """Detect CAPTCHA/MFA/anti-bot gates from bounded browser metadata without solving them."""
    if not isinstance(observation, Mapping):
        raise ValueError("observation must be a mapping")
    if "observation_complete" in observation:
        complete = _strict_bool(observation["observation_complete"], "observation_complete")
        if not complete:
            raise FerretHandoffError("browser observation is incomplete; gate state is unknown")

    values: list[str] = []
    for key in ("title", "body_text", "resolved_url"):
        _append_optional_text(values, observation.get(key), key)

    frames = observation.get("frames", [])
    if frames is None:
        frames = []
    if not isinstance(frames, (list, tuple)):
        raise ValueError("frames must be a list")
    for frame_index, frame in enumerate(frames[:64]):
        if not isinstance(frame, Mapping):
            raise ValueError(f"frames[{frame_index}] must be a mapping")
        for key in ("name", "url", "text", "title"):
            _append_optional_text(values, frame.get(key), f"frames[{frame_index}].{key}")

    fields = observation.get("fields", [])
    if fields is None:
        fields = []
    if not isinstance(fields, (list, tuple)):
        raise ValueError("fields must be a list")
    for field_index, field in enumerate(fields[:128]):
        if not isinstance(field, Mapping):
            raise ValueError(f"fields[{field_index}] must be a mapping")
        for key in ("name", "id", "type", "aria_label", "placeholder"):
            _append_optional_text(values, field.get(key), f"fields[{field_index}].{key}")

    haystack = "\n".join(values).lower()
    providers: set[str] = set()
    signals: list[str] = []

    if "hcaptcha" in haystack or "h-captcha-response" in haystack:
        providers.add("HCAPTCHA")
        signals.append("HCAPTCHA_MARKER")
    if "recaptcha" in haystack or "g-recaptcha-response" in haystack:
        providers.add("RECAPTCHA")
        signals.append("RECAPTCHA_MARKER")
    if "imperva" in haystack or "incapsula" in haystack:
        providers.add("IMPERVA")
        signals.append("IMPERVA_MARKER")
    if "additional security check" in haystack:
        providers.add("IMPERVA")
        signals.append("ADDITIONAL_SECURITY_CHECK")

    captcha_markers = (
        "captcha",
        "i am human",
        "verify you are human",
        "verify that you are human",
    )
    mfa_markers = (
        "two-factor",
        "2fa",
        "multi-factor",
        "mfa",
        "one-time code",
        "verification code",
        "authenticator app",
    )

    if any(marker in haystack for marker in captcha_markers) or {
        "HCAPTCHA",
        "RECAPTCHA",
    } & providers:
        gate_kind = "CAPTCHA"
        signals.append("HUMAN_VERIFICATION_MARKER")
    elif any(marker in haystack for marker in mfa_markers):
        gate_kind = "MFA"
        signals.append("MFA_MARKER")
    elif "IMPERVA" in providers:
        gate_kind = "BOT_CHALLENGE"
    else:
        return None

    evidence_core = {
        "gate_kind": gate_kind,
        "providers": sorted(providers),
        "signals": sorted(set(signals)),
    }
    result = {
        "schema": "GREMLIN_FERRET_HUMAN_GATE_V0_1",
        **evidence_core,
        "policy": "HUMAN_HANDOFF_REQUIRED",
        "automated_solution_attempted": False,
        "observation_commitment": _commit(
            b"GREMLIN-FERRET-GATE-EVIDENCE/v0.1\0", evidence_core
        ),
    }
    result["gate_commitment"] = _commit(b"GREMLIN-FERRET-GATE/v0.1\0", result)
    return result


def _verify_gate(gate: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    if not isinstance(gate, Mapping):
        raise FerretHandoffError("gate must be a mapping")
    gate_dict = dict(gate)
    try:
        supplied = _strict_commitment(gate_dict.pop("gate_commitment", None), "gate_commitment")
    except ValueError as exc:
        raise FerretHandoffError(str(exc)) from exc
    expected = _commit(b"GREMLIN-FERRET-GATE/v0.1\0", gate_dict)
    if not secrets.compare_digest(supplied, expected):
        raise FerretHandoffError("gate commitment mismatch")
    if gate_dict.get("policy") != "HUMAN_HANDOFF_REQUIRED":
        raise FerretHandoffError("gate is not eligible for human handoff")
    return gate_dict, supplied


def prepare_human_handoff(
    preview: Mapping[str, Any],
    gate: Mapping[str, Any],
    *,
    resolved_url: str,
) -> dict[str, Any]:
    """Bind an observed human-verification gate to one exact FERRET preview and origin."""
    preview_dict, preview_commitment = _verify_preview(preview)
    gate_dict, gate_commitment = _verify_gate(gate)
    normalized_url = _normalize_public_https_url(_strict_text(resolved_url, "resolved_url"))
    target_origin = _origin(preview_dict["target_url"])
    if _origin(normalized_url) != target_origin:
        raise FerretHandoffError("handoff origin differs from preview target origin")

    core = {
        "schema": "GREMLIN_FERRET_HUMAN_HANDOFF_V0_1",
        "handoff_id": secrets.token_hex(16),
        "created_unix_ns": time.time_ns(),
        "preview_id": preview_dict["preview_id"],
        "preview_commitment": preview_commitment,
        "gate_kind": gate_dict["gate_kind"],
        "gate_commitment": gate_commitment,
        "target_origin": target_origin,
        "resolved_url": normalized_url,
        "status": "USER_ACTION_REQUIRED",
        "automated_gate_solution_allowed": False,
        "human_action_scope": "COMPLETE_SITE_CHALLENGE_IN_SAME_BROWSER_SESSION_ONLY",
        "resume_requires_storage_state_hash": True,
        "secret_material_returned": False,
        "authority": _authority(),
    }
    core["handoff_commitment"] = _commit(b"GREMLIN-FERRET-HANDOFF/v0.1\0", core)
    return core


def _verify_handoff(handoff: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    if not isinstance(handoff, Mapping):
        raise FerretHandoffError("handoff must be a mapping")
    handoff_dict = dict(handoff)
    try:
        supplied = _strict_commitment(
            handoff_dict.pop("handoff_commitment", None), "handoff_commitment"
        )
    except ValueError as exc:
        raise FerretHandoffError(str(exc)) from exc
    expected = _commit(b"GREMLIN-FERRET-HANDOFF/v0.1\0", handoff_dict)
    if not secrets.compare_digest(supplied, expected):
        raise FerretHandoffError("handoff commitment mismatch")
    if handoff_dict.get("status") != "USER_ACTION_REQUIRED":
        raise FerretHandoffError("handoff is not waiting for user action")
    return handoff_dict, supplied


def complete_human_handoff(
    handoff: Mapping[str, Any],
    *,
    actor: str,
    completed: bool,
    resolved_url: str,
    storage_state_sha256: str,
) -> dict[str, Any]:
    """Create a resume receipt after the human completes the gate in the same browser origin."""
    handoff_dict, handoff_commitment = _verify_handoff(handoff)
    completed_value = _strict_bool(completed, "completed")
    if not completed_value:
        raise FerretHandoffError("explicit human completion is required")
    actor_name = _strict_text(actor, "actor")

    normalized_url = _normalize_public_https_url(_strict_text(resolved_url, "resolved_url"))
    if _origin(normalized_url) != handoff_dict["target_origin"]:
        raise FerretHandoffError("resume origin differs from handoff target origin")

    try:
        state_hash = _strict_commitment(storage_state_sha256, "storage_state_sha256")
    except ValueError as exc:
        raise FerretHandoffError(str(exc)) from exc

    core = {
        "schema": "GREMLIN_FERRET_HANDOFF_RESUME_V0_1",
        "resume_id": secrets.token_hex(16),
        "completed_unix_ns": time.time_ns(),
        "actor": actor_name,
        "handoff_id": handoff_dict["handoff_id"],
        "handoff_commitment": handoff_commitment,
        "preview_commitment": handoff_dict["preview_commitment"],
        "target_origin": handoff_dict["target_origin"],
        "resolved_url": normalized_url,
        "storage_state_sha256": state_hash,
        "status": "READY_TO_RESUME",
        "scope": "SAME_ORIGIN_EXACT_HANDOFF_SESSION",
        "secret_material_returned": False,
    }
    core["resume_commitment"] = _commit(b"GREMLIN-FERRET-RESUME/v0.1\0", core)
    return core


def verify_handoff_resume(
    handoff: Mapping[str, Any], resume: Mapping[str, Any]
) -> None:
    handoff_dict, handoff_commitment = _verify_handoff(handoff)
    if not isinstance(resume, Mapping):
        raise FerretHandoffError("resume must be a mapping")

    resume_dict = dict(resume)
    try:
        supplied = _strict_commitment(
            resume_dict.pop("resume_commitment", None), "resume_commitment"
        )
    except ValueError as exc:
        raise FerretHandoffError(str(exc)) from exc
    expected = _commit(b"GREMLIN-FERRET-RESUME/v0.1\0", resume_dict)
    if not secrets.compare_digest(supplied, expected):
        raise FerretHandoffError("resume commitment mismatch")
    if resume_dict.get("status") != "READY_TO_RESUME":
        raise FerretHandoffError("resume receipt is not ready")
    if resume_dict.get("handoff_id") != handoff_dict.get("handoff_id"):
        raise FerretHandoffError("resume belongs to another handoff")
    if resume_dict.get("handoff_commitment") != handoff_commitment:
        raise FerretHandoffError("resume handoff commitment mismatch")
    if resume_dict.get("preview_commitment") != handoff_dict.get("preview_commitment"):
        raise FerretHandoffError("resume preview commitment mismatch")
    if resume_dict.get("target_origin") != handoff_dict.get("target_origin"):
        raise FerretHandoffError("resume origin binding mismatch")


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
    try:
        status = _strict_text(result.status, "execution status")
        resolved_url = _normalize_public_https_url(
            _strict_text(result.resolved_url, "execution resolved_url")
        )
    except ValueError as exc:
        raise FerretExecutionError(str(exc)) from exc
    if not isinstance(result.evidence, Mapping):
        raise FerretExecutionError("FERRET backend evidence must be a mapping")

    core = {
        "schema": "GREMLIN_FERRET_EXECUTION_RECEIPT_V0_1",
        "preview_id": preview["preview_id"],
        "preview_commitment": preview["preview_commitment"],
        "authorization_id": authorization["authorization_id"],
        "authorization_commitment": authorization["authorization_commitment"],
        "started_unix_ns": started,
        "finished_unix_ns": time.time_ns(),
        "status": status,
        "resolved_url": resolved_url,
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
