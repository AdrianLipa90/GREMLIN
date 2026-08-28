from __future__ import annotations

import copy
import math
import pytest

from tools.gremlin_J_identifiability_no_go_v19 import (
    JIdentifiabilityNoGoError,
    build_J_identifiability_no_go_v19,
    validate_J_identifiability_no_go_v19,
)

BASE = dict(
    intention_state=[1.0, 0.0, 0.0],
    mass_phases_rad=[0.0, 0.43, 1.17],
    theta12_rad=math.radians(33.41),
    theta13_rad=math.radians(8.54),
    theta23_rad=math.radians(42.2),
    delta_cp_rad=math.radians(246.0),
    intention_source_ref="Theory_of_Everything.pdf:R(S,I)",
    phase_source_ref="IDT:relative_phase_transport",
    pmns_source_ref="GREMLIN:v1.5:PDG_PMNS_convention",
    historical_toe_source_ref="Theory_of_Everything.pdf:July-2025",
    corrected_eft_source_ref="noema_fermionic_intention_fields_corrected(4).pdf:May-2026",
)


def test_two_structurally_admissible_J_give_different_flavor_readouts():
    receipt = build_J_identifiability_no_go_v19(audit_id="nonunique", alternative_rotation_rad=0.37, **BASE)
    assert receipt["both_candidates_pass_v18_factorization"] is True
    assert receipt["different_observable_readout"] is True
    assert float.fromhex(receipt["max_flavor_probability_delta_f64_hex"]) > 1e-4
    assert receipt["belzebub_verdict"] == "CURRENT_PREMISES_DO_NOT_IDENTIFY_J"


def test_continuous_family_has_nontrivial_members_at_multiple_angles():
    deltas = []
    for theta in (0.11, 0.29, 0.73):
        receipt = build_J_identifiability_no_go_v19(audit_id=f"family-{theta}", alternative_rotation_rad=theta, **BASE)
        deltas.append(float.fromhex(receipt["max_flavor_probability_delta_f64_hex"]))
        assert receipt["admissible_family_for_dim3"] == "U(3)"
        assert receipt["belzebub_verdict"] == "CURRENT_PREMISES_DO_NOT_IDENTIFY_J"
    assert len({round(x, 12) for x in deltas}) == 3


def test_tiny_but_nontrivial_rotation_is_accepted_when_above_guard():
    receipt = build_J_identifiability_no_go_v19(audit_id="small", alternative_rotation_rad=1e-5, **BASE)
    assert receipt["both_candidates_pass_v18_factorization"] is True


def test_zero_rotation_is_rejected_as_nonuniqueness_witness():
    with pytest.raises(JIdentifiabilityNoGoError):
        build_J_identifiability_no_go_v19(audit_id="zero", alternative_rotation_rad=0.0, **BASE)


def test_no_go_scope_is_only_current_premises_not_absolute_impossibility():
    receipt = build_J_identifiability_no_go_v19(audit_id="scope", alternative_rotation_rad=0.41, **BASE)
    assert receipt["no_go_scope"] == "NON_IDENTIFIABILITY_FROM_CURRENT_PREMISES_ONLY"
    assert "additional" in receipt["future_escape_condition"]
    assert receipt["historical_toe_evidence_status"]["symbolic_SU3"].startswith("REPRESENTATION_PRESENT")


def test_receipt_tamper_fails():
    receipt = build_J_identifiability_no_go_v19(audit_id="tamper", alternative_rotation_rad=0.37, **BASE)
    validate_J_identifiability_no_go_v19(receipt)
    tampered = copy.deepcopy(receipt)
    tampered["pmns_role"] = "SELECTS_J"
    with pytest.raises(JIdentifiabilityNoGoError):
        validate_J_identifiability_no_go_v19(tampered)
