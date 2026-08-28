from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

C_SI = 299_792_458.0
G_SI = 6.67430e-11
TWO_PI = 2.0 * math.pi

RELATIONAL_LAMBDA_FIELD_SCHEMA = "GREMLIN_RELATIONAL_LAMBDA_FIELD_V0_8"
RELATIONAL_LAMBDA_FIELD_DOMAIN = b"GREMLIN-RELATIONAL-LAMBDA-FIELD/v0.8\x00"
RELATIONAL_LAMBDA_ENERGY_SCHEMA = "GREMLIN_RELATIONAL_LAMBDA_ENERGY_V0_8"
RELATIONAL_LAMBDA_ENERGY_DOMAIN = b"GREMLIN-RELATIONAL-LAMBDA-ENERGY/v0.8\x00"
RELATIONAL_GEOMETRY_HOLONOMY_SCHEMA = "GREMLIN_RELATIONAL_GEOMETRY_HOLONOMY_V0_8"
RELATIONAL_GEOMETRY_HOLONOMY_DOMAIN = b"GREMLIN-RELATIONAL-GEOMETRY-HOLONOMY/v0.8\x00"
QHTRI_HOLONOMY_LAG_SCHEMA = "GREMLIN_QHTRI_HOLONOMY_LAG_V0_8"
QHTRI_HOLONOMY_LAG_DOMAIN = b"GREMLIN-QHTRI-HOLONOMY-LAG/v0.8\x00"


