from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

from tools.gremlin_connection_path_holonomy_v09 import (
    build_connection_path_integral_v09,
    build_derived_geometry_holonomy_v09,
    build_qhtri_connection_derived_lag_v09,
    validate_qhtri_connection_derived_lag_v09,
)
from tools.gremlin_relational_lambda_holonomy_v08 import validate_relational_lambda_energy_v08

TWO_PI = 2.0 * math.pi

GEOMETRY_SCHEMA = "GREMLIN_MAXSYM_SPIN_GEOMETRY_V0_10"
GEOMETRY_DOMAIN = b"GREMLIN-MAXSYM-SPIN-GEOMETRY/v0.10\x00"
METRIC_DOMAIN = b"GREMLIN-MAXSYM-METRIC/v0.10\x00"
TETRAD_DOMAIN = b"GREMLIN-MAXSYM-TETRAD/v0.10\x00"
CONNECTION_DOMAIN = b"GREMLIN-MAXSYM-SPIN-CONNECTION/v0.10\x00"
QHTRI_SCHEMA = "GREMLIN_MAXSYM_SPIN_QHTRI_BRIDGE_V0_10"
QHTRI_DOMAIN = b"GREMLIN-MAXSYM-SPIN-QHTRI-BRIDGE/v0.10\x00"


