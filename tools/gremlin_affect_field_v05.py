from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

AFFECT_RECEIPT_SCHEMA = "GREMLIN_RIFC_AFFECT_FIELD_RECEIPT_V0_5"
AFFECT_RECEIPT_DOMAIN = b"GREMLIN-RIFC-AFFECT-FIELD-RECEIPT/v0.5\x00"
KAKU_AFFECT_SCHEMA = "GREMLIN_KAKU_AFFECT_BINDING_V0_5"
KAKU_AFFECT_DOMAIN = b"GREMLIN-KAKU-AFFECT-BINDING/v0.5\x00"

DICTIONARY_REPOSITORY = "AdrianLipa90/The-Consciousness-Dictionary"
DICTIONARY_COMMIT = "b988113faf0cfd0c534dab4bb4a7b5cca41e40b9"
DETECTOR_PATH = "src/consciousness_dictionary/affect_detection.py"
DETECTOR_BLOB_SHA = "6771c2316c1b6b3157ae76c36f2d3000b916baaf"
VALIDATION_PATH = "provenance/AFFECT_DETECTION_V0_1_VALIDATION.json"
VALIDATION_BLOB_SHA = "cda747d3374d0ea96710af0c452a8781503c3a98"
METHOD = "transparent_lexical_surface_v1"

AFFECT_FIELDS = (
    "valence",
    "arousal",
    "urgency",
    "threat_relevance",
    "attachment_relevance",
    "reward_relevance",
)

AFFECT_BOUNDS = {
    "valence": (-1.0, 1.0),
    "arousal": (0.0, 1.0),
    "urgency": (0.0, 1.0),
    "threat_relevance": (0.0, 1.0),
    "attachment_relevance": (0.0, 1.0),
    "reward_relevance": (0.0, 1.0),
}


