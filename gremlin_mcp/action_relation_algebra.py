from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .mathematical_constitution import BLOCK, PASS, UNRESOLVED, decision_from_scalar, lattice_meet

SCHEMA = "GREMLIN_RELATIONAL_ACTION_SCOPE_ALGEBRA_V0_1"
VERSION = "0.1.0"

VISIBILITY_ORDER = {
    "LOCAL_ONLY": 0,
    "PRIVATE": 1,
    "INTERNAL": 2,
    "PUBLIC": 3,
    "UNKNOWN": 4,
}
REVERSIBILITY_RISK = {
    "REVERSIBLE": 0,
    "APPEND_ONLY": 1,
    "IRREVERSIBLE": 2,
    "UNKNOWN": 3,
}
CONSEQUENCE_RADIUS_ORDER = {
    "SINGLE_RESOURCE": 0,
    "REPOSITORY": 1,
    "ORGANIZATION": 2,
    "PUBLIC": 3,
    "GLOBAL": 4,
}
FAIL_MODE_ORDER = {
    "STOP": 0,
    "QUARANTINE": 1,
    "REQUEST_CONTEXT": 2,
}
CONSENT_STATES = frozenset({"EXPLICIT", "DENIED", "UNRESOLVED"})
AUTHORITY_MODES = frozenset({"READ", "WRITE", "MERGE", "PUBLISH", "SEND", "EXECUTE"})
SCOPE_DIMENSIONS = ("operations", "resources")


class RelationalActionAlgebraError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RelationalActionAlgebraError(
            "relational action contract must contain finite JSON data"
        ) from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise RelationalActionAlgebraError(f"{field} must be a string")
    out = value.strip()
    if not out:
        raise RelationalActionAlgebraError(f"{field} must be non-empty")
    return out


def _upper(value: Any, field: str) -> str:
    return _text(value, field).upper()


