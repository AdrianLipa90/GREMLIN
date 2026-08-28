from __future__ import annotations

import cmath
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from tools.gremlin_three_flavor_neutrino_adapter_v15 import FLAVORS, validate_three_flavor_neutrino_propagation_v15

AUDIT_SCHEMA = "GREMLIN_BELZEBUB_FLAVOR_INFORMATION_AUDIT_V1_6"
AUDIT_DOMAIN = b"GREMLIN-BELZEBUB-FLAVOR-INFORMATION-AUDIT/v1.6\x00"

class BelzebubFlavorInformationAuditError(ValueError):
    pass

def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def _seal(value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(AUDIT_DOMAIN + _canonical(value), digest_size=32).hexdigest()

def _from_hex(value: Any, name: str) -> float:
    try:
        x = float.fromhex(str(value))
    except (TypeError, ValueError) as exc:
        raise BelzebubFlavorInformationAuditError(f"{name} must be a binary64 hex float") from exc
    if not math.isfinite(x):
        raise BelzebubFlavorInformationAuditError(f"{name} must be finite")
    return x

def _decode_complex(value: Mapping[str, Any], name: str) -> complex:
    if not isinstance(value, Mapping):
        raise BelzebubFlavorInformationAuditError(f"{name} must be a complex encoding")
    return complex(_from_hex(value.get("re_f64_hex"), f"{name}.re"), _from_hex(value.get("im_f64_hex"), f"{name}.im"))

def _decode_unitary(value: Any, name: str) -> list[list[complex]]:
    if not isinstance(value, list) or len(value) != 3 or any(not isinstance(row, list) or len(row) != 3 for row in value):
        raise BelzebubFlavorInformationAuditError(f"{name} must be encoded 3x3")
    return [[_decode_complex(value[i][j], f"{name}[{i},{j}]") for j in range(3)] for i in range(3)]

def _decode_probabilities(value: Any, name: str) -> list[list[float]]:
    if not isinstance(value, list) or len(value) != 3 or any(not isinstance(row, list) or len(row) != 3 for row in value):
        raise BelzebubFlavorInformationAuditError(f"{name} must be encoded 3x3")
    return [[_from_hex(value[i][j], f"{name}[{i},{j}]") for j in range(3)] for i in range(3)]

def shannon_bits_v16(probabilities: Sequence[float]) -> float:
    values = [float(p) for p in probabilities]
    if any((not math.isfinite(p)) or p < -1e-14 for p in values):
        raise BelzebubFlavorInformationAuditError("probabilities must be finite and non-negative")
    values = [max(0.0, p) for p in values]
    if abs(math.fsum(values) - 1.0) > 2e-10:
        raise BelzebubFlavorInformationAuditError("probabilities must sum to one")
    return -math.fsum(p * math.log2(p) for p in values if p > 0.0)

def uniform_prior_mutual_information_bits_v16(channel: Sequence[Sequence[float]]) -> dict[str, float]:
    if len(channel) != 3 or any(len(row) != 3 for row in channel):
        raise BelzebubFlavorInformationAuditError("channel must be 3x3")
    column_entropies = [shannon_bits_v16([channel[b][a] for b in range(3)]) for a in range(3)]
    output = [math.fsum(channel[b][a] for a in range(3)) / 3.0 for b in range(3)]
    h_y = shannon_bits_v16(output)
    h_y_given_x = math.fsum(column_entropies) / 3.0
    return {"H_Y_bits": h_y, "H_Y_given_X_bits": h_y_given_x, "I_XY_bits": max(0.0, h_y - h_y_given_x)}

def _probability_matrix_from_unitary(u: Sequence[Sequence[complex]]) -> list[list[float]]:
    return [[abs(u[b][a]) ** 2 for a in range(3)] for b in range(3)]

def _max_probability_delta(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> float:
    return max(abs(a[i][j] - b[i][j]) for i in range(3) for j in range(3))

def phase_alias_witness_v16(delta_rad: float = 0.37) -> dict[str, float]:
    delta = float(delta_rad)
    if not math.isfinite(delta) or not (0.0 < delta < math.pi):
        raise BelzebubFlavorInformationAuditError("delta_rad must lie in (0,pi)")
    alias = math.pi - delta
    p1 = math.sin(delta) ** 2
    p2 = math.sin(alias) ** 2
    return {"delta_1_rad": delta, "delta_2_rad": alias, "sin2_delta_1": p1, "sin2_delta_2": p2, "probability_difference": abs(p1 - p2)}

def build_belzebub_flavor_information_audit_v16(*, propagation: Mapping[str, Any], adapter: Mapping[str, Any], channel: str = "standard") -> dict[str, Any]:
    validate_three_flavor_neutrino_propagation_v15(propagation, adapter=adapter)
    if channel not in {"standard", "total"}:
        raise BelzebubFlavorInformationAuditError("channel must be standard or total")
    p_key = "P_standard" if channel == "standard" else "P_total"
    u_key = "U_standard" if channel == "standard" else "U_total"
    p = _decode_probabilities(propagation[p_key], p_key)
    u = _decode_unitary(propagation[u_key], u_key)
    conservation = max(abs(math.fsum(p[b][a] for b in range(3)) - 1.0) for a in range(3))
    entropies = [shannon_bits_v16([p[b][a] for b in range(3)]) for a in range(3)]
    max_entropy = math.log2(3.0)
    entropy_bound_residual = max(max(max(0.0, -h), max(0.0, h - max_entropy)) for h in entropies)
    channel_info = uniform_prior_mutual_information_bits_v16(p)
    global_phase = cmath.exp(1j * 0.731)
    p_global = _probability_matrix_from_unitary([[global_phase * u[i][j] for j in range(3)] for i in range(3)])
    global_phase_delta = _max_probability_delta(p, p_global)
    phases = (0.31, -0.77, 1.19)
    d = [cmath.exp(1j * x) for x in phases]
    u_rephased = [[d[i].conjugate() * u[i][j] * d[j] for j in range(3)] for i in range(3)]
    rephase_delta = _max_probability_delta(p, _probability_matrix_from_unitary(u_rephased))
    norms = [math.fsum(abs(u[b][a]) ** 2 for b in range(3)) for a in range(3)]
    purities = [n * n for n in norms]
    alias = phase_alias_witness_v16()
    checks = {
        "A01_probability_normalization": conservation <= 2e-10,
        "A02_shannon_alphabet_bound": entropy_bound_residual <= 2e-12,
        "A03_global_phase_blindness": global_phase_delta <= 2e-14,
        "A04_flavor_basis_rephasing_blindness": rephase_delta <= 2e-14,
        "A05_unitary_pure_state_preservation": max(abs(n - 1.0) for n in norms) <= 2e-11 and max(abs(q - 1.0) for q in purities) <= 4e-11,
        "A06_phase_to_probability_noninjective": alias["probability_difference"] <= 2e-15,
        "A07_uniform_prior_information_bound": -2e-12 <= channel_info["I_XY_bits"] <= max_entropy + 2e-12,
    }
    core = {
        "schema": AUDIT_SCHEMA,
        "auditor": "BELZEBUB",
        "candidate_generator": "GREMLIN",
        "input_propagation_commitment": str(propagation["three_flavor_neutrino_propagation_commitment"]),
        "input_hamiltonian_commitment": str(adapter["three_flavor_neutrino_hamiltonian_commitment"]),
        "channel": channel,
        "flavor_alphabet": list(FLAVORS),
        "flavor_alphabet_capacity_upper_bound_bits": max_entropy.hex(),
        "flavor_measurement_entropy_bits_by_initial_flavor": {FLAVORS[a]: entropies[a].hex() for a in range(3)},
        "uniform_prior_H_Y_bits": channel_info["H_Y_bits"].hex(),
        "uniform_prior_H_Y_given_X_bits": channel_info["H_Y_given_X_bits"].hex(),
        "uniform_prior_I_XY_bits": channel_info["I_XY_bits"].hex(),
        "channel_information_law": "I(X;Y)=H(Y)-H(Y|X), X=prepared flavor, Y=measured flavor",
        "measurement_entropy_equals_quantum_entropy": False,
        "quantum_state_entropy_status": "PURE_UNITARY_EVOLUTION_ENTROPY_ZERO",
        "flavor_probability_uniquely_reconstructs_phase": False,
        "information_creation_by_unitary_oscillation": False,
        "extra_relational_interaction_required_for_standard_flavor_readout": False,
        "time_phase_identity_status": "UPSTREAM_IDT_PREMISE_OR_DERIVATION_TARGET",
        "supported_candidate_claims": [
            "phase evolution modulates the neutrino flavor-measurement channel",
            "prepared and measured flavors define a three-symbol classical readout channel",
            "mutual information quantifies retained flavor-label information for a declared preparation prior",
        ],
        "blocked_promotions": [
            "flavor Shannon entropy equals intrinsic quantum entropy",
            "flavor probabilities uniquely reconstruct temporal phase",
            "unitary flavor oscillation creates information",
            "R(S,I) is identical to P(alpha->beta) without an explicit isomorphism proof",
            "time equals phase without the upstream IDT derivation",
        ],
        "checks": checks,
        "belzebub_verdict": "SURVIVED_WITH_NARROWED_CLAIM" if all(checks.values()) else "FAILED_AUDIT",
        "canon_status": "CANDIDATE",
        "execution_status": "RESEARCH_AUDIT_ONLY",
    }
    return {**core, "belzebub_flavor_information_audit_commitment": _seal(core)}

def validate_belzebub_flavor_information_audit_v16(receipt: Mapping[str, Any], *, propagation: Mapping[str, Any], adapter: Mapping[str, Any]) -> bool:
    expected = build_belzebub_flavor_information_audit_v16(propagation=propagation, adapter=adapter, channel=str(receipt.get("channel")))
    if receipt != expected:
        raise BelzebubFlavorInformationAuditError("BELZEBUB audit receipt mismatch")
    return True
