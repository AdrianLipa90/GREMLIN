from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any, Iterable, Mapping, Sequence

from gremlin_mcp.semantic_evidence import verify_classification

SCHEMA = "GREMLIN_CLAIM_PROPOSITION_V0_1"
VERSION = "0.1.1"

AFFIRM = "AFFIRM"
NEGATE = "NEGATE"
_ALLOWED_POLARITIES = {AFFIRM, NEGATE}

ASSERTED = "ASSERTED"
NECESSARY = "NECESSARY"
POSSIBLE = "POSSIBLE"
CONDITIONAL = "CONDITIONAL"
UNRESOLVED = "UNRESOLVED"
_ALLOWED_MODALITIES = {ASSERTED, NECESSARY, POSSIBLE, CONDITIONAL, UNRESOLVED}
_STRONG_ASSERTION_MODALITIES = {ASSERTED, NECESSARY}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def normalize_term(value: Any) -> str:
    """Normalize entity/relation arguments without discarding non-ASCII letters.

    NFKC + casefold gives stable compatibility normalization while Unicode letters/digits and
    combining marks remain evidence-bearing term content. Punctuation becomes token boundaries;
    `_`, `:` and `-` are retained for explicit symbolic identifiers.
    """
    text = unicodedata.normalize("NFKC", str(value or "")).casefold().strip()
    normalized = []
    for char in text:
        category = unicodedata.category(char)
        if char.isalnum() or category.startswith("M") or char in "_:-":
            normalized.append(char)
        else:
            normalized.append(" ")
    return " ".join("".join(normalized).split())


def normalize_predicate(value: Any) -> str:
    predicate = _nonempty(value, "predicate").strip().upper()
    return re.sub(r"[^A-Z0-9_:-]+", "_", predicate).strip("_")


def proposition_core(frame: Mapping[str, Any]) -> dict[str, Any]:
    raw_object = frame.get("object")
    normalized_object = frame.get("normalized_object")
    return {
        "claim_id": str(frame.get("claim_id") or "").strip(),
        "source_id": str(frame.get("source_id") or "").strip(),
        "classification_commitment": str(frame.get("classification_commitment") or "").strip(),
        "content_commitment": str(frame.get("content_commitment") or "").strip(),
        "excerpt_commitment": str(frame.get("excerpt_commitment") or "").strip(),
        "subject": str(frame.get("subject") or "").strip(),
        "predicate": str(frame.get("predicate") or "").strip(),
        "object": None if raw_object is None else str(raw_object).strip(),
        "normalized_subject": str(frame.get("normalized_subject") or "").strip(),
        "normalized_predicate": str(frame.get("normalized_predicate") or "").strip(),
        "normalized_object": None if normalized_object is None else str(normalized_object).strip(),
        "polarity": str(frame.get("polarity") or "").strip().upper(),
        "modality": str(frame.get("modality") or "").strip().upper(),
        "extraction_mode": str(frame.get("extraction_mode") or "").strip(),
        "directionality": "EXPLICIT_TYPED_SUBJECT_PREDICATE_OBJECT",
    }


def proposition_commitment(frame: Mapping[str, Any]) -> str:
    return _commit(b"GREMLIN-CLAIM-PROPOSITION/v0.1", proposition_core(frame))


def build_proposition(
    *,
    classification: Mapping[str, Any],
    claim_id: str,
    source_receipts: Sequence[Mapping[str, Any]],
    subject: str,
    predicate: str,
    object: str | None,
    polarity: str,
    modality: str = ASSERTED,
    extraction_mode: str = "EXPLICIT_TYPED_INPUT",
) -> dict[str, Any]:
    validation = verify_classification(
        classification,
        claim_id=claim_id,
        source_receipts=source_receipts,
    )
    if not validation["valid"]:
        raise ValueError(f"classification failed integrity validation: {validation['errors']}")

    raw_subject = _nonempty(subject, "subject")
    raw_predicate = _nonempty(predicate, "predicate")
    raw_object = None if object is None else str(object).strip()
    if object is not None and not raw_object:
        raise ValueError("object must be non-empty when supplied")

    normalized_subject = normalize_term(raw_subject)
    normalized_predicate = normalize_predicate(raw_predicate)
    normalized_object = None if raw_object is None else normalize_term(raw_object)
    if not normalized_subject:
        raise ValueError("subject normalization produced an empty term")
    if raw_object is not None and not normalized_object:
        raise ValueError("object normalization produced an empty term")

    normalized_polarity = _nonempty(polarity, "polarity").upper()
    if normalized_polarity not in _ALLOWED_POLARITIES:
        raise ValueError(f"unsupported polarity: {normalized_polarity}")
    normalized_modality = _nonempty(modality, "modality").upper()
    if normalized_modality not in _ALLOWED_MODALITIES:
        raise ValueError(f"unsupported modality: {normalized_modality}")

    core = {
        "claim_id": str(claim_id).strip(),
        "source_id": str(classification.get("source_id") or "").strip(),
        "classification_commitment": str(classification.get("classification_commitment") or "").strip(),
        "content_commitment": str(classification.get("content_commitment") or "").strip(),
        "excerpt_commitment": str(classification.get("excerpt_commitment") or "").strip(),
        "subject": raw_subject,
        "predicate": raw_predicate,
        "object": raw_object,
        "normalized_subject": normalized_subject,
        "normalized_predicate": normalized_predicate,
        "normalized_object": normalized_object,
        "polarity": normalized_polarity,
        "modality": normalized_modality,
        "extraction_mode": _nonempty(extraction_mode, "extraction_mode"),
        "directionality": "EXPLICIT_TYPED_SUBJECT_PREDICATE_OBJECT",
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "proposition_commitment": _commit(b"GREMLIN-CLAIM-PROPOSITION/v0.1", core),
        "epistemic_status": "CANDIDATE_PROPOSITION_FRAME",
        "semantic_equivalence_policy": "EXACT_NORMALIZED_FRAME_ONLY_NO_SYNONYM_INFERENCE",
        "term_normalization": "UNICODE_NFKC_CASEFOLD_ALNUM_MARK_SAFE",
        "source_content_authority": "UNTRUSTED_EVIDENCE_ONLY",
        "authority": _authority(),
    }


