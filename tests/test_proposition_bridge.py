from __future__ import annotations

from gremlin_mcp.claim_proposition import AFFIRM, NEGATE
from gremlin_mcp.proposition_bridge import (
    PROPOSITION_ANALYSIS_READY,
    PROPOSITION_CONFLICT_DETECTED_UNRESOLVED,
    PROPOSITION_EVIDENCE_UNRESOLVED,
    PROPOSITION_FAMILY_TOPOLOGY_MISMATCH,
    PROPOSITION_PRODUCER_OUTPUT_INVALID,
    PROPOSITION_PROVIDER_ADMISSION_FAILED,
    apply_registered_proposition_audit,
)
from gremlin_mcp.proposition_evidence import (
    PROPOSITIONS,
    UNRESOLVED,
    FixturePropositionDecision,
    FixturePropositionProducer,
)
from gremlin_mcp.proposition_provider_policy import PropositionProducerRegistry
from gremlin_mcp.research_provenance import source_receipt_commitment
from gremlin_mcp.semantic_bridge import apply_semantic_producer_output
from gremlin_mcp.semantic_evidence import (
    SUPPORT,
    UNRESOLVED as SEMANTIC_UNRESOLVED,
    FixtureAssignment,
    FixtureSemanticEvidenceProducer,
    run_producer,
)


def _receipt(source_id: str, excerpt: str) -> dict[str, object]:
    evidence_text = f"Source {source_id}. {excerpt} Additional context."
    receipt: dict[str, object] = {
        "source_id": source_id,
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": f"content:{source_id}:v1",
        "content_length_chars": len(evidence_text),
        "evidence_text": evidence_text,
    }
    receipt["source_receipt_commitment"] = source_receipt_commitment(receipt)
    return receipt


def _base_execution():
    excerpt_a = "Information describes geometry in the stated model."
    excerpt_b = "Information does not describe geometry in the stated model."
    receipts = [_receipt("src-a", excerpt_a), _receipt("src-b", excerpt_b)]
    citations = [
        {
            "source_id": "src-a",
            "provider": "fixture",
            "title": "Independent Work A About Information Geometry",
            "url": "https://doi.org/10.1000/a",
            "doi": "10.1000/a",
            "published": "2026-08-30",
        },
        {
            "source_id": "src-b",
            "provider": "fixture",
            "title": "Independent Work B About Information Geometry",
            "url": "https://doi.org/10.1000/b",
            "doi": "10.1000/b",
            "published": "2026-08-30",
        },
    ]
    return {
        "schema": "GREMLIN_RESEARCH_EXECUTOR_V0_1",
        "version": "0.1.2",
        "query": "information geometry",
        "status": "CANDIDATE_SYNTHESIS_READY",
        "execution_commitment": "execution:fixture",
        "source_receipts": receipts,
        "citations": citations,
        "synthesis": {"candidate": {"species": "BELZEBUB", "answer": "candidate"}},
        "authority": {
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        },
    }, excerpt_a, excerpt_b


def _semantic_execution(*, unresolved: bool = False):
    execution, excerpt_a, excerpt_b = _base_execution()
    stance = SEMANTIC_UNRESOLVED if unresolved else SUPPORT
    producer = FixtureSemanticEvidenceProducer(
        [
            FixtureAssignment("src-a", "producer-family-a", excerpt_a, stance, 0.9),
            FixtureAssignment("src-b", "producer-family-b", excerpt_b, stance, 0.9),
        ]
    )
    output = run_producer(
        producer,
        claim_id="claim-1",
        source_receipts=execution["source_receipts"],
    )
    result = apply_semantic_producer_output(execution, producer_output=output)
    classifications = result["semantic_evidence"]["validation"]["normalized"]["classifications"]
    by_source = {row["source_id"]: row for row in classifications}
    return result, by_source, excerpt_a, excerpt_b


