from __future__ import annotations

import math

from gremlin_mcp.phase_memory_runtime import (
    PhaseMemoryRuntime,
    empty_memory_state,
    memory_order,
    update_memory_state,
)
from gremlin_mcp.role_registry import BESTIARY_ROLE_NAMES
from tools.gremlin_bestiary_phasenav_live_binding_v02 import SPECIES_OPERATOR_BINDINGS
from tools.gremlin_bestiary_phasenav_phase_gates_v02 import (
    DUAL_PAIRS,
    SPECIES,
    binding_manifest,
    orthoplex_vector,
    phase_difference_law_residual,
    role_phase_carrier,
    run_full_bestiary_reference_sweep,
)
from tools.gremlin_geometry_phase_scheduler_v02 import scheduler_manifest


def _dot(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    return sum(a * b for a, b in zip(left, right))


def test_full_20_role_phase_surface_is_exact_registry() -> None:
    assert len(SPECIES) == 20
    assert set(SPECIES) == set(BESTIARY_ROLE_NAMES)
    assert len(DUAL_PAIRS) == 10
    assert set(SPECIES_OPERATOR_BINDINGS) == set(SPECIES)


def test_candidate_role_geometry_is_exact_10_orthoplex() -> None:
    vectors = {name: orthoplex_vector(name) for name in SPECIES}
    assert all(len(v) == 10 for v in vectors.values())
    assert all(_dot(v, v) == 1 for v in vectors.values())

    dual = {}
    for left, right in DUAL_PAIRS:
        dual[left] = right
        dual[right] = left
        assert vectors[right] == tuple(-x for x in vectors[left])

    for left in SPECIES:
        for right in SPECIES:
            expected = 1 if left == right else (-1 if dual[left] == right else 0)
            assert _dot(vectors[left], vectors[right]) == expected


def test_arpl_phase_difference_law_closes_all_role_pairs() -> None:
    residuals = [
        phase_difference_law_residual(left, right)
        for left in SPECIES
        for right in SPECIES
    ]
    assert max(residuals) <= 1e-12


def test_all_20_phase_carriers_are_unique_and_finite() -> None:
    carriers = {name: role_phase_carrier(name) for name in SPECIES}
    assert len({tuple(v) for v in carriers.values()}) == 20
    assert all(len(v) == 36 for v in carriers.values())
    assert all(
        math.isfinite(x) and 0.0 <= x < 2.0 * math.pi
        for vector in carriers.values()
        for x in vector
    )


def test_reference_sweep_arms_all_20_roles() -> None:
    sweep = run_full_bestiary_reference_sweep()
    assert sweep["status"] == "PASS"
    assert sweep["species_count"] == 20
    assert sweep["all_species_distance_reduced"] is True
    assert sweep["all_species_carriers_unique"] is True
    assert sweep["orthoplex_duals_exact"] is True
    assert sweep["max_arpl_phase_law_residual"] <= 1e-12


def test_elephant_and_bees_are_no_longer_anchor_neutral() -> None:
    manifest = scheduler_manifest()
    assert "ELEPHANT" in manifest["validated_phasenav_carrier_species"]
    assert "BEES" in manifest["validated_phasenav_carrier_species"]
    assert manifest["anchor_neutral_dynamic_species"] == []


def test_memory_law_history_changes_future_route_order() -> None:
    elephant_history = empty_memory_state()
    mole_history = empty_memory_state()
    for _ in range(4):
        elephant_history = update_memory_state(
            elephant_history,
            ("SPIDER", "ELEPHANT"),
        )
        mole_history = update_memory_state(
            mole_history,
            ("SPIDER", "MOLE"),
        )

    assert elephant_history["commitment"] != mole_history["commitment"]

    species = ("ELEPHANT", "MOLE")
    base = {"ELEPHANT": 0.5, "MOLE": 0.5}

    order_elephant, scores_elephant = memory_order(
        species,
        base,
        elephant_history,
        source_roles=("SPIDER",),
    )
    order_mole, scores_mole = memory_order(
        species,
        base,
        mole_history,
        source_roles=("SPIDER",),
    )

    assert order_elephant[0] == "ELEPHANT"
    assert order_mole[0] == "MOLE"
    assert scores_elephant["ELEPHANT"] > scores_elephant["MOLE"]
    assert scores_mole["MOLE"] > scores_mole["ELEPHANT"]


def test_memory_ledger_is_append_only_and_restart_recoverable(tmp_path) -> None:
    path = tmp_path / "gremlin.phase-memory.jsonl"
    first = PhaseMemoryRuntime(ledger_path=path)
    s1 = first.observe(("SPIDER", "ELEPHANT"))
    s2 = first.observe(("RAVEN", "BEES"))

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert s2["parent_commitment"] == s1["commitment"]

    recovered = PhaseMemoryRuntime(ledger_path=path)
    assert recovered.snapshot()["commitment"] == s2["commitment"]
    assert recovered.snapshot()["sequence"] == 2


def test_binding_manifest_preserves_candidate_firewall() -> None:
    manifest = binding_manifest()
    assert manifest["species_count"] == 20
    assert manifest["role_geometry"] == "CANDIDATE_10_ORTHOPLEX"
    assert manifest["semantic_axis_assignment"] is False
    assert manifest["physical_analog_claim"] is False
    assert manifest["canon_allowed"] is False
