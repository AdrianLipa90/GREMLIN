from collections import OrderedDict

import numpy as np

from gremlin_mcp.recursive_residual_v03 import recursive_residual_decomposition


def _meta(names):
    return {
        name: {
            "frozen_before_fit": True,
            "independent_of_target_fit": True,
            "source_type": "instrument_channel",
            "source_id": f"synthetic:{name}",
            "null_policy": "sample_circular_shift",
        }
        for name in names
    }


def _case(seed=270927, n=4096):
    rng = np.random.default_rng(seed)
    runs = 16
    t = np.arange(n)

    strong = np.array([
        2.0 * np.sin(2 * np.pi * 31 * t / n + 0.03 * i)
        for i in range(runs)
    ])
    jitter = np.array([
        0.8 * np.sin(2 * np.pi * 53 * t / n + 0.11 * i)
        for i in range(runs)
    ])
    ramp = np.tile(np.linspace(-0.7, 0.7, n), (runs, 1))
    weak = np.array([
        0.10 * np.sin(2 * np.pi * 137 * t / n + 0.20 * i)
        for i in range(runs)
    ])
    noise = rng.normal(size=(runs, n))
    noise_proxy = np.random.default_rng(123).normal(size=(runs, n))

    raw = strong + jitter + ramp + weak + noise
    initial = np.zeros_like(raw)
    components = OrderedDict([
        ("strong_nuisance", strong),
        ("jitter_nuisance", jitter),
        ("ramp_nuisance", ramp),
        ("independent_noise_proxy", noise_proxy),
    ])
    return raw, initial, components


def test_recursive_decomposition_exposes_weak_structure_and_rejects_noise_proxy():
    raw, initial, components = _case()
    result, model, residual = recursive_residual_decomposition(
        raw, initial, components, _meta(components)
    )

    assert result["accepted_layers"] == [
        "strong_nuisance",
        "jitter_nuisance",
        "ramp_nuisance",
    ]
    assert "independent_noise_proxy" in result["rejected_candidates"]
    assert result["rejected_candidates"]["independent_noise_proxy"]["decision"] != "PASS"

    packet = result["final_packet"]
    assert packet["classification"] == "UNRESOLVED_STRUCTURED_CANDIDATE"
    assert packet["metrics"]["consensus_peak_bin"] == 137
    assert packet["metrics"]["stacked_peak_to_median_ratio"] > 12.0
    assert packet["metrics"]["individual_run_support_fraction"] == 1.0

    assert result["raw_sha256"] == result["stages"][0]["commitments"]["raw_sha256"]
    assert all(
        stage["commitments"]["raw_sha256"] == result["raw_sha256"]
        for stage in result["stages"]
    )
    assert np.allclose(raw - model, residual)


def test_candidate_mapping_order_is_not_authoritative():
    raw, initial, components = _case()
    meta = _meta(components)
    a, _, _ = recursive_residual_decomposition(raw, initial, components, meta)

    reversed_components = OrderedDict(reversed(list(components.items())))
    b, _, _ = recursive_residual_decomposition(
        raw, initial, reversed_components, _meta(reversed_components)
    )

    assert a["accepted_layers"] == b["accepted_layers"]
    assert (
        a["final_packet"]["commitments"]["residual_sha256"]
        == b["final_packet"]["commitments"]["residual_sha256"]
    )
    assert a["input_mapping_order_authoritative"] is False


def test_duplicate_nuisance_is_marked_as_attribution_alias_not_second_mechanism():
    rng = np.random.default_rng(11)
    runs, n = 12, 2048
    t = np.arange(n)
    signal = np.array([
        np.sin(2 * np.pi * 29 * t / n + 0.04 * i)
        for i in range(runs)
    ])
    raw = 1.4 * signal + rng.normal(scale=0.5, size=(runs, n))
    components = OrderedDict([
        ("a_sensor", signal),
        ("b_duplicate_sensor", signal.copy()),
    ])
    result, _, _ = recursive_residual_decomposition(
        raw, np.zeros_like(raw), components, _meta(components)
    )

    assert result["accepted_layers"] == ["a_sensor"]
    assert result["status"] == "PASS_WITH_ATTRIBUTION_ALIAS_OPEN"
    assert result["attribution_ambiguous"] is True
    assert len(result["alias_pairs"]) == 1
    assert result["alias_pairs"][0]["abs_correlation"] > 0.999999


def test_target_derived_nuisance_is_rejected_before_fit():
    raw, initial, components = _case(n=1024)
    meta = _meta(components)
    meta["strong_nuisance"]["independent_of_target_fit"] = False
    try:
        recursive_residual_decomposition(raw, initial, components, meta)
    except ValueError as exc:
        assert "target-derived" in str(exc)
    else:
        raise AssertionError("target-derived nuisance was accepted")


def test_train_only_leak_fails_crossfit_gate():
    rng = np.random.default_rng(42)
    runs, n = 16, 1024
    raw = rng.normal(size=(runs, n))
    leak = np.zeros_like(raw)
    leak[::2] = raw[::2]
    leak[1::2] = np.random.default_rng(43).normal(size=(runs // 2, n))
    components = {"train_only_leak": leak}

    result, _, _ = recursive_residual_decomposition(
        raw, np.zeros_like(raw), components, _meta(components)
    )

    assert result["accepted_layers"] == []
    score = result["rejected_candidates"]["train_only_leak"]
    assert score["decision"] == "NO_CONSERVATIVE_HOLDOUT_GAIN"
    assert min(score["holdout_gains"]) < 0.0


def test_pure_noise_proxy_is_not_promoted():
    rng = np.random.default_rng(99)
    raw = rng.normal(size=(16, 2048))
    proxy = np.random.default_rng(100).normal(size=raw.shape)
    components = {"independent_noise_proxy": proxy}

    result, _, _ = recursive_residual_decomposition(
        raw, np.zeros_like(raw), components, _meta(components)
    )

    assert result["accepted_layers"] == []
    assert result["status"] == "NO_NUISANCE_LAYER_ACCEPTED"


def test_stage_hash_chain_is_append_only_consistent():
    raw, initial, components = _case(n=2048)
    result, _, _ = recursive_residual_decomposition(
        raw, initial, components, _meta(components)
    )

    stages = result["stages"]
    assert stages[0]["previous_stage_sha256"] is None
    for previous, current in zip(stages, stages[1:]):
        assert current["previous_stage_sha256"] == previous["stage_sha256"]
    assert len({stage["stage_sha256"] for stage in stages}) == len(stages)
