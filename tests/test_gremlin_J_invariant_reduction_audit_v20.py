from __future__ import annotations

import copy
import pytest

from tools.gremlin_J_invariant_reduction_audit_v20 import (
    JInvariantReductionAuditError,
    build_J_invariant_reduction_audit_v20,
    global_u1_probability_blindness_v20,
    residual_phase_dimension_after_nondegenerate_mass_v20,
    stabilizer_dimension_from_multiplicities_v20,
    validate_J_invariant_reduction_audit_v20,
)

BASE = dict(
    audit_id="J-v20",
    delta_m21_sq_eV2=7.42e-5,
    delta_m31_sq_eV2=2.517e-3,
    mass_source_ref="GREMLIN:v1.5:three-flavor-mass-spectrum",
    relational_holonomy_source_ref="GREMLIN:v0.8:U1_PHASE_PROJECTION",
    neutrinotime_source_ref="Neutrinotime14.pdf:Eq27-29+numerical-pseudocode",
    resonance_source_ref="Theory_of_Everything.pdf:R(S,I)+mass-resonance",
    corrected_eft_source_ref="noema_fermionic_intention_fields_corrected(2).pdf:sections6-7",
)


def test_mass_spectrum_reduces_u3_to_three_phases_but_not_unique():
    receipt = build_J_invariant_reduction_audit_v20(**BASE)
    mass = receipt["candidates"]["nondegenerate_mass_spectrum"]
    assert mass["stabilizer"] == "U(1)^3"
    assert mass["stabilizer_dimension"] == 3
    assert mass["projective_dimension"] == 2
    assert mass["verdict"] == "PARTIAL_REDUCTION"


def test_scalar_holonomy_and_global_berry_phase_do_not_reduce_or_change_probabilities():
    receipt = build_J_invariant_reduction_audit_v20(**BASE)
    assert receipt["candidates"]["relational_lambda_holonomy_v08"]["verdict"] == "INSUFFICIENT_SCALAR_U1"
    temporal = receipt["candidates"]["neutrinotime_global_berry_implementation"]
    assert temporal["verdict"] == "INSUFFICIENT_GLOBAL_PHASE"
    assert float.fromhex(temporal["probability_blindness_max_delta_f64_hex"]) < 1e-15
    assert global_u1_probability_blindness_v20([1+0j, 0.2+0.3j, -0.1j], 1.234) < 1e-15


def test_connected_second_operator_collapses_relative_phase_ambiguity():
    connected = [[0,1,0],[1,0,1],[0,1,0]]
    disconnected = [[0,1,0],[1,0,0],[0,0,0]]
    c = residual_phase_dimension_after_nondegenerate_mass_v20(connected)
    d = residual_phase_dimension_after_nondegenerate_mass_v20(disconnected)
    assert c["connected_components"] == 1
    assert c["projective_phase_dimension"] == 0
    assert c["projectively_identifying"] is True
    assert d["connected_components"] == 2
    assert d["projective_phase_dimension"] == 1
    assert d["projectively_identifying"] is False


def test_stabilizer_dimension_formula_for_three_modes():
    assert stabilizer_dimension_from_multiplicities_v20([1,1,1]) == 3
    assert stabilizer_dimension_from_multiplicities_v20([2,1]) == 5
    assert stabilizer_dimension_from_multiplicities_v20([3]) == 9
    with pytest.raises(JInvariantReductionAuditError):
        stabilizer_dimension_from_multiplicities_v20([1,1])


def test_receipt_validates_and_tamper_fails():
    receipt = build_J_invariant_reduction_audit_v20(**BASE)
    assert validate_J_invariant_reduction_audit_v20(receipt)
    tampered = copy.deepcopy(receipt)
    tampered["strongest_current_reduction"] = "invented"
    with pytest.raises(JInvariantReductionAuditError):
        validate_J_invariant_reduction_audit_v20(tampered)


def test_degenerate_mass_control_does_not_claim_nondegenerate_reduction():
    params = dict(BASE)
    params["delta_m31_sq_eV2"] = params["delta_m21_sq_eV2"]
    receipt = build_J_invariant_reduction_audit_v20(**params)
    mass = receipt["candidates"]["nondegenerate_mass_spectrum"]
    assert mass["source_status"] == "DEGENERATE_OR_UNRESOLVED"
    assert mass["verdict"] == "NO_REDUCTION_CERTIFIED"
