import json
import subprocess
import sys


def test_native_holographic_hive_surfaces_in_isolated_process():
    code = r'''
import json
import math
from gremlin_mcp.server_with_hive import (
    gremlin_hive_holographic_phase_transport,
    gremlin_hive_holographic_project,
    gremlin_hive_holographic_remap,
    gremlin_hive_holographic_retrieve,
    gremlin_hive_status,
)

def cell(offset):
    return [float((offset + 0.09 * i) % (2 * math.pi)) for i in range(36)]

a = cell(0.1)
b = cell(0.6)
records = {"a": a, "b": b}
status = gremlin_hive_status()
holo = status["holographic_orbital_memory"]
projection = gremlin_hive_holographic_project([a, b])
remap = gremlin_hive_holographic_remap(records)
retrieved = gremlin_hive_holographic_retrieve(
    a, records, min_candidates=1, max_hex_ring=3, orbit_radius=8
)
carrier = [0.01 * (i - 18) for i in range(36)]
moved = gremlin_hive_holographic_phase_transport(a, carrier, gain=0.5)
restored = gremlin_hive_holographic_phase_transport(
    moved["phase_36d"], carrier, gain=-0.5
)
err = math.sqrt(
    sum(
        math.atan2(math.sin(x - y), math.cos(x - y)) ** 2
        for x, y in zip(a, restored["phase_36d"])
    ) / 36
)
print(json.dumps({
    "status": holo["status"],
    "ledger_mutation": holo["ledger_mutation"],
    "rebuildable": holo["rebuildable_from_ledger"],
    "projection_sources": projection["source_count"],
    "projection_mutation": projection["authority"]["ledger_mutation"],
    "remap_count": remap["record_count"],
    "remap_canon": remap["authority"]["canon_allowed"],
    "retrieved": retrieved["record_id"],
    "roundtrip_error": err,
    "physical_qhtri_claim": moved["physical_qhtri_claim"],
}, sort_keys=True))
'''
    proc = subprocess.run(
        [sys.executable, "-c", code],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout.strip().splitlines()[-1])
    assert result["status"] == "AVAILABLE_READ_ONLY_DERIVED"
    assert result["ledger_mutation"] is False
    assert result["rebuildable"] is True
    assert result["projection_sources"] == 2
    assert result["projection_mutation"] is False
    assert result["remap_count"] == 2
    assert result["remap_canon"] is False
    assert result["retrieved"] == "a"
    assert result["roundtrip_error"] < 1e-12
    assert result["physical_qhtri_claim"] is False
