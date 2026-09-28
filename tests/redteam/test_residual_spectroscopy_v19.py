import numpy as np

from gremlin_mcp.residual_spectroscopy_v18 import (
    nonlinear_run_dependence_audit_v18,
)
from gremlin_mcp.residual_spectroscopy_v19 import (
    _max_lagged_nonlinear_dependence_stat,
    lagged_nonlinear_run_dependence_audit_v19,
)


def _lagged_nonlinear_witness(seed=19019, runs=16, n=512, lag=37):
    rng=np.random.default_rng(seed)
    z=rng.normal(size=n)
    shifted=np.roll(z,lag)**2
    shifted=(shifted-shifted.mean())/shifted.std()
    raw=rng.normal(size=(runs,n))
    raw[0]=z
    raw[1]=shifted
    return raw


def test_v19_pins_lagged_nonlinear_failure_that_v18_misses():
    raw=_lagged_nonlinear_witness()

    old=nonlinear_run_dependence_audit_v18(
        raw,
        20,
        null_count=255,
        iaaft_iterations=10,
        alpha=0.005,
    )
    assert old["invalidates_crossfit"] is False
    assert old["monte_carlo_p"]>0.005

    new=lagged_nonlinear_run_dependence_audit_v19(
        raw,
        20,
        null_count=255,
        iaaft_iterations=10,
        alpha=0.005,
    )
    assert new["invalidates_crossfit"] is True
    assert new["monte_carlo_p"]==1/256
    assert {new["witness"]["run_i"],new["witness"]["run_j"]}=={0,1}


def test_v19_direct_stat_recovers_shifted_nonlinear_pair_and_lag():
    raw=_lagged_nonlinear_witness()
    value,witness=_max_lagged_nonlinear_dependence_stat(raw)
    assert value>0.95
    assert {witness["run_i"],witness["run_j"]}=={0,1}
    assert {witness["feature_i"],witness["feature_j"]}=={"x","x2"}
    assert witness["circular_lag"] in {37,512-37}


def test_v19_independent_white_does_not_false_invalidate_seed19100():
    rng=np.random.default_rng(19100)
    raw=rng.normal(size=(16,512))
    out=lagged_nonlinear_run_dependence_audit_v19(
        raw,
        20,
        null_count=255,
        iaaft_iterations=10,
        alpha=0.005,
    )
    assert out["invalidates_crossfit"] is False
    assert out["monte_carlo_p"]>0.05


def test_v19_requires_enough_null_worlds_to_resolve_alpha():
    raw=_lagged_nonlinear_witness(n=256,lag=19)
    try:
        lagged_nonlinear_run_dependence_audit_v19(
            raw,
            20,
            null_count=127,
            iaaft_iterations=10,
            alpha=0.005,
        )
    except ValueError as exc:
        assert "cannot resolve" in str(exc)
    else:
        raise AssertionError("under-resolved null ensemble accepted")


def test_v19_claim_boundary_is_explicit():
    raw=_lagged_nonlinear_witness(n=256,lag=19)
    out=lagged_nonlinear_run_dependence_audit_v19(
        raw,
        20,
        null_count=255,
        iaaft_iterations=10,
        alpha=0.005,
    )
    assert out["claim_boundary"]["pass_proves_independence"] is False
    assert out["claim_boundary"]["fail_identifies_cause"] is False
    assert out["claim_boundary"]["circular_lag_is_physical_delay"] is False
