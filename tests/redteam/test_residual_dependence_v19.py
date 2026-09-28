import numpy as np

from gremlin_mcp.residual_dependence_v19 import (
    _max_functional_predictability,
    dual_surface_functional_dependence_audit_v19,
    functional_dependence_surface_audit_v19,
)


def _chebyshev_case(m=17,seed=191917,runs=8,n=128):
    rng=np.random.default_rng(seed)
    phi=rng.uniform(0,2*np.pi,size=n)
    raw=rng.normal(size=(runs,n))
    raw[0]=np.sqrt(2.0)*np.cos(phi)
    raw[1]=np.sqrt(2.0)*np.cos(float(m)*phi)
    return raw


def test_v19_high_order_chebyshev_functional_dependence_is_visible_on_raw():
    raw=_chebyshev_case()
    stat,witness=_max_functional_predictability(raw,k=5)
    assert stat>0.70
    assert {witness["run_i"],witness["run_j"]}=={0,1}

    out=functional_dependence_surface_audit_v19(
        raw,
        20,
        surface="raw",
        null_count=31,
        iaaft_iterations=7,
        alpha=0.05,
        knn_k=5,
    )
    assert out["invalidates_independence"] is True
    assert out["monte_carlo_p"]==1/32


def test_v19_operator_sensitive_disagreement_abstains():
    raw=_chebyshev_case()
    out=dual_surface_functional_dependence_audit_v19(
        raw,
        20,
        total_alpha=0.10,
        null_count=31,
        iaaft_iterations=7,
        knn_k=5,
    )
    assert out["raw_surface"]["invalidates_independence"] is True
    assert out["post_candidate_removal_surface"]["invalidates_independence"] is False
    assert out["status"]=="OPERATOR_SENSITIVE_RUN_DEPENDENCE_AMBIGUOUS"
    assert out["crossfit_valid_under_v19_functional_guard"] is False


def test_v19_variance_only_dependence_is_explicit_no_go():
    rng=np.random.default_rng(190200)
    raw=rng.normal(size=(8,128))
    x=rng.normal(size=128)
    raw[0]=x
    raw[1]=x*rng.normal(size=128)

    out=functional_dependence_surface_audit_v19(
        raw,
        20,
        surface="raw",
        null_count=31,
        iaaft_iterations=7,
        alpha=0.05,
        knn_k=5,
    )
    assert out["invalidates_independence"] is False
    assert out["claim_boundary"]["guard_is_universal_independence_test"] is False
    assert out["claim_boundary"]["conditional_mean_blind_spot_open"] is True


def test_v19_strict_alpha_requires_enough_null_worlds():
    raw=_chebyshev_case()
    try:
        functional_dependence_surface_audit_v19(
            raw,
            20,
            surface="raw",
            null_count=31,
            alpha=0.005,
        )
    except ValueError as exc:
        assert "cannot resolve alpha" in str(exc)
    else:
        raise AssertionError("under-resolved Monte Carlo p accepted")
