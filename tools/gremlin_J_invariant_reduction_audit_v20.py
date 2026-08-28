from __future__ import annotations

import cmath
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

SCHEMA = "GREMLIN_J_INVARIANT_REDUCTION_AUDIT_V2_0"
DOMAIN = b"GREMLIN-J-INVARIANT-REDUCTION-AUDIT/v2.0\\x00"


class JInvariantReductionAuditError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(DOMAIN + _canonical(value), digest_size=32).hexdigest()


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise JInvariantReductionAuditError(f"{name} must be finite")
    return x


def stabilizer_dimension_from_multiplicities_v20(multiplicities: Sequence[int]) -> int:
    values = list(multiplicities)
    if not values or any(isinstance(m, bool) or not isinstance(m, int) or m <= 0 for m in values):
        raise JInvariantReductionAuditError("multiplicities must be positive integers")
    if sum(values) != 3:
        raise JInvariantReductionAuditError("v2.0 audit is scoped to dimension three")
    return sum(m * m for m in values)


def support_graph_components_v20(support: Sequence[Sequence[Any]]) -> int:
    if len(support) != 3 or any(len(row) != 3 for row in support):
        raise JInvariantReductionAuditError("support must be 3x3")
    adjacency = [set() for _ in range(3)]
    for i in range(3):
        for j in range(i + 1, 3):
            if bool(support[i][j]) or bool(support[j][i]):
                adjacency[i].add(j)
                adjacency[j].add(i)
    seen: set[int] = set()
    components = 0
    for start in range(3):
        if start in seen:
            continue
        components += 1
        stack = [start]
        seen.add(start)
        while stack:
            node = stack.pop()
            for nxt in adjacency[node]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
    return components


def residual_phase_dimension_after_nondegenerate_mass_v20(support: Sequence[Sequence[Any]]) -> dict[str, int | bool]:
    components = support_graph_components_v20(support)
    return {
        "connected_components": components,
        "unitary_phase_dimension": components,
        "projective_phase_dimension": max(0, components - 1),
        "projectively_identifying": components == 1,
    }


def global_u1_probability_blindness_v20(amplitudes: Sequence[complex], gamma_rad: Any) -> float:
    if len(amplitudes) != 3:
        raise JInvariantReductionAuditError("three amplitudes are required")
    gamma = _finite(gamma_rad, "gamma_rad")
    phase = cmath.exp(1j * gamma)
    before = [abs(complex(z)) ** 2 for z in amplitudes]
    after = [abs(phase * complex(z)) ** 2 for z in amplitudes]
    return max(abs(before[i] - after[i]) for i in range(3))


def _mass_spectrum_status(dm21: float, dm31: float, tol: float = 1e-15) -> tuple[bool, list[int]]:
    eigenvalues = [0.0, dm21, dm31]
    distinct = all(abs(eigenvalues[i] - eigenvalues[j]) > tol for i in range(3) for j in range(i + 1, 3))
    return distinct, [1, 1, 1] if distinct else [3]


