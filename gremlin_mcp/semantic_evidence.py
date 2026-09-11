from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Protocol, Sequence

from gremlin_mcp.evidence_robustness import CONTRADICT, SUPPORT, excerpt_commitment
from gremlin_mcp.research_provenance import verify_source_receipt

SCHEMA = "GREMLIN_SEMANTIC_EVIDENCE_V0_1"
VERSION = "0.1.0"
UNRESOLVED = "UNRESOLVED"
_ALLOWED_STANCES = {SUPPORT, CONTRADICT, UNRESOLVED}
_CLASSIFICATION_KEYS = frozenset(
    {
        "schema", "version", "claim_id", "source_id", "source_family",
        "content_commitment", "excerpt", "excerpt_commitment", "stance",
        "confidence", "producer_id", "producer_version", "model_id", "mode",
        "source_family_origin", "classification_commitment",
        "source_content_authority", "confidence_authority", "authority",
    }
)
_AUTHORITY_KEYS = frozenset({"production_runtime_write", "execution_admitted", "canon_allowed"})
_SOURCE_CONTENT_AUTHORITY = "UNTRUSTED_EVIDENCE_ONLY"
_CONFIDENCE_AUTHORITY = "METADATA_ONLY"
_SOURCE_FAMILY_ORIGIN = "PRODUCER_DECLARED_UNVERIFIED"


class SemanticEvidenceProducer(Protocol):
    """Provider-agnostic ABI for claim/source semantic classification.

    Implementations may use a model, a deterministic domain solver, a human review surface,
    or another bounded classifier. Source text is untrusted evidence and never instruction
    authority. Producers return typed candidate classifications only.
    """

    producer_id: str
    producer_version: str
    model_id: str | None
    mode: str

    def classify(
        self,
        *,
        claim_id: str,
        source_receipts: Sequence[Mapping[str, Any]],
    ) -> Sequence[Mapping[str, Any]]:
        ...


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
        raise ValueError("semantic evidence data must be finite JSON") from exc


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