class RelationalLambdaHolonomyError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(domain: bytes, value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    text = str(value)
    if not text:
        raise RelationalLambdaHolonomyError(f"{name} must be non-empty")
    return text


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise RelationalLambdaHolonomyError(f"{name} must be finite")
    return x


def _positive(value: Any, name: str) -> float:
    x = _finite(value, name)
    if x <= 0.0:
        raise RelationalLambdaHolonomyError(f"{name} must be positive")
    return x


def _hash64(value: Any, name: str) -> str:
    text = _nonempty(value, name)
    if len(text) != 64:
        raise RelationalLambdaHolonomyError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise RelationalLambdaHolonomyError(f"{name} must be hexadecimal") from exc
    return text


def _from_hex(value: Any, name: str) -> float:
    try:
        x = float.fromhex(str(value))
    except (TypeError, ValueError) as exc:
        raise RelationalLambdaHolonomyError(f"{name} must be a binary64 hex float") from exc
    return _finite(x, name)


def wrap_pi(value: Any) -> float:
    x = _finite(value, "phase_rad")
    y = (x + math.pi) % TWO_PI - math.pi
    if y == -0.0:
        return 0.0
    return y


def build_relational_lambda_field_v08(
    *,
    relation_id: str,
    spacetime_point_id: str,
    lambda_m2: Any,
    source_ref: str,
    source_commitment: str,
    epistemic_status: str,
) -> dict[str, Any]:
    lam = _finite(lambda_m2, "lambda_m2")
    core = {
        "schema": RELATIONAL_LAMBDA_FIELD_SCHEMA,
        "relation_id": _nonempty(relation_id, "relation_id"),
        "spacetime_point_id": _nonempty(spacetime_point_id, "spacetime_point_id"),
        "lambda_R_m_minus_2_f64_hex": lam.hex(),
        "field_units": "m^-2",
        "field_semantics": "RELATIONAL_SCALAR_FIELD_CANDIDATE",
        "source_ref": _nonempty(source_ref, "source_ref"),
        "source_commitment": _hash64(source_commitment, "source_commitment"),
        "epistemic_status": _nonempty(epistemic_status, "epistemic_status"),
        "geometry_derivation_status": "OPEN",
        "holonomy_derivation_status": "OPEN",
        "entanglement_status": "OPEN_REQUIRES_QUANTUM_WITNESS",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "RELATIONAL_LAMBDA_FIELD_BOUND",
    }
    return {**core, "relational_lambda_field_commitment": _seal(RELATIONAL_LAMBDA_FIELD_DOMAIN, core)}


def validate_relational_lambda_field_v08(field: Mapping[str, Any]) -> bool:
    if field.get("schema") != RELATIONAL_LAMBDA_FIELD_SCHEMA:
        raise RelationalLambdaHolonomyError("unsupported relational Lambda field schema")
    for key in ("relation_id", "spacetime_point_id", "source_ref", "epistemic_status"):
        _nonempty(field.get(key), key)
    _from_hex(field.get("lambda_R_m_minus_2_f64_hex"), "lambda_R")
    _hash64(field.get("source_commitment"), "source_commitment")
    if field.get("field_units") != "m^-2" or field.get("field_semantics") != "RELATIONAL_SCALAR_FIELD_CANDIDATE":
        raise RelationalLambdaHolonomyError("relational Lambda field unit/semantic contract mismatch")
    expected = {
        "geometry_derivation_status": "OPEN",
        "holonomy_derivation_status": "OPEN",
        "entanglement_status": "OPEN_REQUIRES_QUANTUM_WITNESS",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "RELATIONAL_LAMBDA_FIELD_BOUND",
    }
    for key, value in expected.items():
        if field.get(key) != value:
            raise RelationalLambdaHolonomyError(f"relational Lambda field status mismatch: {key}")
    supplied = _hash64(field.get("relational_lambda_field_commitment"), "relational_lambda_field_commitment")
    core = dict(field)
    core.pop("relational_lambda_field_commitment", None)
    if supplied != _seal(RELATIONAL_LAMBDA_FIELD_DOMAIN, core):
        raise RelationalLambdaHolonomyError("relational Lambda field commitment mismatch")
    return True


def build_relational_lambda_energy_v08(
    *,
    field: Mapping[str, Any],
    support_volume_m3: Any,
    energy_convention_id: str = "EINSTEIN_LAMBDA_EFFECTIVE_SOURCE_SI_V1",
) -> dict[str, Any]:
    validate_relational_lambda_field_v08(field)
    volume = _positive(support_volume_m3, "support_volume_m3")
    lam = _from_hex(field["lambda_R_m_minus_2_f64_hex"], "lambda_R")
    energy_density = lam * (C_SI ** 4) / (8.0 * math.pi * G_SI)
    energy = energy_density * volume
    core = {
        "schema": RELATIONAL_LAMBDA_ENERGY_SCHEMA,
        "relation_id": str(field["relation_id"]),
        "spacetime_point_id": str(field["spacetime_point_id"]),
        "relational_lambda_field_commitment": str(field["relational_lambda_field_commitment"]),
        "lambda_R_m_minus_2_f64_hex": str(field["lambda_R_m_minus_2_f64_hex"]),
        "support_volume_m3_f64_hex": volume.hex(),
        "effective_source_energy_density_j_m3_f64_hex": energy_density.hex(),
        "effective_source_energy_j_f64_hex": energy.hex(),
        "energy_density_law": "u_R = Lambda_R*c^4/(8*pi*G)",
        "energy_convention_id": _nonempty(energy_convention_id, "energy_convention_id"),
        "dynamic_scalar_energy_terms_status": "OPEN",
        "geometry_adapter_status": "REQUIRED",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "RELATIONAL_LAMBDA_EFFECTIVE_SOURCE_ENERGY_BOUND",
    }
    return {**core, "relational_lambda_energy_commitment": _seal(RELATIONAL_LAMBDA_ENERGY_DOMAIN, core)}


def validate_relational_lambda_energy_v08(energy: Mapping[str, Any]) -> bool:
    if energy.get("schema") != RELATIONAL_LAMBDA_ENERGY_SCHEMA:
        raise RelationalLambdaHolonomyError("unsupported relational Lambda energy schema")
    for key in ("relation_id", "spacetime_point_id", "energy_convention_id"):
        _nonempty(energy.get(key), key)
    _hash64(energy.get("relational_lambda_field_commitment"), "relational_lambda_field_commitment")
    lam = _from_hex(energy.get("lambda_R_m_minus_2_f64_hex"), "lambda_R")
    volume = _positive(_from_hex(energy.get("support_volume_m3_f64_hex"), "support_volume_m3"), "support_volume_m3")
    density = _from_hex(energy.get("effective_source_energy_density_j_m3_f64_hex"), "effective_source_energy_density")
    total = _from_hex(energy.get("effective_source_energy_j_f64_hex"), "effective_source_energy")
    expected_density = lam * (C_SI ** 4) / (8.0 * math.pi * G_SI)
    expected_total = expected_density * volume
    if density.hex() != expected_density.hex() or total.hex() != expected_total.hex():
        raise RelationalLambdaHolonomyError("relational Lambda effective-source energy mismatch")
    if energy.get("energy_density_law") != "u_R = Lambda_R*c^4/(8*pi*G)":
        raise RelationalLambdaHolonomyError("relational Lambda energy law mismatch")
    expected = {
        "dynamic_scalar_energy_terms_status": "OPEN",
        "geometry_adapter_status": "REQUIRED",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "RELATIONAL_LAMBDA_EFFECTIVE_SOURCE_ENERGY_BOUND",
    }
    for key, value in expected.items():
        if energy.get(key) != value:
            raise RelationalLambdaHolonomyError(f"relational Lambda energy status mismatch: {key}")
    supplied = _hash64(energy.get("relational_lambda_energy_commitment"), "relational_lambda_energy_commitment")
    core = dict(energy)
    core.pop("relational_lambda_energy_commitment", None)
    if supplied != _seal(RELATIONAL_LAMBDA_ENERGY_DOMAIN, core):
        raise RelationalLambdaHolonomyError("relational Lambda energy commitment mismatch")
    return True


def build_relational_geometry_holonomy_v08(
    *,
    energy: Mapping[str, Any],
    geometry_adapter_id: str,
    metric_commitment: str,
    connection_commitment: str,
    loop_id: str,
    holonomy_phase_rad: Any,
    source_ref: str,
    epistemic_status: str,
) -> dict[str, Any]:
    validate_relational_lambda_energy_v08(energy)
    phase = wrap_pi(holonomy_phase_rad)
    core = {
        "schema": RELATIONAL_GEOMETRY_HOLONOMY_SCHEMA,
        "relation_id": str(energy["relation_id"]),
        "spacetime_point_id": str(energy["spacetime_point_id"]),
        "relational_lambda_energy_commitment": str(energy["relational_lambda_energy_commitment"]),
        "geometry_adapter_id": _nonempty(geometry_adapter_id, "geometry_adapter_id"),
        "metric_commitment": _hash64(metric_commitment, "metric_commitment"),
        "connection_commitment": _hash64(connection_commitment, "connection_commitment"),
        "loop_id": _nonempty(loop_id, "loop_id"),
        "holonomy_phase_rad_f64_hex": _finite(holonomy_phase_rad, "holonomy_phase_rad").hex(),
        "holonomy_phase_wrapped_rad_f64_hex": phase.hex(),
        "holonomy_projection": "U1_PHASE_PROJECTION",
        "connection_semantics": "INTERNAL_ROTATION_GEOMETRY_CANDIDATE",
        "source_ref": _nonempty(source_ref, "source_ref"),
        "epistemic_status": _nonempty(epistemic_status, "epistemic_status"),
        "geometry_provenance": "UPSTREAM_ADAPTER_WITNESS",
        "connection_derivation_contract": "EXPLICIT_GEOMETRY_ADAPTER_REQUIRED",
        "entanglement_status": "OPEN_REQUIRES_QUANTUM_WITNESS",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "RELATIONAL_GEOMETRY_HOLONOMY_BOUND",
    }
    return {**core, "relational_geometry_holonomy_commitment": _seal(RELATIONAL_GEOMETRY_HOLONOMY_DOMAIN, core)}


def validate_relational_geometry_holonomy_v08(geometry: Mapping[str, Any]) -> bool:
    if geometry.get("schema") != RELATIONAL_GEOMETRY_HOLONOMY_SCHEMA:
        raise RelationalLambdaHolonomyError("unsupported relational geometry holonomy schema")
    for key in ("relation_id", "spacetime_point_id", "geometry_adapter_id", "loop_id", "source_ref", "epistemic_status"):
        _nonempty(geometry.get(key), key)
    for key in ("relational_lambda_energy_commitment", "metric_commitment", "connection_commitment"):
        _hash64(geometry.get(key), key)
    raw = _from_hex(geometry.get("holonomy_phase_rad_f64_hex"), "holonomy_phase_rad")
    wrapped = _from_hex(geometry.get("holonomy_phase_wrapped_rad_f64_hex"), "holonomy_phase_wrapped_rad")
    if wrapped.hex() != wrap_pi(raw).hex():
        raise RelationalLambdaHolonomyError("holonomy phase wrapping mismatch")
    if geometry.get("holonomy_projection") != "U1_PHASE_PROJECTION":
        raise RelationalLambdaHolonomyError("holonomy projection mismatch")
    if geometry.get("connection_semantics") != "INTERNAL_ROTATION_GEOMETRY_CANDIDATE":
        raise RelationalLambdaHolonomyError("connection semantic binding mismatch")
    expected = {
        "geometry_provenance": "UPSTREAM_ADAPTER_WITNESS",
        "connection_derivation_contract": "EXPLICIT_GEOMETRY_ADAPTER_REQUIRED",
        "entanglement_status": "OPEN_REQUIRES_QUANTUM_WITNESS",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "RELATIONAL_GEOMETRY_HOLONOMY_BOUND",
    }
    for key, value in expected.items():
        if geometry.get(key) != value:
            raise RelationalLambdaHolonomyError(f"relational geometry status mismatch: {key}")
    supplied = _hash64(geometry.get("relational_geometry_holonomy_commitment"), "relational_geometry_holonomy_commitment")
    core = dict(geometry)
    core.pop("relational_geometry_holonomy_commitment", None)
    if supplied != _seal(RELATIONAL_GEOMETRY_HOLONOMY_DOMAIN, core):
        raise RelationalLambdaHolonomyError("relational geometry holonomy commitment mismatch")
    return True


def build_qhtri_holonomy_lag_v08(
    *,
    geometry: Mapping[str, Any],
    oscillator_i: str,
    oscillator_j: str,
    n: int,
    m: int,
    theta_i_rad: Any,
    theta_j_rad: Any,
) -> dict[str, Any]:
    validate_relational_geometry_holonomy_v08(geometry)
    if isinstance(n, bool) or isinstance(m, bool) or not isinstance(n, int) or not isinstance(m, int):
        raise RelationalLambdaHolonomyError("QHTRI winding coefficients n and m must be integers")
    if n == 0 and m == 0:
        raise RelationalLambdaHolonomyError("QHTRI winding pair cannot be identically zero")
    theta_i = _finite(theta_i_rad, "theta_i_rad")
    theta_j = _finite(theta_j_rad, "theta_j_rad")
    tau = _from_hex(geometry["holonomy_phase_wrapped_rad_f64_hex"], "holonomy_phase_wrapped_rad")
    epsilon = wrap_pi(n * theta_i - m * theta_j - tau)
    unit_potential_shape = -math.cos(epsilon)
    unit_torsion_force_shape = -math.sin(epsilon)
    phase_lock = math.cos(epsilon / 2.0) ** 2
    core = {
        "schema": QHTRI_HOLONOMY_LAG_SCHEMA,
        "relation_id": str(geometry["relation_id"]),
        "loop_id": str(geometry["loop_id"]),
        "relational_geometry_holonomy_commitment": str(geometry["relational_geometry_holonomy_commitment"]),
        "oscillator_i": _nonempty(oscillator_i, "oscillator_i"),
        "oscillator_j": _nonempty(oscillator_j, "oscillator_j"),
        "n": n,
        "m": m,
        "theta_i_rad_f64_hex": theta_i.hex(),
        "theta_j_rad_f64_hex": theta_j.hex(),
        "tau_holonomy_rad_f64_hex": tau.hex(),
        "epsilon_qhtri_rad_f64_hex": epsilon.hex(),
        "epsilon_law": "epsilon=wrap_pi(n*theta_i-m*theta_j-tau_holonomy)",
        "unit_potential_shape_f64_hex": unit_potential_shape.hex(),
        "unit_torsion_force_shape_f64_hex": unit_torsion_force_shape.hex(),
        "phase_lock_C_f64_hex": phase_lock.hex(),
        "phase_lock_law": "C=cos^2(epsilon/2)",
        "tau_origin": "U1_PROJECTED_GEOMETRIC_HOLONOMY",
        "coupling_energy_scale_status": "OPEN",
        "entanglement_witness_status": "OPEN",
        "entanglement_status": "OPEN_REQUIRES_QUANTUM_WITNESS",
        "vector_synthesis_status": "HELD_FOR_PREVECTOR_ADMISSION",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "QHTRI_HOLONOMY_LAG_BOUND",
    }
    return {**core, "qhtri_holonomy_lag_commitment": _seal(QHTRI_HOLONOMY_LAG_DOMAIN, core)}


def validate_qhtri_holonomy_lag_v08(binding: Mapping[str, Any]) -> bool:
    if binding.get("schema") != QHTRI_HOLONOMY_LAG_SCHEMA:
        raise RelationalLambdaHolonomyError("unsupported QHTRI holonomy-lag schema")
    for key in ("relation_id", "loop_id", "oscillator_i", "oscillator_j"):
        _nonempty(binding.get(key), key)
    _hash64(binding.get("relational_geometry_holonomy_commitment"), "relational_geometry_holonomy_commitment")
    n = binding.get("n")
    m = binding.get("m")
    if isinstance(n, bool) or isinstance(m, bool) or not isinstance(n, int) or not isinstance(m, int) or (n == 0 and m == 0):
        raise RelationalLambdaHolonomyError("invalid QHTRI winding coefficients")
    theta_i = _from_hex(binding.get("theta_i_rad_f64_hex"), "theta_i_rad")
    theta_j = _from_hex(binding.get("theta_j_rad_f64_hex"), "theta_j_rad")
    tau = _from_hex(binding.get("tau_holonomy_rad_f64_hex"), "tau_holonomy_rad")
    epsilon = _from_hex(binding.get("epsilon_qhtri_rad_f64_hex"), "epsilon_qhtri_rad")
    expected_epsilon = wrap_pi(n * theta_i - m * theta_j - tau)
    if epsilon.hex() != expected_epsilon.hex():
        raise RelationalLambdaHolonomyError("QHTRI holonomy epsilon mismatch")
    expected_potential = -math.cos(expected_epsilon)
    expected_force = -math.sin(expected_epsilon)
    expected_lock = math.cos(expected_epsilon / 2.0) ** 2
    if _from_hex(binding.get("unit_potential_shape_f64_hex"), "unit_potential_shape").hex() != expected_potential.hex():
        raise RelationalLambdaHolonomyError("QHTRI unit potential shape mismatch")
    if _from_hex(binding.get("unit_torsion_force_shape_f64_hex"), "unit_torsion_force_shape").hex() != expected_force.hex():
        raise RelationalLambdaHolonomyError("QHTRI unit torsion force shape mismatch")
    if _from_hex(binding.get("phase_lock_C_f64_hex"), "phase_lock_C").hex() != expected_lock.hex():
        raise RelationalLambdaHolonomyError("QHTRI phase-lock scalar mismatch")
    if binding.get("epsilon_law") != "epsilon=wrap_pi(n*theta_i-m*theta_j-tau_holonomy)":
        raise RelationalLambdaHolonomyError("QHTRI epsilon law mismatch")
    if binding.get("phase_lock_law") != "C=cos^2(epsilon/2)" or binding.get("tau_origin") != "U1_PROJECTED_GEOMETRIC_HOLONOMY":
        raise RelationalLambdaHolonomyError("QHTRI holonomy provenance mismatch")
    expected = {
        "coupling_energy_scale_status": "OPEN",
        "entanglement_witness_status": "OPEN",
        "entanglement_status": "OPEN_REQUIRES_QUANTUM_WITNESS",
        "vector_synthesis_status": "HELD_FOR_PREVECTOR_ADMISSION",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "QHTRI_HOLONOMY_LAG_BOUND",
    }
    for key, value in expected.items():
        if binding.get(key) != value:
            raise RelationalLambdaHolonomyError(f"QHTRI holonomy-lag status mismatch: {key}")
    supplied = _hash64(binding.get("qhtri_holonomy_lag_commitment"), "qhtri_holonomy_lag_commitment")
    core = dict(binding)
    core.pop("qhtri_holonomy_lag_commitment", None)
    if supplied != _seal(QHTRI_HOLONOMY_LAG_DOMAIN, core):
        raise RelationalLambdaHolonomyError("QHTRI holonomy-lag commitment mismatch")
    return True
