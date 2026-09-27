from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_gremlind():
    root = Path(__file__).resolve().parents[1]
    path = root / "runtime" / "noema" / "gremlind.py"
    spec = importlib.util.spec_from_file_location("gremlind_source_controlled", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reflexive_provenance_temporal_inversion_routes_history_and_adversarial_audit() -> None:
    gremlind = _load_gremlind()
    vector = (
        "Audit provenance inconsistency: V0_2 supersedes V0_1; "
        "V0_1 was retroactively rewritten after supersession, "
        "creating temporal inversion in lineage"
    )
    route = gremlind._route_roles(vector, source_count=1)
    assert route[0] == "OWL"
    assert {"OWL", "HOUND", "RAVEN"} <= set(route)


def test_plain_provenance_audit_does_not_force_history_or_adversarial_roles() -> None:
    gremlind = _load_gremlind()
    route = gremlind._route_roles("Audit provenance for this source", source_count=1)
    assert route == ["OWL"]
