from __future__ import annotations

import copy
import math

import pytest

from tools.gremlin_connection_path_holonomy_v09 import (
    build_connection_path_integral_v09,
    build_derived_geometry_holonomy_v09,
    build_qhtri_connection_derived_lag_v09,
)
from tools.gremlin_dual_channel_entanglement_probe_v12 import (
    DualChannelEntanglementProbeError,
    build_dual_channel_entanglement_probe_v12,
    validate_dual_channel_entanglement_probe_v12,
)
from tools.gremlin_relational_coupling_energy_v11 import build_relational_coupling_energy_partition_v11
from tools.gremlin_relational_lambda_holonomy_v08 import (
    RelationalLambdaHolonomyError,
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
    derived = build_derived_geometry_holonomy_v09(energy=energy, path=path)
    qhtri = build_qhtri_connection_derived_lag_v09(
        derived_geometry=derived,
        oscillator_i="nu:i",
        oscillator_j="nu:j",
        n=1,
        m=1,
        theta_i_rad=0.0,
        theta_j_rad=0.0,
    )
    partition = build_relational_coupling_energy_partition_v11(energy=energy, path=path)
    return energy, path, qhtri, partition


def _probe(tau: float):
    energy, path, qhtri, partition = _stack(tau)
    receipt = build_dual_channel_entanglement_probe_v12(
        qhtri_receipt=qhtri,
        energy=energy,
        path=path,
        partition=partition,
    )
    assert validate_dual_channel_entanglement_probe_v12(
        receipt,
        qhtri_receipt=qhtri,
        energy=energy,
        path=path,
        partition=partition,
    )
    return receipt


def test_tau_zero_coherence_channel_reaches_first_maximum_and_torsion_is_zero():
    r = _probe(0.0)
    assert r["geometry_rate_ordering"] == "COHERENCE_CHANNEL_FASTER"
    assert r["coherence_first_maximum_status"] == "FINITE_FIRST_MAXIMUM"
    assert r["torsion_first_maximum_status"] == "UNREACHABLE_UNDER_ZERO_CHANNEL_COUPLING"
    assert float.fromhex(r["coherence_probe_concurrence_f64_hex"]) == pytest.approx(1.0)
    assert float.fromhex(r["torsion_probe_concurrence_f64_hex"]) == pytest.approx(0.0)


def test_tau_pi_reverses_channel_ordering():
    r = _probe(math.pi)
    assert r["geometry_rate_ordering"] == "TORSION_CHANNEL_FASTER"
    assert float.fromhex(r["coherence_probe_concurrence_f64_hex"]) == pytest.approx(0.0, abs=1e-12)
    assert float.fromhex(r["torsion_probe_concurrence_f64_hex"]) == pytest.approx(1.0)


def test_half_turn_partition_is_rate_degenerate():
    r = _probe(math.pi / 2.0)
    assert r["geometry_rate_ordering"] == "DEGENERATE_EQUAL_RATE"
    c = float.fromhex(r["coherence_probe_concurrence_f64_hex"])
    d = float.fromhex(r["torsion_probe_concurrence_f64_hex"])
    assert c == pytest.approx(math.sqrt(0.5))
    assert d == pytest.approx(math.sqrt(0.5))


def test_mirror_holonomies_swap_probe_concurrence_channels():
    a = _probe(math.pi / 3.0)
    b = _probe(2.0 * math.pi / 3.0)
    assert float.fromhex(a["coherence_probe_concurrence_f64_hex"]) == pytest.approx(
        float.fromhex(b["torsion_probe_concurrence_f64_hex"])
    )
    assert float.fromhex(a["torsion_probe_concurrence_f64_hex"]) == pytest.approx(
        float.fromhex(b["coherence_probe_concurrence_f64_hex"])
    )


def test_rate_ordering_does_not_promote_physical_channel_selection():
    r = _probe(0.2)
    assert r["rate_ordering_is_channel_selection"] is False
    assert r["channel_selection_status"] == "OPEN_REQUIRES_PHYSICAL_ATTRIBUTION_LAW"
    assert r["synchronization_entanglement_equivalence"] is False


def test_tampered_probe_fails_validation():
    energy, path, qhtri, partition = _stack(0.4)
    r = build_dual_channel_entanglement_probe_v12(
        qhtri_receipt=qhtri,
        energy=energy,
        path=path,
        partition=partition,
    )
    broken = copy.deepcopy(r)
    broken["geometry_rate_ordering"] = "TORSION_CHANNEL_FASTER"
    with pytest.raises(DualChannelEntanglementProbeError):
        validate_dual_channel_entanglement_probe_v12(
            broken,
            qhtri_receipt=qhtri,
            energy=energy,
            path=path,
            partition=partition,
        )


def test_qhtri_relation_lineage_tamper_is_rejected_upstream():
    energy, path, qhtri, partition = _stack(0.4)
    broken = copy.deepcopy(qhtri)
    broken["qhtri_holonomy_lag_v08"]["relation_id"] = "R:other"
    with pytest.raises(RelationalLambdaHolonomyError):
        build_dual_channel_entanglement_probe_v12(
            qhtri_receipt=broken,
            energy=energy,
            path=path,
            partition=partition,
        )
