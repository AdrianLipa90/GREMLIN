from __future__ import annotations

import cmath
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from tools.gremlin_belzebub_flavor_information_audit_v16 import shannon_bits_v16
from tools.gremlin_three_flavor_neutrino_adapter_v15 import FLAVORS, pmns_matrix_v15

SCHEMA = "GREMLIN_INTENTION_MASS_FLAVOR_FACTORIZATION_V1_8"
DOMAIN = b"GREMLIN-INTENTION-MASS-FLAVOR-FACTORIZATION/v1.8\x00"


class IntentionMassFlavorFactorizationError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(DOMAIN + _canonical(value), digest_size=32).hexdigest()


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise IntentionMassFlavorFactorizationError(f"{name} must be finite")
    return x


def _complex(value: Any, name: str) -> complex:
    try:
        z = complex(value)
    except (TypeError, ValueError) as exc:
        raise IntentionMassFlavorFactorizationError(f"{name} must be complex-compatible") from exc
    if not math.isfinite(z.real) or not math.isfinite(z.imag):
        raise IntentionMassFlavorFactorizationError(f"{name} must be finite")
    return z


def _encode_complex(z: complex) -> dict[str, str]:
    return {"re_f64_hex": float(z.real).hex(), "im_f64_hex": float(z.imag).hex()}


def _state(values: Sequence[Any], name: str) -> list[complex]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or len(values) == 0:
        raise IntentionMassFlavorFactorizationError(f"{name} must be a non-empty vector")
    state = [_complex(v, f"{name}[{i}]") for i, v in enumerate(values)]
    norm2 = math.fsum(abs(z) ** 2 for z in state)
    if abs(norm2 - 1.0) > 2e-12:
        raise IntentionMassFlavorFactorizationError(f"{name} must be normalized")
    return state


def _matrix_3xn(values: Sequence[Sequence[Any]], n: int, name: str) -> list[list[complex]]:
    if not isinstance(values, Sequence) or len(values) != 3:
        raise IntentionMassFlavorFactorizationError(f"{name} must have three mass-basis rows")
    out: list[list[complex]] = []
    for i, row in enumerate(values):
        if not isinstance(row, Sequence) or len(row) != n:
            raise IntentionMassFlavorFactorizationError(f"{name}[{i}] must have {n} columns")
        out.append([_complex(v, f"{name}[{i},{j}]") for j, v in enumerate(row)])
    return out


def _dagger(a: Sequence[Sequence[complex]]) -> list[list[complex]]:
    return [[a[i][j].conjugate() for i in range(len(a))] for j in range(len(a[0]))]


def _matmul(a: Sequence[Sequence[complex]], b: Sequence[Sequence[complex]]) -> list[list[complex]]:
    if len(a[0]) != len(b):
        raise IntentionMassFlavorFactorizationError("matrix shape mismatch")
    return [[sum((a[i][k] * b[k][j] for k in range(len(b))), 0.0j) for j in range(len(b[0]))] for i in range(len(a))]


def _matvec(a: Sequence[Sequence[complex]], x: Sequence[complex]) -> list[complex]:
    if any(len(row) != len(x) for row in a):
        raise IntentionMassFlavorFactorizationError("matrix/vector shape mismatch")
    return [sum((row[j] * x[j] for j in range(len(x))), 0.0j) for row in a]


def _identity(n: int) -> list[list[complex]]:
    return [[1.0 + 0.0j if i == j else 0.0j for j in range(n)] for i in range(n)]


def _max_delta(a: Sequence[Sequence[complex]], b: Sequence[Sequence[complex]]) -> float:
    return max(abs(a[i][j] - b[i][j]) for i in range(len(a)) for j in range(len(a[0])))


def _isometry_residual(a: Sequence[Sequence[complex]]) -> float:
    return _max_delta(_matmul(_dagger(a), a), _identity(len(a[0])))


