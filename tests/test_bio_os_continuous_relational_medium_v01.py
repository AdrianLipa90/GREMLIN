from __future__ import annotations

import json
from pathlib import Path

import pytest

from gremlin_mcp.bio_os_continuous_semantics import (
    BioOSLocalityMetrics,
    validate_contract,
    verified_delta_per_joule,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads(
    (
        ROOT
        / "spec"
        / "GREMLIN_BIO_OS_CONTINUOUS_RELATIONAL_MEDIUM_V0_1.json"
    ).read_text(encoding="utf-8")
)


def test_candidate_contract_has_no_global_semantic_tick_or_full_rescan() -> None:
    out = validate_contract(CONTRACT)
    assert out["status"] == "PASS_CONTRACT"
    assert out["global_semantic_tick_required"] is False
    assert out["full_graph_rescan_required"] is False
    assert out["physical_fluid_claim"] is False
    assert out["canon_allowed"] is False


def test_contract_fails_closed_if_global_tick_is_promoted() -> None:
    bad = json.loads(json.dumps(CONTRACT))
    bad["semantics"]["global_semantic_tick_required"] = True
    with pytest.raises(ValueError, match="global_semantic_tick_required"):
        validate_contract(bad)


def test_contract_fails_closed_on_physical_fluid_overclaim() -> None:
    bad = json.loads(json.dumps(CONTRACT))
    bad["forbidden_claims"]["physical_material_fluid_claim"] = True
    with pytest.raises(ValueError, match="physical_material_fluid_claim"):
        validate_contract(bad)


def test_locality_metrics_preserve_sparse_active_support_and_reuse() -> None:
    row = BioOSLocalityMetrics(
        total_nodes=1000,
        active_nodes=50,
        eligible_stable_relations=8000,
        recomputed_stable_relations=200,
        reused_relations=7600,
        recomputed_relations=400,
    ).receipt()
    assert row["active_fraction"] == pytest.approx(0.05)
    assert row["reuse_ratio"] == pytest.approx(0.95)
    assert row["recompute_avoidance"] == pytest.approx(0.975)


def test_energy_metric_requires_real_positive_joule_input() -> None:
    assert verified_delta_per_joule(50.0, 10.0) == pytest.approx(5.0)
    with pytest.raises(ValueError, match="measured_energy_joules"):
        verified_delta_per_joule(50.0, 0.0)
