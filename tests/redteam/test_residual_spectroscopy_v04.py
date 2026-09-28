import numpy as np

from gremlin_mcp.residual_spectroscopy_v04 import analyze_residual_stack_v04


def _ar1(seed, runs=16, n=4096, phi=0.8):
    rng=np.random.default_rng(seed)
    eps=rng.normal(size=(runs,n))
    out=np.zeros_like(eps)
    for j in range(n):
        out[:,j]=eps[:,j] if j==0 else phi*out[:,j-1]+eps[:,j]
    return out


def _one_over_f(seed, runs=16, n=4096):
    rng=np.random.default_rng(seed)
    f=np.fft.rfftfreq(n)
    amp=np.ones_like(f)
    amp[0]=0.0
    amp[1:]=1.0/np.sqrt(f[1:])
    rows=[]
    for _ in range(runs):
        z=amp*np.exp(1j*rng.uniform(0,2*np.pi,len(f)))
        x=np.fft.irfft(z,n=n)
        x=(x-x.mean())/x.std()
        rows.append(x)
    return np.asarray(rows)


def _weak_line(seed, *, fbin=137.5, amplitude=0.10, runs=16, n=4096, colored=False):
    if colored:
        raw=_ar1(seed,runs,n)
        rng=np.random.default_rng(seed+1000)
    else:
        rng=np.random.default_rng(seed)
        raw=rng.normal(size=(runs,n))
    t=np.arange(n)
    for i in range(runs):
        raw[i]+=amplitude*np.sin(2*np.pi*fbin*t/n+0.2*i)
    return raw


def test_v04_ar1_is_colored_not_narrowband():
    raw=_ar1(3)
    out=analyze_residual_stack_v04(raw,np.zeros_like(raw))
    assert out["classification"]=="STOCHASTIC_COLORED_BACKGROUND_COMPATIBLE"
    assert out["legacy_v02_classification"]=="UNRESOLVED_STRUCTURED_CANDIDATE"
    assert out["metrics"]["crossfit_narrowband_gate"]["pass"] is False


def test_v04_one_over_f_is_colored_not_narrowband():
    raw=_one_over_f(5)
    out=analyze_residual_stack_v04(raw,np.zeros_like(raw))
    assert out["classification"]=="STOCHASTIC_COLORED_BACKGROUND_COMPATIBLE"
    assert out["metrics"]["crossfit_narrowband_gate"]["pass"] is False


def test_v04_half_bin_weak_line_survives_crossfit_and_difference_transform():
    raw=_weak_line(7,fbin=137.5,amplitude=0.10)
    out=analyze_residual_stack_v04(raw,np.zeros_like(raw))
    assert out["classification"]=="UNRESOLVED_NARROWBAND_STRUCTURE_CANDIDATE"
    gate=out["metrics"]["crossfit_narrowband_gate"]
    assert gate["pass"] is True
    assert gate["pass_fraction"]>=0.75
    assert gate["bin_agreement_fraction"]>=0.75


def test_v04_narrowband_can_be_detected_on_colored_background():
    raw=_weak_line(11,fbin=137.5,amplitude=0.35,colored=True)
    out=analyze_residual_stack_v04(raw,np.zeros_like(raw))
    assert out["classification"]=="UNRESOLVED_NARROWBAND_STRUCTURE_CANDIDATE"


def test_v04_alternating_offset_is_not_called_persistent_signed_offset():
    rng=np.random.default_rng(13)
    runs,n=16,1024
    signs=np.array([1,-1]*(runs//2),dtype=float)
    raw=np.array([0.2*signs[i]+rng.normal(size=n) for i in range(runs)])
    out=analyze_residual_stack_v04(raw,np.zeros_like(raw))
    assert out["classification"]=="RUNWISE_OFFSET_VARIATION_CANDIDATE"
    assert out["metrics"]["signed_offset_consistency"]<0.80


def test_v04_same_sign_offset_is_persistent_signed_offset():
    rng=np.random.default_rng(17)
    runs,n=16,1024
    raw=np.array([0.2+rng.normal(size=n) for _ in range(runs)])
    out=analyze_residual_stack_v04(raw,np.zeros_like(raw))
    assert out["classification"]=="PERSISTENT_SIGNED_OFFSET_CANDIDATE"
    assert out["metrics"]["signed_offset_consistency"]>=0.80


def test_v04_white_noise_is_not_structured():
    rng=np.random.default_rng(23)
    raw=rng.normal(size=(16,4096))
    out=analyze_residual_stack_v04(raw,np.zeros_like(raw))
    assert out["classification"]=="STOCHASTIC_WHITE_BACKGROUND_COMPATIBLE"
    assert out["metrics"]["crossfit_narrowband_gate"]["pass"] is False


def test_v04_requires_enough_runs_for_crossfit_search():
    raw=np.random.default_rng(29).normal(size=(6,512))
    try:
        analyze_residual_stack_v04(raw,np.zeros_like(raw))
    except ValueError as exc:
        assert ">=8 runs" in str(exc)
    else:
        raise AssertionError("v0.4 accepted too few runs")
