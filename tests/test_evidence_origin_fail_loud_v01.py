from __future__ import annotations

import pytest

from gremlin_mcp.evidence_kind import EMPIRICAL, PRIMARY_EXPERIMENT
from gremlin_mcp.evidence_origin import (
    EXPERIMENT,
    PRIMARY_GENERATION,
    assess_evidence_origin_lineage,
    build_evidence_origin_assignment,
    normalize_evidence_origin_assignments,
    normalize_origin_refs,
    verify_evidence_origin_assignment,
)
from gremlin_mcp.evidence_robustness import SUPPORT
from gremlin_mcp.research_provenance import source_receipt_commitment


def _receipt(source_id: str = "a") -> dict[str, object]:
    text = f"Evidence for {source_id}."
    receipt: dict[str, object] = {
        "source_id": source_id,
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": f"content:{source_id}:v1",
        "content_length_chars": len(text),
        "evidence_text": text,
    }
    receipt["source_receipt_commitment"] = source_receipt_commitment(receipt)
    return receipt


def _origin_assignment(source_id: str = "a") -> dict[str, object]:
    receipt = _receipt(source_id)
    return build_evidence_origin_assignment(
        source_receipt=receipt,
        origin_refs=[
            {
                "origin_id": f"experiment:{source_id}",
                "origin_kind": EXPERIMENT,
                "usage": PRIMARY_GENERATION,
            }
        ],
        producer_id="fixture-origin-producer",
        producer_version="0.1.0",
        mode="FIXTURE_ONLY_EXPLICIT_ORIGIN_ASSIGNMENT",
    )


def test_origin_ref_fields_do_not_silently_coerce() -> None:
    for field, value, pattern in (
        ("origin_id", 123, "origin_id must be a string"),
        ("origin_kind", 123, "origin_kind must be a string"),
        ("usage", False, "usage must be a string"),
    ):
        row = {
            "origin_id": "experiment:A",
            "origin_kind": EXPERIMENT,
            "usage": PRIMARY_GENERATION,
        }
        row[field] = value
        with pytest.raises(ValueError, match=pattern):
            normalize_origin_refs([row])


def test_origin_ref_container_and_unknown_fields_fail_loud() -> None:
    with pytest.raises(ValueError, match="origin_refs must be an iterable of objects"):
        normalize_origin_refs({"origin_id": "x"})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="origin_refs must contain only objects"):
        normalize_origin_refs(["x"])  # type: ignore[list-item]
    with pytest.raises(ValueError, match="unsupported keys"):
        normalize_origin_refs(
            [{"origin_id": "x", "origin_kind": EXPERIMENT, "usage": PRIMARY_GENERATION, "extra": True}]
        )


def test_builder_rejects_non_string_producer_metadata_and_model_id() -> None:
    receipt = _receipt()
    base = {
        "source_receipt": receipt,
        "origin_refs": None,
        "producer_id": "producer",
        "producer_version": "1",
        "mode": "EXPLICIT",
        "rationale_code": "EXPLICIT_ORIGIN_ASSIGNMENT",
        "model_id": None,
    }
    for field, value, pattern in (
        ("producer_id", 7, "producer_id must be a string"),
        ("producer_version", True, "producer_version must be a string"),
        ("mode", ["EXPLICIT"], "mode must be a string"),
        ("rationale_code", 1, "rationale_code must be a string"),
        ("model_id", 123, "model_id must be a string"),
    ):
        kwargs = dict(base)
        kwargs[field] = value
        with pytest.raises(ValueError, match=pattern):
            build_evidence_origin_assignment(**kwargs)  # type: ignore[arg-type]


def test_assignment_unknown_fields_and_malformed_authority_fail_closed() -> None:
    receipt = _receipt()
    assignment = _origin_assignment()
    assignment["extra"] = "ignored-before"
    validation = verify_evidence_origin_assignment(assignment, source_receipts=[receipt])
    assert validation["valid"] is False
    assert validation["errors"] == ["INVALID_EVIDENCE_ORIGIN_ASSIGNMENT_FIELD"]

    assignment = _origin_assignment()
    assignment["authority"] = {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": "false",
    }
    validation = verify_evidence_origin_assignment(assignment, source_receipts=[receipt])
    assert validation["valid"] is False
    assert "INVALID_AUTHORITY_ENVELOPE" in validation["errors"]


def test_normalizer_returns_explicit_invalid_state_for_bad_containers() -> None:
    receipt = _receipt()
    result = normalize_evidence_origin_assignments("bad", source_receipts=[receipt])  # type: ignore[arg-type]
    assert result["status"] == "INVALID_FAIL_CLOSED"
    assert result["invalid_count"] == 1
    assert result["assignments"] == []


def test_lineage_threshold_does_not_coerce_string_float_or_bool() -> None:
    guard = [{"evidence_id": "a", "source_family": "fam-a", "stance": SUPPORT}]
    kinds = [{"source_id": "a", "evidence_kind": PRIMARY_EXPERIMENT}]
    origins = [_origin_assignment()]
    for value in ("2", 2.0, True):
        with pytest.raises(ValueError, match="min_origin_groups must be an integer"):
            assess_evidence_origin_lineage(
                guard,
                evidence_kind_assignments=kinds,
                origin_assignments=origins,
                claim_mode=EMPIRICAL,
                min_origin_groups=value,  # type: ignore[arg-type]
            )


def test_lineage_rejects_unsupported_stance_and_duplicate_assignment_ids() -> None:
    origins = [_origin_assignment()]
    with pytest.raises(ValueError, match="unsupported guard evidence stance"):
        assess_evidence_origin_lineage(
            [{"evidence_id": "a", "source_family": "fam-a", "stance": "MAYBE"}],
            evidence_kind_assignments=[{"source_id": "a", "evidence_kind": PRIMARY_EXPERIMENT}],
            origin_assignments=origins,
            claim_mode=EMPIRICAL,
        )

    with pytest.raises(ValueError, match="duplicate evidence kind source_id"):
        assess_evidence_origin_lineage(
            [{"evidence_id": "a", "source_family": "fam-a", "stance": SUPPORT}],
            evidence_kind_assignments=[
                {"source_id": "a", "evidence_kind": PRIMARY_EXPERIMENT},
                {"source_id": "a", "evidence_kind": PRIMARY_EXPERIMENT},
            ],
            origin_assignments=origins,
            claim_mode=EMPIRICAL,
        )

    with pytest.raises(ValueError, match="duplicate origin assignment source_id"):
        assess_evidence_origin_lineage(
            [{"evidence_id": "a", "source_family": "fam-a", "stance": SUPPORT}],
            evidence_kind_assignments=[{"source_id": "a", "evidence_kind": PRIMARY_EXPERIMENT}],
            origin_assignments=[origins[0], dict(origins[0])],
            claim_mode=EMPIRICAL,
        )
