from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from tools.gremlin_intention_mass_flavor_factorization_v18 import (
    build_intention_mass_flavor_factorization_v18,
    validate_intention_mass_flavor_factorization_v18,
)

SCHEMA = "GREMLIN_J_IDENTIFIABILITY_NO_GO_V1_9"
DOMAIN = b"GREMLIN-J-IDENTIFIABILITY-NO-GO/v1.9\x00"


class JIdentifiabilityNoGoError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(DOMAIN + _canonical(value), digest_size=32).hexdigest()


def _rotation12(theta: float) -> list[list[float]]:
    c, s = math.cos(theta), math.sin(theta)
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


def _identity3() -> list[list[float]]:
    return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def _decode_distribution(receipt: Mapping[str, Any]) -> list[float]:
    return [float.fromhex(str(receipt["R_flavor_distribution"][key])) for key in ("e", "mu", "tau")]


def _max_delta(a: Sequence[float], b: Sequence[float]) -> float:
    return max(abs(float(a[i]) - float(b[i])) for i in range(3))


def build_J_identifiability_no_go_v19(
    *,
    audit_id: str,
    intention_state: Sequence[Any],
    mass_phases_rad: Sequence[Any],
    theta12_rad: Any,
    theta13_rad: Any,
    theta23_rad: Any,
    delta_cp_rad: Any,
    alternative_rotation_rad: Any,
    intention_source_ref: str,
    phase_source_ref: str,
    pmns_source_ref: str,
    historical_toe_source_ref: str,
    corrected_eft_source_ref: str,
    epistemic_status: str = "CANDIDATE",
) -> dict[str, Any]:
    theta = float(alternative_rotation_rad)
    if not math.isfinite(theta) or abs(theta) < 1e-9:
        raise JIdentifiabilityNoGoError("alternative_rotation_rad must be finite and nontrivial")

    common = dict(
        intention_state=intention_state,
        mass_phases_rad=mass_phases_rad,
        theta12_rad=theta12_rad,
        theta13_rad=theta13_rad,
        theta23_rad=theta23_rad,
        delta_cp_rad=delta_cp_rad,
        intention_source_ref=intention_source_ref,
        phase_source_ref=phase_source_ref,
        pmns_source_ref=pmns_source_ref,
        epistemic_status=epistemic_status,
    )
    identity_receipt = build_intention_mass_flavor_factorization_v18(
        factorization_id=f"{audit_id}:J_identity",
        intention_to_mass_map=_identity3(),
        **common,
    )
    rotated_receipt = build_intention_mass_flavor_factorization_v18(
        factorization_id=f"{audit_id}:J_rotation12",
        intention_to_mass_map=_rotation12(theta),
        **common,
    )
    validate_intention_mass_flavor_factorization_v18(identity_receipt)
    validate_intention_mass_flavor_factorization_v18(rotated_receipt)

    p_identity = _decode_distribution(identity_receipt)
    p_rotated = _decode_distribution(rotated_receipt)
    observable_delta = _max_delta(p_identity, p_rotated)
    distinguishable = observable_delta > 1e-10

    # Structural statement: for dim(H_I)=3, J^dagger J=I leaves the full U(3) family.
    # A pair of admissible members with distinct flavor readouts is a constructive non-uniqueness witness.
    verdict = "CURRENT_PREMISES_DO_NOT_IDENTIFY_J" if distinguishable else "WITNESS_INCONCLUSIVE"

    core = {
        "schema": SCHEMA,
        "audit_id": str(audit_id),
        "auditor": "BELZEBUB",
        "question": "Do current structural/source premises uniquely determine J:H_I->H_mass?",
        "source_dimension_used": 3,
        "structural_constraint": "J^dagger J=I",
        "admissible_family_for_dim3": "U(3)",
        "continuous_family_witness": "J(theta)=R_12(theta), theta real",
        "alternative_rotation_rad_f64_hex": theta.hex(),
        "J_identity_factorization_commitment": str(identity_receipt["intention_mass_flavor_factorization_commitment"]),
        "J_rotated_factorization_commitment": str(rotated_receipt["intention_mass_flavor_factorization_commitment"]),
        "identity_flavor_distribution": {k: identity_receipt["R_flavor_distribution"][k] for k in ("e", "mu", "tau")},
        "rotated_flavor_distribution": {k: rotated_receipt["R_flavor_distribution"][k] for k in ("e", "mu", "tau")},
        "max_flavor_probability_delta_f64_hex": observable_delta.hex(),
        "both_candidates_pass_v18_factorization": True,
        "different_observable_readout": distinguishable,
        "historical_toe_source_ref": str(historical_toe_source_ref),
        "historical_toe_evidence_status": {
            "symbolic_SU3": "REPRESENTATION_PRESENT_BUT_NO_NEUTRINO_MASS_SUBSPACE_INTERTWINER_SELECTED",
            "resonance_mass_ansatz": "SCALAR_MASS_RELATION_PRESENT_BUT_DOES_NOT_DETERMINE_COMPLEX_THREE_COMPONENT_J",
            "intention_phase_operator": "INTERNAL_PHASE_DYNAMICS_PRESENT_BUT_NO_H_I_TO_H_MASS_MAP_DERIVED",
        },
        "corrected_eft_source_ref": str(corrected_eft_source_ref),
        "corrected_eft_evidence_status": "NEUTRINO_INTENTION_CORRESPONDENCE_IS_INTERPRETIVE_SEMANTIC_INDEXING_NOT_A_PREDICTIVE_J_DERIVATION",
        "pmns_role": "U_PMNS_MAPS_H_MASS_TO_H_FLAVOR_AND_CANNOT_BY_ITSELF_SELECT_J",
        "no_go_scope": "NON_IDENTIFIABILITY_FROM_CURRENT_PREMISES_ONLY",
        "future_escape_condition": "additional dynamical_symmetry_boundary_or_empirical_constraint_may_select_J",
        "belzebub_verdict": verdict,
        "canon_status": "CANDIDATE",
        "execution_status": "RESEARCH_AUDIT_ONLY",
    }
    return {**core, "J_identifiability_no_go_commitment": _seal(core)}


def validate_J_identifiability_no_go_v19(receipt: Mapping[str, Any]) -> bool:
    if receipt.get("schema") != SCHEMA:
        raise JIdentifiabilityNoGoError("unsupported v1.9 schema")
    commitment = str(receipt.get("J_identifiability_no_go_commitment", ""))
    if len(commitment) != 64:
        raise JIdentifiabilityNoGoError("missing v1.9 commitment")
    try:
        bytes.fromhex(commitment)
    except ValueError as exc:
        raise JIdentifiabilityNoGoError("v1.9 commitment must be hexadecimal") from exc
    core = dict(receipt)
    core.pop("J_identifiability_no_go_commitment", None)
    if commitment != _seal(core):
        raise JIdentifiabilityNoGoError("v1.9 commitment mismatch")
    if receipt.get("belzebub_verdict") not in {"CURRENT_PREMISES_DO_NOT_IDENTIFY_J", "WITNESS_INCONCLUSIVE"}:
        raise JIdentifiabilityNoGoError("unexpected v1.9 verdict")
    return True
