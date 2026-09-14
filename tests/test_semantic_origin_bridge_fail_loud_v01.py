from __future__ import annotations

import pytest

from gremlin_mcp.evidence_kind import EMPIRICAL, PRIMARY_EXPERIMENT, build_evidence_kind_assignment
from gremlin_mcp.evidence_origin import EXPERIMENT, PRIMARY_GENERATION, build_evidence_origin_assignment
from gremlin_mcp.evidence_robustness import SUPPORT
from gremlin_mcp.research_provenance import source_receipt_commitment
from gremlin_mcp.semantic_evidence import FixtureAssignment, FixtureSemanticEvidenceProducer, run_producer
from gremlin_mcp.semantic_origin_bridge import apply_semantic_producer_output_with_origin_lineage


def _setup():
    sentence = "Direct experiment A supports the claim."
    text = f"Source src-a. {sentence}"
    receipt = {
        "source_id": "src-a",
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": "content:src-a:v1",
        "content_length_chars": len(text),
        "evidence_text": text,
    }
    receipt["source_receipt_commitment"] = source_receipt_commitment(receipt)
    execution = {
        "schema": "GREMLIN_RESEARCH_EXECUTOR_V0_1",
        "version": "0.1.2",
        "query": "test",
        "status": "CANDIDATE_SYNTHESIS_READY",
        "synthesis": {"answer": "candidate"},
        "citations": [
            {
                "source_id": "src-a",
                "provider": "fixture",
                "title": "Primary experiment source alpha",
                "url": "https://example.org/a",
                "doi": "10.1000/a",
                "published": "2026-08-30",
                "content_basis": receipt["content_basis"],
                "content_commitment": receipt["content_commitment"],
            }
        ],
        "source_receipts": [receipt],
        "authority": {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False},
    }
    semantic = run_producer(
        FixtureSemanticEvidenceProducer(
            [FixtureAssignment("src-a", "family-a", sentence, SUPPORT, 0.9)]
        ),
        claim_id="claim-a",
        source_receipts=[receipt],
    )
    kind = build_evidence_kind_assignment(
        source_receipt=receipt,
        evidence_kind=PRIMARY_EXPERIMENT,
        producer_id="kind-fixture",
        producer_version="1",
        mode="FIXTURE_ONLY",
    )
    origin = build_evidence_origin_assignment(
        source_receipt=receipt,
        origin_refs=[
            {"origin_id": "experiment:A", "origin_kind": EXPERIMENT, "usage": PRIMARY_GENERATION}
        ],
        producer_id="origin-fixture",
        producer_version="1",
        mode="FIXTURE_ONLY",
    )
    return execution, semantic, kind, origin


def test_kind_assignment_container_does_not_accept_mapping_or_string_iteration() -> None:
    execution, semantic, _, origin = _setup()
    with pytest.raises(ValueError, match="evidence_kind_assignments must be an iterable of objects"):
        apply_semantic_producer_output_with_origin_lineage(
            execution,
            producer_output=semantic,
            evidence_kind_assignments={"source_id": "src-a"},  # type: ignore[arg-type]
            evidence_origin_assignments=[origin],
            claim_mode=EMPIRICAL,
        )


def test_origin_assignment_container_does_not_accept_string_iteration() -> None:
    execution, semantic, kind, _ = _setup()
    with pytest.raises(ValueError, match="evidence_origin_assignments must be an iterable of objects"):
        apply_semantic_producer_output_with_origin_lineage(
            execution,
            producer_output=semantic,
            evidence_kind_assignments=[kind],
            evidence_origin_assignments="bad",  # type: ignore[arg-type]
            claim_mode=EMPIRICAL,
        )


def test_execution_and_producer_output_must_be_objects() -> None:
    execution, semantic, kind, origin = _setup()
    with pytest.raises(ValueError, match="execution must be an object"):
        apply_semantic_producer_output_with_origin_lineage(
            "bad",  # type: ignore[arg-type]
            producer_output=semantic,
            evidence_kind_assignments=[kind],
            evidence_origin_assignments=[origin],
            claim_mode=EMPIRICAL,
        )
    with pytest.raises(ValueError, match="producer_output must be an object"):
        apply_semantic_producer_output_with_origin_lineage(
            execution,
            producer_output="bad",  # type: ignore[arg-type]
            evidence_kind_assignments=[kind],
            evidence_origin_assignments=[origin],
            claim_mode=EMPIRICAL,
        )
