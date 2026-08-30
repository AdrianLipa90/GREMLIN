from __future__ import annotations

from dataclasses import asdict, dataclass
import ntpath
import os
import posixpath
from typing import Mapping


@dataclass(frozen=True)
class GremlinPaths:
    platform: str
    config_dir: str
    state_dir: str
    cache_dir: str
    data_dir: str
    logs_dir: str
    diagnostics_dir: str
    config_file: str
    license_file: str
    client_profile_file: str
    integrations_file: str
    state_db: str
    machine_policy_file: str
    install_root: str
    shared_data_root: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def _env(env: Mapping[str, str], name: str) -> str:
    return str(env.get(name) or "").strip()


def _windows_paths(env: Mapping[str, str]) -> GremlinPaths:
    user_profile = _env(env, "USERPROFILE") or _env(env, "HOME")
    if not user_profile:
        raise RuntimeError("USERPROFILE is required to resolve GREMLIN Windows paths")

    roaming = _env(env, "APPDATA") or ntpath.join(user_profile, "AppData", "Roaming")
    local = _env(env, "LOCALAPPDATA") or ntpath.join(user_profile, "AppData", "Local")
    program_data = _env(env, "ProgramData") or r"C:\ProgramData"

    config_dir = ntpath.join(roaming, "GREMLIN")
    state_dir = ntpath.join(local, "GREMLIN", "state")
    cache_dir = ntpath.join(local, "GREMLIN", "cache")
    data_dir = ntpath.join(local, "GREMLIN", "data")
    install_root = ntpath.join(local, "Programs", "GREMLIN")
    shared_data = ntpath.join(install_root, "resources")

    return GremlinPaths(
        platform="windows",
        config_dir=config_dir,
        state_dir=state_dir,
        cache_dir=cache_dir,
        data_dir=data_dir,
        logs_dir=ntpath.join(local, "GREMLIN", "logs"),
        diagnostics_dir=ntpath.join(data_dir, "diagnostics"),
        config_file=ntpath.join(config_dir, "config.toml"),
        license_file=ntpath.join(config_dir, "license.json"),
        client_profile_file=ntpath.join(config_dir, "client-profile.json"),
        integrations_file=ntpath.join(config_dir, "integrations.json"),
        state_db=ntpath.join(state_dir, "gremlin-worker.sqlite3"),
        machine_policy_file=ntpath.join(program_data, "GREMLIN", "policy.toml"),
        install_root=install_root,
        shared_data_root=shared_data,
    )


def _linux_paths(env: Mapping[str, str]) -> GremlinPaths:
    home = _env(env, "HOME")
    if not home:
        raise RuntimeError("HOME is required to resolve GREMLIN Linux paths")

    config_home = _env(env, "XDG_CONFIG_HOME") or posixpath.join(home, ".config")
    state_home = _env(env, "XDG_STATE_HOME") or posixpath.join(home, ".local", "state")
    cache_home = _env(env, "XDG_CACHE_HOME") or posixpath.join(home, ".cache")
    data_home = _env(env, "XDG_DATA_HOME") or posixpath.join(home, ".local", "share")

    config_dir = posixpath.join(config_home, "gremlin")
    state_dir = posixpath.join(state_home, "gremlin")
    cache_dir = posixpath.join(cache_home, "gremlin")
    data_dir = posixpath.join(data_home, "gremlin")

    return GremlinPaths(
        platform="linux",
        config_dir=config_dir,
        state_dir=state_dir,
        cache_dir=cache_dir,
        data_dir=data_dir,
        logs_dir=posixpath.join(state_dir, "logs"),
        diagnostics_dir=posixpath.join(data_dir, "diagnostics"),
        config_file=posixpath.join(config_dir, "config.toml"),
        license_file=posixpath.join(config_dir, "license.json"),
        client_profile_file=posixpath.join(config_dir, "client-profile.json"),
        integrations_file=posixpath.join(config_dir, "integrations.json"),
        state_db=posixpath.join(state_dir, "gremlin-worker.sqlite3"),
        machine_policy_file="/etc/gremlin/policy.toml",
        install_root="/usr/lib/gremlin",
        shared_data_root="/usr/share/gremlin",
    )


def resolve_paths(
    *,
    platform: str | None = None,
    env: Mapping[str, str] | None = None,
) -> GremlinPaths:
    """Resolve canonical GREMLIN paths for Windows or Linux.

    The resolver accepts an explicit platform and environment so packaging and CI
    can test both operating-system layouts without running on both hosts.
    """
    environ = os.environ if env is None else env
    requested = (platform or ("windows" if os.name == "nt" else "linux")).strip().casefold()
    if requested in {"windows", "win32", "nt"}:
        return _windows_paths(environ)
    if requested in {"linux", "posix"}:
        return _linux_paths(environ)
    raise RuntimeError(f"unsupported GREMLIN installation platform: {requested}")
