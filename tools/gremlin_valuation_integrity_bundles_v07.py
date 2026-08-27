from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

VALUATION_ITEM_SCHEMA = "GREMLIN_VALUATION_ITEM_V0_7"
VALUATION_ITEM_DOMAIN = b"GREMLIN-VALUATION-ITEM/v0.7\x00"
VALUATION_PROFILE_SCHEMA = "GREMLIN_VALUATION_PROFILE_V0_7"
VALUATION_PROFILE_DOMAIN = b"GREMLIN-VALUATION-PROFILE/v0.7\x00"
KAKU_VALUATION_SCHEMA = "GREMLIN_KAKU_VALUATION_BINDING_V0_7"
KAKU_VALUATION_DOMAIN = b"GREMLIN-KAKU-VALUATION-BINDING/v0.7\x00"

CONTRADICTION_ITEM_SCHEMA = "GREMLIN_CONTRADICTION_ITEM_V0_7"
CONTRADICTION_ITEM_DOMAIN = b"GREMLIN-CONTRADICTION-ITEM/v0.7\x00"
CONTRADICTION_BUNDLE_SCHEMA = "GREMLIN_CONTRADICTION_BUNDLE_V0_7"
CONTRADICTION_BUNDLE_DOMAIN = b"GREMLIN-CONTRADICTION-BUNDLE/v0.7\x00"

RECURSIVE_EVIDENCE_SCHEMA = "GREMLIN_RECURSIVE_INTEGRITY_EVIDENCE_V0_7"
RECURSIVE_EVIDENCE_DOMAIN = b"GREMLIN-RECURSIVE-INTEGRITY-EVIDENCE/v0.7\x00"
RECURSIVE_BUNDLE_SCHEMA = "GREMLIN_RECURSIVE_INTEGRITY_BUNDLE_V0_7"
RECURSIVE_BUNDLE_DOMAIN = b"GREMLIN-RECURSIVE-INTEGRITY-BUNDLE/v0.7\x00"

VALUATION_TERM = "CLX2-AFFECT-001"
CONTRADICTION_TERM = "CLX2-DYN-009"
RECURSIVE_INTEGRITY_TERM = "CLX2-DYN-010"
RECURSIVE_REENTRY_TERM = "CLX2-TIME-009"

CONFLICT_NODE_KINDS = {"COMMITMENT", "CONSTRAINT", "PREDICTION", "GOAL"}
RECURSIVE_ASPECTS = {
    "TRAVERSE_CONTRADICTION",
    "REENTER_RELATIONAL_LOOP",
    "DISTINCTION_PRESERVATION",
    "FRAGMENTATION_CONTROL",
}
RECURSIVE_EVIDENCE_STATES = {"EVIDENCED", "UNRESOLVED", "FAILED"}


