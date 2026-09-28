import numpy as np

from gremlin_mcp.recursive_residual_v05 import (
    recursive_residual_decomposition_v05,
)

PLAN="a"*64


def _meta(names):
    return {
        name:{
            "frozen_before_fit":True,
            "independent_of_target_fit":True,
            "source_type":"instrument_channel",
            "source_id":f"v05-redteam:{name}",
            "null_policy":"run_permutation",
        }
        for name in names
    }


def test_v05_repairs_seed10100_recursive_alpha_refresh_false_accept():
    rng=np.random.default_rng(10100)
    runs,n=8,64
    true=rng.normal(size=(runs,n))
    candidates={"true_0":true}
    candidates.update({
        f"noise_{j:02d}":rng.normal(size=(runs,n))
        for j in range(7)
    })
    raw=0.9*true+rng.normal(size=(runs,n))

    result,_,_=recursive_residual_decomposition_v05(
        raw,
        np.zeros_like(raw),
        candidates,
        _meta(candidates),
        global_familywise_alpha=0.01,
        null_count=255,
        max_layers=2,
        analysis_plan_sha256=PLAN,
        analysis_plan_frozen_before_fit=True,
    )

    assert result["accepted_layers"]==["true_0"]
    round2=result["selection_rounds"][1]
    score=round2["candidate_scores"]["noise_04"]
    assert score["decision"]=="FAIL_GLOBAL_ALPHA_BUDGET"
    assert score["familywise_empirical_p"]>score["round_alpha_budget"]


def test_v05_fails_closed_when_null_resolution_cannot_support_global_budget():
    rng=np.random.default_rng(2)
    raw=rng.normal(size=(8,64))
    candidates={"x":rng.normal(size=raw.shape)}
    try:
        recursive_residual_decomposition_v05(
            raw,
            np.zeros_like(raw),
            candidates,
            _meta(candidates),
            global_familywise_alpha=0.01,
            null_count=255,
            max_layers=8,
            analysis_plan_sha256=PLAN,
            analysis_plan_frozen_before_fit=True,
        )
    except ValueError as exc:
        assert "cannot resolve round alpha" in str(exc)
    else:
        raise AssertionError("insufficient Monte Carlo null resolution accepted")


def test_v05_two_strong_true_layers_survive_global_budget():
    rng=np.random.default_rng(5001)
    runs,n=8,64
    a=rng.normal(size=(runs,n))
    b=rng.normal(size=(runs,n))
    candidates={"true_a":a,"true_b":b}
    candidates.update({
        f"noise_{j}":rng.normal(size=(runs,n))
        for j in range(4)
    })
    raw=1.1*a+0.9*b+rng.normal(size=(runs,n))

    result,_,_=recursive_residual_decomposition_v05(
        raw,
        np.zeros_like(raw),
        candidates,
        _meta(candidates),
        global_familywise_alpha=0.02,
        null_count=127,
        max_layers=2,
        analysis_plan_sha256=PLAN,
        analysis_plan_frozen_before_fit=True,
    )

    assert set(result["accepted_layers"])=={"true_a","true_b"}
    assert len(result["accepted_layers"])==2
    assert all(
        not name.startswith("noise_")
        for name in result["accepted_layers"]
    )


def test_v05_pure_noise_family_stays_empty():
    rng=np.random.default_rng(5002)
    raw=rng.normal(size=(8,64))
    candidates={
        f"noise_{j}":rng.normal(size=raw.shape)
        for j in range(8)
    }

    result,_,_=recursive_residual_decomposition_v05(
        raw,
        np.zeros_like(raw),
        candidates,
        _meta(candidates),
        global_familywise_alpha=0.02,
        null_count=127,
        max_layers=2,
        analysis_plan_sha256=PLAN,
        analysis_plan_frozen_before_fit=True,
    )

    assert result["accepted_layers"]==[]
    assert result["status"]=="NO_NUISANCE_LAYER_ACCEPTED"


def test_v05_unfrozen_analysis_plan_fails_before_search():
    rng=np.random.default_rng(5003)
    raw=rng.normal(size=(8,64))
    candidates={"x":rng.normal(size=raw.shape)}
    try:
        recursive_residual_decomposition_v05(
            raw,
            np.zeros_like(raw),
            candidates,
            _meta(candidates),
            global_familywise_alpha=0.02,
            null_count=127,
            max_layers=2,
            analysis_plan_sha256=PLAN,
            analysis_plan_frozen_before_fit=False,
        )
    except ValueError as exc:
        assert "analysis plan" in str(exc)
    else:
        raise AssertionError("unfrozen analysis plan accepted")
