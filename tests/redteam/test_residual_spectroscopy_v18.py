import numpy as np

from gremlin_mcp.residual_spectroscopy_v12 import (
    _notch,
    _pair_dependence_stats,
)
from gremlin_mcp.residual_spectroscopy_v18 import (
    nonlinear_run_dependence_audit_v18,
)


def test_v18_sparse_nonlinear_pair_is_detected_when_v12_linear_stats_are_small():
    rng=np.random.default_rng(120122)
    runs,n=16,512
    z=rng.normal(size=n)
    raw=rng.normal(size=(runs,n))
    raw[0]=z
    raw[1]=(z*z-1.0)/np.sqrt(2.0)

    zero,circ=_pair_dependence_stats(_notch(raw,20))
    assert zero<0.05
    assert circ<0.20

    out=nonlinear_run_dependence_audit_v18(
        raw,20,null_count=255,iaaft_iterations=10,alpha=0.005
    )
    assert out["invalidates_crossfit"] is True
    assert out["monte_carlo_p"]==1/256
    assert {out["witness"]["run_i"],out["witness"]["run_j"]}=={0,1}


def test_v18_harmonic_shared_latent_is_detected():
    rng=np.random.default_rng(120121)
    runs,n=16,512
    phi=rng.uniform(0,2*np.pi,size=n)
    raw=np.array([
        np.sqrt(2.0)*np.cos((i+1)*phi)
        for i in range(runs)
    ])
    out=nonlinear_run_dependence_audit_v18(
        raw,20,null_count=255,iaaft_iterations=10,alpha=0.005
    )
    assert out["invalidates_crossfit"] is True
    assert out["monte_carlo_p"]==1/256


def test_v18_independent_white_does_not_false_invalidate_seed18000():
    rng=np.random.default_rng(18000)
    raw=rng.normal(size=(16,512))
    out=nonlinear_run_dependence_audit_v18(
        raw,20,null_count=255,iaaft_iterations=10,alpha=0.005
    )
    assert out["invalidates_crossfit"] is False
    assert out["monte_carlo_p"]>0.05


def test_v18_independent_student_t3_does_not_false_invalidate_seed20001():
    rng=np.random.default_rng(20001)
    raw=rng.standard_t(df=3,size=(16,256))/np.sqrt(3.0)
    out=nonlinear_run_dependence_audit_v18(
        raw,20,null_count=255,iaaft_iterations=10,alpha=0.005
    )
    assert out["invalidates_crossfit"] is False
    assert out["monte_carlo_p"]>0.005


def test_v18_claim_boundary_is_explicit():
    rng=np.random.default_rng(18001)
    raw=rng.normal(size=(16,256))
    out=nonlinear_run_dependence_audit_v18(
        raw,20,null_count=255,iaaft_iterations=10,alpha=0.005
    )
    assert out["claim_boundary"]["pass_proves_independence"] is False
    assert out["claim_boundary"]["fail_identifies_cause"] is False