def _phase_gauge(phases: Sequence[Any]) -> tuple[list[float], list[float]]:
    if len(phases) != 3:
        raise IntentionMassFlavorFactorizationError("exactly three mass-eigenstate phases are required")
    raw = [_finite(v, f"mass_phase[{i}]") for i, v in enumerate(phases)]
    relative = [0.0, raw[1] - raw[0], raw[2] - raw[0]]
    return raw, relative


def _diag_phase(relative: Sequence[float]) -> list[list[complex]]:
    out = [[0.0j for _ in range(3)] for _ in range(3)]
    for i, phase in enumerate(relative):
        out[i][i] = cmath.exp(-1j * phase)
    return out


def _encode_matrix(a: Sequence[Sequence[complex]]) -> list[list[dict[str, str]]]:
    return [[_encode_complex(z) for z in row] for row in a]


def _encode_state(a: Sequence[complex]) -> list[dict[str, str]]:
    return [_encode_complex(z) for z in a]


def _probabilities(state: Sequence[complex]) -> list[float]:
    p = [abs(z) ** 2 for z in state]
    if abs(math.fsum(p) - 1.0) > 3e-11:
        raise IntentionMassFlavorFactorizationError("flavor probabilities must sum to one")
    return p


def _probability_delta(a: Sequence[float], b: Sequence[float]) -> float:
    return max(abs(a[i] - b[i]) for i in range(3))


def _factorized_state(
    *,
    j_map: Sequence[Sequence[complex]],
    intention_state: Sequence[complex],
    pmns: Sequence[Sequence[complex]],
    relative_phases: Sequence[float],
) -> tuple[list[list[complex]], list[complex], list[float]]:
    d = _diag_phase(relative_phases)
    b_t = _matmul(_matmul(pmns, d), j_map)
    flavor_state = _matvec(b_t, intention_state)
    return b_t, flavor_state, _probabilities(flavor_state)


