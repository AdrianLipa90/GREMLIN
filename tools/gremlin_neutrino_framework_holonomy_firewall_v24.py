from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

SCHEMA = "GREMLIN_NEUTRINO_FRAMEWORK_HOLONOMY_FIREWALL_V2_4"
DOMAIN = b"GREMLIN-NEUTRINO-FRAMEWORK-HOLONOMY-FIREWALL/v2.4\x00"


class NeutrinoFrameworkHolonomyFirewallError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(DOMAIN + _canonical(value), digest_size=32).hexdigest()


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise NeutrinoFrameworkHolonomyFirewallError(f"{name} must be finite")
    return x


def graded_projection_masses_v24(*, delta_m21_sq_eV2: Any, delta_m31_sq_eV2: Any, ratio_squared: Any = 7.0/6.0) -> tuple[float, float, float]:
    dm21 = _finite(delta_m21_sq_eV2, "delta_m21_sq_eV2")
    dm31 = _finite(delta_m31_sq_eV2, "delta_m31_sq_eV2")
    ratio_sq = _finite(ratio_squared, "ratio_squared")
    if dm21 <= 0.0 or dm31 <= dm21 or ratio_sq <= 1.0:
        raise NeutrinoFrameworkHolonomyFirewallError("normal-ordering inputs and ratio_squared>1 are required")
    m1_sq = dm21 / (ratio_sq - 1.0)
    return math.sqrt(m1_sq), math.sqrt(ratio_sq * m1_sq), math.sqrt(m1_sq + dm31)


def tetrahedron_ratio_masses_from_dm21_v24(*, delta_m21_sq_eV2: Any, ratios: Sequence[Any] = (1.0,2.0,10.0)) -> tuple[float, float, float]:
    dm21 = _finite(delta_m21_sq_eV2, "delta_m21_sq_eV2")
    if len(ratios) != 3:
        raise NeutrinoFrameworkHolonomyFirewallError("three tetrahedron ratios are required")
    r = [_finite(v, f"ratios[{i}]") for i,v in enumerate(ratios)]
    if dm21 <= 0.0 or r[0] <= 0.0 or r[1] <= r[0] or r[2] <= r[1]:
        raise NeutrinoFrameworkHolonomyFirewallError("positive ordered tetrahedron ratios are required")
    denom = r[1]*r[1] - r[0]*r[0]
    if denom <= 0.0:
        raise NeutrinoFrameworkHolonomyFirewallError("tetrahedron ratios must define positive dm21")
    scale = math.sqrt(dm21 / denom)
    return tuple(scale*v for v in r)


def splittings_from_masses_v24(masses: Sequence[Any]) -> tuple[float,float]:
    if len(masses) != 3:
        raise NeutrinoFrameworkHolonomyFirewallError("three masses are required")
    m = [_finite(v, f"mass[{i}]") for i,v in enumerate(masses)]
    if any(v <= 0.0 for v in m):
        raise NeutrinoFrameworkHolonomyFirewallError("masses must be positive")
    return m[1]*m[1]-m[0]*m[0], m[2]*m[2]-m[0]*m[0]


