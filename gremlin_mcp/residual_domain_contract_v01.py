from __future__ import annotations
from collections.abc import Mapping
from typing import Any

RESIDUAL_SCHEMA = "GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_2"
DOMAIN_SCHEMA = "GREMLIN_RESIDUAL_DOMAIN_CONTRACT_V0_1"

DOMAIN_CONTROLS = {
    "telescope": (
        "lsf_or_spectral_response",
        "wavelength_or_pixel_jitter",
        "gain_drift",
        "bad_pixel_mask",
        "detector_noise",
        "timestamp_or_clock",
        "sampling_alias",
        "known_spectral_template",
    ),
    "microscope": (
        "psf_or_otf",
        "stage_xy_drift",
        "focus_z_drift",
        "illumination_gain_or_bleaching",
        "pixel_registration",
        "detector_noise",
        "scan_clock_jitter",
        "sample_motion_or_deformation",
        "known_structure_template",
    ),
}
_ALLOWED = {
    "STOCHASTIC_BACKGROUND_COMPATIBLE",
    "SYSTEMATIC_OR_INSTRUMENTAL_CANDIDATE",
    "SYSTEMATIC_DRIFT_CANDIDATE",
    "KNOWN_MODEL_STRUCTURE_CANDIDATE",
    "PERSISTENT_OFFSET_CANDIDATE",
    "UNRESOLVED_STRUCTURED_CANDIDATE",
    "UNRESOLVED_RESIDUAL",
}

def validate_residual_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, Mapping) or packet.get("schema") != RESIDUAL_SCHEMA:
        raise ValueError("unsupported residual packet")
    if packet.get("classification") not in _ALLOWED:
        raise ValueError("unsupported residual classification")
    policy = packet.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("missing residual policy")
    required = {
        "raw_preserved": True,
        "residual_preserved": True,
        "destructive_denoising": False,
        "interpretation_last": True,
        "new_physics_from_residual_only": False,
        "time_fluctuation_claim_allowed": False,
    }
    for key, expected in required.items():
        if policy.get(key) is not expected:
            raise ValueError(f"unsafe residual policy: {key}")
    return dict(packet)

def evaluate_domain_readiness(
    packet: Mapping[str, Any], *, domain: str, controls: Mapping[str, bool]
) -> dict[str, Any]:
    p = validate_residual_packet(packet)
    d = str(domain).strip().lower()
    if d not in DOMAIN_CONTROLS:
        raise ValueError("unsupported domain")
    if not isinstance(controls, Mapping):
        raise ValueError("controls must be mapping")
    required = DOMAIN_CONTROLS[d]
    missing = [name for name in required if controls.get(name) is not True]
    cls = p["classification"]
    if cls in ("SYSTEMATIC_OR_INSTRUMENTAL_CANDIDATE", "SYSTEMATIC_DRIFT_CANDIDATE"):
        status = "DOMAIN_SYSTEMATIC_CANDIDATE"
    elif missing:
        status = "DOMAIN_CONTROLS_INCOMPLETE"
    elif cls == "STOCHASTIC_BACKGROUND_COMPATIBLE":
        status = "DOMAIN_STOCHASTIC_COMPATIBLE"
    elif cls == "KNOWN_MODEL_STRUCTURE_CANDIDATE":
        status = "DOMAIN_KNOWN_STRUCTURE_CANDIDATE"
    elif cls in ("UNRESOLVED_STRUCTURED_CANDIDATE", "PERSISTENT_OFFSET_CANDIDATE"):
        status = "READY_FOR_DOMAIN_HOLDOUT_NOT_PHYSICAL_PROMOTION"
    else:
        status = "DOMAIN_UNRESOLVED"
    return {
        "schema": DOMAIN_SCHEMA,
        "domain": d,
        "classification": cls,
        "status": status,
        "required_controls": list(required),
        "missing_controls": missing,
        "control_complete": not missing,
        "residual_analysis_sha256": p.get("analysis_sha256"),
        "commitments": dict(p.get("commitments") or {}),
        "claims": {
            "physical_signal_established": False,
            "new_physics_established": False,
            "time_fluctuation_established": False,
            "domain_interpretation_established": False,
        },
    }

__all__ = ["RESIDUAL_SCHEMA","DOMAIN_SCHEMA","DOMAIN_CONTROLS","validate_residual_packet","evaluate_domain_readiness"]
