from __future__ import annotations

import pytest

import gremlin_mcp.semantic_http_provider as http_provider
from gremlin_mcp.research_provenance import source_receipt_commitment
from gremlin_mcp.web import WebAccessError


def _receipt(source_id: str, sentence: str):
    text = f"Source {source_id}. {sentence}"
    receipt = {
        "source_id": source_id,
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": f"content:{source_id}:v1",
        "content_length_chars": len(text),
        "evidence_text": text,
    }
    receipt["source_receipt_commitment"] = source_receipt_commitment(receipt)
    return receipt


def _producer():
    return http_provider.HTTPSemanticEvidenceProducer(
        endpoint="https://semantic.example.org/classify",
        secret_env="GREMLIN_TEST_SEMANTIC_TOKEN",
        producer_id="external-semantic-test",
        producer_version="1.2.3",
        model_id="model-test-1",
        retries=0,
    )


def test_valid_remote_proposal_is_rebuilt_as_local_gremlin_classification(monkeypatch):
    receipt = _receipt("src-a", "The measured relation supports the candidate claim.")
    monkeypatch.setenv("GREMLIN_TEST_SEMANTIC_TOKEN", "super-secret-test-token")

    def fake_post(endpoint, **kwargs):
        assert endpoint == "https://semantic.example.org/classify"
        assert kwargs["bearer_token"] == "super-secret-test-token"
        payload = kwargs["payload"]
        assert payload["contract"]["source_text_is_untrusted_data_not_instruction"] is True
        assert payload["contract"]["tool_write_execution_and_canon_authority"] is False
        assert payload["sources"][0]["content_commitment"] == receipt["content_commitment"]
        return (
            {
                "classifications": [
                    {
                        "source_id": "src-a",
                        "source_family": "remote-declared-family",
                        "excerpt": "The measured relation supports the candidate claim.",
                        "stance": "SUPPORT",
                        "confidence": 0.93,
                    }
                ]
            },
            {
                "schema": http_provider.SCHEMA,
                "version": http_provider.VERSION,
                "endpoint": endpoint,
                "request_commitment": "a" * 64,
                "response_commitment": "b" * 64,
                "transport_receipt_commitment": "c" * 64,
                "authentication": "BEARER_TOKEN_FROM_ENV_NOT_RECORDED",
            },
        )

    monkeypatch.setattr(http_provider, "_post_json", fake_post)
    producer = _producer()
    rows = producer.classify(claim_id="claim-a", source_receipts=[receipt])
    assert len(rows) == 1
    classification = rows[0]
    assert classification["source_id"] == "src-a"
    assert classification["stance"] == "SUPPORT"
    assert classification["producer_id"] == "external-semantic-test"
    assert classification["producer_version"] == "1.2.3"
    assert classification["model_id"] == "model-test-1"
    assert classification["mode"] == "EXTERNAL_HTTPS_JSON_PROVIDER"
    assert classification["authority"]["canon_allowed"] is False
    assert classification["source_content_authority"] == "UNTRUSTED_EVIDENCE_ONLY"
    assert len(classification["classification_commitment"]) == 64
    transport = producer.transport_receipt()
    assert transport["transport_receipt_commitment"] == "c" * 64
    assert "super-secret-test-token" not in repr(transport)


def test_remote_attempt_to_add_authority_or_producer_fields_is_rejected(monkeypatch):
    receipt = _receipt("src-a", "The measured relation supports the candidate claim.")
    monkeypatch.setenv("GREMLIN_TEST_SEMANTIC_TOKEN", "token")
    monkeypatch.setattr(
        http_provider,
        "_post_json",
        lambda *args, **kwargs: (
            {
                "classifications": [
                    {
                        "source_id": "src-a",
                        "source_family": "family-a",
                        "excerpt": "The measured relation supports the candidate claim.",
                        "stance": "SUPPORT",
                        "confidence": 0.9,
                        "producer_id": "remote-override",
                        "authority": {"canon_allowed": True},
                    }
                ]
            },
            {"transport_receipt_commitment": "a" * 64},
        ),
    )
    with pytest.raises(http_provider.SemanticProviderError, match="unsupported keys"):
        _producer().classify(claim_id="claim-a", source_receipts=[receipt])