def build_J_invariant_reduction_audit_v20(
    *,
    audit_id: str,
    delta_m21_sq_eV2: Any,
    delta_m31_sq_eV2: Any,
    mass_source_ref: str,
    relational_holonomy_source_ref: str,
    neutrinotime_source_ref: str,
    resonance_source_ref: str,
    corrected_eft_source_ref: str,
    epistemic_status: str = "CANDIDATE",
) -> dict[str, Any]:
    dm21 = _finite(delta_m21_sq_eV2, "delta_m21_sq_eV2")
    dm31 = _finite(delta_m31_sq_eV2, "delta_m31_sq_eV2")
    if not str(audit_id):
        raise JInvariantReductionAuditError("audit_id must be non-empty")
    for value, name in (
        (mass_source_ref, "mass_source_ref"),
        (relational_holonomy_source_ref, "relational_holonomy_source_ref"),
        (neutrinotime_source_ref, "neutrinotime_source_ref"),
        (resonance_source_ref, "resonance_source_ref"),
        (corrected_eft_source_ref, "corrected_eft_source_ref"),
        (epistemic_status, "epistemic_status"),
    ):
        if not str(value):
            raise JInvariantReductionAuditError(f"{name} must be non-empty")

    mass_nondegenerate, mass_mult = _mass_spectrum_status(dm21, dm31)
    mass_dim = stabilizer_dimension_from_multiplicities_v20(mass_mult)
    mass_projective_dim = max(0, mass_dim - 1)

    connected_support = [[0, 1, 0], [1, 0, 1], [0, 1, 0]]
    disconnected_support = [[0, 1, 0], [1, 0, 0], [0, 0, 0]]
    connected = residual_phase_dimension_after_nondegenerate_mass_v20(connected_support)
    disconnected = residual_phase_dimension_after_nondegenerate_mass_v20(disconnected_support)

    blindness_delta = global_u1_probability_blindness_v20(
        [complex(0.6, 0.1), complex(-0.2, 0.4), complex(0.3, -0.5)],
        0.731,
    )

    candidates = {
        "nondegenerate_mass_spectrum": {
            "source_ref": str(mass_source_ref),
            "target_operator": "M^2=diag(0,Delta_m21^2,Delta_m31^2)",
            "source_status": "THREE_DISTINCT_MASS_SQUARED_EIGENVALUES" if mass_nondegenerate else "DEGENERATE_OR_UNRESOLVED",
            "stabilizer": "U(1)^3" if mass_nondegenerate else "UNRESOLVED",
            "stabilizer_dimension": mass_dim,
            "projective_dimension": mass_projective_dim,
            "verdict": "PARTIAL_REDUCTION" if mass_nondegenerate else "NO_REDUCTION_CERTIFIED",
        },
        "relational_lambda_holonomy_v08": {
            "source_ref": str(relational_holonomy_source_ref),
            "current_projection": "U1_PHASE_PROJECTION",
            "operator_character": "SCALAR_PHASE",
            "additional_reduction_after_mass": 0,
            "verdict": "INSUFFICIENT_SCALAR_U1",
        },
        "neutrinotime_global_berry_implementation": {
            "source_ref": str(neutrinotime_source_ref),
            "current_numerical_path": "gamma<-trace(T_op); U_L<-U_L*exp(i*gamma)",
            "operator_character": "GLOBAL_U1_PHASE_AT_READOUT",
            "probability_blindness_max_delta_f64_hex": blindness_delta.hex(),
            "verdict": "INSUFFICIENT_GLOBAL_PHASE",
        },
        "temporal_chirality": {
            "source_ref": str(neutrinotime_source_ref),
            "current_source_object": "scalar/pseudoscalar_chi_n_and_Berry_phase",
            "H_mass_3x3_operator_binding": "UNRESOLVED",
            "conditional_binary_chirality_stabilizer": "U(2)xU(1)",
            "conditional_binary_chirality_projective_dimension": 4,
            "verdict": "STRUCTURALLY_INTERESTING_BUT_UNBOUND_AND_INSUFFICIENT_AS_BINARY_LABEL",
        },
        "resonance_R_S_I": {
            "source_ref": str(resonance_source_ref),
            "current_object": "scalar_overlap_probability_and_scalar_mass_relation",
            "complex_linear_J_determined": False,
            "verdict": "INSUFFICIENT_SCALAR_DATA",
        },
        "boundary_topological_source": {
            "source_ref": str(corrected_eft_source_ref),
            "source_mechanism_status": "ALLOWED_NONTRIVIAL_SOURCE_ROUTE",
            "H_mass_3x3_operator_binding": "UNRESOLVED",
            "verdict": "MECHANISM_ROUTE_NOT_YET_AN_IDENTIFYING_INVARIANT",
        },
        "axial_or_mass_mixing_source": {
            "source_ref": str(corrected_eft_source_ref),
            "source_mechanism_status": "PHYSICALLY_NONTRIVIAL_EFT_ROUTE",
            "H_mass_3x3_operator_binding": "UNRESOLVED",
            "verdict": "PROMISING_SOURCE_CLASS_REQUIRES_TYPED_MATRIX",
        },
    }

    theorem = {
        "name": "NONDEGENERATE_MASS_PLUS_CONNECTED_NONCOMMUTING_INVARIANT",
        "premise_1": "M^2 has three distinct eigenvalues, so residual ambiguity is D=diag(e^{i theta_1},e^{i theta_2},e^{i theta_3})",
        "premise_2": "A_T is a source-bound Hermitian 3x3 operator represented in the same mass basis",
        "premise_3": "the graph of nonzero off-diagonal entries of A_T is connected",
        "consequence": "D A_T D^dagger=A_T forces theta_1=theta_2=theta_3 on every connected edge",
        "residual_group": "U(1)_global",
        "projective_residual_dimension": connected["projective_phase_dimension"],
        "minimal_connected_offdiagonal_edges_for_three_modes": 2,
        "constructive_connected_support": connected_support,
        "constructive_connected_support_result": connected,
        "disconnected_control_support": disconnected_support,
        "disconnected_control_result": disconnected,
        "physical_selection_status": "THEOREM_ONLY_SOURCE_OPERATOR_NOT_YET_DERIVED",
    }

    core = {
        "schema": SCHEMA,
        "audit_id": str(audit_id),
        "auditor": "BELZEBUB",
        "candidate_generator": "GREMLIN",
        "question": "Which existing invariant can reduce the residual U(3) freedom of J without a new arbitrary continuous parameter?",
        "baseline_group": "U(3)",
        "baseline_dimension": 9,
        "baseline_projective_dimension": 8,
        "delta_m21_sq_eV2_f64_hex": dm21.hex(),
        "delta_m31_sq_eV2_f64_hex": dm31.hex(),
        "candidates": candidates,
        "identifiability_theorem": theorem,
        "strongest_current_reduction": "U(3)->U(1)^3_FROM_NONDEGENERATE_MASS_SPECTRUM",
        "strongest_existing_temporal_object_status": "NEUTRINOTIME_T_HAT_IS_STRUCTURALLY_RELEVANT_BUT_CURRENT_NUMERICAL_IMPLEMENTATION_COLLAPSES_TO_GLOBAL_U1",
        "next_required_object": "SOURCE_BOUND_TRACELESS_OR_NONSCALAR_HERMITIAN_3x3_TEMPORAL_OR_MASS_MIXING_OPERATOR_WITH_CONNECTED_OFFDIAGONAL_SUPPORT",
        "next_required_intertwining_contract": "A_mass J = J A_intention together with M_mass J = J M_intention or an equivalent declared paired representation",
        "belzebub_verdict": "MASS_REDUCES_BUT_DOES_NOT_IDENTIFY_J__CONNECTED_NONCOMMUTING_SECOND_INVARIANT_WOULD_IDENTIFY_PROJECTIVELY",
        "canon_status": "CANDIDATE",
        "execution_status": "RESEARCH_AUDIT_ONLY",
        "epistemic_status": str(epistemic_status),
    }
    return {**core, "J_invariant_reduction_audit_commitment": _seal(core)}


def validate_J_invariant_reduction_audit_v20(receipt: Mapping[str, Any]) -> bool:
    if receipt.get("schema") != SCHEMA:
        raise JInvariantReductionAuditError("unsupported v2.0 schema")
    commitment = str(receipt.get("J_invariant_reduction_audit_commitment", ""))
    if len(commitment) != 64:
        raise JInvariantReductionAuditError("missing v2.0 commitment")
    try:
        bytes.fromhex(commitment)
    except ValueError as exc:
        raise JInvariantReductionAuditError("v2.0 commitment must be hexadecimal") from exc
    core = dict(receipt)
    core.pop("J_invariant_reduction_audit_commitment", None)
    if commitment != _seal(core):
        raise JInvariantReductionAuditError("v2.0 commitment mismatch")
    if receipt.get("baseline_group") != "U(3)" or receipt.get("baseline_dimension") != 9:
        raise JInvariantReductionAuditError("baseline group mismatch")
    theorem = receipt.get("identifiability_theorem")
    if not isinstance(theorem, Mapping) or theorem.get("projective_residual_dimension") != 0:
        raise JInvariantReductionAuditError("identifiability theorem mismatch")
    return True
