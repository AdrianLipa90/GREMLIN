from pathlib import Path

from gremlin_mcp.install.launcher import _mode
from gremlin_mcp.server import standalone_phasenav_self_test
from tools.build_gremlin_standalone_v01 import _nuitka_command


def test_launcher_resolves_all_three_standalone_aliases():
    assert _mode("gremlinctl", ["doctor"]) == ("ctl", ["doctor"])
    assert _mode("gremlin-product-mcp", ["--help"]) == ("product-mcp", ["--help"])
    assert _mode("gremlin-mcp", ["--help"]) == ("mcp", ["--help"])
    assert _mode("gremlin-mcp.exe", ["--help"]) == ("mcp", ["--help"])


def test_nuitka_command_contains_full_gremlin_phasenav_runtime_graph(tmp_path):
    entry = tmp_path / "entry.py"
    entry.write_text("pass\n", encoding="utf-8")
    cmd = _nuitka_command(entry=entry, work=tmp_path, exe_name="gremlin-runtime")
    required = {
        "--include-module=gremlin_mcp.server_with_hive",
        "--include-module=gremlin_mcp.phasenav_runtime",
        "--include-module=tools.gremlin_bestiary_phasenav_phase_gates_v01",
        "--include-module=tools.gremlin_bestiary_phasenav_numpy_v01",
        "--include-module=tools.gremlin_bestiary_phasenav_threeway_v01",
        "--include-module=tools.gremlin_bestiary_phasenav_analog_invariants_v01",
        "--include-module=tools.gremlin_bestiary_phasenav_live_binding_v01",
    }
    assert required <= set(cmd)


def test_standalone_phasenav_self_test_is_no_noema_and_fail_closed():
    out = standalone_phasenav_self_test()
    assert out["status"] == "PASS"
    assert out["species_count"] == 18
    assert out["vector_backend_available"] is True
    assert out["threeway_all_species_pass"] is True
    assert out["analog_core_invariants_pass"] is True
    assert out["live_noema_required"] is False
    assert out["external_effects"] is False
    assert out["canon_allowed"] is False
    assert out["physical_analog_claim"] is False