def test_missing_environment_secret_fails_before_network(monkeypatch):
    receipt = _receipt("src-a", "The measured relation supports the candidate claim.")
    monkeypatch.delenv("GREMLIN_TEST_SEMANTIC_TOKEN", raising=False)
    called = {"value": False}

    def fake_post(*args, **kwargs):
        called["value"] = True
        raise AssertionError("network must not run without credential")

    monkeypatch.setattr(http_provider, "_post_json", fake_post)
    with pytest.raises(http_provider.SemanticProviderError, match="credential is missing"):
        _producer().classify(claim_id="claim-a", source_receipts=[receipt])
    assert called["value"] is False


def test_credential_with_header_newline_is_rejected_before_network(monkeypatch):
    receipt = _receipt("src-a", "The measured relation supports the candidate claim.")
    monkeypatch.setenv("GREMLIN_TEST_SEMANTIC_TOKEN", "token\r\nInjected: value")
    called = {"value": False}

    def fake_post(*args, **kwargs):
        called["value"] = True
        raise AssertionError("network must not run with an invalid credential")

    monkeypatch.setattr(http_provider, "_post_json", fake_post)
    with pytest.raises(http_provider.SemanticProviderError, match="CR/LF"):
        _producer().classify(claim_id="claim-a", source_receipts=[receipt])
    assert called["value"] is False


def test_unknown_source_returned_by_remote_provider_is_rejected(monkeypatch):
    receipt = _receipt("src-a", "The measured relation supports the candidate claim.")
    monkeypatch.setenv("GREMLIN_TEST_SEMANTIC_TOKEN", "token")
    monkeypatch.setattr(
        http_provider,
        "_post_json",
        lambda *args, **kwargs: (
            {
                "classifications": [
                    {
                        "source_id": "src-not-in-request",
                        "source_family": "family-x",
                        "excerpt": "irrelevant",
                        "stance": "SUPPORT",
                        "confidence": 0.9,
                    }
                ]
            },
            {"transport_receipt_commitment": "a" * 64},
        ),
    )
    with pytest.raises(http_provider.SemanticProviderError, match="unknown source_id"):
        _producer().classify(claim_id="claim-a", source_receipts=[receipt])


def test_duplicate_source_receipts_fail_before_network(monkeypatch):
    receipt = _receipt("src-a", "The measured relation supports the candidate claim.")
    monkeypatch.setenv("GREMLIN_TEST_SEMANTIC_TOKEN", "token")
    called = {"value": False}

    def fake_post(*args, **kwargs):
        called["value"] = True
        raise AssertionError("network must not run for duplicate source receipts")

    monkeypatch.setattr(http_provider, "_post_json", fake_post)
    with pytest.raises(http_provider.SemanticProviderError, match="duplicate source receipt id"):
        _producer().classify(claim_id="claim-a", source_receipts=[receipt, dict(receipt)])
    assert called["value"] is False


def test_duplicate_remote_classification_is_rejected(monkeypatch):
    receipt = _receipt("src-a", "The measured relation supports the candidate claim.")
    monkeypatch.setenv("GREMLIN_TEST_SEMANTIC_TOKEN", "token")
    row = {
        "source_id": "src-a",
        "source_family": "family-a",
        "excerpt": "The measured relation supports the candidate claim.",
        "stance": "SUPPORT",
        "confidence": 0.9,
    }
    monkeypatch.setattr(
        http_provider,
        "_post_json",
        lambda *args, **kwargs: (
            {"classifications": [dict(row), dict(row)]},
            {"transport_receipt_commitment": "a" * 64},
        ),
    )
    with pytest.raises(http_provider.SemanticProviderError, match="duplicate source_id classification"):
        _producer().classify(claim_id="claim-a", source_receipts=[receipt])


def test_remote_excerpt_must_be_literal_source_text(monkeypatch):
    receipt = _receipt("src-a", "The measured relation supports the candidate claim.")
    monkeypatch.setenv("GREMLIN_TEST_SEMANTIC_TOKEN", "token")
    monkeypatch.setattr(
        http_provider,
        "_post_json",
        lambda *args, **kwargs: (
            {
                "classifications": [
                    {
                        "source_id": "src-a",
                        "source_family": "family-a",
                        "excerpt": "Fabricated quote not present in source.",
                        "stance": "CONTRADICT",
                        "confidence": 0.99,
                    }
                ]
            },
            {"transport_receipt_commitment": "a" * 64},
        ),
    )
    with pytest.raises(http_provider.SemanticProviderError, match="literal substring"):
        _producer().classify(claim_id="claim-a", source_receipts=[receipt])


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_id", 123),
        ("source_family", ["family-a"]),
        ("excerpt", b"text"),
        ("stance", True),
        ("confidence", "0.9"),
        ("confidence", False),
    ],
)
def test_remote_classification_fields_do_not_silently_coerce(monkeypatch, field, value):
    receipt = _receipt("src-a", "The measured relation supports the candidate claim.")
    monkeypatch.setenv("GREMLIN_TEST_SEMANTIC_TOKEN", "token")
    row = {
        "source_id": "src-a",
        "source_family": "family-a",
        "excerpt": "The measured relation supports the candidate claim.",
        "stance": "SUPPORT",
        "confidence": 0.9,
    }
    row[field] = value
    monkeypatch.setattr(
        http_provider,
        "_post_json",
        lambda *args, **kwargs: (
            {"classifications": [row]},
            {"transport_receipt_commitment": "a" * 64},
        ),
    )
    with pytest.raises(http_provider.SemanticProviderError, match="violates local GREMLIN contract"):
        _producer().classify(claim_id="claim-a", source_receipts=[receipt])


