import numpy as np

from gremlin_mcp.residual_spectroscopy_v11 import analyze_residual_stack_v11
from gremlin_mcp.residual_spectroscopy_v12 import (
    _iaaft_row,
    _robust_nonstationarity_diagnostic,
    analyze_residual_stack_v12,
)


def _student_t(seed, runs=16, n=256, df=3):
    rng=np.random.default_rng(seed)
    x=rng.standard_t(df,size=(runs,n))
    if df>2:
        x=x/np.sqrt(df/(df-2))
    return x


def _ar1(seed, runs=16, n=2048, phi=0.99):
    rng=np.random.default_rng(seed)
    eps=rng.normal(size=(runs,n))
    out=np.zeros_like(eps)
    for j in range(n):
        out[:,j]=eps[:,j] if j==0 else phi*out[:,j-1]+eps[:,j]
    return out


def _variance_change_point(seed, runs=16, n=256, ratio=3.0):
    rng=np.random.default_rng(seed)
    x=rng.normal(size=(runs,n))
    x[:,n//2:]*=ratio
    x=(x-x.mean(axis=1,keepdims=True))/x.std(axis=1,keepdims=True)
    return x


def _shared_white(seed=4242, runs=16, n=256, rho=0.2):
    rng=np.random.default_rng(seed)
    common=rng.normal(size=n)
    indep=rng.normal(size=(runs,n))
    return np.sqrt(rho)*common[None,:]+np.sqrt(1-rho)*indep


def test_v11_false_invalidates_stationary_student_t3_seed300_but_v12_does_not():
    raw=_student_t(300)

    old=analyze_residual_stack_v11(
        raw,
        np.zeros_like(raw),
        run_dependence_stationarity_declared=True,
        run_dependence_null_count=255,
    )
    assert old["classification"]=="RUN_DEPENDENCE_INVALIDATES_CROSSFIT"

    new=analyze_residual_stack_v12(
        raw,
        np.zeros_like(raw),
        iaaft_null_applicable_declared=True,
        run_dependence_null_count=255,
        iaaft_iterations=20,
    )
    assert new["classification"]!="RUN_DEPENDENCE_INVALIDATES_CROSSFIT"
    audit=new["metrics"]["run_dependence_iaaft_audit"]
    assert audit["zero_lag_monte_carlo_p"]>0.005
    assert audit["circular_monte_carlo_p"]>0.005


def test_v12_iaaft_preserves_empirical_marginal_exactly_and_psd_approximately():
    x=np.random.default_rng(901).standard_t(3,size=512)
    y,error=_iaaft_row(x,np.random.default_rng(902),20)
    assert np.array_equal(np.sort(x),np.sort(y))
    assert error<0.15


def test_v12_obvious_variance_change_point_abstains_before_dependence_claim():
    raw=_variance_change_point(903)
    diag=_robust_nonstationarity_diagnostic(raw)
    assert diag["obvious_nonstationarity"] is True

    out=analyze_residual_stack_v12(
        raw,
        np.zeros_like(raw),
        iaaft_null_applicable_declared=True,
        run_dependence_null_count=255,
    )
    assert out["classification"]=="RUN_DEPENDENCE_AUDIT_NONSTATIONARY_UNCALIBRATED"


def test_v12_extreme_long_memory_abstains():
    raw=_ar1(104)
    out=analyze_residual_stack_v12(
        raw,
        np.zeros_like(raw),
        iaaft_null_applicable_declared=True,
        run_dependence_null_count=255,
    )
    assert out["classification"]=="RUN_DEPENDENCE_AUDIT_LONG_MEMORY_UNCALIBRATED"


def test_v12_shared_white_realization_still_invalidates_crossfit():
    raw=_shared_white()
    out=analyze_residual_stack_v12(
        raw,
        np.zeros_like(raw),
        iaaft_null_applicable_declared=True,
        run_dependence_null_count=255,
    )
    assert out["classification"]=="RUN_DEPENDENCE_INVALIDATES_CROSSFIT"


def test_v12_requires_explicit_iaaft_null_applicability_declaration():
    raw=np.random.default_rng(904).normal(size=(16,256))
    out=analyze_residual_stack_v12(
        raw,
        np.zeros_like(raw),
        iaaft_null_applicable_declared=False,
    )
    assert out["classification"]=="RUN_DEPENDENCE_AUDIT_IAAFT_NULL_NOT_DECLARED"
    assert out["policy"]["crossfit_valid_under_run_dependence_audit"] is False


def test_v12_fails_closed_when_null_cannot_resolve_bonferroni_alpha():
    raw=np.random.default_rng(905).normal(size=(16,256))
    try:
        analyze_residual_stack_v12(
            raw,
            np.zeros_like(raw),
            iaaft_null_applicable_declared=True,
            run_dependence_alpha=0.01,
            run_dependence_null_count=127,
        )
    except ValueError as exc:
        assert "cannot resolve alpha/2" in str(exc)
    else:
        raise AssertionError("under-resolved Monte Carlo null was accepted")
