from __future__ import annotations

import math
import copy
import pytest

from tools.gremlin_intention_mass_flavor_factorization_v18 import (
    IntentionMassFlavorFactorizationError,
    build_intention_mass_flavor_factorization_v18,
    validate_intention_mass_flavor_factorization_v18,
)
from tools.gremlin_three_flavor_neutrino_adapter_v15 import pmns_matrix_v15

PARAMS = dict(
    theta12_rad=math.radians(33.41),
    theta13_rad=math.radians(8.54),
    theta23_rad=math.radians(42.2),
    delta_cp_rad=math.radians(246.0),
    intention_source_ref="test:intention",
    phase_source_ref="test:relative-phase",
    pmns_source_ref="test:pdg-convention",
)


def _identity3():
    return [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def _decode_p(receipt):
    return [float.fromhex(receipt["R_flavor_distribution"][key]) for key in ("e", "mu", "tau")]


def test_identity_J_zero_phase_reduces_to_pmns_basis_change():
    receipt = build_intention_mass_flavor_factorization_v18(
        factorization_id="pmns-limit",
        intention_state=[1, 0, 0],
        intention_to_mass_map=_identity3(),
        mass_phases_rad=[0, 0, 0],
        **PARAMS,
    )
    u = pmns_matrix_v15(PARAMS["theta12_rad"], PARAMS["theta13_rad"], PARAMS["theta23_rad"], PARAMS["delta_cp_rad"])
    expected = [abs(u[a][0]) ** 2 for a in range(3)]
    actual = _decode_p(receipt)
    assert max(abs(actual[i] - expected[i]) for i in range(3)) < 2e-15
    assert receipt["extra_relational_hamiltonian_required_for_this_readout"] is False


def test_common_phase_shift_is_gauge_and_does_not_change_readout():
    kwargs = dict(
        factorization_id="global-phase",
        intention_state=[1 / math.sqrt(2), 1j / math.sqrt(2), 0],
        intention_to_mass_map=_identity3(),
        **PARAMS,
    )
    a = build_intention_mass_flavor_factorization_v18(mass_phases_rad=[0.2, 1.1, -0.4], **kwargs)
    b = build_intention_mass_flavor_factorization_v18(mass_phases_rad=[3.7, 4.6, 3.1], **kwargs)
    assert max(abs(x - y) for x, y in zip(_decode_p(a), _decode_p(b))) < 2e-14
    assert float.fromhex(a["global_phase_readout_delta_f64_hex"]) < 2e-14


def test_relative_phase_changes_flavor_readout_for_mass_superposition():
    kwargs = dict(
        factorization_id="relative-phase",
        intention_state=[1 / math.sqrt(2), 1 / math.sqrt(2), 0],
        intention_to_mass_map=_identity3(),
        **PARAMS,
    )
    a = build_intention_mass_flavor_factorization_v18(mass_phases_rad=[0, 0, 0], **kwargs)
    b = build_intention_mass_flavor_factorization_v18(mass_phases_rad=[0, math.pi / 2, 0], **kwargs)
    assert max(abs(x - y) for x, y in zip(_decode_p(a), _decode_p(b))) > 1e-3


def test_two_dimensional_intention_space_can_embed_isometrically_into_mass_space():
    receipt = build_intention_mass_flavor_factorization_v18(
        factorization_id="two-mode",
        intention_state=[math.sqrt(0.3), math.sqrt(0.7)],
        intention_to_mass_map=[[1, 0], [0, 1], [0, 0]],
        mass_phases_rad=[0.0, 0.7, 1.2],
        **PARAMS,
    )
    assert receipt["source_dimension"] == 2
    assert float.fromhex(receipt["J_isometry_residual_f64_hex"]) < 2e-12
    assert math.isclose(sum(_decode_p(receipt)), 1.0, abs_tol=3e-12)


def test_four_dimensional_intention_space_is_rejected_for_coherent_qutrit_embedding():
    with pytest.raises(IntentionMassFlavorFactorizationError):
        build_intention_mass_flavor_factorization_v18(
            factorization_id="rank-no-go",
            intention_state=[0.5, 0.5, 0.5, 0.5],
            intention_to_mass_map=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]],
            mass_phases_rad=[0, 0, 0],
            **PARAMS,
        )


def test_nonisometric_J_is_rejected():
    with pytest.raises(IntentionMassFlavorFactorizationError):
        build_intention_mass_flavor_factorization_v18(
            factorization_id="bad-J",
            intention_state=[1, 0, 0],
            intention_to_mass_map=[[0.5, 0, 0], [0, 0.5, 0], [0, 0, 0.5]],
            mass_phases_rad=[0, 0, 0],
            **PARAMS,
        )


def test_receipt_keeps_J_as_the_only_new_physical_mapping_debt():
    receipt = build_intention_mass_flavor_factorization_v18(
        factorization_id="debt",
        intention_state=[1, 0, 0],
        intention_to_mass_map=_identity3(),
        mass_phases_rad=[0.2, 0.5, 1.4],
        **PARAMS,
    )
    assert receipt["J_physical_origin_status"] == "OPEN"
    assert receipt["J_identity_special_case_status"] == "MATHEMATICAL_IDENTIFICATION_ONLY_NOT_PHYSICAL_PROOF"
    assert receipt["belzebub_verdict"] == "FACTORIZATION_SURVIVED_J_MECHANISM_OPEN"
    validate_intention_mass_flavor_factorization_v18(receipt)


def test_tamper_commitment_fails():
    receipt = build_intention_mass_flavor_factorization_v18(
        factorization_id="tamper",
        intention_state=[1, 0, 0],
        intention_to_mass_map=_identity3(),
        mass_phases_rad=[0, 0.2, 0.7],
        **PARAMS,
    )
    tampered = copy.deepcopy(receipt)
    tampered["J_physical_origin_status"] = "ESTABLISHED"
    with pytest.raises(IntentionMassFlavorFactorizationError):
        validate_intention_mass_flavor_factorization_v18(tampered)
