from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from tools.gremlin_relational_lambda_holonomy_v08 import (
    build_qhtri_holonomy_lag_v08,
    build_relational_geometry_holonomy_v08,
    validate_relational_lambda_energy_v08,
    wrap_pi,
)

PATH_SCHEMA = "GREMLIN_CONNECTION_PATH_INTEGRAL_V0_9"
PATH_DOMAIN = b"GREMLIN-CONNECTION-PATH-INTEGRAL/v0.9\x00"
DERIVED_GEOMETRY_SCHEMA = "GREMLIN_DERIVED_GEOMETRY_HOLONOMY_V0_9"
DERIVED_GEOMETRY_DOMAIN = b"GREMLIN-DERIVED-GEOMETRY-HOLONOMY/v0.9\x00"
QHTRI_DERIVED_SCHEMA = "GREMLIN_QHTRI_CONNECTION_DERIVED_LAG_V0_9"
QHTRI_DERIVED_DOMAIN = b"GREMLIN-QHTRI-CONNECTION-DERIVED-LAG/v0.9\x00"


class ConnectionPathHolonomyError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(domain: bytes, value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise ConnectionPathHolonomyError(f"{name} must be finite")
    return x


def _nonempty(value: Any, name: str) -> str:
    text = str(value)
    if not text:
        raise ConnectionPathHolonomyError(f"{name} must be non-empty")
    return text


def _hash64(value: Any, name: str) -> str:
    text = _nonempty(value, name)
    if len(text) != 64:
        raise ConnectionPathHolonomyError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise ConnectionPathHolonomyError(f"{name} must be hexadecimal") from exc
    return text


def _from_hex(value: Any, name: str) -> float:
    try:
        return _finite(float.fromhex(str(value)), name)
    except ValueError as exc:
        raise ConnectionPathHolonomyError(f"{name} must be a binary64 hex float") from exc


def build_connection_path_integral_v09(
    *,
    energy: Mapping[str, Any],
    geometry_adapter_id: str,
    metric_commitment: str,
    connection_commitment: str,
    loop_id: str,
    connection_projection_rad_per_m: Sequence[Any],
    segment_lengths_m: Sequence[Any],
    source_ref: str,
    epistemic_status: str,
    closed_loop: bool = True,
) -> dict[str, Any]:
    validate_relational_lambda_energy_v08(energy)
    if closed_loop is not True:
        raise ConnectionPathHolonomyError("holonomy derivation requires a declared closed loop")
    omega = [_finite(v, "connection_projection_rad_per_m") for v in connection_projection_rad_per_m]
    ds = [_finite(v, "segment_length_m") for v in segment_lengths_m]
    if not omega or len(omega) != len(ds):
        raise ConnectionPathHolonomyError("connection projection and segment arrays must be equal non-empty sequences")
    if any(v < 0.0 for v in ds):
        raise ConnectionPathHolonomyError("segment lengths must be non-negative")
    integral = math.fsum(w * length for w, length in zip(omega, ds))
    wrapped = wrap_pi(integral)
    core = {
        "schema": PATH_SCHEMA,
        "relation_id": str(energy["relation_id"]),
        "spacetime_point_id": str(energy["spacetime_point_id"]),
        "relational_lambda_energy_commitment": str(energy["relational_lambda_energy_commitment"]),
        "geometry_adapter_id": _nonempty(geometry_adapter_id, "geometry_adapter_id"),
        "metric_commitment": _hash64(metric_commitment, "metric_commitment"),
        "connection_commitment": _hash64(connection_commitment, "connection_commitment"),
        "loop_id": _nonempty(loop_id, "loop_id"),
        "closed_loop": True,
        "connection_projection_rad_per_m_f64_hex": [v.hex() for v in omega],
        "segment_lengths_m_f64_hex": [v.hex() for v in ds],
        "connection_line_integral_rad_f64_hex": integral.hex(),
        "holonomy_phase_wrapped_rad_f64_hex": wrapped.hex(),
        "integral_law": "Phi_hol=sum_k(omega_parallel_k*ds_k)",
        "phase_law": "tau_holonomy=wrap_pi(Phi_hol)",
        "lag_parameter_origin": "DERIVED_FROM_BOUND_CONNECTION_PATH",
        "manual_tau_present": False,
        "source_ref": _nonempty(source_ref, "source_ref"),
        "epistemic_status": _nonempty(epistemic_status, "epistemic_status"),
        "entanglement_status": "OPEN_REQUIRES_QUANTUM_WITNESS",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "CONNECTION_PATH_HOLONOMY_DERIVED",
    }
    return {**core, "connection_path_integral_commitment": _seal(PATH_DOMAIN, core)}


def validate_connection_path_integral_v09(path: Mapping[str, Any]) -> bool:
    if path.get("schema") != PATH_SCHEMA:
        raise ConnectionPathHolonomyError("unsupported connection path schema")
    for key in ("relation_id", "spacetime_point_id", "geometry_adapter_id", "loop_id", "source_ref", "epistemic_status"):
        _nonempty(path.get(key), key)
    for key in ("relational_lambda_energy_commitment", "metric_commitment", "connection_commitment"):
        _hash64(path.get(key), key)
    if path.get("closed_loop") is not True:
        raise ConnectionPathHolonomyError("connection path must remain closed")
    omega_raw = path.get("connection_projection_rad_per_m_f64_hex")
    ds_raw = path.get("segment_lengths_m_f64_hex")
    if not isinstance(omega_raw, list) or not isinstance(ds_raw, list) or not omega_raw or len(omega_raw) != len(ds_raw):
        raise ConnectionPathHolonomyError("connection path arrays malformed")
    omega = [_from_hex(v, "connection_projection") for v in omega_raw]
    ds = [_from_hex(v, "segment_length") for v in ds_raw]
    if any(v < 0.0 for v in ds):
        raise ConnectionPathHolonomyError("segment lengths must be non-negative")
    expected_integral = math.fsum(w * length for w, length in zip(omega, ds))
    expected_wrapped = wrap_pi(expected_integral)
    if _from_hex(path.get("connection_line_integral_rad_f64_hex"), "connection_line_integral").hex() != expected_integral.hex():
        raise ConnectionPathHolonomyError("connection line integral mismatch")
    if _from_hex(path.get("holonomy_phase_wrapped_rad_f64_hex"), "holonomy_phase").hex() != expected_wrapped.hex():
        raise ConnectionPathHolonomyError("derived holonomy phase mismatch")
    if path.get("integral_law") != "Phi_hol=sum_k(omega_parallel_k*ds_k)" or path.get("phase_law") != "tau_holonomy=wrap_pi(Phi_hol)":
        raise ConnectionPathHolonomyError("connection path law mismatch")
    if path.get("lag_parameter_origin") != "DERIVED_FROM_BOUND_CONNECTION_PATH" or path.get("manual_tau_present") is not False:
        raise ConnectionPathHolonomyError("manual tau firewall mismatch")
    expected = {
        "entanglement_status": "OPEN_REQUIRES_QUANTUM_WITNESS",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "CONNECTION_PATH_HOLONOMY_DERIVED",
    }
    for key, value in expected.items():
        if path.get(key) != value:
            raise ConnectionPathHolonomyError(f"connection path status mismatch: {key}")
    supplied = _hash64(path.get("connection_path_integral_commitment"), "connection_path_integral_commitment")
    core = dict(path)
    core.pop("connection_path_integral_commitment", None)
    if supplied != _seal(PATH_DOMAIN, core):
        raise ConnectionPathHolonomyError("connection path commitment mismatch")
    return True


def build_derived_geometry_holonomy_v09(*, energy: Mapping[str, Any], path: Mapping[str, Any]) -> dict[str, Any]:
    validate_relational_lambda_energy_v08(energy)
    validate_connection_path_integral_v09(path)
    if str(path["relational_lambda_energy_commitment"]) != str(energy["relational_lambda_energy_commitment"]):
        raise ConnectionPathHolonomyError("Lambda-energy lineage mismatch")
    raw_phase = _from_hex(path["connection_line_integral_rad_f64_hex"], "connection_line_integral")
    geometry = build_relational_geometry_holonomy_v08(
        energy=energy,
        geometry_adapter_id=str(path["geometry_adapter_id"]),
        metric_commitment=str(path["metric_commitment"]),
        connection_commitment=str(path["connection_commitment"]),
        loop_id=str(path["loop_id"]),
        holonomy_phase_rad=raw_phase,
        source_ref=str(path["source_ref"]),
        epistemic_status=str(path["epistemic_status"]),
    )
    core = {
        "schema": DERIVED_GEOMETRY_SCHEMA,
        "connection_path_integral_commitment": str(path["connection_path_integral_commitment"]),
        "relational_geometry_holonomy_v08": geometry,
        "tau_origin": "CONNECTION_PATH_INTEGRAL",
        "manual_tau_present": False,
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "DERIVED_GEOMETRY_HOLONOMY_BOUND",
    }
    return {**core, "derived_geometry_holonomy_commitment": _seal(DERIVED_GEOMETRY_DOMAIN, core)}


def validate_derived_geometry_holonomy_v09(receipt: Mapping[str, Any]) -> bool:
    if receipt.get("schema") != DERIVED_GEOMETRY_SCHEMA:
        raise ConnectionPathHolonomyError("unsupported derived geometry schema")
    _hash64(receipt.get("connection_path_integral_commitment"), "connection_path_integral_commitment")
    geometry = receipt.get("relational_geometry_holonomy_v08")
    if not isinstance(geometry, Mapping):
        raise ConnectionPathHolonomyError("embedded v0.8 geometry missing")
    from tools.gremlin_relational_lambda_holonomy_v08 import validate_relational_geometry_holonomy_v08
    validate_relational_geometry_holonomy_v08(geometry)
    if receipt.get("tau_origin") != "CONNECTION_PATH_INTEGRAL" or receipt.get("manual_tau_present") is not False:
        raise ConnectionPathHolonomyError("derived geometry tau provenance mismatch")
    if receipt.get("execution_status") != "RESEARCH_BINDING_ONLY" or receipt.get("canon_status") != "CANDIDATE" or receipt.get("status") != "DERIVED_GEOMETRY_HOLONOMY_BOUND":
        raise ConnectionPathHolonomyError("derived geometry status mismatch")
    supplied = _hash64(receipt.get("derived_geometry_holonomy_commitment"), "derived_geometry_holonomy_commitment")
    core = dict(receipt)
    core.pop("derived_geometry_holonomy_commitment", None)
    if supplied != _seal(DERIVED_GEOMETRY_DOMAIN, core):
        raise ConnectionPathHolonomyError("derived geometry commitment mismatch")
    return True


def build_qhtri_connection_derived_lag_v09(
    *,
    derived_geometry: Mapping[str, Any],
    oscillator_i: str,
    oscillator_j: str,
    n: int,
    m: int,
    theta_i_rad: Any,
    theta_j_rad: Any,
) -> dict[str, Any]:
    validate_derived_geometry_holonomy_v09(derived_geometry)
    geometry = derived_geometry["relational_geometry_holonomy_v08"]
    qhtri = build_qhtri_holonomy_lag_v08(
        geometry=geometry,
        oscillator_i=oscillator_i,
        oscillator_j=oscillator_j,
        n=n,
        m=m,
        theta_i_rad=theta_i_rad,
        theta_j_rad=theta_j_rad,
    )
    core = {
        "schema": QHTRI_DERIVED_SCHEMA,
        "derived_geometry_holonomy_commitment": str(derived_geometry["derived_geometry_holonomy_commitment"]),
        "qhtri_holonomy_lag_v08": qhtri,
        "tau_origin": "CONNECTION_PATH_INTEGRAL",
        "manual_tau_present": False,
        "entanglement_status": "OPEN_REQUIRES_JOINT_QUANTUM_WITNESS",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "QHTRI_CONNECTION_DERIVED_LAG_BOUND",
    }
    return {**core, "qhtri_connection_derived_commitment": _seal(QHTRI_DERIVED_DOMAIN, core)}


def validate_qhtri_connection_derived_lag_v09(receipt: Mapping[str, Any]) -> bool:
    if receipt.get("schema") != QHTRI_DERIVED_SCHEMA:
        raise ConnectionPathHolonomyError("unsupported QHTRI connection-derived schema")
    _hash64(receipt.get("derived_geometry_holonomy_commitment"), "derived_geometry_holonomy_commitment")
    qhtri = receipt.get("qhtri_holonomy_lag_v08")
    if not isinstance(qhtri, Mapping):
        raise ConnectionPathHolonomyError("embedded QHTRI v0.8 receipt missing")
    from tools.gremlin_relational_lambda_holonomy_v08 import validate_qhtri_holonomy_lag_v08
    validate_qhtri_holonomy_lag_v08(qhtri)
    if receipt.get("tau_origin") != "CONNECTION_PATH_INTEGRAL" or receipt.get("manual_tau_present") is not False:
        raise ConnectionPathHolonomyError("QHTRI derived tau provenance mismatch")
    expected = {
        "entanglement_status": "OPEN_REQUIRES_JOINT_QUANTUM_WITNESS",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "QHTRI_CONNECTION_DERIVED_LAG_BOUND",
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise ConnectionPathHolonomyError(f"QHTRI connection-derived status mismatch: {key}")
    supplied = _hash64(receipt.get("qhtri_connection_derived_commitment"), "qhtri_connection_derived_commitment")
    core = dict(receipt)
    core.pop("qhtri_connection_derived_commitment", None)
    if supplied != _seal(QHTRI_DERIVED_DOMAIN, core):
        raise ConnectionPathHolonomyError("QHTRI connection-derived commitment mismatch")
    return True