def _unique_text(values: Sequence[str], field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise RelationalActionAlgebraError(f"{field} must be a sequence")
    out = tuple(sorted({_text(value, field) for value in values}))
    if not allow_empty and not out:
        raise RelationalActionAlgebraError(f"{field} must be non-empty")
    return out


def _normalized_target(target: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(target, Mapping):
        raise RelationalActionAlgebraError("target must be a mapping")
    required = {"surface", "domain", "revision"}
    if set(target) != required:
        raise RelationalActionAlgebraError(
            "target must contain exactly surface, domain and revision"
        )
    return {
        "surface": _upper(target["surface"], "target.surface"),
        "domain": _text(target["domain"], "target.domain"),
        "revision": _text(target["revision"], "target.revision"),
    }


def _normalized_scope(scope: Mapping[str, Any]) -> dict[str, list[str]]:
    if not isinstance(scope, Mapping):
        raise RelationalActionAlgebraError("scope must be a mapping")
    if set(scope) != set(SCOPE_DIMENSIONS):
        raise RelationalActionAlgebraError(
            "scope must contain exactly operations and resources"
        )
    operations = tuple(
        sorted(
            {
                value.upper()
                for value in _unique_text(scope["operations"], "scope.operations")
            }
        )
    )
    resources = _unique_text(scope["resources"], "scope.resources")
    return {
        "operations": list(operations),
        "resources": list(resources),
    }


def _enum(value: Any, field: str, allowed: Mapping[str, Any] | frozenset[str]) -> str:
    normalized = _upper(value, field)
    if normalized not in allowed:
        raise RelationalActionAlgebraError(f"unsupported {field}: {normalized}")
    return normalized


def _uncertainty(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RelationalActionAlgebraError("uncertainty must be a number")
    out = float(value)
    if not 0.0 <= out <= 1.0:
        raise RelationalActionAlgebraError("uncertainty must be in [0, 1]")
    return out


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def relational_action_algebra_manifest() -> dict[str, Any]:
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "purpose": "FAIL_CLOSED_RELATIONAL_SCOPE_AND_AUTHORITY_ALGEBRA",
        "invariants": [
            "TARGET_DOMAIN_EXACT",
            "SCOPE_MAY_ONLY_NARROW",
            "AUTHORITY_MAY_ONLY_NARROW",
            "VISIBILITY_MAY_NOT_WIDEN",
            "PROVENANCE_MAY_ACCUMULATE_NOT_DISAPPEAR",
            "NO_GO_MAY_ACCUMULATE_NOT_DISAPPEAR",
            "DOMAIN_TRANSITION_REQUIRES_NEW_EXPLICIT_AUTHORIZATION",
            "HIGH_CONSEQUENCE_UNCERTAINTY_MUST_BE_ZERO",
            "NO_IMPLICIT_FALLBACK",
        ],
        "fail_modes": sorted(FAIL_MODE_ORDER),
        "authority_modes": sorted(AUTHORITY_MODES),
        "authority": _authority(),
    }
    return {**core, "manifest_sha256": _sha256(core)}


def build_relational_action_contract(
    *,
    target: Mapping[str, Any],
    scope: Mapping[str, Any],
    visibility: str,
    authority_modes: Sequence[str],
    reversibility: str,
    provenance_refs: Sequence[str] = (),
    relation_refs: Sequence[str] = (),
    uncertainty: float = 0.0,
    consequence_radius: str = "SINGLE_RESOURCE",
    fail_mode: str = "STOP",
    consent_boundary: str = "UNRESOLVED",
    no_go_hits: Sequence[str] = (),
    parent_contract_sha256: str | None = None,
) -> dict[str, Any]:
    target_row = _normalized_target(target)
    scope_row = _normalized_scope(scope)
    visibility_name = _enum(visibility, "visibility", VISIBILITY_ORDER)
    modes = tuple(sorted({_upper(value, "authority_mode") for value in authority_modes}))
    if not modes:
        raise RelationalActionAlgebraError("authority_modes must be non-empty")
    unknown_modes = sorted(set(modes) - AUTHORITY_MODES)
    if unknown_modes:
        raise RelationalActionAlgebraError(
            f"unsupported authority modes: {unknown_modes}"
        )
    reversibility_name = _enum(
        reversibility, "reversibility", REVERSIBILITY_RISK
    )
    provenance = _unique_text(
        provenance_refs, "provenance_ref", allow_empty=True
    )
    relations = _unique_text(relation_refs, "relation_ref", allow_empty=True)
    radius = _enum(
        consequence_radius, "consequence_radius", CONSEQUENCE_RADIUS_ORDER
    )
    fail = _enum(fail_mode, "fail_mode", FAIL_MODE_ORDER)
    consent = _enum(consent_boundary, "consent_boundary", CONSENT_STATES)
    no_go = _unique_text(no_go_hits, "no_go_hit", allow_empty=True)
    parent = (
        None
        if parent_contract_sha256 is None
        else _text(parent_contract_sha256, "parent_contract_sha256")
    )
    if parent is not None:
        if len(parent) != 64:
            raise RelationalActionAlgebraError(
                "parent_contract_sha256 must be 64 hexadecimal characters"
            )
        try:
            int(parent, 16)
        except ValueError as exc:
            raise RelationalActionAlgebraError(
                "parent_contract_sha256 must be hexadecimal"
            ) from exc

    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "target": target_row,
        "scope": scope_row,
        "visibility": visibility_name,
        "authority_modes": list(modes),
        "reversibility": reversibility_name,
        "provenance_refs": list(provenance),
        "relation_refs": list(relations),
        "uncertainty": _uncertainty(uncertainty),
        "consequence_radius": radius,
        "fail_mode": fail,
        "consent_boundary": consent,
        "no_go_hits": list(no_go),
        "parent_contract_sha256": parent,
        "scope_expansion_allowed": False,
        "implicit_fallback_allowed": False,
        "domain_transition_requires_new_explicit_authorization": True,
        "authority": _authority(),
    }
    return {**core, "contract_sha256": _sha256(core)}


def validate_relational_action_contract(packet: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, Mapping):
        raise RelationalActionAlgebraError(
            "relational action contract must be a mapping"
        )
    row = dict(packet)
    if row.get("schema") != SCHEMA or row.get("version") != VERSION:
        raise RelationalActionAlgebraError(
            "unsupported relational action contract schema"
        )
    supplied = _text(row.pop("contract_sha256", None), "contract_sha256")
    expected = build_relational_action_contract(
        target=row.get("target"),
        scope=row.get("scope"),
        visibility=row.get("visibility"),
        authority_modes=row.get("authority_modes"),
        reversibility=row.get("reversibility"),
        provenance_refs=row.get("provenance_refs", ()),
        relation_refs=row.get("relation_refs", ()),
        uncertainty=row.get("uncertainty"),
        consequence_radius=row.get("consequence_radius"),
        fail_mode=row.get("fail_mode"),
        consent_boundary=row.get("consent_boundary"),
        no_go_hits=row.get("no_go_hits", ()),
        parent_contract_sha256=row.get("parent_contract_sha256"),
    )
    expected_sha = expected["contract_sha256"]
    if supplied != expected_sha:
        raise RelationalActionAlgebraError(
            "relational action contract commitment mismatch"
        )
    if row.get("scope_expansion_allowed") is not False:
        raise RelationalActionAlgebraError("scope expansion must remain disabled")
    if row.get("implicit_fallback_allowed") is not False:
        raise RelationalActionAlgebraError("implicit fallback must remain disabled")
    if row.get("domain_transition_requires_new_explicit_authorization") is not True:
        raise RelationalActionAlgebraError(
            "domain transition authorization invariant disabled"
        )
    if row.get("authority") != _authority():
        raise RelationalActionAlgebraError(
            "relational action contract attempted authority widening"
        )
    return {**row, "contract_sha256": supplied}


def domain_transition(
    parent: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    left = validate_relational_action_contract(parent)
    right = validate_relational_action_contract(candidate)
    changes = [
        key
        for key in ("surface", "domain", "revision")
        if left["target"][key] != right["target"][key]
    ]
    changed = bool(changes)
    return {
        "domain_transition": changed,
        "changed_target_dimensions": changes,
        "requires_new_explicit_authorization": changed,
        "admitted_by_parent_contract": not changed,
    }


def monotone_narrowing(
    parent: Mapping[str, Any],
    child: Mapping[str, Any],
) -> dict[str, Any]:
    left = validate_relational_action_contract(parent)
    right = validate_relational_action_contract(child)
    failures: list[str] = []

    if right.get("parent_contract_sha256") != left["contract_sha256"]:
        failures.append("PARENT_COMMITMENT_MISMATCH")
    if left["target"] != right["target"]:
        failures.append("TARGET_DOMAIN_CHANGED")

    for dimension in SCOPE_DIMENSIONS:
        if not set(right["scope"][dimension]).issubset(left["scope"][dimension]):
            failures.append(f"SCOPE_{dimension.upper()}_WIDENED")

    if VISIBILITY_ORDER[right["visibility"]] > VISIBILITY_ORDER[left["visibility"]]:
        failures.append("VISIBILITY_WIDENED")
    if not set(right["authority_modes"]).issubset(left["authority_modes"]):
        failures.append("AUTHORITY_WIDENED")
    if REVERSIBILITY_RISK[right["reversibility"]] > REVERSIBILITY_RISK[left["reversibility"]]:
        failures.append("REVERSIBILITY_RISK_WIDENED")
    left_provenance = set(left["provenance_refs"])
    right_provenance = set(right["provenance_refs"])
    new_provenance = right_provenance - left_provenance
    if not left_provenance.issubset(right_provenance):
        failures.append("PROVENANCE_DROPPED")
    if not set(left["relation_refs"]).issubset(right["relation_refs"]):
        failures.append("RELATION_LINEAGE_DROPPED")
    if right["uncertainty"] > left["uncertainty"]:
        failures.append("UNCERTAINTY_INCREASED")
    if right["uncertainty"] < left["uncertainty"] and not new_provenance:
        failures.append("UNCERTAINTY_REDUCTION_WITHOUT_NEW_PROVENANCE")
    if (
        left["visibility"] == "UNKNOWN"
        and right["visibility"] != "UNKNOWN"
        and not new_provenance
    ):
        failures.append("VISIBILITY_RESOLUTION_WITHOUT_NEW_PROVENANCE")
    if (
        left["reversibility"] == "UNKNOWN"
        and right["reversibility"] != "UNKNOWN"
        and not new_provenance
    ):
        failures.append("REVERSIBILITY_RESOLUTION_WITHOUT_NEW_PROVENANCE")
    if CONSEQUENCE_RADIUS_ORDER[right["consequence_radius"]] > CONSEQUENCE_RADIUS_ORDER[left["consequence_radius"]]:
        failures.append("CONSEQUENCE_RADIUS_WIDENED")
    if FAIL_MODE_ORDER[right["fail_mode"]] > FAIL_MODE_ORDER[left["fail_mode"]]:
        failures.append("FAIL_MODE_WEAKENED")
    if right["consent_boundary"] != left["consent_boundary"]:
        failures.append("CONSENT_BOUNDARY_CHANGED")
    if not set(left["no_go_hits"]).issubset(right["no_go_hits"]):
        failures.append("NO_GO_EVIDENCE_DROPPED")

    return {
        "status": "PASS" if not failures else "BLOCK",
        "monotone_narrowing": not failures,
        "failures": failures,
        "parent_contract_sha256": left["contract_sha256"],
        "child_contract_sha256": right["contract_sha256"],
    }


def _visibility_meet(first: str, second: str) -> str:
    if "UNKNOWN" in {first, second}:
        return "UNKNOWN"
    return min(
        (first, second),
        key=lambda value: VISIBILITY_ORDER[value],
    )


def _reversibility_meet(first: str, second: str) -> str:
    if first == second:
        return first
    if "UNKNOWN" in {first, second}:
        return "UNKNOWN"
    return max(
        (first, second),
        key=lambda value: REVERSIBILITY_RISK[value],
    )


def _consent_meet(first: str, second: str) -> str:
    order = {"DENIED": BLOCK, "UNRESOLVED": UNRESOLVED, "EXPLICIT": PASS}
    return min((first, second), key=lambda value: order[value])


def meet_contracts(
    first: Mapping[str, Any],
    second: Mapping[str, Any],
) -> dict[str, Any]:
    left = validate_relational_action_contract(first)
    right = validate_relational_action_contract(second)
    if left["target"] != right["target"]:
        raise RelationalActionAlgebraError(
            "cannot meet contracts across target domains; new explicit authorization required"
        )

    operations = sorted(
        set(left["scope"]["operations"]) & set(right["scope"]["operations"])
    )
    resources = sorted(
        set(left["scope"]["resources"]) & set(right["scope"]["resources"])
    )
    authority_modes = sorted(
        set(left["authority_modes"]) & set(right["authority_modes"])
    )
    if not operations or not resources or not authority_modes:
        raise RelationalActionAlgebraError(
            "contract meet has empty executable intersection"
        )

    visibility = _visibility_meet(
        left["visibility"], right["visibility"]
    )
    consequence_radius = max(
        (left["consequence_radius"], right["consequence_radius"]),
        key=lambda value: CONSEQUENCE_RADIUS_ORDER[value],
    )
    fail_mode = min(
        (left["fail_mode"], right["fail_mode"]),
        key=lambda value: FAIL_MODE_ORDER[value],
    )

    return build_relational_action_contract(
        target=left["target"],
        scope={"operations": operations, "resources": resources},
        visibility=visibility,
        authority_modes=authority_modes,
        reversibility=_reversibility_meet(
            left["reversibility"], right["reversibility"]
        ),
        provenance_refs=sorted(
            set(left["provenance_refs"]) | set(right["provenance_refs"])
        ),
        relation_refs=sorted(
            set(left["relation_refs"]) | set(right["relation_refs"])
        ),
        uncertainty=max(left["uncertainty"], right["uncertainty"]),
        consequence_radius=consequence_radius,
        fail_mode=fail_mode,
        consent_boundary=_consent_meet(
            left["consent_boundary"], right["consent_boundary"]
        ),
        no_go_hits=sorted(
            set(left["no_go_hits"]) | set(right["no_go_hits"])
        ),
    )


def evaluate_relational_admission(
    contract: Mapping[str, Any],
    *,
    required_authority_modes: Sequence[str],
    high_consequence: bool,
) -> dict[str, Any]:
    row = validate_relational_action_contract(contract)
    required = tuple(
        sorted({_upper(value, "required_authority_mode") for value in required_authority_modes})
    )
    unknown_required = sorted(set(required) - AUTHORITY_MODES)
    if unknown_required:
        raise RelationalActionAlgebraError(
            f"unsupported required authority modes: {unknown_required}"
        )

    gate_state: dict[str, int] = {
        "TARGET": PASS,
        "SCOPE": PASS,
        "AUTHORITY": (
            PASS
            if set(required).issubset(row["authority_modes"])
            else BLOCK
        ),
        "VISIBILITY": (
            UNRESOLVED if row["visibility"] == "UNKNOWN" else PASS
        ),
        "REVERSIBILITY": (
            UNRESOLVED if row["reversibility"] == "UNKNOWN" else PASS
        ),
        "PROVENANCE": (
            PASS if row["provenance_refs"] else UNRESOLVED
        ),
        "RELATION": (
            PASS if row["relation_refs"] else UNRESOLVED
        ),
        "UNCERTAINTY": (
            PASS if row["uncertainty"] == 0.0 else UNRESOLVED
        ),
        "FAIL_MODE": PASS,
        "CONSENT": {
            "EXPLICIT": PASS,
            "UNRESOLVED": UNRESOLVED,
            "DENIED": BLOCK,
        }[row["consent_boundary"]],
        "NO_GO": PASS if not row["no_go_hits"] else BLOCK,
    }

    if high_consequence:
        required_gates = tuple(gate_state)
    else:
        required_gates = (
            "TARGET",
            "SCOPE",
            "AUTHORITY",
            "PROVENANCE",
            "RELATION",
            "FAIL_MODE",
            "NO_GO",
        )
    scalar = lattice_meet(tuple(gate_state[name] for name in required_gates))
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "contract_sha256": row["contract_sha256"],
        "high_consequence": bool(high_consequence),
        "required_authority_modes": list(required),
        "required_gates": list(required_gates),
        "gate_state": gate_state,
        "admissibility_scalar": scalar,
        "decision": decision_from_scalar(scalar),
        "implicit_fallback_allowed": False,
        "authority": _authority(),
    }


__all__ = [
    "AUTHORITY_MODES",
    "CONSEQUENCE_RADIUS_ORDER",
    "CONSENT_STATES",
    "FAIL_MODE_ORDER",
    "REVERSIBILITY_RISK",
    "RelationalActionAlgebraError",
    "SCHEMA",
    "VERSION",
    "VISIBILITY_ORDER",
    "build_relational_action_contract",
    "domain_transition",
    "evaluate_relational_admission",
    "meet_contracts",
    "monotone_narrowing",
    "relational_action_algebra_manifest",
    "validate_relational_action_contract",
]
