from __future__ import annotations

import json
import math

import pytest

import gremlin_mcp.phase_memory_runtime as phase_memory

from gremlin_mcp.phase_memory_runtime import (
    PhaseMemoryError,
    PhaseMemoryRuntime,
    empty_memory_state,
    memory_bias_scores,
    memory_order,
    update_memory_state,
    validate_memory_state,
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


def test_phase_memory_rejects_unknown_state_fields() -> None:
    state = empty_memory_state()
    state["unexpected"] = True
    with pytest.raises(PhaseMemoryError, match="keys mismatch"):
        validate_memory_state(state)


def test_phase_memory_rejects_normalized_role_collisions() -> None:
    state = empty_memory_state()
    state.update(
        {
            "sequence": 1,
            "last_role": "SPIDER",
            "visit_counts": {"SPIDER": 1, "spider": 1},
            "parent_commitment": empty_memory_state()["commitment"],
        }
    )
    with pytest.raises(PhaseMemoryError, match="duplicate normalized visit role"):
        validate_memory_state(state)


def test_phase_memory_rejects_string_route_and_numeric_coercions() -> None:
    state = empty_memory_state()
    with pytest.raises(PhaseMemoryError, match="route must be a sequence"):
        update_memory_state(state, "SPIDER")  # type: ignore[arg-type]
    with pytest.raises(PhaseMemoryError, match="max_bias must be a real number"):
        memory_bias_scores({"SPIDER": 0.5}, state, max_bias=True)
    with pytest.raises(PhaseMemoryError, match="base scores must be real numbers"):
        memory_bias_scores({"SPIDER": "0.5"}, state)  # type: ignore[dict-item]


def test_phase_memory_rejects_validly_hashed_but_inconsistent_counts() -> None:
    genesis = empty_memory_state()
    core = {
        "schema": phase_memory.SCHEMA,
        "version": phase_memory.VERSION,
        "sequence": 1,
        "last_role": "SPIDER",
        "visit_counts": {"SPIDER": 2},
        "transition_counts": {},
        "parent_commitment": genesis["commitment"],
    }
    forged = {**core, "commitment": phase_memory._sha(core)}
    with pytest.raises(PhaseMemoryError, match="transition count"):
        validate_memory_state(forged)


def test_phase_memory_ledger_rejects_forged_genesis(tmp_path) -> None:
    core = {
        "schema": phase_memory.SCHEMA,
        "version": phase_memory.VERSION,
        "sequence": 1,
        "last_role": "SPIDER",
        "visit_counts": {"SPIDER": 1},
        "transition_counts": {},
        "parent_commitment": "0" * 64,
    }
    forged = {**core, "commitment": phase_memory._sha(core)}
    path = tmp_path / "forged-genesis.jsonl"
    path.write_text(json.dumps(forged, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(PhaseMemoryError, match="genesis break"):
        PhaseMemoryRuntime(ledger_path=path)


def test_phase_memory_ledger_rejects_sequence_gap(tmp_path) -> None:
    genesis = empty_memory_state()
    first = update_memory_state(genesis, ("SPIDER",))
    core = {
        "schema": phase_memory.SCHEMA,
        "version": phase_memory.VERSION,
        "sequence": 3,
        "last_role": "SPIDER",
        "visit_counts": {"SPIDER": 3},
        "transition_counts": {"SPIDER->SPIDER": 2},
        "parent_commitment": first["commitment"],
    }
    gap = {**core, "commitment": phase_memory._sha(core)}
    path = tmp_path / "sequence-gap.jsonl"
    path.write_text(
        "\n".join(
            (
                json.dumps(first, sort_keys=True),
                json.dumps(gap, sort_keys=True),
            )
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(PhaseMemoryError, match="sequence break"):
        PhaseMemoryRuntime(ledger_path=path)
