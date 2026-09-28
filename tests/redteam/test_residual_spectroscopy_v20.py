import numpy as np

from gremlin_mcp.residual_spectroscopy_v20 import (
    shared_sample_index_confound_audit_v20,
)


def _white(seed,runs=8,n=256):
    return np.random.default_rng(seed).normal(size=(runs,n))


def _ar1(seed,runs=8,n=256,phi=0.8):
    rng=np.random.default_rng(seed)
    eps=rng.normal(size=(runs,n))
    out=np.zeros_like(eps)
    for j in range(n):
        out[:,j]=eps[:,j] if j==0 else phi*out[:,j-1]+eps[:,j]
    return out


def _garch(seed,runs=8,n=256):
    rng=np.random.default_rng(seed)
    out=np.zeros((runs,n))
    for i in range(runs):
        eps=rng.normal(size=n)
        h=np.ones(n)
        x=np.zeros(n)
        for t in range(1,n):
            h[t]=0.05+0.1*x[t-1]**2+0.85*h[t-1]
            x[t]=np.sqrt(max(h[t],1e-9))*eps[t]
        out[i]=x
    return out


def _bursty(seed,runs=8,n=256):
    rng=np.random.default_rng(seed)
    x=rng.normal(size=(runs,n))
    mask=rng.random((runs,n))<0.03
    x[mask]+=rng.normal(scale=8.0,size=int(mask.sum()))
    return x


def test_v20_hann_window_on_independent_white_is_shared_scale_confound():
    raw=_white(2501)
    windowed=raw*np.hanning(raw.shape[1])[None,:]
    out=shared_sample_index_confound_audit_v20(
        windowed,blocks=8,null_count=199,alpha=0.005
    )
    assert out["shared_sample_index_confound"] is True
    assert out["monte_carlo_p"]==0.005
    assert out["dominant_profile_kind"]=="scale"
    assert out["median_pair_scale_profile_correlation"]>0.95


def test_v20_shared_location_envelope_is_detected():
    rng=np.random.default_rng(2601)
    runs,n=8,256
    t=np.arange(n)
    common=0.8*np.sin(2*np.pi*3*t/n)
    raw=rng.normal(size=(runs,n))+common
    out=shared_sample_index_confound_audit_v20(
        raw,blocks=8,null_count=199,alpha=0.005
    )
    assert out["shared_sample_index_confound"] is True
    assert out["monte_carlo_p"]==0.005
    assert out["dominant_profile_kind"]=="location"


def test_v20_shared_scale_envelope_is_detected():
    rng=np.random.default_rng(2701)
    runs,n=8,256
    t=np.arange(n)
    envelope=np.exp(0.8*np.sin(2*np.pi*2*t/n))
    raw=rng.normal(size=(runs,n))*envelope[None,:]
    out=shared_sample_index_confound_audit_v20(
        raw,blocks=8,null_count=199,alpha=0.005
    )
    assert out["shared_sample_index_confound"] is True
    assert out["monte_carlo_p"]==0.005
    assert out["dominant_profile_kind"]=="scale"


def test_v20_white_control_is_not_false_confound():
    out=shared_sample_index_confound_audit_v20(
        _white(2101),blocks=8,null_count=199,alpha=0.005
    )
    assert out["shared_sample_index_confound"] is False
    assert out["monte_carlo_p"]>0.05


def test_v20_ar1_control_is_not_false_confound():
    out=shared_sample_index_confound_audit_v20(
        _ar1(2204),blocks=8,null_count=199,alpha=0.005
    )
    assert out["shared_sample_index_confound"] is False
    assert out["monte_carlo_p"]>0.05


def test_v20_garch_control_is_not_false_confound():
    out=shared_sample_index_confound_audit_v20(
        _garch(2301),blocks=8,null_count=199,alpha=0.005
    )
    assert out["shared_sample_index_confound"] is False
    assert out["monte_carlo_p"]>0.05


def test_v20_bursty_control_is_not_false_confound():
    out=shared_sample_index_confound_audit_v20(
        _bursty(2402),blocks=8,null_count=199,alpha=0.005
    )
    assert out["shared_sample_index_confound"] is False
    assert out["monte_carlo_p"]>0.01
