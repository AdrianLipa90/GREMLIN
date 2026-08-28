from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from tools.gremlin_phasenav_compiler_v01 import CANDIDATE_SCHEMA

EVIDENCE_SCHEMA = "GREMLIN_EPISTEMIC_EVIDENCE_ITEM_V0_6"
EVIDENCE_DOMAIN = b"GREMLIN-EPISTEMIC-EVIDENCE-ITEM/v0.6\x00"
CONFIDENCE_SCHEMA = "GREMLIN_EPISTEMIC_CONFIDENCE_DECLARATION_V0_6"
CONFIDENCE_DOMAIN = b"GREMLIN-EPISTEMIC-CONFIDENCE-DECLARATION/v0.6\x00"
BUNDLE_SCHEMA = "GREMLIN_EPISTEMIC_SUPPORT_BUNDLE_V0_6"
BUNDLE_DOMAIN = b"GREMLIN-EPISTEMIC-SUPPORT-BUNDLE/v0.6\x00"
KAKU_SCHEMA = "GREMLIN_KAKU_EPISTEMIC_BINDING_V0_6"
KAKU_DOMAIN = b"GREMLIN-KAKU-EPISTEMIC-BINDING/v0.6\x00"

DICTIONARY_REPOSITORY = "AdrianLipa90/The-Consciousness-Dictionary"
DICTIONARY_COMMIT = "b988113faf0cfd0c534dab4bb4a7b5cca41e40b9"
GATES_PATH = "src/consciousness_dictionary/gates.py"
GATES_BLOB_SHA = "125527d347eb0bddee690221b2785a1e903c6554"

EVIDENCE_TERM = "CLX2-SEM-019"
CLAIM_TERM = "CLX2-SEM-020"
PROPOSITION_TERM = "CLX2-SEM-021"
CONFIDENCE_TERM = "CLX2-SEM-023"

EVIDENCE_ROLES = {
    "EMPIRICAL_OBSERVATION",
    "DERIVATION",
    "REFERENCE_CONFORMANCE",
    "FALSIFICATION_SURVIVAL",
    "COUNTEREXAMPLE",
    "PROVENANCE_ASSERTION",
    "CONTEXT",
}

CLAIM_RELATIONS = {"BEARS_ON", "CHALLENGES", "CONTEXT_FOR"}
CONFIDENCE_KINDS = {"RELIABILITY", "PROBABILITY", "COMMITMENT"}


