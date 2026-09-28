import numpy as np

from gremlin_mcp.sealed_abc_residual_v06 import (
    sealed_abc_residual_confirmation_v06,
)

PLAN="b"*64
A=list(range(0,8))
B=list(range(8,16))
C=list(range(16,24))


def _meta(names):
    return {
        name:{
            "frozen_before_fit":True,
            "independent_of_target_fit":True,
            "source_type":"instrument_channel",
            "source_id":f"v06-redteam:{name}",
            "null_policy":"run_permutation",
        }
        for name in names
    }


def test_v06_seed10117_discovery_false_layer_dies_on_sealed_bc():
    rng=np.random.default_rng(10117)
    runs,n=24,64
    true=rng.normal(size=(runs,n))
    candidates={"true_0":true}
    candidates.update({
        f"noise_{j:02d}":rng.normal(size=(runs,n))
        for j in range(7)
    })
    raw=0.9*true+rng.normal(size=(runs,n))

    result,_,_=sealed_abc_residual_confirmation_v06(
        raw,
        np.zeros_like(raw),
        candidates,
        _meta(candidates),
        discovery_runs=A,
        confirmation_runs=B,
        replication_runs=C,
        analysis_plan_sha256=PLAN,
        analysis_plan_frozen_before_fit=True,
        discovery_familywise_alpha=0.01,
        discovery_null_count=255,
        confirmation_alpha=0.01,
        confirmation_null_count=255,
        max_layers=3,
    )

    assert result["discovery_proposals"][:2]==["true_0","noise_06"]
    assert result["confirmed_layers"]==["true_0"]
    assert result["status"]=="PARTIAL_SEALED_ABC_PASS_STOPPED_ON_FAILURE"
    false_stage=result["confirmation_stages"][1]
    assert false_stage["candidate"]=="noise_06"
    assert false_stage["pass"] is False
    assert (
        false_stage["confirmation_B"]["pass"] is False
        or false_stage["replication_C"]["pass"] is False
    )


def test_v06_true_second_layer_survives_discovery_confirmation_replication():
    rng=np.random.default_rng(20000)
    runs,n=24,64
    true0=rng.normal(size=(runs,n))
    true1=rng.normal(size=(runs,n))
    candidates={"true_0":true0,"true_1":true1}
    candidates.update({
        f"noise_{j:02d}":rng.normal(size=(runs,n))
        for j in range(6)
    })
    raw=0.9*true0+0.3*true1+rng.normal(size=(runs,n))

    result,_,_=sealed_abc_residual_confirmation_v06(
        raw,
        np.zeros_like(raw),
        candidates,
        _meta(candidates),
        discovery_runs=A,
        confirmation_runs=B,
        replication_runs=C,
        analysis_plan_sha256=PLAN,
        analysis_plan_frozen_before_fit=True,
        discovery_familywise_alpha=0.01,
        discovery_null_count=255,
        confirmation_alpha=0.01,
        confirmation_null_count=255,
        max_layers=3,
    )

    assert result["confirmed_layers"][:2]==["true_0","true_1"]
    stage={x["candidate"]:x for x in result["confirmation_stages"]}
    assert stage["true_1"]["confirmation_B"]["pass"] is True
    assert stage["true_1"]["replication_C"]["pass"] is True
    assert stage["true_1"]["refit_on_B"] is False
    assert stage["true_1"]["refit_on_C"] is False


def test_v06_overlapping_splits_fail_closed():
    rng=np.random.default_rng(3)
    raw=rng.normal(size=(24,64))
    candidates={"x":rng.normal(size=raw.shape)}
    try:
        sealed_abc_residual_confirmation_v06(
            raw,
            np.zeros_like(raw),
            candidates,
            _meta(candidates),
            discovery_runs=A,
            confirmation_runs=list(range(7,15)),
            replication_runs=C,
            analysis_plan_sha256=PLAN,
            analysis_plan_frozen_before_fit=True,
        )
    except ValueError as exc:
        assert "disjoint" in str(exc)
    else:
        raise AssertionError("overlapping A/B/C split accepted")


def test_v06_unfrozen_plan_fails_closed():
    rng=np.random.default_rng(4)
    raw=rng.normal(size=(24,64))
    candidates={"x":rng.normal(size=raw.shape)}
    try:
        sealed_abc_residual_confirmation_v06(
            raw,
            np.zeros_like(raw),
            candidates,
            _meta(candidates),
            discovery_runs=A,
            confirmation_runs=B,
            replication_runs=C,
            analysis_plan_sha256=PLAN,
            analysis_plan_frozen_before_fit=False,
        )
    except ValueError as exc:
        assert "analysis plan" in str(exc)
    else:
        raise AssertionError("unfrozen plan accepted")


def test_v06_confirmation_null_resolution_fails_closed():
    rng=np.random.default_rng(5)
    raw=rng.normal(size=(24,64))
    candidates={"x":rng.normal(size=raw.shape)}
    try:
        sealed_abc_residual_confirmation_v06(
            raw,
            np.zeros_like(raw),
            candidates,
            _meta(candidates),
            discovery_runs=A,
            confirmation_runs=B,
            replication_runs=C,
            analysis_plan_sha256=PLAN,
            analysis_plan_frozen_before_fit=True,
            confirmation_alpha=0.001,
            confirmation_null_count=255,
        )
    except ValueError as exc:
        assert "cannot resolve" in str(exc)
    else:
        raise AssertionError("unresolved confirmation alpha accepted")
