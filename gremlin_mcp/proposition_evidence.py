from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Protocol, Sequence

from gremlin_mcp.claim_proposition import ASSERTED, build_proposition, verify_proposition
from gremlin_mcp.semantic_evidence import verify_classification

SCHEMA = "GREMLIN_PROPOSITION_PRODUCER_V0_1"
VERSION = "0.1.1"

PROPOSITIONS = "PROPOSITIONS"
UNRESOLVED = "UNRESOLVED"
_ALLOWED_DECISIONS = {PROPOSITIONS, UNRESOLVED}


class PropositionProducer(Protocol):
    """Provider-agnostic ABI for excerpt-bound proposition candidates.

    A producer proposes source-level decisions and raw SPO/polarity/modality fields only. GREMLIN
    reconstructs every accepted proposition locally from the exact current semantic classification
    and source receipt. Each proposed frame must additionally point to a literal support span inside
    the verified classification excerpt. Producer-supplied commitments or authority fields have no
    authority.
    """

    producer_id: str
    producer_version: str
    model_id: str | None
    mode: str

    def extract(
        self,
        *,
        claim_id: str,
        classifications: Sequence[Mapping[str, Any]],
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


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def support_span_commitment(value: str) -> str:
    text = str(value or "")
    return _commit(b"GREMLIN-PROPOSITION-SUPPORT-SPAN/v0.1", {"support_span": text})


def _grounding_core(
    *,
    proposition_commitment: str,
    classification_commitment: str,
    excerpt_commitment: str,
    support_span: str,
) -> dict[str, Any]:
    return {
        "proposition_commitment": str(proposition_commitment),
        "classification_commitment": str(classification_commitment),
        "excerpt_commitment": str(excerpt_commitment),
        "support_span": str(support_span),
        "support_span_commitment": support_span_commitment(support_span),
        "grounding_policy": "LITERAL_SUBSTRING_OF_VERIFIED_CLASSIFICATION_EXCERPT",
    }


def _producer_descriptor(producer: PropositionProducer) -> dict[str, Any]:
    producer_id = str(getattr(producer, "producer_id", "")).strip()
    producer_version = str(getattr(producer, "producer_version", "")).strip()
    mode = str(getattr(producer, "mode", "")).strip()
    if not producer_id:
        raise ValueError("producer_id must be non-empty")
    if not producer_version:
        raise ValueError("producer_version must be non-empty")
    if not mode:
        raise ValueError("producer mode must be non-empty")
    return {
        "producer_id": producer_id,
        "producer_version": producer_version,
        "model_id": getattr(producer, "model_id", None),
        "mode": mode,
    }


def _classification_index(
    *,
    claim_id: str,
    classifications: Sequence[Mapping[str, Any]],
    source_receipts: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Mapping[str, Any]], list[dict[str, Any]]]:
    by_source: dict[str, Mapping[str, Any]] = {}
    invalid: list[dict[str, Any]] = []
    for index, classification in enumerate(classifications):
        validation = verify_classification(
            classification,
            claim_id=claim_id,
            source_receipts=source_receipts,
        )
        source_id = str(classification.get("source_id") or "").strip()
        if not validation["valid"]:
            invalid.append({"index": index, "source_id": source_id, "errors": validation["errors"]})
            continue
        if source_id in by_source:
            invalid.append(
                {
                    "index": index,
                    "source_id": source_id,
                    "errors": ["DUPLICATE_SEMANTIC_CLASSIFICATION_SOURCE_ID"],
                }
            )
            continue
        by_source[source_id] = classification
    return by_source, invalid


