from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

FLAVOR_BASIS = ("nu_e", "nu_mu", "nu_tau")
BRIDGE_SCHEMA = "GREMLIN_INTENTION_FLAVOR_BRIDGE_V1_7"
BRIDGE_DOMAIN = b"GREMLIN-INTENTION-FLAVOR-BRIDGE/v1.7\x00"
COMPARISON_SCHEMA = "GREMLIN_BELZEBUB_INTENTION_FLAVOR_BRIDGE_COMPARISON_V1_7"
COMPARISON_DOMAIN = b"GREMLIN-BELZEBUB-INTENTION-FLAVOR-BRIDGE-COMPARISON/v1.7\x00"


class IntentionFlavorBridgeError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(domain: bytes, value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def _complex(value: Any, name: str) -> complex:
    try:
        z = complex(value)
    except (TypeError, ValueError) as exc:
        raise IntentionFlavorBridgeError(f"{name} must be complex-compatible") from exc
    if not math.isfinite(z.real) or not math.isfinite(z.imag):
        raise IntentionFlavorBridgeError(f"{name} must be finite")
    return z


def _enc(z: complex) -> dict[str, str]:
    return {"re_f64_hex": float(z.real).hex(), "im_f64_hex": float(z.imag).hex()}


def _state(values: Sequence[Any], name: str) -> list[complex]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or len(values) == 0:
        raise IntentionFlavorBridgeError(f"{name} must be a non-empty state vector")
    return [_complex(v, f"{name}[{i}]") for i, v in enumerate(values)]


def _require_normalized(state: Sequence[complex], name: str, tol: float = 2e-12) -> float:
    norm2 = math.fsum(abs(z) ** 2 for z in state)
    if abs(norm2 - 1.0) > tol:
        raise IntentionFlavorBridgeError(f"{name} must be normalized")
    return norm2


def _matrix(values: Sequence[Sequence[Any]], cols: int, name: str) -> list[list[complex]]:
    if not isinstance(values, Sequence) or len(values) != 3:
        raise IntentionFlavorBridgeError(f"{name} must have exactly three flavor rows")
    out: list[list[complex]] = []
    for i, row in enumerate(values):
        if not isinstance(row, Sequence) or len(row) != cols:
            raise IntentionFlavorBridgeError(f"{name}[{i}] must have {cols} columns")
        out.append([_complex(v, f"{name}[{i},{j}]") for j, v in enumerate(row)])
    return out


def _dagger(a: Sequence[Sequence[complex]]) -> list[list[complex]]:
    return [[a[i][j].conjugate() for i in range(len(a))] for j in range(len(a[0]))]


def _matmul(a: Sequence[Sequence[complex]], b: Sequence[Sequence[complex]]) -> list[list[complex]]:
    if not a or not b or len(a[0]) != len(b):
        raise IntentionFlavorBridgeError("matrix product shape mismatch")
    return [[sum((a[i][k] * b[k][j] for k in range(len(b))), 0.0j) for j in range(len(b[0]))] for i in range(len(a))]


def _matvec(a: Sequence[Sequence[complex]], x: Sequence[complex]) -> list[complex]:
    if any(len(row) != len(x) for row in a):
        raise IntentionFlavorBridgeError("matrix/vector shape mismatch")
    return [sum((row[j] * x[j] for j in range(len(x))), 0.0j) for row in a]


def _identity(n: int) -> list[list[complex]]:
    return [[1.0 + 0.0j if i == j else 0.0j for j in range(n)] for i in range(n)]


def _max_delta(a: Sequence[Sequence[complex]], b: Sequence[Sequence[complex]]) -> float:
    return max(abs(a[i][j] - b[i][j]) for i in range(len(a)) for j in range(len(a[0])))


def _isometry_residual(b: Sequence[Sequence[complex]]) -> float:
    n = len(b[0])
    return _max_delta(_matmul(_dagger(b), b), _identity(n))


def _onto_residual(b: Sequence[Sequence[complex]]) -> float:
    return _max_delta(_matmul(b, _dagger(b)), _identity(3))


def _probabilities_from_state(phi: Sequence[complex]) -> list[float]:
    p = [abs(z) ** 2 for z in phi]
    total = math.fsum(p)
    if abs(total - 1.0) > 3e-11:
        raise IntentionFlavorBridgeError("flavor state probability normalization failed")
    return p


def _encode_matrix(a: Sequence[Sequence[complex]]) -> list[list[dict[str, str]]]:
    return [[_enc(z) for z in row] for row in a]


def _encode_state(a: Sequence[complex]) -> list[dict[str, str]]:
    return [_enc(z) for z in a]


def _r_distribution(p: Sequence[float]) -> dict[str, str]:
    return {FLAVOR_BASIS[i]: float(p[i]).hex() for i in range(3)}


def build_isometry_bridge_v17(*, bridge_id: str, matrix_b: Sequence[Sequence[Any]], intention_state: Sequence[Any], source_space_ref: str, epistemic_status: str = "CANDIDATE") -> dict[str, Any]:
    psi = _state(intention_state, "intention_state")
    _require_normalized(psi, "intention_state")
    n = len(psi)
    if n > 3:
        raise IntentionFlavorBridgeError("H_I dimension exceeds flavor qutrit dimension; an isometry H_I->H_F cannot exist")
    b = _matrix(matrix_b, n, "B")
    residual = _isometry_residual(b)
    if residual > 2e-12:
        raise IntentionFlavorBridgeError(f"B is not an isometry; residual={residual}")
    phi = _matvec(b, psi)
    _require_normalized(phi, "flavor_state")
    p = _probabilities_from_state(phi)
    onto = _onto_residual(b) if n == 3 else None
    core = {
        "schema": BRIDGE_SCHEMA,
        "bridge_id": str(bridge_id),
        "bridge_kind": "ISOMETRY",
        "source_space": "H_I",
        "target_space": "H_F_FLAVOR_QUTRIT",
        "source_dimension": n,
        "target_dimension": 3,
        "B_matrix": _encode_matrix(b),
        "intention_state": _encode_state(psi),
        "flavor_state": _encode_state(phi),
        "isometry_residual_f64_hex": residual.hex(),
        "unitary_onto_flavor_space": bool(n == 3 and onto is not None and onto <= 2e-12),
        "onto_residual_f64_hex": None if onto is None else onto.hex(),
        "R_SI_typed_law": "R(nu_alpha,I)=|<nu_alpha|B|I>|^2",
        "R_flavor_distribution": _r_distribution(p),
        "deterministic_channel_admitted": True,
        "postselection_required": False,
        "physical_bridge_mechanism_status": "OPEN",
        "source_space_ref": str(source_space_ref),
        "epistemic_status": str(epistemic_status),
        "belzebub_verdict": "SURVIVED_TYPED_COHERENT_BRIDGE",
        "canon_status": "CANDIDATE",
    }
    return {**core, "intention_flavor_bridge_commitment": _seal(BRIDGE_DOMAIN, core)}


def build_postselected_projection_bridge_v17(*, bridge_id: str, matrix_b: Sequence[Sequence[Any]], intention_state: Sequence[Any], source_space_ref: str, epistemic_status: str = "CANDIDATE") -> dict[str, Any]:
    psi = _state(intention_state, "intention_state")
    _require_normalized(psi, "intention_state")
    n = len(psi)
    b = _matrix(matrix_b, n, "B")
    raw = _matvec(b, psi)
    success = math.fsum(abs(z) ** 2 for z in raw)
    if not math.isfinite(success) or success <= 0.0 or success > 1.0 + 2e-12:
        raise IntentionFlavorBridgeError("declared projection branch must have state-specific success probability in (0,1]")
    phi = [z / math.sqrt(success) for z in raw]
    p = _probabilities_from_state(phi)
    core = {
        "schema": BRIDGE_SCHEMA,
        "bridge_id": str(bridge_id),
        "bridge_kind": "POSTSELECTED_PROJECTION",
        "source_space": "H_I",
        "target_space": "H_F_FLAVOR_QUTRIT",
        "source_dimension": n,
        "target_dimension": 3,
        "B_matrix": _encode_matrix(b),
        "intention_state": _encode_state(psi),
        "conditioned_flavor_state": _encode_state(phi),
        "branch_success_probability_f64_hex": success.hex(),
        "R_SI_typed_law": "R(nu_alpha,I|success)=|<nu_alpha|B|I>|^2/<I|B^dagger B|I>",
        "R_flavor_distribution_conditioned": _r_distribution(p),
        "deterministic_channel_admitted": False,
        "postselection_required": True,
        "failure_branch_required_for_physical_channel": True,
        "global_contraction_status": "UNVERIFIED_BY_STATE_SPECIFIC_PROBE",
        "physical_bridge_mechanism_status": "OPEN",
        "source_space_ref": str(source_space_ref),
        "epistemic_status": str(epistemic_status),
        "belzebub_verdict": "SURVIVED_ONLY_AS_POSTSELECTED_BRANCH",
        "canon_status": "CANDIDATE",
    }
    return {**core, "intention_flavor_bridge_commitment": _seal(BRIDGE_DOMAIN, core)}


def build_cptp_bridge_v17(*, bridge_id: str, kraus_ops: Sequence[Sequence[Sequence[Any]]], intention_state: Sequence[Any], source_space_ref: str, epistemic_status: str = "CANDIDATE") -> dict[str, Any]:
    psi = _state(intention_state, "intention_state")
    _require_normalized(psi, "intention_state")
    n = len(psi)
    if not isinstance(kraus_ops, Sequence) or len(kraus_ops) == 0:
        raise IntentionFlavorBridgeError("at least one Kraus operator is required")
    ks = [_matrix(k, n, f"K[{idx}]") for idx, k in enumerate(kraus_ops)]
    completeness = [[0.0j for _ in range(n)] for _ in range(n)]
    for k in ks:
        term = _matmul(_dagger(k), k)
        for i in range(n):
            for j in range(n):
                completeness[i][j] += term[i][j]
    residual = _max_delta(completeness, _identity(n))
    if residual > 3e-12:
        raise IntentionFlavorBridgeError(f"Kraus completeness failed; residual={residual}")
    rho = [[0.0j for _ in range(3)] for _ in range(3)]
    for k in ks:
        y = _matvec(k, psi)
        for i in range(3):
            for j in range(3):
                rho[i][j] += y[i] * y[j].conjugate()
    trace = sum((rho[i][i] for i in range(3)), 0.0j)
    if abs(trace - 1.0) > 3e-12 or abs(trace.imag) > 3e-12:
        raise IntentionFlavorBridgeError("CPTP output trace mismatch")
    hermitian_residual = max(abs(rho[i][j] - rho[j][i].conjugate()) for i in range(3) for j in range(3))
    if hermitian_residual > 3e-12:
        raise IntentionFlavorBridgeError("CPTP output Hermiticity mismatch")
    p = [max(0.0, float(rho[i][i].real)) for i in range(3)]
    if abs(math.fsum(p) - 1.0) > 3e-12:
        raise IntentionFlavorBridgeError("CPTP flavor probability normalization failed")
    rho2 = _matmul(rho, rho)
    purity = float(sum(rho2[i][i] for i in range(3)).real)
    single_isometry = len(ks) == 1 and _isometry_residual(ks[0]) <= 3e-12
    core = {
        "schema": BRIDGE_SCHEMA,
        "bridge_id": str(bridge_id),
        "bridge_kind": "CPTP_KRAUS_CHANNEL",
        "source_space": "H_I",
        "target_space": "H_F_FLAVOR_QUTRIT",
        "source_dimension": n,
        "target_dimension": 3,
        "kraus_operators": [_encode_matrix(k) for k in ks],
        "kraus_count": len(ks),
        "kraus_completeness_residual_f64_hex": residual.hex(),
        "intention_state": _encode_state(psi),
        "flavor_density_matrix": _encode_matrix(rho),
        "flavor_state_purity_f64_hex": purity.hex(),
        "R_SI_typed_law": "R(nu_alpha,I)=Tr[Pi_alpha B(|I><I|)]",
        "R_flavor_distribution": _r_distribution(p),
        "deterministic_channel_admitted": True,
        "postselection_required": False,
        "single_kraus_isometry_special_case": single_isometry,
        "complete_positivity_witness": "EXPLICIT_KRAUS_REPRESENTATION",
        "trace_preservation_witness": "SUM_K(K^dagger K)=I_HI",
        "general_data_processing_claim_status": "STRUCTURAL_EXPECTATION_NOT_PROVED_BY_THIS_RECEIPT",
        "physical_kraus_source_status": "OPEN",
        "source_space_ref": str(source_space_ref),
        "epistemic_status": str(epistemic_status),
        "belzebub_verdict": "SURVIVED_STRUCTURALLY_UNDERDETERMINED",
        "canon_status": "CANDIDATE",
    }
    return {**core, "intention_flavor_bridge_commitment": _seal(BRIDGE_DOMAIN, core)}


def build_bridge_comparison_v17(*, isometry: Mapping[str, Any], projection: Mapping[str, Any], cptp: Mapping[str, Any]) -> dict[str, Any]:
    for item, kind in ((isometry, "ISOMETRY"), (projection, "POSTSELECTED_PROJECTION"), (cptp, "CPTP_KRAUS_CHANNEL")):
        if item.get("schema") != BRIDGE_SCHEMA or item.get("bridge_kind") != kind:
            raise IntentionFlavorBridgeError(f"comparison requires {kind} receipt")
    core = {
        "schema": COMPARISON_SCHEMA,
        "auditor": "BELZEBUB",
        "historical_operator": "R(S,I)=|<S|I>|^2",
        "typed_repair": "replace cross-space bare overlap by an explicit B:H_I->H_F or quantum channel B:L(H_I)->L(H_F)",
        "isometry_commitment": str(isometry["intention_flavor_bridge_commitment"]),
        "projection_commitment": str(projection["intention_flavor_bridge_commitment"]),
        "cptp_commitment": str(cptp["intention_flavor_bridge_commitment"]),
        "isometry_result": "ADMISSIBLE_COHERENT_SPECIAL_CASE_DIM_HI_LE_3",
        "projection_result": "CONDITIONAL_ONLY_NOT_DETERMINISTIC_WITHOUT_FAILURE_BRANCH",
        "cptp_result": "MOST_GENERAL_STRUCTURALLY_ADMISSIBLE_CLASS_BUT_MECHANISM_UNDERDETERMINED",
        "global_unitary_possible_only_if_dim_HI_eq_3": True,
        "isometry_possible_only_if_dim_HI_le_3": True,
        "canonical_bridge_selected": False,
        "selection_debt": "derive B/Kraus structure from declared physical mass-mixing/topological mechanism and constrain experimentally",
        "belzebub_verdict": "TYPE_ERROR_REPAIRED_MECHANISM_OPEN",
        "canon_status": "CANDIDATE",
    }
    return {**core, "bridge_comparison_commitment": _seal(COMPARISON_DOMAIN, core)}
