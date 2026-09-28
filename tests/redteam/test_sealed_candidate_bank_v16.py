import hashlib
import json

import numpy as np

from gremlin_mcp.sealed_candidate_bank_v16 import (
    SCHEMA_TARGET,
    seal_candidate_bank_v16,
    sealed_joint_family_round_v16,
)


PLAN="a"*64
EVIDENCE="b"*64
VERIFY="c"*64
SOURCE="d"*64


def _meta(names):
    return {
        name:{
            "frozen_before_fit":True,
            "independent_of_target_fit":True,
            "source_type":"instrument_channel",
            "source_id":f"sealed:{name}",
            "source_commitment_sha256":SOURCE,
            "null_policy":"run_permutation",
        }
        for name in names
    }


def _seal(candidates,meta,sealed_ns=100):
    return seal_candidate_bank_v16(
        candidates,
        meta,
        analysis_plan_sha256=PLAN,
        sealed_unix_ns=sealed_ns,
        provenance_authority="NOEMA_APPEND_ONLY_RECEIPT",
        provenance_evidence_id="receipt:test",
        provenance_evidence_sha256=EVIDENCE,
        external_verification_receipt_sha256=VERIFY,
    )


def _sha_array(x):
    a=np.ascontiguousarray(np.asarray(x,dtype=np.float64))
    h=hashlib.sha256(); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def _target(raw,model,access_ns=200):
    return {
        "schema":SCHEMA_TARGET,
        "raw_sha256":_sha_array(raw),
        "initial_model_sha256":_sha_array(model),
        "target_first_access_unix_ns":access_ns,
        "externally_verified":True,
        "external_verification_receipt_sha256":VERIFY,
    }


def test_v16_valid_presealed_bank_reaches_joint_null():
    rng=np.random.default_rng(16001)
    raw=rng.normal(size=(8,128))
    model=np.zeros_like(raw)
    candidates={f"n{j}":rng.normal(size=raw.shape) for j in range(4)}
    meta=_meta(candidates)
    out=sealed_joint_family_round_v16(
        raw,model,candidates,meta,
        bank_seal=_seal(candidates,meta),
        target_access_receipt=_target(raw,model),
        null_count=63,
        familywise_alpha=0.05,
    )
    assert out["status"]=="ADMISSIBLE_BANK_JOINT_NULL_EVALUATED"
    assert out["seal_precedes_target_access"] is True


def test_v16_rejects_exact_raw_copy_even_with_apparently_valid_seal():
    rng=np.random.default_rng(16002)
    raw=rng.normal(size=(8,128))
    model=np.zeros_like(raw)
    candidates={"leak_raw":raw.copy()}
    candidates.update({f"n{j}":rng.normal(size=raw.shape) for j in range(3)})
    meta=_meta(candidates)
    try:
        sealed_joint_family_round_v16(
            raw,model,candidates,meta,
            bank_seal=_seal(candidates,meta,sealed_ns=50),
            target_access_receipt=_target(raw,model,access_ns=200),
            null_count=63,
            familywise_alpha=0.05,
        )
    except ValueError as exc:
        assert "exact target RAW" in str(exc)
    else:
        raise AssertionError("exact target-derived RAW candidate admitted")


def test_v16_rejects_bank_mutation_after_seal():
    rng=np.random.default_rng(16003)
    raw=rng.normal(size=(8,128)); model=np.zeros_like(raw)
    candidates={"x":rng.normal(size=raw.shape)}
    meta=_meta(candidates)
    seal=_seal(candidates,meta)
    candidates2={"x":candidates["x"].copy()}
    candidates2["x"][0,0]+=1e-9
    try:
        sealed_joint_family_round_v16(
            raw,model,candidates2,meta,
            bank_seal=seal,
            target_access_receipt=_target(raw,model),
            null_count=63,
            familywise_alpha=0.05,
        )
    except ValueError as exc:
        assert "differs from sealed bank" in str(exc)
    else:
        raise AssertionError("mutated candidate bank admitted")


def test_v16_rejects_metadata_mutation_after_seal():
    rng=np.random.default_rng(16004)
    raw=rng.normal(size=(8,128)); model=np.zeros_like(raw)
    candidates={"x":rng.normal(size=raw.shape)}
    meta=_meta(candidates)
    seal=_seal(candidates,meta)
    changed=_meta(candidates)
    changed["x"]["source_id"]="different"
    try:
        sealed_joint_family_round_v16(
            raw,model,candidates,changed,
            bank_seal=seal,
            target_access_receipt=_target(raw,model),
            null_count=63,
            familywise_alpha=0.05,
        )
    except ValueError as exc:
        assert "differs from sealed bank" in str(exc)
    else:
        raise AssertionError("mutated metadata admitted")


def test_v16_rejects_seal_created_after_target_access():
    rng=np.random.default_rng(16005)
    raw=rng.normal(size=(8,128)); model=np.zeros_like(raw)
    candidates={"x":rng.normal(size=raw.shape)}
    meta=_meta(candidates)
    try:
        sealed_joint_family_round_v16(
            raw,model,candidates,meta,
            bank_seal=_seal(candidates,meta,sealed_ns=300),
            target_access_receipt=_target(raw,model,access_ns=200),
            null_count=63,
            familywise_alpha=0.05,
        )
    except ValueError as exc:
        assert "not sealed before target access" in str(exc)
    else:
        raise AssertionError("post-target seal admitted")


def test_v16_rejects_target_derived_declaration_before_sealing():
    rng=np.random.default_rng(16006)
    candidates={"x":rng.normal(size=(8,128))}
    meta=_meta(candidates)
    meta["x"]["independent_of_target_fit"]=False
    try:
        _seal(candidates,meta)
    except ValueError as exc:
        assert "target-derived" in str(exc)
    else:
        raise AssertionError("declared target-derived candidate sealed")


def test_v16_mapping_order_does_not_change_bank_hash():
    rng=np.random.default_rng(16007)
    candidates={
        "a":rng.normal(size=(8,128)),
        "b":rng.normal(size=(8,128)),
    }
    meta=_meta(candidates)
    a=_seal(candidates,meta)
    rev=dict(reversed(list(candidates.items())))
    b=_seal(rev,_meta(rev))
    assert a["candidate_bank_sha256"]==b["candidate_bank_sha256"]
