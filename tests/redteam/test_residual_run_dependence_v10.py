import numpy as np

from gremlin_mcp.residual_spectroscopy_v10 import analyze_residual_stack_v10


def _shared(seed, *, runs=16, n=512, shared_fraction=0.20):
    rng=np.random.default_rng(seed)
    base=rng.normal(size=n)
    rows=[]
    for _ in range(runs):
        eps=rng.normal(size=n)
        rows.append(
            np.sqrt(shared_fraction)*base
            + np.sqrt(1.0-shared_fraction)*eps
        )
    return np.asarray(rows)


def _shifted_copy(seed, *, runs=16, n=512):
    rng=np.random.default_rng(seed)
    base=rng.normal(size=n)
    return np.asarray([
        np.roll(base,int(rng.integers(0,n)))
        for _ in range(runs)
    ])


def _ar1(seed, *, runs=16, n=512, phi=0.99):
    rng=np.random.default_rng(seed)
    eps=rng.normal(size=(runs,n))
    out=np.zeros_like(eps)
    for j in range(n):
        out[:,j]=eps[:,j] if j==0 else phi*out[:,j-1]+eps[:,j]
    return out


def _weak_line(seed, *, runs=16, n=512, k=70.5, amp=0.25):
    rng=np.random.default_rng(seed)
    t=np.arange(n)
    return np.asarray([
        rng.normal(size=n)+amp*np.sin(2*np.pi*k*t/n+0.2*i)
        for i in range(runs)
    ])


def test_shared_background_invalidates_crossfit():
    raw=_shared(101,shared_fraction=0.20)
    out=analyze_residual_stack_v10(
        raw,np.zeros_like(raw),
        run_dependence_null_count=127,
    )
    assert out["classification"]=="RUN_DEPENDENCE_INVALIDATES_CROSSFIT"
    audit=out["metrics"]["background_run_dependence_surrogate_audit"]
    assert audit["monte_carlo_p"]<=0.01
    assert out["policy"]["crossfit_valid_under_run_dependence_audit"] is False


def test_shifted_copy_background_invalidates_crossfit():
    raw=_shifted_copy(102)
    out=analyze_residual_stack_v10(
        raw,np.zeros_like(raw),
        run_dependence_null_count=127,
    )
    assert out["classification"]=="RUN_DEPENDENCE_INVALIDATES_CROSSFIT"
    audit=out["metrics"]["background_run_dependence_surrogate_audit"]
    assert audit["observed_median_max_circular_correlation"]>0.95


def test_independent_weak_line_is_not_rejected_as_shared_background():
    raw=_weak_line(103)
    out=analyze_residual_stack_v10(
        raw,np.zeros_like(raw),
        run_dependence_null_count=127,
    )
    assert out["classification"]!="RUN_DEPENDENCE_INVALIDATES_CROSSFIT"
    assert out["classification"]!="RUN_DEPENDENCE_AUDIT_LONG_MEMORY_UNCALIBRATED"
    assert out["policy"]["crossfit_valid_under_run_dependence_audit"] is True


def test_extreme_long_memory_abstains_instead_of_false_shared_claim():
    raw=_ar1(104,phi=0.99)
    out=analyze_residual_stack_v10(
        raw,np.zeros_like(raw),
        run_dependence_null_count=127,
        long_memory_lag1_abstain=0.97,
    )
    assert out["classification"]=="RUN_DEPENDENCE_AUDIT_LONG_MEMORY_UNCALIBRATED"
    assert out["policy"]["crossfit_valid_under_run_dependence_audit"] is False


def test_null_count_below_resolution_fails_closed():
    raw=np.random.default_rng(105).normal(size=(16,512))
    try:
        analyze_residual_stack_v10(
            raw,np.zeros_like(raw),
            run_dependence_null_count=63,
        )
    except ValueError as exc:
        assert ">=99" in str(exc)
    else:
        raise AssertionError("under-resolved null ensemble accepted")


def _student_t(seed, *, runs=16, n=512, df=3):
    rng=np.random.default_rng(seed)
    x=rng.standard_t(df,size=(runs,n))
    return x/np.std(x,axis=1,keepdims=True)


def _bursty(seed, *, runs=16, n=512):
    rng=np.random.default_rng(seed)
    x=rng.normal(size=(runs,n))
    for i in range(runs):
        idx=rng.choice(n,size=max(1,n//40),replace=False)
        x[i,idx]+=rng.normal(0,8,size=len(idx))
    return x


def test_iaaft_heavy_tail_background_not_forced_into_shared_run_claim():
    for raw in (_student_t(106),_bursty(107)):
        out=analyze_residual_stack_v10(
            raw,np.zeros_like(raw),
            run_dependence_null_count=127,
        )
        assert out["classification"]!="RUN_DEPENDENCE_INVALIDATES_CROSSFIT"
        audit=out["metrics"]["background_run_dependence_surrogate_audit"]
        assert audit["median_surrogate_psd_relative_error"]<0.15


def test_long_memory_audit_uses_pre_notch_memory():
    raw=_ar1(104,phi=0.99)
    out=analyze_residual_stack_v10(
        raw,np.zeros_like(raw),
        run_dependence_null_count=127,
        long_memory_lag1_abstain=0.97,
    )
    audit=out["metrics"]["background_run_dependence_surrogate_audit"]
    assert audit["median_abs_lag1_pre_notch"]>=0.97
    assert out["classification"]=="RUN_DEPENDENCE_AUDIT_LONG_MEMORY_UNCALIBRATED"
