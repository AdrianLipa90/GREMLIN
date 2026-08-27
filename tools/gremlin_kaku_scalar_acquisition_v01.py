from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from tools.gremlin_kaku_radical_scalar_plane_v01 import build_kaku_scalar_packet

PRODUCER_SCHEMA = "GREMLIN_KAKU_SCALAR_PRODUCER_CONTRACT_V0_1"
RECEIPT_SCHEMA = "GREMLIN_KAKU_SCALAR_OBSERVATION_RECEIPT_V0_1"
BUNDLE_SCHEMA = "GREMLIN_KAKU_SCALAR_ACQUISITION_BUNDLE_V0_1"

PRODUCER_DOMAIN = b"GREMLIN-KAKU-SCALAR-PRODUCER/v0.1\x00"
RECEIPT_DOMAIN = b"GREMLIN-KAKU-SCALAR-RECEIPT/v0.1\x00"
BUNDLE_DOMAIN = b"GREMLIN-KAKU-SCALAR-BUNDLE/v0.1\x00"

SEMANTIC_CONTRACTS = {
    "valuation": {
        "canonical_term_id": "CLX2-AFFECT-001",
        "semantic_class": "relation/control variable",
    },
    "affect": {
        "canonical_term_id": "CLX2-AFFECT-002",
        "semantic_class": "state/modulator",
    },
    "intention_alignment": {
        "canonical_term_id": "CLX2-AGENCY-001",
        "semantic_class": "future-directed constraint",
    },
    "epistemic_support": {
        "canonical_term_id": "CLX2-SEM-023",
        "semantic_class": "confidence",
        "support_term_ids": ("CLX2-SEM-019", "CLX2-AFFECT-005"),
    },
}

SOURCE_CLASSIFICATIONS = {
    "LIVE_NOEMA_WITNESS",
    "EXTERNAL_OBSERVATION",
    "CIEL_IMPLEMENTATION_DONOR",
    "STATIC_REFERENCE",
    "TEST_FIXTURE",
}

PRODUCER_CLASSIFICATIONS = {
    "SEMANTICALLY_BOUND_PRODUCER_CANDIDATE",
    "REFERENCE_PRODUCER",
    "TEST_PRODUCER",
}

LIVE_ROOT = "/dev/shm/ciel_noema"

CIEL_IMPLEMENTATION_DONORS = {
    "intention_field": {
        "implementation_ref": "AdrianLipa90/CIEL-Omega-ApokalypOS:src/CIEL_OMEGA_COMPLETE_SYSTEM/ciel_omega/fields/intention_field.py@68f93f42a14911ca7ba5a69b3eb7ec37a34eba7a",
        "candidate_role": "intention_alignment",
        "binding_status": "IMPLEMENTATION_DONOR_CANDIDATE",
    },
    "affective_orchestrator": {
        "implementation_ref": "AdrianLipa90/CIEL-Omega-ApokalypOS:src/CIEL_OMEGA_COMPLETE_SYSTEM/ciel_omega/emotion/affective_orchestrator.py@1d0a1dadedaf147fa7628d176352b4c956a06d4a",
        "candidate_role": "affect",
        "binding_status": "IMPLEMENTATION_DONOR_CANDIDATE",
    },
}


class GremlinScalarAcquisitionError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _nonempty(value: Any, name: str) -> str:
    text = str(value)
    if not text:
        raise GremlinScalarAcquisitionError(f"{name} must be non-empty")
    return text


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise GremlinScalarAcquisitionError(f"{name} must be finite")
    return x


def _hash64(value: Any, name: str) -> str:
    text = _nonempty(value, name)
    if len(text) != 64:
        raise GremlinScalarAcquisitionError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise GremlinScalarAcquisitionError(f"{name} must be hex") from exc
    return text


