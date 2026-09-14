from __future__ import annotations

import pytest

import gremlin_mcp.proposition_bridge as bridge
from gremlin_mcp.claim_proposition import AFFIRM
from gremlin_mcp.evidence_robustness import SUPPORT
from gremlin_mcp.proposition_evidence import PROPOSITIONS, FixturePropositionDecision, FixturePropositionProducer
from gremlin_mcp.proposition_provider_policy import PropositionProducerRegistry
from gremlin_mcp.research_provenance import source_receipt_commitment
from gremlin_mcp.semantic_bridge import apply_semantic_producer_output
from gremlin_mcp.semantic_evidence import FixtureAssignment, FixtureSemanticEvidenceProducer, run_producer


def _semantic_execution():
    excerpt = "Information describes geometry in the stated model."
    text = f"Source src-a. {excerpt}"
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
        "query": "information geometry",
        "status": "CANDIDATE_SYNTHESIS_READY",
        "source_receipts": [receipt],
        "citations": [
            {
                "source_id": "src-a",
                "provider": "fixture",
                "title": "Independent Work A About Information Geometry",
                "url": "https://doi.org/10.1000/a",
                "doi": "10.1000/a",
                "published": "2026-08-30",
                "content_basis": receipt["content_basis"],
                "content_commitment": receipt["content_commitment"],
            }
        ],
        "synthesis": {"candidate": "candidate"},
        "authority": {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False},
    }
    semantic_producer = FixtureSemanticEvidenceProducer(
        [FixtureAssignment("src-a", "family-a", excerpt, SUPPORT, 0.9)]
    )
    semantic_output = run_producer(
        semantic_producer,
        claim_id="claim-1",
        source_receipts=[receipt],
    )
    semantic = apply_semantic_producer_output(execution, producer_output=semantic_output)
    classification = semantic["semantic_evidence"]["validation"]["normalized"]["classifications"][0]
    producer = FixturePropositionProducer(
        [
            FixturePropositionDecision(
                source_id="src-a",
                classification_commitment=classification["classification_commitment"],
                decision=PROPOSITIONS,
                frames=(
                    {
                        "subject": "Information",
                        "predicate": "DESCRIBES",
                        "object": "geometry",
                        "polarity": AFFIRM,
                        "modality": "ASSERTED",
                        "support_span": "Information describes geometry",
                    },
                ),
            )
        ]
    )
    registry = PropositionProducerRegistry([producer], allow_fixture=True)
    return semantic, registry, producer


def test_bridge_boolean_flags_do_not_coerce_before_provider_execution() -> None:
    semantic, registry, producer = _semantic_execution()
    for field, value in (("require_complete_coverage", 1), ("quarantine_on_direct_conflict", "false")):
        kwargs = {
            "registry": registry,
            "producer_id": producer.producer_id,
            "require_complete_coverage": True,
            "quarantine_on_direct_conflict": True,
        }
        kwargs[field] = value
        with pytest.raises(ValueError, match=f"{field} must be boolean"):
            bridge.apply_registered_proposition_audit(semantic, **kwargs)  # type: ignore[arg-type]


def test_non_string_semantic_claim_id_fails_precondition_instead_of_stringifying() -> None:
    semantic, registry, producer = _semantic_execution()
    semantic["semantic_evidence"]["validation"]["normalized"]["claim_id"] = 123
    result = bridge.apply_registered_proposition_audit(
        semantic,
        registry=registry,
        producer_id=producer.producer_id,
    )
    assert result["status"] == bridge.SEMANTIC_PRECONDITION_FAILED
    assert "SEMANTIC_CLAIM_ID_INVALID" in result["proposition_analysis"]["semantic_precondition"]["errors"]
    assert result["synthesis"] is None


def test_non_mapping_semantic_classification_row_fails_precondition() -> None:
    semantic, registry, producer = _semantic_execution()
    semantic["semantic_evidence"]["validation"]["normalized"]["classifications"] = ["bad"]
    result = bridge.apply_registered_proposition_audit(
        semantic,
        registry=registry,
        producer_id=producer.producer_id,
    )
    assert result["status"] == bridge.SEMANTIC_PRECONDITION_FAILED
    assert "SEMANTIC_CLASSIFICATIONS_MUST_BE_LIST_OF_OBJECTS" in result["proposition_analysis"]["semantic_precondition"]["errors"]


def test_malformed_family_commitment_fails_semantic_precondition() -> None:
    semantic, registry, producer = _semantic_execution()
    semantic["semantic_evidence"]["provenance_families"]["family_receipt"]["family_set_commitment"] = 123
    result = bridge.apply_registered_proposition_audit(
        semantic,
        registry=registry,
        producer_id=producer.producer_id,
    )
    assert result["status"] == bridge.SEMANTIC_PRECONDITION_FAILED
    assert "SEMANTIC_FAMILY_SET_COMMITMENT_INVALID" in result["proposition_analysis"]["semantic_precondition"]["errors"]


def test_hound_conflict_counts_are_not_integer_coerced(monkeypatch) -> None:
    semantic, registry, producer = _semantic_execution()
    real = bridge.hound_claim_audit

    def malformed(*args, **kwargs):
        out = real(*args, **kwargs)
        out["cross_family_conflict_candidate_count"] = "0"
        return out

    monkeypatch.setattr(bridge, "hound_claim_audit", malformed)
    result = bridge.apply_registered_proposition_audit(
        semantic,
        registry=registry,
        producer_id=producer.producer_id,
    )
    assert result["status"] == bridge.PROPOSITION_HOUND_AUDIT_FAILED
    assert result["synthesis"] is None
    assert result["proposition_analysis"]["reason"] == "HOUND_CONFLICT_COUNTS_MUST_BE_EXACT_NONNEGATIVE_INTEGERS"
