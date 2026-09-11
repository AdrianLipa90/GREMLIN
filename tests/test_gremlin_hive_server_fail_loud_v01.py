from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HIVE_SERVER = ROOT / "gremlin_mcp" / "hive_server.py"


def test_hive_server_uses_single_authority_runtime_for_durable_mutations() -> None:
    source = HIVE_SERVER.read_text(encoding="utf-8")
    assert "from gremlin_mcp.hive_authority import HiveAuthorityRuntime" in source
    assert "runtime = HiveAuthorityRuntime(" in source
    assert "SQLiteHiveStore" not in source
    assert "OrbitalHiveMemory" not in source
    assert "def _persist(" not in source


def test_hive_server_mutations_delegate_to_authority_runtime() -> None:
    source = HIVE_SERVER.read_text(encoding="utf-8")
    for operation in ("place", "update_gates", "dispute", "latch"):
        assert f"runtime.{operation}(" in source
