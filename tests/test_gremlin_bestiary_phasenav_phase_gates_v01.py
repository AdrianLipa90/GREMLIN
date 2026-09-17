import math
import pytest

from tools import gremlin_bestiary_phasenav_phase_gates_v01 as g


def state(offset=0.0, slope=0.01):
    return g.PhaseState36([((offset + slope * i) % g.TAU) for i in range(g.DIM)])


def shifted(s, delta, axes=None):
    theta = list(s.theta)
    if axes is None:
        axes = range(g.DIM)
    for i in axes:
        theta[i] = (theta[i] + delta) % g.TAU
    return g.PhaseState36(theta)


def test_manifest_covers_all_species_and_declares_no_physical_analog_claim():
    manifest = g.species_manifest()
    assert {x["name"] for x in manifest["species"]} == set(g.SPECIES)
    assert manifest["dimension"] == 36 and manifest["space"] == "T^36"
    assert manifest["semantic_axis_assignment"] is False
    assert manifest["fully_analog_physical_claim"] is False
    assert all(g.REALIZATION_MODE[n] in {"HYBRID","ANALOG_CORE_HYBRID_CONTROL","HYBRID_AUTHORITY_BOUNDARY"} for n in g.SPECIES)


def test_exact_36d_and_bounds_fail_closed():
    with pytest.raises(g.PhaseGateError):
        g.PhaseState36([0.0] * 35)
    with pytest.raises(g.PhaseGateError):
        g.PhaseState36([0.0] * 35 + [g.TAU])


def test_phase_gate_scalar_batch_equivalence_and_bounds():
    gate = g.PhaseGate36("MOLE")
    inputs = [state(0.1), state(0.2), state(0.3)]
    scalar = tuple(gate.step(x) for x in inputs)
    batch = gate.step_batch(inputs)
    assert [s.theta for s in scalar] == [s.theta for s in batch]
    assert all(0.0 <= x < g.TAU for s in batch for x in s.theta)


def test_hummingbird_capture_is_lossless_and_non_mutating():
    s = state(0.4)
    out = g.hummingbird_capture(s)
    assert out["data"]["state_id"] == s.state_id
    assert tuple(out["data"]["theta"]) == s.theta
    assert out["external_effects"] is False


def test_octopus_route_is_bounded_and_deterministic():
    s = g.PhaseState36(g._carrier36("SPIDER"))
    candidates = ["SPIDER","RAVEN","HOUND","MOLE","OWL","ANT","MANTIS","FOX","BAT","SERPENT"]
    a = g.octopus_route(s, candidates, max_species=3, min_score=0.0)
    b = g.octopus_route(s, candidates, max_species=3, min_score=0.0)
    assert a == b and len(a["data"]["routes"]) == 3
    assert a["data"]["routes"][0]["species"] == "SPIDER"


def test_spider_detects_near_relation():
    a = state(0.1); b = shifted(a, 0.01); c = state(2.4, 0.17)
    out = g.spider_scan([a,b,c], threshold=0.95)
    assert any(e["left"] == 0 and e["right"] == 1 for e in out["data"]["edges"])


def test_raven_returns_exact_memory_first():
    q = state(0.3)
    out = g.raven_recall(q, [state(1.0), q, state(2.0)], k=2)
    assert out["data"]["matches"][0]["index"] == 1
    assert out["data"]["matches"][0]["score"] == pytest.approx(1.0)


def test_hound_residual_increases_with_anomaly():
    base = state(0.0)
    near = shifted(base, 0.01, [0])
    far = shifted(base, 1.0, [0,1,2,3])
    assert g.hound_scan(far,base)["data"]["rms_residual"] > g.hound_scan(near,base)["data"]["rms_residual"]


def test_mole_relaxation_reduces_target_distance():
    out = g.mole_relax(state(0.1), state(1.2), steps=40)
    assert out["data"]["after_distance"] < out["data"]["before_distance"]


def test_owl_support_is_higher_for_aligned_evidence():
    claim = state(0.2)
    aligned = [shifted(claim,0.01), shifted(claim,-0.01)]
    remote = [state(2.8,0.23), state(4.2,0.31)]
    assert g.owl_audit(claim,aligned)["data"]["mean_support"] > g.owl_audit(claim,remote)["data"]["mean_support"]