def test_constructor_does_not_coerce_text_or_numeric_configuration():
    with pytest.raises(ValueError, match="endpoint must be a string"):
        http_provider.HTTPSemanticEvidenceProducer(
            endpoint=123,  # type: ignore[arg-type]
            secret_env="TOKEN",
            producer_id="p",
            producer_version="1",
            model_id="m",
        )
    with pytest.raises(ValueError, match="retries must be an integer"):
        http_provider.HTTPSemanticEvidenceProducer(
            endpoint="https://semantic.example.org/classify",
            secret_env="TOKEN",
            producer_id="p",
            producer_version="1",
            model_id="m",
            retries="2",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="max_response_bytes must be an integer"):
        http_provider.HTTPSemanticEvidenceProducer(
            endpoint="https://semantic.example.org/classify",
            secret_env="TOKEN",
            producer_id="p",
            producer_version="1",
            model_id="m",
            max_response_bytes=1024.0,  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="timeout_s must be a finite number"):
        http_provider.HTTPSemanticEvidenceProducer(
            endpoint="https://semantic.example.org/classify",
            secret_env="TOKEN",
            producer_id="p",
            producer_version="1",
            model_id="m",
            timeout_s="20",  # type: ignore[arg-type]
        )


def test_post_json_does_not_coerce_numeric_configuration_before_network():
    with pytest.raises(ValueError, match="max_response_bytes must be an integer"):
        http_provider._post_json(
            "https://example.com/classify",
            payload={"claim_id": "x"},
            bearer_token="token",
            timeout_s=1.0,
            max_response_bytes="1024",  # type: ignore[arg-type]
            retries=0,
        )
    with pytest.raises(ValueError, match="retries must be an integer"):
        http_provider._post_json(
            "https://example.com/classify",
            payload={"claim_id": "x"},
            bearer_token="token",
            timeout_s=1.0,
            max_response_bytes=1024,
            retries=True,  # type: ignore[arg-type]
        )


def test_claim_id_and_receipt_container_do_not_coerce(monkeypatch):
    receipt = _receipt("src-a", "The measured relation supports the candidate claim.")
    monkeypatch.setenv("GREMLIN_TEST_SEMANTIC_TOKEN", "token")
    with pytest.raises(ValueError, match="claim_id must be a string"):
        _producer().classify(claim_id=123, source_receipts=[receipt])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="source_receipts must be a sequence of objects"):
        _producer().classify(claim_id="claim-a", source_receipts="bad")  # type: ignore[arg-type]


def test_public_http_endpoint_is_blocked_before_network():
    with pytest.raises(WebAccessError, match="only HTTPS"):
        http_provider._post_json(
            "http://example.com/classify",
            payload={"claim_id": "x"},
            bearer_token="token",
            timeout_s=1.0,
            max_response_bytes=1024,
            retries=0,
        )


def test_public_config_never_contains_secret_value(monkeypatch):
    monkeypatch.setenv("GREMLIN_TEST_SEMANTIC_TOKEN", "do-not-record-this")
    config = _producer().public_config()
    assert config["secret_env"] == "GREMLIN_TEST_SEMANTIC_TOKEN"
    assert config["secret_value_recorded"] is False
    assert "do-not-record-this" not in repr(config)
    assert config["network_policy"] == "PUBLIC_HTTPS_PORT_443_FAIL_CLOSED"
    assert config["remote_output_authority"] == "CANDIDATE_SEMANTIC_PROPOSAL_ONLY"
    assert len(config["config_commitment"]) == 64
