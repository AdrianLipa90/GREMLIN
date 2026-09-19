from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

from gremlin_mcp.core import VERSION

from .doctor import run_doctor
from .paths import GremlinPaths
from .provider_integrations import list_providers
from .readiness import evaluate_readiness

SCHEMA = "GREMLIN_SUPPORT_REPORT_V0_1"
DOMAIN = b"GREMLIN-SUPPORT-REPORT/v0.1\x00"
_WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"(?i)(?<![A-Za-z0-9_])[A-Z]:[\\/][^\s\"'<>|]+")
_POSIX_ABSOLUTE_PATH_RE = re.compile(r"(?<![A-Za-z0-9_:/])/(?:[^\s\"'<>|]+)")


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _redaction_tokens(paths: GremlinPaths, env: Mapping[str, str]) -> list[str]:
    values: set[str] = set()
    for value in paths.as_dict().values():
        if isinstance(value, str) and value:
            values.add(value)
    for name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME"):
        raw = env.get(name)
        if isinstance(raw, str) and raw.strip():
            values.add(raw.strip())
    return sorted(values, key=len, reverse=True)


def _redact(text: Any, tokens: list[str]) -> str:
    value = text if isinstance(text, str) else str(text)
    for token in tokens:
        value = value.replace(token, "<path>")
        alt = token.replace("\\", "/")
        if alt != token:
            value = value.replace(alt, "<path>")
    value = _WINDOWS_ABSOLUTE_PATH_RE.sub("<path>", value)
    value = _POSIX_ABSOLUTE_PATH_RE.sub("<path>", value)
    return value


def _sanitized_doctor(payload: Mapping[str, Any], tokens: list[str]) -> dict[str, Any]:
    checks = payload.get("checks")
    safe_checks: list[dict[str, str]] = []
    if isinstance(checks, list):
        for row in checks:
            if not isinstance(row, Mapping):
                continue
            check = row.get("check")
            status = row.get("status")
            detail = row.get("detail")
            if isinstance(check, str) and isinstance(status, str):
                safe_checks.append({
                    "check": check,
                    "status": status,
                    "detail": _redact(detail or "", tokens),
                })

    product = payload.get("product")
    product_summary: dict[str, Any] | None = None
    if isinstance(product, Mapping):
        product_summary = {
            "status": product.get("status"),
            "reason": _redact(product.get("reason") or "", tokens),
        }

    secret = payload.get("secret_store")
    secret_summary: dict[str, Any] | None = None
    if isinstance(secret, Mapping):
        secret_summary = {
            "backend": secret.get("backend"),
            "available": secret.get("available"),
        }

    return {
        "status": payload.get("status"),
        "counts": payload.get("counts"),
        "checks": safe_checks,
        "product": product_summary,
        "secret_store": secret_summary,
    }


def _sanitized_providers(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("providers")
    if not isinstance(rows, list):
        raise RuntimeError("provider discovery payload must contain providers list")
    safe: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise RuntimeError(f"provider discovery row {index} is not an object")
        safe.append({
            "provider_id": row.get("provider_id"),
            "display_name": row.get("display_name"),
            "detected": row.get("detected"),
            "connected": row.get("connected"),
            "connection_status": row.get("connection_status"),
            "integration_mode": row.get("integration_mode"),
        })
    return safe


def build_support_report(
    paths: GremlinPaths,
    *,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if not isinstance(paths, GremlinPaths):
        raise ValueError("paths must be GremlinPaths")
    environ = os.environ if env is None else env
    if not isinstance(environ, Mapping):
        raise ValueError("env must be a mapping")

    doctor = run_doctor(platform=paths.platform, env=environ)
    readiness = evaluate_readiness(paths)
    providers = list_providers(paths, env=environ)
    tokens = _redaction_tokens(paths, environ)

    readiness_providers = readiness.get("providers")
    readiness_runtime = readiness.get("runtime")
    readiness_profile = readiness.get("profile")

    core = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gremlin_version": VERSION,
        "platform": paths.platform,
        "doctor": _sanitized_doctor(doctor, tokens),
        "readiness": {
            "status": readiness.get("status"),
            "runtime": {
                "available": readiness_runtime.get("available") if isinstance(readiness_runtime, Mapping) else None,
                "transport": readiness_runtime.get("transport") if isinstance(readiness_runtime, Mapping) else None,
            },
            "providers": dict(readiness_providers) if isinstance(readiness_providers, Mapping) else None,
            "profile_configured": readiness_profile.get("configured") if isinstance(readiness_profile, Mapping) else None,
            "actions": list(readiness.get("actions") or []),
        },
        "providers": _sanitized_providers(providers),
        "path_presence": {
            "config": Path(paths.config_file).is_file(),
            "license": Path(paths.license_file).is_file(),
            "client_profile": Path(paths.client_profile_file).is_file(),
            "state_db": Path(paths.state_db).is_file(),
            "issuer_public_key": (Path(paths.shared_data_root) / "issuer-public.pem").is_file(),
        },
        "privacy": {
            "license_key_included": False,
            "absolute_paths_included": False,
            "provider_command_output_included": False,
            "config_contents_included": False,
        },
        "authority": {
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        },
    }
    commitment = hashlib.blake2b(DOMAIN + _canonical(core), digest_size=32).hexdigest()
    return {**core, "report_commitment": commitment}


def _verified_report_commitment(payload: Mapping[str, Any]) -> str:
    if payload.get("schema") != SCHEMA:
        raise ValueError("unsupported support report schema")
    supplied = payload.get("report_commitment")
    if not isinstance(supplied, str) or len(supplied) != 64:
        raise ValueError("support report commitment is required")
    core = dict(payload)
    core.pop("report_commitment", None)
    expected = hashlib.blake2b(DOMAIN + _canonical(core), digest_size=32).hexdigest()
    if supplied != expected:
        raise ValueError("support report commitment mismatch")
    return supplied


def write_support_report(paths: GremlinPaths, report: Mapping[str, Any] | None = None) -> Path:
    payload = build_support_report(paths) if report is None else dict(report)
    commitment = _verified_report_commitment(payload)

    directory = Path(paths.diagnostics_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = directory / f"gremlin-support-{stamp}-{commitment[:10]}.json"
    data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with target.open("x", encoding="utf-8") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    if os.name != "nt":
        target.chmod(0o600)
    return target
