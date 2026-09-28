import hashlib

import numpy as np

from gremlin_mcp.residual_spectroscopy_v19 import (
    provenance_bound_conditional_run_dependence_audit_v19,
)


def _sha_array(x):
    a=np.ascontiguousarray(np.asarray(x,dtype=np.float64))
    h=hashlib.sha256()
    h.update(str(a.shape).encode())
    h.update(a.tobytes())
    return h.hexdigest()


def _meta(conditioned, *, derived=False):
    return {
        "frozen_before_target":True,
        "external_chronology_verified":True,
        "independent_of_target_fit":True,
        "derived_from_target":bool(derived),
        "source_id":"synthetic:external-conditioner",
        "operator_sha256":"a"*64,
        "covariate_commitment_sha256":"b"*64,
        "conditioned_runs_sha256":_sha_array(conditioned),
    }


def _envelope(n=256, depth=0.8, period=64, phase=0.0):
    t=np.arange(n)
    return 1.0+depth*np.sin(2*np.pi*t/period+phase)


def test_v19_external_conditioning_removes_shared_deterministic_envelope_false_dependence():
    rng=np.random.default_rng(37400)
    runs,n=8,256
    env=_envelope(n)
    raw=rng.normal(size=(runs,n))*env[None,:]
    conditioned=raw/env[None,:]

    out=provenance_bound_conditional_run_dependence_audit_v19(
        raw,
        conditioned,
        _meta(conditioned),
        null_count=31,
        iaaft_iterations=8,
        alpha=0.05,
        iaaft_null_applicable_declared=True,
    )

    assert out["status"]=="RAW_DEPENDENCE_EXPLAINED_BY_FROZEN_COVARIATE_CANDIDATE"
    assert out["raw_audit"]["monte_carlo_p"]<=0.05
    assert out["conditioned_audit"]["monte_carlo_p"]>0.05
    assert out["claims"]["independence_proven"] is False


def test_v19_target_derived_conditioner_is_blocked_before_statistics():
    rng=np.random.default_rng(40100)
    raw=rng.normal(size=(8,128))
    mu=raw.mean(axis=0)
    sd=np.maximum(raw.std(axis=0),1e-9)
    conditioned=(raw-mu[None,:])/sd[None,:]

    try:
        provenance_bound_conditional_run_dependence_audit_v19(
            raw,
            conditioned,
            _meta(conditioned,derived=True),
            null_count=31,
            alpha=0.05,
            iaaft_null_applicable_declared=True,
        )
    except ValueError as exc:
        assert "target-derived" in str(exc)
    else:
        raise AssertionError("target-derived conditioning was accepted")


def test_v19_true_chebyshev_dependence_survives_external_conditioning_and_points_to_true_pair():
    rng=np.random.default_rng(51007)
    runs,n=8,256
    env=_envelope(n)
    phi=rng.uniform(0,2*np.pi,n)
    innovations=rng.normal(size=(runs,n))
    innovations[0]=np.sqrt(2.0)*np.cos(phi)
    innovations[1]=np.sqrt(2.0)*np.cos(7.0*phi)
    raw=innovations*env[None,:]
    conditioned=raw/env[None,:]

    out=provenance_bound_conditional_run_dependence_audit_v19(
        raw,
        conditioned,
        _meta(conditioned),
        null_count=31,
        iaaft_iterations=8,
        alpha=0.05,
        iaaft_null_applicable_declared=True,
    )

    assert out["status"]=="CONDITIONED_RUN_DEPENDENCE_DETECTED"
    witness=out["conditioned_audit"]["witness"]
    assert {witness["run_i"],witness["run_j"]}=={0,1}


def test_v19_bad_external_conditioner_fails_closed_by_leaving_detectable_dependence():
    rng=np.random.default_rng(37400)
    runs,n=8,256
    env=_envelope(n)
    raw=rng.normal(size=(runs,n))*env[None,:]
    wrong=_envelope(n,phase=0.6)
    conditioned=raw/wrong[None,:]

    out=provenance_bound_conditional_run_dependence_audit_v19(
        raw,
        conditioned,
        _meta(conditioned),
        null_count=31,
        iaaft_iterations=8,
        alpha=0.05,
        iaaft_null_applicable_declared=True,
    )

    assert out["status"]=="CONDITIONED_RUN_DEPENDENCE_DETECTED"
    assert out["conditioned_audit"]["monte_carlo_p"]<=0.05


def test_v19_conditioned_commitment_mismatch_is_rejected():
    rng=np.random.default_rng(19)
    raw=rng.normal(size=(8,128))
    conditioned=raw.copy()
    meta=_meta(conditioned)
    conditioned[0,0]+=1e-6

    try:
        provenance_bound_conditional_run_dependence_audit_v19(
            raw,
            conditioned,
            meta,
            null_count=31,
            alpha=0.05,
            iaaft_null_applicable_declared=True,
        )
    except ValueError as exc:
        assert "commitment mismatch" in str(exc)
    else:
        raise AssertionError("mutated conditioned array accepted")


def test_v19_abstains_without_declared_iaaft_null_applicability():
    rng=np.random.default_rng(20)
    raw=rng.normal(size=(8,128))
    conditioned=raw.copy()
    out=provenance_bound_conditional_run_dependence_audit_v19(
        raw,
        conditioned,
        _meta(conditioned),
        null_count=31,
        alpha=0.05,
        iaaft_null_applicable_declared=False,
    )
    assert out["status"]=="ABSTAIN_IAAFT_NULL_NOT_DECLARED"
    assert out["claims"]["independence_proven"] is False
