import math

import pytest

from tools import gremlin_bestiary_phasenav_phase_gates_v01 as base
from tools import gremlin_bestiary_phasenav_numpy_v01 as vec


def state(offset: float = 0.0, slope: float = 0.01) -> base.PhaseState36:
    return base.PhaseState36(
        [((offset + slope * i) % base.TAU) for i in range(base.DIM)]
    )


def batch(n: int) -> tuple[base.PhaseState36, ...]:
    return tuple(state(0.03 * j, 0.01 + 0.0001 * j) for j in range(n))


def test_backend_manifest_covers_exact_species_and_fails_no_fallback():
    manifest = vec.backend_manifest()
    assert manifest["dimension"] == 36
    assert manifest["space"] == "T^36"
    assert set(manifest["species"]) == set(base.SPECIES)
    assert manifest["silent_scalar_fallback"] is False
    assert manifest["physical_analog_claim"] is False
    assert manifest["external_effects"] is False


@pytest.mark.parametrize("species", base.SPECIES)
def test_all_species_scalar_vector_equivalence(species):
    states = batch(17)
    result = vec.scalar_vector_equivalence(species, states)
    assert result["species"] == species
    assert result["batch_size"] == len(states)
    assert result["max_torus_error"] < 1e-12
    assert result["silent_scalar_fallback"] is False


@pytest.mark.parametrize("species", base.SPECIES)
def test_all_species_phase_kernel_continuity_probe(species):
    result = vec.analog_kernel_continuity_probe(species, state(0.7, 0.019))
    assert result["finite"] is True
    assert result["phase_kernel_continuity_candidate"] is True
    assert result["input_distance"] > 0.0
    assert result["output_distance"] >= 0.0
    assert math.isfinite(result["local_gain"])
    assert result["physical_analog_claim"] is False


def test_vector_batch_preserves_shape_bounds_and_order():
    states = batch(31)
    gate = base.PhaseGate36("SERPENT")
    out = vec.step_batch_vectorized(gate, states)
    assert len(out) == len(states)
    assert all(len(s.theta) == 36 for s in out)
    assert all(0.0 <= x < base.TAU for s in out for x in s.theta)

    scalar = tuple(gate.step(s) for s in states)
    assert vec.max_torus_error(scalar, out) < 1e-12


def test_vector_batch_target_override_matches_scalar():
    states = batch(9)
    target = state(1.1, 0.007)
    gate = base.PhaseGate36("MOLE")
    vector = vec.step_batch_vectorized(gate, states, target=target.theta)
    scalar = tuple(gate.step(s, target=target.theta) for s in states)
    assert vec.max_torus_error(scalar, vector) < 1e-12


def test_invalid_empty_batch_fails_closed():
    gate = base.PhaseGate36("BAT")
    with pytest.raises(base.PhaseGateError):
        vec.step_batch_vectorized(gate, [])


def test_benchmark_reports_measurement_without_speed_claim_gate():
    result = vec.benchmark_scalar_vs_vector("SPIDER", batch(64), repeats=3)
    assert result["batch_size"] == 64
    assert result["repeats"] == 3
    assert result["scalar_median_s"] > 0.0
    assert result["vector_median_s"] > 0.0
    assert result["speedup"] > 0.0
    assert result["max_torus_error"] < 1e-12
    assert result["physical_analog_claim"] is False


def test_continuity_probe_rejects_invalid_epsilon():
    with pytest.raises(base.PhaseGateError):
        vec.analog_kernel_continuity_probe("SERPENT", state(), epsilon=0.0)
    with pytest.raises(base.PhaseGateError):
        vec.analog_kernel_continuity_probe("SERPENT", state(), epsilon=1.0)
