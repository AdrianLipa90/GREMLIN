import numpy as np
from gremlin_mcp.residual_spectroscopy_v02 import analyze_residual_stack

def test_layered_residual_reveals_weak_structure_after_explicit_nuisance_model():
    rng=np.random.default_rng(270927)
    runs,n=16,4096
    t=np.arange(n)
    nuisance=np.array([
        2.0*np.sin(2*np.pi*31*t/n+0.03*i)
        for i in range(runs)
    ])
    weak=np.array([
        0.10*np.sin(2*np.pi*137*t/n+0.2*i)
        for i in range(runs)
    ])
    noise=rng.normal(size=(runs,n))
    raw=nuisance+weak+noise

    stage1=analyze_residual_stack(
        raw,np.zeros_like(raw),
        nuisance_runs=nuisance,
        channel_runs={"wavelength_jitter_gain_proxy":nuisance},
    )
    assert stage1["classification"]=="SYSTEMATIC_OR_INSTRUMENTAL_CANDIDATE"
    assert stage1["metrics"]["median_abs_nuisance_correlation"]>0.80
    assert stage1["metrics"]["consensus_peak_bin"]==31

    # Model the identified nuisance explicitly; do not destructively alter raw.
    stage2=analyze_residual_stack(
        raw,nuisance,
        channel_runs={"wavelength_jitter_gain_proxy":nuisance},
    )
    assert stage2["classification"]=="UNRESOLVED_STRUCTURED_CANDIDATE"
    assert stage2["metrics"]["consensus_peak_bin"]==137
    assert stage2["metrics"]["stacked_peak_to_median_ratio"]>12.0
    assert stage2["metrics"]["individual_run_support_fraction"]==1.0

    assert stage1["commitments"]["raw_sha256"]==stage2["commitments"]["raw_sha256"]
    assert stage1["commitments"]["model_sha256"]!=stage2["commitments"]["model_sha256"]
    assert stage1["commitments"]["residual_sha256"]!=stage2["commitments"]["residual_sha256"]
