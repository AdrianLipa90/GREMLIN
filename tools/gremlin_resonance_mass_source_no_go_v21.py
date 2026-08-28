from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

SCHEMA = "GREMLIN_RESONANCE_MASS_SOURCE_NO_GO_V2_1"
DOMAIN = b"GREMLIN-RESONANCE-MASS-SOURCE-NO-GO/v2.1\\x00"


class ResonanceMassSourceNoGoError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(DOMAIN + _canonical(value), digest_size=32).hexdigest()


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise ResonanceMassSourceNoGoError(f"{name} must be finite")
    return x


def resonance_triplet_from_splittings_v21(*, mu0_eV2: Any, R1: Any, delta_m21_sq_eV2: Any, delta_m31_sq_eV2: Any) -> tuple[float, float, float]:
    mu0 = _finite(mu0_eV2, "mu0_eV2")
    r1 = _finite(R1, "R1")
    dm21 = _finite(delta_m21_sq_eV2, "delta_m21_sq_eV2")
    dm31 = _finite(delta_m31_sq_eV2, "delta_m31_sq_eV2")
    if mu0 <= 0.0:
        raise ResonanceMassSourceNoGoError("mu0_eV2 must be positive")
    r2 = r1 - dm21 / mu0
    r3 = r1 - dm31 / mu0
    values = (r1, r2, r3)
    if any(r < 0.0 or r > 1.0 for r in values):
        raise ResonanceMassSourceNoGoError("constructed resonance values must lie in [0,1]")
    return values


def reconstructed_splittings_v21(*, mu0_eV2: Any, resonances: tuple[float, float, float]) -> tuple[float, float]:
    mu0 = _finite(mu0_eV2, "mu0_eV2")
    r1, r2, r3 = resonances
    return mu0 * (r1 - r2), mu0 * (r1 - r3)


def normalized_resonant_hamiltonian_gaps_v21(resonances: tuple[float, float, float]) -> tuple[float, float]:
    if any(r <= 0.0 or r > 1.0 for r in resonances):
        raise ResonanceMassSourceNoGoError("positive resonances in (0,1] are required for log gaps")
    logs = [math.log(1.0 / r) for r in resonances]
    return logs[1] - logs[0], logs[2] - logs[0]