class AffectFieldError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(domain: bytes, value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    text = str(value)
    if not text:
        raise AffectFieldError(f"{name} must be non-empty")
    return text


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise AffectFieldError(f"{name} must be finite")
    return x


def _bounded(value: Any, lo: float, hi: float, name: str) -> float:
    x = _finite(value, name)
    if x < lo or x > hi:
        raise AffectFieldError(f"{name} outside [{lo},{hi}]")
    return x


def _hash64(value: Any, name: str) -> str:
    text = _nonempty(value, name)
    if len(text) != 64:
        raise AffectFieldError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise AffectFieldError(f"{name} must be hexadecimal") from exc
    return text


def _validate_upstream_estimate(estimate: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(estimate, Mapping):
        raise AffectFieldError("AffectEstimate payload must be a mapping")
    if estimate.get("method") != METHOD:
        raise AffectFieldError("unsupported affect inference method")

    for key in ("truth_authority", "semantic_authority", "diagnostic_authority", "modulation_authority"):
        if estimate.get(key) is not False:
            raise AffectFieldError(f"upstream affect authority boundary violated: {key}")

    affect = estimate.get("affect")
    if not isinstance(affect, Mapping) or set(affect) != set(AFFECT_FIELDS):
        raise AffectFieldError("exact six-dimensional RIFC affect field required")
    normalized_affect: dict[str, float] = {}
    for name in AFFECT_FIELDS:
        lo, hi = AFFECT_BOUNDS[name]
        normalized_affect[name] = _bounded(affect[name], lo, hi, name)

    confidence = _bounded(estimate.get("confidence"), 0.0, 1.0, "confidence")
    text_sha256 = _hash64(estimate.get("text_sha256"), "text_sha256")

    labels = estimate.get("surface_labels")
    if not isinstance(labels, list) or not labels or any(not str(v) for v in labels):
        raise AffectFieldError("surface_labels must be a non-empty list")
    if confidence < 0.18 and labels != ["insufficient-evidence"]:
        raise AffectFieldError("low-confidence affect must preserve insufficient-evidence state")

    evidence = estimate.get("evidence")
    if not isinstance(evidence, list):
        raise AffectFieldError("affect evidence must be a list")
    normalized_evidence: list[dict[str, Any]] = []
    for index, item in enumerate(evidence):
        if not isinstance(item, Mapping):
            raise AffectFieldError(f"evidence[{index}] must be a mapping")
        cue = str(item.get("cue", ""))
        if not cue:
            raise AffectFieldError(f"evidence[{index}].cue must be non-empty")
        start = int(item.get("start"))
        end = int(item.get("end"))
        if start < 0 or end < 0 or end < start:
            raise AffectFieldError(f"evidence[{index}] span invalid")
        kind = _nonempty(item.get("kind"), f"evidence[{index}].kind")
        contributions = item.get("contributions")
        if not isinstance(contributions, Mapping) or not contributions:
            raise AffectFieldError(f"evidence[{index}].contributions must be non-empty")
        normalized_contrib = {}
        for key, value in sorted(contributions.items()):
            if key not in {"valence", "arousal", "urgency", "threat", "attachment", "reward"}:
                raise AffectFieldError(f"unsupported affect evidence contribution: {key}")
            normalized_contrib[str(key)] = _finite(value, f"evidence[{index}].{key}")
        normalized_evidence.append({
            "cue_sha256": _sha256_text(cue),
            "start": start,
            "end": end,
            "kind": kind,
            "contributions": normalized_contrib,
        })

    if confidence == 0.0 and evidence:
        raise AffectFieldError("zero-confidence affect cannot carry positive cue evidence")

    return {
        "affect": normalized_affect,
        "confidence": confidence,
        "surface_labels": [str(v) for v in labels],
        "evidence": normalized_evidence,
        "text_sha256": text_sha256,
    }


def build_rifc_affect_field_receipt_v05(estimate: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _validate_upstream_estimate(estimate)
    upstream_commitment = hashlib.sha256(_canonical(estimate)).hexdigest()
    core = {
        "schema": AFFECT_RECEIPT_SCHEMA,
        "semantic_term_id": "CLX2-AFFECT-002",
        "formalism": "F-AFFECT-FIELD",
        "affect_field": {
            name: {
                "value_f64_hex": normalized["affect"][name].hex(),
                "scale_id": "SIGNED_UNIT[-1,1]/v0.5" if name == "valence" else "UNIT_INTERVAL[0,1]/v0.5",
            }
            for name in AFFECT_FIELDS
        },
        "inference_confidence": {
            "value_f64_hex": normalized["confidence"].hex(),
            "scale_id": "UNIT_INTERVAL[0,1]/v0.5",
        },
        "surface_labels": normalized["surface_labels"],
        "evidence": normalized["evidence"],
        "text_sha256": normalized["text_sha256"],
        "upstream_estimate_sha256": upstream_commitment,
        "producer": {
            "repository": DICTIONARY_REPOSITORY,
            "commit": DICTIONARY_COMMIT,
            "path": DETECTOR_PATH,
            "blob_sha": DETECTOR_BLOB_SHA,
            "method": METHOD,
            "validation_path": VALIDATION_PATH,
            "validation_blob_sha": VALIDATION_BLOB_SHA,
            "producer_class": "DETERMINISTIC_INPUT_CONDITIONED_PRODUCER_CANDIDATE",
        },
        "privacy": {
            "raw_text_persisted": False,
            "raw_cues_persisted": False,
            "cue_hashes_persisted": True,
        },
        "compatibility": {
            "ciel_vad_v0_4_overlap": ["valence", "arousal"],
            "ciel_vad_v0_4_dominance_semantic_mapping": "UNRESOLVED",
            "ciel_vad_v0_4_confidence_role": "INFERENCE_CONFIDENCE_COMPATIBILITY_ONLY",
        },
        "phase36_embedding_present": False,
        "collapsed_affect_scalar_present": False,
        "truth_authority": False,
        "semantic_authority": False,
        "diagnostic_authority": False,
        "modulation_authority": False,
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "RIFC_AFFECT_FIELD_RECEIPTED",
    }
    return {**core, "affect_field_commitment": _seal(AFFECT_RECEIPT_DOMAIN, core)}


def validate_rifc_affect_field_receipt_v05(receipt: Mapping[str, Any]) -> bool:
    if receipt.get("schema") != AFFECT_RECEIPT_SCHEMA:
        raise AffectFieldError("unsupported RIFC affect receipt schema")
    if receipt.get("semantic_term_id") != "CLX2-AFFECT-002" or receipt.get("formalism") != "F-AFFECT-FIELD":
        raise AffectFieldError("RIFC affect semantic/formal binding mismatch")

    field = receipt.get("affect_field")
    if not isinstance(field, Mapping) or set(field) != set(AFFECT_FIELDS):
        raise AffectFieldError("exact six-dimensional RIFC affect field required")
    for name in AFFECT_FIELDS:
        item = field[name]
        if not isinstance(item, Mapping):
            raise AffectFieldError(f"affect_field.{name} must be a mapping")
        value = _finite(float.fromhex(str(item.get("value_f64_hex"))), name)
        lo, hi = AFFECT_BOUNDS[name]
        if value < lo or value > hi:
            raise AffectFieldError(f"affect field {name} outside declared domain")
        expected_scale = "SIGNED_UNIT[-1,1]/v0.5" if name == "valence" else "UNIT_INTERVAL[0,1]/v0.5"
        if item.get("scale_id") != expected_scale:
            raise AffectFieldError(f"affect field scale mismatch: {name}")

    confidence = receipt.get("inference_confidence")
    if not isinstance(confidence, Mapping):
        raise AffectFieldError("inference confidence missing")
    q = _finite(float.fromhex(str(confidence.get("value_f64_hex"))), "inference_confidence")
    if q < 0.0 or q > 1.0 or confidence.get("scale_id") != "UNIT_INTERVAL[0,1]/v0.5":
        raise AffectFieldError("inference confidence contract mismatch")

    labels = receipt.get("surface_labels")
    if not isinstance(labels, list) or not labels:
        raise AffectFieldError("surface labels missing")
    if q < 0.18 and labels != ["insufficient-evidence"]:
        raise AffectFieldError("low-confidence affect must remain insufficient-evidence")

    evidence = receipt.get("evidence")
    if not isinstance(evidence, list):
        raise AffectFieldError("affect evidence missing")
    for index, item in enumerate(evidence):
        if not isinstance(item, Mapping):
            raise AffectFieldError(f"evidence[{index}] malformed")
        _hash64(item.get("cue_sha256"), f"evidence[{index}].cue_sha256")
        start, end = int(item.get("start")), int(item.get("end"))
        if start < 0 or end < start:
            raise AffectFieldError(f"evidence[{index}] span invalid")
        _nonempty(item.get("kind"), f"evidence[{index}].kind")
        contrib = item.get("contributions")
        if not isinstance(contrib, Mapping) or not contrib:
            raise AffectFieldError(f"evidence[{index}] contribution metadata missing")
        for key, value in contrib.items():
            if key not in {"valence", "arousal", "urgency", "threat", "attachment", "reward"}:
                raise AffectFieldError(f"unsupported evidence dimension: {key}")
            _finite(value, f"evidence[{index}].{key}")

    _hash64(receipt.get("text_sha256"), "text_sha256")
    _hash64(receipt.get("upstream_estimate_sha256"), "upstream_estimate_sha256")

    producer = receipt.get("producer")
    expected_producer = {
        "repository": DICTIONARY_REPOSITORY,
        "commit": DICTIONARY_COMMIT,
        "path": DETECTOR_PATH,
        "blob_sha": DETECTOR_BLOB_SHA,
        "method": METHOD,
        "validation_path": VALIDATION_PATH,
        "validation_blob_sha": VALIDATION_BLOB_SHA,
        "producer_class": "DETERMINISTIC_INPUT_CONDITIONED_PRODUCER_CANDIDATE",
    }
    if producer != expected_producer:
        raise AffectFieldError("affect producer pin mismatch")

    privacy = receipt.get("privacy")
    if privacy != {"raw_text_persisted": False, "raw_cues_persisted": False, "cue_hashes_persisted": True}:
        raise AffectFieldError("affect privacy contract mismatch")

    compatibility = receipt.get("compatibility")
    if not isinstance(compatibility, Mapping):
        raise AffectFieldError("CIEL compatibility metadata missing")
    if compatibility.get("ciel_vad_v0_4_overlap") != ["valence", "arousal"]:
        raise AffectFieldError("CIEL VAD overlap mismatch")
    if compatibility.get("ciel_vad_v0_4_dominance_semantic_mapping") != "UNRESOLVED":
        raise AffectFieldError("CIEL dominance mapping must remain unresolved")

    for key in (
        "phase36_embedding_present",
        "collapsed_affect_scalar_present",
        "truth_authority",
        "semantic_authority",
        "diagnostic_authority",
        "modulation_authority",
        "production_runtime_write",
        "execution_admitted",
        "canon_allowed",
    ):
        if receipt.get(key) is not False:
            raise AffectFieldError(f"affect boundary violated: {key}")
    if receipt.get("status") != "RIFC_AFFECT_FIELD_RECEIPTED":
        raise AffectFieldError("wrong affect field receipt status")

    supplied = _hash64(receipt.get("affect_field_commitment"), "affect_field_commitment")
    core = dict(receipt)
    core.pop("affect_field_commitment", None)
    if supplied != _seal(AFFECT_RECEIPT_DOMAIN, core):
        raise AffectFieldError("affect field commitment mismatch")
    return True


def build_kaku_affect_binding_v05(*, kaku_id: str, affect_receipt: Mapping[str, Any]) -> dict[str, Any]:
    validate_rifc_affect_field_receipt_v05(affect_receipt)
    core = {
        "schema": KAKU_AFFECT_SCHEMA,
        "kaku_id": _nonempty(kaku_id, "kaku_id"),
        "affect_field_commitment": _hash64(affect_receipt.get("affect_field_commitment"), "affect_field_commitment"),
        "affect_representation": "RIFC_AFFECT_FIELD_6_SCALARS_PLUS_CONFIDENCE",
        "remaining_kaku_scalar_families": ["valuation", "intention_alignment", "epistemic_support"],
        "scalar_envelope_complete": False,
        "radical_admission_required": True,
        "vector_synthesis_allowed": False,
        "vector_bound": False,
        "t36_realization_present": False,
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "KAKU_AFFECT_BOUND_SCALAR_ENVELOPE_OPEN",
    }
    return {**core, "kaku_affect_binding_commitment": _seal(KAKU_AFFECT_DOMAIN, core)}


def validate_kaku_affect_binding_v05(binding: Mapping[str, Any]) -> bool:
    if binding.get("schema") != KAKU_AFFECT_SCHEMA:
        raise AffectFieldError("unsupported KAKU affect binding schema")
    _nonempty(binding.get("kaku_id"), "kaku_id")
    _hash64(binding.get("affect_field_commitment"), "affect_field_commitment")
    if binding.get("affect_representation") != "RIFC_AFFECT_FIELD_6_SCALARS_PLUS_CONFIDENCE":
        raise AffectFieldError("KAKU affect representation mismatch")
    if binding.get("remaining_kaku_scalar_families") != ["valuation", "intention_alignment", "epistemic_support"]:
        raise AffectFieldError("KAKU remaining scalar frontier mismatch")
    if binding.get("scalar_envelope_complete") is not False or binding.get("radical_admission_required") is not True:
        raise AffectFieldError("KAKU affect binding scalar frontier mismatch")
    for key in (
        "vector_synthesis_allowed",
        "vector_bound",
        "t36_realization_present",
        "production_runtime_write",
        "execution_admitted",
        "canon_allowed",
    ):
        if binding.get(key) is not False:
            raise AffectFieldError(f"KAKU affect binding boundary violated: {key}")
    if binding.get("status") != "KAKU_AFFECT_BOUND_SCALAR_ENVELOPE_OPEN":
        raise AffectFieldError("wrong KAKU affect binding status")
    supplied = _hash64(binding.get("kaku_affect_binding_commitment"), "kaku_affect_binding_commitment")
    core = dict(binding)
    core.pop("kaku_affect_binding_commitment", None)
    if supplied != _seal(KAKU_AFFECT_DOMAIN, core):
        raise AffectFieldError("KAKU affect binding commitment mismatch")
    return True
