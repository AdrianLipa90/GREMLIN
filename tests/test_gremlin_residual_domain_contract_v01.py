from gremlin_mcp.residual_domain_contract_v01 import evaluate_domain_readiness

def packet(cls="UNRESOLVED_STRUCTURED_CANDIDATE"):
    return {
        "schema":"GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_2",
        "classification":cls,
        "analysis_sha256":"a"*64,
        "commitments":{"raw_sha256":"b"*64,"model_sha256":"c"*64,"residual_sha256":"d"*64},
        "policy":{
            "raw_preserved":True,
            "residual_preserved":True,
            "analysis_copy_allowed":True,
            "destructive_denoising":False,
            "interpretation_last":True,
            "new_physics_from_residual_only":False,
            "time_fluctuation_claim_allowed":False,
        },
    }

def telescope_controls():
    return {k:True for k in (
        "lsf_or_spectral_response","wavelength_or_pixel_jitter","gain_drift",
        "bad_pixel_mask","detector_noise","timestamp_or_clock","sampling_alias",
        "known_spectral_template"
    )}

def microscope_controls():
    return {k:True for k in (
        "psf_or_otf","stage_xy_drift","focus_z_drift",
        "illumination_gain_or_bleaching","pixel_registration","detector_noise",
        "scan_clock_jitter","sample_motion_or_deformation","known_structure_template"
    )}

def test_telescope_complete_is_holdout_ready_not_physical():
    out=evaluate_domain_readiness(packet(),domain="telescope",controls=telescope_controls())
    assert out["status"]=="READY_FOR_DOMAIN_HOLDOUT_NOT_PHYSICAL_PROMOTION"
    assert out["control_complete"]
    assert out["claims"]["physical_signal_established"] is False

def test_microscope_requires_psf_stage_focus_and_scan_clock():
    c=microscope_controls(); c["psf_or_otf"]=False; c["scan_clock_jitter"]=False
    out=evaluate_domain_readiness(packet(),domain="microscope",controls=c)
    assert out["status"]=="DOMAIN_CONTROLS_INCOMPLETE"
    assert set(out["missing_controls"])=={"psf_or_otf","scan_clock_jitter"}

def test_systematic_class_is_not_promoted_even_with_complete_controls():
    out=evaluate_domain_readiness(packet("SYSTEMATIC_OR_INSTRUMENTAL_CANDIDATE"),domain="telescope",controls=telescope_controls())
    assert out["status"]=="DOMAIN_SYSTEMATIC_CANDIDATE"

def test_unsafe_packet_fails_closed():
    p=packet(); p["policy"]["destructive_denoising"]=True
    try: evaluate_domain_readiness(p,domain="microscope",controls=microscope_controls())
    except ValueError: pass
    else: raise AssertionError("unsafe packet accepted")
