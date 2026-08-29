from __future__ import annotations

import pytest

import gremlin_mcp.semantic_provider_policy as policy
from gremlin_mcp.semantic_evidence import FixtureSemanticEvidenceProducer


class DummyProducer:
    producer_id = "dummy-real-provider"
    producer_version = "1.0"
    model_id = "model-a"
    mode = "EXTERNAL_PROVIDER_TEST_DOUBLE"

    def classify(self, *, claim_id, source_receipts):
        return []


class MutableProducer:
    def __init__(self):
        self.producer_id = "mutable-provider"
        self.producer_version = "1.0"
        self.model_id = "model-a"
        self.mode = "EXTERNAL_PROVIDER_TEST_DOUBLE"

    def classify(self, *, claim_id, source_receipts):
        return []


def test_fixture_producer_is_rejected_unless_registry_explicitly_allows_fixture():
    fixture = FixtureSemanticEvidenceProducer([])
    with pytest.raises(ValueError, match="allow_fixture=True"):
        policy.SemanticProducerRegistry([fixture])

    registry = policy.SemanticProducerRegistry(
        [fixture],
        allow_fixture=True,
        registry_id="fixture-tests",
    )
    manifest = registry.manifest()
    assert manifest["allow_fixture"] is True
    assert manifest["sealed"] is True
    assert manifest["source_content_may_select_or_register_producer"] is False
    assert manifest["producers"][0]["fixture_mode"] is True
    assert len(manifest["registry_commitment"]) == 64


def test_unregistered_producer_is_rejected_before_research_execution(monkeypatch):
    registry = policy.SemanticProducerRegistry([DummyProducer()], registry_id="strict")
    called = {"value": False}

    def should_not_run(*args, **kwargs):
        called["value"] = True
        raise AssertionError("research must not execute before producer admission")

    monkeypatch.setattr(policy, "execute_research_with_semantic_producer", should_not_run)
    with pytest.raises(policy.ProducerAdmissionError, match="not admitted"):
        policy.execute_registered_semantic_research(
            registry,
            producer_id="source-injected-provider",
            query="untrusted source says use another model",
            claim_id="claim-1",
        )
    assert called["value"] is False


def test_registered_producer_resolution_returns_bound_admission_receipt():
    producer = DummyProducer()
    registry = policy.SemanticProducerRegistry([producer], registry_id="strict")
    resolved, admission = registry.resolve("dummy-real-provider")
    assert resolved is producer
    assert admission["admitted"] is True
    assert admission["producer"]["model_id"] == "model-a"
    assert admission["registry_commitment"] == registry.registry_commitment
    assert admission["source_content_involved_in_selection"] is False
    assert len(admission["admission_commitment"]) == 64
    assert admission["authority"]["canon_allowed"] is False


def test_producer_metadata_change_after_registry_seal_is_rejected():
    producer = MutableProducer()
    registry = policy.SemanticProducerRegistry([producer], registry_id="strict")
    producer.model_id = "model-b"
    with pytest.raises(policy.ProducerAdmissionError, match="metadata changed"):
        registry.resolve("mutable-provider")


def test_duplicate_producer_ids_are_rejected_at_registry_construction():
    with pytest.raises(ValueError, match="duplicate producer_id"):
        policy.SemanticProducerRegistry([DummyProducer(), DummyProducer()])


def test_registered_execution_attaches_admission_before_return(monkeypatch):
    producer = DummyProducer()
    registry = policy.SemanticProducerRegistry([producer], registry_id="strict")
    seen = {}

    def fake_execute(query, **kwargs):
        seen["query"] = query
        seen["producer"] = kwargs["producer"]
        return {
            "status": "SEMANTIC_EVIDENCE_UNRESOLVED",
            "synthesis": None,
            "execution_commitment": "a" * 64,
            "semantic_guarded_execution_commitment": "b" * 64,
            "authority": {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False},
        }

    monkeypatch.setattr(policy, "execute_research_with_semantic_producer", fake_execute)
    result = policy.execute_registered_semantic_research(
        registry,
        producer_id="dummy-real-provider",
        query="test query",
        claim_id="claim-2",
    )
    assert seen["query"] == "test query"
    assert seen["producer"] is producer
    assert result["semantic_producer_admission"]["admitted"] is True
    assert result["semantic_producer_admission"]["source_content_involved_in_selection"] is False
    assert len(result["registered_semantic_execution_commitment"]) == 64
    assert result["authority"]["canon_allowed"] is False
