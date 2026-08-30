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


def _license_configuration(paths: GremlinPaths, env: Mapping[str, str]) -> tuple[str | None, str | None, str | None, str | None]:
    license_key = str(env.get("GREMLIN_LICENSE_KEY") or "").strip() or None
    license_path = str(env.get("GREMLIN_LICENSE_PATH") or "").strip() or None
    public_key = str(env.get("GREMLIN_LICENSE_PUBLIC_KEY") or "").strip() or None
    profile = str(env.get("GREMLIN_CLIENT_PROFILE") or "").strip() or None

    if license_key is None and license_path is None and Path(paths.license_file).is_file():
        license_path = paths.license_file
    if public_key is None:
        candidate = Path(paths.shared_data_root) / "issuer-public.pem"
        if candidate.is_file():
            public_key = str(candidate)
    if profile is None and Path(paths.client_profile_file).is_file():
        profile = paths.client_profile_file
    return license_path, license_key, public_key, profile


def run_doctor(
    *,
    platform: str | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
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

    license_path, license_key, public_key, profile = _license_configuration(paths, environ)
    if not license_path and not license_key:
        checks.append(DoctorCheck("license", "WARN", "no product license configured"))
        product = None
    elif not public_key:
        checks.append(DoctorCheck("license", "FAIL", "license is configured but issuer public key is unavailable"))
        product = None
    else:
        runtime = ProductRuntime.from_configuration(
            license_path=license_path,
            license_key=license_key,
            public_key_path=public_key,
            profile_path=profile,
            require_license=True,
        )
        product = runtime.status()
        product_status = str(product.get("status") or "UNKNOWN")
        if product_status == "LICENSED":
            checks.append(DoctorCheck("license", "PASS", "signed product entitlement admitted"))
        else:
            reason = str(product.get("reason") or product_status)
            checks.append(DoctorCheck("license", "FAIL", reason))

    if config is not None and config["runtime"]["transport"] == "streamable-http":
        local_http = bool(config["network"].get("local_http"))
        checks.append(
            DoctorCheck(
                "local_http_policy",
                "PASS" if local_http else "FAIL",
                "local streamable HTTP enabled" if local_http else "HTTP transport requested while local_http is disabled",
            )
        )

    secret_state = secret_store_status(paths)
    secret_available = bool(secret_state.get("available"))
    checks.append(
        DoctorCheck(
            "secret_store",
            "PASS" if secret_available else "WARN",
            f"backend={secret_state.get('backend')} available={secret_available}",
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
        counts[check.status] = counts.get(check.status, 0) + 1
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
