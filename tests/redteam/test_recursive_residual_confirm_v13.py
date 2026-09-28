import hashlib
import numpy as np

from gremlin_mcp.recursive_residual_confirm_v13 import confirm_recursive_selection_v13


def _sha_array(x):
    a=np.ascontiguousarray(np.asarray(x,dtype=np.float64))
    h=hashlib.sha256(); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def _case(seed=30116):
    rng=np.random.default_rng(seed+10_000_000)
    runs,n=8,128
    c0=rng.normal(size=(runs,n))
    c1=rng.normal(size=(runs,n))
    c2=rng.normal(size=(runs,n))
    false=rng.normal(size=(runs,n))
    raw=0.6*c0+0.5*c1+0.4*c2+rng.normal(size=(runs,n))
    components={"true_0":c0,"true_1":c1,"true_2":c2,"noise_01":false}
    metadata={
        name:{
            "null_policy":"run_permutation",
            "independent_of_confirmatory_target_fit":True,
            "frozen_before_confirmatory_test":True,
        }
        for name in components
    }
    discovery={
        "schema":"GREMLIN_RECURSIVE_RESIDUAL_DECOMPOSITION_V0_5",
        "raw_sha256":"a"*64,
        "accepted_layers":["true_0","true_1","true_2","noise_01"],
        "final_joint_coefficients":{
            "true_0":0.5866940716403657,
            "true_1":0.47909408132661496,
            "true_2":0.4094279702663255,
            "noise_01":-0.10982469932547012,
        },
    }
    declaration={
        "sealed_before_discovery":True,
        "independent_dataset":True,
        "dataset_id":"confirm:seed30116:independent",
    }
    run_audit={
        "schema":"GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_12",
        "analysis_sha256":"b"*64,
        "commitments":{
            "raw_sha256":_sha_array(raw),
            "model_sha256":_sha_array(np.zeros_like(raw)),
        },
        "policy":{
            "crossfit_valid_under_run_dependence_audit":True,
        },
    }
    return raw,components,metadata,discovery,run_audit,declaration


def test_seed30116_false_layer_fails_sealed_confirmation():
    raw,components,metadata,discovery,run_audit,declaration=_case()
    out=confirm_recursive_selection_v13(
        discovery,
        raw,
        np.zeros_like(raw),
        components,
        metadata,
        run_audit,
        declaration,
        confirmatory_alpha=0.01,
        null_count=255,
    )
    assert out["status"]=="SEALED_CONFIRMATION_FAIL"
    assert set(out["confirmed_layers"])=={"true_0","true_1","true_2"}
    assert out["failed_layers"]==["noise_01"]
    assert out["scores"]["noise_01"]["confirmatory_gain"]<0.0
    assert out["coefficients_refit_on_confirmation"] is False


def test_true_only_selection_confirms_without_refit():
    raw,components,metadata,discovery,run_audit,declaration=_case(30117)
    discovery["accepted_layers"]=["true_0","true_1","true_2"]
    discovery["final_joint_coefficients"]={
        "true_0":0.6,"true_1":0.5,"true_2":0.4,
    }
    out=confirm_recursive_selection_v13(
        discovery,raw,np.zeros_like(raw),components,metadata,run_audit,declaration,
        confirmatory_alpha=0.01,null_count=255,
    )
    assert out["status"]=="SEALED_CONFIRMATION_PASS"
    assert out["failed_layers"]==[]
    assert set(out["confirmed_layers"])=={"true_0","true_1","true_2"}


def test_reusing_discovery_raw_fails_closed():
    raw,components,metadata,discovery,run_audit,declaration=_case()
    discovery["raw_sha256"]=_sha_array(raw)
    try:
        confirm_recursive_selection_v13(
            discovery,raw,np.zeros_like(raw),components,metadata,run_audit,declaration,
            null_count=255,
        )
    except ValueError as exc:
        assert "reuses discovery RAW" in str(exc)
    else:
        raise AssertionError("same RAW accepted as independent confirmation")


def test_unsealed_confirmation_fails_closed():
    raw,components,metadata,discovery,run_audit,declaration=_case()
    declaration["sealed_before_discovery"]=False
    try:
        confirm_recursive_selection_v13(
            discovery,raw,np.zeros_like(raw),components,metadata,run_audit,declaration,
            null_count=255,
        )
    except ValueError as exc:
        assert "not sealed" in str(exc)
    else:
        raise AssertionError("unsealed confirmation accepted")


def test_underresolved_confirmatory_alpha_fails_closed():
    raw,components,metadata,discovery,run_audit,declaration=_case()
    try:
        confirm_recursive_selection_v13(
            discovery,raw,np.zeros_like(raw),components,metadata,run_audit,declaration,
            confirmatory_alpha=0.001,null_count=255,
        )
    except ValueError as exc:
        assert "cannot resolve confirmatory alpha" in str(exc)
    else:
        raise AssertionError("under-resolved confirmation alpha accepted")


def test_target_derived_confirmatory_nuisance_fails_closed():
    raw,components,metadata,discovery,run_audit,declaration=_case()
    metadata["true_0"]["independent_of_confirmatory_target_fit"]=False
    try:
        confirm_recursive_selection_v13(
            discovery,raw,np.zeros_like(raw),components,metadata,run_audit,declaration,
            null_count=255,
        )
    except ValueError as exc:
        assert "target-derived" in str(exc)
    else:
        raise AssertionError("target-derived confirmatory nuisance accepted")


def test_run_independence_raw_commitment_mismatch_fails_closed():
    raw,components,metadata,discovery,run_audit,declaration=_case()
    run_audit["commitments"]["raw_sha256"]="c"*64
    try:
        confirm_recursive_selection_v13(
            discovery,raw,np.zeros_like(raw),components,metadata,run_audit,declaration,
            null_count=255,
        )
    except ValueError as exc:
        assert "RAW commitment mismatch" in str(exc)
    else:
        raise AssertionError("mismatched run-independence RAW accepted")


def test_invalid_run_independence_audit_fails_closed():
    raw,components,metadata,discovery,run_audit,declaration=_case()
    run_audit["policy"]["crossfit_valid_under_run_dependence_audit"]=False
    try:
        confirm_recursive_selection_v13(
            discovery,raw,np.zeros_like(raw),components,metadata,run_audit,declaration,
            null_count=255,
        )
    except ValueError as exc:
        assert "did not validate crossfit" in str(exc)
    else:
        raise AssertionError("invalid run-independence audit accepted")