class EpistemicBundleError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(domain: bytes, value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    text = str(value)
    if not text:
        raise EpistemicBundleError(f"{name} must be non-empty")
    return text


def _hash64(value: Any, name: str) -> str:
    text = _nonempty(value, name)
    if len(text) != 64:
        raise EpistemicBundleError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise EpistemicBundleError(f"{name} must be hexadecimal") from exc
    return text


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise EpistemicBundleError(f"{name} must be finite")
    return x


def build_evidence_item_v06(
    *,
    evidence_id: str,
    source_ref: str,
    source_commitment: str,
    evidence_role: str,
    relation_to_claim: str,
    epistemic_status: str,
    framework_ref: str,
) -> dict[str, Any]:
    role = _nonempty(evidence_role, "evidence_role").upper()
    relation = _nonempty(relation_to_claim, "relation_to_claim").upper()
    if role not in EVIDENCE_ROLES:
        raise EpistemicBundleError(f"unsupported evidence role: {role}")
    if relation not in CLAIM_RELATIONS:
        raise EpistemicBundleError(f"unsupported claim relation: {relation}")
    core = {
        "schema": EVIDENCE_SCHEMA,
        "semantic_term_id": EVIDENCE_TERM,
        "evidence_id": _nonempty(evidence_id, "evidence_id"),
        "source_ref": _nonempty(source_ref, "source_ref"),
        "source_commitment": _hash64(source_commitment, "source_commitment"),
        "evidence_role": role,
        "relation_to_claim": relation,
        "epistemic_status": _nonempty(epistemic_status, "epistemic_status"),
        "framework_ref": _nonempty(framework_ref, "framework_ref"),
        "numeric_weight_present": False,
        "epistemic_support_scalar_present": False,
        "vector_bound": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "EVIDENCE_ITEM_BOUND",
    }
    return {**core, "evidence_item_commitment": _seal(EVIDENCE_DOMAIN, core)}


def validate_evidence_item_v06(item: Mapping[str, Any]) -> bool:
    if item.get("schema") != EVIDENCE_SCHEMA or item.get("semantic_term_id") != EVIDENCE_TERM:
        raise EpistemicBundleError("evidence item schema/semantic binding mismatch")
    for key in ("evidence_id", "source_ref", "epistemic_status", "framework_ref"):
        _nonempty(item.get(key), key)
    _hash64(item.get("source_commitment"), "source_commitment")
    if item.get("evidence_role") not in EVIDENCE_ROLES:
        raise EpistemicBundleError("evidence role mismatch")
    if item.get("relation_to_claim") not in CLAIM_RELATIONS:
        raise EpistemicBundleError("claim relation mismatch")
    for key in ("numeric_weight_present", "epistemic_support_scalar_present", "vector_bound", "execution_admitted", "canon_allowed"):
        if item.get(key) is not False:
            raise EpistemicBundleError(f"evidence boundary violated: {key}")
    if item.get("status") != "EVIDENCE_ITEM_BOUND":
        raise EpistemicBundleError("wrong evidence item status")
    supplied = _hash64(item.get("evidence_item_commitment"), "evidence_item_commitment")
    core = dict(item)
    core.pop("evidence_item_commitment", None)
    if supplied != _seal(EVIDENCE_DOMAIN, core):
        raise EpistemicBundleError("evidence item commitment mismatch")
    return True


def build_belzebub_survival_evidence_v06(candidate: Mapping[str, Any], *, framework_ref: str) -> dict[str, Any]:
    if candidate.get("schema") != CANDIDATE_SCHEMA:
        raise EpistemicBundleError("unsupported GREMLIN candidate schema")
    if candidate.get("status") != "SURVIVED_AUDIT":
        raise EpistemicBundleError("BELZEBUB evidence requires SURVIVED_AUDIT candidate")
    audit = candidate.get("audit")
    if not isinstance(audit, Mapping) or audit.get("belzebub_result") != "SURVIVED":
        raise EpistemicBundleError("BELZEBUB audit survival receipt missing")
    candidate_id = _nonempty(candidate.get("candidate_id"), "candidate_id")
    audit_commitment = hashlib.blake2b(
        b"GREMLIN-BELZEBUB-AUDIT-EVIDENCE/v0.6\x00" + _canonical({"candidate_id": candidate_id, "audit": audit}),
        digest_size=32,
    ).hexdigest()
    return build_evidence_item_v06(
        evidence_id=f"belzebub:{candidate_id}",
        source_ref=f"gremlin://candidate/{candidate_id}#belzebub-audit",
        source_commitment=audit_commitment,
        evidence_role="FALSIFICATION_SURVIVAL",
        relation_to_claim="BEARS_ON",
        epistemic_status="SURVIVED_AUDIT",
        framework_ref=framework_ref,
    )


def build_confidence_declaration_v06(
    *,
    value: Any,
    confidence_kind: str,
    estimator_ref: str,
    source_ref: str,
    source_family: str,
    epistemic_status: str,
) -> dict[str, Any]:
    kind = _nonempty(confidence_kind, "confidence_kind").upper()
    family = _nonempty(source_family, "source_family").upper()
    if kind not in CONFIDENCE_KINDS:
        raise EpistemicBundleError(f"unsupported confidence kind: {kind}")
    if family == "AFFECT_INFERENCE":
        raise EpistemicBundleError("affect inference confidence has a separate semantic lane")
    q = _finite(value, "confidence")
    if q < 0.0 or q > 1.0:
        raise EpistemicBundleError("confidence outside [0,1]")
    core = {
        "schema": CONFIDENCE_SCHEMA,
        "semantic_term_id": CONFIDENCE_TERM,
        "value_f64_hex": q.hex(),
        "scale_id": "UNIT_INTERVAL[0,1]/v0.6",
        "confidence_kind": kind,
        "estimator_ref": _nonempty(estimator_ref, "estimator_ref"),
        "source_ref": _nonempty(source_ref, "source_ref"),
        "source_family": family,
        "epistemic_status": _nonempty(epistemic_status, "epistemic_status"),
        "epistemic_support_scalar_present": False,
        "vector_bound": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "CONFIDENCE_DECLARATION_BOUND",
    }
    return {**core, "confidence_commitment": _seal(CONFIDENCE_DOMAIN, core)}


def validate_confidence_declaration_v06(record: Mapping[str, Any]) -> bool:
    if record.get("schema") != CONFIDENCE_SCHEMA or record.get("semantic_term_id") != CONFIDENCE_TERM:
        raise EpistemicBundleError("confidence schema/semantic binding mismatch")
    q = _finite(float.fromhex(str(record.get("value_f64_hex"))), "confidence")
    if q < 0.0 or q > 1.0 or record.get("scale_id") != "UNIT_INTERVAL[0,1]/v0.6":
        raise EpistemicBundleError("confidence domain mismatch")
    if record.get("confidence_kind") not in CONFIDENCE_KINDS:
        raise EpistemicBundleError("confidence kind mismatch")
    if record.get("source_family") == "AFFECT_INFERENCE":
        raise EpistemicBundleError("affect inference confidence has a separate semantic lane")
    for key in ("estimator_ref", "source_ref", "source_family", "epistemic_status"):
        _nonempty(record.get(key), key)
    for key in ("epistemic_support_scalar_present", "vector_bound", "execution_admitted", "canon_allowed"):
        if record.get(key) is not False:
            raise EpistemicBundleError(f"confidence boundary violated: {key}")
    if record.get("status") != "CONFIDENCE_DECLARATION_BOUND":
        raise EpistemicBundleError("wrong confidence status")
    supplied = _hash64(record.get("confidence_commitment"), "confidence_commitment")
    core = dict(record)
    core.pop("confidence_commitment", None)
    if supplied != _seal(CONFIDENCE_DOMAIN, core):
        raise EpistemicBundleError("confidence commitment mismatch")
    return True


def build_epistemic_support_bundle_v06(
    *,
    claim_id: str,
    claim_commitment: str,
    proposition_commitment: str,
    inference_framework_commitment: str,
    evidence_items: Sequence[Mapping[str, Any]],
    confidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not evidence_items:
        raise EpistemicBundleError("epistemic bundle requires at least one evidence item")
    evidence_refs = []
    seen = set()
    for item in evidence_items:
        validate_evidence_item_v06(item)
        evidence_id = str(item["evidence_id"])
        if evidence_id in seen:
            raise EpistemicBundleError(f"duplicate evidence_id: {evidence_id}")
        seen.add(evidence_id)
        evidence_refs.append({
            "evidence_id": evidence_id,
            "evidence_item_commitment": str(item["evidence_item_commitment"]),
            "evidence_role": str(item["evidence_role"]),
            "relation_to_claim": str(item["relation_to_claim"]),
        })
    evidence_refs.sort(key=lambda x: x["evidence_id"])

    if confidence is None:
        confidence_binding = {"status": "UNRESOLVED", "semantic_term_id": CONFIDENCE_TERM}
    else:
        validate_confidence_declaration_v06(confidence)
        confidence_binding = {
            "status": "BOUND_CANDIDATE",
            "semantic_term_id": CONFIDENCE_TERM,
            "confidence_commitment": str(confidence["confidence_commitment"]),
        }

    core = {
        "schema": BUNDLE_SCHEMA,
        "claim": {
            "semantic_term_id": CLAIM_TERM,
            "claim_id": _nonempty(claim_id, "claim_id"),
            "claim_commitment": _hash64(claim_commitment, "claim_commitment"),
        },
        "proposition": {
            "semantic_term_id": PROPOSITION_TERM,
            "proposition_commitment": _hash64(proposition_commitment, "proposition_commitment"),
        },
        "evidence": evidence_refs,
        "confidence": confidence_binding,
        "inference_framework_commitment": _hash64(
            inference_framework_commitment, "inference_framework_commitment"
        ),
        "dictionary_promotion_gate": {
            "repository": DICTIONARY_REPOSITORY,
            "commit": DICTIONARY_COMMIT,
            "path": GATES_PATH,
            "blob_sha": GATES_BLOB_SHA,
            "function": "promotion_requires_evidence",
            "binding_status": "PINNED_POLICY_REFERENCE",
        },
        "scalarization": {
            "status": "UNRESOLVED",
            "epistemic_support_scalar_present": False,
            "numeric_evidence_weights_present": False,
        },
        "affect_confidence_promoted": False,
        "phase_similarity_promoted": False,
        "vector_bound": False,
        "t36_realization_present": False,
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "EPISTEMIC_ANTECEDENTS_BOUND",
    }
    return {**core, "epistemic_bundle_commitment": _seal(BUNDLE_DOMAIN, core)}


def validate_epistemic_support_bundle_v06(bundle: Mapping[str, Any]) -> bool:
    if bundle.get("schema") != BUNDLE_SCHEMA:
        raise EpistemicBundleError("unsupported epistemic bundle schema")
    claim = bundle.get("claim")
    if not isinstance(claim, Mapping) or claim.get("semantic_term_id") != CLAIM_TERM:
        raise EpistemicBundleError("claim binding mismatch")
    _nonempty(claim.get("claim_id"), "claim_id")
    _hash64(claim.get("claim_commitment"), "claim_commitment")
    proposition = bundle.get("proposition")
    if not isinstance(proposition, Mapping) or proposition.get("semantic_term_id") != PROPOSITION_TERM:
        raise EpistemicBundleError("proposition binding mismatch")
    _hash64(proposition.get("proposition_commitment"), "proposition_commitment")
    _hash64(bundle.get("inference_framework_commitment"), "inference_framework_commitment")

    evidence = bundle.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise EpistemicBundleError("evidence lineage missing")
    ids = []
    for item in evidence:
        if not isinstance(item, Mapping):
            raise EpistemicBundleError("evidence lineage item malformed")
        ids.append(_nonempty(item.get("evidence_id"), "evidence_id"))
        _hash64(item.get("evidence_item_commitment"), "evidence_item_commitment")
        if item.get("evidence_role") not in EVIDENCE_ROLES or item.get("relation_to_claim") not in CLAIM_RELATIONS:
            raise EpistemicBundleError("evidence lineage role mismatch")
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise EpistemicBundleError("evidence lineage must be unique and canonical-order")

    confidence = bundle.get("confidence")
    if not isinstance(confidence, Mapping) or confidence.get("semantic_term_id") != CONFIDENCE_TERM:
        raise EpistemicBundleError("confidence binding missing")
    if confidence.get("status") == "BOUND_CANDIDATE":
        _hash64(confidence.get("confidence_commitment"), "confidence_commitment")
    elif confidence.get("status") != "UNRESOLVED":
        raise EpistemicBundleError("confidence status mismatch")

    gate = bundle.get("dictionary_promotion_gate")
    expected_gate = {
        "repository": DICTIONARY_REPOSITORY,
        "commit": DICTIONARY_COMMIT,
        "path": GATES_PATH,
        "blob_sha": GATES_BLOB_SHA,
        "function": "promotion_requires_evidence",
        "binding_status": "PINNED_POLICY_REFERENCE",
    }
    if gate != expected_gate:
        raise EpistemicBundleError("Dictionary promotion gate pin mismatch")

    scalarization = bundle.get("scalarization")
    if scalarization != {
        "status": "UNRESOLVED",
        "epistemic_support_scalar_present": False,
        "numeric_evidence_weights_present": False,
    }:
        raise EpistemicBundleError("epistemic scalarization frontier mismatch")
    for key in (
        "affect_confidence_promoted",
        "phase_similarity_promoted",
        "vector_bound",
        "t36_realization_present",
        "production_runtime_write",
        "execution_admitted",
        "canon_allowed",
    ):
        if bundle.get(key) is not False:
            raise EpistemicBundleError(f"epistemic boundary violated: {key}")
    if bundle.get("status") != "EPISTEMIC_ANTECEDENTS_BOUND":
        raise EpistemicBundleError("wrong epistemic bundle status")
    supplied = _hash64(bundle.get("epistemic_bundle_commitment"), "epistemic_bundle_commitment")
    core = dict(bundle)
    core.pop("epistemic_bundle_commitment", None)
    if supplied != _seal(BUNDLE_DOMAIN, core):
        raise EpistemicBundleError("epistemic bundle commitment mismatch")
    return True


def build_kaku_epistemic_binding_v06(*, kaku_id: str, bundle: Mapping[str, Any]) -> dict[str, Any]:
    validate_epistemic_support_bundle_v06(bundle)
    core = {
        "schema": KAKU_SCHEMA,
        "kaku_id": _nonempty(kaku_id, "kaku_id"),
        "epistemic_bundle_commitment": _hash64(
            bundle.get("epistemic_bundle_commitment"), "epistemic_bundle_commitment"
        ),
        "antecedents_bound": True,
        "epistemic_support_scalar_present": False,
        "scalarization_status": "UNRESOLVED",
        "vector_synthesis_allowed": False,
        "vector_bound": False,
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "KAKU_EPISTEMIC_ANTECEDENTS_BOUND",
    }
    return {**core, "kaku_epistemic_binding_commitment": _seal(KAKU_DOMAIN, core)}


def validate_kaku_epistemic_binding_v06(binding: Mapping[str, Any]) -> bool:
    if binding.get("schema") != KAKU_SCHEMA:
        raise EpistemicBundleError("unsupported KAKU epistemic binding schema")
    _nonempty(binding.get("kaku_id"), "kaku_id")
    _hash64(binding.get("epistemic_bundle_commitment"), "epistemic_bundle_commitment")
    if binding.get("antecedents_bound") is not True:
        raise EpistemicBundleError("epistemic antecedents must be bound")
    if binding.get("epistemic_support_scalar_present") is not False:
        raise EpistemicBundleError("epistemic scalar remains unresolved")
    if binding.get("scalarization_status") != "UNRESOLVED":
        raise EpistemicBundleError("epistemic scalarization status mismatch")
    for key in ("vector_synthesis_allowed", "vector_bound", "production_runtime_write", "execution_admitted", "canon_allowed"):
        if binding.get(key) is not False:
            raise EpistemicBundleError(f"KAKU epistemic boundary violated: {key}")
    if binding.get("status") != "KAKU_EPISTEMIC_ANTECEDENTS_BOUND":
        raise EpistemicBundleError("wrong KAKU epistemic binding status")
    supplied = _hash64(binding.get("kaku_epistemic_binding_commitment"), "kaku_epistemic_binding_commitment")
    core = dict(binding)
    core.pop("kaku_epistemic_binding_commitment", None)
    if supplied != _seal(KAKU_DOMAIN, core):
        raise EpistemicBundleError("KAKU epistemic binding commitment mismatch")
    return True
