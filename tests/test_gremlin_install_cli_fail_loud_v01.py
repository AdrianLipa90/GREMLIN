from __future__ import annotations

from argparse import Namespace

import gremlin_mcp.install.cli as install_cli
from gremlin_mcp.install.provider_integrations import ProviderAction, PROVIDER_ACTION_SCHEMA


def _args(action: str, provider: str = "opencode") -> Namespace:
    return Namespace(provider_action=action, provider=provider, platform="linux", json=True)


def _provider_result(provider: str, status: str) -> ProviderAction:
    return ProviderAction(PROVIDER_ACTION_SCHEMA, provider, status, "/usr/bin/provider", "/tmp/provider.json", None)


def _avoid_real_paths(monkeypatch) -> None:
    monkeypatch.setattr(install_cli, "resolve_paths", lambda platform=None: object())


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
    assert install_cli._provider_action(_args("test", "codex")) == 0


def test_device_status_secret_store_unavailable_returns_nonzero(monkeypatch) -> None:
    _avoid_real_paths(monkeypatch)
    monkeypatch.setattr(install_cli, "secret_store_status", lambda _paths: {"available": False, "backend": "none"})
    assert install_cli._device_status(Namespace(platform="linux", json=True)) == 1
