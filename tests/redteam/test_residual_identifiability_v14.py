import numpy as np

from gremlin_mcp.residual_identifiability_v14 import baseline_extension_identifiability_v14

F0=137.5/4096.0


def _line(seed,n,runs=16,amp=0.10):
    rng=np.random.default_rng(seed)
    t=np.arange(n)
    return np.asarray([
        rng.normal(size=n)+amp*np.sin(2*np.pi*F0*t+rng.uniform(0,2*np.pi))
        for _ in range(runs)
    ])


def _ar2(seed,n,runs=16,r=0.9998):
    rng=np.random.default_rng(seed)
    w=2*np.pi*F0
    a1=2*r*np.cos(w)
    a2=-(r*r)
    out=[]
    for _ in range(runs):
        eps=rng.normal(size=n)
        x=np.zeros(n,float)
        for t in range(2,n):
            x[t]=a1*x[t-1]+a2*x[t-2]+eps[t]
        x-=x.mean()
        x/=x.std()
        out.append(x)
    return np.asarray(out)


def test_line_like_witness_strengthens_across_baseline_without_physical_promotion():
    data={
        "n4096":_line(1,4096),
        "n8192":_line(2,8192),
        "n16384":_line(3,16384),
    }
    out=baseline_extension_identifiability_v14(
        data,frequency_cycles_per_sample=F0,segment_counts=(4,8,16)
    )
    assert out["status"]=="COHERENCE_STRENGTHENS_WITH_BASELINE_CANDIDATE"
    assert all(v>0 for v in out["endpoint_changes"].values())
    assert out["policy"]["baseline_strengthening_proves_deterministic_line"] is False


def test_high_q_ar2_witness_decays_across_baseline_but_stays_noncausal():
    data={
        "n4096":_ar2(11,4096),
        "n8192":_ar2(12,8192),
        "n16384":_ar2(13,16384),
    }
    out=baseline_extension_identifiability_v14(
        data,frequency_cycles_per_sample=F0,segment_counts=(4,8,16)
    )
    assert out["status"]=="COHERENCE_DECAYS_WITH_BASELINE_CANDIDATE"
    assert all(v<0 for v in out["endpoint_changes"].values())
    assert out["policy"]["baseline_decay_proves_stochastic_origin"] is False


def test_one_window_refuses_identifiability_claim():
    out=baseline_extension_identifiability_v14(
        {"single":_line(21,4096)},
        frequency_cycles_per_sample=F0,
    )
    assert out["status"]=="INSUFFICIENT_BASELINE_EXTENSION"
    assert out["policy"]["single_window_deterministic_line_claim_allowed"] is False


def test_noise_only_does_not_get_forced_into_mechanism_class():
    rng=np.random.default_rng(31)
    data={
        "n4096":rng.normal(size=(16,4096)),
        "n8192":rng.normal(size=(16,8192)),
        "n16384":rng.normal(size=(16,16384)),
    }
    out=baseline_extension_identifiability_v14(
        data,frequency_cycles_per_sample=F0,
    )
    assert out["status"] in {
        "BASELINE_EXTENSION_AMBIGUOUS",
        "COHERENCE_STRENGTHENS_WITH_BASELINE_CANDIDATE",
        "COHERENCE_DECAYS_WITH_BASELINE_CANDIDATE",
    }
    assert out["policy"]["new_physics_established"] is False


def test_frequency_must_be_frozen_and_valid():
    try:
        baseline_extension_identifiability_v14(
            {"x":_line(41,4096)},
            frequency_cycles_per_sample=0.0,
        )
    except ValueError as exc:
        assert "frequency_cycles_per_sample" in str(exc)
    else:
        raise AssertionError("invalid frequency accepted")
