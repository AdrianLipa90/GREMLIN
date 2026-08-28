from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

SCHEMA = "GREMLIN_NEUTRINO_ABSOLUTE_SCALE_CROSSCHECK_V2_2"
DOMAIN = b"GREMLIN-NEUTRINO-ABSOLUTE-SCALE-CROSSCHECK/v2.2\x00"


class NeutrinoAbsoluteScaleCrosscheckError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(DOMAIN + _canonical(value), digest_size=32).hexdigest()


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise NeutrinoAbsoluteScaleCrosscheckError(f"{name} must be finite")
    return x


def absolute_masses_from_ratio_and_splittings_v22(*, m2_over_m1: Any, delta_m21_sq_eV2: Any, delta_m31_sq_eV2: Any) -> tuple[float, float, float]:
    r = _finite(m2_over_m1, "m2_over_m1")
    dm21 = _finite(delta_m21_sq_eV2, "delta_m21_sq_eV2")
    dm31 = _finite(delta_m31_sq_eV2, "delta_m31_sq_eV2")
    if r <= 1.0:
        raise NeutrinoAbsoluteScaleCrosscheckError("m2_over_m1 must exceed one for normal ordered positive dm21")
    if dm21 <= 0.0 or dm31 <= dm21:
        raise NeutrinoAbsoluteScaleCrosscheckError("normal-ordering splittings must satisfy dm31>dm21>0")
    m1_sq = dm21 / (r*r - 1.0)
    m2_sq = r*r * m1_sq
    m3_sq = m1_sq + dm31
    return math.sqrt(m1_sq), math.sqrt(m2_sq), math.sqrt(m3_sq)


def resonance_triplet_from_absolute_masses_v22(*, masses_eV: Sequence[Any], mu0_eV2: Any) -> tuple[float, float, float]:
    if len(masses_eV) != 3:
        raise NeutrinoAbsoluteScaleCrosscheckError("three masses are required")
    masses = [_finite(v, f"mass[{i}]") for i, v in enumerate(masses_eV)]
    mu0 = _finite(mu0_eV2, "mu0_eV2")
    if any(m <= 0.0 for m in masses) or mu0 <= 0.0:
        raise NeutrinoAbsoluteScaleCrosscheckError("masses and mu0 must be positive")
    values = tuple(1.0 - (m*m)/mu0 for m in masses)
    if any(r < 0.0 or r > 1.0 for r in values):
        raise NeutrinoAbsoluteScaleCrosscheckError("mu0 must keep all resonance values in [0,1]")
    return values


def normalized_hst_gaps_v22(resonances: Sequence[Any]) -> tuple[float, float]:
    if len(resonances) != 3:
        raise NeutrinoAbsoluteScaleCrosscheckError("three resonances are required")
    r = [_finite(v, f"R[{i}]") for i,v in enumerate(resonances)]
    if any(v <= 0.0 or v > 1.0 for v in r):
        raise NeutrinoAbsoluteScaleCrosscheckError("resonances must lie in (0,1]")
    w = [math.log(1.0/v) for v in r]
    return w[1]-w[0], w[2]-w[0]