def verify_grounded_proposition(
    frame: Mapping[str, Any],
    *,
    claim_id: str,
    classifications: Sequence[Mapping[str, Any]],
    source_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    proposition_validation = verify_proposition(frame)
    if not proposition_validation["valid"]:
        errors.append("PROPOSITION_INTEGRITY_FAILED")

    source_id = str(frame.get("source_id") or "").strip()
    matching = [
        row
        for row in classifications
        if str(row.get("source_id") or "").strip() == source_id
    ]
    if len(matching) != 1:
        errors.append("EXACT_SEMANTIC_CLASSIFICATION_REQUIRED")
        classification = None
    else:
        classification = matching[0]
        classification_validation = verify_classification(
            classification,
            claim_id=claim_id,
            source_receipts=source_receipts,
        )
        if not classification_validation["valid"]:
            errors.append("SEMANTIC_CLASSIFICATION_INTEGRITY_FAILED")
        if str(frame.get("classification_commitment") or "").strip() != str(
            classification.get("classification_commitment") or ""
        ).strip():
            errors.append("CLASSIFICATION_COMMITMENT_MISMATCH")

    grounding = frame.get("producer_grounding")
    if not isinstance(grounding, Mapping):
        errors.append("PRODUCER_GROUNDING_MISSING")
        expected_grounding = None
        expected_grounding_commitment = None
    elif classification is None:
        expected_grounding = None
        expected_grounding_commitment = None
    else:
        support_span = str(grounding.get("support_span") or "")
        excerpt = str(classification.get("excerpt") or "")
        if not support_span.strip():
            errors.append("SUPPORT_SPAN_MISSING")
        elif support_span not in excerpt:
            errors.append("SUPPORT_SPAN_NOT_IN_CLASSIFICATION_EXCERPT")
        expected_grounding = _grounding_core(
            proposition_commitment=str(frame.get("proposition_commitment") or ""),
            classification_commitment=str(classification.get("classification_commitment") or ""),
            excerpt_commitment=str(classification.get("excerpt_commitment") or ""),
            support_span=support_span,
        )
        for key, value in expected_grounding.items():
            if grounding.get(key) != value:
                errors.append(f"GROUNDING_{key.upper()}_MISMATCH")
        expected_grounding_commitment = _commit(
            b"GREMLIN-PROPOSITION-GROUNDING/v0.1",
            expected_grounding,
        )
        if str(grounding.get("grounding_commitment") or "").strip() != expected_grounding_commitment:
            errors.append("GROUNDING_COMMITMENT_MISMATCH")

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "valid": not errors,
        "errors": errors,
        "source_id": source_id,
        "expected_grounding": expected_grounding,
        "expected_grounding_commitment": expected_grounding_commitment,
        "authority": _authority(),
    }


