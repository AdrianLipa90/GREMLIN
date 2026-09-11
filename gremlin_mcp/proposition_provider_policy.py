from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

from gremlin_mcp.proposition_evidence import PropositionProducer, run_proposition_producer

SCHEMA = "GREMLIN_PROPOSITION_PRODUCER_REGISTRY_V0_1"
VERSION = "0.1.0"


class PropositionProducerAdmissionError(RuntimeError):
    pass


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
        raise ValueError("proposition producer registry data must be finite JSON") from exc


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


def _strict_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field} must be boolean")
    return value


def _producer_rows(values: Iterable[PropositionProducer]) -> list[PropositionProducer]:
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError("producers must be an iterable of producer objects")
    try:
        return list(values)
    except TypeError as exc:
        raise ValueError("producers must be an iterable of producer objects") from exc


def proposition_producer_descriptor(producer: PropositionProducer) -> dict[str, Any]:
    producer_id = _nonempty(getattr(producer, "producer_id", None), "producer_id")
    producer_version = _nonempty(getattr(producer, "producer_version", None), "producer_version")
    mode = _nonempty(getattr(producer, "mode", None), "producer mode")
    model_id = _optional_text(getattr(producer, "model_id", None), "model_id")
    return {
        "producer_id": producer_id,
        "producer_version": producer_version,
        "model_id": model_id,
        "mode": mode,
        "fixture_mode": mode.startswith("FIXTURE_ONLY"),
        "class_module": producer.__class__.__module__,
        "class_name": producer.__class__.__qualname__,
    }


def _transport_receipt(producer: PropositionProducer) -> dict[str, Any] | None:
    accessor = getattr(producer, "transport_receipt", None)
    if not callable(accessor):
        return None
    value = accessor()
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise PropositionProducerAdmissionError(
            "proposition producer transport_receipt() must return a mapping or None"
        )
    receipt = dict(value)
    try:
        _canonical(receipt)
    except ValueError as exc:
        raise PropositionProducerAdmissionError(
            "proposition producer transport_receipt() must contain finite JSON data"
        ) from exc
    return receipt


class PropositionProducerRegistry:
    """Sealed local allowlist for proposition producer objects."""

    def __init__(
        self,
        producers: Iterable[PropositionProducer],
        *,
        allow_fixture: bool = False,
        registry_id: str = "default",
    ) -> None:
        registry_name = _nonempty(registry_id, "registry_id")
        fixture_allowed = _strict_bool(allow_fixture, "allow_fixture")

        entries: dict[str, PropositionProducer] = {}
        descriptors: dict[str, dict[str, Any]] = {}
        for producer in _producer_rows(producers):
            descriptor = proposition_producer_descriptor(producer)
            producer_id = descriptor["producer_id"]
            if producer_id in entries:
                raise ValueError(f"duplicate proposition producer_id in sealed registry: {producer_id}")
            if descriptor["fixture_mode"] and not fixture_allowed:
                raise ValueError(
                    f"fixture proposition producer requires allow_fixture=True: {producer_id}"
                )
            entries[producer_id] = producer
            descriptors[producer_id] = descriptor

        self._registry_id = registry_name
        self._allow_fixture = fixture_allowed
        self._entries = entries
        self._descriptors = descriptors
        manifest_core = {
            "registry_id": self._registry_id,
            "allow_fixture": self._allow_fixture,
            "sealed": True,
            "selection_authority": "OPERATOR_CONFIGURED_LOCAL_REGISTRY_ONLY",
            "source_content_may_select_or_register_producer": False,
            "semantic_output_may_select_or_register_producer": False,
            "proposition_output_may_select_or_register_producer": False,
            "producers": [descriptors[key] for key in sorted(descriptors)],
        }
        self._registry_commitment = _commit(
            b"GREMLIN-PROPOSITION-PRODUCER-REGISTRY/v0.1",
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
            "semantic_output_may_select_or_register_producer": False,
            "proposition_output_may_select_or_register_producer": False,
            "producers": [self._descriptors[key] for key in sorted(self._descriptors)],
            "registry_commitment": self._registry_commitment,
            "authority": _authority(),
        }

    def resolve(self, producer_id: str) -> tuple[PropositionProducer, dict[str, Any]]:
        try:
            key = _nonempty(producer_id, "producer_id")
        except ValueError as exc:
            raise PropositionProducerAdmissionError(str(exc)) from exc
        producer = self._entries.get(key)
        if producer is None:
            raise PropositionProducerAdmissionError(
                f"proposition producer is not admitted by sealed registry: {key}"
            )

        try:
            current = proposition_producer_descriptor(producer)
        except ValueError as exc:
            raise PropositionProducerAdmissionError(
                f"registered proposition producer metadata became invalid after registry seal: {key}: {exc}"
            ) from exc
        expected = self._descriptors[key]
        if current != expected:
            raise PropositionProducerAdmissionError(
                f"registered proposition producer metadata changed after registry seal: {key}"
            )

        receipt_core = {
            "producer": current,
            "registry_id": self._registry_id,
            "registry_commitment": self._registry_commitment,
            "admitted": True,
            "selection_authority": "OPERATOR_CONFIGURED_LOCAL_REGISTRY_ONLY",
            "source_content_involved_in_selection": False,
            "semantic_output_involved_in_selection": False,
            "proposition_output_involved_in_selection": False,
        }
        return producer, {
            "schema": SCHEMA,
            "version": VERSION,
            **receipt_core,
            "admission_commitment": _commit(
                b"GREMLIN-PROPOSITION-PRODUCER-ADMISSION/v0.1",
                receipt_core,
            ),
            "authority": _authority(),
        }


def run_registered_proposition_producer(
    registry: PropositionProducerRegistry,
    *,
    producer_id: str,
    claim_id: str,
    classifications: Sequence[Mapping[str, Any]],
    source_receipts: Sequence[Mapping[str, Any]],
    require_complete_coverage: bool = True,
) -> dict[str, Any]:
    """Resolve local admission before any proposition producer execution."""
    if not isinstance(registry, PropositionProducerRegistry):
        raise PropositionProducerAdmissionError("registry must be a PropositionProducerRegistry")
    coverage_required = _strict_bool(require_complete_coverage, "require_complete_coverage")
    producer, admission = registry.resolve(producer_id)
    result = run_proposition_producer(
        producer,
        claim_id=claim_id,
        classifications=classifications,
        source_receipts=source_receipts,
        require_complete_coverage=coverage_required,
    )
    transport = _transport_receipt(producer)
    out = dict(result)
    out["proposition_producer_admission"] = admission
    out["proposition_provider_transport"] = transport
    out["authority"] = _authority()
    out["registered_proposition_execution_commitment"] = _commit(
        b"GREMLIN-REGISTERED-PROPOSITION-EXECUTION/v0.1",
        {
            "registry_commitment": registry.registry_commitment,
            "admission_commitment": admission["admission_commitment"],
            "transport_receipt_commitment": None
            if transport is None
            else transport.get("transport_receipt_commitment"),
            "proposition_producer_output_commitment": out.get(
                "proposition_producer_output_commitment"
            ),
            "status": out.get("status"),
        },
    )
    return out
