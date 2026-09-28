import numpy as np

from gremlin_mcp.residual_spectroscopy_v07 import analyze_residual_stack_v07
from gremlin_mcp.residual_spectroscopy_v08 import analyze_residual_stack_v08


def _wandering(seed, *, runs=16, n=2048, amp=0.4, k0=120.0, dk=0.75, phi=None):
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
        k=k0+dk*i
        raw[i]+=amp*np.sin(2*np.pi*k*t/n+0.15*i)
    return raw


def test_v08_recovers_linear_frequency_wander_missed_by_v07():
    raw=_wandering(250000,amp=0.4)
    old=analyze_residual_stack_v07(raw,np.zeros_like(raw))
    assert old["classification"]!="UNRESOLVED_WEAK_NARROWBAND_ACCUMULATION_CANDIDATE"

    out=analyze_residual_stack_v08(raw,np.zeros_like(raw))
    assert out["classification"]=="UNRESOLVED_FREQUENCY_WANDERING_STRUCTURE_CANDIDATE"
    gate=out["metrics"]["spectral_path_gate"]
    assert gate["pass"] is True
    assert gate["pass_fraction"]==1.0
    assert gate["parameter_agreement_fraction"]==1.0
    assert abs(gate["median_slope_bins_per_run"]-0.75)<=0.25


def test_v08_white_noise_seed_bank_rejects_path():
    for seed in range(10):
        raw=np.random.default_rng(260000+seed).normal(size=(16,1024))
        out=analyze_residual_stack_v08(raw,np.zeros_like(raw))
        assert out["classification"]!="UNRESOLVED_FREQUENCY_WANDERING_STRUCTURE_CANDIDATE"
        assert out["metrics"]["spectral_path_gate"]["pass"] is False


def test_v08_ar1_seed_bank_rejects_path():
    for seed in range(5):
        rng=np.random.default_rng(261000+seed)
        eps=rng.normal(size=(16,1024))
        raw=np.zeros_like(eps)
        for j in range(raw.shape[1]):
            raw[:,j]=eps[:,j] if j==0 else 0.8*raw[:,j-1]+eps[:,j]
        out=analyze_residual_stack_v08(raw,np.zeros_like(raw))
        assert out["classification"]!="UNRESOLVED_FREQUENCY_WANDERING_STRUCTURE_CANDIDATE"
        assert out["metrics"]["spectral_path_gate"]["pass"] is False


def test_v08_random_run_frequency_does_not_form_linear_path():
    rng=np.random.default_rng(262000)
    runs,n=16,2048
    t=np.arange(n)
    ks=rng.uniform(100,160,size=runs)
    raw=np.asarray([
        rng.normal(size=n)+0.8*np.sin(2*np.pi*ks[i]*t/n+0.2*i)
        for i in range(runs)
    ])
    out=analyze_residual_stack_v08(raw,np.zeros_like(raw))
    assert out["classification"]!="UNRESOLVED_FREQUENCY_WANDERING_STRUCTURE_CANDIDATE"


def test_v08_path_family_does_not_override_low_frequency_ambiguity():
    rng=np.random.default_rng(263000)
    runs,n=16,2048
    t=np.arange(n)
    raw=np.asarray([
        rng.normal(size=n)+1.0*np.sin(2*np.pi*(1.0+0.05*i)*t/n)
        for i in range(runs)
    ])
    out=analyze_residual_stack_v08(raw,np.zeros_like(raw))
    assert out["classification"]!="UNRESOLVED_FREQUENCY_WANDERING_STRUCTURE_CANDIDATE"


def test_v08_path_candidate_never_promotes_physics():
    raw=_wandering(264000,amp=0.4)
    out=analyze_residual_stack_v08(raw,np.zeros_like(raw))
    assert out["policy"]["spectral_path_candidate_is_not_physical_attribution"] is True
    assert out["policy"]["time_fluctuation_claim_allowed"] is False
