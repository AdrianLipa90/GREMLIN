from __future__ import annotations

import copy
import math

import pytest

from tools.gremlin_connection_path_holonomy_v09 import (
    ConnectionPathHolonomyError,
    build_connection_path_integral_v09,
    build_derived_geometry_holonomy_v09,
    build_qhtri_connection_derived_lag_v09,
    validate_connection_path_integral_v09,
    validate_derived_geometry_holonomy_v09,
    validate_qhtri_connection_derived_lag_v09,
)
from tools.gremlin_relational_lambda_holonomy_v08 import (
    build_relational_lambda_energy_v08,
    build_relational_lambda_field_v08,
    wrap_pi,
)

H = "a" * 64


def _energy():
    field = build_relational_lambda_field_v08(
        relation_id="R:Lambda",
        spacetime_point_id="x:0",
        lambda_m2=1.1e-52,
        source_ref="source:imploding-universe3:p4",
        source_commitment=H,
        epistemic_status="MODEL_CANDIDATE",
    )
    return build_relational_lambda_energy_v08(field=field, support_volume_m3=1.0)


def _path(omega=(0.2, 0.3), ds=(1.0, 2.0)):
    return build_connection_path_integral_v09(
        energy=_energy(),
        geometry_adapter_id="adapter:spin-connection-projection:v1",
        metric_commitment="b" * 64,
        connection_commitment="c" * 64,
        loop_id="gamma:ij",
        connection_projection_rad_per_m=omega,
        segment_lengths_m=ds,
        source_ref="geometry:upstream:witness",
        epistemic_status="MODEL_CANDIDATE",
    )


def test_path_integral_derives_tau_without_manual_parameter():
    p = _path()
    assert validate_connection_path_integral_v09(p)
    assert float.fromhex(p["connection_line_integral_rad_f64_hex"]) == pytest.approx(0.8)
    assert float.fromhex(p["holonomy_phase_wrapped_rad_f64_hex"]) == pytest.approx(0.8)
    assert p["lag_parameter_origin"] == "DERIVED_FROM_BOUND_CONNECTION_PATH"
    assert p["manual_tau_present"] is False


def test_path_split_preserves_holonomy_for_constant_projection():
    a = _path(omega=(0.4,), ds=(3.0,))
    b = _path(omega=(0.4, 0.4, 0.4), ds=(1.0, 1.0, 1.0))
    assert float.fromhex(a["holonomy_phase_wrapped_rad_f64_hex"]) == pytest.approx(
        float.fromhex(b["holonomy_phase_wrapped_rad_f64_hex"])
    )


def test_path_wraps_full_turns():
    p = _path(omega=(2.0 * math.pi + 0.25,), ds=(1.0,))
    assert float.fromhex(p["holonomy_phase_wrapped_rad_f64_hex"]) == pytest.approx(0.25)


def test_open_loop_is_rejected():
    with pytest.raises(ConnectionPathHolonomyError):
        build_connection_path_integral_v09(
            energy=_energy(),
            geometry_adapter_id="a",
            metric_commitment="b" * 64,
            connection_commitment="c" * 64,
            loop_id="open",
            connection_projection_rad_per_m=[0.2],
            segment_lengths_m=[1.0],
            source_ref="s",
            epistemic_status="CANDIDATE",
            closed_loop=False,
        )


def test_negative_length_and_shape_mismatch_are_rejected():
    with pytest.raises(ConnectionPathHolonomyError):
        _path(omega=(0.2,), ds=(-1.0,))
    with pytest.raises(ConnectionPathHolonomyError):
        _path(omega=(0.2, 0.3), ds=(1.0,))


def test_tampered_integral_fails_validation():
    p = _path()
    broken = copy.deepcopy(p)
    broken["connection_line_integral_rad_f64_hex"] = (1.7).hex()
    with pytest.raises(ConnectionPathHolonomyError):
        validate_connection_path_integral_v09(broken)


def test_derived_geometry_uses_path_integral_as_holonomy_input():
    energy = _energy()
    p = build_connection_path_integral_v09(
        energy=energy,
        geometry_adapter_id="adapter",
        metric_commitment="b" * 64,
        connection_commitment="c" * 64,
        loop_id="gamma",
        connection_projection_rad_per_m=[0.5],
        segment_lengths_m=[2.0],
        source_ref="geometry:witness",
        epistemic_status="MODEL_CANDIDATE",
    )
    d = build_derived_geometry_holonomy_v09(energy=energy, path=p)
    assert validate_derived_geometry_holonomy_v09(d)
    g = d["relational_geometry_holonomy_v08"]
    assert float.fromhex(g["holonomy_phase_wrapped_rad_f64_hex"]) == pytest.approx(1.0)
    assert d["tau_origin"] == "CONNECTION_PATH_INTEGRAL"
    assert d["manual_tau_present"] is False


def test_qhtri_epsilon_inherits_connection_derived_tau():
    energy = _energy()
    p = build_connection_path_integral_v09(
        energy=energy,
        geometry_adapter_id="adapter",
        metric_commitment="b" * 64,
        connection_commitment="c" * 64,
        loop_id="gamma",
        connection_projection_rad_per_m=[0.3],
        segment_lengths_m=[2.0],
        source_ref="geometry:witness",
        epistemic_status="MODEL_CANDIDATE",
    )
    d = build_derived_geometry_holonomy_v09(energy=energy, path=p)
    q = build_qhtri_connection_derived_lag_v09(
        derived_geometry=d,
        oscillator_i="nu:i",
        oscillator_j="nu:j",
        n=2,
        m=3,
        theta_i_rad=1.1,
        theta_j_rad=0.2,
    )
    assert validate_qhtri_connection_derived_lag_v09(q)
    inner = q["qhtri_holonomy_lag_v08"]
    tau = float.fromhex(inner["tau_holonomy_rad_f64_hex"])
    epsilon = float.fromhex(inner["epsilon_qhtri_rad_f64_hex"])
    assert tau == pytest.approx(0.6)
    assert epsilon == pytest.approx(wrap_pi(2 * 1.1 - 3 * 0.2 - tau))
    assert q["tau_origin"] == "CONNECTION_PATH_INTEGRAL"
    assert q["entanglement_status"] == "OPEN_REQUIRES_QUANTUM_WITNESS"


def test_exact_winding_identity_is_preserved_without_gcd_normalization():
    energy = _energy()
    p = build_connection_path_integral_v09(
        energy=energy,
        geometry_adapter_id="adapter",
        metric_commitment="b" * 64,
        connection_commitment="c" * 64,
        loop_id="gamma",
        connection_projection_rad_per_m=[0.0],
        segment_lengths_m=[1.0],
        source_ref="geometry:witness",
        epistemic_status="MODEL_CANDIDATE",
    )
    d = build_derived_geometry_holonomy_v09(energy=energy, path=p)
    q = build_qhtri_connection_derived_lag_v09(
        derived_geometry=d,
        oscillator_i="i",
        oscillator_j="j",
        n=2,
        m=4,
        theta_i_rad=0.1,
        theta_j_rad=0.2,
    )
    inner = q["qhtri_holonomy_lag_v08"]
    assert inner["n"] == 2
    assert inner["m"] == 4
