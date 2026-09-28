import numpy as np

from gremlin_mcp.residual_spectroscopy_v12 import _notch
from gremlin_mcp.residual_spectroscopy_v19 import (
    _ksg_mi_pair,
    raw_run_dependence_ksg_audit_v19,
)


def _chebyshev(seed,m,runs=8,n=256):
    rng=np.random.default_rng(seed)
    phi=rng.uniform(0,2*np.pi,size=n)
    raw=rng.normal(size=(runs,n))
    raw[0]=np.sqrt(2.0)*np.cos(phi)
    raw[1]=np.sqrt(2.0)*np.cos(m*phi)
    return raw


def _ar1(seed,runs=8,n=128,phi=0.8):
    rng=np.random.default_rng(seed)
    eps=rng.normal(size=(runs,n))
    out=np.zeros_like(eps)
    for j in range(n):
        out[:,j]=eps[:,j] if j==0 else phi*out[:,j-1]+eps[:,j]
    return out


def test_v19_high_order_chebyshev_is_detected_on_raw_before_notch():
    raw=_chebyshev(717,17)
    out=raw_run_dependence_ksg_audit_v19(
        raw,
        null_count=199,
        iaaft_iterations=8,
        alpha=0.005,
        k=3,
    )
    assert out["invalidates_crossfit"] is True
    assert out["monte_carlo_p"]==0.005
    assert {out["witness"]["run_i"],out["witness"]["run_j"]}=={0,1}
    assert out["observed_max_pair_ksg_mi"]>out["q99_null"]


def test_v19_notch_can_mask_same_deterministic_dependence():
    raw=_chebyshev(717,17)
    notched=_notch(raw,20)

    before=raw_run_dependence_ksg_audit_v19(
        raw,
        null_count=199,
        iaaft_iterations=8,
        alpha=0.005,
        k=3,
    )
    after=raw_run_dependence_ksg_audit_v19(
        notched,
        null_count=199,
        iaaft_iterations=8,
        alpha=0.005,
        k=3,
    )

    assert before["invalidates_crossfit"] is True
    assert after["invalidates_crossfit"] is False
    assert after["monte_carlo_p"]>0.10
    assert {after["witness"]["run_i"],after["witness"]["run_j"]}!={0,1}


def test_v19_white_control_does_not_false_invalidate():
    rng=np.random.default_rng(1101)
    raw=rng.normal(size=(8,128))
    out=raw_run_dependence_ksg_audit_v19(
        raw,
        null_count=199,
        iaaft_iterations=8,
        alpha=0.005,
        k=3,
    )
    assert out["invalidates_crossfit"] is False
    assert out["monte_carlo_p"]>0.05


def test_v19_ar1_control_does_not_false_invalidate():
    raw=_ar1(1305)
    out=raw_run_dependence_ksg_audit_v19(
        raw,
        null_count=199,
        iaaft_iterations=8,
        alpha=0.005,
        k=3,
    )
    assert out["invalidates_crossfit"] is False
    assert out["monte_carlo_p"]>0.005


def test_v19_exact_ties_fail_closed():
    raw=np.tile(np.arange(128,dtype=float)%4,(8,1))
    out=raw_run_dependence_ksg_audit_v19(
        raw,
        null_count=199,
        iaaft_iterations=8,
        alpha=0.005,
        k=3,
    )
    assert out["status"]=="ABSTAIN_EXACT_TIES_PRESENT"
    assert out["invalidates_crossfit"] is None
    assert out["max_exact_tie_fraction"]>0.0


def test_v19_ksg_matches_expected_easy_nonlinear_ordering():
    rng=np.random.default_rng(1919)
    x=rng.normal(size=256)
    y=(x*x-1.0)/np.sqrt(2.0)
    independent=np.random.default_rng(1920).normal(size=256)
    assert _ksg_mi_pair(x,y,3)>1.0
    assert _ksg_mi_pair(x,independent,3)<0.2