def normalize_proposition_producer_output(
    *,
    claim_id: str,
    classifications: Sequence[Mapping[str, Any]],
    source_receipts: Sequence[Mapping[str, Any]],
    decisions: Iterable[Mapping[str, Any]],
    producer: Mapping[str, Any],
    require_complete_coverage: bool = True,
) -> dict[str, Any]:
    claim = str(claim_id or "").strip()
    if not claim:
        raise ValueError("claim_id must be non-empty")

    descriptor = {
        "producer_id": str(producer.get("producer_id") or "").strip(),
        "producer_version": str(producer.get("producer_version") or "").strip(),
        "model_id": producer.get("model_id"),
        "mode": str(producer.get("mode") or "").strip(),
    }
    if not descriptor["producer_id"] or not descriptor["producer_version"] or not descriptor["mode"]:
        raise ValueError("producer descriptor must include non-empty producer_id, producer_version and mode")

    classification_by_source, classification_errors = _classification_index(
        claim_id=claim,
        classifications=classifications,
        source_receipts=source_receipts,
    )
    receipt_by_source = {
        str(row.get("source_id") or "").strip(): row
        for row in source_receipts
        if str(row.get("source_id") or "").strip()
    }

    rows = [dict(row) for row in decisions]
    decision_errors: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    normalized_decisions: list[dict[str, Any]] = []
    propositions: list[dict[str, Any]] = []
    unresolved_sources: list[str] = []

    for index, row in enumerate(rows):
        source_id = str(row.get("source_id") or "").strip()
        decision = str(row.get("decision") or "").strip().upper()
        errors: list[str] = []
        if not source_id:
            errors.append("SOURCE_ID_MISSING")
        elif source_id in seen_sources:
            errors.append("DUPLICATE_SOURCE_DECISION")
        seen_sources.add(source_id)

        classification = classification_by_source.get(source_id)
        if classification is None:
            errors.append("SEMANTIC_CLASSIFICATION_MISSING_OR_INVALID")
        else:
            supplied_classification_commitment = str(row.get("classification_commitment") or "").strip()
            expected_classification_commitment = str(classification.get("classification_commitment") or "").strip()
            if supplied_classification_commitment != expected_classification_commitment:
                errors.append("CLASSIFICATION_COMMITMENT_MISMATCH")

        if decision not in _ALLOWED_DECISIONS:
            errors.append("INVALID_DECISION")

        raw_frames = row.get("frames")
        if decision == PROPOSITIONS:
            if not isinstance(raw_frames, list) or not raw_frames:
                errors.append("PROPOSITIONS_DECISION_REQUIRES_NONEMPTY_FRAMES")
        elif decision == UNRESOLVED:
            if raw_frames not in (None, []):
                errors.append("UNRESOLVED_DECISION_CANNOT_SUPPLY_FRAMES")

        local_frames: list[dict[str, Any]] = []
        if not errors and decision == PROPOSITIONS and classification is not None:
            receipt = receipt_by_source.get(source_id)
            if receipt is None:
                errors.append("SOURCE_RECEIPT_MISSING")
            else:
                excerpt = str(classification.get("excerpt") or "")
                for frame_index, raw_frame in enumerate(raw_frames):
                    if not isinstance(raw_frame, Mapping):
                        errors.append(f"FRAME_{frame_index}_MUST_BE_MAPPING")
                        continue
                    support_span = str(raw_frame.get("support_span") or "")
                    if not support_span.strip():
                        errors.append(f"FRAME_{frame_index}_SUPPORT_SPAN_MISSING")
                        continue
                    if support_span not in excerpt:
                        errors.append(f"FRAME_{frame_index}_SUPPORT_SPAN_NOT_IN_CLASSIFICATION_EXCERPT")
                        continue
                    try:
                        local_frame = build_proposition(
                            classification=classification,
                            claim_id=claim,
                            source_receipts=source_receipts,
                            subject=str(raw_frame.get("subject") or ""),
                            predicate=str(raw_frame.get("predicate") or ""),
                            object=None if raw_frame.get("object") is None else str(raw_frame.get("object")),
                            polarity=str(raw_frame.get("polarity") or ""),
                            modality=str(raw_frame.get("modality") or ASSERTED),
                            extraction_mode=(
                                f"PRODUCER_PROPOSED_GREMLIN_REBUILT:{descriptor['producer_id']}:{descriptor['producer_version']}"
                            ),
                        )
                    except (TypeError, ValueError) as exc:
                        errors.append(f"FRAME_{frame_index}_REJECTED:{type(exc).__name__}:{exc}")
                        continue
                    grounding_core = _grounding_core(
                        proposition_commitment=local_frame["proposition_commitment"],
                        classification_commitment=str(classification.get("classification_commitment") or ""),
                        excerpt_commitment=str(classification.get("excerpt_commitment") or ""),
                        support_span=support_span,
                    )
                    local_frame["producer_grounding"] = {
                        **grounding_core,
                        "grounding_commitment": _commit(
                            b"GREMLIN-PROPOSITION-GROUNDING/v0.1",
                            grounding_core,
                        ),
                    }
                    local_frame["producer_proposal_index"] = frame_index
                    local_frame["producer_supplied_proposition_commitment_ignored"] = raw_frame.get(
                        "proposition_commitment"
                    )
                    local_frame["producer_supplied_support_span_commitment_ignored"] = raw_frame.get(
                        "support_span_commitment"
                    )
                    local_frame["producer_authority_ignored"] = raw_frame.get("authority")
                    local_frames.append(local_frame)

        if errors:
            decision_errors.append({"index": index, "source_id": source_id, "errors": errors})
            continue

        if decision == UNRESOLVED:
            unresolved_sources.append(source_id)
        else:
            propositions.extend(local_frames)
        normalized_decisions.append(
            {
                "source_id": source_id,
                "classification_commitment": str(classification.get("classification_commitment") or ""),
                "decision": decision,
                "proposition_commitments": [frame["proposition_commitment"] for frame in local_frames],
                "grounding_commitments": [frame["producer_grounding"]["grounding_commitment"] for frame in local_frames],
                "proposition_count": len(local_frames),
            }
        )

    expected_sources = set(classification_by_source)
    covered_sources = {row["source_id"] for row in normalized_decisions}
    missing_sources = sorted(expected_sources - covered_sources)
    unexpected_sources = sorted(
        source_id for source_id in seen_sources if source_id and source_id not in expected_sources
    )
    coverage_complete = (
        not classification_errors
        and not decision_errors
        and not missing_sources
        and not unexpected_sources
        and covered_sources == expected_sources
    )

    if classification_errors or decision_errors:
        status = "INVALID_FAIL_CLOSED"
    elif require_complete_coverage and not coverage_complete:
        status = "INCOMPLETE_COVERAGE_FAIL_CLOSED"
    else:
        status = "VALID"

    accepted_propositions = propositions if status == "VALID" else []
    accepted_decisions = normalized_decisions if status == "VALID" else []
    accepted_unresolved = sorted(unresolved_sources) if status == "VALID" else []

    grounding_validations = [
        verify_grounded_proposition(
            frame,
            claim_id=claim,
            classifications=classifications,
            source_receipts=source_receipts,
        )
        for frame in accepted_propositions
    ]
    if any(not validation["valid"] for validation in grounding_validations):
        status = "GROUNDING_REVALIDATION_FAILED_CLOSED"
        accepted_propositions = []
        accepted_decisions = []
        accepted_unresolved = []

    core = {
        "claim_id": claim,
        "producer": descriptor,
        "decision_count": len(rows),
        "semantic_classification_count": len(classification_by_source),
        "proposition_count": len(accepted_propositions),
        "unresolved_source_count": len(accepted_unresolved),
        "status": status,
        "require_complete_coverage": bool(require_complete_coverage),
        "coverage": {
            "expected_source_ids": sorted(expected_sources),
            "covered_source_ids": sorted(covered_sources),
            "missing_source_ids": missing_sources,
            "unexpected_source_ids": unexpected_sources,
            "complete": coverage_complete,
            "policy": "EVERY_VALID_SEMANTIC_CLASSIFICATION_REQUIRES_PROPOSITIONS_OR_EXPLICIT_UNRESOLVED",
        },
        "classification_errors": classification_errors,
        "decision_errors": decision_errors,
        "grounding_validations": grounding_validations,
        "decisions": accepted_decisions,
        "propositions": accepted_propositions,
        "unresolved_source_ids": accepted_unresolved,
        "producer_commitment_authority": "NONE_REBUILT_LOCALLY",
        "producer_authority_fields": "IGNORED",
        "grounding_policy": "LITERAL_SUPPORT_SPAN_INSIDE_VERIFIED_CLASSIFICATION_EXCERPT",
        "source_content_authority": "UNTRUSTED_EVIDENCE_ONLY",
        "authority": _authority(),
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "proposition_producer_output_commitment": _commit(
            b"GREMLIN-PROPOSITION-PRODUCER-OUTPUT/v0.1", core
        ),
    }


