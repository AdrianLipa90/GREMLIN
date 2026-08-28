from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

from tools.gremlin_kaku_radical_scalar_plane_v01 import PNCS_KAKU_CLASSIFICATION
from tools.gremlin_scalar_acquisition_v02 import validate_scalar_observation_receipt

AFFECT_SCHEMA = "GREMLIN_AFFECT_VAD_FACETS_V0_4"
AFFECT_DOMAIN = b"GREMLIN-AFFECT-VAD-FACETS/v0.4\x00"
TARGET_SCHEMA = "GREMLIN_INTENTION_TARGET_PHASE_V0_4"
TARGET_DOMAIN = b"GREMLIN-INTENTION-TARGET-PHASE/v0.4\x00"
ALIGNMENT_SCHEMA = "GREMLIN_INTENTION_ALIGNMENT_CANDIDATE_V0_4"
ALIGNMENT_DOMAIN = b"GREMLIN-INTENTION-ALIGNMENT-CANDIDATE/v0.4\x00"
KAKU_FACET_SCHEMA = "GREMLIN_KAKU_SCALAR_FACET_ENVELOPE_V0_4"
KAKU_FACET_DOMAIN = b"GREMLIN-KAKU-SCALAR-FACET-ENVELOPE/v0.4\x00"

CIEL_DONOR_REPOSITORY = "AdrianLipa90/CIEL-Omega-ApokalypOS"
CIEL_DONOR_COMMIT = "aa0da54ef29a1f80dd0390427935342225388950"
CIEL_AFFECT_PATH = "src/CIEL_OMEGA_COMPLETE_SYSTEM/ciel_omega/memory/affective_lexicon.py"
CIEL_INTENTION_LIVE_PATH = "phasenav/CIELINGO_PHASENAV_CONCEPT_PHASES.noema.jsonl"
TAU = 2.0 * math.pi


class KakuScalarFacetError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(domain: bytes, core: Mapping[str, Any]) -> str:
    return hashlib.blake2b(domain + _canonical(core), digest_size=32).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    text = str(value)
    if not text:
        raise KakuScalarFacetError(f"{name} must be non-empty")
    return text


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise KakuScalarFacetError(f"{name} must be finite")
    return x


def _bounded(value: Any, lo: float, hi: float, name: str) -> float:
    x = _finite(value, name)
    if x < lo or x > hi:
        raise KakuScalarFacetError(f"{name} outside [{lo}, {hi}]")
    return x


def _hash64(value: Any, name: str) -> str:
    text = _nonempty(value, name)
    if len(text) != 64:
        raise KakuScalarFacetError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise KakuScalarFacetError(f"{name} must be hexadecimal") from exc
    return text


def _phase_0_tau(value: Any, name: str) -> float:
    return _finite(value, name) % TAU


def _wrap_pi(value: float) -> float:
    return (value + math.pi) % TAU - math.pi


