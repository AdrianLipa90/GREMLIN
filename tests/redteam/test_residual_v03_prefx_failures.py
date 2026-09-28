import numpy as np

from gremlin_mcp.residual_spectroscopy_v02 import analyze_residual_stack
from gremlin_mcp.recursive_residual_v03 import recursive_residual_decomposition


def _ar1(seed, runs=16, n=2048, phi=0.8):
    rng=np.random.default_rng(seed)
    eps=rng.normal(size=(runs,n))
    out=np.zeros_like(eps)
    for j in range(n):
        out[:,j]=eps[:,j] if j==0 else phi*out[:,j-1]+eps[:,j]
    return out


def _meta(names):
    return {
        name:{
            "frozen_before_fit":True,
            "independent_of_target_fit":True,
            "source_type":"instrument_channel",
            "source_id":f"redteam:{name}",
            "null_policy":"run_permutation",
        }
        for name in names
    }


def test_prefx_v02_colored_ar1_is_promoted_to_unresolved_structured():
    raw=_ar1(17)
    model=np.zeros_like(raw)
    out=analyze_residual_stack(raw,model)
    # Reproducer of the v0.2 failure: broad correlated stochastic structure is
    # indistinguishable from a persistent narrow spectral structure by the
    # global peak/median rule.
    assert out["classification"]=="UNRESOLVED_STRUCTURED_CANDIDATE"
    assert out["metrics"]["median_abs_lag1"]>0.7
    assert out["metrics"]["stacked_peak_to_median_ratio"]>12.0


def test_prefx_v02_alternating_offset_is_called_persistent_offset():
    rng=np.random.default_rng(19)
    runs,n=16,1024
    signs=np.array([1,-1]*(runs//2),dtype=float)
    raw=np.array([
        0.2*signs[i]+rng.normal(size=n)
        for i in range(runs)
    ])
    out=analyze_residual_stack(raw,np.zeros_like(raw))
    # Reproducer: v0.2 uses |mean| significance and does not preserve offset sign.
    assert out["classification"]=="PERSISTENT_OFFSET_CANDIDATE"
    run_means=np.array([row["mean"] for row in out["per_run"]])
    assert np.any(run_means>0) and np.any(run_means<0)


def test_prefx_v02_half_bin_weak_line_falls_below_structured_gate():
    rng=np.random.default_rng(23)
    runs,n=16,4096
    t=np.arange(n)
    raw=np.array([
        rng.normal(size=n)+0.10*np.sin(2*np.pi*137.5*t/n+0.2*i)
        for i in range(runs)
    ])
    out=analyze_residual_stack(raw,np.zeros_like(raw))
    # Reproducer: exact-bin FFT gate loses a half-bin line by leakage.
    assert out["classification"]!="UNRESOLVED_STRUCTURED_CANDIDATE"
    assert out["metrics"]["stacked_peak_to_median_ratio"]<12.0


def test_prefx_v03_multiple_candidate_search_accepts_pure_noise_proxy():
    rng=np.random.default_rng(1)
    runs,n=4,128
    raw=rng.normal(size=(runs,n))
    candidates={}
    for j in range(64):
        candidates[f"noise_proxy_{j:02d}"]=rng.normal(size=(runs,n))

    result,_,_=recursive_residual_decomposition(
        raw,
        np.zeros_like(raw),
        candidates,
        _meta(candidates),
        min_holdout_gain=0.01,
        min_gain_over_null=0.005,
        max_layers=1,
    )
    # Deterministic false accept under a 64-candidate pure-noise family.
    assert result["accepted_layers"]==["noise_proxy_34"]
    score=result["selection_rounds"][0]["candidate_scores"]["noise_proxy_34"]
    assert score["conservative_holdout_gain"]>0.02
    assert score["gain_over_null_margin"]>0.03
