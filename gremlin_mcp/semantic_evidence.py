from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Protocol, Sequence

from gremlin_mcp.evidence_robustness import CONTRADICT, SUPPORT, excerpt_commitment
from gremlin_mcp.research_provenance import verify_source_receipt

SCHEMA = "GREMLIN_SEMANTIC_EVIDENCE_V0_1"
VERSION = "0.1.0"
UNRESOLVED = "UNRESOLVED"
_ALLOWED_STANCES = {SUPPORT, CONTRADICT, UNRESOLVED}


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


def classification_core(classification: Mapping[str, Any]) -> dict[str, Any]:
    stance = str(classification.get("stance") or "").strip().upper()
    confidence = float(classification.get("confidence", 0.0))
    return {
        "claim_id": str(classification.get("claim_id") or "").strip(),
        "source_id": str(classification.get("source_id") or "").strip(),
        "source_family": str(classification.get("source_family") or "").strip(),
        "content_commitment": str(classification.get("content_commitment") or "").strip(),
        "excerpt": str(classification.get("excerpt") or ""),
        "excerpt_commitment": str(classification.get("excerpt_commitment") or "").strip(),
        "stance": stance,
        "confidence": confidence,
        "producer_id": str(classification.get("producer_id") or "").strip(),
        "producer_version": str(classification.get("producer_version") or "").strip(),
        "model_id": None if classification.get("model_id") is None else str(classification.get("model_id")),
        "mode": str(classification.get("mode") or "").strip(),
        "source_family_origin": str(classification.get("source_family_origin") or "PRODUCER_DECLARED_UNVERIFIED"),
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
    receipt_validation = verify_source_receipt(source_receipt)
    if not receipt_validation["valid"]:
        raise ValueError(f"source receipt failed integrity validation: {receipt_validation['errors']}")

    claim = _nonempty(claim_id, "claim_id")
    source_id = _nonempty(source_receipt.get("source_id"), "source_id")
    family = _nonempty(source_family, "source_family")
    text = _nonempty(excerpt, "excerpt")
    evidence_text = str(source_receipt.get("evidence_text") or "")
    if text not in evidence_text:
        raise ValueError("excerpt must be a literal substring of source receipt evidence_text")

    normalized_stance = _nonempty(stance, "stance").upper()
    if normalized_stance not in _ALLOWED_STANCES:
        raise ValueError(f"unsupported stance: {normalized_stance}")
    numeric_confidence = float(confidence)
    if not 0.0 <= numeric_confidence <= 1.0:
        raise ValueError("confidence must be within [0, 1]")

    core = {
        "claim_id": claim,
        "source_id": source_id,
        "source_family": family,
        "content_commitment": _nonempty(source_receipt.get("content_commitment"), "content_commitment"),
        "excerpt": text,
        "excerpt_commitment": excerpt_commitment(text),
        "stance": normalized_stance,
        "confidence": numeric_confidence,
        "producer_id": _nonempty(producer_id, "producer_id"),
        "producer_version": _nonempty(producer_version, "producer_version"),
        "model_id": None if model_id is None else str(model_id),
        "mode": _nonempty(mode, "mode"),
        "source_family_origin": "PRODUCER_DECLARED_UNVERIFIED",
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "classification_commitment": _commit(b"GREMLIN-SEMANTIC-CLASSIFICATION/v0.1", core),
        "source_content_authority": "UNTRUSTED_EVIDENCE_ONLY",
        "confidence_authority": "METADATA_ONLY",
        "authority": _authority(),
    }


def verify_classification(
    classification: Mapping[str, Any],
    *,
    claim_id: str,
    source_receipts: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        core = classification_core(classification)
    except (TypeError, ValueError):
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "valid": False,
            "errors": ["INVALID_CLASSIFICATION_FIELD_TYPE"],
            "source_id": str(classification.get("source_id") or ""),
            "stance": None,
        }

    expected_claim = str(claim_id or "").strip()
    if not expected_claim:
        raise ValueError("claim_id must be non-empty")
    if core["claim_id"] != expected_claim:
        errors.append("CLAIM_ID_MISMATCH")
    if not core["source_id"]:
        errors.append("SOURCE_ID_MISSING")
    if not core["source_family"]:
        errors.append("SOURCE_FAMILY_MISSING")
    if core["stance"] not in _ALLOWED_STANCES:
        errors.append("INVALID_STANCE")
    if not 0.0 <= core["confidence"] <= 1.0:
        errors.append("INVALID_CONFIDENCE")
    if not core["producer_id"]:
        errors.append("PRODUCER_ID_MISSING")
    if not core["producer_version"]:
        errors.append("PRODUCER_VERSION_MISSING")
    if not core["mode"]:
        errors.append("MODE_MISSING")

    receipt_by_id: dict[str, Mapping[str, Any]] = {}
    duplicates: set[str] = set()
    for receipt in source_receipts:
        sid = str(receipt.get("source_id") or "").strip()
        if not sid:
            continue
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
        if core["content_commitment"] != str(receipt.get("content_commitment") or "").strip():
            errors.append("CONTENT_COMMITMENT_MISMATCH")
        excerpt = core["excerpt"]
        if not excerpt.strip():
            errors.append("EXCERPT_MISSING")
        elif excerpt not in str(receipt.get("evidence_text") or ""):
            errors.append("EXCERPT_NOT_IN_SOURCE_RECEIPT")
        expected_excerpt = None
        if excerpt.strip():
            expected_excerpt = excerpt_commitment(excerpt)
            if core["excerpt_commitment"] != expected_excerpt:
                errors.append("EXCERPT_COMMITMENT_MISMATCH")

    supplied_commitment = str(classification.get("classification_commitment") or "").strip()
    expected_commitment = _commit(b"GREMLIN-SEMANTIC-CLASSIFICATION/v0.1", core)
    if not supplied_commitment:
        errors.append("CLASSIFICATION_COMMITMENT_MISSING")
    elif supplied_commitment != expected_commitment:
        errors.append("CLASSIFICATION_COMMITMENT_MISMATCH")

    if classification.get("source_content_authority") not in (None, "UNTRUSTED_EVIDENCE_ONLY"):
        errors.append("INVALID_SOURCE_CONTENT_AUTHORITY")
    authority = classification.get("authority")
    if authority is not None and any(bool(authority.get(key)) for key in ("production_runtime_write", "execution_admitted", "canon_allowed")):
        errors.append("INVALID_AUTHORITY_ESCALATION")

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "valid": not errors,
        "errors": errors,
        "source_id": core["source_id"],
        "stance": core["stance"] if core["stance"] in _ALLOWED_STANCES else None,
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
    rows = [dict(row) for row in classifications]
    validations = [
        verify_classification(row, claim_id=claim_id, source_receipts=source_receipts)
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
        pair = (str(row.get("claim_id") or "").strip(), str(row.get("source_id") or "").strip())
        if pair in seen_pairs:
            duplicates.append({"claim_id": pair[0], "source_id": pair[1]})
        seen_pairs.add(pair)
    if duplicates:
        invalid.append({"index": -1, "source_id": "", "errors": ["DUPLICATE_CLAIM_SOURCE_CLASSIFICATION"]})

    accepted = [] if invalid else rows
    unresolved = [row for row in accepted if str(row.get("stance") or "").upper() == UNRESOLVED]
    resolved = [row for row in accepted if str(row.get("stance") or "").upper() in {SUPPORT, CONTRADICT}]

    guard_evidence = [
        {
            "evidence_id": row["source_id"],
            "source_family": row["source_family"],
            "stance": str(row["stance"]).upper(),
            "content_commitment": row["content_commitment"],
            "excerpt": row["excerpt"],
            "excerpt_commitment": row["excerpt_commitment"],
            "payload_commitment": row["excerpt_commitment"],
            "credibility": float(row.get("confidence", 0.0)),
        }
        for row in resolved
    ]

    core = {
        "claim_id": str(claim_id).strip(),
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
        self._assignments = list(assignments)

    def classify(
        self,
        *,
        claim_id: str,
        source_receipts: Sequence[Mapping[str, Any]],
    ) -> Sequence[Mapping[str, Any]]:
        by_id = {str(row.get("source_id") or "").strip(): row for row in source_receipts}
        output: list[dict[str, Any]] = []
        for assignment in self._assignments:
            receipt = by_id.get(str(assignment.source_id).strip())
            if receipt is None:
                raise ValueError(f"fixture source_id not present in source receipts: {assignment.source_id}")
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
    if str(getattr(producer, "mode", "")).strip() == "":
        raise ValueError("producer mode must be declared")
    raw = producer.classify(claim_id=claim_id, source_receipts=source_receipts)
    result = normalize_producer_output(
        claim_id=claim_id,
        source_receipts=source_receipts,
        classifications=raw,
    )
    result["producer"] = {
        "producer_id": str(getattr(producer, "producer_id", "")),
        "producer_version": str(getattr(producer, "producer_version", "")),
        "model_id": getattr(producer, "model_id", None),
        "mode": str(getattr(producer, "mode", "")),
    }
    result["external_semantic_provider_executed"] = not str(getattr(producer, "mode", "")).startswith("FIXTURE_ONLY")
    result["fixture_semantics_claimed_as_real"] = False
    return result
