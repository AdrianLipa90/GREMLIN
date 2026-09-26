import numpy as np
from gremlin_mcp.residual_spectroscopy_v02 import analyze_residual_stack

def base(seed=1,runs=16,n=4096):
    rng=np.random.default_rng(seed); return rng,np.zeros((runs,n))

def test_white_noise_stays_stochastic_compatible():
    rng,m=base(); out=analyze_residual_stack(rng.normal(size=m.shape),m); assert out["classification"]=="STOCHASTIC_BACKGROUND_COMPATIBLE"

def test_weak_line_emerges_only_in_stacked_residual_spectrum():
    rng,m=base(12); n=m.shape[1]; t=np.arange(n)
    raw=np.array([rng.normal(size=n)+0.10*np.sin(2*np.pi*137*t/n+0.2*i) for i in range(m.shape[0])])
    out=analyze_residual_stack(raw,m)
    assert out["classification"]=="UNRESOLVED_STRUCTURED_CANDIDATE"
    assert out["metrics"]["consensus_peak_bin"]==137
    assert out["metrics"]["stacked_peak_to_median_ratio"]>12
    assert out["metrics"]["individual_run_support_fraction"]>=0.5

def test_small_persistent_offset_is_preserved_not_zeroed():
    rng,m=base(7); raw=rng.normal(size=m.shape)+0.10
    out=analyze_residual_stack(raw,m)
    assert out["classification"]=="PERSISTENT_OFFSET_CANDIDATE"
    assert out["metrics"]["median_mean_offset_z"]>5

def test_nuisance_linked_line_is_systematic_candidate():
    rng,m=base(3); n=m.shape[1]; t=np.arange(n)
    nuis=np.array([np.sin(2*np.pi*31*t/n+0.03*i) for i in range(m.shape[0])])
    raw=0.8*nuis+rng.normal(scale=.3,size=m.shape)
    out=analyze_residual_stack(raw,m,nuisance_runs=nuis)
    assert out["classification"]=="SYSTEMATIC_OR_INSTRUMENTAL_CANDIDATE"

def test_cross_channel_coherence_is_reported_without_physical_promotion():
    rng,m=base(9); n=m.shape[1]; t=np.arange(n)
    ch=np.array([np.sin(2*np.pi*55*t/n+0.1*i) for i in range(m.shape[0])])
    raw=.7*ch+rng.normal(scale=.35,size=m.shape)
    out=analyze_residual_stack(raw,m,channel_runs={"aux_sensor":ch})
    assert out["metrics"]["cross_channel_coherence"]["aux_sensor"]>0.9
    assert out["policy"]["new_physics_from_residual_only"] is False

def test_known_template_and_drift_controls_win():
    rng,m=base(5); n=m.shape[1]; t=np.arange(n)
    q=np.array([np.cos(2*np.pi*41*t/n) for _ in range(m.shape[0])])
    out=analyze_residual_stack(.7*q+rng.normal(scale=.2,size=m.shape),m,known_template_runs=q)
    assert out["classification"]=="KNOWN_MODEL_STRUCTURE_CANDIDATE"
    tt=np.linspace(-1,1,n)
    raw=np.array([2*tt+rng.normal(scale=.15,size=n) for _ in range(m.shape[0])])
    out2=analyze_residual_stack(raw,m)
    assert out2["classification"]=="SYSTEMATIC_DRIFT_CANDIDATE"

def test_commitments_are_mutation_sensitive():
    rng,m=base(6); raw=rng.normal(size=m.shape)
    a=analyze_residual_stack(raw,m); raw[0,0]+=1e-6; b=analyze_residual_stack(raw,m)
    assert a["commitments"]["residual_sha256"]!=b["commitments"]["residual_sha256"]
