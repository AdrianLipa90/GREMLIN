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


def _sha_array(x):
    import hashlib
    a=np.ascontiguousarray(np.asarray(x,dtype=np.float64))
    h=hashlib.sha256(); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def test_v16_forged_external_receipt_can_admit_near_target_leak():
    # Intentional trust-root reproducer. The v0.16 function can verify internal
    # consistency of a supplied provenance receipt, but cannot authenticate the
    # truth of caller-supplied timestamps/verification booleans by itself.
    rng=np.random.default_rng(161600)
    raw=rng.normal(size=(8,128))
    model=np.zeros_like(raw)
    near=0.999*raw+1e-4*rng.normal(size=raw.shape)
    candidates={"near_leak":near}
    candidates.update({
        f"noise_{j}":rng.normal(size=raw.shape)
        for j in range(7)
    })
    metadata={
        name:{
            "frozen_before_fit":True,
            "independent_of_target_fit":True,
            "source_type":"instrument_channel",
            "source_id":f"forged:{name}",
            "source_commitment_sha256":SOURCE,
            "null_policy":"run_permutation",
        }
        for name in candidates
    }

    seal=seal_candidate_bank_v16(
        candidates,
        metadata,
        analysis_plan_sha256=PLAN,
        sealed_unix_ns=50,
        provenance_authority="NOEMA_APPEND_ONLY_RECEIPT",
        provenance_evidence_id="forged:receipt",
        provenance_evidence_sha256=EVIDENCE,
        external_verification_receipt_sha256=VERIFY,
    )
    target={
        "schema":SCHEMA_TARGET,
        "raw_sha256":_sha_array(raw),
        "initial_model_sha256":_sha_array(model),
        "target_first_access_unix_ns":200,
        "externally_verified":True,
        "external_verification_receipt_sha256":VERIFY,
    }

    out=sealed_joint_family_round_v16(
        raw,
        model,
        candidates,
        metadata,
        bank_seal=seal,
        target_access_receipt=target,
        null_count=127,
        familywise_alpha=0.05,
    )

    score=out["joint_family_result"]["scores"]["near_leak"]

    # The contract accepts the internally consistent but forged provenance.
    # This test pins the external trust-root limitation.
    assert _sha_array(near)!=_sha_array(raw)
    assert score["decision"]=="PASS"
    assert score["conservative_holdout_gain"]>0.999999
    assert score["familywise_monte_carlo_p"]==0.0078125