def build_intention_mass_flavor_factorization_v18(
    *,
    factorization_id: str,
    intention_state: Sequence[Any],
    intention_to_mass_map: Sequence[Sequence[Any]],
    mass_phases_rad: Sequence[Any],
    theta12_rad: Any,
    theta13_rad: Any,
    theta23_rad: Any,
    delta_cp_rad: Any,
    intention_source_ref: str,
    phase_source_ref: str,
    pmns_source_ref: str,
    epistemic_status: str = "CANDIDATE",
) -> dict[str, Any]:
    psi_i = _state(intention_state, "intention_state")
    n = len(psi_i)
    if n > 3:
        raise IntentionMassFlavorFactorizationError("an isometric J:H_I->H_mass(C^3) requires dim(H_I)<=3")
    j_map = _matrix_3xn(intention_to_mass_map, n, "J")
    j_residual = _isometry_residual(j_map)
    if j_residual > 2e-12:
        raise IntentionMassFlavorFactorizationError(f"J must be isometric for coherent factorization; residual={j_residual}")

    t12 = _finite(theta12_rad, "theta12_rad")
    t13 = _finite(theta13_rad, "theta13_rad")
    t23 = _finite(theta23_rad, "theta23_rad")
    delta = _finite(delta_cp_rad, "delta_cp_rad")
    pmns = pmns_matrix_v15(t12, t13, t23, delta)
    raw_phases, relative = _phase_gauge(mass_phases_rad)
    b_t, flavor_state, p = _factorized_state(
        j_map=j_map,
        intention_state=psi_i,
        pmns=pmns,
        relative_phases=relative,
    )
    b_residual = _isometry_residual(b_t)
    if b_residual > 5e-12:
        raise IntentionMassFlavorFactorizationError(f"factorized bridge lost isometry; residual={b_residual}")

    # Explicit global-phase gauge control. A common shift of all mass phases must not alter readout.
    chi = 0.731
    _, shifted_relative = _phase_gauge([v + chi for v in raw_phases])
    _, _, p_shifted = _factorized_state(
        j_map=j_map,
        intention_state=psi_i,
        pmns=pmns,
        relative_phases=shifted_relative,
    )
    global_phase_readout_delta = _probability_delta(p, p_shifted)
    if global_phase_readout_delta > 2e-14:
        raise IntentionMassFlavorFactorizationError("global phase leaked into flavor readout")

    entropy_bits = shannon_bits_v16(p)
    mass_state = _matvec(j_map, psi_i)
    after_phase = _matvec(_diag_phase(relative), mass_state)
    core = {
        "schema": SCHEMA,
        "factorization_id": str(factorization_id),
        "source_space": "H_I",
        "mass_space": "H_MASS_C3",
        "flavor_space": "H_FLAVOR_C3",
        "source_dimension": n,
        "mass_dimension": 3,
        "flavor_dimension": 3,
        "factorization_law": "B_T=U_PMNS*D_DeltaPhi*J",
        "typed_readout_law": "R_alpha(I,T)=|<nu_alpha|U_PMNS D_DeltaPhi J|I>|^2",
        "J_intention_to_mass": _encode_matrix(j_map),
        "J_isometry_residual_f64_hex": j_residual.hex(),
        "J_physical_origin_status": "OPEN",
        "J_identity_special_case_status": "MATHEMATICAL_IDENTIFICATION_ONLY_NOT_PHYSICAL_PROOF",
        "intention_state": _encode_state(psi_i),
        "mass_state_before_phase": _encode_state(mass_state),
        "raw_mass_phases_rad_f64_hex": [v.hex() for v in raw_phases],
        "relative_mass_phases_rad_f64_hex": [v.hex() for v in relative],
        "phase_gauge": "PHI_1_SUBTRACTED_GLOBAL_U1_QUOTIENT",
        "phase_transport_operator": _encode_matrix(_diag_phase(relative)),
        "mass_state_after_relative_phase": _encode_state(after_phase),
        "pmns_matrix": _encode_matrix(pmns),
        "factorized_B_T": _encode_matrix(b_t),
        "factorized_isometry_residual_f64_hex": b_residual.hex(),
        "flavor_state": _encode_state(flavor_state),
        "R_flavor_distribution": {FLAVORS[i]: p[i].hex() for i in range(3)},
        "flavor_measurement_entropy_bits_f64_hex": entropy_bits.hex(),
        "global_phase_readout_delta_f64_hex": global_phase_readout_delta.hex(),
        "extra_relational_hamiltonian_required_for_this_readout": False,
        "time_phase_binding_status": "UPSTREAM_IDT_RELATIVE_PHASE_TRANSPORT_REQUIRED",
        "information_status": "READOUT_DISTRIBUTION_NOT_CREATED_BY_UNITARY_EVOLUTION",
        "intention_source_ref": str(intention_source_ref),
        "phase_source_ref": str(phase_source_ref),
        "pmns_source_ref": str(pmns_source_ref),
        "epistemic_status": str(epistemic_status),
        "belzebub_verdict": "FACTORIZATION_SURVIVED_J_MECHANISM_OPEN",
        "canon_status": "CANDIDATE",
        "execution_status": "RESEARCH_AUDIT_ONLY",
    }
    return {**core, "intention_mass_flavor_factorization_commitment": _seal(core)}


def validate_intention_mass_flavor_factorization_v18(receipt: Mapping[str, Any]) -> bool:
    if receipt.get("schema") != SCHEMA:
        raise IntentionMassFlavorFactorizationError("unsupported v1.8 schema")
    commitment = str(receipt.get("intention_mass_flavor_factorization_commitment", ""))
    if len(commitment) != 64:
        raise IntentionMassFlavorFactorizationError("missing commitment")
    try:
        bytes.fromhex(commitment)
    except ValueError as exc:
        raise IntentionMassFlavorFactorizationError("commitment must be hexadecimal") from exc
    core = dict(receipt)
    core.pop("intention_mass_flavor_factorization_commitment", None)
    if commitment != _seal(core):
        raise IntentionMassFlavorFactorizationError("v1.8 factorization commitment mismatch")
    if receipt.get("belzebub_verdict") != "FACTORIZATION_SURVIVED_J_MECHANISM_OPEN":
        raise IntentionMassFlavorFactorizationError("unexpected BELZEBUB verdict")
    return True
