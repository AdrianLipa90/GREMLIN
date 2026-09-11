from __future__ import annotations

import pytest

from gremlin_mcp.proposition_provider_policy import (
    PropositionProducerAdmissionError,
    PropositionProducerRegistry,
    proposition_producer_descriptor,
    run_registered_proposition_producer,
)


class Producer:
    producer_id = "p"
    producer_version = "1.0"
    model_id = None
    mode = "LOCAL_TEST_NONFIXTURE"

    def __init__(self):
        self.calls = 0

    def extract(self, *, claim_id, classifications, source_receipts):
        self.calls += 1
        return []


def test_descriptor_rejects_non_string_metadata_instead_of_stringifying() -> None:
    for attribute, value, pattern in (
        ("producer_id", 123, "producer_id must be a string"),
        ("producer_version", True, "producer_version must be a string"),
        ("model_id", 99, "model_id must be a string"),
        ("mode", ["LOCAL"], "producer mode must be a string"),
    ):
        producer = Producer()
        setattr(producer, attribute, value)
        with pytest.raises(ValueError, match=pattern):
            proposition_producer_descriptor(producer)


def test_registry_id_and_allow_fixture_do_not_coerce() -> None:
    with pytest.raises(ValueError, match="registry_id must be a string"):
        PropositionProducerRegistry([Producer()], registry_id=123)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="allow_fixture must be boolean"):
        PropositionProducerRegistry([Producer()], allow_fixture=1)  # type: ignore[arg-type]


def test_registry_rejects_invalid_producer_container() -> None:
    with pytest.raises(ValueError, match="producers must be an iterable"):
        PropositionProducerRegistry("producer")  # type: ignore[arg-type]


def test_resolve_rejects_non_string_id_before_lookup() -> None:
    registry = PropositionProducerRegistry([Producer()])
    with pytest.raises(PropositionProducerAdmissionError, match="producer_id must be a string"):
        registry.resolve(123)  # type: ignore[arg-type]


def test_non_boolean_coverage_rejected_before_provider_execution() -> None:
    producer = Producer()
    registry = PropositionProducerRegistry([producer])
    with pytest.raises(ValueError, match="require_complete_coverage must be boolean"):
        run_registered_proposition_producer(
            registry,
            producer_id="p",
            claim_id="claim-1",
            classifications=[],
            source_receipts=[],
            require_complete_coverage="true",  # type: ignore[arg-type]
        )
    assert producer.calls == 0


def test_wrong_registry_type_is_rejected_before_any_resolution() -> None:
    with pytest.raises(PropositionProducerAdmissionError, match="registry must be"):
        run_registered_proposition_producer(
            object(),  # type: ignore[arg-type]
            producer_id="p",
            claim_id="claim-1",
            classifications=[],
            source_receipts=[],
        )


def test_invalid_transport_receipt_json_fails_closed() -> None:
    class BadTransport(Producer):
        producer_id = "bad"

        def transport_receipt(self):
            return {"bad": float("nan")}

    producer = BadTransport()
    registry = PropositionProducerRegistry([producer])
    with pytest.raises(PropositionProducerAdmissionError, match="finite JSON"):
        run_registered_proposition_producer(
            registry,
            producer_id="bad",
            claim_id="claim-1",
            classifications=[],
            source_receipts=[],
        )
