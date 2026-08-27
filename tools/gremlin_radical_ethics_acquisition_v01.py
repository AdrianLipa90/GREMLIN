from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from tools.gremlin_kaku_radical_scalar_plane_v01 import (
    build_radical_scalar_admission,
    validate_radical_scalar_admission,
)

SCALAR_PRODUCER_SCHEMA = "GREMLIN_RADICAL_ETHICS_SCALAR_PRODUCER_CONTRACT_V0_1"
SCALAR_RECEIPT_SCHEMA = "GREMLIN_RADICAL_ETHICS_SCALAR_RECEIPT_V0_1"
GATE_RECEIPT_SCHEMA = "GREMLIN_RADICAL_ETHICS_GATE_RECEIPT_V0_1"
BUNDLE_SCHEMA = "GREMLIN_RADICAL_ETHICS_ACQUISITION_BUNDLE_V0_1"

SCALAR_PRODUCER_DOMAIN = b"GREMLIN-RADICAL-ETHICS-SCALAR-PRODUCER/v0.1\x00"
SCALAR_RECEIPT_DOMAIN = b"GREMLIN-RADICAL-ETHICS-SCALAR-RECEIPT/v0.1\x00"
GATE_RECEIPT_DOMAIN = b"GREMLIN-RADICAL-ETHICS-GATE-RECEIPT/v0.1\x00"
BUNDLE_DOMAIN = b"GREMLIN-RADICAL-ETHICS-BUNDLE/v0.1\x00"

PRE_VECTOR_STAGE = "PRE_VECTOR_CONTEXTUAL_ASSESSMENT"
POST_REALIZATION_STAGE = "POST_REALIZATION_RELATIONAL_ETHICS"
LIVE_ROOT = "/dev/shm/ciel_noema"

SCALAR_CONTRACTS = {
    "contradiction_load": {
        "canonical_term_id": "CLX2-DYN-009",
        "semantic_class": "relational tension",
        "support_term_ids": (),
    },
    "recursive_integrity": {
        "canonical_term_id": "CLX2-DYN-010",
        "semantic_class": "organizational property",
        "support_term_ids": ("CLX2-DYN-009", "CLX2-TIME-009"),
    },
    "ethical_integrity": {
        "canonical_term_id": "CLX2-DYN-011",
        "semantic_class": "relational-contextual scalar/constraint family",
        "support_term_ids": (
            "CLX2-DYN-010",
            "CLX2-DYN-012",
            "CLX2-DYN-013",
            "CLX2-DYN-014",
            "CLX2-SEM-019",
        ),
    },
}

GATE_CONTRACTS = {
    "consent": {
        "canonical_term_id": "CLX2-DYN-012",
        "allowed_status": ("GRANTED", "DENIED", "UNRESOLVED"),
    },
    "reversibility": {
        "canonical_term_id": "CLX2-DYN-013",
        "allowed_status": ("SATISFIED", "FAILED", "UNRESOLVED"),
    },
    "no_go": {
        "canonical_term_id": "CLX2-DYN-014",
        "allowed_status": ("CLEAR", "HIT", "UNRESOLVED"),
    },
}

SOURCE_CLASSIFICATIONS = {
    "LIVE_NOEMA_WITNESS",
    "EXTERNAL_OBSERVATION",
    "CIEL_IMPLEMENTATION_DONOR",
    "NOEMA_IMPLEMENTATION_DONOR",
    "STATIC_REFERENCE",
    "TEST_FIXTURE",
}

PRODUCER_CLASSIFICATIONS = {
    "SEMANTICALLY_BOUND_PRODUCER_CANDIDATE",
    "REFERENCE_PRODUCER",
    "TEST_PRODUCER",
}