class MaxSymSpinGeometryError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(domain: bytes, value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise MaxSymSpinGeometryError(f"{name} must be finite")
    return x


def _positive(value: Any, name: str) -> float:
    x = _finite(value, name)
    if x <= 0.0:
        raise MaxSymSpinGeometryError(f"{name} must be positive")
    return x


def _hash64(value: Any, name: str) -> str:
    text = str(value)
    if len(text) != 64:
        raise MaxSymSpinGeometryError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise MaxSymSpinGeometryError(f"{name} must be hexadecimal") from exc
    return text


def _from_hex(value: Any, name: str) -> float:
    try:
        return _finite(float.fromhex(str(value)), name)
    except ValueError as exc:
        raise MaxSymSpinGeometryError(f"{name} must be a binary64 hex float") from exc


def _section_functions(k: float, r: float) -> tuple[float, float, float]:
    if k > 0.0:
        root = math.sqrt(k)
        x = root * r
        if not (0.0 < x < math.pi):
            raise MaxSymSpinGeometryError("positive-curvature calibration radius must lie before the antipode")
        s = math.sin(x) / root
        c = math.cos(x)
        one_minus_c = 2.0 * math.sin(0.5 * x) ** 2
    elif k < 0.0:
        root = math.sqrt(-k)
        x = root * r
        s = math.sinh(x) / root
        c = math.cosh(x)
        one_minus_c = -2.0 * math.sinh(0.5 * x) ** 2
    else:
        s = r
        c = 1.0
        one_minus_c = 0.0
    if not math.isfinite(s) or s <= 0.0:
        raise MaxSymSpinGeometryError("section circumference radius must be positive and finite")
    return s, c, one_minus_c


def build_maxsym_spin_geometry_v010(*, energy: Mapping[str, Any], radius_m: Any) -> dict[str, Any]:
    validate_relational_lambda_energy_v08(energy)
    r = _positive(radius_m, "radius_m")
    lam = _from_hex(energy["lambda_R_m_minus_2_f64_hex"], "lambda_R")
    k = lam / 3.0
    s, c, one_minus_c = _section_functions(k, r)

    area = math.pi * r * r if k == 0.0 else TWO_PI * one_minus_c / k
    vector_holonomy = TWO_PI * one_minus_c
    spin_half_holonomy = 0.5 * vector_holonomy
    circumference = TWO_PI * s
    spin_half_projection_per_m = 0.5 * one_minus_c / s

    metric_core = {
        "coordinates": ["r", "phi"],
        "g_rr_f64_hex": 1.0.hex(),
        "g_phiphi_m2_f64_hex": (s * s).hex(),
        "section_radius_S_K_m_f64_hex": s.hex(),
        "sectional_curvature_K_m_minus_2_f64_hex": k.hex(),
    }
    metric_commitment = _seal(METRIC_DOMAIN, metric_core)

    tetrad_core = {
        "coframe": ["e^r=dr", "e^phi=S_K(r)*dphi"],
        "e_r_dr_f64_hex": 1.0.hex(),
        "e_phi_dphi_m_f64_hex": s.hex(),
        "metric_commitment": metric_commitment,
    }
    tetrad_commitment = _seal(TETRAD_DOMAIN, tetrad_core)

    connection_core = {
        "tetrad_commitment": tetrad_commitment,
        "cartan_equation": "de^a+omega^a_b wedge e^b=0",
        "omega_rphi_dphi_raw_f64_hex": (-c).hex(),
        "flat_polar_gauge_baseline_dphi_f64_hex": (-1.0).hex(),
        "curvature_excess_dphi_f64_hex": one_minus_c.hex(),
        "spin_half_u1_dphi_f64_hex": (0.5 * one_minus_c).hex(),
        "spin_half_projection_rad_per_m_f64_hex": spin_half_projection_per_m.hex(),
    }
    connection_commitment = _seal(CONNECTION_DOMAIN, connection_core)

    core = {
        "schema": GEOMETRY_SCHEMA,
        "relation_id": str(energy["relation_id"]),
        "spacetime_point_id": str(energy["spacetime_point_id"]),
        "relational_lambda_energy_commitment": str(energy["relational_lambda_energy_commitment"]),
        "geometry_law": "4D_MAXIMALLY_SYMMETRIC_EINSTEIN_CALIBRATION_K=Lambda_R/3",
        "section_metric_law": "ds2=dr2+S_K(r)^2*dphi2",
        "radius_m_f64_hex": r.hex(),
        "lambda_R_m_minus_2_f64_hex": lam.hex(),
        "sectional_curvature_K_m_minus_2_f64_hex": k.hex(),
        "ricci_scalar_4d_m_minus_2_f64_hex": (4.0 * lam).hex(),
        "ricci_scalar_section_2d_m_minus_2_f64_hex": (2.0 * k).hex(),
        "section_radius_S_K_m_f64_hex": s.hex(),
        "S_K_prime_f64_hex": c.hex(),
        "one_minus_S_K_prime_f64_hex": one_minus_c.hex(),
        "disk_area_m2_f64_hex": area.hex(),
        "circle_circumference_m_f64_hex": circumference.hex(),
        "vector_curvature_holonomy_rad_f64_hex": vector_holonomy.hex(),
        "spin_half_curvature_holonomy_rad_f64_hex": spin_half_holonomy.hex(),
        "stokes_law": "Phi_vector=K*A=2*pi*(1-S_K_prime)",
        "spin_half_law": "tau_half=Phi_vector/2",
        "polar_frame_gauge_baseline_removed": True,
        "flat_limit_holonomy_zero": True,
        "metric": metric_core,
        "metric_commitment": metric_commitment,
        "tetrad": tetrad_core,
        "tetrad_commitment": tetrad_commitment,
        "spin_connection": connection_core,
        "connection_commitment": connection_commitment,
        "connection_source": "TORSION_FREE_CARTAN_FROM_BOUND_TETRAD",
        "phase_projection": "SPIN_HALF_U1_CURVATURE_EXCESS",
        "entanglement_status": "OPEN_REQUIRES_JOINT_QUANTUM_WITNESS",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "MAXSYM_SPIN_GEOMETRY_DERIVED",
    }
    return {**core, "maxsym_spin_geometry_commitment": _seal(GEOMETRY_DOMAIN, core)}


def validate_maxsym_spin_geometry_v010(geometry: Mapping[str, Any]) -> bool:
    if geometry.get("schema") != GEOMETRY_SCHEMA:
        raise MaxSymSpinGeometryError("unsupported maxsym spin geometry schema")
    _hash64(geometry.get("relational_lambda_energy_commitment"), "relational_lambda_energy_commitment")
    r = _positive(_from_hex(geometry.get("radius_m_f64_hex"), "radius_m"), "radius_m")
    lam = _from_hex(geometry.get("lambda_R_m_minus_2_f64_hex"), "lambda_R")
    k = _from_hex(geometry.get("sectional_curvature_K_m_minus_2_f64_hex"), "K")
    if k.hex() != (lam / 3.0).hex():
        raise MaxSymSpinGeometryError("K=Lambda_R/3 closure mismatch")
    s, c, one_minus_c = _section_functions(k, r)
    if _from_hex(geometry.get("section_radius_S_K_m_f64_hex"), "S_K").hex() != s.hex():
        raise MaxSymSpinGeometryError("S_K mismatch")
    if _from_hex(geometry.get("S_K_prime_f64_hex"), "S_K_prime").hex() != c.hex():
        raise MaxSymSpinGeometryError("S_K derivative mismatch")
    if _from_hex(geometry.get("one_minus_S_K_prime_f64_hex"), "one_minus_S_K_prime").hex() != one_minus_c.hex():
        raise MaxSymSpinGeometryError("curvature-excess coefficient mismatch")
    expected_area = math.pi * r * r if k == 0.0 else TWO_PI * one_minus_c / k
    expected_vector = TWO_PI * one_minus_c
    expected_half = 0.5 * expected_vector
    if _from_hex(geometry.get("disk_area_m2_f64_hex"), "disk_area").hex() != expected_area.hex():
        raise MaxSymSpinGeometryError("disk area mismatch")
    if _from_hex(geometry.get("vector_curvature_holonomy_rad_f64_hex"), "vector_holonomy").hex() != expected_vector.hex():
        raise MaxSymSpinGeometryError("vector holonomy mismatch")
    if _from_hex(geometry.get("spin_half_curvature_holonomy_rad_f64_hex"), "spin_half_holonomy").hex() != expected_half.hex():
        raise MaxSymSpinGeometryError("spin-half holonomy mismatch")
    if (k * expected_area).hex() != expected_vector.hex() and k != 0.0:
        raise MaxSymSpinGeometryError("Stokes curvature-area closure mismatch")
    if _from_hex(geometry.get("ricci_scalar_4d_m_minus_2_f64_hex"), "R4").hex() != (4.0 * lam).hex():
        raise MaxSymSpinGeometryError("4D Ricci scalar closure mismatch")
    if _from_hex(geometry.get("ricci_scalar_section_2d_m_minus_2_f64_hex"), "R2").hex() != (2.0 * k).hex():
        raise MaxSymSpinGeometryError("2D Ricci scalar closure mismatch")

    metric = geometry.get("metric")
    tetrad = geometry.get("tetrad")
    connection = geometry.get("spin_connection")
    if not isinstance(metric, Mapping) or not isinstance(tetrad, Mapping) or not isinstance(connection, Mapping):
        raise MaxSymSpinGeometryError("metric/tetrad/connection lineage missing")
    if _hash64(geometry.get("metric_commitment"), "metric_commitment") != _seal(METRIC_DOMAIN, metric):
        raise MaxSymSpinGeometryError("metric commitment mismatch")
    if _hash64(geometry.get("tetrad_commitment"), "tetrad_commitment") != _seal(TETRAD_DOMAIN, tetrad):
        raise MaxSymSpinGeometryError("tetrad commitment mismatch")
    if _hash64(geometry.get("connection_commitment"), "connection_commitment") != _seal(CONNECTION_DOMAIN, connection):
        raise MaxSymSpinGeometryError("connection commitment mismatch")
    if connection.get("tetrad_commitment") != geometry.get("tetrad_commitment"):
        raise MaxSymSpinGeometryError("connection-to-tetrad lineage mismatch")
    expected_projection = 0.5 * one_minus_c / s
    if _from_hex(connection.get("spin_half_projection_rad_per_m_f64_hex"), "spin_half_projection").hex() != expected_projection.hex():
        raise MaxSymSpinGeometryError("spin-half path projection mismatch")

    expected = {
        "geometry_law": "4D_MAXIMALLY_SYMMETRIC_EINSTEIN_CALIBRATION_K=Lambda_R/3",
        "section_metric_law": "ds2=dr2+S_K(r)^2*dphi2",
        "stokes_law": "Phi_vector=K*A=2*pi*(1-S_K_prime)",
        "spin_half_law": "tau_half=Phi_vector/2",
        "polar_frame_gauge_baseline_removed": True,
        "flat_limit_holonomy_zero": True,
        "connection_source": "TORSION_FREE_CARTAN_FROM_BOUND_TETRAD",
        "phase_projection": "SPIN_HALF_U1_CURVATURE_EXCESS",
        "entanglement_status": "OPEN_REQUIRES_JOINT_QUANTUM_WITNESS",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "MAXSYM_SPIN_GEOMETRY_DERIVED",
    }
    for key, value in expected.items():
        if geometry.get(key) != value:
            raise MaxSymSpinGeometryError(f"geometry contract mismatch: {key}")
    supplied = _hash64(geometry.get("maxsym_spin_geometry_commitment"), "maxsym_spin_geometry_commitment")
    core = dict(geometry)
    core.pop("maxsym_spin_geometry_commitment", None)
    if supplied != _seal(GEOMETRY_DOMAIN, core):
        raise MaxSymSpinGeometryError("maxsym spin geometry commitment mismatch")
    return True


def build_maxsym_spin_qhtri_bridge_v010(
    *,
    energy: Mapping[str, Any],
    geometry: Mapping[str, Any],
    oscillator_i: str,
    oscillator_j: str,
    n: int,
    m: int,
    theta_i_rad: Any,
    theta_j_rad: Any,
) -> dict[str, Any]:
    validate_relational_lambda_energy_v08(energy)
    validate_maxsym_spin_geometry_v010(geometry)
    if str(geometry["relational_lambda_energy_commitment"]) != str(energy["relational_lambda_energy_commitment"]):
        raise MaxSymSpinGeometryError("energy-to-geometry lineage mismatch")
    connection = geometry["spin_connection"]
    projection = _from_hex(connection["spin_half_projection_rad_per_m_f64_hex"], "spin_half_projection")
    circumference = _from_hex(geometry["circle_circumference_m_f64_hex"], "circumference")
    path = build_connection_path_integral_v09(
        energy=energy,
        geometry_adapter_id="MAXSYM_SPIN_GEOMETRY_V0_10",
        metric_commitment=str(geometry["metric_commitment"]),
        connection_commitment=str(geometry["connection_commitment"]),
        loop_id=f"circle:r={geometry['radius_m_f64_hex']}",
        connection_projection_rad_per_m=[projection],
        segment_lengths_m=[circumference],
        source_ref=str(geometry["maxsym_spin_geometry_commitment"]),
        epistemic_status="MODEL_CANDIDATE",
    )
    derived = build_derived_geometry_holonomy_v09(energy=energy, path=path)
    qhtri = build_qhtri_connection_derived_lag_v09(
        derived_geometry=derived,
        oscillator_i=oscillator_i,
        oscillator_j=oscillator_j,
        n=n,
        m=m,
        theta_i_rad=theta_i_rad,
        theta_j_rad=theta_j_rad,
    )
    validate_qhtri_connection_derived_lag_v09(qhtri)
    tau_path = float.fromhex(qhtri["qhtri_holonomy_lag_v08"]["tau_holonomy_rad_f64_hex"])
    expected_tau_unwrapped = _from_hex(geometry["spin_half_curvature_holonomy_rad_f64_hex"], "spin_half_holonomy")
    from tools.gremlin_relational_lambda_holonomy_v08 import wrap_pi
    if tau_path.hex() != wrap_pi(expected_tau_unwrapped).hex():
        raise MaxSymSpinGeometryError("spin-half geometry to QHTRI tau closure mismatch")
    core = {
        "schema": QHTRI_SCHEMA,
        "maxsym_spin_geometry_commitment": str(geometry["maxsym_spin_geometry_commitment"]),
        "connection_path_integral_v09": path,
        "qhtri_connection_derived_lag_v09": qhtri,
        "tau_origin": "LAMBDA_TO_MAXSYM_METRIC_TO_TETRAD_TO_SPIN_CONNECTION_TO_CURVATURE_HOLONOMY",
        "manual_tau_present": False,
        "geometry_ansatz_status": "DECLARED_MAXIMALLY_SYMMETRIC_CALIBRATION",
        "entanglement_status": "OPEN_REQUIRES_JOINT_QUANTUM_WITNESS",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "MAXSYM_SPIN_QHTRI_BRIDGE_BOUND",
    }
    return {**core, "maxsym_spin_qhtri_bridge_commitment": _seal(QHTRI_DOMAIN, core)}


def validate_maxsym_spin_qhtri_bridge_v010(receipt: Mapping[str, Any]) -> bool:
    if receipt.get("schema") != QHTRI_SCHEMA:
        raise MaxSymSpinGeometryError("unsupported maxsym spin QHTRI bridge schema")
    _hash64(receipt.get("maxsym_spin_geometry_commitment"), "maxsym_spin_geometry_commitment")
    path = receipt.get("connection_path_integral_v09")
    qhtri = receipt.get("qhtri_connection_derived_lag_v09")
    if not isinstance(path, Mapping) or not isinstance(qhtri, Mapping):
        raise MaxSymSpinGeometryError("embedded path/QHTRI lineage missing")
    validate_qhtri_connection_derived_lag_v09(qhtri)
    if qhtri.get("tau_origin") != "CONNECTION_PATH_INTEGRAL":
        raise MaxSymSpinGeometryError("embedded QHTRI tau provenance mismatch")
    expected = {
        "tau_origin": "LAMBDA_TO_MAXSYM_METRIC_TO_TETRAD_TO_SPIN_CONNECTION_TO_CURVATURE_HOLONOMY",
        "manual_tau_present": False,
        "geometry_ansatz_status": "DECLARED_MAXIMALLY_SYMMETRIC_CALIBRATION",
        "entanglement_status": "OPEN_REQUIRES_JOINT_QUANTUM_WITNESS",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "MAXSYM_SPIN_QHTRI_BRIDGE_BOUND",
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise MaxSymSpinGeometryError(f"QHTRI bridge contract mismatch: {key}")
    supplied = _hash64(receipt.get("maxsym_spin_qhtri_bridge_commitment"), "maxsym_spin_qhtri_bridge_commitment")
    core = dict(receipt)
    core.pop("maxsym_spin_qhtri_bridge_commitment", None)
    if supplied != _seal(QHTRI_DOMAIN, core):
        raise MaxSymSpinGeometryError("maxsym spin QHTRI bridge commitment mismatch")
    return True
