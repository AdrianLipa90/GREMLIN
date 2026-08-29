from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

from gremlin_mcp.semantic_bridge import execute_research_with_semantic_producer
from gremlin_mcp.semantic_evidence import SemanticEvidenceProducer

SCHEMA = "GREMLIN_SEMANTIC_PRODUCER_REGISTRY_V0_1"
VERSION = "0.1.0"


class ProducerAdmissionError(RuntimeError):
    pass


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


def producer_descriptor(producer: SemanticEvidenceProducer) -> dict[str, Any]:
    producer_id = str(getattr(producer, "producer_id", "")).strip()
    producer_version = str(getattr(producer, "producer_version", "")).strip()
    mode = str(getattr(producer, "mode", "")).strip()
    model_id = getattr(producer, "model_id", None)
    if not producer_id:
        raise ValueError("producer_id must be non-empty")
    if not producer_version:
        raise ValueError("producer_version must be non-empty")
    if not mode:
        raise ValueError("producer mode must be non-empty")
    return {
        "producer_id": producer_id,
        "producer_version": producer_version,
        "model_id": None if model_id is None else str(model_id),
        "mode": mode,
        "fixture_mode": mode.startswith("FIXTURE_ONLY"),
        "class_module": producer.__class__.__module__,
        "class_name": producer.__class__.__qualname__,
    }


class SemanticProducerRegistry:
    """Sealed local allowlist of semantic producer objects.

    The registry is constructed before research execution and exposes no mutation method.
    Retrieved source content is never consulted when choosing or admitting a producer.
    """

    def __init__(
        self,
        producers: Iterable[SemanticEvidenceProducer],
        *,
        allow_fixture: bool = False,
        registry_id: str = "default",
    ) -> None:
        registry_name = str(registry_id).strip()
        if not registry_name:
            raise ValueError("registry_id must be non-empty")
        entries: dict[str, SemanticEvidenceProducer] = {}
        descriptors: dict[str, dict[str, Any]] = {}
        for producer in producers:
            descriptor = producer_descriptor(producer)
            producer_id = descriptor["producer_id"]
            if producer_id in entries:
                raise ValueError(f"duplicate producer_id in sealed registry: {producer_id}")
            if descriptor["fixture_mode"] and not allow_fixture:
                raise ValueError(
                    f"fixture producer requires allow_fixture=True: {producer_id}"
                )
            entries[producer_id] = producer
            descriptors[producer_id] = descriptor
        self._registry_id = registry_name
        self._allow_fixture = bool(allow_fixture)
        self._entries = entries
        self._descriptors = descriptors
        manifest_core = {
            "registry_id": self._registry_id,
            "allow_fixture": self._allow_fixture,
            "sealed": True,
            "selection_authority": "OPERATOR_CONFIGURED_LOCAL_REGISTRY_ONLY",
            "source_content_may_select_or_register_producer": False,
            "producers": [descriptors[key] for key in sorted(descriptors)],
        }
        self._registry_commitment = _commit(
            b"GREMLIN-SEMANTIC-PRODUCER-REGISTRY/v0.1",
            manifest_core,
        )

    @property
    def registry_commitment(self) -> str:
        return self._registry_commitment

    def manifest(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "registry_id": self._registry_id,
            "allow_fixture": self._allow_fixture,
            "sealed": True,
            "selection_authority": "OPERATOR_CONFIGURED_LOCAL_REGISTRY_ONLY",
            "source_content_may_select_or_register_producer": False,
            "producers": [self._descriptors[key] for key in sorted(self._descriptors)],
            "registry_commitment": self._registry_commitment,
            "authority": _authority(),
        }

    def resolve(self, producer_id: str) -> tuple[SemanticEvidenceProducer, dict[str, Any]]:
        key = str(producer_id).strip()
        if not key:
            raise ProducerAdmissionError("producer_id must be non-empty")
        producer = self._entries.get(key)
        if producer is None:
            raise ProducerAdmissionError(f"producer is not admitted by sealed registry: {key}")
        current = producer_descriptor(producer)
        expected = self._descriptors[key]
        if current != expected:
            raise ProducerAdmissionError(
                f"registered producer metadata changed after registry seal: {key}"
            )
        receipt_core = {
            "producer": current,
            "registry_id": self._registry_id,
            "registry_commitment": self._registry_commitment,
            "admitted": True,
            "selection_authority": "OPERATOR_CONFIGURED_LOCAL_REGISTRY_ONLY",
            "source_content_involved_in_selection": False,
        }
        return producer, {
            "schema": SCHEMA,
            "version": VERSION,
            **receipt_core,
            "admission_commitment": _commit(
                b"GREMLIN-SEMANTIC-PRODUCER-ADMISSION/v0.1",
                receipt_core,
            ),
            "authority": _authority(),
        }


def execute_registered_semantic_research(
    registry: SemanticProducerRegistry,
    *,
    producer_id: str,
    query: str,
    claim_id: str,
    hound_receipt: Mapping[str, Any] | None = None,
    providers: tuple[str, ...] = ("crossref", "arxiv", "duckduckgo"),
    limit_per_provider: int = 6,
    max_species: int = 4,
    max_sources: int = 12,
    require_complete_coverage: bool = True,
) -> dict[str, Any]:
    """Resolve producer admission before any research/network execution."""
    producer, admission = registry.resolve(producer_id)
    result = execute_research_with_semantic_producer(
        query,
        claim_id=claim_id,
        producer=producer,
        hound_receipt=hound_receipt,
        providers=providers,
        limit_per_provider=limit_per_provider,
        max_species=max_species,
        max_sources=max_sources,
        require_complete_coverage=require_complete_coverage,
    )
    out = dict(result)
    out["semantic_producer_admission"] = admission
    out["authority"] = _authority()
    out["registered_semantic_execution_commitment"] = _commit(
        b"GREMLIN-REGISTERED-SEMANTIC-EXECUTION/v0.1",
        {
            "registry_commitment": registry.registry_commitment,
            "admission_commitment": admission["admission_commitment"],
            "semantic_guarded_execution_commitment": out.get("semantic_guarded_execution_commitment"),
            "execution_commitment": out.get("execution_commitment"),
            "status": out.get("status"),
        },
    )
    return out
