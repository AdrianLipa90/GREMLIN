from tools import gremlin_bestiary_phasenav_analog_invariants_v01 as inv
from tools import gremlin_bestiary_phasenav_threeway_v01 as tri


def test_invariant_suite_covers_exact_analog_core_species():
    assert frozenset(inv.CHECKS) == tri.ANALOG_CORE_SPECIES


def test_each_analog_core_specialist_invariant_passes():
    suite = inv.run_analog_invariant_suite()
    assert suite["species_count"] == len(tri.ANALOG_CORE_SPECIES)
    assert suite["summary"]["all_analog_core_specialist_invariants_pass"] is True
    assert suite["summary"]["passed"] == len(tri.ANALOG_CORE_SPECIES)
    assert suite["summary"]["failed"] == 0
    assert suite["summary"]["failed_species"] == []
    assert suite["summary"]["fully_analog_specialist_semantics_claim"] is False
    assert suite["summary"]["physical_analog_claim"] is False
    assert suite["summary"]["hardware_analog_witness"] is False
    assert suite["summary"]["external_effects"] is False
    assert suite["summary"]["canon_allowed"] is False


def test_serpent_invariant_retains_temperature_and_novelty_ordering():
    out = inv.serpent_invariant()
    assert out["pass"] is True
    assert out["warm_temperature"] > out["cold_temperature"]
    assert out["warm_novelty"] > out["cold_novelty"]


def test_bat_invariant_retains_injected_harmonic():
    out = inv.bat_invariant()
    assert out["pass"] is True
    assert out["observed_harmonic"] == out["injected_harmonic"]
    assert out["power_fraction"] > 0.80


def test_canary_invariant_retains_blocking_drift():
    out = inv.canary_invariant()
    assert out["pass"] is True
    assert out["verdict"] == "BLOCK_CANDIDATE"