class ValuationIntegrityError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(domain: bytes, value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    text = str(value)
    if not text:
        raise ValuationIntegrityError(f"{name} must be non-empty")
    return text


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise ValuationIntegrityError(f"{name} must be finite")
    return x


def _hash64(value: Any, name: str) -> str:
    text = _nonempty(value, name)
    if len(text) != 64:
        raise ValuationIntegrityError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise ValuationIntegrityError(f"{name} must be hexadecimal") from exc
    return text


def build_valuation_item_v07(
    *,
    option_id: str,
    value: Any,
    scale_id: str,
    source_ref: str,
    epistemic_status: str,
) -> dict[str, Any]:
    core = {
        "schema": VALUATION_ITEM_SCHEMA,
        "semantic_term_id": VALUATION_TERM,
        "option_id": _nonempty(option_id, "option_id"),
        "value_f64_hex": _finite(value, "valuation").hex(),
        "scale_id": _nonempty(scale_id, "scale_id"),
        "source_ref": _nonempty(source_ref, "source_ref"),
        "epistemic_status": _nonempty(epistemic_status, "epistemic_status"),
        "value_origin": "EXPLICIT_DECLARATION_OR_UPSTREAM_PRODUCER",
        "truth_authority": False,
        "epistemic_support_authority": False,
        "vector_bound": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "VALUATION_ITEM_BOUND",
    }
    return {**core, "valuation_item_commitment": _seal(VALUATION_ITEM_DOMAIN, core)}


def validate_valuation_item_v07(item: Mapping[str, Any]) -> bool:
    if item.get("schema") != VALUATION_ITEM_SCHEMA or item.get("semantic_term_id") != VALUATION_TERM:
        raise ValuationIntegrityError("valuation item schema/semantic binding mismatch")
    _nonempty(item.get("option_id"), "option_id")
    _finite(float.fromhex(str(item.get("value_f64_hex"))), "valuation")
    for key in ("scale_id", "source_ref", "epistemic_status"):
        _nonempty(item.get(key), key)
    if item.get("value_origin") != "EXPLICIT_DECLARATION_OR_UPSTREAM_PRODUCER":
        raise ValuationIntegrityError("valuation origin mismatch")
    for key in ("truth_authority", "epistemic_support_authority", "vector_bound", "execution_admitted", "canon_allowed"):
        if item.get(key) is not False:
            raise ValuationIntegrityError(f"valuation boundary violated: {key}")
    if item.get("status") != "VALUATION_ITEM_BOUND":
        raise ValuationIntegrityError("wrong valuation item status")
    supplied = _hash64(item.get("valuation_item_commitment"), "valuation_item_commitment")
    core = dict(item)
    core.pop("valuation_item_commitment", None)
    if supplied != _seal(VALUATION_ITEM_DOMAIN, core):
        raise ValuationIntegrityError("valuation item commitment mismatch")
    return True


def build_valuation_profile_v07(
    *,
    comparison_set_id: str,
    items: Sequence[Mapping[str, Any]],
    criterion_ref: str,
) -> dict[str, Any]:
    if not items:
        raise ValuationIntegrityError("valuation profile requires at least one option")
    refs = []
    seen = set()
    common_scale = None
    for item in items:
        validate_valuation_item_v07(item)
        option_id = str(item["option_id"])
        if option_id in seen:
            raise ValuationIntegrityError(f"duplicate valuation option: {option_id}")
        seen.add(option_id)
        scale = str(item["scale_id"])
        if common_scale is None:
            common_scale = scale
        elif scale != common_scale:
            raise ValuationIntegrityError("valuation comparison set requires a common declared scale")
        refs.append({
            "option_id": option_id,
            "value_f64_hex": str(item["value_f64_hex"]),
            "valuation_item_commitment": str(item["valuation_item_commitment"]),
        })
    refs.sort(key=lambda x: x["option_id"])
    core = {
        "schema": VALUATION_PROFILE_SCHEMA,
        "semantic_term_id": VALUATION_TERM,
        "comparison_set_id": _nonempty(comparison_set_id, "comparison_set_id"),
        "criterion_ref": _nonempty(criterion_ref, "criterion_ref"),
        "scale_id": str(common_scale),
        "items": refs,
        "normalization": "DECLARED_SCALE_PRESERVED",
        "evaluator_status": "SOURCE_SPECIFIC",
        "cross_scale_comparison_allowed": False,
        "vector_bound": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "VALUATION_PROFILE_BOUND",
    }
    return {**core, "valuation_profile_commitment": _seal(VALUATION_PROFILE_DOMAIN, core)}


def validate_valuation_profile_v07(profile: Mapping[str, Any]) -> bool:
    if profile.get("schema") != VALUATION_PROFILE_SCHEMA or profile.get("semantic_term_id") != VALUATION_TERM:
        raise ValuationIntegrityError("valuation profile schema/semantic binding mismatch")
    for key in ("comparison_set_id", "criterion_ref", "scale_id"):
        _nonempty(profile.get(key), key)
    items = profile.get("items")
    if not isinstance(items, list) or not items:
        raise ValuationIntegrityError("valuation profile item lineage missing")
    ids = []
    for item in items:
        if not isinstance(item, Mapping):
            raise ValuationIntegrityError("valuation profile item malformed")
        ids.append(_nonempty(item.get("option_id"), "option_id"))
        _finite(float.fromhex(str(item.get("value_f64_hex"))), "valuation")
        _hash64(item.get("valuation_item_commitment"), "valuation_item_commitment")
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ValuationIntegrityError("valuation profile requires unique canonical option order")
    if profile.get("normalization") != "DECLARED_SCALE_PRESERVED" or profile.get("evaluator_status") != "SOURCE_SPECIFIC":
        raise ValuationIntegrityError("valuation profile scale/evaluator contract mismatch")
    if profile.get("cross_scale_comparison_allowed") is not False:
        raise ValuationIntegrityError("cross-scale valuation comparison requires an explicit adapter")
    for key in ("vector_bound", "execution_admitted", "canon_allowed"):
        if profile.get(key) is not False:
            raise ValuationIntegrityError(f"valuation profile boundary violated: {key}")
    if profile.get("status") != "VALUATION_PROFILE_BOUND":
        raise ValuationIntegrityError("wrong valuation profile status")
    supplied = _hash64(profile.get("valuation_profile_commitment"), "valuation_profile_commitment")
    core = dict(profile)
    core.pop("valuation_profile_commitment", None)
    if supplied != _seal(VALUATION_PROFILE_DOMAIN, core):
        raise ValuationIntegrityError("valuation profile commitment mismatch")
    return True


def build_kaku_valuation_binding_v07(
    *,
    kaku_id: str,
    option_id: str,
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    validate_valuation_profile_v07(profile)
    selected = [item for item in profile["items"] if item["option_id"] == option_id]
    if len(selected) != 1:
        raise ValuationIntegrityError("KAKU valuation option must resolve exactly once in comparison set")
    item = selected[0]
    core = {
        "schema": KAKU_VALUATION_SCHEMA,
        "kaku_id": _nonempty(kaku_id, "kaku_id"),
        "comparison_set_id": str(profile["comparison_set_id"]),
        "valuation_profile_commitment": str(profile["valuation_profile_commitment"]),
        "option_id": str(option_id),
        "valuation_item_commitment": str(item["valuation_item_commitment"]),
        "valuation_value_f64_hex": str(item["value_f64_hex"]),
        "scale_id": str(profile["scale_id"]),
        "vector_synthesis_allowed": False,
        "vector_bound": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "KAKU_VALUATION_BOUND",
    }
    return {**core, "kaku_valuation_binding_commitment": _seal(KAKU_VALUATION_DOMAIN, core)}


def validate_kaku_valuation_binding_v07(binding: Mapping[str, Any]) -> bool:
    if binding.get("schema") != KAKU_VALUATION_SCHEMA:
        raise ValuationIntegrityError("unsupported KAKU valuation binding schema")
    for key in ("kaku_id", "comparison_set_id", "option_id", "scale_id"):
        _nonempty(binding.get(key), key)
    _hash64(binding.get("valuation_profile_commitment"), "valuation_profile_commitment")
    _hash64(binding.get("valuation_item_commitment"), "valuation_item_commitment")
    _finite(float.fromhex(str(binding.get("valuation_value_f64_hex"))), "valuation")
    for key in ("vector_synthesis_allowed", "vector_bound", "execution_admitted", "canon_allowed"):
        if binding.get(key) is not False:
            raise ValuationIntegrityError(f"KAKU valuation boundary violated: {key}")
    if binding.get("status") != "KAKU_VALUATION_BOUND":
        raise ValuationIntegrityError("wrong KAKU valuation binding status")
    supplied = _hash64(binding.get("kaku_valuation_binding_commitment"), "kaku_valuation_binding_commitment")
    core = dict(binding)
    core.pop("kaku_valuation_binding_commitment", None)
    if supplied != _seal(KAKU_VALUATION_DOMAIN, core):
        raise ValuationIntegrityError("KAKU valuation binding commitment mismatch")
    return True


def build_contradiction_item_v07(
    *,
    contradiction_id: str,
    left_id: str,
    left_kind: str,
    left_commitment: str,
    right_id: str,
    right_kind: str,
    right_commitment: str,
    criterion_ref: str,
    evidence_refs: Sequence[str],
    epistemic_status: str,
) -> dict[str, Any]:
    lk = _nonempty(left_kind, "left_kind").upper()
    rk = _nonempty(right_kind, "right_kind").upper()
    if lk not in CONFLICT_NODE_KINDS or rk not in CONFLICT_NODE_KINDS:
        raise ValuationIntegrityError("contradiction endpoints require commitment/constraint/prediction/goal kinds")
    refs = sorted({_nonempty(v, "evidence_ref") for v in evidence_refs})
    if not refs:
        raise ValuationIntegrityError("contradiction declaration requires evidence")
    left = {
        "id": _nonempty(left_id, "left_id"),
        "kind": lk,
        "commitment": _hash64(left_commitment, "left_commitment"),
    }
    right = {
        "id": _nonempty(right_id, "right_id"),
        "kind": rk,
        "commitment": _hash64(right_commitment, "right_commitment"),
    }
    endpoints = sorted([left, right], key=lambda x: (x["id"], x["kind"], x["commitment"]))
    if endpoints[0] == endpoints[1]:
        raise ValuationIntegrityError("contradiction endpoints must identify distinct bound states")
    core = {
        "schema": CONTRADICTION_ITEM_SCHEMA,
        "semantic_term_id": CONTRADICTION_TERM,
        "contradiction_id": _nonempty(contradiction_id, "contradiction_id"),
        "relation": "DECLARED_INCOMPATIBILITY",
        "endpoints": endpoints,
        "criterion_ref": _nonempty(criterion_ref, "criterion_ref"),
        "evidence_refs": refs,
        "epistemic_status": _nonempty(epistemic_status, "epistemic_status"),
        "severity_scalar_present": False,
        "vector_bound": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "CONTRADICTION_BOUND",
    }
    return {**core, "contradiction_item_commitment": _seal(CONTRADICTION_ITEM_DOMAIN, core)}


def validate_contradiction_item_v07(item: Mapping[str, Any]) -> bool:
    if item.get("schema") != CONTRADICTION_ITEM_SCHEMA or item.get("semantic_term_id") != CONTRADICTION_TERM:
        raise ValuationIntegrityError("contradiction item schema/semantic binding mismatch")
    _nonempty(item.get("contradiction_id"), "contradiction_id")
    if item.get("relation") != "DECLARED_INCOMPATIBILITY":
        raise ValuationIntegrityError("contradiction relation mismatch")
    endpoints = item.get("endpoints")
    if not isinstance(endpoints, list) or len(endpoints) != 2:
        raise ValuationIntegrityError("contradiction requires exactly two endpoints")
    canonical = []
    for endpoint in endpoints:
        if not isinstance(endpoint, Mapping):
            raise ValuationIntegrityError("contradiction endpoint malformed")
        node_id = _nonempty(endpoint.get("id"), "endpoint.id")
        kind = _nonempty(endpoint.get("kind"), "endpoint.kind")
        if kind not in CONFLICT_NODE_KINDS:
            raise ValuationIntegrityError("contradiction endpoint kind mismatch")
        commitment = _hash64(endpoint.get("commitment"), "endpoint.commitment")
        canonical.append({"id": node_id, "kind": kind, "commitment": commitment})
    if canonical != sorted(canonical, key=lambda x: (x["id"], x["kind"], x["commitment"])):
        raise ValuationIntegrityError("contradiction endpoints require canonical ordering")
    if canonical[0] == canonical[1]:
        raise ValuationIntegrityError("contradiction endpoints must differ")
    _nonempty(item.get("criterion_ref"), "criterion_ref")
    refs = item.get("evidence_refs")
    if not isinstance(refs, list) or not refs or refs != sorted(set(refs)):
        raise ValuationIntegrityError("contradiction evidence refs require unique canonical order")
    _nonempty(item.get("epistemic_status"), "epistemic_status")
    for key in ("severity_scalar_present", "vector_bound", "execution_admitted", "canon_allowed"):
        if item.get(key) is not False:
            raise ValuationIntegrityError(f"contradiction boundary violated: {key}")
    if item.get("status") != "CONTRADICTION_BOUND":
        raise ValuationIntegrityError("wrong contradiction status")
    supplied = _hash64(item.get("contradiction_item_commitment"), "contradiction_item_commitment")
    core = dict(item)
    core.pop("contradiction_item_commitment", None)
    if supplied != _seal(CONTRADICTION_ITEM_DOMAIN, core):
        raise ValuationIntegrityError("contradiction item commitment mismatch")
    return True


def build_contradiction_bundle_v07(*, radical_id: str, items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not items:
        raise ValuationIntegrityError("contradiction bundle requires at least one declared incompatibility")
    refs = []
    seen = set()
    for item in items:
        validate_contradiction_item_v07(item)
        cid = str(item["contradiction_id"])
        if cid in seen:
            raise ValuationIntegrityError(f"duplicate contradiction_id: {cid}")
        seen.add(cid)
        refs.append({
            "contradiction_id": cid,
            "contradiction_item_commitment": str(item["contradiction_item_commitment"]),
        })
    refs.sort(key=lambda x: x["contradiction_id"])
    core = {
        "schema": CONTRADICTION_BUNDLE_SCHEMA,
        "semantic_term_id": CONTRADICTION_TERM,
        "radical_id": _nonempty(radical_id, "radical_id"),
        "items": refs,
        "declared_conflict_count": len(refs),
        "contradiction_load_scalar_present": False,
        "scalarization_status": "UNRESOLVED",
        "vector_bound": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "CONTRADICTION_ANTECEDENTS_BOUND",
    }
    return {**core, "contradiction_bundle_commitment": _seal(CONTRADICTION_BUNDLE_DOMAIN, core)}


def validate_contradiction_bundle_v07(bundle: Mapping[str, Any]) -> bool:
    if bundle.get("schema") != CONTRADICTION_BUNDLE_SCHEMA or bundle.get("semantic_term_id") != CONTRADICTION_TERM:
        raise ValuationIntegrityError("contradiction bundle schema/semantic binding mismatch")
    _nonempty(bundle.get("radical_id"), "radical_id")
    items = bundle.get("items")
    if not isinstance(items, list) or not items:
        raise ValuationIntegrityError("contradiction bundle lineage missing")
    ids = []
    for item in items:
        if not isinstance(item, Mapping):
            raise ValuationIntegrityError("contradiction bundle item malformed")
        ids.append(_nonempty(item.get("contradiction_id"), "contradiction_id"))
        _hash64(item.get("contradiction_item_commitment"), "contradiction_item_commitment")
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ValuationIntegrityError("contradiction bundle requires unique canonical ordering")
    if bundle.get("declared_conflict_count") != len(items):
        raise ValuationIntegrityError("declared conflict count mismatch")
    if bundle.get("contradiction_load_scalar_present") is not False or bundle.get("scalarization_status") != "UNRESOLVED":
        raise ValuationIntegrityError("contradiction scalarization frontier mismatch")
    for key in ("vector_bound", "execution_admitted", "canon_allowed"):
        if bundle.get(key) is not False:
            raise ValuationIntegrityError(f"contradiction bundle boundary violated: {key}")
    if bundle.get("status") != "CONTRADICTION_ANTECEDENTS_BOUND":
        raise ValuationIntegrityError("wrong contradiction bundle status")
    supplied = _hash64(bundle.get("contradiction_bundle_commitment"), "contradiction_bundle_commitment")
    core = dict(bundle)
    core.pop("contradiction_bundle_commitment", None)
    if supplied != _seal(CONTRADICTION_BUNDLE_DOMAIN, core):
        raise ValuationIntegrityError("contradiction bundle commitment mismatch")
    return True


def build_recursive_integrity_evidence_v07(
    *,
    aspect: str,
    state: str,
    source_ref: str,
    source_commitment: str,
    epistemic_status: str,
) -> dict[str, Any]:
    asp = _nonempty(aspect, "aspect").upper()
    st = _nonempty(state, "state").upper()
    if asp not in RECURSIVE_ASPECTS:
        raise ValuationIntegrityError(f"unsupported recursive-integrity aspect: {asp}")
    if st not in RECURSIVE_EVIDENCE_STATES:
        raise ValuationIntegrityError(f"unsupported recursive-integrity evidence state: {st}")
    core = {
        "schema": RECURSIVE_EVIDENCE_SCHEMA,
        "semantic_term_id": RECURSIVE_INTEGRITY_TERM,
        "aspect": asp,
        "state": st,
        "source_ref": _nonempty(source_ref, "source_ref"),
        "source_commitment": _hash64(source_commitment, "source_commitment"),
        "epistemic_status": _nonempty(epistemic_status, "epistemic_status"),
        "numeric_score_present": False,
        "vector_bound": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "RECURSIVE_INTEGRITY_EVIDENCE_BOUND",
    }
    return {**core, "recursive_evidence_commitment": _seal(RECURSIVE_EVIDENCE_DOMAIN, core)}


def validate_recursive_integrity_evidence_v07(item: Mapping[str, Any]) -> bool:
    if item.get("schema") != RECURSIVE_EVIDENCE_SCHEMA or item.get("semantic_term_id") != RECURSIVE_INTEGRITY_TERM:
        raise ValuationIntegrityError("recursive-integrity evidence schema/semantic binding mismatch")
    if item.get("aspect") not in RECURSIVE_ASPECTS or item.get("state") not in RECURSIVE_EVIDENCE_STATES:
        raise ValuationIntegrityError("recursive-integrity aspect/state mismatch")
    _nonempty(item.get("source_ref"), "source_ref")
    _hash64(item.get("source_commitment"), "source_commitment")
    _nonempty(item.get("epistemic_status"), "epistemic_status")
    for key in ("numeric_score_present", "vector_bound", "execution_admitted", "canon_allowed"):
        if item.get(key) is not False:
            raise ValuationIntegrityError(f"recursive-integrity evidence boundary violated: {key}")
    if item.get("status") != "RECURSIVE_INTEGRITY_EVIDENCE_BOUND":
        raise ValuationIntegrityError("wrong recursive-integrity evidence status")
    supplied = _hash64(item.get("recursive_evidence_commitment"), "recursive_evidence_commitment")
    core = dict(item)
    core.pop("recursive_evidence_commitment", None)
    if supplied != _seal(RECURSIVE_EVIDENCE_DOMAIN, core):
        raise ValuationIntegrityError("recursive-integrity evidence commitment mismatch")
    return True


def build_recursive_integrity_bundle_v07(
    *,
    radical_id: str,
    contradiction_bundle: Mapping[str, Any],
    recursive_reentry_commitment: str,
    evidence: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    validate_contradiction_bundle_v07(contradiction_bundle)
    if contradiction_bundle.get("radical_id") != radical_id:
        raise ValuationIntegrityError("recursive-integrity Radical identity mismatch")
    if not evidence:
        raise ValuationIntegrityError("recursive-integrity bundle requires aspect evidence")
    refs = {}
    for item in evidence:
        validate_recursive_integrity_evidence_v07(item)
        aspect = str(item["aspect"])
        if aspect in refs:
            raise ValuationIntegrityError(f"duplicate recursive-integrity aspect: {aspect}")
        refs[aspect] = {
            "state": str(item["state"]),
            "recursive_evidence_commitment": str(item["recursive_evidence_commitment"]),
        }
    ordered = {key: refs[key] for key in sorted(refs)}
    missing = sorted(RECURSIVE_ASPECTS - set(refs))
    states = {key: value["state"] for key, value in ordered.items()}
    if any(state == "FAILED" for state in states.values()):
        antecedent_state = "FAILED_EVIDENCE_PRESENT"
    elif missing or any(state == "UNRESOLVED" for state in states.values()):
        antecedent_state = "OPEN"
    else:
        antecedent_state = "COMPLETE_EVIDENCED"
    core = {
        "schema": RECURSIVE_BUNDLE_SCHEMA,
        "semantic_term_id": RECURSIVE_INTEGRITY_TERM,
        "dependency_terms": [RECURSIVE_REENTRY_TERM, CONTRADICTION_TERM],
        "radical_id": _nonempty(radical_id, "radical_id"),
        "contradiction_bundle_commitment": str(contradiction_bundle["contradiction_bundle_commitment"]),
        "recursive_reentry_commitment": _hash64(recursive_reentry_commitment, "recursive_reentry_commitment"),
        "aspects": ordered,
        "missing_aspects": missing,
        "antecedent_state": antecedent_state,
        "recursive_integrity_scalar_present": False,
        "scalarization_status": "UNRESOLVED",
        "vector_bound": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "RECURSIVE_INTEGRITY_ANTECEDENTS_BOUND",
    }
    return {**core, "recursive_integrity_bundle_commitment": _seal(RECURSIVE_BUNDLE_DOMAIN, core)}


def validate_recursive_integrity_bundle_v07(bundle: Mapping[str, Any]) -> bool:
    if bundle.get("schema") != RECURSIVE_BUNDLE_SCHEMA or bundle.get("semantic_term_id") != RECURSIVE_INTEGRITY_TERM:
        raise ValuationIntegrityError("recursive-integrity bundle schema/semantic binding mismatch")
    if bundle.get("dependency_terms") != [RECURSIVE_REENTRY_TERM, CONTRADICTION_TERM]:
        raise ValuationIntegrityError("recursive-integrity dependency binding mismatch")
    _nonempty(bundle.get("radical_id"), "radical_id")
    _hash64(bundle.get("contradiction_bundle_commitment"), "contradiction_bundle_commitment")
    _hash64(bundle.get("recursive_reentry_commitment"), "recursive_reentry_commitment")
    aspects = bundle.get("aspects")
    if not isinstance(aspects, Mapping) or not aspects:
        raise ValuationIntegrityError("recursive-integrity aspect lineage missing")
    if list(aspects) != sorted(aspects):
        raise ValuationIntegrityError("recursive-integrity aspects require canonical ordering")
    for aspect, item in aspects.items():
        if aspect not in RECURSIVE_ASPECTS or not isinstance(item, Mapping):
            raise ValuationIntegrityError("recursive-integrity aspect malformed")
        if item.get("state") not in RECURSIVE_EVIDENCE_STATES:
            raise ValuationIntegrityError("recursive-integrity state mismatch")
        _hash64(item.get("recursive_evidence_commitment"), "recursive_evidence_commitment")
    missing = bundle.get("missing_aspects")
    expected_missing = sorted(RECURSIVE_ASPECTS - set(aspects))
    if missing != expected_missing:
        raise ValuationIntegrityError("recursive-integrity missing-aspect lineage mismatch")
    states = [item["state"] for item in aspects.values()]
    expected_state = (
        "FAILED_EVIDENCE_PRESENT" if any(s == "FAILED" for s in states)
        else "OPEN" if expected_missing or any(s == "UNRESOLVED" for s in states)
        else "COMPLETE_EVIDENCED"
    )
    if bundle.get("antecedent_state") != expected_state:
        raise ValuationIntegrityError("recursive-integrity antecedent state mismatch")
    if bundle.get("recursive_integrity_scalar_present") is not False or bundle.get("scalarization_status") != "UNRESOLVED":
        raise ValuationIntegrityError("recursive-integrity scalarization frontier mismatch")
    for key in ("vector_bound", "execution_admitted", "canon_allowed"):
        if bundle.get(key) is not False:
            raise ValuationIntegrityError(f"recursive-integrity bundle boundary violated: {key}")
    if bundle.get("status") != "RECURSIVE_INTEGRITY_ANTECEDENTS_BOUND":
        raise ValuationIntegrityError("wrong recursive-integrity bundle status")
    supplied = _hash64(bundle.get("recursive_integrity_bundle_commitment"), "recursive_integrity_bundle_commitment")
    core = dict(bundle)
    core.pop("recursive_integrity_bundle_commitment", None)
    if supplied != _seal(RECURSIVE_BUNDLE_DOMAIN, core):
        raise ValuationIntegrityError("recursive-integrity bundle commitment mismatch")
    return True