IMPLEMENTATION_DONORS = {
    "ciel_ethical_engine": {
        "implementation_ref": "AdrianLipa90/CIEL-Omega-ApokalypOS:src/CIEL_OMEGA_COMPLETE_SYSTEM/ciel_omega/ethics/ethical_engine.py@82757ef793b55f7344ed47fc55b4f2618263798a",
        "candidate_role": "ethical_integrity_feature",
        "binding_status": "PARTIAL_FEATURE_DONOR_CANDIDATE",
        "realization_stage": POST_REALIZATION_STAGE,
    },
    "noema_relational_ethics_field_v2_1": {
        "implementation_ref": "NOEMA:/NOEMA/00_CONTROL/ETHICS/noema_relational_ethics_field_v2_1.py@sha256:8b98af7b1edba93e572114585b974a9dbbf7c94f93cbb484b1819c797b9fb9a6",
        "candidate_role": "ethical_integrity_relational_realization",
        "binding_status": "HARDPATH_VALIDATED_DONOR",
        "realization_stage": POST_REALIZATION_STAGE,
        "operating_mode": "LIVE_COMPUTE_ON_EXCHANGE_NO_STATIC_ETHICS_STATE",
    },
}


class GremlinRadicalEthicsError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _commit(domain: bytes, value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    text = str(value)
    if not text:
        raise GremlinRadicalEthicsError(f"{name} must be non-empty")
    return text


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise GremlinRadicalEthicsError(f"{name} must be finite")
    return x


def _digest(value: Any, name: str) -> str:
    text = _nonempty(value, name)
    if len(text) != 64:
        raise GremlinRadicalEthicsError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise GremlinRadicalEthicsError(f"{name} must be hex") from exc
    return text


def _unique(values: Sequence[str], name: str) -> list[str]:
    result = sorted(_nonempty(v, name) for v in values)
    if len(set(result)) != len(result):
        raise GremlinRadicalEthicsError(f"duplicate {name}")
    return result


def _scalar(role: str) -> Mapping[str, Any]:
    try:
        return SCALAR_CONTRACTS[role]
    except KeyError as exc:
        raise GremlinRadicalEthicsError(f"unsupported Radical ethics scalar role: {role}") from exc


def _gate(role: str) -> Mapping[str, Any]:
    try:
        return GATE_CONTRACTS[role]
    except KeyError as exc:
        raise GremlinRadicalEthicsError(f"unsupported Radical ethics gate role: {role}") from exc


def _live_binding(source_classification: str, live_required: bool, live_surface_ref: str | None) -> str | None:
    if live_required:
        if source_classification != "LIVE_NOEMA_WITNESS":
            raise GremlinRadicalEthicsError("live-required source must bind LIVE_NOEMA_WITNESS")
        live_ref = _nonempty(live_surface_ref, "live_surface_ref")
        if live_ref != LIVE_ROOT and not live_ref.startswith(LIVE_ROOT + "/"):
            raise GremlinRadicalEthicsError("live-required source must bind the canonical NOEMA surface")
        return live_ref
    return None if live_surface_ref is None else _nonempty(live_surface_ref, "live_surface_ref")


def build_scalar_producer_contract(
    *,
    producer_id: str,
    producer_version: str,
    semantic_role: str,
    scale_id: str,
    formula_contract_ref: str,
    implementation_ref: str,
    source_classification: str,
    producer_classification: str = "SEMANTICALLY_BOUND_PRODUCER_CANDIDATE",
    live_required: bool = False,
) -> dict[str, Any]:
    semantic = _scalar(semantic_role)
    source = _nonempty(source_classification, "source_classification").upper()
    producer_class = _nonempty(producer_classification, "producer_classification").upper()
    if source not in SOURCE_CLASSIFICATIONS:
        raise GremlinRadicalEthicsError(f"unsupported source classification: {source}")
    if producer_class not in PRODUCER_CLASSIFICATIONS:
        raise GremlinRadicalEthicsError(f"unsupported producer classification: {producer_class}")
    if live_required and source != "LIVE_NOEMA_WITNESS":
        raise GremlinRadicalEthicsError("live-required producer must bind LIVE_NOEMA_WITNESS")

    core = {
        "schema": SCALAR_PRODUCER_SCHEMA,
        "producer_id": _nonempty(producer_id, "producer_id"),
        "producer_version": _nonempty(producer_version, "producer_version"),
        "producer_classification": producer_class,
        "semantic_role": semantic_role,
        "canonical_term_id": semantic["canonical_term_id"],
        "semantic_class": semantic["semantic_class"],
        "support_term_ids": list(semantic["support_term_ids"]),
        "scale_id": _nonempty(scale_id, "scale_id"),
        "formula_contract_ref": _nonempty(formula_contract_ref, "formula_contract_ref"),
        "implementation_ref": _nonempty(implementation_ref, "implementation_ref"),
        "source_classification": source,
        "live_required": bool(live_required),
        "realization_stage": PRE_VECTOR_STAGE,
        "silent_scale_conversion_allowed": False,
        "conflict_averaging_allowed": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "RADICAL_ETHICS_SCALAR_PRODUCER_CANDIDATE",
    }
    return {**core, "producer_contract_commitment": _commit(SCALAR_PRODUCER_DOMAIN, core)}


def validate_scalar_producer_contract(contract: Mapping[str, Any]) -> bool:
    if contract.get("schema") != SCALAR_PRODUCER_SCHEMA:
        raise GremlinRadicalEthicsError("unsupported scalar producer schema")
    semantic = _scalar(str(contract.get("semantic_role", "")))
    if contract.get("canonical_term_id") != semantic["canonical_term_id"]:
        raise GremlinRadicalEthicsError("scalar producer canonical term mismatch")
    if contract.get("semantic_class") != semantic["semantic_class"]:
        raise GremlinRadicalEthicsError("scalar producer semantic class mismatch")
    if list(contract.get("support_term_ids", ())) != list(semantic["support_term_ids"]):
        raise GremlinRadicalEthicsError("scalar producer support-term mismatch")
    for key in ("producer_id", "producer_version", "scale_id", "formula_contract_ref", "implementation_ref"):
        _nonempty(contract.get(key), key)
    source = str(contract.get("source_classification", ""))
    if source not in SOURCE_CLASSIFICATIONS:
        raise GremlinRadicalEthicsError("invalid scalar producer source classification")
    if str(contract.get("producer_classification", "")) not in PRODUCER_CLASSIFICATIONS:
        raise GremlinRadicalEthicsError("invalid scalar producer classification")
    if contract.get("live_required") is True and source != "LIVE_NOEMA_WITNESS":
        raise GremlinRadicalEthicsError("live-required producer source mismatch")
    if contract.get("realization_stage") != PRE_VECTOR_STAGE:
        raise GremlinRadicalEthicsError("scalar producer realization stage mismatch")
    if contract.get("silent_scale_conversion_allowed") is not False or contract.get("conflict_averaging_allowed") is not False:
        raise GremlinRadicalEthicsError("scalar aggregation boundary violated")
    if contract.get("execution_admitted") is not False or contract.get("canon_allowed") is not False:
        raise GremlinRadicalEthicsError("scalar producer authority boundary violated")
    if contract.get("status") != "RADICAL_ETHICS_SCALAR_PRODUCER_CANDIDATE":
        raise GremlinRadicalEthicsError("invalid scalar producer status")
    supplied = _digest(contract.get("producer_contract_commitment"), "producer_contract_commitment")
    core = dict(contract)
    core.pop("producer_contract_commitment", None)
    if supplied != _commit(SCALAR_PRODUCER_DOMAIN, core):
        raise GremlinRadicalEthicsError("scalar producer commitment mismatch")
    return True


def build_gate_receipt(
    *,
    gate_role: str,
    status: str,
    relation_ids: Sequence[str],
    source_ref: str,
    decision_context_commitment: str,
    epistemic_status: str,
    evidence_refs: Sequence[str],
    reason: str = "",
    subject_refs: Sequence[str] = (),
    source_classification: str = "EXTERNAL_OBSERVATION",
    live_required: bool = False,
    live_surface_ref: str | None = None,
) -> dict[str, Any]:
    semantic = _gate(gate_role)
    normalized_status = _nonempty(status, "status").upper()
    if normalized_status not in semantic["allowed_status"]:
        raise GremlinRadicalEthicsError(f"unsupported {gate_role} status: {normalized_status}")
    relations = _unique(relation_ids, "relation_id")
    if not relations:
        raise GremlinRadicalEthicsError("gate receipt requires relation coverage")
    subjects = _unique(subject_refs, "subject_ref")
    if gate_role == "consent" and not subjects:
        raise GremlinRadicalEthicsError("consent receipt requires affected subject references")
    source = _nonempty(source_classification, "source_classification").upper()
    if source not in SOURCE_CLASSIFICATIONS:
        raise GremlinRadicalEthicsError("unsupported gate source classification")
    live_ref = _live_binding(source, bool(live_required), live_surface_ref)

    core = {
        "schema": GATE_RECEIPT_SCHEMA,
        "gate_role": gate_role,
        "canonical_term_id": semantic["canonical_term_id"],
        "status": normalized_status,
        "relation_ids": relations,
        "subject_refs": subjects,
        "source_classification": source,
        "source_ref": _nonempty(source_ref, "source_ref"),
        "live_required": bool(live_required),
        "live_surface_ref": live_ref,
        "decision_context_commitment": _digest(decision_context_commitment, "decision_context_commitment"),
        "epistemic_status": _nonempty(epistemic_status, "epistemic_status"),
        "evidence_refs": sorted(_nonempty(v, "evidence_ref") for v in evidence_refs),
        "reason": str(reason),
        "gate_is_structural": True,
        "gate_weighting_allowed": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status_class": "RADICAL_STRUCTURAL_GATE_RECEIPT",
    }
    return {**core, "receipt_id": _commit(GATE_RECEIPT_DOMAIN, core)}


def validate_gate_receipt(receipt: Mapping[str, Any]) -> bool:
    if receipt.get("schema") != GATE_RECEIPT_SCHEMA:
        raise GremlinRadicalEthicsError("unsupported gate receipt schema")
    role = str(receipt.get("gate_role", ""))
    semantic = _gate(role)
    if receipt.get("canonical_term_id") != semantic["canonical_term_id"] or receipt.get("status") not in semantic["allowed_status"]:
        raise GremlinRadicalEthicsError("gate semantic/status mismatch")
    relations = receipt.get("relation_ids")
    subjects = receipt.get("subject_refs")
    if not isinstance(relations, list) or relations != sorted(set(map(str, relations))) or not relations:
        raise GremlinRadicalEthicsError("gate relation coverage must be canonical and unique")
    if not isinstance(subjects, list) or subjects != sorted(set(map(str, subjects))):
        raise GremlinRadicalEthicsError("gate subject refs must be canonical and unique")
    if role == "consent" and not subjects:
        raise GremlinRadicalEthicsError("consent receipt requires affected subject references")
    source = str(receipt.get("source_classification", ""))
    if source not in SOURCE_CLASSIFICATIONS:
        raise GremlinRadicalEthicsError("invalid gate source classification")
    _live_binding(source, receipt.get("live_required") is True, receipt.get("live_surface_ref"))
    _nonempty(receipt.get("source_ref"), "source_ref")
    _nonempty(receipt.get("epistemic_status"), "epistemic_status")
    _digest(receipt.get("decision_context_commitment"), "decision_context_commitment")
    if receipt.get("gate_is_structural") is not True or receipt.get("gate_weighting_allowed") is not False:
        raise GremlinRadicalEthicsError("structural gate boundary violated")
    if receipt.get("execution_admitted") is not False or receipt.get("canon_allowed") is not False:
        raise GremlinRadicalEthicsError("gate receipt authority boundary violated")
    if receipt.get("status_class") != "RADICAL_STRUCTURAL_GATE_RECEIPT":
        raise GremlinRadicalEthicsError("invalid gate receipt status class")
    supplied = _digest(receipt.get("receipt_id"), "receipt_id")
    core = dict(receipt)
    core.pop("receipt_id", None)
    if supplied != _commit(GATE_RECEIPT_DOMAIN, core):
        raise GremlinRadicalEthicsError("gate receipt commitment mismatch")
    return True


def build_scalar_receipt(
    *,
    producer_contract: Mapping[str, Any],
    value: Any,
    source_ref: str,
    input_commitment: str,
    epistemic_status: str,
    evidence_refs: Sequence[str],
    support_receipt_ids: Sequence[str] = (),
    observed_scale_id: str | None = None,
    live_surface_ref: str | None = None,
) -> dict[str, Any]:
    validate_scalar_producer_contract(producer_contract)
    scale_id = _nonempty(observed_scale_id or producer_contract["scale_id"], "observed_scale_id")
    if scale_id != producer_contract["scale_id"]:
        raise GremlinRadicalEthicsError("observed scale differs from producer scale contract")
    support_receipts = sorted(_digest(v, "support_receipt_id") for v in support_receipt_ids)
    if len(set(support_receipts)) != len(support_receipts):
        raise GremlinRadicalEthicsError("duplicate support receipt")
    live_ref = _live_binding(
        str(producer_contract["source_classification"]),
        bool(producer_contract["live_required"]),
        live_surface_ref,
    )

    core = {
        "schema": SCALAR_RECEIPT_SCHEMA,
        "producer_contract_commitment": producer_contract["producer_contract_commitment"],
        "producer_id": producer_contract["producer_id"],
        "producer_version": producer_contract["producer_version"],
        "semantic_role": producer_contract["semantic_role"],
        "canonical_term_id": producer_contract["canonical_term_id"],
        "support_term_ids": list(producer_contract["support_term_ids"]),
        "support_receipt_ids": support_receipts,
        "value_f64_hex": _finite(value, "value").hex(),
        "scale_id": scale_id,
        "source_classification": producer_contract["source_classification"],
        "source_ref": _nonempty(source_ref, "source_ref"),
        "live_required": bool(producer_contract["live_required"]),
        "live_surface_ref": live_ref,
        "input_commitment": _digest(input_commitment, "input_commitment"),
        "formula_contract_ref": producer_contract["formula_contract_ref"],
        "implementation_ref": producer_contract["implementation_ref"],
        "realization_stage": PRE_VECTOR_STAGE,
        "epistemic_status": _nonempty(epistemic_status, "epistemic_status"),
        "evidence_refs": sorted(_nonempty(v, "evidence_ref") for v in evidence_refs),
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "RADICAL_ETHICS_SCALAR_RECORDED",
    }
    return {**core, "receipt_id": _commit(SCALAR_RECEIPT_DOMAIN, core)}


def validate_scalar_receipt(receipt: Mapping[str, Any]) -> bool:
    if receipt.get("schema") != SCALAR_RECEIPT_SCHEMA:
        raise GremlinRadicalEthicsError("unsupported scalar receipt schema")
    semantic = _scalar(str(receipt.get("semantic_role", "")))
    if receipt.get("canonical_term_id") != semantic["canonical_term_id"] or list(receipt.get("support_term_ids", ())) != list(semantic["support_term_ids"]):
        raise GremlinRadicalEthicsError("scalar receipt semantic contract mismatch")
    support_receipts = receipt.get("support_receipt_ids")
    if not isinstance(support_receipts, list) or support_receipts != sorted(set(map(str, support_receipts))):
        raise GremlinRadicalEthicsError("support receipt lineage must be canonical and unique")
    for support in support_receipts:
        _digest(support, "support_receipt_id")
    _finite(float.fromhex(str(receipt.get("value_f64_hex"))), "value")
    for key in ("producer_id", "producer_version", "scale_id", "source_ref", "formula_contract_ref", "implementation_ref", "epistemic_status"):
        _nonempty(receipt.get(key), key)
    _digest(receipt.get("producer_contract_commitment"), "producer_contract_commitment")
    _digest(receipt.get("input_commitment"), "input_commitment")
    source = str(receipt.get("source_classification", ""))
    if source not in SOURCE_CLASSIFICATIONS:
        raise GremlinRadicalEthicsError("invalid scalar receipt source classification")
    _live_binding(source, receipt.get("live_required") is True, receipt.get("live_surface_ref"))
    if receipt.get("realization_stage") != PRE_VECTOR_STAGE:
        raise GremlinRadicalEthicsError("scalar receipt realization stage mismatch")
    if receipt.get("execution_admitted") is not False or receipt.get("canon_allowed") is not False:
        raise GremlinRadicalEthicsError("scalar receipt authority boundary violated")
    if receipt.get("status") != "RADICAL_ETHICS_SCALAR_RECORDED":
        raise GremlinRadicalEthicsError("invalid scalar receipt status")
    supplied = _digest(receipt.get("receipt_id"), "receipt_id")
    core = dict(receipt)
    core.pop("receipt_id", None)
    if supplied != _commit(SCALAR_RECEIPT_DOMAIN, core):
        raise GremlinRadicalEthicsError("scalar receipt commitment mismatch")
    return True


def _validate_lineage(
    scalars: Mapping[str, Mapping[str, Any]],
    gates: Mapping[str, Mapping[str, Any]],
) -> None:
    contradiction = scalars["contradiction_load"]
    recursive = scalars["recursive_integrity"]
    ethical = scalars["ethical_integrity"]
    if contradiction["receipt_id"] not in recursive["support_receipt_ids"]:
        raise GremlinRadicalEthicsError("recursive integrity receipt must bind contradiction lineage")
    required = {
        recursive["receipt_id"],
        gates["consent"]["receipt_id"],
        gates["reversibility"]["receipt_id"],
        gates["no_go"]["receipt_id"],
    }
    if not required.issubset(set(ethical["support_receipt_ids"])):
        raise GremlinRadicalEthicsError("ethical integrity receipt must bind recursive integrity and all structural gate receipts")


def build_ethics_acquisition_bundle(
    *,
    relation_ids: Sequence[str],
    scalar_receipts: Sequence[Mapping[str, Any]],
    gate_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    relations = _unique(relation_ids, "relation_id")
    if not relations:
        raise GremlinRadicalEthicsError("ethics acquisition requires relation lineage")

    scalars: dict[str, Mapping[str, Any]] = {}
    for receipt in scalar_receipts:
        validate_scalar_receipt(receipt)
        role = str(receipt["semantic_role"])
        if role in scalars:
            raise GremlinRadicalEthicsError(f"conflicting duplicate ethics scalar role: {role}")
        scalars[role] = receipt
    if set(scalars) != set(SCALAR_CONTRACTS):
        raise GremlinRadicalEthicsError("exact Radical ethics scalar role set required")

    gates: dict[str, Mapping[str, Any]] = {}
    for receipt in gate_receipts:
        validate_gate_receipt(receipt)
        role = str(receipt["gate_role"])
        if role in gates:
            raise GremlinRadicalEthicsError(f"conflicting duplicate structural gate role: {role}")
        if receipt["relation_ids"] != relations:
            raise GremlinRadicalEthicsError(f"{role} gate relation coverage differs from Radical lineage")
        gates[role] = receipt
    if set(gates) != set(GATE_CONTRACTS):
        raise GremlinRadicalEthicsError("exact Radical structural gate set required")
    _validate_lineage(scalars, gates)

    scalar_entries = []
    for role in sorted(scalars):
        receipt = scalars[role]
        scalar_entries.append({
            "semantic_role": role,
            "canonical_term_id": receipt["canonical_term_id"],
            "receipt_id": receipt["receipt_id"],
            "support_receipt_ids": list(receipt["support_receipt_ids"]),
            "value_f64_hex": receipt["value_f64_hex"],
            "scale_id": receipt["scale_id"],
            "source_classification": receipt["source_classification"],
            "source_ref": receipt["source_ref"],
            "live_required": receipt["live_required"],
            "live_surface_ref": receipt["live_surface_ref"],
            "epistemic_status": receipt["epistemic_status"],
        })

    gate_entries = []
    for role in sorted(gates):
        receipt = gates[role]
        gate_entries.append({
            "gate_role": role,
            "canonical_term_id": receipt["canonical_term_id"],
            "receipt_id": receipt["receipt_id"],
            "status": receipt["status"],
            "relation_ids": list(receipt["relation_ids"]),
            "subject_refs": list(receipt["subject_refs"]),
            "source_classification": receipt["source_classification"],
            "source_ref": receipt["source_ref"],
            "live_required": receipt["live_required"],
            "live_surface_ref": receipt["live_surface_ref"],
            "decision_context_commitment": receipt["decision_context_commitment"],
            "reason": receipt["reason"],
        })

    core = {
        "schema": BUNDLE_SCHEMA,
        "relation_ids": relations,
        "scalar_receipts": scalar_entries,
        "gate_receipts": gate_entries,
        "pre_vector_stage": PRE_VECTOR_STAGE,
        "relational_ethics_realization_stage": POST_REALIZATION_STAGE,
        "relational_ethics_realization_pending": True,
        "gate_weighting_used": False,
        "gate_conflict_averaging_used": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "RADICAL_ETHICS_ACQUISITION_COMPLETE",
    }
    return {**core, "ethics_acquisition_commitment": _commit(BUNDLE_DOMAIN, core)}


def validate_ethics_acquisition_bundle(bundle: Mapping[str, Any]) -> bool:
    if bundle.get("schema") != BUNDLE_SCHEMA:
        raise GremlinRadicalEthicsError("unsupported ethics acquisition bundle schema")
    relations = bundle.get("relation_ids")
    if not isinstance(relations, list) or relations != sorted(set(map(str, relations))) or not relations:
        raise GremlinRadicalEthicsError("bundle relation lineage must be canonical and unique")
    scalar_items = bundle.get("scalar_receipts")
    gate_items = bundle.get("gate_receipts")
    if not isinstance(scalar_items, list) or [x.get("semantic_role") for x in scalar_items] != sorted(SCALAR_CONTRACTS):
        raise GremlinRadicalEthicsError("bundle scalar role ordering mismatch")
    if not isinstance(gate_items, list) or [x.get("gate_role") for x in gate_items] != sorted(GATE_CONTRACTS):
        raise GremlinRadicalEthicsError("bundle gate role ordering mismatch")

    scalars: dict[str, Mapping[str, Any]] = {}
    for item in scalar_items:
        role = str(item.get("semantic_role", ""))
        semantic = _scalar(role)
        if item.get("canonical_term_id") != semantic["canonical_term_id"]:
            raise GremlinRadicalEthicsError("bundle scalar canonical term mismatch")
        _digest(item.get("receipt_id"), "receipt_id")
        supports = item.get("support_receipt_ids")
        if not isinstance(supports, list) or supports != sorted(set(map(str, supports))):
            raise GremlinRadicalEthicsError("bundle scalar support lineage mismatch")
        for support in supports:
            _digest(support, "support_receipt_id")
        _finite(float.fromhex(str(item.get("value_f64_hex"))), "value")
        for key in ("scale_id", "source_ref", "epistemic_status"):
            _nonempty(item.get(key), key)
        source = str(item.get("source_classification", ""))
        if source not in SOURCE_CLASSIFICATIONS:
            raise GremlinRadicalEthicsError("bundle scalar source classification mismatch")
        _live_binding(source, item.get("live_required") is True, item.get("live_surface_ref"))
        scalars[role] = item

    gates: dict[str, Mapping[str, Any]] = {}
    for item in gate_items:
        role = str(item.get("gate_role", ""))
        semantic = _gate(role)
        if item.get("canonical_term_id") != semantic["canonical_term_id"] or item.get("status") not in semantic["allowed_status"]:
            raise GremlinRadicalEthicsError("bundle gate semantic/status mismatch")
        if item.get("relation_ids") != relations:
            raise GremlinRadicalEthicsError("bundle gate relation coverage mismatch")
        _digest(item.get("receipt_id"), "receipt_id")
        _digest(item.get("decision_context_commitment"), "decision_context_commitment")
        _nonempty(item.get("source_ref"), "source_ref")
        subjects = item.get("subject_refs")
        if not isinstance(subjects, list) or subjects != sorted(set(map(str, subjects))):
            raise GremlinRadicalEthicsError("bundle gate subject lineage mismatch")
        if role == "consent" and not subjects:
            raise GremlinRadicalEthicsError("bundle consent subject lineage required")
        source = str(item.get("source_classification", ""))
        if source not in SOURCE_CLASSIFICATIONS:
            raise GremlinRadicalEthicsError("bundle gate source classification mismatch")
        _live_binding(source, item.get("live_required") is True, item.get("live_surface_ref"))
        gates[role] = item

    _validate_lineage(scalars, gates)
    if bundle.get("pre_vector_stage") != PRE_VECTOR_STAGE or bundle.get("relational_ethics_realization_stage") != POST_REALIZATION_STAGE:
        raise GremlinRadicalEthicsError("ethics acquisition stage contract mismatch")
    if bundle.get("relational_ethics_realization_pending") is not True:
        raise GremlinRadicalEthicsError("relational ethics realization must remain pending at pre-vector acquisition")
    if bundle.get("gate_weighting_used") is not False or bundle.get("gate_conflict_averaging_used") is not False:
        raise GremlinRadicalEthicsError("structural gate aggregation boundary violated")
    if bundle.get("execution_admitted") is not False or bundle.get("canon_allowed") is not False:
        raise GremlinRadicalEthicsError("ethics bundle authority boundary violated")
    if bundle.get("status") != "RADICAL_ETHICS_ACQUISITION_COMPLETE":
        raise GremlinRadicalEthicsError("invalid ethics acquisition bundle status")
    supplied = _digest(bundle.get("ethics_acquisition_commitment"), "ethics_acquisition_commitment")
    core = dict(bundle)
    core.pop("ethics_acquisition_commitment", None)
    if supplied != _commit(BUNDLE_DOMAIN, core):
        raise GremlinRadicalEthicsError("ethics acquisition bundle commitment mismatch")
    return True


def build_radical_admission_from_ethics_acquisition(
    *,
    ethics_bundle: Mapping[str, Any],
    radical_id: str,
    candidate_id: str,
    ordered_kaku_packets: Sequence[Mapping[str, Any]],
    relation_ids: Sequence[str],
    evidence_refs: Sequence[str] = (),
) -> dict[str, Any]:
    validate_ethics_acquisition_bundle(ethics_bundle)
    relations = _unique(relation_ids, "relation_id")
    if relations != ethics_bundle["relation_ids"]:
        raise GremlinRadicalEthicsError("Radical relation lineage differs from ethics acquisition")
    scalars = {x["semantic_role"]: x for x in ethics_bundle["scalar_receipts"]}
    gates = {x["gate_role"]: x for x in ethics_bundle["gate_receipts"]}

    def scalar_mapping(name: str) -> dict[str, Any]:
        item = scalars[name]
        return {
            "value": float.fromhex(item["value_f64_hex"]),
            "scale_id": item["scale_id"],
            "source_ref": f"receipt:{item['receipt_id']}",
            "epistemic_status": item["epistemic_status"],
        }

    def gate_mapping(name: str) -> dict[str, Any]:
        item = gates[name]
        return {
            "status": item["status"],
            "source_ref": f"receipt:{item['receipt_id']}",
            "reason": item["reason"],
        }

    lineage = [f"receipt:{x['receipt_id']}" for x in ethics_bundle["scalar_receipts"]]
    lineage.extend(f"receipt:{x['receipt_id']}" for x in ethics_bundle["gate_receipts"])
    lineage.append(f"ethics-acquisition:{ethics_bundle['ethics_acquisition_commitment']}")
    lineage.extend(str(v) for v in evidence_refs)

    record = build_radical_scalar_admission(
        radical_id=radical_id,
        candidate_id=candidate_id,
        ordered_kaku_packets=ordered_kaku_packets,
        relation_ids=relations,
        ethical_integrity=scalar_mapping("ethical_integrity"),
        consent_gate=gate_mapping("consent"),
        reversibility_gate=gate_mapping("reversibility"),
        no_go_gate=gate_mapping("no_go"),
        contradiction_load=scalar_mapping("contradiction_load"),
        recursive_integrity=scalar_mapping("recursive_integrity"),
        evidence_refs=lineage,
    )
    validate_radical_scalar_admission(record)
    return record
