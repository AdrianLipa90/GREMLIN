from __future__ import annotations

import copy
import math

import pytest

from tools.gremlin_connection_path_holonomy_v09 import build_connection_path_integral_v09
from tools.gremlin_relational_coupling_energy_v11 import (
    RelationalCouplingEnergyError,
    build_relational_coupling_energy_partition_v11,
    validate_relational_coupling_energy_partition_v11,
)
from tools.gremlin_relational_lambda_holonomy_v08 import (
    build_relational_lambda_energy_v08,
    build_relational_lambda_field_v08,
)

H = "a" * 64


def _energy(lambda_m2=1.1e-52, volume=1.0):
    field = build_relational_lambda_field_v08(
        relation_id="R:Lambda",
        spacetime_point_id="x:0",
        lambda_m2=lambda_m2,
        source_ref="source:imploding-universe3:p4",
        source_commitment=H,
        epistemic_status="MODEL_CANDIDATE",
    )
    return build_relational_lambda_energy_v08(field=field, support_volume_m3=volume)


def _path(energy, tau):
    return build_connection_path_integral_v09(
        energy=energy,
        geometry_adapter_id="adapter:spin-connection-projection:v1",
        metric_commitment="b" * 64,
        connection_commitment="c" * 64,
        loop_id="gamma:ij",
        connection_projection_rad_per_m=[tau],
        segment_lengths_m=[1.0],
        source_ref="geometry:upstream:witness",
        epistemic_status="MODEL_CANDIDATE",
    )


def test_zero_holonomy_puts_energy_in_coherence_channel():
    energy = _energy()
    path = _path(energy, 0.0)
    receipt = build_relational_coupling_energy_partition_v11(energy=energy, path=path)
    assert validate_relational_coupling_energy_partition_v11(receipt, energy=energy, path=path)
    source = float.fromhex(receipt["source_energy_j_f64_hex"])
    assert float.fromhex(receipt["coherence_C_h_f64_hex"]) == pytest.approx(1.0)
    assert float.fromhex(receipt["torsion_D_h_f64_hex"]) == pytest.approx(0.0)
    assert float.fromhex(receipt["coherence_channel_J_C_j_f64_hex"]) == pytest.approx(source)
    assert float.fromhex(receipt["torsion_channel_J_D_j_f64_hex"]) == pytest.approx(0.0)


def test_pi_holonomy_puts_energy_in_torsion_channel():
    energy = _energy()
    path = _path(energy, math.pi)
    receipt = build_relational_coupling_energy_partition_v11(energy=energy, path=path)
    source = float.fromhex(receipt["source_energy_j_f64_hex"])
    assert float.fromhex(receipt["coherence_C_h_f64_hex"]) == pytest.approx(0.0, abs=1e-15)
    assert float.fromhex(receipt["torsion_D_h_f64_hex"]) == pytest.approx(1.0, abs=1e-15)
    assert float.fromhex(receipt["torsion_channel_J_D_j_f64_hex"]) == pytest.approx(source)


def test_half_turn_partition_is_balanced_at_pi_over_two():
    energy = _energy()
    path = _path(energy, math.pi / 2.0)
    receipt = build_relational_coupling_energy_partition_v11(energy=energy, path=path)
    assert float.fromhex(receipt["coherence_C_h_f64_hex"]) == pytest.approx(0.5)
    assert float.fromhex(receipt["torsion_D_h_f64_hex"]) == pytest.approx(0.5)


def test_energy_partition_reconstructs_bound_source_energy():
    energy = _energy(volume=3.0)
    path = _path(energy, 0.731)
    receipt = build_relational_coupling_energy_partition_v11(energy=energy, path=path)
    source = float.fromhex(receipt["source_energy_j_f64_hex"])
    jc = float.fromhex(receipt["coherence_channel_J_C_j_f64_hex"])
    jd = float.fromhex(receipt["torsion_channel_J_D_j_f64_hex"])
    residual = float.fromhex(receipt["partition_residual_j_f64_hex"])
    assert jc + jd == pytest.approx(source)
    assert residual == pytest.approx(source - (jc + jd))


def test_full_turns_do_not_change_partition():
    energy = _energy()
    a = build_relational_coupling_energy_partition_v11(energy=energy, path=_path(energy, 0.2))
    b = build_relational_coupling_energy_partition_v11(energy=energy, path=_path(energy, 2.0 * math.pi + 0.2))
    assert float.fromhex(a["coherence_C_h_f64_hex"]) == pytest.approx(float.fromhex(b["coherence_C_h_f64_hex"]))
    assert float.fromhex(a["torsion_D_h_f64_hex"]) == pytest.approx(float.fromhex(b["torsion_D_h_f64_hex"]))


def test_channel_selection_remains_open():
    energy = _energy()
    receipt = build_relational_coupling_energy_partition_v11(energy=energy, path=_path(energy, 0.4))
    assert receipt["channel_selection_status"] == "OPEN"
    assert receipt["channel_candidates"] == ["COHERENCE_CHANNEL", "TORSION_CHANNEL"]
    assert receipt["parameter_free_given_bound_source_energy_and_holonomy"] is True
    assert receipt["entangling_channel_attribution_status"] == "OPEN"


def test_energy_lineage_mismatch_is_rejected():
    energy_a = _energy(lambda_m2=1.1e-52)
    energy_b = _energy(lambda_m2=2.2e-52)
    path_a = _path(energy_a, 0.3)
    with pytest.raises(RelationalCouplingEnergyError):
        build_relational_coupling_energy_partition_v11(energy=energy_b, path=path_a)


def test_tampered_channel_energy_fails_validation():
    energy = _energy()
    path = _path(energy, 0.9)
    receipt = build_relational_coupling_energy_partition_v11(energy=energy, path=path)
    broken = copy.deepcopy(receipt)
    broken["torsion_channel_J_D_j_f64_hex"] = (123.0).hex()
    with pytest.raises(RelationalCouplingEnergyError):
        validate_relational_coupling_energy_partition_v11(broken, energy=energy, path=path)


def test_negative_lambda_energy_preserves_signed_partition():
    energy = _energy(lambda_m2=-1.1e-52)
    path = _path(energy, math.pi / 3.0)
    receipt = build_relational_coupling_energy_partition_v11(energy=energy, path=path)
    source = float.fromhex(receipt["source_energy_j_f64_hex"])
    jc = float.fromhex(receipt["coherence_channel_J_C_j_f64_hex"])
    jd = float.fromhex(receipt["torsion_channel_J_D_j_f64_hex"])
    assert source < 0.0
    assert jc <= 0.0
    assert jd <= 0.0
    assert jc + jd == pytest.approx(source)
