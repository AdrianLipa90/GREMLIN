import numpy as np

from gremlin_mcp.recursive_residual_v05 import recursive_residual_decomposition_v05


def _meta(names):
    return {
        name:{
            "frozen_before_fit":True,
            "independent_of_target_fit":True,
            "source_type":"instrument_channel",
            "source_id":f"redteam:{name}",
            "null_policy":"run_permutation",
        }
        for name in names
    }


def test_v05_fails_closed_if_null_resolution_cannot_support_spent_alpha():
    rng=np.random.default_rng(1)
    raw=rng.normal(size=(8,128))
    candidates={f"p{j}":rng.normal(size=raw.shape) for j in range(8)}
    try:
        recursive_residual_decomposition_v05(
            raw,
            np.zeros_like(raw),
            candidates,
            _meta(candidates),
            experimentwise_alpha=0.01,
            null_count=255,
            max_layers=8,
        )
    except ValueError as exc:
        assert "cannot resolve Bonferroni-spent round alpha" in str(exc)
    else:
        raise AssertionError("under-resolved Monte Carlo alpha was accepted")


def test_v05_records_experimentwise_alpha_budget():
    rng=np.random.default_rng(2)
    raw=rng.normal(size=(8,128))
    candidates={f"p{j}":rng.normal(size=raw.shape) for j in range(4)}
    result,_,_=recursive_residual_decomposition_v05(
        raw,
        np.zeros_like(raw),
        candidates,
        _meta(candidates),
        experimentwise_alpha=0.08,
        null_count=63,
        max_layers=4,
    )
    ec=result["sequential_error_control"]
    assert ec["planned_rounds"]==4
    assert abs(ec["round_alpha"]-0.02)<1e-15
    assert ec["maximum_total_alpha_spend"]<=0.08+1e-15
    assert ec["monte_carlo_resolution"]<=ec["round_alpha"]


def test_v05_seed1_64_noise_family_is_rejected_under_experimentwise_gate():
    rng=np.random.default_rng(1)
    runs,n=8,128
    raw=rng.normal(size=(runs,n))
    candidates={f"noise_proxy_{j:02d}":rng.normal(size=(runs,n)) for j in range(64)}
    result,_,_=recursive_residual_decomposition_v05(
        raw,
        np.zeros_like(raw),
        candidates,
        _meta(candidates),
        min_holdout_gain=0.01,
        min_gain_over_individual_null=0.005,
        experimentwise_alpha=0.05,
        null_count=127,
        max_layers=1,
    )
    assert result["accepted_layers"]==[]
    assert all(
        score["decision"]!="PASS"
        for score in result["selection_rounds"][0]["candidate_scores"].values()
    )


def test_v05_real_nuisance_survives_64_candidate_family():
    rng=np.random.default_rng(3)
    runs,n=8,128
    true=rng.normal(size=(runs,n))
    raw=0.6*true+rng.normal(size=(runs,n))
    candidates={"true_nuisance":true}
    candidates.update({
        f"noise_proxy_{j:02d}":rng.normal(size=(runs,n))
        for j in range(63)
    })
    result,_,_=recursive_residual_decomposition_v05(
        raw,
        np.zeros_like(raw),
        candidates,
        _meta(candidates),
        experimentwise_alpha=0.05,
        null_count=127,
        max_layers=1,
    )
    assert result["accepted_layers"]==["true_nuisance"]
    score=result["selection_rounds"][0]["candidate_scores"]["true_nuisance"]
    assert score["decision"]=="PASS"
    assert score["familywise_monte_carlo_p"]<=0.05


def test_v05_target_derived_nuisance_still_fails_before_statistics():
    rng=np.random.default_rng(4)
    raw=rng.normal(size=(8,128))
    candidates={"leak":raw.copy()}
    meta=_meta(candidates)
    meta["leak"]["independent_of_target_fit"]=False
    try:
        recursive_residual_decomposition_v05(
            raw,np.zeros_like(raw),candidates,meta,
            experimentwise_alpha=0.05,
            null_count=63,
            max_layers=1,
        )
    except ValueError as exc:
        assert "target-derived" in str(exc)
    else:
        raise AssertionError("target-derived nuisance accepted")