def test_ant_enumeration_is_bounded_and_unique():
    ids = g.ant_enumerate(state(), axes=(0,1), delta=0.2, budget=5)["data"]["variant_ids"]
    assert len(ids) == 5 and len(set(ids)) == 5


def test_mantis_prunes_phase_duplicates():
    a = state(0.1); b = g.PhaseState36(a.theta); c = shifted(a,0.3,[0])
    out = g.mantis_prune([a,b,c], epsilon=1e-12)
    assert len(out["data"]["kept_state_ids"]) == 2
    assert len(out["data"]["dropped"]) == 1


def test_fox_geodesic_plan_is_monotone():
    out = g.fox_plan(state(0.1), state(1.0), steps=8)
    assert out["data"]["monotone"] is True
    assert out["data"]["goal_distances"][-1] == pytest.approx(0.0, abs=1e-12)


def test_beaver_constructs_between_close_parts():
    a = state(0.0); b = shifted(a,0.2)
    out = g.beaver_construct([a,b]); c = g.PhaseState36(out["data"]["theta"])
    assert g.torus_distance(c.theta,a.theta) < g.torus_distance(a.theta,b.theta)
    assert g.torus_distance(c.theta,b.theta) < g.torus_distance(a.theta,b.theta)


def test_bat_finds_injected_harmonic():
    n = 32; harmonic = 4; history = []
    for t in range(n):
        phi = 1.0 + 0.35 * math.sin(2.0 * math.pi * harmonic * t / n)
        history.append(g.PhaseState36([phi] * g.DIM))
    out = g.bat_scan(history)
    assert out["data"]["dominant_harmonic"] == harmonic
    assert out["data"]["power_fraction"] > 0.9


def test_canary_flags_sudden_phase_drift():
    base = state(0.1)
    history = [base, shifted(base,0.01), shifted(base,0.02), shifted(base,0.8), shifted(base,1.5)]
    assert g.canary_watch(history,slack=0.005,threshold=0.4)["data"]["verdict"] == "BLOCK_CANDIDATE"


def test_serpent_temperature_and_novelty_respond_to_change():
    base = state(0.1); small = shifted(base,0.01); hot = shifted(small,0.8)
    cold = g.serpent_sense([base,small],reference=[base])
    warm = g.serpent_sense([small,hot],reference=[base])
    assert warm["data"]["temperature"] > cold["data"]["temperature"]
    assert warm["data"]["novelty"] > cold["data"]["novelty"]
    assert len(warm["data"]["taste_signature"]) == 6


def test_chameleon_roundtrip_and_no_crypto_claim():
    s = state(0.7,0.09)
    restored = g.chameleon_unskin(g.chameleon_skin(s,"test-profile"),"test-profile")
    assert g.torus_distance(s.theta,restored.theta) < 1e-12
    receipt = g.chameleon_transform(s,"test-profile")
    assert receipt["data"]["cryptographic_claim"] is False
    assert receipt["operation"] == "REVERSIBLE_PHASE_SKIN_NOT_CRYPTOGRAPHY"


def test_belzebub_robust_synthesis_reduces_outlier_pull():
    a = state(0.1); b = shifted(a,0.02); c = shifted(a,-0.02); outlier = state(3.0,0.27)
    out = g.belzebub_synthesize([a,b,c,outlier]); candidate = g.PhaseState36(out["data"]["theta"])
    assert g.torus_distance(candidate.theta,a.theta) < g.torus_distance(outlier.theta,a.theta)
    assert len(out["data"]["kept_state_ids"]) == 3


def test_gremlin_aggregate_returns_candidate_not_canon():
    out = g.gremlin_aggregate([state(0.1),state(0.11)])
    assert out["canon_allowed"] is False and out["external_effects"] is False
    assert out["data"]["mean_disagreement"] >= 0.0


def test_ferret_is_fail_closed_and_never_executes_external_action_here():
    blocked = g.ferret_authorize(explicit_authorization=False,scope_match=True,receipt_valid=True,action_commitment="abc")
    admitted = g.ferret_authorize(explicit_authorization=True,scope_match=True,receipt_valid=True,action_commitment="abc")
    assert blocked["data"]["verdict"] == "BLOCK"
    assert admitted["data"]["verdict"] == "ADMITTED"
    assert admitted["data"]["external_action_executed"] is False


def test_receipts_are_deterministic():
    s = state(0.2)
    assert g.hummingbird_capture(s) == g.hummingbird_capture(s)
    assert g.species_manifest() == g.species_manifest()
