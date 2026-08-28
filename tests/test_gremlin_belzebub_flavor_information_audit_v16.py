from __future__ import annotations

import math
import copy
import pytest

from tools.gremlin_three_flavor_neutrino_adapter_v15 import (
    ADAPTER_SCHEMA,
    build_three_flavor_neutrino_propagation_v15,
)
from tools.gremlin_belzebub_flavor_information_audit_v16 import (
    BelzebubFlavorInformationAuditError,
    build_belzebub_flavor_information_audit_v16,
    phase_alias_witness_v16,
    shannon_bits_v16,
    uniform_prior_mutual_information_bits_v16,
    validate_belzebub_flavor_information_audit_v16,
)


def _enc(z: complex) -> dict[str, str]:
    return {"re_f64_hex": float(z.real).hex(), "im_f64_hex": float(z.imag).hex()}


def _mat(a):
    return [[_enc(complex(v)) for v in row] for row in a]


def _adapter():
    j = 1.0e-21
    h = [
        [0.0, j, 0.25j * j],
        [j, 0.0, 0.7 * j],
        [-0.25j * j, 0.7 * j, 0.0],
    ]
    return {
        "schema": ADAPTER_SCHEMA,
        "three_flavor_neutrino_hamiltonian_commitment": "1" * 64,
        "H_standard_j": _mat(h),
        "H_total_j": _mat(h),
    }


def test_identity_channel_has_zero_measurement_entropy_and_log3_mutual_information():
    adapter = _adapter()
    propagation = build_three_flavor_neutrino_propagation_v15(adapter=adapter, baseline_m=0.0)
    audit = build_belzebub_flavor_information_audit_v16(propagation=propagation, adapter=adapter, channel="standard")
    assert audit["belzebub_verdict"] == "SURVIVED_WITH_NARROWED_CLAIM"
    assert all(float.fromhex(v) == 0.0 for v in audit["flavor_measurement_entropy_bits_by_initial_flavor"].values())
    assert math.isclose(float.fromhex(audit["uniform_prior_I_XY_bits"]), math.log2(3.0), rel_tol=0.0, abs_tol=2e-15)


def test_nontrivial_unitary_channel_survives_all_firewalls():
    adapter = _adapter()
    propagation = build_three_flavor_neutrino_propagation_v15(adapter=adapter, baseline_m=1.0e-5)
    audit = build_belzebub_flavor_information_audit_v16(propagation=propagation, adapter=adapter, channel="standard")
    assert audit["belzebub_verdict"] == "SURVIVED_WITH_NARROWED_CLAIM"
    assert all(audit["checks"].values())
    assert audit["measurement_entropy_equals_quantum_entropy"] is False
    assert audit["information_creation_by_unitary_oscillation"] is False


def test_uniform_random_channel_has_zero_mutual_information():
    channel = [[1.0 / 3.0] * 3 for _ in range(3)]
    info = uniform_prior_mutual_information_bits_v16(channel)
    assert math.isclose(info["H_Y_bits"], math.log2(3.0), abs_tol=2e-15)
    assert math.isclose(info["H_Y_given_X_bits"], math.log2(3.0), abs_tol=2e-15)
    assert abs(info["I_XY_bits"]) < 2e-15


def test_phase_alias_is_explicit_noninjectivity_witness():
    witness = phase_alias_witness_v16(0.37)
    assert abs(witness["delta_1_rad"] - witness["delta_2_rad"]) > 1e-6
    assert witness["probability_difference"] < 2e-15


def test_shannon_rejects_unnormalized_values():
    with pytest.raises(BelzebubFlavorInformationAuditError):
        shannon_bits_v16([0.2, 0.2, 0.2])


def test_receipt_tamper_fails_validation():
    adapter = _adapter()
    propagation = build_three_flavor_neutrino_propagation_v15(adapter=adapter, baseline_m=1.0e-5)
    audit = build_belzebub_flavor_information_audit_v16(propagation=propagation, adapter=adapter, channel="standard")
    validate_belzebub_flavor_information_audit_v16(audit, propagation=propagation, adapter=adapter)
    tampered = copy.deepcopy(audit)
    tampered["information_creation_by_unitary_oscillation"] = True
    with pytest.raises(BelzebubFlavorInformationAuditError):
        validate_belzebub_flavor_information_audit_v16(tampered, propagation=propagation, adapter=adapter)