def build_affect_vad_facets_v04(
    *,
    term: str,
    valence: Any,
    arousal: Any,
    dominance: Any,
    confidence: Any,
    source_ref: str,
    epistemic_status: str,
) -> dict[str, Any]:
    """Build explicit CIEL-VAD scalar facets without collapsing them to one affect score."""

    v = _bounded(valence, -1.0, 1.0, "valence")
    a = _bounded(arousal, 0.0, 1.0, "arousal")
    d = _bounded(dominance, -1.0, 1.0, "dominance")
    q = _bounded(confidence, 0.0, 1.0, "confidence")

    phi_v = math.pi * (v + 1.0)
    phi_a = TAU * a
    phi_d = math.pi * (d + 1.0)
    sx = (math.cos(phi_v) + math.cos(phi_a) + math.cos(phi_d)) / 3.0
    sy = (math.sin(phi_v) + math.sin(phi_a) + math.sin(phi_d)) / 3.0
    resultant = math.hypot(sx, sy)
    phase_resolved = resultant > 1e-15
    phase = math.atan2(sy, sx) % TAU if phase_resolved else None

    core = {
        "schema": AFFECT_SCHEMA,
        "term": _nonempty(term, "term"),
        "semantic_term_id": "CLX2-AFFECT-002",
        "facets": {
            "valence": {"value_f64_hex": v.hex(), "scale_id": "CIEL_VAD_VALENCE[-1,1]/v0.4"},
            "arousal": {"value_f64_hex": a.hex(), "scale_id": "CIEL_VAD_AROUSAL[0,1]/v0.4"},
            "dominance": {"value_f64_hex": d.hex(), "scale_id": "CIEL_VAD_DOMINANCE[-1,1]/v0.4"},
            "confidence": {"value_f64_hex": q.hex(), "scale_id": "CIEL_VAD_CONFIDENCE[0,1]/v0.4"},
        },
        "derived_phase_candidate": {
            "phi_valence_rad_f64_hex": phi_v.hex(),
            "phi_arousal_rad_f64_hex": phi_a.hex(),
            "phi_dominance_rad_f64_hex": phi_d.hex(),
            "resultant_R_f64_hex": resultant.hex(),
            "phase_resolved": phase_resolved,
            "affective_phase_rad_f64_hex": phase.hex() if phase is not None else None,
            "formula_id": "CIEL_VAD_CIRCULAR_MEAN/v0.4",
            "status": "MODEL_REALIZATION_CANDIDATE",
        },
        "source_ref": _nonempty(source_ref, "source_ref"),
        "epistemic_status": _nonempty(epistemic_status, "epistemic_status"),
        "model_donor": {
            "repository": CIEL_DONOR_REPOSITORY,
            "commit": CIEL_DONOR_COMMIT,
            "path": CIEL_AFFECT_PATH,
            "role": "SCALE_AND_MODEL_DONOR",
        },
        "collapsed_affect_scalar_present": False,
        "vector_bound": False,
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "AFFECT_FACETS_BOUND",
    }
    return {**core, "affect_facets_commitment": _seal(AFFECT_DOMAIN, core)}


def validate_affect_vad_facets_v04(packet: Mapping[str, Any]) -> bool:
    if packet.get("schema") != AFFECT_SCHEMA:
        raise KakuScalarFacetError("unsupported affect facet schema")
    if packet.get("semantic_term_id") != "CLX2-AFFECT-002":
        raise KakuScalarFacetError("affect semantic term binding mismatch")
    _nonempty(packet.get("term"), "term")
    _nonempty(packet.get("source_ref"), "source_ref")
    _nonempty(packet.get("epistemic_status"), "epistemic_status")

    facets = packet.get("facets")
    if not isinstance(facets, Mapping) or set(facets) != {"valence", "arousal", "dominance", "confidence"}:
        raise KakuScalarFacetError("exact VAD+confidence facet set required")
    bounds = {
        "valence": (-1.0, 1.0),
        "arousal": (0.0, 1.0),
        "dominance": (-1.0, 1.0),
        "confidence": (0.0, 1.0),
    }
    for name, (lo, hi) in bounds.items():
        value = _finite(float.fromhex(str(facets[name].get("value_f64_hex"))), name)
        if value < lo or value > hi:
            raise KakuScalarFacetError(f"{name} outside declared facet domain")
        _nonempty(facets[name].get("scale_id"), f"facets.{name}.scale_id")

    donor = packet.get("model_donor")
    if not isinstance(donor, Mapping):
        raise KakuScalarFacetError("affect model donor binding missing")
    expected_donor = {
        "repository": CIEL_DONOR_REPOSITORY,
        "commit": CIEL_DONOR_COMMIT,
        "path": CIEL_AFFECT_PATH,
        "role": "SCALE_AND_MODEL_DONOR",
    }
    if dict(donor) != expected_donor:
        raise KakuScalarFacetError("affect model donor binding mismatch")

    derived = packet.get("derived_phase_candidate")
    if not isinstance(derived, Mapping) or derived.get("status") != "MODEL_REALIZATION_CANDIDATE":
        raise KakuScalarFacetError("affect derived-phase candidate metadata missing")
    if derived.get("formula_id") != "CIEL_VAD_CIRCULAR_MEAN/v0.4":
        raise KakuScalarFacetError("affect phase formula mismatch")
    resultant = _finite(float.fromhex(str(derived.get("resultant_R_f64_hex"))), "resultant_R")
    if resultant < 0.0 or resultant > 1.0 + 1e-15:
        raise KakuScalarFacetError("affect phase resultant outside [0,1]")
    phase_resolved = derived.get("phase_resolved") is True
    phase_hex = derived.get("affective_phase_rad_f64_hex")
    if phase_resolved:
        phase = _finite(float.fromhex(str(phase_hex)), "affective_phase")
        if phase < 0.0 or phase >= TAU:
            raise KakuScalarFacetError("affective phase outside [0,2pi)")
    elif phase_hex is not None:
        raise KakuScalarFacetError("unresolved affective phase must remain null")

    if packet.get("collapsed_affect_scalar_present") is not False or packet.get("vector_bound") is not False:
        raise KakuScalarFacetError("affect facets cannot be silently collapsed or vector-bound")
    if packet.get("production_runtime_write") is not False:
        raise KakuScalarFacetError("affect facets cannot grant runtime write")
    if packet.get("execution_admitted") is not False or packet.get("canon_allowed") is not False:
        raise KakuScalarFacetError("affect facet authority boundary violated")
    if packet.get("status") != "AFFECT_FACETS_BOUND":
        raise KakuScalarFacetError("wrong affect facet status")

    supplied = _hash64(packet.get("affect_facets_commitment"), "affect_facets_commitment")
    core = dict(packet)
    core.pop("affect_facets_commitment", None)
    if supplied != _seal(AFFECT_DOMAIN, core):
        raise KakuScalarFacetError("affect facet commitment mismatch")
    return True


