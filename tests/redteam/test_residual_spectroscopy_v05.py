import numpy as np

from gremlin_mcp.residual_spectroscopy_v05 import analyze_residual_stack_v05


def _line(seed, *, mode, runs=16, n=2048, k=137.5, amp=0.20):
    rng=np.random.default_rng(seed)
    t=np.arange(n)
    rows=[]
    for i in range(runs):
        phase=rng.uniform(0,2*np.pi) if mode=="random" else 0.20*i
        rows.append(
            rng.normal(size=n)
            + amp*np.sin(2*np.pi*k*t/n+phase)
        )
    return np.asarray(rows)


def test_v05_random_phase_narrowband_is_phase_unordered():
    raw=_line(1,mode="random")
    out=analyze_residual_stack_v05(raw,np.zeros_like(raw),ordered_runs=True)
    assert out["legacy_v04_classification"]=="UNRESOLVED_NARROWBAND_STRUCTURE_CANDIDATE"
    assert out["classification"]=="UNRESOLVED_NARROWBAND_PHASE_UNORDERED_CANDIDATE"
    phase=out["metrics"]["phase_trajectory_audit"]
    assert phase["trajectory_ordered"] is False
    assert phase["monte_carlo_p"]>0.01


def test_v05_linear_phase_trajectory_is_ordered():
    raw=_line(2,mode="ramp")
    out=analyze_residual_stack_v05(raw,np.zeros_like(raw),ordered_runs=True)
    assert out["legacy_v04_classification"]=="UNRESOLVED_NARROWBAND_STRUCTURE_CANDIDATE"
    assert out["classification"]=="UNRESOLVED_NARROWBAND_PHASE_ORDERED_CANDIDATE"
    phase=out["metrics"]["phase_trajectory_audit"]
    assert phase["trajectory_ordered"] is True
    assert phase["phase_increment_coherence"]>phase["permutation_null_q99"]
    assert phase["monte_carlo_p"]<=0.01


def test_v05_without_run_order_refuses_phase_trajectory_claim():
    raw=_line(3,mode="ramp")
    out=analyze_residual_stack_v05(raw,np.zeros_like(raw),ordered_runs=False)
    assert out["classification"]=="UNRESOLVED_NARROWBAND_PHASE_UNTYPED_CANDIDATE"
    phase=out["metrics"]["phase_trajectory_audit"]
    assert phase["ordered_runs"] is False
    assert phase["trajectory_ordered"] is False
    assert phase["monte_carlo_p"] is None


def test_v05_white_noise_stays_white_background_compatible():
    raw=np.random.default_rng(4).normal(size=(16,2048))
    out=analyze_residual_stack_v05(raw,np.zeros_like(raw),ordered_runs=True)
    assert out["classification"]=="STOCHASTIC_WHITE_BACKGROUND_COMPATIBLE"


def test_v05_phase_taxonomy_never_promotes_physics():
    raw=_line(5,mode="ramp")
    out=analyze_residual_stack_v05(raw,np.zeros_like(raw),ordered_runs=True)
    assert out["policy"]["phase_ordering_is_diagnostic_not_physical_attribution"] is True
    assert out["policy"]["phase_ordered_does_not_mean_new_physics"] is True
    assert out["policy"]["time_fluctuation_claim_allowed"] is False