def build_neutrino_absolute_scale_crosscheck_v22(
    *,
    audit_id: str,
    delta_m21_sq_eV2: Any,
    delta_m31_sq_eV2: Any,
    structural_ratio_squared: Any = 7.0/6.0,
    declared_sum_eV: Any = 0.098,
    mu0_witness_a_eV2: Any = 0.01,
    mu0_witness_b_eV2: Any = 0.02,
    ratio_source_ref: str,
    declared_sum_source_ref: str,
    mass_resonance_source_ref: str,
    epistemic_status: str = "CANDIDATE",
) -> dict[str, Any]:
    if not str(audit_id):
        raise NeutrinoAbsoluteScaleCrosscheckError("audit_id must be non-empty")
    ratio_sq = _finite(structural_ratio_squared, "structural_ratio_squared")
    if ratio_sq <= 1.0:
        raise NeutrinoAbsoluteScaleCrosscheckError("structural_ratio_squared must exceed one")
    ratio = math.sqrt(ratio_sq)
    dm21 = _finite(delta_m21_sq_eV2, "delta_m21_sq_eV2")
    dm31 = _finite(delta_m31_sq_eV2, "delta_m31_sq_eV2")
    declared_sum = _finite(declared_sum_eV, "declared_sum_eV")
    if declared_sum <= 0.0:
        raise NeutrinoAbsoluteScaleCrosscheckError("declared_sum_eV must be positive")
    for value,name in ((ratio_source_ref,"ratio_source_ref"),(declared_sum_source_ref,"declared_sum_source_ref"),(mass_resonance_source_ref,"mass_resonance_source_ref"),(epistemic_status,"epistemic_status")):
        if not str(value):
            raise NeutrinoAbsoluteScaleCrosscheckError(f"{name} must be non-empty")

    masses = absolute_masses_from_ratio_and_splittings_v22(m2_over_m1=ratio, delta_m21_sq_eV2=dm21, delta_m31_sq_eV2=dm31)
    mass_sum = math.fsum(masses)
    sum_delta = mass_sum - declared_sum
    sum_relative = abs(sum_delta) / declared_sum
    reconstructed_dm21 = masses[1]**2 - masses[0]**2
    reconstructed_dm31 = masses[2]**2 - masses[0]**2

    mu_a = _finite(mu0_witness_a_eV2, "mu0_witness_a_eV2")
    mu_b = _finite(mu0_witness_b_eV2, "mu0_witness_b_eV2")
    ra = resonance_triplet_from_absolute_masses_v22(masses_eV=masses, mu0_eV2=mu_a)
    rb = resonance_triplet_from_absolute_masses_v22(masses_eV=masses, mu0_eV2=mu_b)
    ga = normalized_hst_gaps_v22(ra)
    gb = normalized_hst_gaps_v22(rb)
    mu0_nonunique = max(abs(ra[i]-rb[i]) for i in range(3)) > 1e-9 and max(abs(ga[i]-gb[i]) for i in range(2)) > 1e-9

    exact_7_6 = abs(ratio_sq - 7.0/6.0) <= 1e-15
    analytic_m1_sq_factor = 6.0 if exact_7_6 else 1.0/(ratio_sq-1.0)
    analytic_m2_sq_factor = 7.0 if exact_7_6 else ratio_sq/(ratio_sq-1.0)

    core = {
        "schema": SCHEMA,
        "audit_id": str(audit_id),
        "auditor": "BELZEBUB",
        "candidate_generator": "GREMLIN",
        "structural_ratio_squared_f64_hex": ratio_sq.hex(),
        "m2_over_m1_f64_hex": ratio.hex(),
        "delta_m21_sq_eV2_f64_hex": dm21.hex(),
        "delta_m31_sq_eV2_f64_hex": dm31.hex(),
        "absolute_masses_eV_f64_hex": [m.hex() for m in masses],
        "absolute_masses_meV": [1000.0*m for m in masses],
        "mass_sum_eV_f64_hex": mass_sum.hex(),
        "mass_sum_meV": 1000.0*mass_sum,
        "declared_sum_eV_f64_hex": declared_sum.hex(),
        "declared_sum_not_used_to_derive_masses": True,
        "sum_crosscheck_delta_eV_f64_hex": sum_delta.hex(),
        "sum_crosscheck_relative_error_f64_hex": sum_relative.hex(),
        "reconstructed_delta_m21_sq_eV2_f64_hex": reconstructed_dm21.hex(),
        "reconstructed_delta_m31_sq_eV2_f64_hex": reconstructed_dm31.hex(),
        "analytic_when_ratio_sq_7_over_6": {
            "m1_squared_factor_times_dm21": analytic_m1_sq_factor,
            "m2_squared_factor_times_dm21": analytic_m2_sq_factor,
            "m3_squared_law": "m3^2=m1^2+Delta_m31^2",
        },
        "ratio_source_ref": str(ratio_source_ref),
        "declared_sum_source_ref": str(declared_sum_source_ref),
        "absolute_neutrino_scale_status": "DERIVED_WITHIN_DECLARED_FRAMEWORK_FROM_STRUCTURAL_RATIO_PLUS_SPLITTINGS",
        "crosscheck_status": "INPUT_INDEPENDENT_INTERNAL_CONSISTENCY_CHECK_NOT_INDEPENDENT_DATASET",
        "mass_resonance_source_ref": str(mass_resonance_source_ref),
        "mass_resonance_mu0_status": "STILL_UNBOUND_GENERIC_MASS_SCALE_PARAMETER",
        "mu0_witness_a_eV2_f64_hex": mu_a.hex(),
        "mu0_witness_b_eV2_f64_hex": mu_b.hex(),
        "mu0_witness_a_R": [v.hex() for v in ra],
        "mu0_witness_b_R": [v.hex() for v in rb],
        "mu0_witness_a_normalized_HsT_gaps": [v.hex() for v in ga],
        "mu0_witness_b_normalized_HsT_gaps": [v.hex() for v in gb],
        "mu0_remains_nonunique_after_absolute_mass_scale": mu0_nonunique,
        "remaining_source_spectrum_degrees": ["mu0 normalization", "three-mode symbolic-projector selection"],
        "belzebub_verdict": "ABSOLUTE_NEUTRINO_MASS_SCALE_CANDIDATE_CLOSED__RESONANCE_MU0_AND_PROJECTORS_STILL_OPEN" if mu0_nonunique else "WITNESS_INCONCLUSIVE",
        "canon_status": "CANDIDATE",
        "execution_status": "RESEARCH_AUDIT_ONLY",
        "epistemic_status": str(epistemic_status),
    }
    return {**core, "neutrino_absolute_scale_crosscheck_commitment": _seal(core)}


def validate_neutrino_absolute_scale_crosscheck_v22(receipt: Mapping[str, Any]) -> bool:
    if receipt.get("schema") != SCHEMA:
        raise NeutrinoAbsoluteScaleCrosscheckError("unsupported v2.2 schema")
    commitment = str(receipt.get("neutrino_absolute_scale_crosscheck_commitment", ""))
    if len(commitment) != 64:
        raise NeutrinoAbsoluteScaleCrosscheckError("missing v2.2 commitment")
    try:
        bytes.fromhex(commitment)
    except ValueError as exc:
        raise NeutrinoAbsoluteScaleCrosscheckError("v2.2 commitment must be hexadecimal") from exc
    core = dict(receipt)
    core.pop("neutrino_absolute_scale_crosscheck_commitment", None)
    if commitment != _seal(core):
        raise NeutrinoAbsoluteScaleCrosscheckError("v2.2 commitment mismatch")
    return True
