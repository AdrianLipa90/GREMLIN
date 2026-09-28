import numpy as np

from gremlin_mcp.provenance_bound_sealed_abc_v07 import (
    provenance_bound_sealed_abc_v07,
)
from gremlin_mcp.recursive_residual_v04 import _sha_array

PLAN="c"*64
A=list(range(0,8))
B=list(range(8,16))
C=list(range(16,24))


def _meta(names):
    return {
        name:{
            "frozen_before_fit":True,
            "independent_of_target_fit":True,
            "source_type":"instrument_channel",
            "source_id":f"v07:{name}",
            "null_policy":"run_permutation",
        }
        for name in names
    }


def _receipts(candidates, *, authority="NOEMA_ACQUISITION_BOUND"):
    return {
        name:{
            "schema":"GREMLIN_NUISANCE_SOURCE_PROVENANCE_V0_1",
            "authority":authority,
            "source_is_independent_acquisition":True,
            "target_derived":False,
            "construction_rule_frozen_before_target_fit":True,
            "receipt_bound_before_target_fit":True,
            "bound_analysis_plan_sha256":PLAN,
            "candidate_payload_sha256":_sha_array(value),
            "source_receipt_sha256":"d"*64,
            "source_capture_relation":"SIMULTANEOUS_INDEPENDENT_SENSOR",
        }
        for name,value in candidates.items()
    }


def test_v07_valid_independent_sources_keep_true_second_layer():
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

    result,_,_=provenance_bound_sealed_abc_v07(
        raw,
        np.zeros_like(raw),
        candidates,
        _meta(candidates),
        _receipts(candidates),
        discovery_runs=A,
        confirmation_runs=B,
        replication_runs=C,
        analysis_plan_sha256=PLAN,
        analysis_plan_frozen_before_fit=True,
        discovery_null_count=255,
        confirmation_null_count=255,
        max_layers=3,
    )

    assert result["confirmed_layers"][:2]==["true_0","true_1"]
    assert result["policy"]["candidate_source_receipt_required"] is True
    assert len(result["source_provenance"]["provenance_bundle_sha256"])==64


def test_v07_missing_receipt_blocks_before_statistical_search():
    rng=np.random.default_rng(7)
    raw=rng.normal(size=(24,64))
    candidates={"x":rng.normal(size=raw.shape)}
    try:
        provenance_bound_sealed_abc_v07(
            raw,
            np.zeros_like(raw),
            candidates,
            _meta(candidates),
            {},
            discovery_runs=A,
            confirmation_runs=B,
            replication_runs=C,
            analysis_plan_sha256=PLAN,
            analysis_plan_frozen_before_fit=True,
        )
    except ValueError as exc:
        assert "missing provenance receipt" in str(exc)
    else:
        raise AssertionError("missing receipt accepted")


def test_v07_target_derived_receipt_blocks_leak_exploit():
    rng=np.random.default_rng(777)
    raw=rng.normal(size=(24,64))
    candidates={"leaked_target_copy":raw.copy()}
    receipts=_receipts(candidates)
    receipts["leaked_target_copy"]["target_derived"]=True

    try:
        provenance_bound_sealed_abc_v07(
            raw,
            np.zeros_like(raw),
            candidates,
            _meta(candidates),
            receipts,
            discovery_runs=A,
            confirmation_runs=B,
            replication_runs=C,
            analysis_plan_sha256=PLAN,
            analysis_plan_frozen_before_fit=True,
            max_layers=1,
        )
    except ValueError as exc:
        assert "target-derived provenance" in str(exc)
    else:
        raise AssertionError("target-derived candidate accepted")


def test_v07_candidate_hash_mismatch_blocks():
    rng=np.random.default_rng(8)
    raw=rng.normal(size=(24,64))
    candidates={"x":rng.normal(size=raw.shape)}
    receipts=_receipts(candidates)
    receipts["x"]["candidate_payload_sha256"]="0"*64

    try:
        provenance_bound_sealed_abc_v07(
            raw,
            np.zeros_like(raw),
            candidates,
            _meta(candidates),
            receipts,
            discovery_runs=A,
            confirmation_runs=B,
            replication_runs=C,
            analysis_plan_sha256=PLAN,
            analysis_plan_frozen_before_fit=True,
        )
    except ValueError as exc:
        assert "payload hash mismatch" in str(exc)
    else:
        raise AssertionError("hash mismatch accepted")


def test_v07_untrusted_authority_blocks():
    rng=np.random.default_rng(9)
    raw=rng.normal(size=(24,64))
    candidates={"x":rng.normal(size=raw.shape)}
    receipts=_receipts(candidates,authority="SELF_ASSERTED")

    try:
        provenance_bound_sealed_abc_v07(
            raw,
            np.zeros_like(raw),
            candidates,
            _meta(candidates),
            receipts,
            discovery_runs=A,
            confirmation_runs=B,
            replication_runs=C,
            analysis_plan_sha256=PLAN,
            analysis_plan_frozen_before_fit=True,
        )
    except ValueError as exc:
        assert "untrusted provenance authority" in str(exc)
    else:
        raise AssertionError("untrusted authority accepted")
