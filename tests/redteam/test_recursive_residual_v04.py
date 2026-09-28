from collections import OrderedDict

import numpy as np

from gremlin_mcp.recursive_residual_v04 import recursive_residual_decomposition_v04


def _meta(names, null_policy="run_permutation"):
    return {
        name:{
            "frozen_before_fit":True,
            "independent_of_target_fit":True,
            "source_type":"instrument_channel",
            "source_id":f"redteam:{name}",
            "null_policy":null_policy,
        }
        for name in names
    }


def test_v04_familywise_gate_rejects_seed1_64_proxy_false_accept_reproducer():
    rng=np.random.default_rng(1)
    runs,n=8,128
    raw=rng.normal(size=(runs,n))
    candidates={f"noise_proxy_{j:02d}":rng.normal(size=(runs,n)) for j in range(64)}

    result,_,_=recursive_residual_decomposition_v04(
        raw,
        np.zeros_like(raw),
        candidates,
        _meta(candidates),
        min_holdout_gain=0.01,
        min_gain_over_individual_null=0.005,
        familywise_alpha=0.05,
        null_count=127,
        max_layers=1,
    )

    assert result["accepted_layers"]==[]
    round0=result["selection_rounds"][0]
    assert round0["familywise_null_worlds"]>=100
    assert all(
        score["decision"]!="PASS"
        for score in round0["candidate_scores"].values()
    )


def test_v04_familywise_gate_keeps_real_nuisance_inside_64_candidate_family():
    rng=np.random.default_rng(2)
    runs,n=8,128
    true=rng.normal(size=(runs,n))
    raw=0.5*true+rng.normal(size=(runs,n))
    candidates={"true_nuisance":true}
    candidates.update({
        f"noise_proxy_{j:02d}":rng.normal(size=(runs,n))
        for j in range(63)
    })

    result,_,_=recursive_residual_decomposition_v04(
        raw,
        np.zeros_like(raw),
        candidates,
        _meta(candidates),
        familywise_alpha=0.05,
        null_count=127,
        max_layers=1,
    )

    assert result["accepted_layers"]==["true_nuisance"]
    score=result["selection_rounds"][0]["candidate_scores"]["true_nuisance"]
    assert score["decision"]=="PASS"
    assert score["conservative_holdout_gain"]>score["familywise_max_null_threshold"]


def test_v04_rejects_large_uncontrolled_candidate_bank():
    rng=np.random.default_rng(3)
    raw=rng.normal(size=(8,128))
    candidates={f"p{j}":rng.normal(size=raw.shape) for j in range(65)}
    try:
        recursive_residual_decomposition_v04(
            raw,np.zeros_like(raw),candidates,_meta(candidates)
        )
    except ValueError as exc:
        assert "candidate family too large" in str(exc)
    else:
        raise AssertionError("uncontrolled large candidate family accepted")


def test_v04_requires_eight_runs():
    rng=np.random.default_rng(4)
    raw=rng.normal(size=(6,128))
    candidates={"x":rng.normal(size=raw.shape)}
    try:
        recursive_residual_decomposition_v04(
            raw,np.zeros_like(raw),candidates,_meta(candidates)
        )
    except ValueError as exc:
        assert ">=8 runs" in str(exc)
    else:
        raise AssertionError("too few runs accepted")


def test_v04_target_derived_nuisance_rejected_before_family_test():
    rng=np.random.default_rng(5)
    raw=rng.normal(size=(8,128))
    candidates={"leak":raw.copy()}
    metadata=_meta(candidates)
    metadata["leak"]["independent_of_target_fit"]=False
    try:
        recursive_residual_decomposition_v04(
            raw,np.zeros_like(raw),candidates,metadata
        )
    except ValueError as exc:
        assert "target-derived" in str(exc)
    else:
        raise AssertionError("target-derived nuisance accepted")


def test_v04_duplicate_channels_leave_attribution_open():
    rng=np.random.default_rng(6)
    runs,n=8,256
    signal=rng.normal(size=(runs,n))
    raw=0.8*signal+rng.normal(scale=0.3,size=(runs,n))
    candidates=OrderedDict([
        ("a_sensor",signal),
        ("b_duplicate_sensor",signal.copy()),
    ])

    result,_,_=recursive_residual_decomposition_v04(
        raw,np.zeros_like(raw),candidates,_meta(candidates),
        null_count=127,
        max_layers=1,
    )

    assert len(result["accepted_layers"])==1
    assert result["status"]=="PASS_WITH_ATTRIBUTION_ALIAS_OPEN"
    assert result["attribution_ambiguous"] is True
    assert result["alias_pairs"][0]["abs_correlation"]>0.999999
