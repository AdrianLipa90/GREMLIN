import numpy as np

from gremlin_mcp.joint_family_null_v15 import joint_family_round_v15


def _meta(names):
    return {name:{"null_policy":"run_permutation"} for name in names}


def _correlated_family(seed,amp=0.10,rho=0.99,k=8):
    rng=np.random.default_rng(seed)
    runs,n=8,128
    latent=rng.normal(size=(runs,n))
    X={
        f"c{j}":rho*latent+np.sqrt(1-rho*rho)*rng.normal(size=(runs,n))
        for j in range(k)
    }
    raw=amp*X["c0"]+rng.normal(size=(runs,n))
    return raw,X


def test_joint_null_recovers_pinned_weak_true_candidate_in_correlated_family():
    raw,X=_correlated_family(1900008)
    out=joint_family_round_v15(
        raw,np.zeros_like(raw),X,_meta(X),
        null_count=127,familywise_alpha=0.05,
    )
    assert out["scores"]["c0"]["decision"]=="PASS"
    assert out["scores"]["c0"]["familywise_monte_carlo_p"]<=0.05


def test_mapping_order_does_not_change_joint_family_result():
    raw,X=_correlated_family(1900008)
    a=joint_family_round_v15(
        raw,np.zeros_like(raw),X,_meta(X),null_count=127,familywise_alpha=0.05
    )
    Y=dict(reversed(list(X.items())))
    b=joint_family_round_v15(
        raw,np.zeros_like(raw),Y,_meta(Y),null_count=127,familywise_alpha=0.05
    )
    assert a["analysis_sha256"]==b["analysis_sha256"]
    assert a["passing_candidates"]==b["passing_candidates"]


def test_pure_noise_family_does_not_force_acceptance():
    rng=np.random.default_rng(77)
    raw=rng.normal(size=(8,128))
    X={f"n{j}":rng.normal(size=raw.shape) for j in range(8)}
    out=joint_family_round_v15(
        raw,np.zeros_like(raw),X,_meta(X),null_count=127,familywise_alpha=0.05
    )
    assert out["passing_candidates"]==[]


def test_joint_world_policy_is_explicit():
    raw,X=_correlated_family(1900008)
    out=joint_family_round_v15(
        raw,np.zeros_like(raw),X,_meta(X),null_count=127,familywise_alpha=0.05
    )
    assert out["same_world_transform_shared_within_null_policy"] is True
    assert out["policy"]["candidate_specific_unsynchronized_family_null_forbidden"] is True
