from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

from tools.gremlin_connection_path_holonomy_v09 import validate_connection_path_integral_v09
from tools.gremlin_relational_coupling_energy_v11 import validate_relational_coupling_energy_partition_v11
from tools.gremlin_relational_lambda_holonomy_v08 import validate_relational_lambda_energy_v08

ORIENTED_COUPLING_SCHEMA = "GREMLIN_ORIENTED_RELATIONAL_COUPLING_V1_3"
ORIENTED_COUPLING_DOMAIN = b"GREMLIN-ORIENTED-RELATIONAL-COUPLING/v1.3\x00"
BINARY64_REL_TOL = 1e-14
ORIENTATION_TOL = 1e-15


class OrientedRelationalCouplingError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(domain: bytes, value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def _hash64(value: Any, name: str) -> str:
    text = str(value)
    if len(text) != 64:
        raise OrientedRelationalCouplingError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise OrientedRelationalCouplingError(f"{name} must be hexadecimal") from exc
    return text


def _from_hex(value: Any, name: str) -> float:
    try:
        x = float.fromhex(str(value))
    except (TypeError, ValueError) as exc:
        raise OrientedRelationalCouplingError(f"{name} must be a binary64 hex float") from exc
    if not math.isfinite(x):
        raise OrientedRelationalCouplingError(f"{name} must be finite")
    return x


def _orientation(sin_tau: float) -> str:
    if abs(sin_tau) <= ORIENTATION_TOL:
        return "AXIAL_OR_ZERO_HOLONOMY_ORIENTATION"
    if sin_tau > 0.0:
        return "POSITIVE_HOLONOMY_ORIENTATION"
    return "NEGATIVE_HOLONOMY_ORIENTATION"


def build_oriented_relational_coupling_v13(
    *,
    energy: Mapping[str, Any],
    path: Mapping[str, Any],
    partition: Mapping[str, Any],
) -> dict[str, Any]:
    validate_relational_lambda_energy_v08(energy)
    validate_connection_path_integral_v09(path)
    validate_relational_coupling_energy_partition_v11(partition, energy=energy, path=path)

    source_energy = _from_hex(partition["source_energy_j_f64_hex"], "source_energy")
    tau = _from_hex(partition["tau_holonomy_rad_f64_hex"], "tau_holonomy")
    j_c = _from_hex(partition["coherence_channel_J_C_j_f64_hex"], "J_C")
    j_d = _from_hex(partition["torsion_channel_J_D_j_f64_hex"], "J_D")
    c_h = _from_hex(partition["coherence_C_h_f64_hex"], "C_h")
    d_h = _from_hex(partition["torsion_D_h_f64_hex"], "D_h")

    cos_tau = math.cos(tau)
    sin_tau = math.sin(tau)
    unit_norm = math.hypot(cos_tau, sin_tau)

    normalized_partition_imbalance = c_h - d_h
    imbalance_trig_residual = normalized_partition_imbalance - cos_tau
    if not math.isclose(normalized_partition_imbalance, cos_tau, rel_tol=BINARY64_REL_TOL, abs_tol=1e-15):
        raise OrientedRelationalCouplingError("v1.1 channel imbalance does not match cos(tau) within binary64 tolerance")

    partition_energy_imbalance = j_c - j_d
    oriented_real = source_energy * cos_tau
    oriented_imag = source_energy * sin_tau
    energy_imbalance_residual = partition_energy_imbalance - oriented_real
    if not math.isclose(partition_energy_imbalance, oriented_real, rel_tol=BINARY64_REL_TOL, abs_tol=1e-300):
        raise OrientedRelationalCouplingError("v1.1 energy imbalance does not match E_R*cos(tau) within binary64 tolerance")

    oriented_magnitude = math.hypot(oriented_real, oriented_imag)
    magnitude_residual = oriented_magnitude - abs(source_energy)
    if not math.isclose(oriented_magnitude, abs(source_energy), rel_tol=BINARY64_REL_TOL, abs_tol=1e-300):
        raise OrientedRelationalCouplingError("oriented coupling magnitude does not close to |E_R|")

    core = {
        "schema": ORIENTED_COUPLING_SCHEMA,
        "relation_id": str(energy["relation_id"]),
        "spacetime_point_id": str(energy["spacetime_point_id"]),
        "relational_lambda_energy_commitment": str(energy["relational_lambda_energy_commitment"]),
        "connection_path_integral_commitment": str(path["connection_path_integral_commitment"]),
        "relational_coupling_energy_commitment": _hash64(
            partition["relational_coupling_energy_commitment"],
            "relational_coupling_energy_commitment",
        ),
        "tau_holonomy_rad_f64_hex": tau.hex(),
        "holonomy_unit_real_cos_tau_f64_hex": cos_tau.hex(),
        "holonomy_unit_imag_sin_tau_f64_hex": sin_tau.hex(),
        "holonomy_unit_norm_f64_hex": unit_norm.hex(),
        "holonomy_unit_law": "h_R=exp(i*tau)=cos(tau)+i*sin(tau)",
        "holonomy_orientation": _orientation(sin_tau),
        "orientation_tolerance_f64_hex": ORIENTATION_TOL.hex(),
        "coherence_C_h_f64_hex": c_h.hex(),
        "torsion_D_h_f64_hex": d_h.hex(),
        "normalized_channel_imbalance_f64_hex": normalized_partition_imbalance.hex(),
        "normalized_channel_imbalance_law": "C_h-D_h=cos(tau)",
        "normalized_imbalance_trig_residual_f64_hex": imbalance_trig_residual.hex(),
        "coherence_channel_J_C_j_f64_hex": j_c.hex(),
        "torsion_channel_J_D_j_f64_hex": j_d.hex(),
        "partition_energy_imbalance_j_f64_hex": partition_energy_imbalance.hex(),
        "oriented_coupling_real_j_f64_hex": oriented_real.hex(),
        "oriented_coupling_imag_j_f64_hex": oriented_imag.hex(),
        "oriented_coupling_law": "J_complex=E_R*exp(i*tau)",
        "real_projection_law": "Re(J_complex)=E_R*cos(tau)=J_C-J_D",
        "rotation_quadrature_law": "Im(J_complex)=E_R*sin(tau)",
        "energy_imbalance_projection_residual_j_f64_hex": energy_imbalance_residual.hex(),
        "oriented_coupling_magnitude_j_f64_hex": oriented_magnitude.hex(),
        "magnitude_law": "abs(J_complex)=abs(E_R)",
        "magnitude_residual_j_f64_hex": magnitude_residual.hex(),
        "binary64_relative_tolerance_f64_hex": BINARY64_REL_TOL.hex(),
        "parameter_free_given_v1_1_partition_and_holonomy": True,
        "orientation_sign_retained": True,
        "channel_selection_status": "OPEN_REQUIRES_PHYSICAL_ATTRIBUTION_LAW",
        "hermitian_operator_embedding_status": "OPEN_REQUIRES_EXPLICIT_OPERATOR_PAIRING",
        "entanglement_attribution_status": "OPEN_REQUIRES_HERMITIAN_EVOLUTION_WITNESS",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "ORIENTED_RELATIONAL_COUPLING_BOUND",
    }
    return {**core, "oriented_relational_coupling_commitment": _seal(ORIENTED_COUPLING_DOMAIN, core)}


def validate_oriented_relational_coupling_v13(
    receipt: Mapping[str, Any],
    *,
    energy: Mapping[str, Any],
    path: Mapping[str, Any],
    partition: Mapping[str, Any],
) -> bool:
    expected = build_oriented_relational_coupling_v13(energy=energy, path=path, partition=partition)
    if receipt.get("schema") != ORIENTED_COUPLING_SCHEMA:
        raise OrientedRelationalCouplingError("unsupported oriented relational coupling schema")
    for key, value in expected.items():
        if key == "oriented_relational_coupling_commitment":
            continue
        if receipt.get(key) != value:
            raise OrientedRelationalCouplingError(f"oriented relational coupling mismatch: {key}")
    supplied = _hash64(
        receipt.get("oriented_relational_coupling_commitment"),
        "oriented_relational_coupling_commitment",
    )
    core = dict(receipt)
    core.pop("oriented_relational_coupling_commitment", None)
    if supplied != _seal(ORIENTED_COUPLING_DOMAIN, core):
        raise OrientedRelationalCouplingError("oriented relational coupling commitment mismatch")
    return True
