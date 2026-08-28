from __future__ import annotations

import math
import pytest

from tools.gremlin_intention_flavor_bridge_v17 import (
    IntentionFlavorBridgeError,
    build_bridge_comparison_v17,
    build_cptp_bridge_v17,
    build_isometry_bridge_v17,
    build_postselected_projection_bridge_v17,
)


def test_three_dimensional_identity_isometry_recovers_historical_basis_overlap():
    psi = [1 / math.sqrt(2), 1j / math.sqrt(2), 0.0]
    b = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    receipt = build_isometry_bridge_v17(bridge_id="identity-qutrit", matrix_b=b, intention_state=psi, source_space_ref="test:H_I")
    assert receipt["unitary_onto_flavor_space"] is True
    p = {k: float.fromhex(v) for k, v in receipt["R_flavor_distribution"].items()}
    assert math.isclose(p["nu_e"], 0.5, abs_tol=2e-15)
    assert math.isclose(p["nu_mu"], 0.5, abs_tol=2e-15)
    assert math.isclose(p["nu_tau"], 0.0, abs_tol=2e-15)


def test_two_dimensional_isometry_embeds_into_flavor_qutrit():
    psi = [math.sqrt(0.3), math.sqrt(0.7)]
    b = [[1, 0], [0, 1], [0, 0]]
    receipt = build_isometry_bridge_v17(bridge_id="two-to-three", matrix_b=b, intention_state=psi, source_space_ref="test:H_I2")
    assert receipt["source_dimension"] == 2
    assert receipt["unitary_onto_flavor_space"] is False
    assert receipt["belzebub_verdict"] == "SURVIVED_TYPED_COHERENT_BRIDGE"


def test_four_dimensional_source_cannot_isometrically_embed_into_qutrit():
    psi = [0.5, 0.5, 0.5, 0.5]
    b = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]]
    with pytest.raises(IntentionFlavorBridgeError):
        build_isometry_bridge_v17(bridge_id="impossible-rank", matrix_b=b, intention_state=psi, source_space_ref="test:H_I4")


def test_projection_is_explicitly_postselected_not_deterministic():
    psi = [1 / math.sqrt(3)] * 3
    b = [[1, 0, 0], [0, 0.5, 0], [0, 0, 0.25]]
    receipt = build_postselected_projection_bridge_v17(bridge_id="filter", matrix_b=b, intention_state=psi, source_space_ref="test:H_I")
    success = float.fromhex(receipt["branch_success_probability_f64_hex"])
    assert 0.0 < success < 1.0
    assert receipt["deterministic_channel_admitted"] is False
    assert receipt["postselection_required"] is True
    assert receipt["belzebub_verdict"] == "SURVIVED_ONLY_AS_POSTSELECTED_BRANCH"


def test_cptp_amplitude_damping_channel_is_trace_preserving():
    gamma = 0.36
    k0 = [[1, 0, 0], [0, math.sqrt(1 - gamma), 0], [0, 0, 1]]
    k1 = [[0, math.sqrt(gamma), 0], [0, 0, 0], [0, 0, 0]]
    receipt = build_cptp_bridge_v17(bridge_id="qutrit-damping", kraus_ops=[k0, k1], intention_state=[0, 1, 0], source_space_ref="test:H_I")
    p = {k: float.fromhex(v) for k, v in receipt["R_flavor_distribution"].items()}
    assert math.isclose(sum(p.values()), 1.0, abs_tol=2e-15)
    assert math.isclose(p["nu_e"], gamma, abs_tol=2e-15)
    assert math.isclose(p["nu_mu"], 1 - gamma, abs_tol=2e-15)
    assert receipt["single_kraus_isometry_special_case"] is False


def test_incomplete_kraus_set_is_rejected():
    k0 = [[0.5, 0, 0], [0, 0.5, 0], [0, 0, 0.5]]
    with pytest.raises(IntentionFlavorBridgeError):
        build_cptp_bridge_v17(bridge_id="bad-channel", kraus_ops=[k0], intention_state=[1, 0, 0], source_space_ref="test:H_I")


def test_comparison_does_not_silently_select_a_physical_bridge():
    psi = [1, 0, 0]
    identity = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    iso = build_isometry_bridge_v17(bridge_id="iso", matrix_b=identity, intention_state=psi, source_space_ref="test")
    proj = build_postselected_projection_bridge_v17(bridge_id="proj", matrix_b=[[0.5, 0, 0], [0, 0.5, 0], [0, 0, 0.5]], intention_state=psi, source_space_ref="test")
    cptp = build_cptp_bridge_v17(bridge_id="cptp", kraus_ops=[identity], intention_state=psi, source_space_ref="test")
    comparison = build_bridge_comparison_v17(isometry=iso, projection=proj, cptp=cptp)
    assert comparison["canonical_bridge_selected"] is False
    assert comparison["belzebub_verdict"] == "TYPE_ERROR_REPAIRED_MECHANISM_OPEN"
    assert comparison["global_unitary_possible_only_if_dim_HI_eq_3"] is True
