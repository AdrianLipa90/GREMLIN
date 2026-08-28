import json
from pathlib import Path

from tools.gremlin_kaku_scalar_facets_v04 import validate_live_ciel_intention_phase_anchor_v04


def test_intention_anchor_live_witness_preserves_unresolved_target_and_alignment():
    path = Path("provenance/INTENTION_PHASE_ANCHOR_LIVE_WITNESS_V0_4.json")
    witness = json.loads(path.read_text(encoding="utf-8"))
    assert witness["schema"] == "GREMLIN_INTENTION_PHASE_ANCHOR_LIVE_WITNESS_V0_4"
    assert witness["live_gremlin_producer_claim"] is False
    assert witness["target_status"] == "UNRESOLVED"
    assert witness["alignment_status"] == "UNRESOLVED"
    assert witness["authority"] == {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
    assert validate_live_ciel_intention_phase_anchor_v04(witness["phase_anchor_receipt"])