def _confidence(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("confidence must be a finite number within [0, 1]")
    numeric = float(value)
    if not math.isfinite(numeric) or not 0.0 <= numeric <= 1.0:
        raise ValueError("confidence must be a finite number within [0, 1]")
    return numeric


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


def _mapping_rows(values: Iterable[Mapping[str, Any]], field: str) -> list[Mapping[str, Any]]:
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError(f"{field} must be an iterable of objects")
    try:
        rows = list(values)
    except TypeError as exc:
        raise ValueError(f"{field} must be an iterable of objects") from exc
    if any(not isinstance(row, Mapping) for row in rows):
        raise ValueError(f"{field} must contain only objects")
    return rows


def _stance(value: Any) -> str:
    normalized = _nonempty(value, "stance").upper()
    if normalized not in _ALLOWED_STANCES:
        raise ValueError(f"unsupported stance: {normalized}")
    return normalized


def classification_core(classification: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(classification, Mapping):
        raise ValueError("classification must be an object")
    return {
        "claim_id": _nonempty(classification.get("claim_id"), "claim_id"),
        "source_id": _nonempty(classification.get("source_id"), "source_id"),
        "source_family": _nonempty(classification.get("source_family"), "source_family"),
        "content_commitment": _nonempty(classification.get("content_commitment"), "content_commitment"),
        "excerpt": _nonempty(classification.get("excerpt"), "excerpt"),
        "excerpt_commitment": _nonempty(classification.get("excerpt_commitment"), "excerpt_commitment"),
        "stance": _stance(classification.get("stance")),
        "confidence": _confidence(classification.get("confidence")),
        "producer_id": _nonempty(classification.get("producer_id"), "producer_id"),
        "producer_version": _nonempty(classification.get("producer_version"), "producer_version"),
        "model_id": _optional_text(classification.get("model_id"), "model_id"),
        "mode": _nonempty(classification.get("mode"), "mode"),
        "source_family_origin": _nonempty(classification.get("source_family_origin"), "source_family_origin"),
    }


def classification_commitment(classification: Mapping[str, Any]) -> str:
    return _commit(b"GREMLIN-SEMANTIC-CLASSIFICATION/v0.1", classification_core(classification))


def build_classification(
    *,
    claim_id: str,
    source_receipt: Mapping[str, Any],
    source_family: str,
    excerpt: str,
    stance: str,
    confidence: float,
    producer_id: str,
    producer_version: str,
    model_id: str | None,
    mode: str,
) -> dict[str, Any]:
    if not isinstance(source_receipt, Mapping):
        raise ValueError("source_receipt must be an object")
    receipt_validation = verify_source_receipt(source_receipt)
    if not receipt_validation["valid"]:
        raise ValueError(f"source receipt failed integrity validation: {receipt_validation['errors']}")

    claim = _nonempty(claim_id, "claim_id")
    source_id = _nonempty(source_receipt.get("source_id"), "source_id")
    family = _nonempty(source_family, "source_family")
    text = _nonempty(excerpt, "excerpt")
    evidence_text = source_receipt.get("evidence_text")
    if not isinstance(evidence_text, str):
        raise ValueError("source receipt evidence_text must be a string")
    if text not in evidence_text:
        raise ValueError("excerpt must be a literal substring of source receipt evidence_text")

    core = {
        "claim_id": claim,
        "source_id": source_id,
        "source_family": family,
        "content_commitment": _nonempty(source_receipt.get("content_commitment"), "content_commitment"),
        "excerpt": text,
        "excerpt_commitment": excerpt_commitment(text),
        "stance": _stance(stance),
        "confidence": _confidence(confidence),
        "producer_id": _nonempty(producer_id, "producer_id"),
        "producer_version": _nonempty(producer_version, "producer_version"),
        "model_id": _optional_text(model_id, "model_id"),
        "mode": _nonempty(mode, "mode"),
        "source_family_origin": _SOURCE_FAMILY_ORIGIN,
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "classification_commitment": _commit(b"GREMLIN-SEMANTIC-CLASSIFICATION/v0.1", core),
        "source_content_authority": _SOURCE_CONTENT_AUTHORITY,
        "confidence_authority": _CONFIDENCE_AUTHORITY,
        "authority": _authority(),
    }


def verify_classification(
    classification: Mapping[str, Any],
    *,
    claim_id: str,
    source_receipts: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(classification, Mapping):
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "valid": False,
            "errors": ["CLASSIFICATION_MUST_BE_OBJECT"],
            "source_id": "",
            "stance": None,
        }
    try:
        _reject_unknown_keys(classification, _CLASSIFICATION_KEYS, "classification")
        core = classification_core(classification)
    except (TypeError, ValueError):
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "valid": False,
            "errors": ["INVALID_CLASSIFICATION_FIELD_TYPE"],
            "source_id": classification.get("source_id") if isinstance(classification.get("source_id"), str) else "",
            "stance": None,
        }

    expected_claim = _nonempty(claim_id, "claim_id")
    if core["claim_id"] != expected_claim:
        errors.append("CLAIM_ID_MISMATCH")
    if classification.get("schema") != SCHEMA:
        errors.append("CLASSIFICATION_SCHEMA_MISMATCH")
    if classification.get("version") != VERSION:
        errors.append("CLASSIFICATION_VERSION_MISMATCH")
    if classification.get("source_content_authority") != _SOURCE_CONTENT_AUTHORITY:
        errors.append("INVALID_SOURCE_CONTENT_AUTHORITY")
    if classification.get("confidence_authority") != _CONFIDENCE_AUTHORITY:
        errors.append("INVALID_CONFIDENCE_AUTHORITY")
    if core["source_family_origin"] != _SOURCE_FAMILY_ORIGIN:
        errors.append("INVALID_SOURCE_FAMILY_ORIGIN")
    if not _strict_authority(classification.get("authority")):
        errors.append("INVALID_AUTHORITY_ENVELOPE")

    try:
        receipt_rows = _mapping_rows(source_receipts, "source_receipts")
    except ValueError:
        receipt_rows = []
        errors.append("SOURCE_RECEIPTS_INVALID")

    receipt_by_id: dict[str, Mapping[str, Any]] = {}
    duplicates: set[str] = set()
    for receipt in receipt_rows:
        sid = receipt.get("source_id")
        if not isinstance(sid, str) or not sid.strip():
            errors.append("SOURCE_RECEIPT_ID_INVALID")
            continue
        sid = sid.strip()
        if sid in receipt_by_id:
            duplicates.add(sid)
        receipt_by_id[sid] = receipt
    if core["source_id"] in duplicates:
        errors.append("DUPLICATE_SOURCE_RECEIPT")

    receipt = receipt_by_id.get(core["source_id"])
    if receipt is None:
        errors.append("SOURCE_RECEIPT_MISSING")
    else:
        receipt_validation = verify_source_receipt(receipt)
        if not receipt_validation["valid"]:
            errors.append("SOURCE_RECEIPT_INTEGRITY_FAILED")
        receipt_content = receipt.get("content_commitment")
        if not isinstance(receipt_content, str) or core["content_commitment"] != receipt_content.strip():
            errors.append("CONTENT_COMMITMENT_MISMATCH")
        evidence_text = receipt.get("evidence_text")
        if not isinstance(evidence_text, str):
            errors.append("SOURCE_EVIDENCE_TEXT_INVALID")
        elif core["excerpt"] not in evidence_text:
            errors.append("EXCERPT_NOT_IN_SOURCE_RECEIPT")
        expected_excerpt = excerpt_commitment(core["excerpt"])
        if core["excerpt_commitment"] != expected_excerpt:
            errors.append("EXCERPT_COMMITMENT_MISMATCH")

    supplied_commitment = classification.get("classification_commitment")
    expected_commitment = _commit(b"GREMLIN-SEMANTIC-CLASSIFICATION/v0.1", core)
    if not isinstance(supplied_commitment, str) or not supplied_commitment.strip():
        errors.append("CLASSIFICATION_COMMITMENT_MISSING")
    elif supplied_commitment.strip() != expected_commitment:
        errors.append("CLASSIFICATION_COMMITMENT_MISMATCH")

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "valid": not errors,
        "errors": errors,
        "source_id": core["source_id"],
        "stance": core["stance"],
        "confidence": core["confidence"],
        "expected_classification_commitment": expected_commitment,
        "authority": _authority(),
    }


