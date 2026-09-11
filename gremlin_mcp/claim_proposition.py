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
_AUTHORITY_KEYS = frozenset({"production_runtime_write", "execution_admitted", "canon_allowed"})
_PROPOSITION_KEYS = frozenset(
    {
        "schema",
        "version",
        "claim_id",
        "source_id",
        "classification_commitment",
        "content_commitment",
        "excerpt_commitment",
        "subject",
        "predicate",
        "object",
        "normalized_subject",
        "normalized_predicate",
        "normalized_object",
        "polarity",
        "modality",
        "extraction_mode",
        "directionality",
        "proposition_commitment",
        "epistemic_status",
        "semantic_equivalence_policy",
        "term_normalization",
        "source_content_authority",
        "authority",
    }
)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("claim proposition data must be finite JSON") from exc


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


def _optional_text(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _nonempty(value, name)


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _strict_authority(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == _AUTHORITY_KEYS
        and all(type(value.get(key)) is bool and value.get(key) is False for key in _AUTHORITY_KEYS)
    )


def _reject_unknown_keys(value: Mapping[Any, Any], allowed: frozenset[str], field: str) -> None:
    unknown = [key for key in value if not isinstance(key, str) or key not in allowed]
    if unknown:
        raise ValueError(f"{field} contains unsupported keys: {unknown}")


def _mapping_rows(values: Iterable[Mapping[str, Any]], field: str) -> list[dict[str, Any]]:
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError(f"{field} must be an iterable of objects")
    try:
        raw = list(values)
    except TypeError as exc:
        raise ValueError(f"{field} must be an iterable of objects") from exc
    if any(not isinstance(row, Mapping) for row in raw):
        raise ValueError(f"{field} must contain only objects")
    return [dict(row) for row in raw]


def normalize_term(value: Any) -> str:
    """Normalize a typed string term without discarding non-ASCII letters."""
    if not isinstance(value, str):
        raise ValueError("term must be a string")
    text = unicodedata.normalize("NFKC", value).casefold().strip()
    normalized = []
    for char in text:
        category = unicodedata.category(char)
        if char.isalnum() or category.startswith("M") or char in "_:-":
            normalized.append(char)
        else:
            normalized.append(" ")
    return " ".join("".join(normalized).split())


def normalize_predicate(value: Any) -> str:
    predicate = _nonempty(value, "predicate").upper()
    normalized = re.sub(r"[^A-Z0-9_:-]+", "_", predicate).strip("_")
    if not normalized:
        raise ValueError("predicate normalization produced an empty operator")
    return normalized


def proposition_core(frame: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(frame, Mapping):
        raise ValueError("proposition must be an object")
    raw_object = frame.get("object")
    normalized_object = frame.get("normalized_object")
    polarity = _nonempty(frame.get("polarity"), "polarity").upper()
    modality = _nonempty(frame.get("modality"), "modality").upper()
    return {
        "claim_id": _nonempty(frame.get("claim_id"), "claim_id"),
        "source_id": _nonempty(frame.get("source_id"), "source_id"),
        "classification_commitment": _nonempty(
            frame.get("classification_commitment"), "classification_commitment"
        ),
        "content_commitment": _nonempty(frame.get("content_commitment"), "content_commitment"),
        "excerpt_commitment": _nonempty(frame.get("excerpt_commitment"), "excerpt_commitment"),
        "subject": _nonempty(frame.get("subject"), "subject"),
        "predicate": _nonempty(frame.get("predicate"), "predicate"),
        "object": _optional_text(raw_object, "object"),
        "normalized_subject": _nonempty(frame.get("normalized_subject"), "normalized_subject"),
        "normalized_predicate": _nonempty(frame.get("normalized_predicate"), "normalized_predicate"),
        "normalized_object": _optional_text(normalized_object, "normalized_object"),
        "polarity": polarity,
        "modality": modality,
        "extraction_mode": _nonempty(frame.get("extraction_mode"), "extraction_mode"),
        "directionality": _nonempty(frame.get("directionality"), "directionality"),
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
    if not isinstance(classification, Mapping):
        raise ValueError("classification must be an object")
    claim = _nonempty(claim_id, "claim_id")
    validation = verify_classification(
        classification,
        claim_id=claim,
        source_receipts=source_receipts,
    )
    if not validation["valid"]:
        raise ValueError(f"classification failed integrity validation: {validation['errors']}")

    raw_subject = _nonempty(subject, "subject")
    raw_predicate = _nonempty(predicate, "predicate")
    raw_object = _optional_text(object, "object")

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
        "claim_id": claim,
        "source_id": _nonempty(classification.get("source_id"), "classification.source_id"),
        "classification_commitment": _nonempty(
            classification.get("classification_commitment"), "classification.classification_commitment"
        ),
        "content_commitment": _nonempty(
            classification.get("content_commitment"), "classification.content_commitment"
        ),
        "excerpt_commitment": _nonempty(
            classification.get("excerpt_commitment"), "classification.excerpt_commitment"
        ),
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
    if not isinstance(frame, Mapping):
        return {"valid": False, "errors": ["PROPOSITION_MUST_BE_OBJECT"], "authority": _authority()}
    errors: list[str] = []
    try:
        _reject_unknown_keys(frame, _PROPOSITION_KEYS, "proposition")
        core = proposition_core(frame)
    except (TypeError, ValueError):
        return {"valid": False, "errors": ["INVALID_PROPOSITION_FIELD_TYPE"], "authority": _authority()}

    if frame.get("schema") != SCHEMA:
        errors.append("PROPOSITION_SCHEMA_MISMATCH")
    if frame.get("version") != VERSION:
        errors.append("PROPOSITION_VERSION_MISMATCH")
    if core["directionality"] != "EXPLICIT_TYPED_SUBJECT_PREDICATE_OBJECT":
        errors.append("DIRECTIONALITY_MISMATCH")
    if frame.get("epistemic_status") != "CANDIDATE_PROPOSITION_FRAME":
        errors.append("EPISTEMIC_STATUS_MISMATCH")
    if frame.get("semantic_equivalence_policy") != "EXACT_NORMALIZED_FRAME_ONLY_NO_SYNONYM_INFERENCE":
        errors.append("SEMANTIC_EQUIVALENCE_POLICY_MISMATCH")
    if frame.get("term_normalization") != "UNICODE_NFKC_CASEFOLD_ALNUM_MARK_SAFE":
        errors.append("TERM_NORMALIZATION_POLICY_MISMATCH")
    if frame.get("source_content_authority") != "UNTRUSTED_EVIDENCE_ONLY":
        errors.append("SOURCE_CONTENT_AUTHORITY_MISMATCH")

    try:
        expected_subject = normalize_term(core["subject"])
    except ValueError:
        expected_subject = ""
    if expected_subject != core["normalized_subject"]:
        errors.append("SUBJECT_NORMALIZATION_MISMATCH")
    try:
        expected_predicate = normalize_predicate(core["predicate"])
    except ValueError:
        expected_predicate = ""
    if expected_predicate != core["normalized_predicate"]:
        errors.append("PREDICATE_NORMALIZATION_MISMATCH")
    try:
        expected_object = None if core["object"] is None else normalize_term(core["object"])
    except ValueError:
        expected_object = ""
    if expected_object != core["normalized_object"]:
        errors.append("OBJECT_NORMALIZATION_MISMATCH")
    if core["polarity"] not in _ALLOWED_POLARITIES:
        errors.append("INVALID_POLARITY")
    if core["modality"] not in _ALLOWED_MODALITIES:
        errors.append("INVALID_MODALITY")

    expected_commitment = _commit(b"GREMLIN-CLAIM-PROPOSITION/v0.1", core)
    supplied_commitment = frame.get("proposition_commitment")
    if not isinstance(supplied_commitment, str) or supplied_commitment.strip() != expected_commitment:
        errors.append("PROPOSITION_COMMITMENT_MISMATCH")
    if not _strict_authority(frame.get("authority")):
        errors.append("INVALID_AUTHORITY_ENVELOPE")

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
    rows = _mapping_rows(frames, "frames")
    comparisons: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for index, left in enumerate(rows):
        for right in rows[index + 1 :]:
            comparison = compare_propositions(left, right)
            comparisons.append(comparison)
            if comparison.get("logical_conflict_candidate") is True:
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
