from __future__ import annotations

import json
import os
from pathlib import Path
import stat

import pytest

import gremlin_mcp.install.integrations as integrations


def test_backup_preserves_source_permissions_without_post_write_window(tmp_path: Path) -> None:
    config = tmp_path / "client.json"
    config.write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")
    if os.name != "nt":
        config.chmod(0o600)
    receipt = integrations.install_json_mcp(
        client_id="strict-client",
        config_path=config,
        entry={"command": "gremlin-product-mcp", "args": []},
        backup_root=tmp_path / "backups",
    )
    assert receipt.backup_path is not None
    backup = Path(receipt.backup_path)
    assert backup.is_file()
    if os.name != "nt":
        assert stat.S_IMODE(backup.stat().st_mode) == 0o600


def test_new_config_is_removed_when_post_write_verification_fails(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "new-client.json"
    real_load = integrations._load
    calls = 0

    def inconsistent_second_read(path: Path):
        nonlocal calls
        calls += 1
        if calls == 2:
            return {"mcpServers": {}}, b'{"mcpServers":{}}'
        return real_load(path)

    monkeypatch.setattr(integrations, "_load", inconsistent_second_read)
    with pytest.raises(RuntimeError, match="verification failed; original configuration restored"):
        integrations.install_json_mcp(
            client_id="strict-client",
            config_path=config,
            entry={"command": "gremlin-product-mcp"},
            backup_root=tmp_path / "backups",
        )
    assert not config.exists()


def test_remove_rejects_false_success_when_entry_is_absent(tmp_path: Path) -> None:
    config = tmp_path / "client.json"
    original = {"mcpServers": {"other": {"command": "other"}}}
    config.write_text(json.dumps(original), encoding="utf-8")
    with pytest.raises(ValueError, match="entry is not installed"):
        integrations.remove_json_mcp(
            client_id="strict-client",
            config_path=config,
            backup_root=tmp_path / "backups",
        )
    assert json.loads(config.read_text(encoding="utf-8")) == original


def test_server_name_and_client_id_do_not_silently_coerce_types(tmp_path: Path) -> None:
    config = tmp_path / "client.json"
    config.write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="client_id must be a string"):
        integrations.install_json_mcp(
            client_id=123,  # type: ignore[arg-type]
            config_path=config,
            entry={"command": "gremlin-product-mcp"},
            backup_root=tmp_path / "backups",
        )
    with pytest.raises(ValueError, match="server_name must be a string"):
        integrations.inspect_json_mcp(config, server_name=123)  # type: ignore[arg-type]
