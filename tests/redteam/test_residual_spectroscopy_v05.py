import numpy as np

from gremlin_mcp.residual_spectroscopy_v05 import analyze_residual_stack_v05


def _line(seed,phase_mode,amplitude=0.35,runs=16,n=2048):
    rng=np.random.default_rng(seed)
    t=np.arange(n)
    if phase_mode=="random":
        phases=rng.uniform(0,2*np.pi,runs)
    elif phase_mode=="linear":
        phases=0.2*np.arange(runs)
    elif phase_mode=="constant":
        phases=np.full(runs,0.4)
    else:
        raise ValueError("bad phase_mode")
    return np.array([
        rng.normal(size=n)
        +amplitude*np.sin(2*np.pi*137.5*t/n+phases[i])
        for i in range(runs)
    ])


def test_v05_random_phase_narrowband_is_power_structure_phase_unresolved():
    raw=_line(444,"random",0.35)
    out=analyze_residual_stack_v05(raw,np.zeros_like(raw))
    assert out["base_v04_classification"]=="UNRESOLVED_NARROWBAND_STRUCTURE_CANDIDATE"
    assert out["classification"]=="UNRESOLVED_NARROWBAND_POWER_CANDIDATE_PHASE_UNRESOLVED"
    gate=out["metrics"]["run_phase_relation_gate"]
    assert gate["pass"] is False
    assert gate["pass_fraction"]<0.75


def test_v05_linear_phase_law_survives_out_of_fold_phase_validation():
    raw=_line(445,"linear",0.35)
    out=analyze_residual_stack_v05(raw,np.zeros_like(raw))
    assert out["classification"]=="UNRESOLVED_RUN_PHASE_RELATIONAL_NARROWBAND_CANDIDATE"
    gate=out["metrics"]["run_phase_relation_gate"]
    assert gate["pass"] is True
    assert gate["pass_fraction"]>=0.75
    assert gate["median_holdout_coherence"]>=0.70


def test_v05_constant_phase_is_phase_relational_but_not_physical_promotion():
    raw=_line(446,"constant",0.35)
    out=analyze_residual_stack_v05(raw,np.zeros_like(raw))
    assert out["classification"]=="UNRESOLVED_RUN_PHASE_RELATIONAL_NARROWBAND_CANDIDATE"
    assert out["policy"]["phase_relation_not_physical_mechanism"] is True
    assert out["policy"]["run_index_phase_relation_not_physical_time"] is True


def test_v05_white_noise_remains_white_background():
    rng=np.random.default_rng(447)
    raw=rng.normal(size=(16,2048))
    out=analyze_residual_stack_v05(raw,np.zeros_like(raw))
    assert out["classification"]=="STOCHASTIC_WHITE_BACKGROUND_COMPATIBLE"
    assert out["metrics"]["run_phase_relation_gate"] is None


def test_v05_preserves_v04_commitments():
    raw=_line(448,"linear",0.20)
    out=analyze_residual_stack_v05(raw,np.zeros_like(raw))
    assert len(out["commitments"]["raw_sha256"])==64
    assert len(out["commitments"]["model_sha256"])==64
    assert len(out["commitments"]["residual_sha256"])==64
