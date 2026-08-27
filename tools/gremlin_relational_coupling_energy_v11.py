from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

from tools.gremlin_connection_path_holonomy_v09 import validate_connection_path_integral_v09
from tools.gremlin_relational_lambda_holonomy_v08 import validate_relational_lambda_energy_v08

COUPLING_ENERGY_SCHEMA = "GREMLIN_RELATIONAL_COUPLING_ENERGY_PARTITION_V1_1"
COUPLING_ENERGY_DOMAIN = b"GREMLIN-RELATIONAL-COUPLING-ENERGY-PARTITION/v1.1\x00"


class RelationalCouplingEnergyError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(domain: bytes, value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    text = str(value)
    if not text:
        raise RelationalCouplingEnergyError(f"{name} must be non-empty")
    return text


def _hash64(value: Any, name: str) -> str:
    text = _nonempty(value, name)
    if len(text) != 64:
        raise RelationalCouplingEnergyError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise RelationalCouplingEnergyError(f"{name} must be hexadecimal") from exc
    return text


def _from_hex(value: Any, name: str) -> float:
    try:
        x = float.fromhex(str(value))
    except (TypeError, ValueError) as exc:
        raise RelationalCouplingEnergyError(f"{name} must be a binary64 hex float") from exc
    if not math.isfinite(x):
        raise RelationalCouplingEnergyError(f"{name} must be finite")
    return x


def build_relational_coupling_energy_partition_v11(
    *,
    energy: Mapping[str, Any],
    path: Mapping[str, Any],
) -> dict[str, Any]:
    validate_relational_lambda_energy_v08(energy)
    validate_connection_path_integral_v09(path)
    if str(path["relational_lambda_energy_commitment"]) != str(energy["relational_lambda_energy_commitment"]):
        raise RelationalCouplingEnergyError("Lambda-energy and connection-path lineage mismatch")

    tau = _from_hex(path["holonomy_phase_wrapped_rad_f64_hex"], "tau_holonomy")
    source_energy = _from_hex(energy["effective_source_energy_j_f64_hex"], "effective_source_energy")

    coherence = math.cos(tau / 2.0) ** 2
    if coherence < 0.0 and coherence > -1e-15:
        coherence = 0.0
    if coherence > 1.0 and coherence < 1.0 + 1e-15:
        coherence = 1.0
    torsion = 1.0 - coherence

    j_coherence = source_energy * coherence
    j_torsion = source_energy - j_coherence
    reconstructed = j_coherence + j_torsion
    residual = source_energy - reconstructed

    core = {
        "schema": COUPLING_ENERGY_SCHEMA,
        "relation_id": str(energy["relation_id"]),
        "spacetime_point_id": str(energy["spacetime_point_id"]),
        "relational_lambda_energy_commitment": str(energy["relational_lambda_energy_commitment"]),
        "connection_path_integral_commitment": str(path["connection_path_integral_commitment"]),
        "tau_holonomy_rad_f64_hex": tau.hex(),
        "source_energy_j_f64_hex": source_energy.hex(),
        "coherence_C_h_f64_hex": coherence.hex(),
        "torsion_D_h_f64_hex": torsion.hex(),
        "phase_partition_law": "C_h=cos^2(tau/2); D_h=1-C_h=sin^2(tau/2)",
        "coherence_channel_J_C_j_f64_hex": j_coherence.hex(),
        "torsion_channel_J_D_j_f64_hex": j_torsion.hex(),
        "energy_partition_law": "J_C=E_R*C_h; J_D=E_R-J_C",
        "reconstructed_source_energy_j_f64_hex": reconstructed.hex(),
        "partition_residual_j_f64_hex": residual.hex(),
        "parameter_free_given_bound_source_energy_and_holonomy": True,
        "channel_selection_status": "OPEN",
        "channel_candidates": ["COHERENCE_CHANNEL", "TORSION_CHANNEL"],
        "coupling_model_status": "RELATIONAL_ENERGY_PARTITION_CANDIDATE",
        "entangling_channel_attribution_status": "OPEN",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "RELATIONAL_COUPLING_ENERGY_PARTITION_BOUND",
    }
    return {**core, "relational_coupling_energy_commitment": _seal(COUPLING_ENERGY_DOMAIN, core)}


def validate_relational_coupling_energy_partition_v11(
    receipt: Mapping[str, Any],
    *,
    energy: Mapping[str, Any],
    path: Mapping[str, Any],
) -> bool:
    validate_relational_lambda_energy_v08(energy)
    validate_connection_path_integral_v09(path)
    if receipt.get("schema") != COUPLING_ENERGY_SCHEMA:
        raise RelationalCouplingEnergyError("unsupported relational coupling-energy schema")
    if str(path["relational_lambda_energy_commitment"]) != str(energy["relational_lambda_energy_commitment"]):
        raise RelationalCouplingEnergyError("Lambda-energy and connection-path lineage mismatch")
    if str(receipt.get("relational_lambda_energy_commitment")) != str(energy["relational_lambda_energy_commitment"]):
        raise RelationalCouplingEnergyError("coupling receipt Lambda-energy lineage mismatch")
    if str(receipt.get("connection_path_integral_commitment")) != str(path["connection_path_integral_commitment"]):
        raise RelationalCouplingEnergyError("coupling receipt connection-path lineage mismatch")
    for key in ("relational_lambda_energy_commitment", "connection_path_integral_commitment"):
        _hash64(receipt.get(key), key)
    if str(receipt.get("relation_id")) != str(energy["relation_id"]) or str(receipt.get("spacetime_point_id")) != str(energy["spacetime_point_id"]):
        raise RelationalCouplingEnergyError("coupling receipt relation/spacetime lineage mismatch")

    tau = _from_hex(path["holonomy_phase_wrapped_rad_f64_hex"], "tau_holonomy")
    source_energy = _from_hex(energy["effective_source_energy_j_f64_hex"], "effective_source_energy")
    coherence = math.cos(tau / 2.0) ** 2
    if coherence < 0.0 and coherence > -1e-15:
        coherence = 0.0
    if coherence > 1.0 and coherence < 1.0 + 1e-15:
        coherence = 1.0
    torsion = 1.0 - coherence
    j_coherence = source_energy * coherence
    j_torsion = source_energy - j_coherence
    reconstructed = j_coherence + j_torsion
    residual = source_energy - reconstructed

    expected_hex = {
        "tau_holonomy_rad_f64_hex": tau.hex(),
        "source_energy_j_f64_hex": source_energy.hex(),
        "coherence_C_h_f64_hex": coherence.hex(),
        "torsion_D_h_f64_hex": torsion.hex(),
        "coherence_channel_J_C_j_f64_hex": j_coherence.hex(),
        "torsion_channel_J_D_j_f64_hex": j_torsion.hex(),
        "reconstructed_source_energy_j_f64_hex": reconstructed.hex(),
        "partition_residual_j_f64_hex": residual.hex(),
    }
    for key, value in expected_hex.items():
        if str(receipt.get(key)) != value:
            raise RelationalCouplingEnergyError(f"relational coupling-energy mismatch: {key}")

    if receipt.get("phase_partition_law") != "C_h=cos^2(tau/2); D_h=1-C_h=sin^2(tau/2)":
        raise RelationalCouplingEnergyError("phase partition law mismatch")
    if receipt.get("energy_partition_law") != "J_C=E_R*C_h; J_D=E_R-J_C":
        raise RelationalCouplingEnergyError("energy partition law mismatch")

    expected = {
        "parameter_free_given_bound_source_energy_and_holonomy": True,
        "channel_selection_status": "OPEN",
        "channel_candidates": ["COHERENCE_CHANNEL", "TORSION_CHANNEL"],
        "coupling_model_status": "RELATIONAL_ENERGY_PARTITION_CANDIDATE",
        "entangling_channel_attribution_status": "OPEN",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "RELATIONAL_COUPLING_ENERGY_PARTITION_BOUND",
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise RelationalCouplingEnergyError(f"relational coupling-energy status mismatch: {key}")

    supplied = _hash64(receipt.get("relational_coupling_energy_commitment"), "relational_coupling_energy_commitment")
    core = dict(receipt)
    core.pop("relational_coupling_energy_commitment", None)
    if supplied != _seal(COUPLING_ENERGY_DOMAIN, core):
        raise RelationalCouplingEnergyError("relational coupling-energy commitment mismatch")
    return True
