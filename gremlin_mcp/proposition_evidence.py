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
_DECISION_KEYS = frozenset({"source_id", "classification_commitment", "decision", "frames"})
_FRAME_KEYS = frozenset(
    {
        "subject",
        "predicate",
        "object",
        "polarity",
        "modality",
        "support_span",
        "proposition_commitment",
        "support_span_commitment",
        "authority",
    }
)
_GROUNDING_KEYS = frozenset(
    {
        "proposition_commitment",
        "classification_commitment",
        "excerpt_commitment",
        "support_span",
        "support_span_commitment",
        "grounding_policy",
        "grounding_commitment",
    }
)


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
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("proposition producer data must be finite JSON") from exc


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field} must be non-empty")
    return text


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _nonempty(value, field)


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


def _sequence_rows(values: Sequence[Mapping[str, Any]], field: str) -> list[dict[str, Any]]:
    return _mapping_rows(values, field)


def _reject_unknown_keys(value: Mapping[Any, Any], allowed: frozenset[str], field: str) -> None:
    unknown = [key for key in value if not isinstance(key, str) or key not in allowed]
    if unknown:
        raise ValueError(f"{field} contains unsupported keys: {unknown}")


def _strict_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field} must be boolean")
    return value


def support_span_commitment(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("support_span must be a string")
    return _commit(b"GREMLIN-PROPOSITION-SUPPORT-SPAN/v0.1", {"support_span": value})


def _grounding_core(
    *,
    proposition_commitment: str,
    classification_commitment: str,
    excerpt_commitment: str,
    support_span: str,
) -> dict[str, Any]:
    return {
        "proposition_commitment": _nonempty(proposition_commitment, "proposition_commitment"),
        "classification_commitment": _nonempty(classification_commitment, "classification_commitment"),
        "excerpt_commitment": _nonempty(excerpt_commitment, "excerpt_commitment"),
        "support_span": _nonempty(support_span, "support_span"),
        "support_span_commitment": support_span_commitment(support_span),
        "grounding_policy": "LITERAL_SUBSTRING_OF_VERIFIED_CLASSIFICATION_EXCERPT",
    }


def _producer_descriptor(producer: PropositionProducer) -> dict[str, Any]:
    producer_id = _nonempty(getattr(producer, "producer_id", None), "producer_id")
    producer_version = _nonempty(getattr(producer, "producer_version", None), "producer_version")
    mode = _nonempty(getattr(producer, "mode", None), "producer mode")
    model_id = _optional_text(getattr(producer, "model_id", None), "model_id")
    return {
        "producer_id": producer_id,
        "producer_version": producer_version,
        "model_id": model_id,
        "mode": mode,
    }


def _classification_index(
    *,
    claim_id: str,
    classifications: Sequence[Mapping[str, Any]],
    source_receipts: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Mapping[str, Any]], list[dict[str, Any]]]:
    classification_rows = _sequence_rows(classifications, "classifications")
    receipt_rows = _sequence_rows(source_receipts, "source_receipts")
    by_source: dict[str, Mapping[str, Any]] = {}
    invalid: list[dict[str, Any]] = []
    for index, classification in enumerate(classification_rows):
        validation = verify_classification(
            classification,
            claim_id=claim_id,
            source_receipts=receipt_rows,
        )
        raw_source_id = classification.get("source_id")
        source_id = raw_source_id.strip() if isinstance(raw_source_id, str) else ""
        if not validation["valid"]:
            invalid.append({"index": index, "source_id": source_id, "errors": validation["errors"]})
            continue
        if not source_id:
            invalid.append({"index": index, "source_id": "", "errors": ["SOURCE_ID_INVALID"]})
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
    if not isinstance(frame, Mapping):
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "valid": False,
            "errors": ["PROPOSITION_MUST_BE_OBJECT"],
            "source_id": "",
            "expected_grounding": None,
            "expected_grounding_commitment": None,
            "authority": _authority(),
        }
    errors: list[str] = []
    classification_rows = _sequence_rows(classifications, "classifications")
    receipt_rows = _sequence_rows(source_receipts, "source_receipts")
    proposition_validation = verify_proposition(frame)
    if not proposition_validation["valid"]:
        errors.append("PROPOSITION_INTEGRITY_FAILED")

    raw_source_id = frame.get("source_id")
    source_id = raw_source_id.strip() if isinstance(raw_source_id, str) else ""
    if not source_id:
        errors.append("SOURCE_ID_INVALID")
    matching = [
        row
        for row in classification_rows
        if isinstance(row.get("source_id"), str) and row.get("source_id").strip() == source_id
    ]
    if len(matching) != 1:
        errors.append("EXACT_SEMANTIC_CLASSIFICATION_REQUIRED")
        classification = None
    else:
        classification = matching[0]
        classification_validation = verify_classification(
            classification,
            claim_id=claim_id,
            source_receipts=receipt_rows,
        )
        if not classification_validation["valid"]:
            errors.append("SEMANTIC_CLASSIFICATION_INTEGRITY_FAILED")
        frame_commitment = frame.get("classification_commitment")
        classification_commitment = classification.get("classification_commitment")
        if (
            not isinstance(frame_commitment, str)
            or not isinstance(classification_commitment, str)
            or frame_commitment.strip() != classification_commitment.strip()
        ):
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
        try:
            _reject_unknown_keys(grounding, _GROUNDING_KEYS, "producer grounding")
            support_span = _nonempty(grounding.get("support_span"), "support_span")
            excerpt = _nonempty(classification.get("excerpt"), "classification excerpt")
            proposition_commitment_value = _nonempty(
                frame.get("proposition_commitment"), "proposition_commitment"
            )
            classification_commitment_value = _nonempty(
                classification.get("classification_commitment"), "classification_commitment"
            )
            excerpt_commitment_value = _nonempty(
                classification.get("excerpt_commitment"), "excerpt_commitment"
            )
        except ValueError:
            errors.append("GROUNDING_FIELD_TYPE_INVALID")
            expected_grounding = None
            expected_grounding_commitment = None
        else:
            if support_span not in excerpt:
                errors.append("SUPPORT_SPAN_NOT_IN_CLASSIFICATION_EXCERPT")
            expected_grounding = _grounding_core(
                proposition_commitment=proposition_commitment_value,
                classification_commitment=classification_commitment_value,
                excerpt_commitment=excerpt_commitment_value,
                support_span=support_span,
            )
            for key, value in expected_grounding.items():
                if grounding.get(key) != value:
                    errors.append(f"GROUNDING_{key.upper()}_MISMATCH")
            expected_grounding_commitment = _commit(
                b"GREMLIN-PROPOSITION-GROUNDING/v0.1",
                expected_grounding,
            )
            supplied_grounding_commitment = grounding.get("grounding_commitment")
            if (
                not isinstance(supplied_grounding_commitment, str)
                or supplied_grounding_commitment.strip() != expected_grounding_commitment
            ):
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
    claim = _nonempty(claim_id, "claim_id")
    coverage_required = _strict_bool(require_complete_coverage, "require_complete_coverage")
    classification_rows = _sequence_rows(classifications, "classifications")
    receipt_rows = _sequence_rows(source_receipts, "source_receipts")
    if not isinstance(producer, Mapping):
        raise ValueError("producer descriptor must be an object")
    descriptor = {
        "producer_id": _nonempty(producer.get("producer_id"), "producer_id"),
        "producer_version": _nonempty(producer.get("producer_version"), "producer_version"),
        "model_id": _optional_text(producer.get("model_id"), "model_id"),
        "mode": _nonempty(producer.get("mode"), "producer mode"),
    }

    classification_by_source, classification_errors = _classification_index(
        claim_id=claim,
        classifications=classification_rows,
        source_receipts=receipt_rows,
    )
    receipt_by_source: dict[str, Mapping[str, Any]] = {}
    duplicate_receipts: set[str] = set()
    for row in receipt_rows:
        sid_raw = row.get("source_id")
        if not isinstance(sid_raw, str) or not sid_raw.strip():
            classification_errors.append(
                {"index": -1, "source_id": "", "errors": ["SOURCE_RECEIPT_ID_INVALID"]}
            )
            continue
        sid = sid_raw.strip()
        if sid in receipt_by_source:
            duplicate_receipts.add(sid)
        receipt_by_source[sid] = row
    for sid in sorted(duplicate_receipts):
        classification_errors.append(
            {"index": -1, "source_id": sid, "errors": ["DUPLICATE_SOURCE_RECEIPT"]}
        )

    rows = _mapping_rows(decisions, "decisions")
    decision_errors: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    normalized_decisions: list[dict[str, Any]] = []
    propositions: list[dict[str, Any]] = []
    unresolved_sources: list[str] = []

    for index, row in enumerate(rows):
        errors: list[str] = []
        try:
            _reject_unknown_keys(row, _DECISION_KEYS, f"decision at index {index}")
            source_id = _nonempty(row.get("source_id"), "source_id")
            decision = _nonempty(row.get("decision"), "decision").upper()
            supplied_classification_commitment = _nonempty(
                row.get("classification_commitment"), "classification_commitment"
            )
        except ValueError as exc:
            decision_errors.append(
                {"index": index, "source_id": "", "errors": [f"INVALID_DECISION_FIELD:{exc}"]}
            )
            continue

        if source_id in seen_sources:
            errors.append("DUPLICATE_SOURCE_DECISION")
        seen_sources.add(source_id)

        classification = classification_by_source.get(source_id)
        if classification is None:
            errors.append("SEMANTIC_CLASSIFICATION_MISSING_OR_INVALID")
        else:
            expected_classification_commitment = classification.get("classification_commitment")
            if (
                not isinstance(expected_classification_commitment, str)
                or supplied_classification_commitment != expected_classification_commitment.strip()
            ):
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
                excerpt_value = classification.get("excerpt")
                if not isinstance(excerpt_value, str) or not excerpt_value.strip():
                    errors.append("CLASSIFICATION_EXCERPT_INVALID")
                    excerpt = ""
                else:
                    excerpt = excerpt_value
                for frame_index, raw_frame in enumerate(raw_frames):
                    if not isinstance(raw_frame, Mapping):
                        errors.append(f"FRAME_{frame_index}_MUST_BE_MAPPING")
                        continue
                    try:
                        _reject_unknown_keys(raw_frame, _FRAME_KEYS, f"frame {frame_index}")
                        support_span = _nonempty(raw_frame.get("support_span"), "support_span")
                    except ValueError as exc:
                        errors.append(f"FRAME_{frame_index}_REJECTED:ValueError:{exc}")
                        continue
                    if support_span not in excerpt:
                        errors.append(f"FRAME_{frame_index}_SUPPORT_SPAN_NOT_IN_CLASSIFICATION_EXCERPT")
                        continue
                    try:
                        local_frame = build_proposition(
                            classification=classification,
                            claim_id=claim,
                            source_receipts=receipt_rows,
                            subject=raw_frame.get("subject"),  # type: ignore[arg-type]
                            predicate=raw_frame.get("predicate"),  # type: ignore[arg-type]
                            object=raw_frame.get("object"),  # type: ignore[arg-type]
                            polarity=raw_frame.get("polarity"),  # type: ignore[arg-type]
                            modality=raw_frame.get("modality", ASSERTED),  # type: ignore[arg-type]
                            extraction_mode=(
                                f"PRODUCER_PROPOSED_GREMLIN_REBUILT:{descriptor['producer_id']}:{descriptor['producer_version']}"
                            ),
                        )
                    except (TypeError, ValueError) as exc:
                        errors.append(f"FRAME_{frame_index}_REJECTED:{type(exc).__name__}:{exc}")
                        continue
                    classification_commitment_value = _nonempty(
                        classification.get("classification_commitment"), "classification_commitment"
                    )
                    excerpt_commitment_value = _nonempty(
                        classification.get("excerpt_commitment"), "excerpt_commitment"
                    )
                    grounding_core = _grounding_core(
                        proposition_commitment=local_frame["proposition_commitment"],
                        classification_commitment=classification_commitment_value,
                        excerpt_commitment=excerpt_commitment_value,
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
        assert classification is not None
        normalized_decisions.append(
            {
                "source_id": source_id,
                "classification_commitment": _nonempty(
                    classification.get("classification_commitment"), "classification_commitment"
                ),
                "decision": decision,
                "proposition_commitments": [frame["proposition_commitment"] for frame in local_frames],
                "grounding_commitments": [
                    frame["producer_grounding"]["grounding_commitment"] for frame in local_frames
                ],
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
    elif coverage_required and not coverage_complete:
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
            classifications=classification_rows,
            source_receipts=receipt_rows,
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
        "require_complete_coverage": coverage_required,
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
    claim = _nonempty(claim_id, "claim_id")
    classification_rows = _sequence_rows(classifications, "classifications")
    receipt_rows = _sequence_rows(source_receipts, "source_receipts")
    coverage_required = _strict_bool(require_complete_coverage, "require_complete_coverage")
    raw = producer.extract(
        claim_id=claim,
        classifications=classification_rows,
        source_receipts=receipt_rows,
    )
    result = normalize_proposition_producer_output(
        claim_id=claim,
        classifications=classification_rows,
        source_receipts=receipt_rows,
        decisions=raw,
        producer=descriptor,
        require_complete_coverage=coverage_required,
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
        if isinstance(decisions, (str, bytes, Mapping)):
            raise ValueError("fixture decisions must be an iterable of FixturePropositionDecision")
        try:
            rows = list(decisions)
        except TypeError as exc:
            raise ValueError("fixture decisions must be an iterable of FixturePropositionDecision") from exc
        if any(not isinstance(row, FixturePropositionDecision) for row in rows):
            raise ValueError("fixture decisions must contain only FixturePropositionDecision values")
        self._decisions = rows

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