def _semantic_contract(role: str) -> Mapping[str, Any]:
    try:
        return SEMANTIC_CONTRACTS[role]
    except KeyError as exc:
        raise GremlinScalarAcquisitionError(f"unsupported scalar semantic role: {role}") from exc


def build_producer_contract(
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
    semantic = _semantic_contract(semantic_role)
    source_class = _nonempty(source_classification, "source_classification").upper()
    if source_class not in SOURCE_CLASSIFICATIONS:
        raise GremlinScalarAcquisitionError(f"unsupported source classification: {source_class}")
    producer_class = _nonempty(producer_classification, "producer_classification").upper()
    if producer_class not in PRODUCER_CLASSIFICATIONS:
        raise GremlinScalarAcquisitionError(f"unsupported producer classification: {producer_class}")
    if live_required and source_class != "LIVE_NOEMA_WITNESS":
        raise GremlinScalarAcquisitionError("live-required producer must bind LIVE_NOEMA_WITNESS")

    core = {
        "schema": PRODUCER_SCHEMA,
        "producer_id": _nonempty(producer_id, "producer_id"),
        "producer_version": _nonempty(producer_version, "producer_version"),
        "producer_classification": producer_class,
        "semantic_role": semantic_role,
        "canonical_term_id": semantic["canonical_term_id"],
        "semantic_class": semantic["semantic_class"],
        "support_term_ids": list(semantic.get("support_term_ids", ())),
        "scale_id": _nonempty(scale_id, "scale_id"),
        "formula_contract_ref": _nonempty(formula_contract_ref, "formula_contract_ref"),
        "implementation_ref": _nonempty(implementation_ref, "implementation_ref"),
        "source_classification": source_class,
        "live_required": bool(live_required),
        "silent_scale_conversion_allowed": False,
        "conflict_averaging_allowed": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "PRODUCER_CONTRACT_CANDIDATE",
    }
    commitment = hashlib.blake2b(PRODUCER_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    return {**core, "producer_contract_commitment": commitment}


def validate_producer_contract(contract: Mapping[str, Any]) -> bool:
    if contract.get("schema") != PRODUCER_SCHEMA:
        raise GremlinScalarAcquisitionError("unsupported producer schema")
    semantic_role = str(contract.get("semantic_role", ""))
    semantic = _semantic_contract(semantic_role)
    if contract.get("canonical_term_id") != semantic["canonical_term_id"]:
        raise GremlinScalarAcquisitionError("producer canonical term mismatch")
    if contract.get("semantic_class") != semantic["semantic_class"]:
        raise GremlinScalarAcquisitionError("producer semantic class mismatch")
    if list(contract.get("support_term_ids", ())) != list(semantic.get("support_term_ids", ())):
        raise GremlinScalarAcquisitionError("producer support-term contract mismatch")
    for key in (
        "producer_id",
        "producer_version",
        "scale_id",
        "formula_contract_ref",
        "implementation_ref",
    ):
        _nonempty(contract.get(key), key)
    source_class = str(contract.get("source_classification", ""))
    if source_class not in SOURCE_CLASSIFICATIONS:
        raise GremlinScalarAcquisitionError("invalid source classification")
    producer_class = str(contract.get("producer_classification", ""))
    if producer_class not in PRODUCER_CLASSIFICATIONS:
        raise GremlinScalarAcquisitionError("invalid producer classification")
    if contract.get("live_required") is True and source_class != "LIVE_NOEMA_WITNESS":
        raise GremlinScalarAcquisitionError("live-required producer source mismatch")
    if contract.get("silent_scale_conversion_allowed") is not False:
        raise GremlinScalarAcquisitionError("silent scale conversion boundary violated")
    if contract.get("conflict_averaging_allowed") is not False:
        raise GremlinScalarAcquisitionError("conflict averaging boundary violated")
    if contract.get("execution_admitted") is not False or contract.get("canon_allowed") is not False:
        raise GremlinScalarAcquisitionError("producer authority boundary violated")
    if contract.get("status") != "PRODUCER_CONTRACT_CANDIDATE":
        raise GremlinScalarAcquisitionError("invalid producer status")

    supplied = _hash64(contract.get("producer_contract_commitment"), "producer_contract_commitment")
    core = dict(contract)
    core.pop("producer_contract_commitment", None)
    expected = hashlib.blake2b(PRODUCER_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    if supplied != expected:
        raise GremlinScalarAcquisitionError("producer contract commitment mismatch")
    return True


def build_observation_receipt(
    *,
    producer_contract: Mapping[str, Any],
    value: Any,
    source_ref: str,
    input_commitment: str,
    epistemic_status: str,
    evidence_refs: Sequence[str],
    observed_scale_id: str | None = None,
    live_surface_ref: str | None = None,
) -> dict[str, Any]:
    validate_producer_contract(producer_contract)
    scale_id = _nonempty(observed_scale_id or producer_contract["scale_id"], "observed_scale_id")
    if scale_id != producer_contract["scale_id"]:
        raise GremlinScalarAcquisitionError("observed scale differs from producer scale contract")

    source_class = str(producer_contract["source_classification"])
    live_required = bool(producer_contract["live_required"])
    if live_required:
        live_ref = _nonempty(live_surface_ref, "live_surface_ref")
        if live_ref != LIVE_ROOT and not live_ref.startswith(LIVE_ROOT + "/"):
            raise GremlinScalarAcquisitionError("live producer must bind the canonical NOEMA surface")
    else:
        live_ref = None if live_surface_ref is None else _nonempty(live_surface_ref, "live_surface_ref")

    core = {
        "schema": RECEIPT_SCHEMA,
        "producer_contract_commitment": producer_contract["producer_contract_commitment"],
        "producer_id": producer_contract["producer_id"],
        "producer_version": producer_contract["producer_version"],
        "producer_classification": producer_contract["producer_classification"],
        "semantic_role": producer_contract["semantic_role"],
        "canonical_term_id": producer_contract["canonical_term_id"],
        "support_term_ids": list(producer_contract["support_term_ids"]),
        "value_f64_hex": _finite(value, "value").hex(),
        "scale_id": scale_id,
        "source_classification": source_class,
        "source_ref": _nonempty(source_ref, "source_ref"),
        "live_required": live_required,
        "live_surface_ref": live_ref,
        "input_commitment": _hash64(input_commitment, "input_commitment"),
        "formula_contract_ref": producer_contract["formula_contract_ref"],
        "implementation_ref": producer_contract["implementation_ref"],
        "epistemic_status": _nonempty(epistemic_status, "epistemic_status"),
        "evidence_refs": sorted(_nonempty(v, "evidence_ref") for v in evidence_refs),
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "SCALAR_OBSERVATION_RECORDED",
    }
    receipt_id = hashlib.blake2b(RECEIPT_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    return {**core, "receipt_id": receipt_id}


def validate_observation_receipt(receipt: Mapping[str, Any]) -> bool:
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise GremlinScalarAcquisitionError("unsupported observation receipt schema")
    semantic_role = str(receipt.get("semantic_role", ""))
    semantic = _semantic_contract(semantic_role)
    if receipt.get("canonical_term_id") != semantic["canonical_term_id"]:
        raise GremlinScalarAcquisitionError("observation canonical term mismatch")
    if list(receipt.get("support_term_ids", ())) != list(semantic.get("support_term_ids", ())):
        raise GremlinScalarAcquisitionError("observation support-term mismatch")
    _finite(float.fromhex(str(receipt.get("value_f64_hex"))), "value")
    for key in (
        "producer_id",
        "producer_version",
        "scale_id",
        "source_ref",
        "formula_contract_ref",
        "implementation_ref",
        "epistemic_status",
    ):
        _nonempty(receipt.get(key), key)
    if str(receipt.get("producer_classification", "")) not in PRODUCER_CLASSIFICATIONS:
        raise GremlinScalarAcquisitionError("invalid observation producer classification")
    source_class = str(receipt.get("source_classification", ""))
    if source_class not in SOURCE_CLASSIFICATIONS:
        raise GremlinScalarAcquisitionError("invalid observation source classification")
    _hash64(receipt.get("producer_contract_commitment"), "producer_contract_commitment")
    _hash64(receipt.get("input_commitment"), "input_commitment")
    if receipt.get("live_required") is True:
        if source_class != "LIVE_NOEMA_WITNESS":
            raise GremlinScalarAcquisitionError("live observation source mismatch")
        live_ref = _nonempty(receipt.get("live_surface_ref"), "live_surface_ref")
        if live_ref != LIVE_ROOT and not live_ref.startswith(LIVE_ROOT + "/"):
            raise GremlinScalarAcquisitionError("live observation surface mismatch")
    if receipt.get("execution_admitted") is not False or receipt.get("canon_allowed") is not False:
        raise GremlinScalarAcquisitionError("observation authority boundary violated")
    if receipt.get("status") != "SCALAR_OBSERVATION_RECORDED":
        raise GremlinScalarAcquisitionError("invalid observation status")

    supplied = _hash64(receipt.get("receipt_id"), "receipt_id")
    core = dict(receipt)
    core.pop("receipt_id", None)
    expected = hashlib.blake2b(RECEIPT_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    if supplied != expected:
        raise GremlinScalarAcquisitionError("observation receipt commitment mismatch")
    return True


def build_acquisition_bundle(receipts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    expected_roles = set(SEMANTIC_CONTRACTS)
    by_role: dict[str, Mapping[str, Any]] = {}
    for receipt in receipts:
        validate_observation_receipt(receipt)
        role = str(receipt["semantic_role"])
        if role in by_role:
            raise GremlinScalarAcquisitionError(f"conflicting duplicate scalar role: {role}")
        by_role[role] = receipt
    if set(by_role) != expected_roles:
        missing = sorted(expected_roles - set(by_role))
        extra = sorted(set(by_role) - expected_roles)
        raise GremlinScalarAcquisitionError(f"exact scalar role set required; missing={missing}, extra={extra}")

    ordered = []
    for role in sorted(by_role):
        receipt = by_role[role]
        ordered.append({
            "semantic_role": role,
            "canonical_term_id": receipt["canonical_term_id"],
            "receipt_id": receipt["receipt_id"],
            "value_f64_hex": receipt["value_f64_hex"],
            "scale_id": receipt["scale_id"],
            "source_classification": receipt["source_classification"],
            "source_ref": receipt["source_ref"],
            "epistemic_status": receipt["epistemic_status"],
        })

    core = {
        "schema": BUNDLE_SCHEMA,
        "observations": ordered,
        "role_count": len(ordered),
        "silent_scale_conversion_used": False,
        "conflict_averaging_used": False,
        "vector_bound": False,
        "t36_realization_present": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "KAKU_SCALAR_ACQUISITION_COMPLETE",
    }
    commitment = hashlib.blake2b(BUNDLE_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    return {**core, "acquisition_bundle_commitment": commitment}


def validate_acquisition_bundle(bundle: Mapping[str, Any]) -> bool:
    if bundle.get("schema") != BUNDLE_SCHEMA:
        raise GremlinScalarAcquisitionError("unsupported acquisition bundle schema")
    observations = bundle.get("observations")
    if not isinstance(observations, list) or len(observations) != len(SEMANTIC_CONTRACTS):
        raise GremlinScalarAcquisitionError("exact acquisition observation count required")
    roles = [str(v.get("semantic_role", "")) for v in observations]
    if roles != sorted(SEMANTIC_CONTRACTS):
        raise GremlinScalarAcquisitionError("acquisition observations must use canonical role ordering")
    if len(set(roles)) != len(roles):
        raise GremlinScalarAcquisitionError("duplicate acquisition role")
    for observation in observations:
        role = str(observation["semantic_role"])
        semantic = _semantic_contract(role)
        if observation.get("canonical_term_id") != semantic["canonical_term_id"]:
            raise GremlinScalarAcquisitionError("bundle semantic term mismatch")
        _hash64(observation.get("receipt_id"), "receipt_id")
        _finite(float.fromhex(str(observation.get("value_f64_hex"))), "value")
        for key in ("scale_id", "source_ref", "epistemic_status"):
            _nonempty(observation.get(key), key)
        if str(observation.get("source_classification", "")) not in SOURCE_CLASSIFICATIONS:
            raise GremlinScalarAcquisitionError("bundle source classification invalid")
    if bundle.get("role_count") != len(SEMANTIC_CONTRACTS):
        raise GremlinScalarAcquisitionError("bundle role count mismatch")
    if bundle.get("silent_scale_conversion_used") is not False:
        raise GremlinScalarAcquisitionError("silent scale conversion boundary violated")
    if bundle.get("conflict_averaging_used") is not False:
        raise GremlinScalarAcquisitionError("conflict averaging boundary violated")
    if bundle.get("vector_bound") is not False or bundle.get("t36_realization_present") is not False:
        raise GremlinScalarAcquisitionError("acquisition bundle crossed pre-vector boundary")
    if bundle.get("execution_admitted") is not False or bundle.get("canon_allowed") is not False:
        raise GremlinScalarAcquisitionError("acquisition authority boundary violated")
    if bundle.get("status") != "KAKU_SCALAR_ACQUISITION_COMPLETE":
        raise GremlinScalarAcquisitionError("invalid acquisition bundle status")

    supplied = _hash64(bundle.get("acquisition_bundle_commitment"), "acquisition_bundle_commitment")
    core = dict(bundle)
    core.pop("acquisition_bundle_commitment", None)
    expected = hashlib.blake2b(BUNDLE_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    if supplied != expected:
        raise GremlinScalarAcquisitionError("acquisition bundle commitment mismatch")
    return True


def build_kaku_scalar_packet_from_acquisition(
    *,
    acquisition_bundle: Mapping[str, Any],
    kaku_id: str,
    operator_kind: str,
    direction: str,
    polarity: Any,
    role: str,
    source_binding: str,
    target_binding: str,
    evidence_refs: Sequence[str] = (),
) -> dict[str, Any]:
    validate_acquisition_bundle(acquisition_bundle)
    observations = {item["semantic_role"]: item for item in acquisition_bundle["observations"]}

    def to_packet_observation(name: str) -> dict[str, Any]:
        item = observations[name]
        return {
            "value": float.fromhex(item["value_f64_hex"]),
            "scale_id": item["scale_id"],
            "source_ref": f"receipt:{item['receipt_id']}",
            "epistemic_status": item["epistemic_status"],
        }

    inherited_evidence = [f"receipt:{item['receipt_id']}" for item in acquisition_bundle["observations"]]
    inherited_evidence.append(f"acquisition:{acquisition_bundle['acquisition_bundle_commitment']}")
    inherited_evidence.extend(str(v) for v in evidence_refs)

    packet = build_kaku_scalar_packet(
        kaku_id=kaku_id,
        operator_kind=operator_kind,
        direction=direction,
        polarity=polarity,
        role=role,
        source_binding=source_binding,
        target_binding=target_binding,
        valuation=to_packet_observation("valuation"),
        affect=to_packet_observation("affect"),
        intention_alignment=to_packet_observation("intention_alignment"),
        epistemic_support=to_packet_observation("epistemic_support"),
        evidence_refs=inherited_evidence,
    )
    packet["scalar_acquisition_bundle_commitment"] = acquisition_bundle["acquisition_bundle_commitment"]
    packet["scalar_acquisition_status"] = "RECEIPT_BOUND"
    return packet