def verify_proposition(frame: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        core = proposition_core(frame)
    except (TypeError, ValueError):
        return {"valid": False, "errors": ["INVALID_PROPOSITION_FIELD_TYPE"], "authority": _authority()}

    if not core["claim_id"]:
        errors.append("CLAIM_ID_MISSING")
    if not core["source_id"]:
        errors.append("SOURCE_ID_MISSING")
    if not core["classification_commitment"]:
        errors.append("CLASSIFICATION_COMMITMENT_MISSING")
    if not core["content_commitment"]:
        errors.append("CONTENT_COMMITMENT_MISSING")
    if not core["excerpt_commitment"]:
        errors.append("EXCERPT_COMMITMENT_MISSING")
    if normalize_term(core["subject"]) != core["normalized_subject"]:
        errors.append("SUBJECT_NORMALIZATION_MISMATCH")
    try:
        expected_predicate = normalize_predicate(core["predicate"])
    except ValueError:
        expected_predicate = ""
    if expected_predicate != core["normalized_predicate"]:
        errors.append("PREDICATE_NORMALIZATION_MISMATCH")
    expected_object = None if core["object"] is None else normalize_term(core["object"])
    if expected_object != core["normalized_object"]:
        errors.append("OBJECT_NORMALIZATION_MISMATCH")
    if core["polarity"] not in _ALLOWED_POLARITIES:
        errors.append("INVALID_POLARITY")
    if core["modality"] not in _ALLOWED_MODALITIES:
        errors.append("INVALID_MODALITY")
    if not core["extraction_mode"]:
        errors.append("EXTRACTION_MODE_MISSING")

    expected_commitment = _commit(b"GREMLIN-CLAIM-PROPOSITION/v0.1", core)
    if str(frame.get("proposition_commitment") or "").strip() != expected_commitment:
        errors.append("PROPOSITION_COMMITMENT_MISMATCH")
    authority = frame.get("authority")
    if authority is not None and any(
        bool(authority.get(key)) for key in ("production_runtime_write", "execution_admitted", "canon_allowed")
    ):
        errors.append("INVALID_AUTHORITY_ESCALATION")

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "valid": not errors,
        "errors": errors,
        "expected_proposition_commitment": expected_commitment,
        "authority": _authority(),
    }


def compare_propositions(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    left_validation = verify_proposition(left)
    right_validation = verify_proposition(right)
    if not left_validation["valid"] or not right_validation["valid"]:
        return {
            "status": "INVALID_PROPOSITION_FAIL_CLOSED",
            "logical_conflict_candidate": False,
            "left_errors": left_validation["errors"],
            "right_errors": right_validation["errors"],
            "authority": _authority(),
        }

    a = proposition_core(left)
    b = proposition_core(right)
    same_frame = (
        a["normalized_subject"],
        a["normalized_predicate"],
        a["normalized_object"],
    ) == (
        b["normalized_subject"],
        b["normalized_predicate"],
        b["normalized_object"],
    )

    if not same_frame:
        status = "DISTINCT_PROPOSITION_FRAMES"
        conflict = False
    elif a["polarity"] == b["polarity"]:
        status = "CONSISTENT_AT_EXACT_FRAME_LEVEL"
        conflict = False
    elif a["modality"] not in _STRONG_ASSERTION_MODALITIES or b["modality"] not in _STRONG_ASSERTION_MODALITIES:
        status = "POLARITY_DIFF_BUT_MODALITY_BLOCKS_DIRECT_CONTRADICTION"
        conflict = False
    else:
        status = "DIRECT_EXACT_FRAME_POLARITY_CONFLICT_CANDIDATE"
        conflict = True

    core = {
        "status": status,
        "logical_conflict_candidate": conflict,
        "same_exact_normalized_frame": same_frame,
        "left_proposition_commitment": left["proposition_commitment"],
        "right_proposition_commitment": right["proposition_commitment"],
        "left_source_id": a["source_id"],
        "right_source_id": b["source_id"],
        "semantic_equivalence_inferred": False,
        "object_exclusivity_inferred": False,
        "authority": _authority(),
    }
    return {
        **core,
        "comparison_commitment": _commit(b"GREMLIN-PROPOSITION-COMPARISON/v0.1", core),
    }


def scan_proposition_conflicts(frames: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in frames]
    comparisons: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for index, left in enumerate(rows):
        for right in rows[index + 1 :]:
            comparison = compare_propositions(left, right)
            comparisons.append(comparison)
            if comparison.get("logical_conflict_candidate"):
                conflicts.append(comparison)

    core = {
        "frame_count": len(rows),
        "comparison_count": len(comparisons),
        "direct_exact_frame_conflict_candidate_count": len(conflicts),
        "comparisons": comparisons,
        "conflict_candidates": conflicts,
        "policy": "EXACT_SPO_POLARITY_ONLY_MODALITY_GATED_NO_SEMANTIC_EQUIVALENCE_INFERENCE",
        "authority": _authority(),
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "scan_commitment": _commit(b"GREMLIN-PROPOSITION-CONFLICT-SCAN/v0.1", core),
    }
