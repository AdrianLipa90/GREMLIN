from __future__ import annotations

from gremlin_mcp.install.paths import resolve_paths


def test_windows_paths_use_roaming_for_config_and_local_for_state() -> None:
    paths = resolve_paths(
        platform="windows",
        env={
            "USERPROFILE": r"C:\Users\Alice",
            "APPDATA": r"C:\Users\Alice\AppData\Roaming",
            "LOCALAPPDATA": r"C:\Users\Alice\AppData\Local",
            "ProgramData": r"C:\ProgramData",
        },
    )
    assert paths.config_file == r"C:\Users\Alice\AppData\Roaming\GREMLIN\config.toml"
    assert paths.license_file == r"C:\Users\Alice\AppData\Roaming\GREMLIN\license.json"
    assert paths.state_db == r"C:\Users\Alice\AppData\Local\GREMLIN\state\gremlin-worker.sqlite3"
    assert paths.install_root == r"C:\Users\Alice\AppData\Local\Programs\GREMLIN"
    assert paths.machine_policy_file == r"C:\ProgramData\GREMLIN\policy.toml"


def test_windows_paths_have_safe_fallbacks() -> None:
    paths = resolve_paths(platform="windows", env={"USERPROFILE": r"D:\User"})
    assert paths.config_dir == r"D:\User\AppData\Roaming\GREMLIN"
    assert paths.state_dir == r"D:\User\AppData\Local\GREMLIN\state"


def test_linux_paths_follow_xdg_overrides() -> None:
    paths = resolve_paths(
        platform="linux",
        env={
            "HOME": "/home/alice",
            "XDG_CONFIG_HOME": "/cfg",
            "XDG_STATE_HOME": "/state",
            "XDG_CACHE_HOME": "/cache",
            "XDG_DATA_HOME": "/data",
        },
    )
    assert paths.config_file == "/cfg/gremlin/config.toml"
    assert paths.state_db == "/state/gremlin/gremlin-worker.sqlite3"
    assert paths.cache_dir == "/cache/gremlin"
    assert paths.diagnostics_dir == "/data/gremlin/diagnostics"
    assert paths.machine_policy_file == "/etc/gremlin/policy.toml"
    assert paths.install_root == "/usr/lib/gremlin"
    assert paths.shared_data_root == "/usr/share/gremlin"


def test_linux_paths_use_xdg_defaults() -> None:
    paths = resolve_paths(platform="linux", env={"HOME": "/home/alice"})
    assert paths.config_dir == "/home/alice/.config/gremlin"
    assert paths.state_dir == "/home/alice/.local/state/gremlin"
    assert paths.cache_dir == "/home/alice/.cache/gremlin"
    assert paths.data_dir == "/home/alice/.local/share/gremlin"
