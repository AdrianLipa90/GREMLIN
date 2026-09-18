import math

import pytest

from tools import gremlin_bestiary_phasenav_phase_gates_v01 as base
from tools import gremlin_bestiary_phasenav_threeway_v01 as tri


def tiny_batch():
    return tri.frozen_workload(8)


def test_realization_classes_partition_exact_bestiary():
    assert tri.ANALOG_CORE_SPECIES | tri.HYBRID_SPECIES | tri.AUTHORITY_BOUNDARY_SPECIES == set(base.SPECIES)
    assert not (tri.ANALOG_CORE_SPECIES & tri.HYBRID_SPECIES)
    assert not (tri.ANALOG_CORE_SPECIES & tri.AUTHORITY_BOUNDARY_SPECIES)
    assert not (tri.HYBRID_SPECIES & tri.AUTHORITY_BOUNDARY_SPECIES)


def test_phase_field_matches_one_forward_euler_step():
    states = tiny_batch()
    gate = base.PhaseGate36("SERPENT", dt=1e-5)
    matrix = tri._matrix(states)
    field = tri.phase_field(gate, matrix)
    predicted = (matrix + gate.dt * field) % base.TAU
    stepped = tri.scalar_euler_batch(gate, states, horizon=gate.dt, steps=1)
    actual = tri._matrix(stepped)
    delta = (actual - predicted + math.pi) % base.TAU - math.pi
    assert abs(delta).max() < 1e-12


@pytest.mark.parametrize("species", base.SPECIES)
def test_scalar_and_vector_trajectories_match_all_species(species):
    states = tiny_batch()
    gate = base.PhaseGate36(species)
    scalar = tri.scalar_euler_batch(gate, states, horizon=0.4, steps=16)
    vector = tri.vector_euler_batch(gate, states, horizon=0.4, steps=16)
    assert tri.max_coordinate_error(scalar, vector) <= 1e-12


@pytest.mark.parametrize("species", sorted(tri.ANALOG_CORE_SPECIES))
def test_analog_core_species_converge_to_continuous_phase_field(species):
    result = tri.evaluate_species(
        species,
        tiny_batch(),
        horizon=0.8,
        coarse_steps=8,
        fine_steps=64,
        rk4_substeps=256,
    )
    assert result["gates"]["scalar_vector_equivalent"] is True
    assert result["gates"]["continuous_error_within_tolerance"] is True
    assert result["gates"]["euler_converges_toward_continuous"] is True
    assert result["classification"] == "ANALOG_CORE_NUMERICAL_PASS_HYBRID_CONTROL"
    assert result["physical_analog_claim"] is False


@pytest.mark.parametrize("species", sorted(tri.HYBRID_SPECIES))
def test_hybrid_species_remain_hybrid_even_when_phase_subkernel_converges(species):
    result = tri.evaluate_species(
        species,
        tiny_batch(),
        horizon=0.8,
        coarse_steps=8,
        fine_steps=64,
        rk4_substeps=256,
    )
    assert result["classification"] == "HYBRID_PASS"
    assert result["hardware_analog_witness"] is False


def test_ferret_remains_authority_boundary():
    result = tri.evaluate_species(
        "FERRET",
        tiny_batch(),
        horizon=0.8,
        coarse_steps=8,
        fine_steps=64,
        rk4_substeps=256,
    )
    assert result["classification"] == "HYBRID_AUTHORITY_BOUNDARY_PASS"
    assert result["external_effects"] is False
    assert result["canon_allowed"] is False


def test_full_threeway_suite_passes_without_physical_analog_claim():
    suite = tri.run_threeway_suite(
        batch_size=12,
        horizon=0.8,
        coarse_steps=8,
        fine_steps=64,
        rk4_substeps=256,
    )
    s = suite["summary"]
    assert s["species_count"] == len(base.SPECIES)
    assert s["all_species_pass"] is True
    assert s["failures"] == []
    assert s["analog_core_numerical_pass_count"] == len(tri.ANALOG_CORE_SPECIES)
    assert s["hybrid_pass_count"] == len(tri.HYBRID_SPECIES) + len(tri.AUTHORITY_BOUNDARY_SPECIES)
    assert s["fully_analog_physical_pass_count"] == 0
    assert s["physical_analog_claim"] is False
    assert s["hardware_analog_witness"] is False


def test_invalid_trajectory_inputs_fail_closed():
    gate = base.PhaseGate36("BAT")
    with pytest.raises(base.PhaseGateError):
        tri.rk4_continuous_batch(gate, [], horizon=1.0, substeps=32)
    with pytest.raises(base.PhaseGateError):
        tri.scalar_euler_batch(gate, tiny_batch(), horizon=0.0, steps=8)
    with pytest.raises(base.PhaseGateError):
        tri.vector_euler_batch(gate, tiny_batch(), horizon=1.0, steps=0)
