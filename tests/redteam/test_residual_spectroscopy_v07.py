import numpy as np

from gremlin_mcp.residual_spectroscopy_v06 import analyze_residual_stack_v06
from gremlin_mcp.residual_spectroscopy_v07 import analyze_residual_stack_v07


def _weak_line(seed, *, runs=32, n=2048, amp=0.10, k=137.5, phi=None):
    rng=np.random.default_rng(seed)
    if phi is None:
        raw=rng.normal(size=(runs,n))
    else:
        eps=rng.normal(size=(runs,n))
        raw=np.zeros_like(eps)
        for j in range(n):
            raw[:,j]=eps[:,j] if j==0 else phi*raw[:,j-1]+eps[:,j]
    t=np.arange(n)
    for i in range(runs):
        raw[i]+=amp*np.sin(2*np.pi*k*t/n+0.2*i)
    return raw


def test_v07_recovers_seed130000_weak_line_missed_by_fixed_prominence_gate():
    raw=_weak_line(130000)
    old=analyze_residual_stack_v06(raw,np.zeros_like(raw))
    assert old["classification"]=="STOCHASTIC_WHITE_BACKGROUND_COMPATIBLE"

    out=analyze_residual_stack_v07(raw,np.zeros_like(raw))
    assert out["classification"]=="UNRESOLVED_WEAK_NARROWBAND_ACCUMULATION_CANDIDATE"
    gate=out["metrics"]["replicate_accumulation_gate"]
    assert gate["pass"] is True
    assert gate["pass_fraction"]==1.0
    assert gate["bin_agreement_fraction"]==1.0
    assert gate["individual_run_effect_size_threshold_required"] is False


def test_v07_white_noise_seed_bank_does_not_promote():
    for seed in range(20):
        raw=np.random.default_rng(200000+seed).normal(size=(16,1024))
        out=analyze_residual_stack_v07(raw,np.zeros_like(raw))
        assert out["classification"]=="STOCHASTIC_WHITE_BACKGROUND_COMPATIBLE"
        assert out["metrics"]["replicate_accumulation_gate"]["pass"] is False


def test_v07_ar1_seed_bank_does_not_promote_without_line():
    for seed in range(10):
        rng=np.random.default_rng(210000+seed)
        eps=rng.normal(size=(16,1024))
        raw=np.zeros_like(eps)
        for j in range(raw.shape[1]):
            raw[:,j]=eps[:,j] if j==0 else 0.8*raw[:,j-1]+eps[:,j]
        out=analyze_residual_stack_v07(raw,np.zeros_like(raw))
        assert out["classification"]=="STOCHASTIC_COLORED_BACKGROUND_COMPATIBLE"
        assert out["metrics"]["replicate_accumulation_gate"]["pass"] is False


def test_v07_colored_background_weak_line_can_accumulate():
    raw=_weak_line(220000,runs=16,n=2048,amp=0.35,k=137.5,phi=0.8)
    out=analyze_residual_stack_v07(raw,np.zeros_like(raw))
    assert out["classification"] in {
        "UNRESOLVED_WEAK_NARROWBAND_ACCUMULATION_CANDIDATE",
        "UNRESOLVED_NARROWBAND_PHASE_UNTYPED_CANDIDATE",
    }
    assert out["classification"]!="STOCHASTIC_COLORED_BACKGROUND_COMPATIBLE"


def test_v07_outlier_runs_do_not_create_accumulation_candidate():
    for nbad in (1,2,3):
        rng=np.random.default_rng(230000+nbad)
        raw=rng.normal(size=(16,1024))
        t=np.arange(1024)
        for i in range(nbad):
            raw[i]+=8.0*np.sin(2*np.pi*123*t/1024+i)
        out=analyze_residual_stack_v07(raw,np.zeros_like(raw))
        assert out["classification"]!="UNRESOLVED_WEAK_NARROWBAND_ACCUMULATION_CANDIDATE"


def test_v07_low_frequency_structure_still_routes_to_ambiguity_not_accumulation():
    rng=np.random.default_rng(240000)
    runs,n=16,2048
    t=np.arange(n)
    raw=np.asarray([
        rng.normal(size=n)+1.0*np.sin(2*np.pi*1.5*t/n+0.2*i)
        for i in range(runs)
    ])
    out=analyze_residual_stack_v07(raw,np.zeros_like(raw))
    assert out["classification"]=="LOW_FREQUENCY_TREND_OR_NARROWBAND_AMBIGUOUS_CANDIDATE"


def test_v07_policy_does_not_promote_physics():
    raw=_weak_line(130001)
    out=analyze_residual_stack_v07(raw,np.zeros_like(raw))
    assert out["policy"]["accumulation_candidate_is_not_physical_attribution"] is True
    assert out["policy"]["time_fluctuation_claim_allowed"] is False
