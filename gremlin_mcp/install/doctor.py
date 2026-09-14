from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
from typing import Any, Mapping

from gremlin_mcp.product import ProductRuntime

from .config import load_effective_config
from .paths import GremlinPaths, resolve_paths
from .secrets import secret_store_status


@dataclass(frozen=True)
class DoctorCheck:
    check: str
    status: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"check": self.check, "status": self.status, "detail": self.detail}


def _nearest_existing(path: Path) -> Path | None:
    current = path
    while not current.exists():
        parent = current.parent
        if parent == current:
            return None
        current = parent
    return current


def _writable_target(path: str) -> tuple[bool, str]:
    target = Path(path)
    existing = target if target.exists() else _nearest_existing(target)
    if existing is None:
        return False, "no existing ancestor"
    writable = os.access(existing, os.W_OK)
    return writable, str(existing)


def _env_text(env: Mapping[str, str], name: str) -> str | None:
    if name not in env:
        return None
    value = env[name]
    if not isinstance(value, str):
        raise ValueError(f"{name} environment value must be a string")
    text = value.strip()
    return text or None


def _license_configuration(paths: GremlinPaths, env: Mapping[str, str]) -> tuple[str | None, str | None, str | None, str | None]:
    license_key = _env_text(env, "GREMLIN_LICENSE_KEY")
    license_path = _env_text(env, "GREMLIN_LICENSE_PATH")
    public_key = _env_text(env, "GREMLIN_LICENSE_PUBLIC_KEY")
    profile = _env_text(env, "GREMLIN_CLIENT_PROFILE")

    if license_key is None and license_path is None and Path(paths.license_file).is_file():
        license_path = paths.license_file
    if public_key is None:
        candidate = Path(paths.shared_data_root) / "issuer-public.pem"
        if candidate.is_file():
            public_key = str(candidate)
    if profile is None and Path(paths.client_profile_file).is_file():
        profile = paths.client_profile_file
    return license_path, license_key, public_key, profile


def _product_status(runtime: ProductRuntime) -> tuple[dict[str, Any] | None, DoctorCheck]:
    try:
        raw = runtime.status()
    except Exception as exc:
        return None, DoctorCheck("license", "FAIL", f"{type(exc).__name__}: product entitlement status failed")
    if not isinstance(raw, Mapping):
        return None, DoctorCheck("license", "FAIL", "product runtime returned a non-object status")
    product = dict(raw)
    status = product.get("status")
    if not isinstance(status, str) or not status.strip():
        return product, DoctorCheck("license", "FAIL", "product runtime returned an invalid status field")
    status = status.strip()
    if status == "LICENSED":
        return product, DoctorCheck("license", "PASS", "signed product entitlement admitted")
    reason = product.get("reason")
    detail = reason.strip() if isinstance(reason, str) and reason.strip() else status
    return product, DoctorCheck("license", "FAIL", detail)


