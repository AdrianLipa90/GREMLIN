from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

import gremlin_mcp.install.cli as install_cli
from gremlin_mcp.install.paths import GremlinPaths
from gremlin_mcp.install.provider_integrations import ProviderAction, PROVIDER_ACTION_SCHEMA


def _args(action: str, provider: str = "opencode") -> Namespace:
    return Namespace(provider_action=action, provider=provider, platform="linux", json=True)


def _provider_result(provider: str, status: str) -> ProviderAction:
    return ProviderAction(PROVIDER_ACTION_SCHEMA, provider, status, "/usr/bin/provider", "/tmp/provider.json", None)


def _avoid_real_paths(monkeypatch) -> None:
    monkeypatch.setattr(install_cli, "resolve_paths", lambda platform=None: object())


def _install_paths(tmp_path: Path) -> GremlinPaths:
    config = tmp_path / "config"
    state = tmp_path / "state"
    data = tmp_path / "data"
    return GremlinPaths(
        platform="linux",
        config_dir=str(config),
        state_dir=str(state),
        cache_dir=str(tmp_path / "cache"),
        data_dir=str(data),
        logs_dir=str(state / "logs"),
        diagnostics_dir=str(data / "diagnostics"),
        config_file=str(config / "config.toml"),
        license_file=str(config / "license.json"),
        client_profile_file=str(config / "client-profile.json"),
        integrations_file=str(config / "integrations.json"),
        state_db=str(state / "gremlin-worker.sqlite3"),
        machine_policy_file=str(tmp_path / "policy.toml"),
        install_root=str(tmp_path / "install"),
        shared_data_root=str(tmp_path / "resources"),
    )


def test_connect_registered_unverified_is_completed_registration(monkeypatch) -> None:
    _avoid_real_paths(monkeypatch)
    monkeypatch.setattr(install_cli, "connect_provider", lambda provider, _paths: _provider_result(provider, "REGISTERED_UNVERIFIED"))
    assert install_cli._provider_action(_args("connect", "codex")) == 0


def test_connect_configured_unverified_is_completed_configuration(monkeypatch) -> None:
    _avoid_real_paths(monkeypatch)
    monkeypatch.setattr(install_cli, "connect_provider", lambda provider, _paths: _provider_result(provider, "CONFIGURED_UNVERIFIED"))
    assert install_cli._provider_action(_args("connect", "cursor")) == 0


def test_disconnect_manual_remove_required_returns_nonzero(monkeypatch) -> None:
    _avoid_real_paths(monkeypatch)
    monkeypatch.setattr(install_cli, "disconnect_provider", lambda provider, _paths: _provider_result(provider, "MANUAL_REMOVE_REQUIRED"))
    assert install_cli._provider_action(_args("disconnect")) == 1


def test_runtime_not_ready_test_returns_nonzero(monkeypatch) -> None:
    _avoid_real_paths(monkeypatch)
    monkeypatch.setattr(install_cli, "test_provider", lambda provider, _paths: _provider_result(provider, "REGISTERED_RUNTIME_NOT_READY"))
    assert install_cli._provider_action(_args("test")) == 1


def test_registered_unverified_test_returns_nonzero(monkeypatch) -> None:
    _avoid_real_paths(monkeypatch)
    monkeypatch.setattr(install_cli, "test_provider", lambda provider, _paths: _provider_result(provider, "REGISTERED_UNVERIFIED"))
    assert install_cli._provider_action(_args("test", "vscode")) == 1


def test_provider_pass_returns_zero(monkeypatch) -> None:
    _avoid_real_paths(monkeypatch)
    monkeypatch.setattr(install_cli, "test_provider", lambda provider, _paths: _provider_result(provider, "PASS"))
    assert install_cli._provider_action(_args("test", "opencode")) == 0


def test_device_status_secret_store_unavailable_returns_nonzero(monkeypatch) -> None:
    _avoid_real_paths(monkeypatch)
    monkeypatch.setattr(install_cli, "secret_store_status", lambda _paths: {"available": False, "backend": "none"})
    assert install_cli._device_status(Namespace(platform="linux", json=True)) == 1


def test_init_creates_and_validates_default_config(tmp_path: Path, monkeypatch, capsys) -> None:
    paths = _install_paths(tmp_path)
    monkeypatch.setattr(install_cli, "resolve_paths", lambda **_kwargs: paths)

    assert install_cli._init(Namespace(platform="linux", json=True)) == 0
    config = Path(paths.config_file)
    assert config.is_file()
    output = capsys.readouterr().out
    assert '"status": "READY"' in output
    assert '"config_created": true' in output


def test_init_rejects_existing_config_directory_instead_of_reporting_ready(tmp_path: Path, monkeypatch) -> None:
    paths = _install_paths(tmp_path)
    Path(paths.config_file).mkdir(parents=True)
    monkeypatch.setattr(install_cli, "resolve_paths", lambda **_kwargs: paths)

    with pytest.raises(RuntimeError, match="not a regular file"):
        install_cli._init(Namespace(platform="linux", json=True))


def test_init_rejects_invalid_existing_config_instead_of_reporting_ready(tmp_path: Path, monkeypatch) -> None:
    paths = _install_paths(tmp_path)
    config = Path(paths.config_file)
    config.parent.mkdir(parents=True)
    config.write_text(
        'schema = "GREMLIN_CONFIG_V0_1"\n[runtime]\ntransport = "invalid"\n',
        encoding="utf-8",
    )
    before = config.read_bytes()
    monkeypatch.setattr(install_cli, "resolve_paths", lambda **_kwargs: paths)

    with pytest.raises(ValueError, match="runtime.transport"):
        install_cli._init(Namespace(platform="linux", json=True))
    assert config.read_bytes() == before


def test_device_status_rejects_non_boolean_secret_store_availability(tmp_path: Path, monkeypatch) -> None:
    paths = _install_paths(tmp_path)
    monkeypatch.setattr(install_cli, "resolve_paths", lambda **_kwargs: paths)
    monkeypatch.setattr(
        install_cli,
        "secret_store_status",
        lambda _paths: {"schema": "GREMLIN_SECRET_STORE_STATUS_V0_1", "available": "false"},
    )

    with pytest.raises(RuntimeError, match="availability status must be boolean"):
        install_cli._device_status(Namespace(platform="linux", json=True))
