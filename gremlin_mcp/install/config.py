from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping
import os

try:
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]


CONFIG_SCHEMA = "GREMLIN_CONFIG_V0_1"
_ALLOWED_CONFIG_KEYS = frozenset({"schema", "runtime", "network", "research", "logging"})
_ALLOWED_SECTION_KEYS = {
    "runtime": frozenset({"transport", "state"}),
    "network": frozenset({"internet", "local_http"}),
    "research": frozenset({"max_workers", "max_sources"}),
    "logging": frozenset({"level"}),
}
_ALLOWED_POLICY_KEYS = frozenset({"runtime", "network", "research"})
_ALLOWED_POLICY_SECTION_KEYS = {
    "runtime": frozenset({"force_transport"}),
    "network": frozenset({"internet", "local_http"}),
    "research": frozenset({"max_workers", "max_sources"}),
}

DEFAULT_CONFIG: dict[str, Any] = {
    "schema": CONFIG_SCHEMA,
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


def _require_table(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a table/object")
    return value


def _strict_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be boolean")
    return value


def _strict_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def _strict_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field} must be non-empty")
    return text


def _reject_unknown_keys(value: Mapping[str, Any], allowed: frozenset[str], field: str) -> None:
    unknown = sorted(str(key) for key in value if key not in allowed)
    if unknown:
        raise ValueError(f"{field} contains unsupported keys: {unknown}")


def _bool_env(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean environment value: {value!r}")


def _env_value(values: Mapping[str, str], name: str) -> str | None:
    if name not in values:
        return None
    value = values[name]
    if not isinstance(value, str):
        raise ValueError(f"{name} environment value must be a string")
    if not value.strip():
        return None
    return value


def _env_int(value: str, name: str) -> int:
    text = value.strip()
    if not text or any(ch not in "0123456789" for ch in text):
        raise ValueError(f"{name} environment value must be a positive decimal integer")
    return int(text, 10)


def env_overrides(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    values = os.environ if env is None else env
    out: dict[str, Any] = {}

    def set_nested(section: str, key: str, value: Any) -> None:
        out.setdefault(section, {})[key] = value

    value = _env_value(values, "GREMLIN_TRANSPORT")
    if value is not None:
        set_nested("runtime", "transport", value.strip())
    value = _env_value(values, "GREMLIN_INTERNET")
    if value is not None:
        set_nested("network", "internet", _bool_env(value))
    value = _env_value(values, "GREMLIN_LOCAL_HTTP")
    if value is not None:
        set_nested("network", "local_http", _bool_env(value))
    value = _env_value(values, "GREMLIN_MAX_WORKERS")
    if value is not None:
        set_nested("research", "max_workers", _env_int(value, "GREMLIN_MAX_WORKERS"))
    value = _env_value(values, "GREMLIN_MAX_SOURCES")
    if value is not None:
        set_nested("research", "max_sources", _env_int(value, "GREMLIN_MAX_SOURCES"))
    value = _env_value(values, "GREMLIN_LOG_LEVEL")
    if value is not None:
        set_nested("logging", "level", value.strip())
    return out


def _validate_machine_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(_require_table(policy, "machine policy"))
    _reject_unknown_keys(body, _ALLOWED_POLICY_KEYS, "machine policy")
    normalized: dict[str, Any] = {}
    for section, allowed in _ALLOWED_POLICY_SECTION_KEYS.items():
        if section not in body:
            continue
        table = dict(_require_table(body[section], f"machine policy.{section}"))
        _reject_unknown_keys(table, allowed, f"machine policy.{section}")
        normalized[section] = table
    return normalized


def _apply_machine_policy(config: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    """Apply restrictive machine policy after user/env/CLI configuration.

    v0.1 intentionally supports only restrictions. Policy cannot grant product
    entitlements; the signed license and client profile remain separate gates.
    Malformed policy is rejected rather than coerced or silently ignored.
    """
    out = deepcopy(dict(config))
    body = _validate_machine_policy(policy)
    p_network = body.get("network", {})
    p_research = body.get("research", {})
    p_runtime = body.get("runtime", {})

    if "internet" in p_network:
        policy_value = _strict_bool(p_network["internet"], "machine policy.network.internet")
        out["network"]["internet"] = out["network"]["internet"] and policy_value
    if "local_http" in p_network:
        policy_value = _strict_bool(p_network["local_http"], "machine policy.network.local_http")
        out["network"]["local_http"] = out["network"]["local_http"] and policy_value

    if "max_workers" in p_research:
        ceiling = _strict_int(p_research["max_workers"], "machine policy.research.max_workers")
        if not 1 <= ceiling <= 256:
            raise ValueError("machine policy.research.max_workers must be in 1..256")
        out["research"]["max_workers"] = min(out["research"]["max_workers"], ceiling)
    if "max_sources" in p_research:
        ceiling = _strict_int(p_research["max_sources"], "machine policy.research.max_sources")
        if not 1 <= ceiling <= 1024:
            raise ValueError("machine policy.research.max_sources must be in 1..1024")
        out["research"]["max_sources"] = min(out["research"]["max_sources"], ceiling)

    if "force_transport" in p_runtime:
        force_transport = _strict_text(p_runtime["force_transport"], "machine policy.runtime.force_transport")
        if force_transport not in {"stdio", "streamable-http"}:
            raise ValueError("machine policy.runtime.force_transport must be stdio or streamable-http")
        out["runtime"]["transport"] = force_transport
    return out


def validate_runtime_config(config: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(_require_table(config, "configuration"))
    _reject_unknown_keys(body, _ALLOWED_CONFIG_KEYS, "configuration")
    if body.get("schema") != CONFIG_SCHEMA:
        raise ValueError("unsupported GREMLIN config schema")

    for section, allowed in _ALLOWED_SECTION_KEYS.items():
        table = _require_table(body.get(section), section)
        _reject_unknown_keys(table, allowed, section)

    runtime = dict(body["runtime"])
    network = dict(body["network"])
    research = dict(body["research"])
    logging = dict(body["logging"])

    transport = _strict_text(runtime.get("transport"), "runtime.transport")
    if transport not in {"stdio", "streamable-http"}:
        raise ValueError("runtime.transport must be stdio or streamable-http")
    state = _strict_text(runtime.get("state"), "runtime.state")

    internet = _strict_bool(network.get("internet"), "network.internet")
    local_http = _strict_bool(network.get("local_http"), "network.local_http")

    workers = _strict_int(research.get("max_workers"), "research.max_workers")
    sources = _strict_int(research.get("max_sources"), "research.max_sources")
    if not 1 <= workers <= 256:
        raise ValueError("research.max_workers must be in 1..256")
    if not 1 <= sources <= 1024:
        raise ValueError("research.max_sources must be in 1..1024")

    level = _strict_text(logging.get("level"), "logging.level").casefold()
    if level not in {"debug", "info", "warning", "error"}:
        raise ValueError("logging.level must be debug, info, warning or error")

    return {
        "schema": CONFIG_SCHEMA,
        "runtime": {"transport": transport, "state": state},
        "network": {"internet": internet, "local_http": local_http},
        "research": {"max_workers": workers, "max_sources": sources},
        "logging": {"level": level},
    }


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
    if cli_overrides is not None:
        if not isinstance(cli_overrides, Mapping):
            raise ValueError("cli_overrides must be a mapping")
        effective = _deep_merge(effective, cli_overrides)
    # Validate ordinary settings before applying policy so malformed user/CLI
    # values cannot be coerced while the restrictive intersection is computed.
    effective = validate_runtime_config(effective)
    effective = _apply_machine_policy(effective, _read_toml(machine_policy_path))
    return validate_runtime_config(effective)
