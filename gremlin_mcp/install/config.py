from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping
import os

try:
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]


DEFAULT_CONFIG: dict[str, Any] = {
    "schema": "GREMLIN_CONFIG_V0_1",
    "runtime": {
        "transport": "stdio",
        "state": "auto",
    },
    "network": {
        "internet": True,
        "local_http": False,
    },
    "research": {
        "max_workers": 4,
        "max_sources": 24,
    },
    "logging": {
        "level": "info",
    },
}


def _deep_merge(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    out = deepcopy(dict(base))
    for key, value in overlay.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), Mapping):
            out[key] = _deep_merge(out[key], value)  # type: ignore[arg-type]
        else:
            out[key] = deepcopy(value)
    return out


def _read_toml(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    p = Path(path)
    if not p.is_file():
        return {}
    with p.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"configuration must decode to a table: {p}")
    return data


def _bool_env(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean environment value: {value!r}")


def env_overrides(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    values = os.environ if env is None else env
    out: dict[str, Any] = {}

    def set_nested(section: str, key: str, value: Any) -> None:
        out.setdefault(section, {})[key] = value

    if values.get("GREMLIN_TRANSPORT"):
        set_nested("runtime", "transport", str(values["GREMLIN_TRANSPORT"]).strip())
    if values.get("GREMLIN_INTERNET"):
        set_nested("network", "internet", _bool_env(str(values["GREMLIN_INTERNET"])))
    if values.get("GREMLIN_LOCAL_HTTP"):
        set_nested("network", "local_http", _bool_env(str(values["GREMLIN_LOCAL_HTTP"])))
    if values.get("GREMLIN_MAX_WORKERS"):
        set_nested("research", "max_workers", int(values["GREMLIN_MAX_WORKERS"]))
    if values.get("GREMLIN_MAX_SOURCES"):
        set_nested("research", "max_sources", int(values["GREMLIN_MAX_SOURCES"]))
    if values.get("GREMLIN_LOG_LEVEL"):
        set_nested("logging", "level", str(values["GREMLIN_LOG_LEVEL"]).strip())
    return out


def _apply_machine_policy(config: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    """Apply restrictive machine policy after user/env/CLI configuration.

    v0.1 intentionally supports only restrictions. Policy cannot grant product
    entitlements; the signed license and client profile remain separate gates.
    """
    out = deepcopy(dict(config))
    p_network = dict(policy.get("network") or {})
    p_research = dict(policy.get("research") or {})
    p_runtime = dict(policy.get("runtime") or {})

    if "internet" in p_network:
        out["network"]["internet"] = bool(out["network"].get("internet", True)) and bool(p_network["internet"])
    if "local_http" in p_network:
        out["network"]["local_http"] = bool(out["network"].get("local_http", False)) and bool(p_network["local_http"])

    if "max_workers" in p_research:
        out["research"]["max_workers"] = min(
            int(out["research"].get("max_workers", 4)), int(p_research["max_workers"])
        )
    if "max_sources" in p_research:
        out["research"]["max_sources"] = min(
            int(out["research"].get("max_sources", 24)), int(p_research["max_sources"])
        )

    force_transport = str(p_runtime.get("force_transport") or "").strip()
    if force_transport:
        out["runtime"]["transport"] = force_transport
    return out


def validate_runtime_config(config: Mapping[str, Any]) -> dict[str, Any]:
    out = deepcopy(dict(config))
    if out.get("schema") != "GREMLIN_CONFIG_V0_1":
        raise ValueError("unsupported GREMLIN config schema")

    transport = str(out.get("runtime", {}).get("transport") or "").strip()
    if transport not in {"stdio", "streamable-http"}:
        raise ValueError("runtime.transport must be stdio or streamable-http")
    workers = int(out.get("research", {}).get("max_workers", 0))
    sources = int(out.get("research", {}).get("max_sources", 0))
    if not 1 <= workers <= 256:
        raise ValueError("research.max_workers must be in 1..256")
    if not 1 <= sources <= 1024:
        raise ValueError("research.max_sources must be in 1..1024")
    level = str(out.get("logging", {}).get("level") or "").casefold()
    if level not in {"debug", "info", "warning", "error"}:
        raise ValueError("logging.level must be debug, info, warning or error")
    out["logging"]["level"] = level
    return out


def load_effective_config(
    *,
    user_config_path: str | Path | None = None,
    machine_policy_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    cli_overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve operational configuration.

    Precedence for ordinary settings is defaults < user config < environment < CLI.
    Machine policy is applied last and can only restrict selected capabilities.
    Product entitlements are still enforced independently by ProductRuntime.
    """
    effective = deepcopy(DEFAULT_CONFIG)
    effective = _deep_merge(effective, _read_toml(user_config_path))
    effective = _deep_merge(effective, env_overrides(env))
    effective = _deep_merge(effective, dict(cli_overrides or {}))
    effective = _apply_machine_policy(effective, _read_toml(machine_policy_path))
    return validate_runtime_config(effective)