def build_resonance_mass_source_no_go_v21(
    *,
    audit_id: str,
    delta_m21_sq_eV2: Any,
    delta_m31_sq_eV2: Any,
    witness_a_mu0_eV2: Any,
    witness_a_R1: Any,
    witness_b_mu0_eV2: Any,
    witness_b_R1: Any,
    mass_resonance_source_ref: str,
    resonant_hamiltonian_source_ref: str,
    epistemic_status: str = "CANDIDATE",
) -> dict[str, Any]:
    if not str(audit_id):
        raise ResonanceMassSourceNoGoError("audit_id must be non-empty")
    dm21 = _finite(delta_m21_sq_eV2, "delta_m21_sq_eV2")
    dm31 = _finite(delta_m31_sq_eV2, "delta_m31_sq_eV2")
    if dm21 == 0.0 or dm31 == 0.0 or dm21 == dm31:
        raise ResonanceMassSourceNoGoError("two distinct nonzero mass-squared splittings are required")
    for value, name in ((mass_resonance_source_ref, "mass_resonance_source_ref"), (resonant_hamiltonian_source_ref, "resonant_hamiltonian_source_ref"), (epistemic_status, "epistemic_status")):
        if not str(value):
            raise ResonanceMassSourceNoGoError(f"{name} must be non-empty")

    mu_a = _finite(witness_a_mu0_eV2, "witness_a_mu0_eV2")
    mu_b = _finite(witness_b_mu0_eV2, "witness_b_mu0_eV2")
    ra = resonance_triplet_from_splittings_v21(mu0_eV2=mu_a, R1=witness_a_R1, delta_m21_sq_eV2=dm21, delta_m31_sq_eV2=dm31)
    rb = resonance_triplet_from_splittings_v21(mu0_eV2=mu_b, R1=witness_b_R1, delta_m21_sq_eV2=dm21, delta_m31_sq_eV2=dm31)
    d_a = reconstructed_splittings_v21(mu0_eV2=mu_a, resonances=ra)
    d_b = reconstructed_splittings_v21(mu0_eV2=mu_b, resonances=rb)
    gaps_a = normalized_resonant_hamiltonian_gaps_v21(ra)
    gaps_b = normalized_resonant_hamiltonian_gaps_v21(rb)

    same_target = max(abs(d_a[0]-dm21), abs(d_a[1]-dm31), abs(d_b[0]-dm21), abs(d_b[1]-dm31)) <= 1e-15
    different_source = max(abs(ra[i]-rb[i]) for i in range(3)) > 1e-9
    different_hst = max(abs(gaps_a[i]-gaps_b[i]) for i in range(2)) > 1e-9
    survived = same_target and different_source and different_hst

    core = {
        "schema": SCHEMA,
        "audit_id": str(audit_id),
        "auditor": "BELZEBUB",
        "candidate_generator": "GREMLIN",
        "source_mass_resonance_law": "m_i^2=mu0*(1-R_i)",
        "implied_splitting_laws": ["Delta_m21^2=mu0*(R1-R2)", "Delta_m31^2=mu0*(R1-R3)"],
        "delta_m21_sq_eV2_f64_hex": dm21.hex(),
        "delta_m31_sq_eV2_f64_hex": dm31.hex(),
        "witness_a": {
            "mu0_eV2_f64_hex": mu_a.hex(),
            "R": [r.hex() for r in ra],
            "reconstructed_delta_m21_sq_eV2_f64_hex": d_a[0].hex(),
            "reconstructed_delta_m31_sq_eV2_f64_hex": d_a[1].hex(),
            "normalized_HsT_log_gaps": [g.hex() for g in gaps_a],
        },
        "witness_b": {
            "mu0_eV2_f64_hex": mu_b.hex(),
            "R": [r.hex() for r in rb],
            "reconstructed_delta_m21_sq_eV2_f64_hex": d_b[0].hex(),
            "reconstructed_delta_m31_sq_eV2_f64_hex": d_b[1].hex(),
            "normalized_HsT_log_gaps": [g.hex() for g in gaps_b],
        },
        "same_mass_splittings": same_target,
        "different_resonance_triplets": different_source,
        "different_normalized_resonant_hamiltonian_gaps": different_hst,
        "continuous_family_parameterization": "for any admissible mu0 and R1: R2=R1-Delta_m21^2/mu0; R3=R1-Delta_m31^2/mu0",
        "mass_resonance_source_ref": str(mass_resonance_source_ref),
        "resonant_hamiltonian_source_ref": str(resonant_hamiltonian_source_ref),
        "source_side_M_I_identified": False,
        "remaining_degrees": ["mu0 normalization", "one absolute resonance/absolute mass anchor", "three-mode symbolic-state selection"],
        "escape_conditions": [
            "source-derived mu0 plus one absolute R_i or absolute m_i^2 anchor",
            "an independent source law fixing the absolute resonance origin and scale",
            "a directly derived three-mode spectral matching between H_sT projectors and neutrino mass projectors",
        ],
        "belzebub_verdict": "CURRENT_MASS_SPLITTINGS_DO_NOT_IDENTIFY_RESONANCE_SOURCE_SPECTRUM" if survived else "WITNESS_INCONCLUSIVE",
        "canon_status": "CANDIDATE",
        "execution_status": "RESEARCH_AUDIT_ONLY",
        "epistemic_status": str(epistemic_status),
    }
    return {**core, "resonance_mass_source_no_go_commitment": _seal(core)}


def validate_resonance_mass_source_no_go_v21(receipt: Mapping[str, Any]) -> bool:
    if receipt.get("schema") != SCHEMA:
        raise ResonanceMassSourceNoGoError("unsupported v2.1 schema")
    commitment = str(receipt.get("resonance_mass_source_no_go_commitment", ""))
    if len(commitment) != 64:
        raise ResonanceMassSourceNoGoError("missing v2.1 commitment")
    try:
        bytes.fromhex(commitment)
    except ValueError as exc:
        raise ResonanceMassSourceNoGoError("v2.1 commitment must be hexadecimal") from exc
    core = dict(receipt)
    core.pop("resonance_mass_source_no_go_commitment", None)
    if commitment != _seal(core):
        raise ResonanceMassSourceNoGoError("v2.1 commitment mismatch")
    return True