def build_neutrino_framework_holonomy_firewall_v24(
    *,
    audit_id: str,
    delta_m21_sq_eV2: Any,
    delta_m31_sq_eV2: Any,
    graded_ratio_squared: Any = 7.0/6.0,
    tetrahedron_ratios: Sequence[Any] = (1.0,2.0,10.0),
    tetrahedron_displayed_masses_eV: Sequence[Any] = (0.00501,0.01002,0.0501),
    graded_source_ref: str,
    tetrahedron_source_ref: str,
    epistemic_status: str = "CANDIDATE",
) -> dict[str, Any]:
    if not str(audit_id):
        raise NeutrinoFrameworkHolonomyFirewallError("audit_id must be non-empty")
    dm21 = _finite(delta_m21_sq_eV2, "delta_m21_sq_eV2")
    dm31 = _finite(delta_m31_sq_eV2, "delta_m31_sq_eV2")
    ratio_sq = _finite(graded_ratio_squared, "graded_ratio_squared")
    if len(tetrahedron_ratios) != 3 or len(tetrahedron_displayed_masses_eV) != 3:
        raise NeutrinoFrameworkHolonomyFirewallError("three tetrahedron ratios and displayed masses are required")
    tr = tuple(_finite(v, f"tetrahedron_ratios[{i}]") for i,v in enumerate(tetrahedron_ratios))
    displayed = tuple(_finite(v, f"tetrahedron_displayed_masses_eV[{i}]") for i,v in enumerate(tetrahedron_displayed_masses_eV))
    for value,name in ((graded_source_ref,"graded_source_ref"),(tetrahedron_source_ref,"tetrahedron_source_ref"),(epistemic_status,"epistemic_status")):
        if not str(value):
            raise NeutrinoFrameworkHolonomyFirewallError(f"{name} must be non-empty")

    graded = graded_projection_masses_v24(delta_m21_sq_eV2=dm21, delta_m31_sq_eV2=dm31, ratio_squared=ratio_sq)
    tetra_norm = tetrahedron_ratio_masses_from_dm21_v24(delta_m21_sq_eV2=dm21, ratios=tr)
    tetra_norm_splits = splittings_from_masses_v24(tetra_norm)
    displayed_splits = splittings_from_masses_v24(displayed)

    graded_ratio = graded[1]/graded[0]
    tetra_ratio = tr[1]/tr[0]
    ratio_delta = abs(graded_ratio-tetra_ratio)
    ratio_incompatible = ratio_delta > 1e-12
    sum_graded = math.fsum(graded)
    sum_tetra_norm = math.fsum(tetra_norm)
    sum_tetra_displayed = math.fsum(displayed)
    dm31_residual = tetra_norm_splits[1]-dm31
    dm31_relative = dm31_residual/dm31

    core = {
        "schema": SCHEMA,
        "audit_id": str(audit_id),
        "auditor": "BELZEBUB",
        "candidate_generator": "GREMLIN",
        "shared_delta_m21_sq_eV2_f64_hex": dm21.hex(),
        "shared_delta_m31_sq_eV2_f64_hex": dm31.hex(),
        "graded_projection_branch": {
            "source_ref": str(graded_source_ref),
            "structural_ratio_squared_f64_hex": ratio_sq.hex(),
            "m2_over_m1_f64_hex": graded_ratio.hex(),
            "masses_eV_f64_hex": [v.hex() for v in graded],
            "mass_sum_eV_f64_hex": sum_graded.hex(),
            "status": "INTERNALLY_CONSISTENT_CANDIDATE_WITHIN_ITS_DECLARED_FRAMEWORK",
        },
        "tir_tetrahedron_branch": {
            "source_ref": str(tetrahedron_source_ref),
            "structural_ratios": [float(v) for v in tr],
            "m2_over_m1_f64_hex": tetra_ratio.hex(),
            "dm21_normalized_masses_eV_f64_hex": [v.hex() for v in tetra_norm],
            "dm21_normalized_mass_sum_eV_f64_hex": sum_tetra_norm.hex(),
            "dm21_normalized_predicted_dm31_sq_eV2_f64_hex": tetra_norm_splits[1].hex(),
            "dm31_residual_vs_shared_eV2_f64_hex": dm31_residual.hex(),
            "dm31_relative_residual_f64_hex": dm31_relative.hex(),
            "source_displayed_masses_eV_f64_hex": [v.hex() for v in displayed],
            "source_displayed_mass_sum_eV_f64_hex": sum_tetra_displayed.hex(),
            "source_displayed_splittings_eV2_f64_hex": [v.hex() for v in displayed_splits],
            "status": "DISTINCT_TIR_TETRAHEDRON_CANDIDATE",
        },
        "ratio_conflict": {
            "graded_m2_over_m1": graded_ratio,
            "tetrahedron_m2_over_m1": tetra_ratio,
            "absolute_delta_f64_hex": ratio_delta.hex(),
            "mutually_exactly_compatible": not ratio_incompatible,
        },
        "absolute_scale_shared_canon_status": "BLOCKED_CROSS_FRAMEWORK_CONFLICT" if ratio_incompatible else "NO_CONFLICT_DETECTED",
        "v22_status_preserved": "VALID_ONLY_WITHIN_GRADED_PROJECTION_BRANCH_NOT_PROMOTED_ACROSS_TIR",
        "tetrahedron_status_preserved": "VALID_AS_ITS_OWN_DECLARED_TIR_BRANCH_PENDING_CROSS_FRAMEWORK_RECONCILIATION",
        "resolution_requirements": [
            "derive an explicit transformation or limiting relation between the graded-projection neutrino ratio and the TIR tetrahedron signature",
            "or establish a supersession/authority rule with provenance",
            "or identify an empirical discriminant and retain both branches until tested",
        ],
        "J_bridge_effect": "complex-overlap v2.3 remains structurally valid, but any source-spectrum intertwining that uses absolute neutrino masses must remain branch-qualified",
        "belzebub_verdict": "HARD_FRAMEWORK_BRANCH_CONFLICT__NO_SHARED_ABSOLUTE_NEUTRINO_SCALE_PROMOTION" if ratio_incompatible else "NO_HARD_CONFLICT",
        "canon_status": "CANDIDATE",
        "execution_status": "RESEARCH_AUDIT_ONLY",
        "epistemic_status": str(epistemic_status),
    }
    return {**core, "neutrino_framework_holonomy_firewall_commitment": _seal(core)}


def validate_neutrino_framework_holonomy_firewall_v24(receipt: Mapping[str, Any]) -> bool:
    if receipt.get("schema") != SCHEMA:
        raise NeutrinoFrameworkHolonomyFirewallError("unsupported v2.4 schema")
    commitment = str(receipt.get("neutrino_framework_holonomy_firewall_commitment", ""))
    if len(commitment) != 64:
        raise NeutrinoFrameworkHolonomyFirewallError("missing v2.4 commitment")
    try:
        bytes.fromhex(commitment)
    except ValueError as exc:
        raise NeutrinoFrameworkHolonomyFirewallError("commitment must be hexadecimal") from exc
    core = dict(receipt)
    core.pop("neutrino_framework_holonomy_firewall_commitment", None)
    if commitment != _seal(core):
        raise NeutrinoFrameworkHolonomyFirewallError("v2.4 commitment mismatch")
    return True