def normalize_producer_output(
    *,
    claim_id: str,
    source_receipts: Sequence[Mapping[str, Any]],
    classifications: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    claim = _nonempty(claim_id, "claim_id")
    receipt_rows = [dict(row) for row in _mapping_rows(source_receipts, "source_receipts")]
    rows = [dict(row) for row in _mapping_rows(classifications, "classifications")]
    validations = [
        verify_classification(row, claim_id=claim, source_receipts=receipt_rows)
        for row in rows
    ]
    invalid = [
        {"index": index, "source_id": validation["source_id"], "errors": validation["errors"]}
        for index, validation in enumerate(validations)
        if not validation["valid"]
    ]
    seen_pairs: set[tuple[str, str]] = set()
    duplicates: list[dict[str, str]] = []
    for row in rows:
        row_claim = row.get("claim_id")
        row_source = row.get("source_id")
        if not isinstance(row_claim, str) or not isinstance(row_source, str):
            continue
        pair = (row_claim.strip(), row_source.strip())
        if pair in seen_pairs:
            duplicates.append({"claim_id": pair[0], "source_id": pair[1]})
        seen_pairs.add(pair)
    if duplicates:
        invalid.append({"index": -1, "source_id": "", "errors": ["DUPLICATE_CLAIM_SOURCE_CLASSIFICATION"]})

    accepted = [] if invalid else rows
    unresolved = [row for row in accepted if row["stance"] == UNRESOLVED]
    resolved = [row for row in accepted if row["stance"] in {SUPPORT, CONTRADICT}]

    guard_evidence = [
        {
            "evidence_id": row["source_id"],
            "source_family": row["source_family"],
            "stance": row["stance"],
            "content_commitment": row["content_commitment"],
            "excerpt": row["excerpt"],
            "excerpt_commitment": row["excerpt_commitment"],
            "payload_commitment": row["excerpt_commitment"],
            "credibility": row["confidence"],
        }
        for row in resolved
    ]

    core = {
        "claim_id": claim,
        "classification_count": len(rows),
        "resolved_count": len(resolved),
        "unresolved_count": len(unresolved),
        "invalid_count": len(invalid),
        "validations": validations,
        "invalid": invalid,
        "classifications": accepted,
        "guard_evidence": guard_evidence,
        "unresolved_classifications": unresolved,
        "status": "VALID" if not invalid else "INVALID_FAIL_CLOSED",
        "unresolved_policy": "PRESERVE_NOT_COERCE",
        "source_family_policy": "PRODUCER_DECLARED_UNVERIFIED_NOT_INDEPENDENCE_PROOF",
        "authority": _authority(),
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "producer_output_commitment": _commit(b"GREMLIN-SEMANTIC-PRODUCER-OUTPUT/v0.1", core),
    }


@dataclass(frozen=True)
class FixtureAssignment:
    source_id: str
    source_family: str
    excerpt: str
    stance: str
    confidence: float = 1.0


class FixtureSemanticEvidenceProducer:
    """Explicit test-only producer; it does not infer semantics from source text."""

    producer_id = "GREMLIN_FIXTURE_SEMANTIC_PRODUCER"
    producer_version = "0.1.0"
    model_id = None
    mode = "FIXTURE_ONLY_NO_SEMANTIC_INFERENCE"

    def __init__(self, assignments: Iterable[FixtureAssignment]):
        if isinstance(assignments, (str, bytes, Mapping)):
            raise ValueError("fixture assignments must be an iterable of FixtureAssignment")
        self._assignments = list(assignments)
        if any(not isinstance(row, FixtureAssignment) for row in self._assignments):
            raise ValueError("fixture assignments must contain only FixtureAssignment values")

    def classify(
        self,
        *,
        claim_id: str,
        source_receipts: Sequence[Mapping[str, Any]],
    ) -> Sequence[Mapping[str, Any]]:
        receipt_rows = _mapping_rows(source_receipts, "source_receipts")
        by_id: dict[str, Mapping[str, Any]] = {}
        for row in receipt_rows:
            sid = _nonempty(row.get("source_id"), "source_id")
            if sid in by_id:
                raise ValueError(f"duplicate fixture source receipt id: {sid}")
            by_id[sid] = row
        output: list[dict[str, Any]] = []
        for assignment in self._assignments:
            assignment_source = _nonempty(assignment.source_id, "fixture source_id")
            receipt = by_id.get(assignment_source)
            if receipt is None:
                raise ValueError(f"fixture source_id not present in source receipts: {assignment_source}")
            output.append(
                build_classification(
                    claim_id=claim_id,
                    source_receipt=receipt,
                    source_family=assignment.source_family,
                    excerpt=assignment.excerpt,
                    stance=assignment.stance,
                    confidence=assignment.confidence,
                    producer_id=self.producer_id,
                    producer_version=self.producer_version,
                    model_id=self.model_id,
                    mode=self.mode,
                )
            )
        return output


def run_producer(
    producer: SemanticEvidenceProducer,
    *,
    claim_id: str,
    source_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    claim = _nonempty(claim_id, "claim_id")
    producer_id = _nonempty(getattr(producer, "producer_id", None), "producer_id")
    producer_version = _nonempty(getattr(producer, "producer_version", None), "producer_version")
    model_id = _optional_text(getattr(producer, "model_id", None), "model_id")
    mode = _nonempty(getattr(producer, "mode", None), "producer mode")
    receipt_rows = [dict(row) for row in _mapping_rows(source_receipts, "source_receipts")]

    raw = producer.classify(claim_id=claim, source_receipts=receipt_rows)
    result = normalize_producer_output(
        claim_id=claim,
        source_receipts=receipt_rows,
        classifications=raw,
    )
    result["producer"] = {
        "producer_id": producer_id,
        "producer_version": producer_version,
        "model_id": model_id,
        "mode": mode,
    }
    result["external_semantic_provider_executed"] = not mode.startswith("FIXTURE_ONLY")
    result["fixture_semantics_claimed_as_real"] = False
    return result
