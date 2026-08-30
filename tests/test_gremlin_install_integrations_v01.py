from __future__ import annotations

import json

import pytest

from gremlin_mcp.install.integrations import gremlin_stdio_entry, inspect_json_mcp, install_json_mcp, remove_json_mcp
from gremlin_mcp.install.paths import resolve_paths


def test_generic_json_mcp_install_preserves_existing_servers_and_backs_up(tmp_path) -> None:
    config = tmp_path / "client.json"
    original = {
        "theme": "dark",
        "mcpServers": {
            "existing": {"command": "existing-tool", "args": []},
        },
    }
    config.write_text(json.dumps(original), encoding="utf-8")
    backup_root = tmp_path / "backups"
    paths = resolve_paths(platform="linux", env={"HOME": str(tmp_path)})
    entry = gremlin_stdio_entry(paths)

    receipt = install_json_mcp(
        client_id="test-client",
        config_path=config,
        entry=entry,
        backup_root=backup_root,
    )
    assert receipt.status == "INSTALLED"
    assert receipt.backup_path is not None
    installed = json.loads(config.read_text(encoding="utf-8"))
    assert installed["theme"] == "dark"
    assert installed["mcpServers"]["existing"] == original["mcpServers"]["existing"]
    assert installed["mcpServers"]["gremlin"] == entry
    assert inspect_json_mcp(config)["gremlin_present"] is True


def test_generic_json_mcp_remove_preserves_other_configuration(tmp_path) -> None:
    config = tmp_path / "client.json"
    config.write_text(
        json.dumps(
            {
                "setting": 7,
                "mcpServers": {
                    "gremlin": {"command": "gremlin-product-mcp"},
                    "other": {"command": "other"},
                },
            }
        ),
        encoding="utf-8",
    )
    receipt = remove_json_mcp(
        client_id="test-client",
        config_path=config,
        backup_root=tmp_path / "backups",
    )
    assert receipt.status == "REMOVED"
    installed = json.loads(config.read_text(encoding="utf-8"))
    assert installed["setting"] == 7
    assert "gremlin" not in installed["mcpServers"]
    assert installed["mcpServers"]["other"]["command"] == "other"


def test_integration_client_id_cannot_escape_backup_root(tmp_path) -> None:
    config = tmp_path / "client.json"
    config.write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="safe identifier"):
        install_json_mcp(
            client_id="../../outside",
            config_path=config,
            entry={"command": "gremlin-product-mcp"},
            backup_root=tmp_path / "backups",
        )
    assert not (tmp_path / "outside").exists()


def test_windows_stdio_entry_uses_windows_separators_even_when_tested_on_linux() -> None:
    paths = resolve_paths(
        platform="windows",
        env={
            "USERPROFILE": r"C:\Users\Alice",
            "APPDATA": r"C:\Users\Alice\AppData\Roaming",
            "LOCALAPPDATA": r"C:\Users\Alice\AppData\Local",
        },
    )
    entry = gremlin_stdio_entry(paths)
    assert entry["command"] == r"C:\Users\Alice\AppData\Local\Programs\GREMLIN\gremlin-product-mcp.exe"
    assert entry["env"]["GREMLIN_LICENSE_PUBLIC_KEY"] == r"C:\Users\Alice\AppData\Local\Programs\GREMLIN\resources\issuer-public.pem"