def run_doctor(
    *,
    platform: str | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if env is not None and not isinstance(env, Mapping):
        raise ValueError("env must be a mapping of strings")
    environ = os.environ if env is None else env
    checks: list[DoctorCheck] = []

    try:
        paths = resolve_paths(platform=platform, env=environ)
        checks.append(DoctorCheck("paths", "PASS", f"resolved {paths.platform} installation layout"))
    except Exception as exc:
        checks.append(DoctorCheck("paths", "FAIL", f"{type(exc).__name__}: {exc}"))
        return _result(checks, paths=None, config=None, product=None, secret_store=None)

    for name, target in (
        ("config_parent_writable", paths.config_dir),
        ("state_parent_writable", paths.state_dir),
        ("cache_parent_writable", paths.cache_dir),
    ):
        writable, ancestor = _writable_target(target)
        checks.append(
            DoctorCheck(name, "PASS" if writable else "FAIL", f"nearest existing ancestor: {ancestor}")
        )

    try:
        config = load_effective_config(
            user_config_path=paths.config_file,
            machine_policy_path=paths.machine_policy_file,
            env=environ,
        )
        checks.append(DoctorCheck("config", "PASS", "effective GREMLIN_CONFIG_V0_1 validated"))
    except Exception as exc:
        config = None
        checks.append(DoctorCheck("config", "FAIL", f"{type(exc).__name__}: {exc}"))

    executable = shutil.which("gremlin-product-mcp")
    checks.append(
        DoctorCheck(
            "product_mcp_entrypoint",
            "PASS" if executable else "WARN",
            executable or "gremlin-product-mcp is not on PATH (normal in source-only checkout)",
        )
    )

    product: dict[str, Any] | None = None
    try:
        license_path, license_key, public_key, profile = _license_configuration(paths, environ)
    except ValueError as exc:
        checks.append(DoctorCheck("license", "FAIL", str(exc)))
    else:
        if not license_path and not license_key:
            checks.append(DoctorCheck("license", "WARN", "no product license configured"))
        elif not public_key:
            checks.append(DoctorCheck("license", "FAIL", "license is configured but issuer public key is unavailable"))
        else:
            try:
                runtime = ProductRuntime.from_configuration(
                    license_path=license_path,
                    license_key=license_key,
                    public_key_path=public_key,
                    profile_path=profile,
                    require_license=True,
                )
            except Exception as exc:
                checks.append(DoctorCheck("license", "FAIL", f"{type(exc).__name__}: product runtime initialization failed"))
            else:
                product, product_check = _product_status(runtime)
                checks.append(product_check)

    if config is not None and config["runtime"]["transport"] == "streamable-http":
        local_http = config["network"].get("local_http")
        if type(local_http) is not bool:
            checks.append(DoctorCheck("local_http_policy", "FAIL", "validated config returned non-boolean local_http"))
        else:
            checks.append(
                DoctorCheck(
                    "local_http_policy",
                    "PASS" if local_http else "FAIL",
                    "local streamable HTTP enabled" if local_http else "HTTP transport requested while local_http is disabled",
                )
            )

    secret_state: dict[str, object] | None
    try:
        raw_secret_state = secret_store_status(paths)
    except Exception as exc:
        secret_state = None
        checks.append(DoctorCheck("secret_store", "FAIL", f"{type(exc).__name__}: secret-store status failed"))
    else:
        if not isinstance(raw_secret_state, Mapping):
            secret_state = None
            checks.append(DoctorCheck("secret_store", "FAIL", "secret-store status returned a non-object payload"))
        else:
            secret_state = dict(raw_secret_state)
            available = secret_state.get("available")
            if type(available) is not bool:
                checks.append(DoctorCheck("secret_store", "FAIL", "secret-store availability must be boolean"))
            else:
                backend = secret_state.get("backend")
                backend_text = backend if isinstance(backend, str) and backend else "UNKNOWN"
                checks.append(
                    DoctorCheck(
                        "secret_store",
                        "PASS" if available else "WARN",
                        f"backend={backend_text} available={available}",
                    )
                )
    return _result(checks, paths=paths, config=config, product=product, secret_store=secret_state)


def _result(
    checks: list[DoctorCheck],
    *,
    paths: GremlinPaths | None,
    config: dict[str, Any] | None,
    product: dict[str, Any] | None,
    secret_store: dict[str, object] | None,
) -> dict[str, Any]:
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for check in checks:
        if check.status not in counts:
            raise RuntimeError(f"unsupported doctor check status: {check.status}")
        counts[check.status] += 1
    overall = "FAIL" if counts["FAIL"] else ("WARN" if counts["WARN"] else "PASS")
    return {
        "schema": "GREMLIN_DOCTOR_V0_1",
        "status": overall,
        "counts": counts,
        "checks": [row.as_dict() for row in checks],
        "paths": paths.as_dict() if paths else None,
        "config": config,
        "product": product,
        "secret_store": secret_store,
    }


def doctor_json(**kwargs: Any) -> str:
    return json.dumps(run_doctor(**kwargs), ensure_ascii=False, indent=2, sort_keys=True)