def build_intention_target_phase_v04(
    *,
    target_id: str,
    target_phase_rad: Any,
    source_ref: str,
    epistemic_status: str,
) -> dict[str, Any]:
    phase = _phase_0_tau(target_phase_rad, "target_phase_rad")
    core = {
        "schema": TARGET_SCHEMA,
        "target_id": _nonempty(target_id, "target_id"),
        "semantic_term_id": "CLX2-AGENCY-003",
        "target_phase_rad_f64_hex": phase.hex(),
        "scale_id": "RADIAN_PHASE[0,2pi)/v0.4",
        "source_ref": _nonempty(source_ref, "source_ref"),
        "epistemic_status": _nonempty(epistemic_status, "epistemic_status"),
        "status": "TARGET_PHASE_DECLARED",
        "vector_bound": False,
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
    return {**core, "target_phase_commitment": _seal(TARGET_DOMAIN, core)}


def validate_intention_target_phase_v04(target: Mapping[str, Any]) -> bool:
    if target.get("schema") != TARGET_SCHEMA:
        raise KakuScalarFacetError("unsupported intention target schema")
    if target.get("semantic_term_id") != "CLX2-AGENCY-003":
        raise KakuScalarFacetError("target semantic term binding mismatch")
    _nonempty(target.get("target_id"), "target_id")
    _nonempty(target.get("source_ref"), "source_ref")
    _nonempty(target.get("epistemic_status"), "epistemic_status")
    phase = _finite(float.fromhex(str(target.get("target_phase_rad_f64_hex"))), "target_phase")
    if phase < 0.0 or phase >= TAU:
        raise KakuScalarFacetError("target phase outside [0,2pi)")
    if target.get("status") != "TARGET_PHASE_DECLARED":
        raise KakuScalarFacetError("wrong target phase status")
    if target.get("vector_bound") is not False:
        raise KakuScalarFacetError("target phase must remain pre-vector")
    if target.get("production_runtime_write") is not False:
        raise KakuScalarFacetError("target phase cannot grant runtime write")
    if target.get("execution_admitted") is not False or target.get("canon_allowed") is not False:
        raise KakuScalarFacetError("target phase authority boundary violated")
    supplied = _hash64(target.get("target_phase_commitment"), "target_phase_commitment")
    core = dict(target)
    core.pop("target_phase_commitment", None)
    if supplied != _seal(TARGET_DOMAIN, core):
        raise KakuScalarFacetError("target phase commitment mismatch")
    return True


def validate_live_ciel_intention_phase_anchor_v04(receipt: Mapping[str, Any]) -> bool:
    validate_scalar_observation_receipt(receipt)
    if receipt.get("observation_name") != "intention_phase_anchor":
        raise KakuScalarFacetError("intention phase anchor observation name mismatch")
    if receipt.get("scale_id") != "RADIAN_PHASE/v0.4":
        raise KakuScalarFacetError("intention phase anchor scale mismatch")
    producer = receipt.get("producer")
    if not isinstance(producer, Mapping) or producer.get("producer_kind") != "CIEL_NOEMA_JSONL_FIELD":
        raise KakuScalarFacetError("intention phase anchor requires CIEL/NOEMA JSONL producer")
    if producer.get("source_path") != CIEL_INTENTION_LIVE_PATH:
        raise KakuScalarFacetError("intention phase anchor source path mismatch")
    extraction = producer.get("extraction")
    if not isinstance(extraction, Mapping):
        raise KakuScalarFacetError("intention phase anchor extraction metadata missing")
    expected = {
        "selector_key": "name",
        "selector_value": "Intention",
        "field": "geometric_phase_rad",
    }
    for key, value in expected.items():
        if extraction.get(key) != value:
            raise KakuScalarFacetError(f"intention phase anchor extraction mismatch: {key}")
    phase = _finite(float.fromhex(str(receipt.get("value_f64_hex"))), "intention_phase_anchor")
    if phase < -TAU or phase > TAU * 2.0:
        raise KakuScalarFacetError("intention phase anchor outside conservative radian domain")
    return True


def build_intention_alignment_candidate_v04(
    *,
    phase_anchor_receipt: Mapping[str, Any],
    target_phase: Mapping[str, Any],
) -> dict[str, Any]:
    validate_live_ciel_intention_phase_anchor_v04(phase_anchor_receipt)
    validate_intention_target_phase_v04(target_phase)

    anchor = _phase_0_tau(float.fromhex(str(phase_anchor_receipt["value_f64_hex"])), "anchor_phase")
    target = float.fromhex(str(target_phase["target_phase_rad_f64_hex"]))
    delta = _wrap_pi(anchor - target)
    signed = math.cos(delta)
    lock = 0.5 * (1.0 + signed)

    core = {
        "schema": ALIGNMENT_SCHEMA,
        "semantic_term_id": "CLX2-AGENCY-001",
        "anchor_receipt_commitment": _hash64(
            phase_anchor_receipt.get("observation_receipt_commitment"),
            "anchor_receipt_commitment",
        ),
        "target_phase_commitment": _hash64(
            target_phase.get("target_phase_commitment"),
            "target_phase_commitment",
        ),
        "anchor_phase_rad_f64_hex": anchor.hex(),
        "target_phase_rad_f64_hex": target.hex(),
        "wrapped_delta_rad_f64_hex": delta.hex(),
        "signed_cosine_alignment_f64_hex": signed.hex(),
        "lock_alignment_01_f64_hex": lock.hex(),
        "formula": "C(delta)=(1+cos(delta))/2=cos^2(delta/2)",
        "formula_id": "QHTRI_PHASE_LOCK_ALIGNMENT/v0.4",
        "epistemic_status": "MODEL_REALIZATION_CANDIDATE",
        "vector_bound": False,
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "INTENTION_ALIGNMENT_CANDIDATE",
    }
    return {**core, "intention_alignment_commitment": _seal(ALIGNMENT_DOMAIN, core)}


def validate_intention_alignment_candidate_v04(record: Mapping[str, Any]) -> bool:
    if record.get("schema") != ALIGNMENT_SCHEMA:
        raise KakuScalarFacetError("unsupported intention alignment schema")
    if record.get("semantic_term_id") != "CLX2-AGENCY-001":
        raise KakuScalarFacetError("intention semantic term binding mismatch")
    _hash64(record.get("anchor_receipt_commitment"), "anchor_receipt_commitment")
    _hash64(record.get("target_phase_commitment"), "target_phase_commitment")
    delta = _finite(float.fromhex(str(record.get("wrapped_delta_rad_f64_hex"))), "wrapped_delta")
    signed = _finite(float.fromhex(str(record.get("signed_cosine_alignment_f64_hex"))), "signed_alignment")
    lock = _finite(float.fromhex(str(record.get("lock_alignment_01_f64_hex"))), "lock_alignment")
    if delta < -math.pi or delta >= math.pi:
        raise KakuScalarFacetError("wrapped intention delta outside [-pi,pi)")
    if signed < -1.0 - 1e-15 or signed > 1.0 + 1e-15:
        raise KakuScalarFacetError("signed intention alignment outside [-1,1]")
    if lock < 0.0 or lock > 1.0:
        raise KakuScalarFacetError("intention lock alignment outside [0,1]")
    if abs(lock - 0.5 * (1.0 + signed)) > 1e-15:
        raise KakuScalarFacetError("intention alignment algebra mismatch")
    if record.get("formula_id") != "QHTRI_PHASE_LOCK_ALIGNMENT/v0.4":
        raise KakuScalarFacetError("intention alignment formula mismatch")
    if record.get("epistemic_status") != "MODEL_REALIZATION_CANDIDATE":
        raise KakuScalarFacetError("intention alignment epistemic status mismatch")
    if record.get("vector_bound") is not False:
        raise KakuScalarFacetError("intention alignment must remain pre-vector")
    if record.get("production_runtime_write") is not False:
        raise KakuScalarFacetError("intention alignment cannot grant runtime write")
    if record.get("execution_admitted") is not False or record.get("canon_allowed") is not False:
        raise KakuScalarFacetError("intention alignment authority boundary violated")
    if record.get("status") != "INTENTION_ALIGNMENT_CANDIDATE":
        raise KakuScalarFacetError("wrong intention alignment status")
    supplied = _hash64(record.get("intention_alignment_commitment"), "intention_alignment_commitment")
    core = dict(record)
    core.pop("intention_alignment_commitment", None)
    if supplied != _seal(ALIGNMENT_DOMAIN, core):
        raise KakuScalarFacetError("intention alignment commitment mismatch")
    return True


def _require_standard_scalar_receipt(receipt: Mapping[str, Any], observation_name: str) -> str:
    validate_scalar_observation_receipt(receipt)
    if receipt.get("observation_name") != observation_name:
        raise KakuScalarFacetError(f"expected {observation_name} observation receipt")
    return _hash64(receipt.get("observation_receipt_commitment"), f"{observation_name}.commitment")


def build_kaku_scalar_facet_envelope_v04(
    *,
    kaku_id: str,
    operator_kind: str,
    direction: str,
    polarity: Any,
    role: str,
    source_binding: str,
    target_binding: str,
    valuation_receipt: Mapping[str, Any],
    affect_facets: Mapping[str, Any],
    intention_alignment: Mapping[str, Any],
    epistemic_support_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    operator = _nonempty(operator_kind, "operator_kind").upper()
    if operator not in PNCS_KAKU_CLASSIFICATION:
        raise KakuScalarFacetError("operator_kind outside bounded PNCS/PNV KAKU set")

    valuation_commitment = _require_standard_scalar_receipt(valuation_receipt, "valuation")
    epistemic_commitment = _require_standard_scalar_receipt(epistemic_support_receipt, "epistemic_support")
    validate_affect_vad_facets_v04(affect_facets)
    validate_intention_alignment_candidate_v04(intention_alignment)

    core = {
        "schema": KAKU_FACET_SCHEMA,
        "kaku_id": _nonempty(kaku_id, "kaku_id"),
        "operator_kind": operator,
        "operator_classification": PNCS_KAKU_CLASSIFICATION[operator],
        "direction": _nonempty(direction, "direction"),
        "polarity_f64_hex": _finite(polarity, "polarity").hex(),
        "role": _nonempty(role, "role"),
        "source_binding": _nonempty(source_binding, "source_binding"),
        "target_binding": _nonempty(target_binding, "target_binding"),
        "scalar_bindings": {
            "valuation_receipt_commitment": valuation_commitment,
            "affect_facets_commitment": _hash64(
                affect_facets.get("affect_facets_commitment"), "affect_facets_commitment"
            ),
            "intention_alignment_commitment": _hash64(
                intention_alignment.get("intention_alignment_commitment"),
                "intention_alignment_commitment",
            ),
            "epistemic_support_receipt_commitment": epistemic_commitment,
        },
        "affect_representation": "VAD_PLUS_CONFIDENCE_FACETS",
        "scalar_facets_complete": True,
        "radical_admission_required": True,
        "vector_synthesis_allowed": False,
        "vector_bound": False,
        "t36_realization_present": False,
        "semantic_mass_present": False,
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "KAKU_SCALAR_FACETS_COMPLETE",
    }
    return {**core, "kaku_scalar_facet_commitment": _seal(KAKU_FACET_DOMAIN, core)}


def validate_kaku_scalar_facet_envelope_v04(record: Mapping[str, Any]) -> bool:
    if record.get("schema") != KAKU_FACET_SCHEMA:
        raise KakuScalarFacetError("unsupported KAKU scalar facet envelope schema")
    operator = str(record.get("operator_kind", ""))
    if operator not in PNCS_KAKU_CLASSIFICATION:
        raise KakuScalarFacetError("invalid KAKU operator kind")
    if record.get("operator_classification") != PNCS_KAKU_CLASSIFICATION[operator]:
        raise KakuScalarFacetError("KAKU operator classification mismatch")
    for key in ("kaku_id", "direction", "role", "source_binding", "target_binding"):
        _nonempty(record.get(key), key)
    _finite(float.fromhex(str(record.get("polarity_f64_hex"))), "polarity")

    bindings = record.get("scalar_bindings")
    expected_keys = {
        "valuation_receipt_commitment",
        "affect_facets_commitment",
        "intention_alignment_commitment",
        "epistemic_support_receipt_commitment",
    }
    if not isinstance(bindings, Mapping) or set(bindings) != expected_keys:
        raise KakuScalarFacetError("exact KAKU scalar facet binding set required")
    for key in expected_keys:
        _hash64(bindings.get(key), f"scalar_bindings.{key}")

    if record.get("affect_representation") != "VAD_PLUS_CONFIDENCE_FACETS":
        raise KakuScalarFacetError("KAKU affect facet representation mismatch")
    if record.get("scalar_facets_complete") is not True:
        raise KakuScalarFacetError("KAKU scalar facets must be complete")
    if record.get("radical_admission_required") is not True:
        raise KakuScalarFacetError("KAKU facet envelope must require Radical admission")
    if record.get("vector_synthesis_allowed") is not False or record.get("vector_bound") is not False:
        raise KakuScalarFacetError("KAKU facet envelope cannot directly open vector synthesis")
    if record.get("t36_realization_present") is not False or record.get("semantic_mass_present") is not False:
        raise KakuScalarFacetError("KAKU facet envelope cannot contain post-realization state")
    if record.get("production_runtime_write") is not False:
        raise KakuScalarFacetError("KAKU facet envelope cannot grant runtime write")
    if record.get("execution_admitted") is not False or record.get("canon_allowed") is not False:
        raise KakuScalarFacetError("KAKU facet envelope authority boundary violated")
    if record.get("status") != "KAKU_SCALAR_FACETS_COMPLETE":
        raise KakuScalarFacetError("wrong KAKU scalar facet status")

    supplied = _hash64(record.get("kaku_scalar_facet_commitment"), "kaku_scalar_facet_commitment")
    core = dict(record)
    core.pop("kaku_scalar_facet_commitment", None)
    if supplied != _seal(KAKU_FACET_DOMAIN, core):
        raise KakuScalarFacetError("KAKU scalar facet commitment mismatch")
    return True
