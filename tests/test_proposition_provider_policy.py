from __future__ import annotations

import pytest

from gremlin_mcp.claim_proposition import AFFIRM
from gremlin_mcp.evidence_robustness import SUPPORT
from gremlin_mcp.proposition_evidence import (
    PROPOSITIONS,
    FixturePropositionDecision,
    FixturePropositionProducer,
)
from gremlin_mcp.proposition_provider_policy import (
    PropositionProducerAdmissionError,
    PropositionProducerRegistry,
    run_registered_proposition_producer,
)
from gremlin_mcp.research_provenance import source_receipt_commitment
from gremlin_mcp.semantic_evidence import build_classification


def _receipt(source_id: str, excerpt: str) -> dict[str, object]:
    evidence_text = f"Source {source_id}. {excerpt}"
    receipt: dict[str, object] = {
        "source_id": source_id,
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": f"content:{source_id}:v1",
        "content_length_chars": len(evidence_text),
        "evidence_text": evidence_text,
    }
    receipt["source_receipt_commitment"] = source_receipt_commitment(receipt)
    return receipt


def _classification(receipt, excerpt):
    return build_classification(
        claim_id="claim-1",
        source_receipt=receipt,
        source_family="producer-declared-untrusted",
        excerpt=excerpt,
        stance=SUPPORT,
        confidence=0.9,
        producer_id="semantic-fixture",
        producer_version="0.1",
        model_id=None,
        mode="FIXTURE_ONLY_NO_SEMANTIC_INFERENCE",
    )


def _fixture_producer(classification):
    return FixturePropositionProducer(
        [
            FixturePropositionDecision(
                source_id="src-a",
                classification_commitment=classification["classification_commitment"],
                decision=PROPOSITIONS,
                frames=(
                    {
                        "subject": "Informacja",
                        "predicate": "DESCRIBES",
                        "object": "geometria",
                        "polarity": AFFIRM,
                        "modality": "ASSERTED",
                        "support_span": "Informacja opisuje geometrię",
                    },
                ),
            )
        ]
    )


def test_fixture_producer_requires_explicit_registry_admission_flag():
    excerpt = "Informacja opisuje geometrię w tym modelu."
    receipt = _receipt("src-a", excerpt)
    classification = _classification(receipt, excerpt)
    producer = _fixture_producer(classification)
    with pytest.raises(ValueError, match="allow_fixture=True"):
        PropositionProducerRegistry([producer])


def test_manifest_is_sealed_and_denies_source_or_model_selection_authority():
    excerpt = "Informacja opisuje geometrię w tym modelu."
    receipt = _receipt("src-a", excerpt)
    classification = _classification(receipt, excerpt)
    producer = _fixture_producer(classification)
    registry = PropositionProducerRegistry(
        [producer],
        allow_fixture=True,
        registry_id="fixture-registry",
    )
    manifest = registry.manifest()
    assert manifest["sealed"] is True
    assert manifest["selection_authority"] == "OPERATOR_CONFIGURED_LOCAL_REGISTRY_ONLY"
    assert manifest["source_content_may_select_or_register_producer"] is False
    assert manifest["semantic_output_may_select_or_register_producer"] is False
    assert manifest["proposition_output_may_select_or_register_producer"] is False
    assert manifest["authority"]["execution_admitted"] is False
    assert manifest["authority"]["canon_allowed"] is False


def test_unadmitted_source_requested_producer_is_rejected_before_any_execution():
    class CountingProducer:
        producer_id = "admitted"
        producer_version = "1.0"
        model_id = None
        mode = "LOCAL_TEST_NONFIXTURE"

        def __init__(self):
            self.calls = 0

        def extract(self, *, claim_id, classifications, source_receipts):
            self.calls += 1
            return []

    producer = CountingProducer()
    registry = PropositionProducerRegistry([producer], registry_id="sealed")
    source_requested_id = "evil-provider-mentioned-inside-fetched-document"
    with pytest.raises(PropositionProducerAdmissionError, match="not admitted"):
        run_registered_proposition_producer(
            registry,
            producer_id=source_requested_id,
            claim_id="claim-1",
            classifications=[],
            source_receipts=[],
        )
    assert producer.calls == 0


def test_registered_fixture_executes_only_after_explicit_resolution_and_keeps_candidate_authority():
    excerpt = "Informacja opisuje geometrię w tym modelu."
    receipt = _receipt("src-a", excerpt)
    classification = _classification(receipt, excerpt)
    producer = _fixture_producer(classification)
    registry = PropositionProducerRegistry(
        [producer],
        allow_fixture=True,
        registry_id="fixture-registry",
    )
    result = run_registered_proposition_producer(
        registry,
        producer_id=producer.producer_id,
        claim_id="claim-1",
        classifications=[classification],
        source_receipts=[receipt],
    )
    assert result["status"] == "VALID"
    assert result["proposition_count"] == 1
    admission = result["proposition_producer_admission"]
    assert admission["admitted"] is True
    assert admission["source_content_involved_in_selection"] is False
    assert admission["semantic_output_involved_in_selection"] is False
    assert admission["proposition_output_involved_in_selection"] is False
    assert admission["authority"]["canon_allowed"] is False
    assert result["external_proposition_provider_executed"] is False
    assert result["fixture_propositions_claimed_as_real"] is False
    assert result["registered_proposition_execution_commitment"]


def test_provider_metadata_mutation_after_registry_seal_is_rejected():
    class MutableProducer:
        producer_id = "mutable"
        producer_version = "1.0"
        model_id = "model-a"
        mode = "LOCAL_TEST_NONFIXTURE"

        def extract(self, *, claim_id, classifications, source_receipts):
            return []

    producer = MutableProducer()
    registry = PropositionProducerRegistry([producer], registry_id="sealed")
    producer.producer_version = "2.0"
    with pytest.raises(PropositionProducerAdmissionError, match="metadata changed"):
        registry.resolve("mutable")


def test_invalid_transport_receipt_type_fails_closed():
    class BadTransportProducer:
        producer_id = "bad-transport"
        producer_version = "1.0"
        model_id = None
        mode = "LOCAL_TEST_NONFIXTURE"

        def extract(self, *, claim_id, classifications, source_receipts):
            return []

        def transport_receipt(self):
            return "not-a-mapping"

    producer = BadTransportProducer()
    registry = PropositionProducerRegistry([producer], registry_id="sealed")
    with pytest.raises(PropositionProducerAdmissionError, match="transport_receipt"):
        run_registered_proposition_producer(
            registry,
            producer_id="bad-transport",
            claim_id="claim-1",
            classifications=[],
            source_receipts=[],
        )


def test_duplicate_producer_ids_are_rejected_at_registry_construction():
    class ProducerA:
        producer_id = "dup"
        producer_version = "1.0"
        model_id = None
        mode = "LOCAL_TEST_NONFIXTURE"

        def extract(self, *, claim_id, classifications, source_receipts):
            return []

    class ProducerB:
        producer_id = "dup"
        producer_version = "2.0"
        model_id = None
        mode = "LOCAL_TEST_NONFIXTURE"

        def extract(self, *, claim_id, classifications, source_receipts):
            return []

    with pytest.raises(ValueError, match="duplicate proposition producer_id"):
        PropositionProducerRegistry([ProducerA(), ProducerB()])