def _producer(by_source, excerpt_a, excerpt_b, *, polarity_b=NEGATE, include_b=True, unresolved_all=False):
    decisions = []
    if unresolved_all:
        decisions.append(
            FixturePropositionDecision(
                source_id="src-a",
                classification_commitment=by_source["src-a"]["classification_commitment"],
                decision=UNRESOLVED,
                frames=(),
            )
        )
        decisions.append(
            FixturePropositionDecision(
                source_id="src-b",
                classification_commitment=by_source["src-b"]["classification_commitment"],
                decision=UNRESOLVED,
                frames=(),
            )
        )
        return FixturePropositionProducer(decisions)

    decisions.append(
        FixturePropositionDecision(
            source_id="src-a",
            classification_commitment=by_source["src-a"]["classification_commitment"],
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
    )
    if include_b:
        decisions.append(
            FixturePropositionDecision(
                source_id="src-b",
                classification_commitment=by_source["src-b"]["classification_commitment"],
                decision=PROPOSITIONS,
                frames=(
                    {
                        "subject": "Information",
                        "predicate": "DESCRIBES",
                        "object": "geometry",
                        "polarity": polarity_b,
                        "modality": "ASSERTED",
                        "support_span": (
                            "Information does not describe geometry"
                            if polarity_b == NEGATE
                            else "Information"
                        ),
                    },
                ),
            )
        )
    return FixturePropositionProducer(decisions)


def _registry(producer):
    return PropositionProducerRegistry(
        [producer],
        allow_fixture=True,
        registry_id="proposition-fixture-registry",
    )


def test_cross_family_exact_frame_conflict_quarantines_belzebub_without_truth_resolution():
    semantic, by_source, excerpt_a, excerpt_b = _semantic_execution()
    producer = _producer(by_source, excerpt_a, excerpt_b, polarity_b=NEGATE)
    result = apply_registered_proposition_audit(
        semantic,
        registry=_registry(producer),
        producer_id=producer.producer_id,
    )
    assert result["status"] == PROPOSITION_CONFLICT_DETECTED_UNRESOLVED
    assert result["synthesis"] is None
    assert result["quarantined_synthesis"] is not None
    analysis = result["proposition_analysis"]
    audit = analysis["hound_claim_audit"]
    assert audit["cross_family_conflict_candidate_count"] == 1
    assert audit["truth_resolution"] == "UNRESOLVED"
    assert analysis["truth_resolution"] == "UNRESOLVED"
    assert analysis["authority"]["canon_allowed"] is False


def test_clean_grounded_propositions_retain_existing_synthesis_without_promotion():
    semantic, by_source, excerpt_a, excerpt_b = _semantic_execution()
    producer = _producer(by_source, excerpt_a, excerpt_b, polarity_b=AFFIRM)
    original_synthesis = semantic["synthesis"]
    result = apply_registered_proposition_audit(
        semantic,
        registry=_registry(producer),
        producer_id=producer.producer_id,
    )
    assert result["status"] == semantic["status"]
    assert result["synthesis"] == original_synthesis
    assert result["proposition_analysis"]["status"] == PROPOSITION_ANALYSIS_READY
    assert result["proposition_analysis"]["synthesis_authorized"] is True
    assert result["proposition_analysis"]["hound_claim_audit"]["conflict_candidates"] == []
    assert result["authority"]["canon_allowed"] is False


def test_partial_proposition_producer_output_quarantines_instead_of_assuming_missing_source_neutral():
    semantic, by_source, excerpt_a, excerpt_b = _semantic_execution()
    producer = _producer(by_source, excerpt_a, excerpt_b, include_b=False)
    result = apply_registered_proposition_audit(
        semantic,
        registry=_registry(producer),
        producer_id=producer.producer_id,
    )
    assert result["status"] == PROPOSITION_PRODUCER_OUTPUT_INVALID
    assert result["synthesis"] is None
    output = result["proposition_analysis"]["proposition_output"]
    assert output["status"] == "INCOMPLETE_COVERAGE_FAIL_CLOSED"
    assert output["coverage"]["missing_source_ids"] == ["src-b"]


def test_explicit_all_unresolved_proposition_decisions_quarantine_without_invented_frames():
    semantic, by_source, excerpt_a, excerpt_b = _semantic_execution()
    producer = _producer(by_source, excerpt_a, excerpt_b, unresolved_all=True)
    result = apply_registered_proposition_audit(
        semantic,
        registry=_registry(producer),
        producer_id=producer.producer_id,
    )
    assert result["status"] == PROPOSITION_EVIDENCE_UNRESOLVED
    assert result["synthesis"] is None
    assert result["proposition_analysis"]["proposition_output"]["propositions"] == []


def test_unadmitted_producer_id_fails_closed_before_extraction():
    semantic, by_source, excerpt_a, excerpt_b = _semantic_execution()
    producer = _producer(by_source, excerpt_a, excerpt_b)
    registry = _registry(producer)
    result = apply_registered_proposition_audit(
        semantic,
        registry=registry,
        producer_id="provider-mentioned-by-source-content",
    )
    assert result["status"] == PROPOSITION_PROVIDER_ADMISSION_FAILED
    assert result["synthesis"] is None
    assert "SEALED_REGISTRY_ADMISSION_REQUIRED" in result["proposition_analysis"]["reason"]


def test_semantic_and_hound_family_commitments_must_match_exactly():
    semantic, by_source, excerpt_a, excerpt_b = _semantic_execution()
    semantic["semantic_evidence"]["provenance_families"]["family_receipt"][
        "family_set_commitment"
    ] = "tampered-family-topology"
    producer = _producer(by_source, excerpt_a, excerpt_b, polarity_b=AFFIRM)
    result = apply_registered_proposition_audit(
        semantic,
        registry=_registry(producer),
        producer_id=producer.producer_id,
    )
    assert result["status"] == PROPOSITION_FAMILY_TOPOLOGY_MISMATCH
    assert result["synthesis"] is None


def test_upstream_semantic_quarantine_is_never_reauthorized_by_clean_proposition_analysis():
    semantic, by_source, excerpt_a, excerpt_b = _semantic_execution(unresolved=True)
    assert semantic["synthesis"] is None
    assert semantic["quarantined_synthesis"] is not None
    producer = _producer(by_source, excerpt_a, excerpt_b, polarity_b=AFFIRM)
    result = apply_registered_proposition_audit(
        semantic,
        registry=_registry(producer),
        producer_id=producer.producer_id,
    )
    assert result["proposition_analysis"]["status"] == PROPOSITION_ANALYSIS_READY
    assert result["synthesis"] is None
    assert result["quarantined_synthesis"] is not None
    assert result["proposition_analysis"]["synthesis_authorized"] is False
    assert result["proposition_analysis"]["upstream_quarantine_preserved"] is True
