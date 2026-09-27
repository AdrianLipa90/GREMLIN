import numpy as np

from gremlin_mcp.residual_spectroscopy import analyze_residual_stack


def base(seed=1, runs=8, n=2048):
    rng = np.random.default_rng(seed)
    model = np.zeros((runs, n))
    return rng, model


def test_white_noise_remains_compatible_with_stochastic_background():
    rng, model = base()
    raw = rng.normal(size=model.shape)
    out = analyze_residual_stack(raw, model)
    assert out["classification"] == "STOCHASTIC_BACKGROUND_COMPATIBLE"
    assert out["policy"]["residual_preserved"] is True


def test_persistent_weak_line_is_not_discarded_as_noise():
    rng, model = base(2)
    n = model.shape[1]
    t = np.arange(n)
    runs = [
        0.8 * np.sin(2 * np.pi * 73 * t / n + 0.06 * i)
        + rng.normal(scale=0.9, size=n)
        for i in range(model.shape[0])
    ]
    out = analyze_residual_stack(np.array(runs), model)
    assert out["classification"] == "UNRESOLVED_STRUCTURED_CANDIDATE"
    assert abs(out["metrics"]["consensus_peak_bin"] - 73) <= 1
    assert out["metrics"]["cross_run_peak_persistence"] >= 0.75


def test_nuisance_coupled_structure_is_typed_instrumental_candidate():
    rng, model = base(3)
    n = model.shape[1]
    t = np.arange(n)
    nuis, raw = [], []
    for i in range(model.shape[0]):
        q = np.sin(2 * np.pi * 31 * t / n + 0.02 * i)
        nuis.append(q)
        raw.append(0.9 * q + rng.normal(scale=0.25, size=n))
    out = analyze_residual_stack(np.array(raw), model, nuisance_runs=np.array(nuis))
    assert out["classification"] == "SYSTEMATIC_OR_INSTRUMENTAL_CANDIDATE"
    assert out["metrics"]["median_abs_nuisance_correlation"] > 0.7


def test_linear_drift_is_not_promoted_to_new_physics():
    rng, model = base(4)
    n = model.shape[1]
    t = np.linspace(-1, 1, n)
    raw = np.array([2.0 * t + rng.normal(scale=0.15, size=n) for _ in range(model.shape[0])])
    out = analyze_residual_stack(raw, model)
    assert out["classification"] == "SYSTEMATIC_DRIFT_CANDIDATE"
    assert out["policy"]["time_fluctuation_claim_allowed"] is False


def test_known_template_wins_over_unresolved_label():
    rng, model = base(5)
    n = model.shape[1]
    t = np.arange(n)
    known, raw = [], []
    for _ in range(model.shape[0]):
        q = np.cos(2 * np.pi * 41 * t / n)
        known.append(q)
        raw.append(0.7 * q + rng.normal(scale=0.2, size=n))
    out = analyze_residual_stack(np.array(raw), model, known_template_runs=np.array(known))
    assert out["classification"] == "KNOWN_MODEL_STRUCTURE_CANDIDATE"


def test_commitments_change_if_residual_changes():
    rng, model = base(6)
    raw = rng.normal(size=model.shape)
    a = analyze_residual_stack(raw, model)
    raw2 = raw.copy()
    raw2[0, 0] += 1e-6
    b = analyze_residual_stack(raw2, model)
    assert a["commitments"]["raw_sha256"] != b["commitments"]["raw_sha256"]
    assert a["commitments"]["residual_sha256"] != b["commitments"]["residual_sha256"]
