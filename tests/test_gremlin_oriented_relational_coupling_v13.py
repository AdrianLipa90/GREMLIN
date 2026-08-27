from __future__ import annotations

import copy
import math

import pytest

from tools.gremlin_connection_path_holonomy_v09 import build_connection_path_integral_v09
from tools.gremlin_oriented_relational_coupling_v13 import (
    OrientedRelationalCouplingError,
    build_oriented_relational_coupling_v13,
    validate_oriented_relational_coupling_v13,
)
from tools.gremlin_relational_coupling_energy_v11 import build_relational_coupling_energy_partition_v11
from tools.gremlin_relational_lambda_holonomy_v08 import (
    build_relational_lambda_energy_v08,
    build_relational_lambda_field_v08,
)

H = "a" * 64


def _stack(tau: float):
    field = build_relational_lambda_field_v08(
        relation_id="R:Lambda",
        spacetime_point_id="x:0",
        lambda_m2=1.1e-52,
        source_ref="source:model",
        source_commitment=H,
        epistemic_status="MODEL_CANDIDATE",
    )
    energy = build_relational_lambda_energy_v08(field=field, support_volume_m3=1.0)
    path = build_connection_path_integral_v09(
        energy=energy,
        geometry_adapter_id="adapter:test",
        metric_commitment="b" * 64,
        connection_commitment="c" * 64,
        loop_id="gamma:test",
        connection_projection_rad_per_m=[tau],
        segment_lengths_m=[1.0],
        source_ref="geometry:test",
        epistemic_status="MODEL_CANDIDATE",
    )
    partition = build_relational_coupling_energy_partition_v11(energy=energy, path=path)
    receipt = build_oriented_relational_coupling_v13(energy=energy, path=path, partition=partition)
    assert validate_oriented_relational_coupling_v13(receipt, energy=energy, path=path, partition=partition)
    return energy, path, partition, receipt


def test_tau_zero_is_positive_real_axis():
    _, _, _, r = _stack(0.0)
    assert float.fromhex(r["holonomy_unit_real_cos_tau_f64_hex"]) == pytest.approx(1.0)
    assert float.fromhex(r["holonomy_unit_imag_sin_tau_f64_hex"]) == pytest.approx(0.0)
    assert r["holonomy_orientation"] == "AXIAL_OR_ZERO_HOLONOMY_ORIENTATION"
    assert float.fromhex(r["normalized_channel_imbalance_f64_hex"]) == pytest.approx(1.0)


def test_tau_pi_is_negative_real_axis_and_reverses_channel_imbalance():
    _, _, _, r = _stack(math.pi)
    assert float.fromhex(r["holonomy_unit_real_cos_tau_f64_hex"]) == pytest.approx(-1.0)
    assert float.fromhex(r["normalized_channel_imbalance_f64_hex"]) == pytest.approx(-1.0)
    assert r["holonomy_orientation"] == "AXIAL_OR_ZERO_HOLONOMY_ORIENTATION"


def test_positive_and_negative_quarter_turn_retain_orientation_sign():
    _, _, _, pos = _stack(math.pi / 2.0)
    _, _, _, neg = _stack(-math.pi / 2.0)
    assert pos["holonomy_orientation"] == "POSITIVE_HOLONOMY_ORIENTATION"
    assert neg["holonomy_orientation"] == "NEGATIVE_HOLONOMY_ORIENTATION"
    assert float.fromhex(pos["oriented_coupling_real_j_f64_hex"]) == pytest.approx(
        float.fromhex(neg["oriented_coupling_real_j_f64_hex"]), abs=1e-24
    )
    assert float.fromhex(pos["oriented_coupling_imag_j_f64_hex"]) == pytest.approx(
        -float.fromhex(neg["oriented_coupling_imag_j_f64_hex"])
    )


def test_complex_magnitude_closes_to_source_energy_magnitude():
    _, _, partition, r = _stack(0.73)
    source = abs(float.fromhex(partition["source_energy_j_f64_hex"]))
    magnitude = float.fromhex(r["oriented_coupling_magnitude_j_f64_hex"])
    assert magnitude == pytest.approx(source, rel=1e-14)


def test_v11_partition_imbalance_is_real_projection():
    _, _, partition, r = _stack(1.1)
    j_c = float.fromhex(partition["coherence_channel_J_C_j_f64_hex"])
    j_d = float.fromhex(partition["torsion_channel_J_D_j_f64_hex"])
    real = float.fromhex(r["oriented_coupling_real_j_f64_hex"])
    assert j_c - j_d == pytest.approx(real, rel=1e-14, abs=1e-300)


def test_orientation_retained_without_promoting_channel_or_entanglement_claims():
    _, _, _, r = _stack(0.5)
    assert r["parameter_free_given_v1_1_partition_and_holonomy"] is True
    assert r["orientation_sign_retained"] is True
    assert r["channel_selection_status"] == "OPEN_REQUIRES_PHYSICAL_ATTRIBUTION_LAW"
    assert r["hermitian_operator_embedding_status"] == "OPEN_REQUIRES_EXPLICIT_OPERATOR_PAIRING"
    assert r["entanglement_attribution_status"] == "OPEN_REQUIRES_HERMITIAN_EVOLUTION_WITNESS"


def test_tampered_oriented_component_fails_validation():
    energy, path, partition, r = _stack(0.5)
    broken = copy.deepcopy(r)
    broken["oriented_coupling_imag_j_f64_hex"] = (0.0).hex()
    with pytest.raises(OrientedRelationalCouplingError):
        validate_oriented_relational_coupling_v13(broken, energy=energy, path=path, partition=partition)