def run_proposition_producer(
    producer: PropositionProducer,
    *,
    claim_id: str,
    classifications: Sequence[Mapping[str, Any]],
    source_receipts: Sequence[Mapping[str, Any]],
    require_complete_coverage: bool = True,
) -> dict[str, Any]:
    descriptor = _producer_descriptor(producer)
    raw = producer.extract(
        claim_id=claim_id,
        classifications=classifications,
        source_receipts=source_receipts,
    )
    result = normalize_proposition_producer_output(
        claim_id=claim_id,
        classifications=classifications,
        source_receipts=source_receipts,
        decisions=raw,
        producer=descriptor,
        require_complete_coverage=require_complete_coverage,
    )
    result["external_proposition_provider_executed"] = not descriptor["mode"].startswith("FIXTURE_ONLY")
    result["fixture_propositions_claimed_as_real"] = False
    return result


@dataclass(frozen=True)
class FixturePropositionDecision:
    source_id: str
    classification_commitment: str
    decision: str
    frames: tuple[Mapping[str, Any], ...] = ()


class FixturePropositionProducer:
    """Explicit test-only producer; it does not infer propositions from source text."""

    producer_id = "GREMLIN_FIXTURE_PROPOSITION_PRODUCER"
    producer_version = "0.1.0"
    model_id = None
    mode = "FIXTURE_ONLY_NO_PROPOSITION_INFERENCE"

    def __init__(self, decisions: Iterable[FixturePropositionDecision]):
        self._decisions = list(decisions)

    def extract(
        self,
        *,
        claim_id: str,
        classifications: Sequence[Mapping[str, Any]],
        source_receipts: Sequence[Mapping[str, Any]],
    ) -> Sequence[Mapping[str, Any]]:
        return [
            {
                "source_id": decision.source_id,
                "classification_commitment": decision.classification_commitment,
                "decision": decision.decision,
                "frames": [dict(frame) for frame in decision.frames],
            }
            for decision in self._decisions
        ]
